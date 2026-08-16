/* Gallery Directory */

(function () {
  'use strict';

  let DATA = [];

  const TYPE_LABELS = {
    commercial: 'Commercial',
    ari: 'Artist-run',
    museum: 'Museum',
    university: 'University',
    project_space: 'Project space',
  };

  const ENTRY_LABELS = {
    free: 'Free entry',
    paid: 'Paid entry',
    donation: 'Donation',
    unknown: '',
  };

  async function init() {
    try {
      const resp = await fetch('galleries.json?v=' + Date.now());
      const json = await resp.json();
      DATA = json.galleries || [];
    } catch (e) {
      console.error('Failed to load galleries:', e);
      DATA = [];
    }
    populateSuburbs();
    
    // Pre-fill search from URL param (linked from exhibitions page)
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    if (q) {
      document.getElementById('search').value = q;
    }
    
    render();
    setupListeners();
  }

  function populateSuburbs() {
    const suburbs = new Set();
    DATA.forEach(g => { if (g.suburb) suburbs.add(g.suburb); });
    const sel = document.getElementById('filter-suburb');
    Array.from(suburbs).sort().forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    });
  }

  function getFiltered() {
    const q = document.getElementById('search').value.toLowerCase().trim();
    const type = document.getElementById('filter-type').value;
    const suburb = document.getElementById('filter-suburb').value;

    return DATA.filter(g => {
      if (type && g.type !== type) return false;
      if (suburb && g.suburb !== suburb) return false;
      if (q) {
        const hay = [g.name, g.suburb, g.address].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }

  function render() {
    const list = document.getElementById('gallery-list');
    const noResults = document.getElementById('no-results');
    const filtered = getFiltered();

    document.getElementById('gallery-count').textContent =
      `${filtered.length} gal${filtered.length === 1 ? 'lery' : 'leries'}`;

    list.innerHTML = '';
    if (filtered.length === 0) {
      noResults.hidden = false;
      return;
    }
    noResults.hidden = true;
    filtered.forEach(g => list.appendChild(createCard(g)));
  }

  function createCard(g) {
    const card = document.createElement('div');
    card.className = 'gallery-card';

    // Type badge
    const typeLabel = TYPE_LABELS[g.type] || '';
    const entryLabel = ENTRY_LABELS[g.entry] || '';

    // Location
    let location = '';
    if (g.address) location += esc(g.address);
    if (g.suburb) location += (location ? ', ' : '') + esc(g.suburb);
    if (g.postcode) location += ' ' + esc(g.postcode);

    // Map link
    let mapLink = '';
    if (g.latitude && g.longitude) {
      mapLink = `https://www.google.com/maps/search/?api=1&query=${g.latitude},${g.longitude}`;
    } else if (location) {
      mapLink = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(g.name + ' ' + location)}`;
    }

    // Links
    let links = '';
    if (g.website) {
      links += `<a href="${esc(g.website)}" target="_blank" rel="noopener" class="g-link">Website</a>`;
    }
    if (g.instagram) {
      const handle = g.instagram.replace('@', '');
      links += `<a href="https://instagram.com/${esc(handle)}" target="_blank" rel="noopener" class="g-link">${esc(g.instagram)}</a>`;
    }
    if (mapLink) {
      links += `<a href="${mapLink}" target="_blank" rel="noopener" class="g-link">Map</a>`;
    }

    // Meta badges
    let badges = '';
    if (typeLabel) badges += `<span class="g-badge g-type-${g.type}">${typeLabel}</span>`;
    if (entryLabel) badges += `<span class="g-badge g-entry">${entryLabel}</span>`;

    card.innerHTML = `
      <div class="g-header">
        <h3>${esc(g.name)}</h3>
        ${badges ? `<div class="g-badges">${badges}</div>` : ''}
      </div>
      ${location ? `<p class="g-location">${location}</p>` : ''}
      ${g.hours ? `<p class="g-hours">${esc(g.hours)}</p>` : ''}
      ${g.accessibility ? `<p class="g-access">${esc(g.accessibility)}</p>` : ''}
      ${links ? `<div class="g-links">${links}</div>` : ''}
    `;
    return card;
  }

  function esc(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function setupListeners() {
    const rerender = () => render();
    document.getElementById('search').addEventListener('input', rerender);
    document.getElementById('filter-type').addEventListener('change', rerender);
    document.getElementById('filter-suburb').addEventListener('change', rerender);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
