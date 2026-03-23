const analyticsNode = document.getElementById("analytics-data");

if (analyticsNode && window.Chart) {
    const data = JSON.parse(analyticsNode.textContent || "{}");
    const monthlyCanvas = document.getElementById("monthly-out-chart");
    const topCanvas = document.getElementById("top-issued-chart");

    if (monthlyCanvas) {
        new Chart(monthlyCanvas, {
            type: "line",
            data: {
                labels: data.monthlyOutTotals.map((item) => item.label),
                datasets: [
                    {
                        label: "Units issued",
                        data: data.monthlyOutTotals.map((item) => item.total),
                        borderColor: "#15806a",
                        backgroundColor: "rgba(21, 128, 106, 0.18)",
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: "#f8faf7",
                        pointBorderColor: "#15806a",
                        pointRadius: 3,
                        pointHoverRadius: 5,
                    },
                ],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: "rgba(34, 50, 43, 0.08)" } },
                    y: { beginAtZero: true, grid: { color: "rgba(34, 50, 43, 0.08)" } },
                },
            },
        });
    }

    if (topCanvas) {
        new Chart(topCanvas, {
            type: "bar",
            data: {
                labels: data.topIssued.map((item) => item.label),
                datasets: [
                    {
                        label: "Issued",
                        data: data.topIssued.map((item) => item.total),
                        backgroundColor: ["#15806a", "#2c9677", "#58ab89", "#8bc3a2", "#d09a43", "#c86a40"],
                        borderRadius: 10,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: "rgba(34, 50, 43, 0.08)" } },
                    y: { grid: { display: false } },
                },
            },
        });
    }
}
