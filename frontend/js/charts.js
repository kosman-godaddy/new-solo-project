let chartInstance = null;

// Colors used for each slice of the donut chart
const PALETTE = [
  '#7c87f5', '#f87171', '#4ade80', '#fbbf24', '#a78bfa',
  '#38bdf8', '#fb923c', '#f472b6', '#34d399', '#94a3b8'
];

function renderChart(summary) {
  const ctx = document.getElementById('spending-chart').getContext('2d');

  // Only show categories where money was spent (negative amounts)
  const spending = summary.filter(r => r.total < 0);

  // Destroy the old chart before drawing a new one
  if (chartInstance) chartInstance.destroy();

  if (!spending.length) return;

  // Calculate the total spent so we can show percentages
  const total = spending.reduce((s, r) => s + Math.abs(r.total), 0);

  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      // Add the percentage to each category label in the legend
      labels: spending.map(r => {
        const pct = ((Math.abs(r.total) / total) * 100).toFixed(1);
        return `${r.category}  ${pct}%`;
      }),
      datasets: [{
        data: spending.map(r => Math.abs(r.total)),
        backgroundColor: PALETTE,
        borderColor: '#1a1d27',
        borderWidth: 3,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 12 }, padding: 16 }
        },
        // Show dollar amount and percentage when hovering over a slice
        tooltip: {
          callbacks: {
            label: ctx => {
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return ` $${ctx.raw.toFixed(2)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}
