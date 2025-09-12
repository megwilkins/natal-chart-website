from flask import Flask, render_template, request, url_for
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Render
import matplotlib.pyplot as plt
import numpy as np
import datetime
import os
from immanuel.charts import Natal, Subject

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None

    if request.method == "POST":
        date = request.form["date"]
        time_str = request.form["time"]
        latitude = float(request.form["latitude"])
        longitude = float(request.form["longitude"])
        timezone = float(request.form["timezone"])

        # Build chart
        native = Subject(f"{date} {time_str}", latitude, longitude, timezone_offset=timezone)
        chart = Natal(native)

        # Planets to plot
        all_planets = [
            "Sun", "Moon", "Mercury", "Venus", "Mars",
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
        ]
        planets_in_chart = [p for p in all_planets if p in chart.objects]

        # Zodiac glyphs
        zodiac = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

        # Aspects
        aspects = {
            "Conjunction": (0, 8, "gold"),
            "Opposition": (180, 8, "royalblue"),
            "Trine": (120, 7, "limegreen"),
            "Square": (90, 6, "red"),
            "Sextile": (60, 6, "turquoise")
        }

        fig, ax = plt.subplots(figsize=(12,12), subplot_kw={'projection':'polar'})
        ax.set_facecolor("#0d1b2a")
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2)

        # Outer zodiac ring
        for i, sign in enumerate(zodiac):
            start_angle = i * np.pi/6
            ax.bar(start_angle, 1, width=np.pi/6, bottom=8.5,
                   color='none', edgecolor='white', linewidth=1.5)
            angle = start_angle + np.pi/12
            ax.text(angle, 9.8, sign, fontsize=22, ha='center', va='center', color='white')

        # Houses
        for house_num, cusp in enumerate(chart.houses.values(), start=1):
            angle = np.radians(90 - cusp.longitude.raw)
            ax.plot([angle, angle], [2, 9], color="white", linewidth=1)

        # Planet positions
        planet_positions = {}
        for name in planets_in_chart:
            p = chart.objects[name]
            lon = p.longitude.raw
            planet_positions[name] = lon
            ax.scatter(np.radians(lon), 7.8, color='gold', s=120, zorder=5)
            ax.text(np.radians(lon), 8.2, p.symbol, fontsize=18,
                    ha='center', va='center', color='gold')

        # Aspect lines
        for i, p1 in enumerate(planets_in_chart):
            for p2 in planets_in_chart[i+1:]:
                lon1 = planet_positions[p1]
                lon2 = planet_positions[p2]
                diff = abs(lon1 - lon2)
                diff = min(diff, 360 - diff)
                for asp, (angle, orb, color) in aspects.items():
                    if abs(diff - angle) <= orb:
                        theta1 = np.radians(90 - lon1)
                        theta2 = np.radians(90 - lon2)
                        ax.plot([theta1, theta2], [7.5, 7.5],
                                color=color, linewidth=1.2, alpha=0.8, zorder=1)

        # Inner aspect circle
        circle = plt.Circle((0,0), 7.5, transform=ax.transData._b,
                            color="white", fill=False, lw=1)
        ax.add_artist(circle)

        # Cleanup
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.set_ylim(0, 10)
        plt.title("Natal Chart", color='white', fontsize=16)

        # Save with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"natal_chart_{timestamp}.png"
        filepath = os.path.join("static", filename)
        plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="#0d1b2a")
        plt.close(fig)

        chart_url = url_for("static", filename=filename)

    return render_template("index.html", chart_url=chart_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
