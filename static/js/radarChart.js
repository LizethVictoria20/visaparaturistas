// radarChart.js
export function createRadarChart(ctx, data) {
  let myChart =  new Chart(ctx, {
    type: "radar",
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 10,
          angleLines: {
            color: "rgba(0, 0, 0, 0.2)",
            lineWidth: 2,
          },
          grid: {
            color: "rgba(0, 0, 0, 0.1)",
            lineWidth: 2,
          },
          pointLabels: {
            color: "#34495e",
            font: {
              size: 14,
              weight: "bold",
            },
          },
          ticks: {
            backdropColor: "rgba(255, 255, 255, 0.2)",
            color: "#34495e",
            beginAtZero: true,
            stepSize: 2,
            showLabelBackdrop: false,
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          titleColor: "#ecf0f1",
          bodyColor: "#ecf0f1",
          borderColor: "rgba(41, 128, 185, 1)",
          borderWidth: 1,
        },
      },
    },
  });
}

export function createProbabilityBar(percentage) {
  const barContainer = document.createElement("div");
  barContainer.classList.add("probability-bar");

  const barInner = document.createElement("div");
  barInner.classList.add("probability-bar-inner");
  barInner.style.width = `${percentage}%`;

  barContainer.appendChild(barInner);
  return barContainer;
}

export function appendProbabilityBar(percentage, parentElementId) {
  const parentElement = document.getElementById(parentElementId);
  const bar = createProbabilityBar(percentage);
  parentElement.appendChild(bar);
}

// radarChar.js
// radarChart.js

// Definir la función
export function updateStatusAndCircle(score, elementId, statusId) {
  if (isNaN(score) || score === null) {
      document.getElementById(elementId).innerHTML = `<span>N/A</span>`;
      document.getElementById(statusId).innerText = 'N/A';
      document.getElementById(statusId).className = 'analysis-status';
      document.getElementById(elementId).className = 'circle';
      document.getElementById(elementId).style.background = 'conic-gradient(lightgray 0% 360deg)';
      return;
  }

  var status = 'POSITIVO';
  var className = 'positivo';
  if (score < 3) {
      status = 'NEGATIVO';
      className = 'negativo';
  } else if (score < 6.5) {
      status = 'NEUTRO';
      className = 'neutro';
  }

  var degree = (score / 10) * 360;
  var background = `conic-gradient(green 0% ${degree}deg, lightgray ${degree}deg 360deg)`;
  if (className === 'neutro') {
      background = `conic-gradient(#ff9800 0% ${degree}deg, lightgray ${degree}deg 360deg)`;
  } else if (className === 'negativo') {
      background = `conic-gradient(#f44336 0% ${degree}deg, lightgray ${degree}deg 360deg)`;
  }

  document.getElementById(elementId).innerHTML = `<span>${score}</span>`;
  document.getElementById(statusId).innerText = status;
  document.getElementById(statusId).className = `analysis-status ${className}`;
  document.getElementById(elementId).className = `circle ${className}`;
  document.getElementById(elementId).style.background = background;
}
