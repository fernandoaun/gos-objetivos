/**
 * Mini-gráficos Chart.js para el mosaico del DashBoard.
 */
const charts = new Map();

const PALETTE = {
  gold: "#e8b84a",
  goldSoft: "rgba(232, 184, 74, 0.35)",
  cyan: "#5ec8d8",
  cyanSoft: "rgba(94, 200, 216, 0.3)",
  white: "#f2f5fa",
  muted: "#8b97a8",
  ok: "#5fd68a",
  bad: "#e85a6a",
  grid: "rgba(255,255,255,0.06)",
};

function destroyAll() {
  charts.forEach((c) => c.destroy());
  charts.clear();
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 700 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#141a24",
        titleColor: PALETTE.gold,
        bodyColor: PALETTE.white,
        borderColor: PALETTE.gold,
        borderWidth: 1,
        displayColors: false,
      },
    },
    ...extra,
  };
}

export function renderBar(canvasId, labels, values, color = PALETTE.gold) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === "undefined") return;
  if (charts.has(canvasId)) charts.get(canvasId).destroy();

  const chart = new Chart(el, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: color,
          borderRadius: 2,
          borderSkipped: false,
          maxBarThickness: 18,
        },
      ],
    },
    options: baseOptions({
      scales: {
        x: {
          ticks: { color: PALETTE.muted, font: { size: 9 }, maxRotation: 0 },
          grid: { display: false },
          border: { display: false },
        },
        y: {
          ticks: { color: PALETTE.muted, font: { size: 9 }, maxTicksLimit: 4 },
          grid: { color: PALETTE.grid },
          border: { display: false },
          beginAtZero: true,
        },
      },
    }),
  });
  charts.set(canvasId, chart);
}

export function renderLine(canvasId, labels, values, color = PALETTE.cyan) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === "undefined") return;
  if (charts.has(canvasId)) charts.get(canvasId).destroy();

  const chart = new Chart(el, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: color,
          backgroundColor: PALETTE.cyanSoft,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: baseOptions({
      scales: {
        x: {
          ticks: { color: PALETTE.muted, font: { size: 9 }, maxRotation: 0 },
          grid: { display: false },
          border: { display: false },
        },
        y: {
          ticks: { color: PALETTE.muted, font: { size: 9 }, maxTicksLimit: 4 },
          grid: { color: PALETTE.grid },
          border: { display: false },
          beginAtZero: true,
        },
      },
    }),
  });
  charts.set(canvasId, chart);
}

export function renderDoughnut(canvasId, labels, values, colors) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === "undefined") return;
  if (charts.has(canvasId)) charts.get(canvasId).destroy();

  const chart = new Chart(el, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors || [PALETTE.gold, PALETTE.cyan, PALETTE.ok, PALETTE.bad, PALETTE.muted],
          borderWidth: 0,
          hoverOffset: 4,
        },
      ],
    },
    options: baseOptions({
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#141a24",
          titleColor: PALETTE.gold,
          bodyColor: PALETTE.white,
          borderColor: PALETTE.gold,
          borderWidth: 1,
        },
      },
    }),
  });
  charts.set(canvasId, chart);
}

export function renderHorizontal(canvasId, labels, values, color = PALETTE.gold) {
  const el = document.getElementById(canvasId);
  if (!el || typeof Chart === "undefined") return;
  if (charts.has(canvasId)) charts.get(canvasId).destroy();

  const chart = new Chart(el, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: color,
          borderRadius: 2,
          borderSkipped: false,
          maxBarThickness: 12,
        },
      ],
    },
    options: baseOptions({
      indexAxis: "y",
      scales: {
        x: {
          ticks: { color: PALETTE.muted, font: { size: 9 }, maxTicksLimit: 4 },
          grid: { color: PALETTE.grid },
          border: { display: false },
          beginAtZero: true,
        },
        y: {
          ticks: { color: PALETTE.muted, font: { size: 9 } },
          grid: { display: false },
          border: { display: false },
        },
      },
    }),
  });
  charts.set(canvasId, chart);
}

export function clearCharts() {
  destroyAll();
}

export { PALETTE };
