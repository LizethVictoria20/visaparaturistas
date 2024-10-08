document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM completamente cargado y analizado.");

    // Verificar si existen secciones en el formulario
    const sections = document.querySelectorAll('.form-section');
    if (sections.length === 0) {
        console.error("No se encontraron elementos con la clase 'form-section'. Asegúrate de que el HTML contiene estos elementos.");
    }

    const nextBtn = document.getElementById('next-btn');
    const prevBtn = document.getElementById('prev-btn');
    const submitBtn = document.getElementById('submit-btn');
    let currentSectionIndex = 0;

    function updateSectionVisibility() {
        sections.forEach((section, index) => {
            section.style.display = index === currentSectionIndex ? 'block' : 'none';
        });
        if (prevBtn) prevBtn.style.display = currentSectionIndex > 0 ? 'inline-block' : 'none';
        if (nextBtn) nextBtn.style.display = currentSectionIndex < sections.length - 1 ? 'inline-block' : 'none';
        if (submitBtn) submitBtn.style.display = currentSectionIndex === sections.length - 1 ? 'inline-block' : 'none';
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (currentSectionIndex < sections.length - 1) {
                currentSectionIndex++;
                updateSectionVisibility();
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (currentSectionIndex > 0) {
                currentSectionIndex--;
                updateSectionVisibility();
            }
        });
    }

    updateSectionVisibility();

    // Manejo de la tabla y exportación
    var searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', filterTable);
    } else {
        console.error("El elemento con id 'search-input' no existe.");
    }

    var resultsTable = document.getElementById('results-table');
    if (resultsTable) {
        // Añade otros event listeners relacionados con resultsTable aquí
    } else {
        console.error("El elemento con id 'results-table' no existe.");
    }

    var selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.addEventListener('change', function () {
            var checkboxes = document.querySelectorAll('#results-table tbody tr:not([style*="display: none"]) .row-checkbox');
            checkboxes.forEach(function (checkbox) {
                checkbox.checked = selectAll.checked;
            });
            updateExportButtonsState();
        });
    } else {
        console.error("El elemento con id 'select-all' no existe.");
    }

    // Función para filtrar la tabla
    function filterTable() {
        var input = document.getElementById('search-input');
        if (!input) return;
        var filter = input.value.toLowerCase();
        var table = document.getElementById('results-table');
        if (!table) return;
        var trs = table.getElementsByTagName('tr');

        for (var i = 1; i < trs.length; i++) {
            var tds = trs[i].getElementsByTagName('td');
            var found = false;

            for (var j = 0; j < tds.length; j++) {
                if (tds[j].innerHTML.toLowerCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }

            trs[i].style.display = found ? '' : 'none';
        }

        updateExportButtonsState();
    }

    setTimeout(function() {
      var flashElements = document.querySelectorAll('.alert');
      flashElements.forEach(function(element) {
        var alert = new bootstrap.Alert(element);
        alert.close();
      });
    }, 1000);
    // Función para actualizar el estado de los botones de exportación
    function updateExportButtonsState() {
        var checkboxes = document.querySelectorAll('#results-table tbody tr:not([style*="display: none"]) .row-checkbox:checked');
        var exportButtons = document.querySelectorAll('.export-button');

        exportButtons.forEach(function(button) {
            if (checkboxes.length > 0) {
                button.classList.remove('disabled');
                button.removeAttribute('disabled');
            } else {
                button.classList.add('disabled');
                button.setAttribute('disabled', true);
            }
        });
    }

    // Actualizar estado de los botones al cambiar la selección
    document.querySelectorAll('#results-table .row-checkbox').forEach(function (checkbox) {
        checkbox.addEventListener('change', updateExportButtonsState);
    });

    function getSelectedRows() {
        var rows = [];
        var checkboxes = document.querySelectorAll('#results-table tbody tr:not([style*="display: none"]) .row-checkbox:checked');
        checkboxes.forEach(function (checkbox) {
            rows.push(checkbox.closest('tr'));
        });
        return rows;
    }

    // Exportar a CSV
    window.exportTableToCSV = function (filename) {
        var csv = [];
        var rows = getSelectedRows();
        if (rows.length === 0) {
            rows = document.querySelectorAll("#results-table tr");
        }
        rows.forEach(function (row) {
            var cols = row.querySelectorAll("td, th");
            var rowData = [];
            cols.forEach(function (col) {
                rowData.push(col.innerText);
            });
            csv.push(rowData.join(","));
        });
        downloadCSV(csv.join("\n"), filename);
    };

    function downloadCSV(filename) {
        var downloadLink = document.createElement("a");
        downloadLink.download = filename;
        downloadLink.href = '/export-all-csv';
        downloadLink.style.display = "none";
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }

    // Exportar a XLS
    window.exportTableToXLS = function (filename) {
        var table = document.createElement('table');
        var headerRow = document.querySelector("#results-table thead").cloneNode(true);
        table.appendChild(headerRow);
        rows.forEach(function (row) {
            table.appendChild(row.cloneNode(true));
        });
        var downloadLink = document.createElement("a");
        downloadLink.href = '/export-all-xls';
        downloadLink.download = filename;
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    };

    // Ordenar la tabla
    window.sortTable = function (columnIndex) {
        var table = document.getElementById("results-table");
        if (!table) return;
        var tbody = table.tBodies[0];
        var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));

        var isAscending = !table.querySelectorAll("th")[columnIndex].classList.contains("asc");
        table.querySelectorAll("th").forEach(function(th) {
            th.classList.remove("asc", "desc");
        });

        rows.sort(function (a, b) {
            var cellA = a.children[columnIndex].textContent.trim();
            var cellB = b.children[columnIndex].textContent.trim();

            if (!isNaN(cellA) && !isNaN(cellB)) {
                cellA = parseFloat(cellA);
                cellB = parseFloat(cellB);
            }

            if (isAscending) {
                return cellA > cellB ? 1 : -1;
            } else {
                return cellA < cellB ? 1 : -1;
            }
        });

        rows.forEach(function (row) {
            tbody.appendChild(row);
        });

        if (isAscending) {
            table.querySelectorAll("th")[columnIndex].classList.add("asc");
        } else {
            table.querySelectorAll("th")[columnIndex].classList.add("desc");
        }

        updateSortIndicators();
    };

    function updateSortIndicators() {
        var headers = document.querySelectorAll("th.sortable");
        headers.forEach(function (header) {
            var sortIndicator = header.querySelector(".sort-indicator");
            if (header.classList.contains("asc")) {
                sortIndicator.style.borderTop = "5px solid white";
                sortIndicator.style.borderBottom = "none";
            } else if (header.classList.contains("desc")) {
                sortIndicator.style.borderTop = "none";
                sortIndicator.style.borderBottom = "5px solid white";
            } else {
                sortIndicator.style.borderTop = "5px solid white";
                sortIndicator.style.borderBottom = "none";
            }
        });
    }

    // Paginación
    var rowsPerPage = 10;
    var currentPage = 1;
    var maxPagesVisible = 6;
    var rows = Array.from(document.getElementById('results-table').getElementsByTagName('tr')).slice(1);
    var totalPages = Math.ceil(rows.length / rowsPerPage);

    function renderTable() {
        rows.forEach((row, index) => {
            row.style.display = 'none';
            if (index >= (currentPage - 1) * rowsPerPage && index < currentPage * rowsPerPage) {
                row.style.display = '';
            }
        });
    }

    function renderPagination() {
        const paginationContainer = document.getElementById('pagination-container');
        paginationContainer.innerHTML = '';

        const startPage = Math.max(currentPage - Math.floor(maxPagesVisible / 2), 1);
        const endPage = Math.min(startPage + maxPagesVisible - 1, totalPages);

        for (let i = startPage; i <= endPage; i++) {
            const pageButton = document.createElement('span');
            pageButton.classList.add('page-number');
            if (i === currentPage) {
                pageButton.classList.add('active');
            }
            pageButton.innerText = i;
            pageButton.onclick = function () {
                currentPage = i;
                renderTable();
                renderPagination();
            };
            paginationContainer.appendChild(pageButton);
        }

        if (startPage > 1) {
            const firstPageButton = document.createElement('span');
            firstPageButton.classList.add('page-number');
            firstPageButton.innerText = 1;
            firstPageButton.onclick = function () {
                currentPage = 1;
                renderTable();
                renderPagination();
            };
            paginationContainer.insertBefore(firstPageButton, paginationContainer.firstChild);
        }

        if (endPage < totalPages) {
            const lastPageButton = document.createElement('span');
            lastPageButton.classList.add('page-number');
            lastPageButton.innerText = totalPages;
            lastPageButton.onclick = function () {
                currentPage = totalPages;
                renderTable();
                renderPagination();
            };
            paginationContainer.appendChild(lastPageButton);
        }
    }

    var recordsPerPage = document.getElementById('recordsPerPage');
    if (recordsPerPage) {
        recordsPerPage.addEventListener('change', function () {
            rowsPerPage = parseInt(this.value);
            currentPage = 1;
            totalPages = Math.ceil(rows.length / rowsPerPage);
            renderTable();
            renderPagination();
        });
    } else {
        console.error("El elemento con id 'recordsPerPage' no existe.");
    }

    renderTable();
    renderPagination();
    updateExportButtonsState();
});

document.addEventListener('DOMContentLoaded', function () {
    // Variables y elementos del DOM
    const sections = document.querySelectorAll('.form-section');
    const nextBtn = document.getElementById('next-btn');
    const prevBtn = document.getElementById('prev-btn');
    const submitBtn = document.getElementById('submit-btn');
    const progressBar = document.getElementById('progress-bar');
    let currentSectionIndex = 0;

    function updateSectionVisibility() {
        sections.forEach((section, index) => {
            section.style.display = index === currentSectionIndex ? 'block' : 'none';
        });
        if (prevBtn) prevBtn.style.display = currentSectionIndex > 0 ? 'inline-block' : 'none';
        if (nextBtn) nextBtn.style.display = currentSectionIndex < sections.length - 1 ? 'inline-block' : 'none';
        if (submitBtn) submitBtn.style.display = currentSectionIndex === sections.length - 1 ? 'inline-block' : 'none';
        updateProgressBar();
    }

    function updateProgressBar() {
        const progress = (currentSectionIndex / (sections.length - 1)) * 100;
        progressBar.style.width = progress + '%';
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (currentSectionIndex < sections.length - 1) {
                currentSectionIndex++;
                updateSectionVisibility();
            }
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (currentSectionIndex > 0) {
                currentSectionIndex--;
                updateSectionVisibility();
            }
        });
    }

    updateSectionVisibility();
});

