let chartInstance = null;

const PALETTE = [
  '#7c87f5', '#f87171', '#4ade80', '#fbbf24', '#a78bfa',
  '#38bdf8', '#fb923c', '#f472b6', '#34d399', '#94a3b8'
];

function renderChart(summary) {
  const ctx = document.getElementById('spending-chart').getContext('2d');
  const spending = summary.filter(r => r.total < 0);

  if (chartInstance) chartInstance.destroy();

  if (!spending.length) return;

  const total = spending.reduce((s, r) => s + Math.abs(r.total), 0);

  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
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
