from flask import Flask, render_template, request, send_file
import io
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from immanuel import charts

app = Flask(__name__)

# --- Utility: Draw natal chart ---
def draw_chart(chart_data):
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    ax.set_facecolor("#0d1b2a")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_theta_offset(np.pi / 2)
    ax.set_ylim(0, 1)

    # Zodiac wheel (12 segments)
    for i in range(12):
        ax.bar(
            (i * np.pi / 6), 1, width=np.pi / 6, bottom=0,
            color=("#1b263b" if i % 2 == 0 else "#24324a"),
            edgecolor="gold", linewidth=1, alpha=0.8
        )

    # Planets
    planets = chart_data['planets']
    for name, pdata in planets.items():
        lon = np.radians(pdata['lon'])
        ax.scatter(lon, 0.8, s=120, c="gold", edgecolor="black", zorder=5)
        ax.text(lon, 0.85, name[0], color="white", ha="center", va="center", fontsize=10)

    # Houses
    houses = chart_data['houses']
    for i, cusp in enumerate(houses, start=1):
        lon = np.radians(cusp)
        ax.plot([lon, lon], [0, 1], color="white", linewidth=0.8, alpha=0.6)
        ax.text(lon, 0.05, f"H{i}", color="white", ha="center", va="center", fontsize=8)

    # Aspect lines
    aspects = chart_data['aspects']
    for aspect in aspects:
        p1 = np.radians(planets[aspect['p1']]['lon'])
        p2 = np.radians(planets[aspect['p2']]['lon'])
        ax.plot([p1, p2], [0.8, 0.8], color="red", alpha=0.5, linewidth=1)

    # Outer border
    circ = Circle((0, 0), 1, transform=ax.transData._b, fill=False, edgecolor="gold", linewidth=2)
    ax.add_artist(circ)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#0d1b2a")
    buf.seek(0)
    plt.close(fig)
    return buf


# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    chart_data = None
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]
        place = request.form["place"]

        # Generate chart with immanuel
        natal = charts.Natal(
            name=name,
            date=date,
            time=time,
            place=place,
        )

        chart_data = {
            "planets": {p.name: {"lon": p.lon} for p in natal.planets},
            "houses": [h.cusp for h in natal.houses],
            "aspects": [{"p1": a.p1, "p2": a.p2, "type": a.type} for a in natal.aspects],
            "positions": [(p.name, round(p.lon, 2), p.sign) for p in natal.planets],
        }

    return render_template("index.html", chart=chart_data)


@app.route("/chart.png")
def chart_png():
    # Example fallback data (use latest computed chart in real use)
    sample_data = {
        "planets": {"Sun": {"lon": 0}, "Moon": {"lon": 90}},
        "houses": [i * 30 for i in range(12)],
        "aspects": [],
    }
    buf = draw_chart(sample_data)
    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)