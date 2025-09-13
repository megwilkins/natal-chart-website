import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, url_for
from immanuel.charts import Natal, Subject

app = Flask(__name__)

# Planet + Angle symbols
PLANET_SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Ascendant": "ASC",
    "Descendant": "DSC",
    "Midheaven": "MC",
    "IC": "IC"
}

ZODIAC = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

# Include 10 planets + 4 angles
PLANET_ORDER = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "Ascendant", "Descendant", "Midheaven", "IC"
]

@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None
    planet_table = []
    if request.method == "POST":
        date = request.form.get("date")
        time_str = request.form.get("time")
        latitude = float(request.form.get("latitude"))
        longitude = float(request.form.get("longitude"))
        dt_str = f"{date} {time_str}"

        try:
            native = Subject(dt_str, latitude, longitude, timezone_offset=0)
            chart = Natal(native)

            chart_url, planet_table = build_chart(chart)

        except Exception as e:
            return f"<h3>Error generating chart: {e}</h3>"

    return render_template("index.html", chart_url=chart_url, planet_table=planet_table)


def build_chart(chart):
    aspect_color = "gold"
    aspects = {
        "Conjunction": (0, 8),
        "Opposition": (180, 8),
        "Trine": (120, 7),
        "Square": (90, 6),
        "Sextile": (60, 6)
    }

    fig, ax = plt.subplots(figsize=(12,12), subplot_kw={'projection':'polar'})
    ax.set_facecolor("#0d1b2a")
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi/2)

    # Zodiac ring (faint like reference)
    for i, sign in enumerate(ZODIAC):
        start_angle = i * np.pi/6
        ax.bar(start_angle, 1, width=np.pi/6, bottom=8.5,
               color='none', edgecolor='white', linewidth=1, alpha=0.25)
        angle = start_angle + np.pi/12
        ax.text(angle, 9.2, sign, fontsize=28, ha='center', va='center', color='white')

    # House lines (super faint)
    for cusp in chart.houses.values():
        angle = np.radians(90 - cusp.longitude.raw)
        ax.plot([angle, angle], [2, 9], color="white", linewidth=0.8, alpha=0.15)

    planet_positions = {}
    planet_table = []

    for obj in chart.objects.values():
        if obj.name not in PLANET_ORDER:
            continue

        lon = obj.longitude.raw
        planet_positions[obj.name] = lon
        theta = np.radians(90 - lon)

        deg = int(lon % 30)
        minutes = int((lon % 1) * 60)
        sign = ZODIAC[int(lon // 30)]
        symbol = PLANET_SYMBOLS.get(obj.name, obj.name)
        position = f"{deg}°{minutes:02d}′ {sign}"
        planet_table.append((symbol, position, obj.name))

        # Plot planets just outside zodiac band
        ax.scatter(theta, 9.5, color="gold", s=180, zorder=5)
        ax.text(theta, 10.0, symbol, fontsize=24,
                ha="center", va="center", color="gold")

    # Aspect lines
    planet_names = list(planet_positions.keys())
    for i, p1 in enumerate(planet_names):
        for p2 in planet_names[i+1:]:
            lon1 = planet_positions[p1]
            lon2 = planet_positions[p2]
            diff = abs(lon1 - lon2)
            diff = min(diff, 360 - diff)
            for asp, (angle_deg, orb) in aspects.items():
                if abs(diff - angle_deg) <= orb:
                    theta1 = np.radians(90 - lon1)
                    theta2 = np.radians(90 - lon2)
                    style = "--" if (p1 in ["Ascendant","Descendant","Midheaven","IC"] or
                                     p2 in ["Ascendant","Descendant","Midheaven","IC"]) else "-"
                    ax.plot([theta1, theta2], [7.5, 7.5],
                            color=aspect_color, linewidth=1.2, alpha=0.9,
                            zorder=1, linestyle=style)

    # Inner aspect circle (faint)
    ax.add_artist(plt.Circle((0,0), 7.5, transform=ax.transData._b,
                             color="white", fill=False, lw=1, alpha=0.25))

    # Outer dotted circle (bolder, containing planets)
    ax.add_artist(plt.Circle((0,0), 9.0, transform=ax.transData._b,
                             color="white", fill=False, lw=1.5,
                             alpha=0.8, linestyle="--"))

    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.set_ylim(0, 10.5)
    plt.title("Natal Chart", color='white', fontsize=16)

    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"natal_chart_{timestamp}.png"
    filepath = os.path.join("static", filename)
    plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="#0d1b2a")
    plt.close(fig)

    planet_table_sorted = sorted(
        planet_table,
        key=lambda x: PLANET_ORDER.index(x[2]) if x[2] in PLANET_ORDER else 999
    )

    return url_for("static", filename=filename), planet_table_sorted


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)