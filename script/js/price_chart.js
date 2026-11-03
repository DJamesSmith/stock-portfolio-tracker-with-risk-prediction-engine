document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("price-chart")
    const dataElement = document.getElementById("price-chart-data")

    if (!canvas || !dataElement || typeof Chart === "undefined") {
        return
    }

    const trend = JSON.parse(dataElement.textContent)
    const labels = trend.points.map(function (point) { return point.date })
    const closes = trend.points.map(function (point) { return parseFloat(point.close_price) })
    const buyPrice = parseFloat(trend.buy_price)
    const buyLine = labels.map(function () { return buyPrice })

    new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: trend.ticker + " close",
                    data: closes,
                    borderColor: "#0d6efd",
                    backgroundColor: "rgba(13, 110, 253, 0.08)",
                    fill: true,
                    pointRadius: 0,
                    borderWidth: 2,
                    tension: 0.2
                },
                {
                    label: "Buy price",
                    data: buyLine,
                    borderColor: "#6c757d",
                    borderDash: [6, 6],
                    pointRadius: 0,
                    borderWidth: 1.5,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            scales: {
                x: { ticks: { maxTicksLimit: 10 } },
                y: { title: { display: true, text: "Price ($)" } }
            }
        }
    })
})
