const analyticsNode = document.getElementById("analytics-data");

if (analyticsNode && window.Chart) {
    // Chart data is precomputed by the Flask view so this script only handles
    // presentation, not business calculations.
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
                        borderWidth: 2,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: "#f8faf7",
                        pointBorderColor: "#15806a",
                        pointRadius: 2.5,
                        pointHoverRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        grid: { color: "rgba(34, 50, 43, 0.08)" },
                        ticks: { maxRotation: 0, autoSkipPadding: 14, color: "#5d645d", font: { size: 11 } },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(34, 50, 43, 0.08)" },
                        ticks: { precision: 0, color: "#5d645d", font: { size: 11 } },
                    },
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
                        maxBarThickness: 18,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: "rgba(34, 50, 43, 0.08)" },
                        ticks: { precision: 0, color: "#5d645d", font: { size: 11 } },
                    },
                    y: { grid: { display: false }, ticks: { color: "#26332d", font: { size: 11 } } },
                },
            },
        });
    }
}
