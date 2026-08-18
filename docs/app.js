/* Art Openings Sydney - Frontend */

(function () {
  'use strict';

  let DATA = [];
  let GALLERIES = [];
  let calYear, calMonth;

  async function init() {
    try {
      const resp = await fetch('data.json?v=' + Date.now());
      const json = await resp.json();
      DATA = json.exhibitions || [];
    } catch (e) {
      console.error('Failed to load data:', e);
      DATA = [];
    }
    try {
      const resp = await fetch('galleries.json?v=' + Date.now());
      const json = await resp.json();
      GALLERIES = json.galleries || [];
    } catch (e) {
      GALLERIES = [];
    }
    populateSuburbs();
    populateVenues();
    render();
    setupListeners();
    const now = new Date();
    calYear = now.getFullYear();
    calMonth = now.getMonth();
    renderCalendar();
  }

  function populateVenues() {
    const venues = new Set();
    DATA.forEach(ex => { if (ex.venue) venues.add(ex.venue); });
    const sel = document.getElementById('filter-venue');
    Array.from(venues).sort((a, b) => a.localeCompare(b)).forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
  }

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

  // ---- Helpers ----
  const TODAY = new Date();
  TODAY.setHours(0, 0, 0, 0);
  const TODAY_STR = `${TODAY.getFullYear()}-${String(TODAY.getMonth()+1).padStart(2,'0')}-${String(TODAY.getDate()).padStart(2,'0')}`;

  function isOnNow(ex) {
    const start = ex.start_date || ex.opening_date;
    const end = ex.end_date;
    if (!start) return false;
    if (start > TODAY_STR && !end) return false; // future, no end
    if (start <= TODAY_STR && (!end || end >= TODAY_STR)) return true;
    return false;
  }

  function isOpeningThisWeek(ex) {
    const d = ex.opening_date || ex.start_date;
    if (!d) return false;
    const dt = new Date(d + 'T00:00:00');
    const diff = (dt - TODAY) / 86400000;
    return diff >= 0 && diff <= 7;
  }

  // ---- Filtering & Sorting ----
  function getFiltered() {
    const q = document.getElementById('search').value.toLowerCase().trim();
    const onNow = document.getElementById('filter-on-now').checked;
    const openingWeek = document.getElementById('filter-opening-week').checked;
    const showClosed = document.getElementById('filter-closed').checked;
    const suburb = document.getElementById('filter-suburb').value;
    const venue = document.getElementById('filter-venue').value;

    let results = DATA.filter(ex => {
      // Closed toggle
      if (showClosed) {
        if (ex.status !== 'closed') return false;
      } else {
        if (ex.status === 'closed') return false;
      }

      // On now filter
      if (onNow && !showClosed) {
        if (!isOnNow(ex) && !isOpeningThisWeek(ex)) return false;
      }

      // Opening this week filter (additive narrowing)
      if (openingWeek && !showClosed) {
        if (!isOpeningThisWeek(ex)) return false;
      }

      // Suburb
      if (suburb && ex.suburb !== suburb) return false;
      if (venue && ex.venue !== venue) return false;

      // Search
      if (q) {
        const hay = [ex.title, ex.artist, ex.venue, ex.suburb, ex.description]
          .join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    // Sort: on now first, then upcoming by start date, then past
    results.sort((a, b) => {
      const aNow = isOnNow(a) ? 0 : 1;
      const bNow = isOnNow(b) ? 0 : 1;
      if (aNow !== bNow) return aNow - bNow;

      // Within same group, sort by opening/start date ascending
      const aDate = a.opening_date || a.start_date || '9999';
      const bDate = b.opening_date || b.start_date || '9999';

      // For "on now", show soonest-ending first
      if (aNow === 0 && bNow === 0) {
        const aEnd = a.end_date || '9999';
        const bEnd = b.end_date || '9999';
        return aEnd.localeCompare(bEnd);
      }

      return aDate.localeCompare(bDate);
    });

    return results;
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
    filtered.forEach(ex => list.appendChild(createCard(ex)));
  }

  function createCard(ex) {
    const card = document.createElement('div');
    card.className = 'ex-card' + (ex.status === 'closed' ? ' status-closed' : '');

    const badge = getBadge(ex);
    const titleLink = ex.website
      ? `<a href="${esc(ex.website)}" target="_blank" rel="noopener">${esc(ex.title)}</a>`
      : esc(ex.title);

    let meta = '';
    if (ex.venue) meta += `<a href="#" class="venue" onclick="showGallery('${esc(ex.venue).replace(/'/g, "\\'")}');return false;">${esc(ex.venue)}</a>`;
    if (ex.suburb) meta += (meta ? ', ' : '') + esc(ex.suburb);
    if (ex.artist) meta += (meta ? ' &middot; ' : '') + esc(ex.artist);

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
      actions += `<a href="${gcUrl}" target="_blank" rel="noopener" title="Google Calendar">GCal</a>`;
    }

    card.innerHTML = `
      <h3>${titleLink}</h3>
      ${badge}
      ${meta ? `<div class="ex-meta">${meta}</div>` : ''}
      ${dates ? `<div class="ex-dates">${dates}</div>` : ''}
      ${ex.description ? `<p class="ex-desc">${esc(ex.description)}</p>` : ''}
      ${actions ? `<div class="ex-actions">${actions}</div>` : ''}
    `;
    return card;
  }

  function getBadge(ex) {
    if (ex.status === 'closed') return '';

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (ex.opening_date) {
      const opDate = new Date(ex.opening_date + 'T00:00:00');
      const diff = Math.ceil((opDate - today) / 86400000);
      if (diff === 0) return '<div class="badge badge-opening">Opening tonight</div>';
      if (diff > 0 && diff <= 3) return `<div class="badge badge-opening">Opens in ${diff}d</div>`;
    }

    if (ex.end_date) {
      const endDate = new Date(ex.end_date + 'T00:00:00');
      const diff = Math.ceil((endDate - today) / 86400000);
      if (diff === 0) return '<div class="badge badge-closing">Last day</div>';
      if (diff > 0 && diff <= 3) return `<div class="badge badge-closing">Closes in ${diff}d</div>`;
    }

    if (isOnNow(ex)) return '<div class="badge badge-on-now">On now</div>';
    return '';
  }

  // ---- Calendar ----
  const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function renderCalendar() {
    document.getElementById('cal-title').textContent = `${MONTH_NAMES[calMonth]} ${calYear}`;
    renderCalGrid();
    renderAgenda();
  }

  function renderCalGrid() {
    const grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    DAY_NAMES.forEach(d => {
      const h = document.createElement('div');
      h.className = 'cal-day-header';
      h.textContent = d;
      grid.appendChild(h);
    });

    const firstDay = new Date(calYear, calMonth, 1);
    let startDow = firstDay.getDay() - 1;
    if (startDow < 0) startDow = 6;

    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const prevMonthDays = new Date(calYear, calMonth, 0).getDate();

    // Events index by date - each exhibition once
    const evByDate = {};
    const allData = DATA.filter(ex => ex.status !== 'closed');
    allData.forEach(ex => {
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
      cell.className = 'cal-cell' + (dateStr === TODAY_STR ? ' today' : '');
      let inner = `<div class="day-num">${d}</div>`;

      const events = evByDate[dateStr] || [];
      events.slice(0, 3).forEach(({ ex, type }) => {
        inner += `<span class="cal-dot type-${type}" data-id="${esc(ex.id)}">${esc(ex.title)}</span>`;
      });
      if (events.length > 3) {
        inner += `<span class="cal-dot cal-more">+${events.length - 3} more</span>`;
      }

      cell.innerHTML = inner;
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

    const monthEvents = {};
    const allData = DATA.filter(ex => ex.status !== 'closed');
    allData.forEach(ex => {
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
        item.innerHTML = `<span>${esc(ex.title)}</span>${detail}`;
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
      'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Art Openings Sydney//EN',
      'BEGIN:VEVENT', 'UID:' + uid, 'DTSTART:' + dtStart, 'DTEND:' + dtEnd,
      'SUMMARY:' + icsEscape(summary), 'DESCRIPTION:' + icsEscape(ex.description || ''),
      location ? 'LOCATION:' + icsEscape(location) : '',
      ex.website ? 'URL:' + ex.website : '',
      'END:VEVENT', 'END:VCALENDAR',
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
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE'
      + '&text=' + encodeURIComponent(title)
      + '&dates=' + dates
      + '&details=' + encodeURIComponent(ex.description || '')
      + (location ? '&location=' + encodeURIComponent(location) : '');
  }

  function exportAllICS() {
    const filtered = getFiltered().filter(ex => ex.opening_date || ex.start_date);
    if (filtered.length === 0) return;
    if (typeof JSZip === 'undefined') {
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

  // ---- Gallery popup ----
  const GALLERY_ALIASES = {
    'art gallery of nsw':                   'art gallery of new south wales',
    'agnsw':                                'art gallery of new south wales',
    'mca':                                  'museum of contemporary art australia',
    'mca australia':                        'museum of contemporary art australia',
    'museum of contemporary art':           'museum of contemporary art australia',
    'redfern art gallery in sydney':        'redfern art gallery',
    'woollahra gallery':                    'woollahra gallery at redleaf',
    'station':                              'station sydney',
    'gallery 144 (formerly outsider)':      'gallery 144',
    'michael reid':                         'michael reid sydney',
    'piermarq':                             'piermarq',
    'piermarq*':                            'piermarq',
    'station | sydney':                     'station sydney',
  };

  function findGallery(name) {
    const nl = name.toLowerCase().trim();
    const canonical = GALLERY_ALIASES[nl] || nl;
    return GALLERIES.find(g => {
      const gl = g.name.toLowerCase().trim();
      return gl === canonical ||
             gl === nl ||
             gl.includes(nl) ||
             nl.includes(gl);
    });
  }

  window.showGallery = function (name) {
    const gallery = findGallery(name);

    const popup = document.getElementById('event-popup');
    document.getElementById('popup-title').textContent = name;

    if (!gallery) {
      document.getElementById('popup-meta').innerHTML = '<span class="venue">Gallery not yet in directory</span>';
      document.getElementById('popup-dates').innerHTML = '';
      document.getElementById('popup-desc').textContent = '';
      document.getElementById('popup-actions').innerHTML =
        `<a class="btn-web" href="galleries.html" target="_blank">Browse Gallery Directory</a>`;
      popup.hidden = false;
      popup.querySelector('.popup-backdrop').onclick = () => { popup.hidden = true; };
      popup.querySelector('.popup-close').onclick = () => { popup.hidden = true; };
      return;
    }

    let meta = '';
    if (gallery.type) {
      const typeLabels = { commercial: 'Commercial', ari: 'Artist-run', museum: 'Museum', university: 'University', project_space: 'Project space' };
      meta += `<span class="venue">${typeLabels[gallery.type] || gallery.type}</span>`;
    }
    if (gallery.entry && gallery.entry !== 'unknown') {
      const entryLabels = { free: 'Free entry', paid: 'Paid entry', donation: 'Donation' };
      meta += (meta ? ' · ' : '') + (entryLabels[gallery.entry] || '');
    }
    document.getElementById('popup-meta').innerHTML = meta;

    let location = '';
    if (gallery.address) location += esc(gallery.address);
    if (gallery.suburb) location += (location ? ', ' : '') + esc(gallery.suburb);
    if (gallery.postcode) location += ' ' + esc(gallery.postcode);
    let info = location ? `<div style="margin-bottom:0.4rem">${location}</div>` : '';
    if (gallery.hours) info += `<div style="margin-bottom:0.4rem;color:var(--purple)">${esc(gallery.hours)}</div>`;
    document.getElementById('popup-dates').innerHTML = info;

    document.getElementById('popup-desc').textContent = gallery.accessibility || '';

    let actions = '';
    if (gallery.website) {
      actions += `<a class="btn-web" href="${esc(gallery.website)}" target="_blank" rel="noopener">Website</a>`;
    }
    if (gallery.instagram) {
      const handle = gallery.instagram.replace('@', '');
      actions += `<a class="btn-gcal" href="https://instagram.com/${esc(handle)}" target="_blank" rel="noopener">${esc(gallery.instagram)}</a>`;
    }
    const mapQuery = [name, location].filter(Boolean).join(' ');
    const mapUrl = mapQuery ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}` : '';
    if (mapUrl) {
      actions += `<a class="btn-ics" href="${mapUrl}" target="_blank" rel="noopener">Map</a>`;
    }
    document.getElementById('popup-actions').innerHTML = actions;

    popup.hidden = false;
    popup.querySelector('.popup-backdrop').onclick = () => { popup.hidden = true; };
    popup.querySelector('.popup-close').onclick = () => { popup.hidden = true; };
  };

  // ---- Popup ----
  function showPopup(id) {
    const ex = DATA.find(e => e.id === id);
    if (!ex) return;
    document.getElementById('popup-title').textContent = ex.title;

    let meta = '';
    if (ex.venue) meta += `<span class="venue">${esc(ex.venue)}</span>`;
    if (ex.suburb) meta += (meta ? ', ' : '') + esc(ex.suburb);
    if (ex.artist) meta += (meta ? ' &middot; ' : '') + esc(ex.artist);
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
      actions += `<a class="btn-gcal" href="${buildGoogleCalUrl(ex)}" target="_blank" rel="noopener">Google Calendar</a>`;
    }
    if (ex.website) {
      actions += `<a class="btn-web" href="${esc(ex.website)}" target="_blank" rel="noopener">Website</a>`;
    }
    document.getElementById('popup-actions').innerHTML = actions;

    const popup = document.getElementById('event-popup');
    popup.hidden = false;
    popup.querySelector('.popup-backdrop').onclick = () => { popup.hidden = true; };
    popup.querySelector('.popup-close').onclick = () => { popup.hidden = true; };
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') document.getElementById('event-popup').hidden = true;
  });

  // ---- Helpers ----
  function esc(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function icsEscape(str) {
    return (str || '').replace(/[\\;,\n]/g, c => c === '\n' ? '\\n' : '\\' + c);
  }
  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch { return dateStr; }
  }

  // ---- Event listeners ----
  function setupListeners() {
    const rerender = () => { render(); renderCalendar(); };
    document.getElementById('search').addEventListener('input', rerender);
    document.getElementById('filter-on-now').addEventListener('change', rerender);
    document.getElementById('filter-opening-week').addEventListener('change', rerender);
    document.getElementById('filter-closed').addEventListener('change', rerender);
    document.getElementById('filter-suburb').addEventListener('change', rerender);
    document.getElementById('filter-venue').addEventListener('change', rerender);

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

  document.addEventListener('DOMContentLoaded', init);
})();
