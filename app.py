from flask import Flask, render_template, request
import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const

app = Flask(__name__)

# Main 13 points
PLANETS = [
    const.SUN, const.MOON, const.MERCURY, const.VENUS,
    const.MARS, const.JUPITER, const.SATURN,
    const.URANUS, const.NEPTUNE, const.PLUTO,
    const.ASC, const.MC, const.DESC
]

ZODIAC_SIGNS = [
    ("Aries", "♈"), ("Taurus", "♉"), ("Gemini", "♊"),
    ("Cancer", "♋"), ("Leo", "♌"), ("Virgo", "♍"),
    ("Libra", "♎"), ("Scorpio", "♏"), ("Sagittarius", "♐"),
    ("Capricorn", "♑"), ("Aquarius", "♒"), ("Pisces", "♓")
]

def format_position(obj):
    """Format planetary position as degrees°minutes′ sign."""
    lon = obj.lon
    sign_index = int(lon // 30)
    deg = int(lon % 30)
    minute = int((lon % 1) * 60)
    sign = ZODIAC_SIGNS[sign_index][1]
    return f"{deg}°{minute:02d}′ {sign}"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]
        latitude = request.form["latitude"]
        longitude = request.form["longitude"]

        # Build chart
        dt = Datetime(date, time, "+00:00")
        pos = GeoPos(latitude, longitude)
        chart = Chart(dt, pos)

        # Collect planetary positions
        planet_positions = []
        for body in PLANETS:
            obj = chart.get(body)
            planet_positions.append((obj.symbol, format_position(obj)))

        # Create chart figure
        fig, ax = plt.subplots(figsize=(8, 8), facecolor="#0d1b2a")
        ax.set_facecolor("#0d1b2a")
        ax.set_aspect("equal")
        ax.axis("off")

        # Radii
        outer_r = 1.0
        planet_r = 1.15

        # Background rings
        for r in [0.2, 0.4, 0.6, 0.8]:
            ax.add_patch(plt.Circle((0, 0), r, fill=False, color="white", alpha=0.2, lw=1))
        ax.add_patch(plt.Circle((0, 0), outer_r, fill=False, color="white", alpha=0.4, lw=1))
        ax.add_patch(plt.Circle((0, 0), planet_r, fill=False, color="white", ls="--", lw=2))

        # Zodiac glyphs around circle
        for i, (_, glyph) in enumerate(ZODIAC_SIGNS):
            angle = np.deg2rad(i * 30)
            x = 1.35 * np.cos(angle)
            y = 1.35 * np.sin(angle)
            ax.text(x, y, glyph, ha="center", va="center", fontsize=20, color="white")

        # Plot planets
        positions = {}
        for body in PLANETS:
            obj = chart.get(body)
            lon = obj.lon
            angle = np.deg2rad(90 - lon)
            x = planet_r * np.cos(angle)
            y = planet_r * np.sin(angle)
            ax.plot(x, y, "o", color="gold", markersize=10)
            ax.text(1.45 * np.cos(angle), 1.45 * np.sin(angle),
                    obj.symbol, ha="center", va="center", fontsize=20, color="gold")
            positions[body] = (x, y)

        # Aspect lines
        for i, body1 in enumerate(PLANETS):
            for body2 in PLANETS[i + 1:]:
                x1, y1 = positions[body1]
                x2, y2 = positions[body2]
                if body1 in [const.ASC, const.MC, const.DESC] or body2 in [const.ASC, const.MC, const.DESC]:
                    ax.plot([x1, x2], [y1, y2], color="gold", lw=1, ls="--", alpha=0.8)
                else:
                    ax.plot([x1, x2], [y1, y2], color="gold", lw=1, alpha=0.7)

        # Save chart to memory
        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)

        chart_data = base64.b64encode(buf.read()).decode("utf-8")

        return render_template("index.html", chart_data=chart_data, positions=planet_positions)

    return render_template("index.html", chart_data=None, positions=None)

if __name__ == "__main__":
    app.run(debug=True)