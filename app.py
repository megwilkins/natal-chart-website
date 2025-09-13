from flask import Flask, render_template, request
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
from immanuel import charts
from immanuel.const import PLANETS, ANGLES, ASPECTS

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    chart_url = None
    positions = None

    if request.method == "POST":
        try:
            date = request.form["date"]
            time = request.form["time"]
            latitude = float(request.form["latitude"])
            longitude = float(request.form["longitude"])

            # Build natal chart
            chart = charts.Natal(date=date, time=time, latitude=latitude, longitude=longitude)

            # Positions for planets + angles
            objects = PLANETS + ANGLES
            positions = {obj: chart[obj].position for obj in objects}

            # Matplotlib setup
            fig, ax = plt.subplots(figsize=(8, 8), facecolor="#0b1c2c")
            ax.set_facecolor("#0b1c2c")
            ax.axis("off")

            outer_radius = 1.0
            glyph_radius = 1.2

            # Faint concentric circles
            for r in [0.2, 0.4, 0.6, 0.8]:
                circle = plt.Circle((0, 0), r, color="white", linestyle="-", alpha=0.2, fill=False)
                ax.add_artist(circle)

            # Bold dashed outer boundary
            circle = plt.Circle((0, 0), outer_radius, color="white", linestyle="--", linewidth=2, fill=False)
            ax.add_artist(circle)

            # Zodiac glyphs
            zodiac = ["♈", "♉", "♊", "♋", "♌", "♍",
                      "♎", "♏", "♐", "♑", "♒", "♓"]
            for i, sign in enumerate(zodiac):
                angle = np.deg2rad(i * 30)
                x = 1.35 * np.cos(angle)
                y = 1.35 * np.sin(angle)
                ax.text(x, y, sign, fontsize=18, ha="center", va="center", color="white")

            # Plot planets + angles
            for obj, pos in positions.items():
                angle = np.deg2rad(pos)
                x = glyph_radius * np.cos(angle)
                y = glyph_radius * np.sin(angle)

                ax.plot(x, y, "o", color="gold", markersize=14)
                ax.text(x, y, chart[obj].symbol, fontsize=18, ha="center", va="center", color="gold")

            # Aspects
            for asp in chart.aspects():
                if asp.type not in ASPECTS:
                    continue
                a1 = np.deg2rad(chart[asp.obj1].position)
                a2 = np.deg2rad(chart[asp.obj2].position)
                x1, y1 = outer_radius * np.cos(a1), outer_radius * np.sin(a1)
                x2, y2 = outer_radius * np.cos(a2), outer_radius * np.sin(a2)

                # Dotted if involves Asc/MC/Desc
                if asp.obj1 in ["Ascendant", "Midheaven", "Descendant"] or asp.obj2 in ["Ascendant", "Midheaven", "Descendant"]:
                    ax.plot([x1, x2], [y1, y2], linestyle="dotted", color="gold", linewidth=1)
                else:
                    ax.plot([x1, x2], [y1, y2], color="gold", linewidth=1)

            # Save chart as base64
            buf = io.BytesIO()
            plt.savefig(buf, format="png", facecolor=fig.get_facecolor(), dpi=150, bbox_inches="tight")
            buf.seek(0)
            chart_url = base64.b64encode(buf.getvalue()).decode()
            plt.close(fig)

        except Exception as e:
            return f"Error generating chart: {e}"

    return render_template("index.html", chart_url=chart_url, positions=positions)