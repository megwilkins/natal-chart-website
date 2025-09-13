# app.py
from flask import Flask, render_template, request
import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from immanuel.charts import Natal, Subject

app = Flask(__name__)

# Which objects we want to show (main planets + angles)
DESIRED = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "Ascendant", "Descendant", "Midheaven", "IC"
]

# Zodiac glyphs for the ring
ZODIAC = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

# Aspect definitions (angle in degrees, orb)
ASPECTS = {
    "Conjunction": (0, 8),
    "Opposition": (180, 8),
    "Trine": (120, 7),
    "Square": (90, 6),
    "Sextile": (60, 6)
}

ANGLE_SET = {"Ascendant", "Midheaven", "Descendant", "IC"}

def format_position(lon):
    """Return string like 23°15′ ♊"""
    deg = int(lon % 30)
    minutes = int((lon % 1) * 60)
    sign = ZODIAC[int(lon // 30)]
    return f"{deg}°{minutes:02d}′ {sign}"

@app.route("/", methods=["GET", "POST"])
def index():
    chart_b64 = None
    planet_table = None

    if request.method == "POST":
        date = request.form["date"]
        time = request.form.get("time", "12:00")
        lat = float(request.form["latitude"])
        lon = float(request.form["longitude"])

        try:
            # Build the natal chart using Subject -> Natal (same pattern that worked in Colab)
            subj = Subject(f"{date} {time}", lat, lon, timezone_offset=0)
            chart = Natal(subj)

            # Gather objects present in chart (only those we want)
            available = [name for name in DESIRED if name in chart.objects]
            # planet_positions in decimal degrees (0..360)
            planet_positions = {}
            planet_symbols = {}
            for name in available:
                obj = chart.objects[name]
                # immanuel object: obj.longitude.raw is the numeric longitude in earlier working code
                # fallback to getattr if slightly different API
                try:
                    lon_deg = obj.longitude.raw
                except Exception:
                    lon_deg = float(obj.longitude)
                planet_positions[name] = lon_deg
                # symbol for table and glyph
                symbol = getattr(obj, "symbol", name)
                planet_symbols[name] = symbol

            # Build the matplotlib polar chart
            fig, ax = plt.subplots(figsize=(10,10), subplot_kw={'projection':'polar'})
            ax.set_facecolor("#0b1c2c")
            ax.set_theta_direction(-1)
            ax.set_theta_offset(np.pi/2)   # 0° at top
            ax.set_ylim(0, 11)
            ax.set_yticklabels([])
            ax.set_xticklabels([])

            # Faint inner rings (subtle grid)
            for r in [2, 4, 6, 8]:
                ax.plot(np.linspace(0, 2*np.pi, 360), [r]*360, color="white", alpha=0.12, linewidth=0.8)

            # Faint house lines (use chart.houses if available)
            try:
                for cusp in chart.houses.values():
                    a = np.radians(cusp.longitude.raw)
                    ax.plot([a, a], [1.5, 8.5], color="white", linewidth=0.8, alpha=0.08)
            except Exception:
                # fallback: no house lines
                pass

            # Zodiac glyphs (just inside dashed circle)
            zodiac_radius = 9.0
            for i, sign in enumerate(ZODIAC):
                start_deg = i * 30 + 15  # center of the sign
                a = np.radians(start_deg)
                ax.text(a, zodiac_radius, sign, fontsize=22, ha='center', va='center', color='white')

            # Outer dashed circle (bold white dashed)
            outer_r = 9.2
            outer_circle = plt.Circle((0,0), outer_r, transform=ax.transData._b,
                                      color="white", fill=False, lw=2.0, linestyle="--", alpha=1.0)
            ax.add_artist(outer_circle)

            # Inner aspect circle (faint)
            inner_circle = plt.Circle((0,0), 7.5, transform=ax.transData._b,
                                      color="white", fill=False, lw=1.0, alpha=0.18)
            ax.add_artist(inner_circle)

            # Plot planets: gold dot inside dashed circle, glyph outside
            dot_r = 8.6     # inside dashed
            glyph_r = 9.8   # outside dashed
            for name in available:
                lon_deg = planet_positions[name]
                theta = np.radians(lon_deg)
                ax.scatter(theta, dot_r, color="gold", s=120, zorder=5)
                ax.text(theta, glyph_r, planet_symbols[name], fontsize=28, ha='center', va='center', color='gold')

            # Build planet table (ordered as in DESIRED, but only present ones)
            planet_table = []
            for name in DESIRED:
                if name in planet_positions:
                    planet_table.append((planet_symbols[name], format_position(planet_positions[name]), name))

            # Aspect lines — compute from positions and ASPECTS table
            names = list(planet_positions.keys())
            for i in range(len(names)):
                for j in range(i+1, len(names)):
                    n1 = names[i]; n2 = names[j]
                    lon1 = planet_positions[n1]
                    lon2 = planet_positions[n2]
                    diff = abs(lon1 - lon2)
                    diff = min(diff, 360 - diff)
                    for angle_deg, orb in ASPECTS.values():
                        if abs(diff - angle_deg) <= orb:
                            t1 = np.radians(lon1)
                            t2 = np.radians(lon2)
                            # dotted if ASC/MC/DESC/IC involved
                            if (n1 in ANGLE_SET) or (n2 in ANGLE_SET):
                                ax.plot([t1, t2], [7.5, 7.5], color="gold", linewidth=1.0, alpha=0.95, linestyle="--", zorder=1)
                            else:
                                ax.plot([t1, t2], [7.5, 7.5], color="gold", linewidth=1.0, alpha=0.9, zorder=1)
                            break

            # Title (optional)
            plt.title("Natal Chart", color="white", fontsize=18, pad=20)

            # Export to base64 PNG
            buf = io.BytesIO()
            plt.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=200)
            plt.close(fig)
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        except Exception as e:
            return f"<h3>Error generating chart: {e}</h3>"

    return render_template("index.html", chart_b64=chart_b64, table=planet_table)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)