// radarChart.js
export function createRadarChart(ctx, data) {
  new Chart(ctx, {
      type: 'radar',
      data: data,
      options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
              r: {
                  min: 0,
                  max: 10,
                  angleLines: {
                      color: 'rgba(0, 0, 0, 0.2)',
                      lineWidth: 2
                  },
                  grid: {
                      color: 'rgba(0, 0, 0, 0.1)',
                      lineWidth: 2
                  },
                  pointLabels: {
                      color: '#34495e',
                      font: {
                          size: 14,
                          weight: 'bold'
                      }
                  },
                  ticks: {
                      backdropColor: 'rgba(255, 255, 255, 0.2)',
                      color: '#34495e',
                      beginAtZero: true,
                      stepSize: 2,
                      showLabelBackdrop: false
                  }
              }
          },
          plugins: {
              legend: {
                  display: false
              },
              tooltip: {
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  titleColor: '#ecf0f1',
                  bodyColor: '#ecf0f1',
                  borderColor: 'rgba(41, 128, 185, 1)',
                  borderWidth: 1
              }
          }
      }
  });
}

export function createProbabilityBar(percentage) {
  const barContainer = document.createElement('div');
  barContainer.classList.add('probability-bar');

  const barInner = document.createElement('div');
  barInner.classList.add('probability-bar-inner');
  barInner.style.width = `${percentage}%`;

  barContainer.appendChild(barInner);
  return barContainer;
}

export function appendProbabilityBar(percentage, parentElementId) {
  const parentElement = document.getElementById(parentElementId);
  const bar = createProbabilityBar(percentage);
  parentElement.appendChild(bar);
}
