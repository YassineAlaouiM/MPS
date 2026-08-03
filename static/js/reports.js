// Reports Page JavaScript
(function() {
    const chartInstances = {};
    const API_ENDPOINTS = {
        rest: '/api/reports/rest_history',
        shift: '/api/reports/shift_summary',
        machine: '/api/reports/machine_history',
        operator: '/api/reports/operator_complete'
    };

    const EXPORT_ENDPOINTS = {
        rest: '/export_report/rest_history',
        shift: '/export_report/shift_summary',
        machine: '/export_report/machine_history',
        operator: '/export_report/operator_complete'
    };

    const PERIOD_LABELS = {
        matin: 'Matin',
        apres_midi: 'Après-midi',
        nuit: 'Nuit'
    };

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.report-filters').forEach(setupFilterPanel);

        const exportBtn = document.getElementById('reportExportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                const panel = getActiveReportPanel();
                if (!panel) return;
                exportReportPdf(panel.dataset.report, panel);
            });
        }
    });

    function getActiveReportPanel() {
        const activePane = document.querySelector('#reportTabContent .tab-pane.active');
        return activePane ? activePane.querySelector('.report-filters') : null;
    }

    function setupFilterPanel(panel) {
        const reportType = panel.dataset.report;
        const resultsEl = document.getElementById(`${reportType}-results`);

        panel.querySelector('.btn-filter').addEventListener('click', function() {
            loadReport(reportType, panel, resultsEl);
        });

        panel.querySelector('.btn-reset').addEventListener('click', function() {
            resetFilters(panel, resultsEl, reportType);
        });

        const searchInput = panel.querySelector('.report-search');
        if (searchInput) {
            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') loadReport(reportType, panel, resultsEl);
            });
        }
    }

    function resetFilters(panel, resultsEl, reportType) {
        const defaults = window.REPORT_DEFAULTS || {};
        panel.querySelector('.report-start').value = defaults.startDate || '';
        panel.querySelector('.report-end').value = defaults.endDate || '';
        const opSelect = panel.querySelector('.report-operator');
        if (opSelect) opSelect.value = '';
        const machineSelect = panel.querySelector('.report-machine');
        if (machineSelect) machineSelect.value = '';
        const searchInput = panel.querySelector('.report-search');
        if (searchInput) searchInput.value = '';
        destroyCharts(reportType);
        resultsEl.innerHTML = getEmptyState(reportType);
    }

    function getEmptyState(reportType) {
        const icons = { rest: 'fa-bed', shift: 'fa-clock', machine: 'fa-cogs', operator: 'fa-user' };
        const messages = {
            rest: 'Sélectionnez un opérateur et une période pour afficher l\'historique des repos.',
            shift: 'Sélectionnez un opérateur et une période pour afficher le cumul des shifts.',
            machine: 'Sélectionnez une machine et une période pour afficher l\'historique.',
            operator: 'Sélectionnez un opérateur et une période pour afficher l\'historique complet.'
        };
        return `<div class="empty-report-state">
            <i class="fas ${icons[reportType]} fa-2x mb-3"></i>
            <p>${messages[reportType]}</p>
        </div>`;
    }

    function loadReport(reportType, panel, resultsEl) {
        const params = buildReportParams(reportType, panel);
        if (!params) return;

        resultsEl.innerHTML = '<div class="report-loading"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-2">Chargement...</p></div>';
        destroyCharts(reportType);

        fetch(`${API_ENDPOINTS[reportType]}?${params}`)
            .then(res => res.json())
            .then(response => {
                if (!response.success) {
                    resultsEl.innerHTML = `<div class="report-error">${response.message || 'Erreur lors du chargement.'}</div>`;
                    return;
                }
                renderReport(reportType, response.data, resultsEl);
            })
            .catch(() => {
                resultsEl.innerHTML = '<div class="report-error">Erreur de connexion au serveur.</div>';
            });
    }

    function buildReportParams(reportType, panel) {
        const startDate = panel.querySelector('.report-start').value;
        const endDate = panel.querySelector('.report-end').value;
        const params = new URLSearchParams({ start_date: startDate, end_date: endDate });

        if (reportType === 'machine') {
            const machineId = panel.querySelector('.report-machine').value;
            if (!machineId) { alert('Veuillez sélectionner une machine.'); return null; }
            params.set('machine_id', machineId);
            const search = panel.querySelector('.report-search').value.trim();
            if (search) params.set('search', search);
        } else {
            const operatorId = panel.querySelector('.report-operator').value;
            if (!operatorId) { alert('Veuillez sélectionner un opérateur.'); return null; }
            params.set('operator_id', operatorId);
        }
        return params;
    }

    function exportReportPdf(reportType, panel) {
        const params = buildReportParams(reportType, panel);
        if (!params) return;
        window.open(`${EXPORT_ENDPOINTS[reportType]}?${params}`, '_blank');
    }

    function renderReport(reportType, data, container) {
        switch (reportType) {
            case 'rest': renderRestHistory(data, container); break;
            case 'shift': renderShiftSummary(data, container); break;
            case 'machine': renderMachineHistory(data, container); break;
            case 'operator': renderOperatorComplete(data, container); break;
        }
    }

    function renderStatsCards(stats) {
        return `<div class="stats-grid">${stats.map(s =>
            `<div class="stat-card">
                <div class="stat-value">${s.value}</div>
                <div class="stat-label">${s.label}</div>
            </div>`
        ).join('')}</div>`;
    }

    function renderTable(title, headers, rows) {
        if (!rows.length) {
            return `<div class="report-table-section"><h5>${title}</h5><p class="text-muted">Aucune donnée pour cette période.</p></div>`;
        }
        return `<div class="report-table-section">
            <h5>${title}</h5>
            <table class="table table-striped report-table">
                <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
                <tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    function periodBadge(period) {
        const label = PERIOD_LABELS[period] || period;
        return `<span class="period-badge period-${period}">${label}</span>`;
    }

    function renderRestHistory(data, container) {
        const stats = data.statistics;
        container.innerHTML = renderStatsCards([
            { value: stats.total_rest_days, label: 'Total jours de repos' },
            { value: stats.monthly_average, label: 'Moyenne mensuelle' },
            { value: stats.months_in_period, label: 'Mois dans la période' }
        ]);

        if (data.chart.labels.length) {
            container.innerHTML += `<div class="chart-container"><canvas id="rest-chart"></canvas></div>`;
        }

        const rows = data.rest_days.map(r => [formatDate(r.date)]);
        container.innerHTML += renderTable('Détail des jours de repos', ['Date'], rows);

        if (data.chart.labels.length) {
            createBarChart('rest', 'rest-chart', 'Jours de repos par mois', data.chart.labels, data.chart.values, '#1461d4');
        }
    }

    function renderShiftSummary(data, container) {
        const stats = data.statistics;
        container.innerHTML = renderStatsCards([
            { value: stats.total_shifts, label: 'Total shifts' },
            { value: stats.total_hours + ' h', label: 'Heures travaillées' },
            { value: stats.matin, label: 'Matin' },
            { value: stats.apres_midi, label: 'Après-midi' },
            { value: stats.nuit, label: 'Nuit' }
        ]);

        container.innerHTML += `<div class="chart-container"><canvas id="shift-chart"></canvas></div>`;

        const rows = data.assignments.map(a => [
            formatDate(a.date),
            a.machine_name,
            a.shift_name,
            periodBadge(a.shift_period),
            `${a.start_time} - ${a.end_time}`,
            a.hours + ' h'
        ]);
        container.innerHTML += renderTable('Détail des shifts', ['Date', 'Machine', 'Shift', 'Période', 'Horaire', 'Heures'], rows);

        createDoughnutChart('shift', 'shift-chart', 'Répartition des shifts', data.chart.labels, data.chart.values);
    }

    function renderMachineHistory(data, container) {
        const stats = data.statistics;
        const machineName = data.machine ? data.machine.name : '';
        container.innerHTML = `<h5 class="mb-3">Machine : <strong>${machineName}</strong></h5>`;
        container.innerHTML += renderStatsCards([
            { value: stats.total_assignments, label: 'Total affectations' },
            { value: stats.unique_operators, label: 'Opérateurs distincts' },
            { value: stats.total_hours + ' h', label: 'Heures totales' }
        ]);

        if (data.chart.labels.length) {
            container.innerHTML += `<div class="chart-container"><canvas id="machine-chart"></canvas></div>`;
        }

        const opRows = data.operator_statistics.map(s => [
            s.operator_name, s.assignments, s.days_worked, s.total_hours + ' h'
        ]);
        container.innerHTML += renderTable('Statistiques par opérateur', ['Opérateur', 'Affectations', 'Jours travaillés', 'Heures'], opRows);

        const rows = data.assignments.map(a => [
            formatDate(a.date),
            a.operator_name,
            a.shift_name,
            `${a.start_time} - ${a.end_time}`,
            a.hours + ' h'
        ]);
        container.innerHTML += renderTable('Détail des affectations', ['Date', 'Opérateur', 'Shift', 'Horaire', 'Heures'], rows);

        if (data.chart.labels.length) {
            createBarChart('machine', 'machine-chart', 'Affectations par opérateur', data.chart.labels, data.chart.values, '#17a2b8');
        }
    }

    function renderOperatorComplete(data, container) {
        const stats = data.statistics;
        const opName = data.operator ? data.operator.name : '';
        container.innerHTML = `<h5 class="mb-3">Opérateur : <strong>${opName}</strong></h5>`;
        container.innerHTML += renderStatsCards([
            { value: stats.total_shifts, label: 'Total shifts' },
            { value: stats.total_hours + ' h', label: 'Heures travaillées' },
            { value: stats.total_rest_days, label: 'Jours de repos' },
            { value: stats.monthly_average_rest, label: 'Moy. repos/mois' },
            { value: stats.total_absences, label: 'Absences' },
            { value: stats.unique_machines, label: 'Machines' }
        ]);

        container.innerHTML += `<div class="charts-row">
            <div class="chart-container"><canvas id="operator-shift-chart"></canvas></div>
            <div class="chart-container"><canvas id="operator-machine-chart"></canvas></div>
        </div>`;

        const machineRows = data.machine_statistics.map(m => [
            m.machine_name, m.assignments, m.total_hours + ' h'
        ]);
        container.innerHTML += renderTable('Statistiques par machine', ['Machine', 'Affectations', 'Heures'], machineRows);

        const shiftRows = data.shifts.map(s => [
            formatDate(s.date),
            s.machine_name,
            s.shift_name,
            periodBadge(s.shift_period),
            s.hours + ' h'
        ]);
        container.innerHTML += renderTable('Shifts', ['Date', 'Machine', 'Shift', 'Période', 'Heures'], shiftRows);

        const restRows = data.rest_days.map(r => [formatDate(r.date)]);
        container.innerHTML += renderTable('Jours de repos', ['Date'], restRows);

        const absenceRows = data.absences.map(a => [
            formatDate(a.start_date),
            formatDate(a.end_date),
            a.reason || '-'
        ]);
        container.innerHTML += renderTable('Absences', ['Début', 'Fin', 'Motif'], absenceRows);

        createDoughnutChart('operator-shift', 'operator-shift-chart', 'Répartition des shifts', data.charts.shifts.labels, data.charts.shifts.values);
        if (data.charts.machines.labels.length) {
            createBarChart('operator-machine', 'operator-machine-chart', 'Affectations par machine', data.charts.machines.labels, data.charts.machines.values, '#1461d4');
        }
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const parts = dateStr.split('-');
        if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
        return dateStr;
    }

    function destroyCharts(prefix) {
        Object.keys(chartInstances).forEach(key => {
            if (key.startsWith(prefix)) {
                chartInstances[key].destroy();
                delete chartInstances[key];
            }
        });
    }

    const CHART_COLORS = ['#1461d4', '#ffc107', '#28a745', '#17a2b8', '#dc3545', '#6f42c1', '#fd7e14', '#20c997'];

    function createBarChart(key, canvasId, title, labels, values, color) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        chartInstances[key] = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: title,
                    data: values,
                    backgroundColor: color || '#1461d4',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, title: { display: true, text: title } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    function createDoughnutChart(key, canvasId, title, labels, values) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        chartInstances[key] = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: CHART_COLORS.slice(0, labels.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' }, title: { display: true, text: title } }
            }
        });
    }
})();
