/* Art Openings Sydney - Frontend */

(function () {
  'use strict';

  let DATA = [];
  let calYear, calMonth;

  // ---- Init ----
  async function init() {
    try {
      const resp = await fetch('data.json?v=' + Date.now());
      const json = await resp.json();
      DATA = json.exhibitions || [];
    } catch (e) {
      console.error('Failed to load data:', e);
      DATA = [];
    }

    populateSuburbs();
    render();
    setupListeners();

    const now = new Date();
    calYear = now.getFullYear();
    calMonth = now.getMonth();
    renderCalendar();
  }

  // ---- Populate suburb filter ----
  function populateSuburbs() {
    const suburbs = new Set();
    DATA.forEach(ex => { if (ex.suburb) suburbs.add(ex.suburb); });
    const sel = document.getElementById('filter-suburb');
    Array.from(suburbs).sort().forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    });
  }

  // ---- Filtering ----
  function getFiltered() {
    const q = document.getElementById('search').value.toLowerCase().trim();
    const openingToday = document.getElementById('filter-opening-today').checked;
    const showClosed = document.getElementById('filter-closed').checked;
    const suburb = document.getElementById('filter-suburb').value;

    const todayStr = new Date().toISOString().slice(0, 10);

    return DATA.filter(ex => {
      // Status filter
      if (showClosed) {
        if (ex.status !== 'closed') return false;
      } else {
        if (ex.status === 'closed') return false;
      }

      // Opening today filter
      if (openingToday) {
        if (ex.opening_date !== todayStr && ex.start_date !== todayStr) return false;
      }

      // Suburb filter
      if (suburb && ex.suburb !== suburb) return false;

      // Search
      if (q) {
        const hay = [ex.title, ex.artist, ex.venue, ex.suburb, ex.description]
          .join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }

      return true;
    });
  }

  // ---- Render list ----
  function render() {
    const list = document.getElementById('exhibition-list');
    const noResults = document.getElementById('no-results');
    const filtered = getFiltered();

    list.innerHTML = '';

    if (filtered.length === 0) {
      noResults.hidden = false;
      return;
    }
    noResults.hidden = true;

    filtered.forEach(ex => {
      list.appendChild(createCard(ex));
    });
  }

  function createCard(ex) {
    const card = document.createElement('div');
    card.className = 'ex-card' + (ex.status === 'closed' ? ' status-closed' : '');

    // Badge
    const badge = getBadge(ex);

    // Title
    const titleLink = ex.website
      ? `<a href="${esc(ex.website)}" target="_blank" rel="noopener">${esc(ex.title)}</a>`
      : esc(ex.title);

    // Meta line
    let meta = '';
    if (ex.venue) meta += `<span class="venue">${esc(ex.venue)}</span>`;
    if (ex.suburb) meta += (meta ? ', ' : '') + esc(ex.suburb);
    if (ex.artist) meta += (meta ? ' · ' : '') + esc(ex.artist);

    // Dates
    let dates = '';
    if (ex.start_date || ex.end_date) {
      let range = formatDate(ex.start_date);
      if (ex.end_date) range += ' \u2013 ' + formatDate(ex.end_date);
      dates += `<span class="date-exhibition">${range}</span>`;
    }
    if (ex.opening_date) {
      let opStr = formatDate(ex.opening_date);
      if (ex.opening_time) opStr += ' ' + esc(ex.opening_time);
      dates += `<span class="date-opening">Opening: ${opStr}</span>`;
    }

    // Actions
    let actions = '';
    if (ex.website) {
      actions += `<a href="${esc(ex.website)}" target="_blank" rel="noopener">Website</a>`;
    }
    if (ex.instagram) {
      const handle = ex.instagram.replace('@', '');
      actions += `<a href="https://instagram.com/${esc(handle)}" target="_blank" rel="noopener">${esc(ex.instagram)}</a>`;
    }
    if (ex.opening_date || ex.start_date) {
      actions += `<button onclick="downloadICS('${esc(ex.id)}')" title="Add to calendar">ICS</button>`;
      const gcUrl = buildGoogleCalUrl(ex);
      actions += `<a href="${gcUrl}" target="_blank" rel="noopener" title="Add to Google Calendar">GCal</a>`;
    }

    card.innerHTML = `
      ${badge}
      <h3>${titleLink}</h3>
      ${meta ? `<div class="ex-meta">${meta}</div>` : ''}
      ${dates ? `<div class="ex-dates">${dates}</div>` : ''}
      ${ex.description ? `<p class="ex-desc">${esc(ex.description)}</p>` : ''}
      ${actions ? `<div class="ex-actions">${actions}</div>` : ''}
    `;

    return card;
  }

  function getBadge(ex) {
    if (ex.status === 'closed') {
      return '<span class="badge badge-closed">Closed</span>';
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (ex.opening_date) {
      const opDate = new Date(ex.opening_date + 'T00:00:00');
      const diff = Math.ceil((opDate - today) / 86400000);
      if (diff === 0) return '<span class="badge badge-opening">Opening tonight</span>';
      if (diff > 0 && diff <= 3) return `<span class="badge badge-opening">Opening in ${diff}d</span>`;
    }

    if (ex.end_date) {
      const endDate = new Date(ex.end_date + 'T00:00:00');
      const diff = Math.ceil((endDate - today) / 86400000);
      if (diff >= 0 && diff <= 3) {
        if (diff === 0) return '<span class="badge badge-closing">Last day</span>';
        return `<span class="badge badge-closing">Closing in ${diff}d</span>`;
      }
    }

    return '';
  }

  // ---- Calendar ----
  const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function renderCalendar() {
    document.getElementById('cal-title').textContent =
      `${MONTH_NAMES[calMonth]} ${calYear}`;

    renderCalGrid();
    renderAgenda();
  }

  function renderCalGrid() {
    const grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    // Day headers
    DAY_NAMES.forEach(d => {
      const h = document.createElement('div');
      h.className = 'cal-day-header';
      h.textContent = d;
      grid.appendChild(h);
    });

    const firstDay = new Date(calYear, calMonth, 1);
    // Monday = 0
    let startDow = firstDay.getDay() - 1;
    if (startDow < 0) startDow = 6;

    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const prevMonthDays = new Date(calYear, calMonth, 0).getDate();

    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);

    // Events index by date - each exhibition appears once
    // Use opening_date if available, otherwise start_date
    const evByDate = {};
    const filtered = getFiltered();
    filtered.forEach(ex => {
      const date = ex.opening_date || ex.start_date;
      if (!date) return;
      const type = ex.opening_date ? 'opening' : 'exhibition';
      if (!evByDate[date]) evByDate[date] = [];
      evByDate[date].push({ ex, type });
    });

    // Prev month fill
    for (let i = startDow - 1; i >= 0; i--) {
      const cell = document.createElement('div');
      cell.className = 'cal-cell other-month';
      cell.innerHTML = `<div class="day-num">${prevMonthDays - i}</div>`;
      grid.appendChild(cell);
    }

    // This month
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const cell = document.createElement('div');
      cell.className = 'cal-cell' + (dateStr === todayStr ? ' today' : '');
      let inner = `<div class="day-num">${d}</div>`;

      const events = evByDate[dateStr] || [];
      events.slice(0, 3).forEach(({ ex, type }) => {
        inner += `<span class="cal-dot type-${type}" title="${esc(ex.title)}" data-id="${esc(ex.id)}">${esc(ex.title)}</span>`;
      });
      if (events.length > 3) {
        inner += `<span class="cal-dot">+${events.length - 3} more</span>`;
      }

      cell.innerHTML = inner;
      // Add click handlers to cal-dots
      cell.querySelectorAll('.cal-dot[data-id]').forEach(dot => {
        dot.addEventListener('click', () => showPopup(dot.dataset.id));
      });
      grid.appendChild(cell);
    }

    // Next month fill
    const totalCells = startDow + daysInMonth;
    const remaining = (7 - (totalCells % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      const cell = document.createElement('div');
      cell.className = 'cal-cell other-month';
      cell.innerHTML = `<div class="day-num">${i}</div>`;
      grid.appendChild(cell);
    }
  }

  function renderAgenda() {
    const agenda = document.getElementById('cal-agenda');
    agenda.innerHTML = '';

    const filtered = getFiltered();
    const monthEvents = {};

    filtered.forEach(ex => {
      const date = ex.opening_date || ex.start_date;
      if (!date) return;
      const type = ex.opening_date ? 'opening' : 'exhibition';
      const d = new Date(date + 'T00:00:00');
      if (d.getFullYear() === calYear && d.getMonth() === calMonth) {
        if (!monthEvents[date]) monthEvents[date] = [];
        monthEvents[date].push({ type, ex });
      }
    });

    const sortedDates = Object.keys(monthEvents).sort();
    if (sortedDates.length === 0) {
      agenda.innerHTML = '<p class="no-results">No events this month.</p>';
      return;
    }

    sortedDates.forEach(date => {
      const dayDiv = document.createElement('div');
      dayDiv.className = 'agenda-day';
      dayDiv.innerHTML = `<div class="agenda-day-header">${formatDate(date)}</div>`;

      monthEvents[date].forEach(({ type, ex }) => {
        const item = document.createElement('div');
        item.className = 'agenda-item' + (type === 'opening' ? ' type-opening' : '');
        let detail = '';
        if (ex.venue) detail = ` at ${esc(ex.venue)}`;
        if (type === 'opening' && ex.opening_time) detail += ` ${esc(ex.opening_time)}`;
        item.innerHTML = `<span class="agenda-link">${esc(ex.title)}</span>${detail}`;
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => showPopup(ex.id));
        dayDiv.appendChild(item);
      });

      agenda.appendChild(dayDiv);
    });
  }

  // ---- ICS ----
  function makeICSContent(ex) {
    const uid = ex.id + '@art-openings-syd';
    const date = ex.opening_date || ex.start_date;
    if (!date) return null;

    const dtStart = date.replace(/-/g, '') + 'T180000';
    const dtEnd = date.replace(/-/g, '') + 'T210000';

    let summary = ex.title;
    if (ex.venue) summary += ' at ' + ex.venue;

    let location = '';
    if (ex.address) location = ex.address;
    if (ex.suburb) location += (location ? ', ' : '') + ex.suburb;

    return [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Art Openings Sydney//EN',
      'BEGIN:VEVENT',
      'UID:' + uid,
      'DTSTART:' + dtStart,
      'DTEND:' + dtEnd,
      'SUMMARY:' + icsEscape(summary),
      'DESCRIPTION:' + icsEscape(ex.description || ''),
      location ? 'LOCATION:' + icsEscape(location) : '',
      ex.website ? 'URL:' + ex.website : '',
      'END:VEVENT',
      'END:VCALENDAR',
    ].filter(Boolean).join('\r\n');
  }

  window.downloadICS = function (id) {
    const ex = DATA.find(e => e.id === id);
    if (!ex) return;
    const content = makeICSContent(ex);
    if (!content) return;

    const blob = new Blob([content], { type: 'text/calendar' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (ex.title || 'event').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 50) + '.ics';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  function buildGoogleCalUrl(ex) {
    const date = ex.opening_date || ex.start_date;
    if (!date) return '#';
    const dt = date.replace(/-/g, '');
    const dates = dt + 'T180000/' + dt + 'T210000';

    let title = ex.title;
    if (ex.venue) title += ' at ' + ex.venue;

    let location = '';
    if (ex.address) location = ex.address;
    if (ex.suburb) location += (location ? ', ' : '') + ex.suburb;

    // Manual URL construction to avoid URLSearchParams encoding slashes in dates
    const base = 'https://calendar.google.com/calendar/render?action=TEMPLATE';
    const params = '&text=' + encodeURIComponent(title)
      + '&dates=' + dates
      + '&details=' + encodeURIComponent(ex.description || '')
      + (location ? '&location=' + encodeURIComponent(location) : '');

    return base + params;
  }

  // Bulk ICS export
  function exportAllICS() {
    const filtered = getFiltered().filter(ex => ex.opening_date || ex.start_date);
    if (filtered.length === 0) return;

    if (typeof JSZip === 'undefined') {
      // Fallback: single combined file
      const events = filtered.map(makeICSContent).filter(Boolean);
      const blob = new Blob([events.join('\r\n')], { type: 'text/calendar' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'art-openings-sydney.ics';
      a.click();
      return;
    }

    const zip = new JSZip();
    filtered.forEach(ex => {
      const content = makeICSContent(ex);
      if (content) {
        const name = (ex.title || 'event').replace(/[^a-zA-Z0-9]/g, '_').slice(0, 50) + '.ics';
        zip.file(name, content);
      }
    });

    zip.generateAsync({ type: 'blob' }).then(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'art-openings-sydney.zip';
      a.click();
    });
  }

  // ---- Helpers ----
  function esc(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function icsEscape(str) {
    return (str || '').replace(/[\\;,\n]/g, c => {
      if (c === '\n') return '\\n';
      return '\\' + c;
    });
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  // ---- Event popup ----
  function showPopup(id) {
    const ex = DATA.find(e => e.id === id);
    if (!ex) return;

    document.getElementById('popup-title').textContent = ex.title;

    let meta = '';
    if (ex.venue) meta += `<span class="venue">${esc(ex.venue)}</span>`;
    if (ex.suburb) meta += (meta ? ', ' : '') + esc(ex.suburb);
    if (ex.artist) meta += (meta ? ' · ' : '') + esc(ex.artist);
    document.getElementById('popup-meta').innerHTML = meta;

    let dates = '';
    if (ex.start_date || ex.end_date) {
      dates += formatDate(ex.start_date);
      if (ex.end_date) dates += ' \u2013 ' + formatDate(ex.end_date);
    }
    if (ex.opening_date) {
      if (dates) dates += '<br>';
      dates += 'Opening: ' + formatDate(ex.opening_date);
      if (ex.opening_time) dates += ' ' + esc(ex.opening_time);
    }
    document.getElementById('popup-dates').innerHTML = dates;

    document.getElementById('popup-desc').textContent = ex.description || '';

    let actions = '';
    if (ex.opening_date || ex.start_date) {
      actions += `<button class="btn-ics" onclick="downloadICS('${esc(ex.id)}')">Download ICS</button>`;
      const gcUrl = buildGoogleCalUrl(ex);
      actions += `<a class="btn-gcal" href="${gcUrl}" target="_blank" rel="noopener">Google Calendar</a>`;
    }
    if (ex.website) {
      actions += `<a class="btn-web" href="${esc(ex.website)}" target="_blank" rel="noopener">Website</a>`;
    }
    document.getElementById('popup-actions').innerHTML = actions;

    const popup = document.getElementById('event-popup');
    popup.hidden = false;

    // Close handlers
    popup.querySelector('.popup-backdrop').onclick = () => { popup.hidden = true; };
    popup.querySelector('.popup-close').onclick = () => { popup.hidden = true; };
  }

  // Close popup on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.getElementById('event-popup').hidden = true;
    }
  });

  // ---- Event listeners ----
  function setupListeners() {
    document.getElementById('search').addEventListener('input', () => { render(); renderCalendar(); });
    document.getElementById('filter-opening-today').addEventListener('change', () => { render(); renderCalendar(); });
    document.getElementById('filter-closed').addEventListener('change', () => { render(); renderCalendar(); });
    document.getElementById('filter-suburb').addEventListener('change', () => { render(); renderCalendar(); });

    document.getElementById('btn-view-list').addEventListener('click', () => switchView('list'));
    document.getElementById('btn-view-cal').addEventListener('click', () => switchView('cal'));
    document.getElementById('btn-to-cal').addEventListener('click', () => switchView('cal'));

    document.getElementById('cal-prev').addEventListener('click', () => {
      calMonth--;
      if (calMonth < 0) { calMonth = 11; calYear--; }
      renderCalendar();
    });
    document.getElementById('cal-next').addEventListener('click', () => {
      calMonth++;
      if (calMonth > 11) { calMonth = 0; calYear++; }
      renderCalendar();
    });

    document.getElementById('btn-export-ics').addEventListener('click', exportAllICS);
  }

  function switchView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('view-' + view).classList.add('active');
    document.getElementById('btn-view-' + view).classList.add('active');
    if (view === 'cal') renderCalendar();
  }

  // ---- Boot ----
  document.addEventListener('DOMContentLoaded', init);
})();
