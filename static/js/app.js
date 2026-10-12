/**
 * app.js - Frontend Client Logic for DataBridge Web Dashboard
 * 
 * Handles:
 * - Tab switching
 * - Drag & drop CSV uploads + 1-Click sample imports
 * - Rendering dynamic audit KPI cards & rejection tables
 * - Live instant database search & filtering
 * - Demographic chart visualization
 * - Database reset workflows
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('csvFileInput');
  const btnRunSample = document.getElementById('btnRunSampleImport');
  const btnQuickSample = document.getElementById('btnQuickSample');
  const btnResetDb = document.getElementById('btnResetDb');
  const importLoading = document.getElementById('importLoading');
  const auditReportSection = document.getElementById('auditReportSection');

  // Customer table elements
  const searchInput = document.getElementById('customerSearchInput');
  const btnRefresh = document.getElementById('btnRefreshCustomers');
  const customersTableBody = document.getElementById('customersTableBody');
  const navCountBadge = document.getElementById('navCountBadge');

  // Audit Report metric elements
  const kpiTotalRead = document.getElementById('kpiTotalRead');
  const kpiValidCount = document.getElementById('kpiValidCount');
  const kpiInserted = document.getElementById('kpiInserted');
  const kpiDuplicates = document.getElementById('kpiDuplicates');
  const kpiRejected = document.getElementById('kpiRejected');
  const errMissing = document.getElementById('errMissing');
  const errEmail = document.getElementById('errEmail');
  const errAge = document.getElementById('errAge');
  const errDuplicate = document.getElementById('errDuplicate');
  const rejectedTableBody = document.getElementById('rejectedTableBody');
  const rejectedCountBadge = document.getElementById('rejectedCountBadge');

  // Analytics elements
  const statsTotal = document.getElementById('statsTotal');
  const statsCities = document.getElementById('statsCities');
  const statsAvgAge = document.getElementById('statsAvgAge');
  const statsAgeRange = document.getElementById('statsAgeRange');
  const cityChartContainer = document.getElementById('cityChartContainer');

  // Toast container
  const toastContainer = document.getElementById('toastContainer');

  /* ==========================================================================
     1. Toast Notifications
     ========================================================================== */
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
      <span>${escapeHtml(message)}</span>
    `;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /* ==========================================================================
     2. Navigation Tabs
     ========================================================================== */
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTabId = btn.getAttribute('data-tab');
      
      tabButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetContent = document.getElementById(targetTabId);
      if (targetContent) targetContent.classList.add('active');

      // Refresh data when navigating to specific tabs
      if (targetTabId === 'tab-database') {
        loadCustomers();
      } else if (targetTabId === 'tab-analytics') {
        loadStats();
      } else if (targetTabId === 'tab-architecture') {
        loadSchema();
      }
    });
  });

  /* ==========================================================================
     3. Drag and Drop File Ingestion
     ========================================================================== */
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        uploadCsvFile(files[0]);
      }
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        uploadCsvFile(fileInput.files[0]);
      }
    });
  }

  if (btnRunSample) {
    btnRunSample.addEventListener('click', () => runSampleImport());
  }

  if (btnQuickSample) {
    btnQuickSample.addEventListener('click', () => runSampleImport());
  }

  function showLoading(isLoading) {
    if (isLoading) {
      dropZone.classList.add('hidden');
      importLoading.classList.remove('hidden');
    } else {
      dropZone.classList.remove('hidden');
      importLoading.classList.add('hidden');
    }
  }

  /* ==========================================================================
     4. API Calls: Ingestion & Validation
     ========================================================================== */
  async function uploadCsvFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please select a valid .csv file.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showLoading(true);
    try {
      const response = await fetch('/api/import', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      handleImportResult(data);
    } catch (err) {
      showToast('Upload failed: ' + err.message, 'error');
    } finally {
      showLoading(false);
      fileInput.value = '';
    }
  }

  async function runSampleImport() {
    showLoading(true);
    try {
      const response = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_sample: true })
      });
      const data = await response.json();
      handleImportResult(data);
    } catch (err) {
      showToast('Sample import failed: ' + err.message, 'error');
    } finally {
      showLoading(false);
    }
  }

  function handleImportResult(data) {
    if (!data.success) {
      showToast(data.error || 'Import failed', 'error');
      return;
    }

    showToast('CSV import & cleaning finished successfully!', 'success');
    renderAuditReport(data.report);

    // Refresh database table and analytics in background
    loadCustomers();
    loadStats();
  }

  /* ==========================================================================
     5. Render Audit Report & Rejections
     ========================================================================== */
  function renderAuditReport(report) {
    if (!report) return;

    auditReportSection.classList.remove('hidden');
    auditReportSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // KPI values
    kpiTotalRead.textContent = report.total_rows_read || 0;
    kpiValidCount.textContent = report.valid_records || 0;
    kpiInserted.textContent = report.successfully_inserted || 0;
    kpiDuplicates.textContent = report.duplicates_skipped || 0;
    kpiRejected.textContent = report.invalid_records_rejected || 0;

    // Error breakdown
    const errors = report.error_counts || {};
    errMissing.textContent = errors.missing_value || 0;
    errEmail.textContent = errors.invalid_email || 0;
    errAge.textContent = errors.invalid_age || 0;
    errDuplicate.textContent = errors.duplicate_id || 0;

    // Rejected rows table
    const rejectedList = report.rejected_details || [];
    rejectedCountBadge.textContent = `${rejectedList.length} Rejections`;
    rejectedTableBody.innerHTML = '';

    if (rejectedList.length === 0) {
      rejectedTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-6 text-muted">
            No rows were rejected! All records met schema and validation criteria.
          </td>
        </tr>
      `;
      return;
    }

    rejectedList.forEach(item => {
      const tr = document.createElement('tr');
      const categoryBadge = getCategoryBadge(item.category);
      tr.innerHTML = `
        <td><span style="font-family: var(--font-mono); color: var(--text-muted);">${item.row_num}</span></td>
        <td><strong class="customer-id-cell">${escapeHtml(item.customer_id)}</strong></td>
        <td>${categoryBadge}</td>
        <td style="color: #cbd5e1;">${escapeHtml(item.reason)}</td>
      `;
      rejectedTableBody.appendChild(tr);
    });
  }

  function getCategoryBadge(category) {
    switch (category) {
      case 'missing_value':
        return '<span class="badge badge-amber">Missing Value</span>';
      case 'invalid_email':
        return '<span class="badge badge-rose">Invalid Email</span>';
      case 'invalid_age':
        return '<span class="badge badge-orange">Invalid Age</span>';
      case 'duplicate_id':
        return '<span class="badge badge-purple">Duplicate ID</span>';
      default:
        return `<span class="badge badge-danger">${escapeHtml(category || 'Error')}</span>`;
    }
  }

  /* ==========================================================================
     6. Customer Database Explorer & Search
     ========================================================================== */
  let searchDebounceTimeout = null;

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounceTimeout);
      searchDebounceTimeout = setTimeout(() => {
        loadCustomers(searchInput.value.trim());
      }, 250);
    });
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadCustomers(searchInput ? searchInput.value.trim() : '');
      showToast('Records refreshed', 'info');
    });
  }

  async function loadCustomers(query = '') {
    try {
      const url = query ? `/api/search?q=${encodeURIComponent(query)}` : '/api/customers';
      const response = await fetch(url);
      const data = await response.json();

      if (!data.success) {
        showToast(data.error, 'error');
        return;
      }

      renderCustomersTable(data.customers || []);
    } catch (err) {
      console.error('Failed to load customers:', err);
    }
  }

  function renderCustomersTable(customers) {
    if (!customersTableBody) return;
    customersTableBody.innerHTML = '';

    if (navCountBadge) {
      navCountBadge.textContent = customers.length;
    }

    if (customers.length === 0) {
      customersTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-8 text-muted">
            No customer records found matching your query.
          </td>
        </tr>
      `;
      return;
    }

    customers.forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="customer-id-cell">
          <span class="customer-id-pill" title="Click to copy Customer ID" data-id="${escapeHtml(c.customer_id)}">
            ${escapeHtml(c.customer_id)}
          </span>
        </td>
        <td><strong>${escapeHtml(c.name)}</strong></td>
        <td class="email-cell">${escapeHtml(c.email)}</td>
        <td>${escapeHtml(c.city)}</td>
        <td><span class="badge badge-accent">${c.age} yrs</span></td>
        <td style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--text-muted);">${escapeHtml(c.imported_at || '-')}</td>
      `;
      customersTableBody.appendChild(tr);
    });

    // Attach click-to-copy handlers to all Customer ID pills
    document.querySelectorAll('.customer-id-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        const idVal = pill.getAttribute('data-id');
        if (idVal && navigator.clipboard) {
          navigator.clipboard.writeText(idVal).then(() => {
            showToast(`Copied Customer ID: ${idVal}`, 'info');
          });
        }
      });
    });
  }

  /* ==========================================================================
     7. Analytics & Demographics
     ========================================================================== */
  async function loadStats() {
    try {
      const response = await fetch('/api/stats');
      const data = await response.json();
      if (!data.success) return;

      const stats = data.stats;
      statsTotal.textContent = stats.total_customers || 0;
      statsCities.textContent = stats.unique_cities || 0;
      statsAvgAge.textContent = (stats.average_age || 0.0) + ' yrs';
      statsAgeRange.textContent = `${stats.min_age || 0} - ${stats.max_age || 0} yrs`;

      renderCityChart(stats.city_breakdown || []);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }

  function renderCityChart(cities) {
    if (!cityChartContainer) return;
    cityChartContainer.innerHTML = '';

    if (cities.length === 0) {
      cityChartContainer.innerHTML = `
        <p class="text-muted text-center py-6">Import data to visualize geographic customer distribution.</p>
      `;
      return;
    }

    const maxCount = Math.max(...cities.map(c => c.count), 1);

    cities.forEach(item => {
      const barItem = document.createElement('div');
      barItem.className = 'chart-bar-item';
      
      const percent = Math.max((item.count / maxCount) * 100, 8);

      barItem.innerHTML = `
        <div class="chart-bar-label">${escapeHtml(item.city)}</div>
        <div class="chart-bar-track">
          <div class="chart-bar-fill" style="width: ${percent}%;">
            <span class="chart-bar-count">${item.count}</span>
          </div>
        </div>
      `;
      cityChartContainer.appendChild(barItem);
    });
  }

  /* ==========================================================================
     8. Reset Database
     ========================================================================== */
  if (btnResetDb) {
    btnResetDb.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to reset the database? All customer records will be cleared for re-testing.')) {
        return;
      }

      try {
        const response = await fetch('/api/reset', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
          showToast('Database reset successfully! Table is now empty.', 'success');
          loadCustomers();
          loadStats();
          if (auditReportSection) auditReportSection.classList.add('hidden');
        } else {
          showToast(data.error || 'Reset failed', 'error');
        }
      } catch (err) {
        showToast('Reset failed: ' + err.message, 'error');
      }
    });
  }

  /* ==========================================================================
     9. Interactive SQL Query Console
     ========================================================================== */
  const sqlQueryInput = document.getElementById('sqlQueryInput');
  const btnRunQuery = document.getElementById('btnRunQuery');
  const sqlResultThead = document.getElementById('sqlResultThead');
  const sqlResultTbody = document.getElementById('sqlResultTbody');
  const queryTimerBadge = document.getElementById('queryTimerBadge');
  const queryCountBadge = document.getElementById('queryCountBadge');
  const presetChips = document.querySelectorAll('.preset-chip');

  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      presetChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const query = chip.getAttribute('data-query');
      if (query && sqlQueryInput) {
        sqlQueryInput.value = query;
        runCustomQuery(query);
      }
    });
  });

  if (btnRunQuery) {
    btnRunQuery.addEventListener('click', () => {
      if (sqlQueryInput) {
        runCustomQuery(sqlQueryInput.value.trim());
      }
    });
  }

  async function runCustomQuery(sql) {
    if (!sql) {
      showToast('Please enter an SQL query to execute.', 'error');
      return;
    }

    if (queryTimerBadge) queryTimerBadge.textContent = 'Running...';

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: sql })
      });
      const data = await response.json();

      if (!data.success) {
        showToast(data.error || 'Query failed', 'error');
        if (queryTimerBadge) queryTimerBadge.textContent = 'Error';
        if (queryCountBadge) queryCountBadge.textContent = '0 Rows';
        if (sqlResultThead) sqlResultThead.innerHTML = '';
        if (sqlResultTbody) {
          sqlResultTbody.innerHTML = `
            <tr>
              <td class="text-center py-6" style="color: var(--color-danger);">
                ✕ ${escapeHtml(data.error)}
              </td>
            </tr>
          `;
        }
        return;
      }

      // Success
      if (queryTimerBadge) queryTimerBadge.textContent = `${data.execution_time_ms} ms`;
      if (queryCountBadge) queryCountBadge.textContent = `${data.row_count} Rows`;

      renderSqlResults(data.columns || [], data.rows || []);
      showToast(`Query executed in ${data.execution_time_ms} ms (${data.row_count} rows)`, 'success');
    } catch (err) {
      showToast('Query error: ' + err.message, 'error');
      if (queryTimerBadge) queryTimerBadge.textContent = 'Failed';
    }
  }

  function renderSqlResults(columns, rows) {
    if (!sqlResultThead || !sqlResultTbody) return;

    if (columns.length === 0) {
      sqlResultThead.innerHTML = '';
      sqlResultTbody.innerHTML = `
        <tr>
          <td class="text-center py-6 text-muted">Query executed successfully, no columns returned.</td>
        </tr>
      `;
      return;
    }

    // Render table headers
    let theadHtml = '<tr>';
    columns.forEach(col => {
      theadHtml += `<th>${escapeHtml(col)}</th>`;
    });
    theadHtml += '</tr>';
    sqlResultThead.innerHTML = theadHtml;

    // Render table rows
    if (rows.length === 0) {
      sqlResultTbody.innerHTML = `
        <tr>
          <td colspan="${columns.length}" class="text-center py-6 text-muted">
            0 rows returned by this query.
          </td>
        </tr>
      `;
      return;
    }

    let tbodyHtml = '';
    rows.forEach(row => {
      tbodyHtml += '<tr>';
      columns.forEach(col => {
        const val = row[col];
        if (col === 'customer_id') {
          tbodyHtml += `<td class="customer-id-cell"><span class="customer-id-pill" title="Click to copy" onclick="navigator.clipboard.writeText('${escapeHtml(val)}'); window.showToast('Copied ID: ${escapeHtml(val)}', 'info');">${escapeHtml(val)}</span></td>`;
        } else if (col === 'email') {
          tbodyHtml += `<td class="email-cell">${escapeHtml(val)}</td>`;
        } else {
          tbodyHtml += `<td>${val !== null && val !== undefined ? escapeHtml(val) : '<span class="text-muted">NULL</span>'}</td>`;
        }
      });
      tbodyHtml += '</tr>';
    });
    sqlResultTbody.innerHTML = tbodyHtml;
  }

  /* ==========================================================================
     10. Database Schema & Health Diagnostics
     ========================================================================== */
  const schemaTableBody = document.getElementById('schemaTableBody');
  const healthFileSize = document.getElementById('healthFileSize');
  const healthIntegrity = document.getElementById('healthIntegrity');
  const healthRowCount = document.getElementById('healthRowCount');
  const btnRefreshSchema = document.getElementById('btnRefreshSchema');

  if (btnRefreshSchema) {
    btnRefreshSchema.addEventListener('click', () => {
      loadSchema();
      showToast('Schema diagnostics updated', 'info');
    });
  }

  async function loadSchema() {
    try {
      const response = await fetch('/api/schema');
      const data = await response.json();
      if (!data.success) return;

      // Update Health metrics
      if (healthFileSize && data.health) {
        healthFileSize.textContent = `${data.health.file_size_kb} KB`;
      }
      if (healthIntegrity && data.health) {
        healthIntegrity.textContent = data.health.integrity_status.toUpperCase();
      }
      if (healthRowCount && data.health) {
        healthRowCount.textContent = data.health.total_records;
      }

      // Render Schema table
      if (schemaTableBody && data.schema) {
        schemaTableBody.innerHTML = '';
        data.schema.forEach(col => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong class="font-mono text-primary">${escapeHtml(col.name)}</strong></td>
            <td><span class="badge badge-accent">${escapeHtml(col.type)}</span></td>
            <td>${col.pk ? '<span class="badge badge-success">PRIMARY KEY</span>' : '<span class="text-muted">-</span>'}</td>
            <td>${col.notnull ? '<span class="badge badge-amber">NOT NULL</span>' : '<span class="text-muted">NULLABLE</span>'}</td>
            <td><span class="font-mono text-muted">${escapeHtml(col.dflt_value || 'None')}</span></td>
          `;
          schemaTableBody.appendChild(tr);
        });
      }
    } catch (err) {
      console.error('Failed to load schema:', err);
    }
  }

  // Initial load
  loadCustomers();
  loadStats();
});
