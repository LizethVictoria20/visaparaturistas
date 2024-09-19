// Clase ProbabilityBarInner que maneja la barra de probabilidad
export class ProbabilityBarInner {
  constructor(container, probability) {
    this.container = container;
    this.probability = probability;
    this.init();
  }

  // Inicializar la barra de probabilidad
  init() {
    const barInner = document.createElement('div');
    barInner.classList.add('progress-bar-inner');
    barInner.style.width = `${this.probability}%`;
    this.container.appendChild(barInner);
  }
}
