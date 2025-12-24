(function(){
  'use strict';

  // Toggle for dev frontend mocks. Default: false (use real API)
  const DEV_FRONTEND = false;

  const btn = document.getElementById('btn-refresh');
  if (!btn) { console.warn('dashboard.js: #btn-refresh not found'); return; }

  let chartA = null, chartR = null;
  let lastParams = '';

  function getFilters(){
    return {
      desde: document.getElementById('desde').value || '',
      hasta: document.getElementById('hasta').value || '',
      medico: document.getElementById('medico').value || '',
      institucion: document.getElementById('institucion').value || ''
    };
  }

  function updateExportLinks(params){
    const csv = document.getElementById('export-csv');
    const xlsx = document.getElementById('export-xlsx');
    const pdf = document.getElementById('export-pdf');
    if(csv) csv.href = `/panel/api/dashboard/export_csv/?${params}`;
    if(xlsx) xlsx.href = `/panel/api/dashboard/export_xlsx/?${params}`;
    if(pdf) pdf.href = `/panel/api/dashboard/export_pdf/?${params}`;
  }

  function destroyCharts(){
    if (window.chartA && typeof window.chartA.destroy === 'function') { window.chartA.destroy(); window.chartA = null; }
    if (window.chartR && typeof window.chartR.destroy === 'function') { window.chartR.destroy(); window.chartR = null; }
  }

  function hideCharts(){
    const a = document.getElementById('chartAtenciones');
    const r = document.getElementById('chartRecaudo');
    if(a) a.style.display = 'none';
    if(r) r.style.display = 'none';
  }

  function showCharts(){
    const a = document.getElementById('chartAtenciones');
    const r = document.getElementById('chartRecaudo');
    if(a) a.style.display = '';
    if(r) r.style.display = '';
  }

  function showEmptyMessage(){
    const m = document.getElementById('pan-no-data');
    if(m) m.style.display = 'block';
  }

  function hideEmptyMessage(){
    const m = document.getElementById('pan-no-data');
    if(m) m.style.display = 'none';
  }

  function renderCharts(apiData){
    destroyCharts();

    // Normalized shape expected: { chart1: {...}, chart2: {...} }
    const c1 = apiData.chart1 || apiData.atenciones || null;
    const c2 = apiData.chart2 || apiData.recaudo || null;

    // If data shapes are not present or empty -> show empty message
    const hasC1 = c1 && Array.isArray(c1.datasets) && c1.datasets.length>0 && Array.isArray(c1.labels) && c1.labels.length>0;
    const hasC2 = c2 && Array.isArray(c2.datasets) && c2.datasets.length>0 && Array.isArray(c2.labels) && c2.labels.length>0;

    if (!hasC1 && !hasC2) { hideCharts(); showEmptyMessage(); return; }

    hideEmptyMessage();
    showCharts();

    if (hasC1) {
      const ctxA = document.getElementById('chartAtenciones').getContext('2d');
      window.chartA = new Chart(ctxA, { type: 'bar', data: c1, options: { responsive: true } });
    }

    if (hasC2) {
      const ctxR = document.getElementById('chartRecaudo').getContext('2d');
      window.chartR = new Chart(ctxR, { type: 'bar', data: c2, options: { responsive: true } });
    }
  }

  function renderTable(apiData){
    if(!apiData.rows) return;
    const tbody = document.querySelector('#detail-table tbody');
    if(!tbody) return;
    tbody.innerHTML = '';
    apiData.rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.periodo||''}</td><td>${r.atenciones||''}</td><td>${r.total_consulta||''}</td><td>${r.total_medicina||''}</td>`;
      tbody.appendChild(tr);
    });
  }

  async function fetchDashboardData(){
    const f = getFilters();
    const params = new URLSearchParams(f).toString();
    lastParams = params;
    updateExportLinks(params);

    if (DEV_FRONTEND){
      // Mock UI data for frontend development
      renderCharts({
        chart1: { labels: ['Ene','Feb','Mar'], datasets: [{ label: 'Consultas', data: [10,20,15], backgroundColor: 'rgba(0,122,204,0.7)' }] },
        chart2: { labels: ['A','B','C'], datasets: [{ label: 'Pacientes', data: [5,8,12], backgroundColor: 'rgba(16,150,50,0.7)' }] },
        rows: [ { periodo: '2025-12-01', atenciones: 10, total_consulta: 100, total_medicina: 20 } ]
      });
      renderTable({ rows: [] });
      return;
    }

    try {
      const res = await fetch(`/panel/api/dashboard/?${params}`);
      if (!res.ok) throw new Error('HTTP '+res.status);
      const json = await res.json();

      // Accept several shapes: { chart1, chart2, rows } or { labels, datasets... }
      if (!json || ((!(json.chart1 || json.atenciones) || (json.chart1 && (!json.chart1.datasets||json.chart1.datasets.length===0))) && (!(json.chart2 || json.recaudo) || (json.chart2 && (!json.chart2.datasets||json.chart2.datasets.length===0))))) {
        destroyCharts(); hideCharts(); showEmptyMessage(); renderTable({ rows: [] });
        return;
      }

      // Normalize shape if backend uses different keys
      const normalized = {};
      if (json.chart1 || json.atenciones) normalized.chart1 = json.chart1 || json.atenciones;
      if (json.chart2 || json.recaudo) normalized.chart2 = json.chart2 || json.recaudo;
      normalized.rows = json.rows || json.detalle || [];

      renderCharts(normalized);
      renderTable(normalized);

    } catch (err){
      console.error('Error fetching dashboard data:', err);
      destroyCharts(); hideCharts(); showEmptyMessage(); renderTable({ rows: [] });
    }
  }

  // Initial UI state: hide charts, show friendly message
  hideCharts(); showEmptyMessage();

  btn.addEventListener('click', function(e){ e.preventDefault(); fetchDashboardData(); });

})();
