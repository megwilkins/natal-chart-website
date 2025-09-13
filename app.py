from flask import Flask, render_template, request, send_file
import matplotlib.pyplot as plt
import numpy as np
import io
import datetime
from immanuel.charts import Natal, Subject

app = Flask(__name__)

# Zodiac symbols
ZODIAC = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

# Planet symbols (top 13 only)
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
    "Ascendant": "Asc",
    "Descendant": "Dsc",
    "MC": "MC",
    "IC": "IC"
}

PLANET_ORDER = list(PLANET_SYMBOLS.keys())

# Aspects (all gold now)
ASPECTS = {
    "Conjunction": (0, 8),
    "Opposition": (180, 8),
    "Trine": (120, 7),
    "Square": (90, 6),
    "Sextile": (60, 6)
}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            date_str = request.form["date"]
            time_str = request.form.get("time", "12:00")
            latitude = float(request.form["latitude"])
            longitude = float(request.form["longitude"])

            # Parse datetime
            dt = f"{date_str} {time_str}"
            native = Subject(dt, latitude, longitude, timezone_offset=0)
            chart = Natal(native)

            # Filter to top 13
            objects = {k: v for k, v in chart.objects.items() if k in PLANET_ORDER}

            # Start figure
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection':'polar'})
            ax.set_facecolor("#0d1b2a")
            ax.set_theta_direction(-1)
            ax.set_theta_offset(np.pi/2)

            # Zodiac ring
            for i, sign in enumerate(ZODIAC):
                start_angle = i * np.pi/6
                angle = start_angle + np.pi/12
                ax.text(angle, 10.5, sign, fontsize=26,
                        ha="center", va="center", color="white")

            # Houses (faint)
            for cusp in chart.houses.values():
                angle = np.radians(90 - cusp.longitude.raw)
                ax.plot([angle, angle], [2, 9.2],
                        color="white", linewidth=1, alpha=0.25)

            planet_positions = {}
            planet_table = []

            # Plot planets
            for obj in objects.values():
                lon = obj.longitude.raw
                planet_positions[obj.name] = lon
                theta = np.radians(90 - lon)

                deg = int(lon % 30)
                minutes = int((lon % 1) * 60)
                sign = ZODIAC[int(lon // 30)]
                symbol = PLANET_SYMBOLS.get(obj.name, obj.name)
                position = f"{deg}°{minutes:02d}′ {sign}"
                planet_table.append((symbol, position, obj.name))

                # dot inside
                ax.scatter(theta, 8.8, color="gold", s=160, zorder=5)

                # glyph outside
                ax.text(theta, 10.0, symbol, fontsize=34,
                        ha="center", va="center", color="gold")

            # Aspects (gold lines)
            for i, p1 in enumerate(objects.keys()):
                for p2 in list(objects.keys())[i+1:]:
                    lon1 = planet_positions[p1]
                    lon2 = planet_positions[p2]
                    diff = abs(lon1 - lon2)
                    diff = min(diff, 360 - diff)
                    for angle, orb in ASPECTS.values():
                        if abs(diff - angle) <= orb:
                            theta1 = np.radians(90 - lon1)
                            theta2 = np.radians(90 - lon2)
                            ax.plot([theta1, theta2], [8.8, 8.8],
                                    color="gold", linewidth=1.2, alpha=0.9, zorder=1)

            # Inner faint aspect circle
            ax.add_artist(plt.Circle((0,0), 7.5, transform=ax.transData._b,
                                     color="white", fill=False, lw=1, alpha=0.25))

            # Outer bold dashed circle
            ax.add_artist(plt.Circle((0,0), 9.2, transform=ax.transData._b,
                                     color="white", fill=False, lw=2,
                                     linestyle="--", alpha=1.0))

            # Style
            ax.set_yticklabels([])
            ax.set_xticklabels([])
            ax.set_ylim(0, 11)
            plt.title("Natal Chart", color="white", fontsize=18)

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, dpi=300, bbox_inches="tight", facecolor="#0d1b2a")
            buf.seek(0)
            plt.close(fig)

            return send_file(buf, mimetype="image/png")

        except Exception as e:
            return f"Error generating chart: {e}"

    return render_template("index.html")