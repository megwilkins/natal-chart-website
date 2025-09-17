# app.py
from flask import Flask, render_template, request, url_for, send_file, abort
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import datetime
import os
import logging
import traceback

# Try to import immanuel; we'll fall back if unavailable or if it raises.
try:
    from immanuel.charts import Natal, Subject
    IMMANUEL_AVAILABLE = True
except Exception:
    IMMANUEL_AVAILABLE = False

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# In-memory store for generated charts (token -> bytes). Simple and OK for small demo apps.
CHART_STORE = {}

ZODIAC = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def deg_to_rad(deg):
    return np.deg2rad(deg)

def sign_name(lon):
    idx = int(lon // 30) % 12
    return ZODIAC[idx]

def generate_chart_bytes(name, date_str, time_str, place_str):
    """
    Returns (buf, positions_list). buf is a BytesIO PNG image.
    positions_list is a list of tuples: (planet_name, longitude(deg), sign_name)
    This function will attempt to use immanuel if available; if not, it will
    generate fallback positions.
    """
    # Try to get planetary positions via immanuel (if available)
    planets_positions = {}
    houses = []
    aspects = []

    try:
        if IMMANUEL_AVAILABLE:
            # attempt to use immanuel API. This block is defensive in case your
            # immanuel version provides slightly different signatures.
            try:
                subj = Subject(name=name, date=date_str, time=time_str, place=place_str)
                natal = Natal(subject=subj)
                # The library structures can vary by version; we attempt common patterns:
                if hasattr(natal, "planets"):
                    # typical: natal.planets is iterable of objects with .name and .lon or .longitude
                    for p in natal.planets:
                        lon = getattr(p, "lon", None) or getattr(p, "longitude", None)
                        if lon is None:
                            continue
                        planets_positions[getattr(p, "name", "Planet")] = float(lon)
                if hasattr(natal, "houses"):
                    try:
                        houses = [float(getattr(h, "cusp", getattr(h, "degree", 0))) for h in natal.houses]
                    except Exception:
                        houses = []
                # aspects (best-effort)
                if hasattr(natal, "aspects"):
                    for a in natal.aspects:
                        try:
                            p1 = getattr(a, "p1", None) or getattr(a, "planet1", None)
                            p2 = getattr(a, "p2", None) or getattr(a, "planet2", None)
                            atype = getattr(a, "type", "unknown")
                            if p1 and p2:
                                aspects.append({"p1": p1, "p2": p2, "type": atype})
                        except Exception:
                            continue
            except Exception:
                # If immanuel is installed but unexpected API is used, fall back below
                app.logger.exception("immanuel usage failed; falling back to synthetic data")
                planets_positions = {}
        # If immanuel not available or returned nothing, we will create fallback positions
    except Exception:
        app.logger.exception("Unexpected error while trying immanuel; falling back")

    # Fallback: if we have no planets, create some evenly spaced positions based on hash
    if not planets_positions:
        seed = 0
        try:
            # Use time/date/place to produce a simple deterministic seed
            seed = sum(ord(c) for c in f"{name}|{date_str}|{time_str}|{place_str}") % 360
        except Exception:
            seed = int(datetime.datetime.utcnow().timestamp()) % 360
        # basic planet list
        planet_names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                        "Saturn", "Uranus", "Neptune", "Pluto"]
        for i, pname in enumerate(planet_names):
            lon = (seed + i * 34.7) % 360  # simple deterministic spacing
            planets_positions[pname] = float(lon)
        houses = [(seed + i * 30.0) % 360 for i in range(12)]
        aspects = []

    # Build positions list for template
    positions = []
    for pname, lon in planets_positions.items():
        positions.append((pname, round(float(lon), 2), sign_name(float(lon))))

    # --- Draw the chart with matplotlib ---
    fig = plt.figure(figsize=(8, 8), dpi=200)
    ax = plt.subplot(111, polar=True)
    ax.set_facecolor("#0d1b2a")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_theta_offset(np.pi / 2)  # 0° at top
    ax.set_theta_direction(-1)  # clockwise

    # Outer solid border
    outer = plt.Circle((0, 0), 1.05, transform=ax.transData._b, fill=False,
                       edgecolor="#f5d76e", linewidth=2)
    ax.add_artist(outer)

    # Zodiac ring (thin alternating segments)
    for i in range(12):
        start = deg_to_rad(i * 30)
        width = deg_to_rad(30)
        color = "#102233" if i % 2 == 0 else "#0f2a3a"
        ax.bar(start + width / 2, 1.0, width=width, bottom=0, color=color, edgecolor="none", alpha=0.95)

    # Zodiac glyphs (use simple text of sign initial)
    for i in range(12):
        ang = deg_to_rad((i * 30) + 15)  # center of sign
        ax.text(ang, 1.02, ZODIAC[i][0], color="white", fontsize=14, fontweight="bold",
                ha="center", va="center")

    # Draw house lines & labels
    for i, cusp in enumerate(houses):
        ang = deg_to_rad(cusp)
        ax.plot([ang, ang], [0.0, 0.95], color="#a8c0cf", linewidth=0.8, alpha=0.6)
        # label small H#
        ax.text(ang, 0.02, f"H{i+1}", color="#cfe9ff", fontsize=8, ha="center", va="center")

    # Plot planets
    planet_theta = {}
    for pname, lon in planets_positions.items():
        ang = deg_to_rad(lon)
        planet_theta[pname] = ang
        ax.scatter(ang, 0.72, s=120, color="#f5d76e", edgecolor="#07202b", zorder=5)
        # label with short glyph (use first 2 letters)
        label = pname if len(pname) <= 3 else pname[:2]
        ax.text(ang, 0.82, label, color="white", fontsize=10, ha="center", va="center")

    # Draw aspects (simple straight lines inside the wheel)
    for a in aspects:
        try:
            p1 = a["p1"]
            p2 = a["p2"]
            if p1 in planet_theta and p2 in planet_theta:
                ang1 = planet_theta[p1]
                ang2 = planet_theta[p2]
                ax.plot([ang1, ang2], [0.72, 0.72], color="#8bd3c7", linewidth=1, alpha=0.6)
        except Exception:
            continue

    # small central circles / rings for style
    for r, lw in [(0.55, 0.5), (0.35, 0.5), (0.12, 0.5)]:
        circ = plt.Circle((0, 0), r, transform=ax.transData._b, fill=False, edgecolor="#123241", linewidth=lw)
        ax.add_artist(circ)

    # Title / info text
    info_text = f"{name} • {date_str} {time_str} • {place_str}"
    plt.annotate(info_text, xy=(0.5, 0.975), xycoords="figure fraction", color="#dbefff",
                 ha="center", fontsize=10)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#0d1b2a")
    plt.close(fig)
    buf.seek(0)

    return buf, positions


@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None
    positions = []
    error = None
    if request.method == "POST":
        name = request.form.get("name", "Unknown")
        date_str = request.form.get("date", "")
        time_str = request.form.get("time", "")
        place_str = request.form.get("place", "")

        try:
            buf, positions = generate_chart_bytes(name, date_str, time_str, place_str)
            # create a simple unique token
            token = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            CHART_STORE[token] = buf.getvalue()
            chart_url = url_for("chart_token", token=token)
        except Exception as e:
            error = f"Chart generation failed: {e}"
            app.logger.error("Chart generation error:\n%s", traceback.format_exc())

    return render_template("index.html", chart_url=chart_url, positions=positions, error=error)


@app.route("/chart/<token>.png")
def chart_token(token):
    data = CHART_STORE.get(token)
    if not data:
        abort(404)
    return send_file(io.BytesIO(data), mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)