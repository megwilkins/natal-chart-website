import os
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, send_file, url_for
from immanuel.charts import Natal, Subject

app = Flask(__name__)

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None
    if request.method == "POST":
        # Collect input data
        date = request.form.get("date")
        time_str = request.form.get("time")
        latitude = float(request.form.get("latitude"))
        longitude = float(request.form.get("longitude"))

        # Merge into datetime string
        dt_str = f"{date} {time_str}"

        try:
            native = Subject(dt_str, latitude, longitude, timezone_offset=0)
            chart = Natal(native)

            # Build chart image
            chart_url = build_chart(chart)

        except Exception as e:
            return f"<h3>Error generating chart: {e}</h3>"

    return render_template("index.html", chart_url=chart_url)


def build_chart(chart):
    # Planets
    all_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                   "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    planets_in_chart = [p for p in all_planets if p in chart.objects]

    zodiac = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

    # Aspect definitions: color + tolerance ("orb")
    aspects = {
        "Conjunction": (0, 8, "gold"),
        "Opposition": (180, 8, "#3FA9F5"),   # light blue
        "Trine": (120, 7, "#00FF7F"),        # green
        "Square": (90, 6, "#FF4C4C"),        # red
        "Sextile": (60, 6, "#40E0D0")        # turquoise
    }

    # Create figure
    fig, ax = plt.subplots(figsize=(12,12), subplot_kw={'projection':'polar'})
    ax.set_facecolor("#0d1b2a")  # navy background
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi/2)

    # Outer zodiac ring
    for i, sign in enumerate(zodiac):
        start_angle = i * np.pi/6
        ax.bar(start_angle, 1, width=np.pi/6, bottom=8.5,
               color='none', edgecolor='white', linewidth=1.5)
        angle = start_angle + np.pi/12
        ax.text(angle, 9.8, sign, fontsize=22, ha='center', va='center', color='white')

    # House cusps
    for cusp in chart.houses.values():
        angle = np.radians(90 - cusp.longitude.raw)
        ax.plot([angle, angle], [2, 9], color="white", linewidth=1)

    # Planet positions
    planet_positions = {}
    for name in planets_in_chart:
        p = chart.objects[name]
        lon = p.longitude.raw
        planet_positions[name] = lon
        theta = np.radians(90 - lon)
        ax.scatter(theta, 7.8, color='gold', s=120, zorder=5)
        ax.text(theta, 8.2, p.symbol, fontsize=18,
                ha='center', va='center', color='gold')

    # Aspect lines
    for i, p1 in enumerate(planets_in_chart):
        for p2 in planets_in_chart[i+1:]:
            lon1 = planet_positions[p1]
            lon2 = planet_positions[p2]
            diff = abs(lon1 - lon2)
            diff = min(diff, 360 - diff)
            for asp, (angle_deg, orb, color) in aspects.items():
                if abs(diff - angle_deg) <= orb:
                    theta1 = np.radians(90 - lon1)
                    theta2 = np.radians(90 - lon2)
                    ax.plot([theta1, theta2], [7.5, 7.5],
                            color=color, linewidth=1.5, alpha=0.9, zorder=1)

    # Inner aspect circle
    circle = plt.Circle((0,0), 7.5, transform=ax.transData._b,
                        color="white", fill=False, lw=1.2)
    ax.add_artist(circle)

    # Style cleanup
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.set_ylim(0, 10)
    plt.title("Natal Chart", color='white', fontsize=16)

    # Save chart with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"natal_chart_{timestamp}.png"
    filepath = os.path.join("static", filename)
    plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="#0d1b2a")
    plt.close(fig)

    return url_for("static", filename=filename)


# ---------- MAIN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)