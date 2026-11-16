// The page owns state and scientific data. This module owns only its stage.
const DRAWN = 'Drawn by code from open data; the code was written with AI assistance.';
const UNAVAILABLE = 'The 3D globes cannot run in this browser. Use the buttons and the flat maps.';
const RAD = Math.PI / 180;
const finite = x => typeof x === 'number' && Number.isFinite(x);
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const wrap = x => ((x + 180) % 360 + 360) % 360 - 180;
const el = (tag, cls, text) => {
  const n = document.createElement(tag); n.className = cls || 'gb-text';
  if (text != null) n.textContent = text;
  return n;
};
const button = (text, action, cls = 'gb-button') => {
  const b = el('button', cls, text); b.type = 'button'; b.addEventListener('click', action); return b;
};
let libraryPromise;
function library() {
  if (typeof window.Globe === 'function') return Promise.resolve(window.Globe);
  if (!libraryPromise) libraryPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = new URL('./vendor/globe.gl.min.js', import.meta.url).href;
    script.onload = () => typeof window.Globe === 'function' ? resolve(window.Globe) : reject(new Error('No globe library.'));
    script.onerror = () => { script.remove(); reject(new Error('No globe library.')); };
    document.head.append(script);
  }).catch(error => { libraryPromise = null; throw error; });
  return libraryPromise;
}

function squareReader(manifest, buffers) {
  if (!manifest || manifest.count !== manifest.ids?.length) return null;
  const types = { uint8: ['getUint8', 1], int8: ['getInt8', 1], uint16: ['getUint16', 2],
    int16: ['getInt16', 2], uint32: ['getUint32', 4], int32: ['getInt32', 4],
    float32: ['getFloat32', 4], float64: ['getFloat64', 8] };
  const columns = new Map();
  for (const [key, c] of Object.entries(manifest.columns || {})) {
    const [method, bytes] = types[c.type] || [];
    if (!method || !Number.isInteger(c.offset) || c.offset < 0 || !finite(c.scale) || c.scale <= 0) return null;
    columns.set(key, { ...c, file: c.file || manifest.file, method, bytes, end: c.offset + manifest.count * bytes });
  }
  return (key, i) => {
    const c = columns.get(key), view = c && buffers.get(c.file);
    if (!c || !view || c.end > view.byteLength || i < 0 || i >= manifest.count) return null;
    const raw = view[c.method](c.offset + i * c.bytes, true);
    return !finite(raw) || raw === c.unknown ? null : raw / c.scale;
  };
}

// The outline file contains polar rings, not a global GeoJSON map.
function landFeatures(data) {
  if (!finite(data?.scale) || data.scale <= 0) return [];
  return [...(data.north || []), ...(data.south || [])].map((ring, index) => ({
    type: 'Feature', id: index, properties: {}, geometry: { type: 'Polygon', coordinates: [
      Array.from({ length: ring.length / 2 }, (_, i) => [ring[i * 2] / data.scale, ring[i * 2 + 1] / data.scale])
    ] }
  }));
}

function palette(root, mode) {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = getComputedStyle(root).getPropertyValue(mode === 'mars' ? '--mars' : '--moon').trim()
    || (mode === 'mars' ? '#e89673' : '#efc56e');
  ctx.fillRect(0, 0, 1, 1);
  const high = [...ctx.getImageData(0, 0, 1, 1).data].slice(0, 3).map(x => Math.round(x * .8 + 255 * .2));
  const low = high.map(x => Math.round(x * .29));
  return t => `rgb(${low.map((v, i) => Math.round(v + (high[i] - v) * clamp(t, 0, 1))).join(',')})`;
}

export async function mount(root, api) {
  const oldNodes = [...root.children].map(node => ({ node, hidden: node.hidden }));
  const lifecycle = new AbortController(), cleanups = [], globes = [], textureURLs = [];
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let alive = true, touched = false, failed = false, previous = null, dataKey = '', points = [], pins = [];
  let earth, moonGlobe, marsGlobe, resizeObserver, visibilityObserver, selected = null;
  let labelFrame = 0, labelResizeTimer = 0, earthPins = [];
  let matches = null, matchVersion = 0, shownMatchVersion = -1, showAllPlaces = false, scoreRequest = 0, tourSnapshotActive = false;
  const wrapper = el('div', 'gb-module'), scene = el('div', 'gb-scene');
  const toolbar = el('div', 'gb-toolbar'), status = el('p', 'gb-status'); status.setAttribute('role', 'status');
  const summary = el('p', 'gb-summary'); summary.setAttribute('aria-live', 'polite');
  const working = el('p', 'gb-status'); working.setAttribute('role', 'status'); working.hidden = true;
  const legend = el('div', 'gb-legend'), places = el('ul', 'gb-places');
  places.setAttribute('aria-label', 'Places on the Earth');
  const caption = el('p', 'gb-caption', DRAWN), credits = el('span', 'gb-credits'); caption.append(credits);
  const about = el('details', 'gb-about'), description = el('p', 'gb-description');
  const unknownNote = el('p', 'gb-unknown');
  about.append(el('summary', 'gb-about-title', 'About this picture'), status, description, unknownNote, caption);
  const morePlaces = button('Show all', () => { showAllPlaces = !showAllPlaces; renderPlaces(); }, 'gb-place-button gb-more');
  morePlaces.setAttribute('aria-expanded', 'false'); morePlaces.hidden = true;
  const placeRow = el('div', 'gb-place-row'); placeRow.append(places, morePlaces);
  const globeButton = button('Globe', () => api.setState({ stage: 'globe' }));
  const flatButton = button('Flat maps', () => api.setState({ stage: 'flat', go: api.getState().dest === 'mars' ? 'mars-map' : 'map' }));
  toolbar.setAttribute('aria-label', 'Stage view'); toolbar.append(globeButton, flatButton);
  wrapper.append(toolbar, working, scene, legend, summary, placeRow, about);
  root.append(wrapper);
  const read = (name, bin = false) => Promise.resolve().then(() => bin ? api.loadBin(name) : api.loadJSON(name)).catch(() => null);
  const [mars, meta, land, lunar, textures] = await Promise.all([
    read('mars.json'), read('meta.json'), read('land.json'), read('moon.json'),
    fetch(new URL('./vendor/textures/textures.json', import.meta.url), { redirect: 'error' })
      .then(r => r.ok ? r.json() : null).catch(() => null)
  ]);
  const squareBuffers = new Map(), squareLoads = new Map(), squareFailed = new Set();
  const loadSquareFile = file => {
    if (!file) return Promise.resolve(false);
    if (!squareLoads.has(file)) squareLoads.set(file, read(file, true).then(buffer => {
      if (buffer instanceof ArrayBuffer) { squareBuffers.set(file, new DataView(buffer)); return true; }
      squareFailed.add(file); return false;
    }));
    return squareLoads.get(file);
  };
  const sharedReady = mars?.squares?.file ? await loadSquareFile(mars.squares.file) : false;
  const readSquare = sharedReady ? squareReader(mars.squares, squareBuffers) : null;
  for (const picture of textures?.images || []) {
    if (picture.body && picture.credit) credits.append(el('span', 'gb-credit', `${picture.body}: ${picture.credit}`));
  }
  const areas = Array.from({ length: api.areaCount }, (_, i) => ({ ...api.area(i), area: i }))
    .filter(a => a.id && finite(a.lat) && finite(a.lon));
  const squares = readSquare ? mars.squares.ids.map((id, i) => ({ id, index: i,
    lat: readSquare('lat', i), lon: readSquare('lon', i), region: mars.squares.regions[readSquare('region', i)] }))
    .filter(a => finite(a.lat) && finite(a.lon)) : [];
  const squareById = new Map(squares.map(s => [s.id, s]));
  const areaByIndex = new Map(areas.map(a => [a.area, a]));
  const squareByIndex = new Map(squares.map(a => [a.index, a]));
  const num = (n, digits = 0) => finite(n) ? api.fmtNumber(n, digits) : 'unknown';
  const nameArea = a => a.named || `${a.region || 'Area'} · ${a.id}`;
  const nameSquare = a => `${a.region || 'Square'} · ${a.id}`;
  const moonCoordinates = new Map((mars?.locators?.moon || []).map(s => [s.id, s]));
  for (const card of lunar?.cards || []) {
    if (finite(card.centre?.lat) && finite(card.centre?.lon_east)) moonCoordinates.set(card.id, card.centre);
  }
  const moonMeta = new Map((meta?.targets || []).map(t => [t.id, t]));
  const moonSites = api.targets.map(t => ({ ...moonMeta.get(t.id), ...t, ...moonCoordinates.get(t.id), id: t.id, name: t.name }))
    .filter(s => finite(s.lat) && finite(s.lon_east));
  const marsCoordinates = new Map((mars?.locators?.mars || []).map(s => [s.id, s]));
  const marsSites = (mars?.sites || []).map(s => ({ ...marsCoordinates.get(s.id), ...s }))
    .filter(s => finite(s.lat) && finite(s.lon_east));
  const stateOf = s => ({ ...s, dest: s.dest === 'mars' ? 'mars' : 'moon',
    target: s.target || api.targets[0]?.id, msite: s.msite || mars?.sites?.[0]?.id,
    mgoal: ['full', 'landscape', 'environment'].includes(s.mgoal) ? s.mgoal : 'full', step: +s.step || 3 });
  const current = () => stateOf(api.getState());
  const listsOf = s => Array.isArray(s.lists) ? s.lists.filter(value => typeof value === 'string' && value.trim()) : [];
  const marsGroups = [...new Set(marsSites.flatMap(listsOf))].sort();
  const sourceLine = s => listsOf(s).join(' · ') || s.list_summary || s.list_line || '';
  const groupOf = (s, mode) => {
    const tags = listsOf(s);
    if (mode === 'moon') {
      const kept = Array.isArray(s.lists) ? tags.some(tag => /\b2024\b/.test(tag))
        : String(s.list_summary || '').split(/(?<=[.!?])\s+/).some(line => /\b2024\b/.test(line) && !/\b(?:not|no longer|removed)\b/i.test(line));
      return kept ? 'NASA 2024 list' : 'NASA 2022 list only';
    }
    return ['NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones']
      .find((group, i) => tags.some(tag => i === 0 ? /NASA landing sites?/i.test(tag) : i === 1 ? /2021/.test(tag) : /2015/.test(tag))) || 'Mars';
  };
  const shapeOf = (s, mode) => mode === 'moon' ? s.has_model === false ? 'diamond' : 'circle'
    : listsOf(s).length ? `polygon-${marsGroups.indexOf(listsOf(s)[0]) + 3}` : 'circle';
  const shapeVertices = shape => {
    const count = shape === 'circle' ? 16 : shape === 'diamond' ? 4 : Number(shape.slice(8));
    return Array.from({ length: count }, (_, i) => { const angle = i * Math.PI * 2 / count - Math.PI / 2; return [Math.cos(angle), Math.sin(angle)]; });
  };
  const squareSize = () => `First pass · squares of ${num(mars?.meta?.square_deg, 1)}° (approximately ${num(mars?.meta?.square_km_about)} km)`;

  function activate(pin) {
    stopRotation();
    if (pin.mode === 'mars') api.setState({ dest: 'mars', msquare: pin.id, go: 'mars-square' });
    else api.openPlace(pin.id);
  }
  function stopRotation() {
    touched = true;
    globes.forEach(g => { g.globe.controls().autoRotate = false; });
  }
  wrapper.addEventListener('pointerdown', stopRotation, { signal: lifecycle.signal });
  wrapper.addEventListener('keydown', stopRotation, { signal: lifecycle.signal });

  function panel(body, title) {
    const box = el('div', `gb-body gb-${body}`), host = el('div', 'gb-host');
    host.setAttribute('aria-label', title); host.setAttribute('role', 'group');
    box.append(el('p', 'gb-body-label', title), host); scene.append(box);
    return { box, host, body, visible: true };
  }
  const moonPanel = panel('moon', 'The Moon, south pole · close view');
  const marsPanel = panel('mars', 'Mars');
  const earthPanel = panel('earth', 'The Earth');
  const destinationMenus = [];
  let highlighted = { moon: null, mars: null };
  const focusedDestination = mode => document.activeElement?.closest(`[data-mode="${mode}"][data-destination]`)?.dataset.destination || null;
  const clearUnfocused = mode => queueMicrotask(() => { highlighted[mode] = focusedDestination(mode); updateDestinationMarks(); });
  function selectDestination(d) {
    stopRotation();
    api.setState(d.mode === 'moon' ? { dest: 'moon', target: d.id } : { dest: 'mars', msite: d.id });
    destinationMenus.forEach(menu => { menu.fold.open = false; });
  }
  function destinationMenu(panel, list, mode) {
    const fold = el('details', 'gb-destinations'), title = el('summary', 'gb-destination-title', `${num(list.length)} ${mode === 'moon' ? 'lunar regions' : 'Mars sites'}`);
    const body = el('div', 'gb-destination-menu'), searchLabel = el('label', 'gb-destination-filter'), input = el('input', 'gb-destination-input');
    input.type = 'search'; input.autocomplete = 'off'; input.setAttribute('aria-label', mode === 'moon' ? 'Filter lunar regions' : 'Filter Mars sites');
    searchLabel.append(el('span', '', 'Filter by name or list'), input);
    const rows = el('ul', 'gb-destination-list'), empty = el('p', 'gb-destination-empty', 'No destination has these words.'); empty.hidden = true;
    const groups = (mode === 'moon' ? ['NASA 2024 list', 'NASA 2022 list only']
      : ['NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones', 'Mars'])
      .filter(group => list.some(d => groupOf(d, mode) === group));
    const ordered = mode === 'moon' ? [...list].sort((a, b) => (a.limitDeg ?? a.limit_deg ?? Infinity) - (b.limitDeg ?? b.limit_deg ?? Infinity)) : list;
    const entries = [];
    for (const group of groups) {
      const heading = el('li', 'gb-destination-group', group); rows.append(heading);
      for (const data of ordered.filter(d => groupOf(d, mode) === group)) {
        const d = { ...data, mode }, row = el('li', 'gb-destination'), choose = button(d.name, () => selectDestination(d), 'gb-place-button');
        choose.dataset.destination = d.id; choose.dataset.mode = mode;
        const note = [sourceLine(d), d.has_model === false ? 'No terrain model' : ''].filter(Boolean).join(' · ');
        if (note) choose.append(el('small', 'gb-destination-note', note));
        for (const event of ['focus', 'blur', 'pointerenter', 'pointerleave']) choose.addEventListener(event, () => {
          if (event === 'focus' || event === 'pointerenter') { highlighted[mode] = d.id; updateDestinationMarks(); }
          else clearUnfocused(mode);
        });
        row.append(choose); rows.append(row); entries.push({ row, choose, group, words: `${d.name} ${note}`.toLocaleLowerCase() });
      }
    }
    const filter = () => {
      const words = input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
      for (const entry of entries) entry.row.hidden = !words.every(word => entry.words.includes(word));
      for (const heading of rows.querySelectorAll('.gb-destination-group')) heading.hidden = !entries.some(entry => entry.group === heading.textContent && !entry.row.hidden);
      empty.hidden = entries.some(entry => !entry.row.hidden);
    };
    input.addEventListener('input', filter);
    fold.addEventListener('toggle', () => {
      if (menu.skipToggle) { menu.skipToggle = false; return; }
      if (fold.open) { destinationMenus.forEach(menu => { if (menu.fold !== fold) menu.fold.open = false; }); input.focus({ preventScroll: true }); }
      else { highlighted[mode] = null; updateDestinationMarks(); }
    });
    fold.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); fold.open = false; title.focus(); return; }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      const choices = entries.filter(entry => !entry.row.hidden).map(entry => entry.choose); if (!choices.length) return;
      event.preventDefault(); const at = choices.indexOf(document.activeElement);
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? choices.length - 1 : (at + (event.key === 'ArrowUp' ? -1 : 1) + choices.length) % choices.length;
      choices[index].focus();
    });
    body.append(searchLabel, rows, empty); fold.append(title, body); panel.box.append(fold);
    const menu = { fold, input, filter, rows, skipToggle: false }; destinationMenus.push(menu); return menu;
  }
  const lunarMenu = destinationMenu(moonPanel, moonSites, 'moon'), marsMenu = destinationMenu(marsPanel, marsSites, 'mars');
  const lunarChoices = lunarMenu.fold;
  const shapeKey = el('ul', 'gb-shape-key');
  shapeKey.append(el('li', '', 'Moon: a circle marks a region with a terrain model. A diamond marks a region without a terrain model.'));
  for (const [index, group] of marsGroups.entries()) {
    const item = el('li', ''), symbol = el('span', 'gb-shape-symbol');
    symbol.setAttribute('aria-hidden', 'true'); symbol.style.clipPath = `polygon(${shapeVertices(`polygon-${index + 3}`).map(([x, y]) => `${50 + x * 50}% ${50 + y * 50}%`).join(',')})`;
    item.append(symbol, document.createTextNode(`Mars · ${group}`)); shapeKey.append(item);
  }
  if (!marsGroups.length) shapeKey.append(el('li', '', 'Mars: a circle marks a site. The data has no list tags.'));
  about.append(shapeKey);
  const controls = el('div', 'gb-earth-controls');
  const earthAltitude = () => root.clientWidth < 480 ? 1.55 : 1.5;
  const turn = (lat, lon, altitude = earthAltitude(), duration = 1200) => {
    if (!earth || !finite(lat) || !finite(lon)) return;
    const start = earth.pointOfView();
    earth.pointOfView({ lat: clamp(lat, -89.8, 89.8), lng: start.lng + wrap(lon - start.lng), altitude }, motion.matches ? 0 : duration);
  };
  const poleControls = el('div', 'gb-poles');
  for (const [label, lat] of [['Arctic', 89.8], ['Antarctic', -89.8]]) {
    poleControls.append(button(label, () => { stopRotation(); turn(lat, earth?.pointOfView().lng || 0); }));
  }
  const zoomControls = el('div', 'gb-zoom');
  for (const [label, factor, accessible] of [['+', .8, 'Zoom in on the Earth'], ['−', 1.25, 'Zoom out from the Earth']]) {
    const b = button(label, () => { stopRotation(); const p = earth?.pointOfView(); if (p) turn(p.lat, p.lng, clamp(p.altitude * factor, 1.15, 4)); });
    b.setAttribute('aria-label', accessible); zoomControls.append(b);
  }
  controls.append(poleControls, zoomControls); earthPanel.box.append(controls);

  // The ring remains at its data coordinate; a leader line separates nearby names.
  function htmlMarker(d) {
    const holder = el('div', `gb-anchor gb-${d.mode}-marker${d.result ? ' gb-result' : ''}${d.destination ? ' gb-destination-marker' : ''}`), dot = el('span', 'gb-dot');
    dot.setAttribute('aria-hidden', 'true');
    const label = button(d.result ? String(d.order + 1) : d.label, () => {
      if (d.destination) {
        selectDestination(d);
      } else activate(d);
    }, 'gb-marker');
    label.setAttribute('aria-label', d.fullLabel || d.label);
    label.title = d.fullLabel || d.label;
    if (d.destination) {
      label.textContent = ''; label.append(el('span', 'gb-destination-name', d.label));
      if (d.has_model === false) label.append(el('span', 'gb-marker-note', 'No terrain model'));
      holder.dataset.shape = d.shape; holder.dataset.destination = d.id; holder.dataset.mode = d.mode;
      label.addEventListener('focus', () => { highlighted[d.mode] = d.id; updateDestinationMarks(); });
      label.addEventListener('blur', () => clearUnfocused(d.mode));
      dot.style.clipPath = `polygon(${shapeVertices(d.shape).map(([x, y]) => `${50 + x * 50}% ${50 + y * 50}%`).join(',')})`;
    }
    const stem = el('span', 'gb-stem'); stem.setAttribute('aria-hidden', 'true');
    holder.append(stem, dot, label); d.element = holder; d.button = label;
    const s = current();
    const chosen = d.destination ? d.id === (d.mode === 'moon' ? s.target : s.msite)
      : d.id === (d.mode === 'moon' ? s.place : s.msquare);
    holder.classList.toggle('gb-chosen', chosen); label.setAttribute('aria-pressed', String(chosen));
    const compact = root.getBoundingClientRect().width < 430;
    let dx = 0, dy = -23;
    if (!d.destination) {
      dx = (d.order % 2 ? 1 : -1) * (compact ? 65 : 92);
      dy = -90 + (d.order % 5) * 45;
    }
    d.offset = { dx, dy }; d.stem = stem;
    setLabel(d, dx, dy); scheduleLabels();
    return holder;
  }
  function setLabel(d, dx, dy) {
    d.button.style.left = `${dx}px`; d.button.style.top = `${dy}px`;
    d.stem.style.width = `${Math.hypot(dx, dy)}px`;
    d.stem.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
  }
  function scheduleLabels() {
    if (!alive || labelFrame) return;
    labelFrame = requestAnimationFrame(() => {
      labelFrame = 0;
      if (failed) return;
      for (const [panel, items] of [[moonPanel, moonMarkers], [marsPanel, marsMarkers], [earthPanel, earthPins]]) {
        const occupied = [], w = panel.host.clientWidth, h = panel.host.clientHeight;
        if (!panel.globe || !w || !h) continue;
        const visible = items.filter(d => d.button && d.element?.isConnected && !d.element.hidden);
        if (panel === earthPanel) {
          const top = Math.max(12, moonPanel.box.offsetHeight - panel.box.offsetTop + 14);
          const entries = visible.map(d => ({ d, point: panel.globe.getScreenCoords(d.lat, d.lon, .025) }))
            .sort((a, b) => a.point.x - b.point.x);
          const split = Math.ceil(entries.length / 2);
          for (const [column, list] of [entries.slice(0, split), entries.slice(split)].entries()) {
            list.sort((a, b) => a.point.y - b.point.y).forEach(({ d, point }, index) => {
              const bw = d.button.offsetWidth, bh = d.button.offsetHeight;
              const x = clamp(w * (column ? .76 : .24), bw / 2 + 5, w - bw / 2 - 5);
              const y = clamp(top + (h - top - 48) * (index + .5) / list.length, top + bh / 2, h - 48 - bh / 2);
              setLabel(d, x - point.x, y - point.y);
            });
          }
          continue;
        }
        for (const d of visible) {
          const point = panel.globe.getScreenCoords(d.lat, d.lon, .025);
          const bw = d.button.offsetWidth, bh = d.button.offsetHeight;
          const top = d.destination ? 35 : Math.max(12, moonPanel.box.offsetHeight - panel.box.offsetTop + 12);
          const bottom = d.destination ? 8 : 48;
          const x = clamp(point.x + d.offset.dx, bw / 2 + 5, w - bw / 2 - 5);
          let y = clamp(point.y + d.offset.dy, top + bh / 2, h - bottom - bh / 2);
          // Keep names legible when nearby pins share one part of the globe.
          const candidates = [y, y + bh + 5, y - bh - 5];
          for (let slot = top + bh / 2; slot <= h - bottom - bh / 2; slot += bh + 5) candidates.push(slot);
          for (const option of candidates) {
            const candidate = clamp(option, top + bh / 2, h - bottom - bh / 2);
            if (!occupied.some(r => Math.abs(x - r.x) < (bw + r.w) / 2 + 3 && Math.abs(candidate - r.y) < (bh + r.h) / 2 + 3)) {
              y = candidate; break;
            }
          }
          occupied.push({ x, y, w: bw, h: bh }); setLabel(d, x - point.x, y - point.y);
        }
      }
    });
  }
  const destinationMarkers = (list, mode) => list.map((s, order) => ({ ...s, lon: wrap(s.lon_east),
    label: s.name, fullLabel: s.name, shape: shapeOf(s, mode), destination: true, mode, order }));
  const moonMarkers = destinationMarkers(moonSites, 'moon'), marsMarkers = destinationMarkers(marsSites, 'mars');
  function visibleDestination(panel, d) {
    const view = panel.globe.pointOfView(), latitude = view.lat * RAD, longitude = view.lng * RAD;
    const facing = Math.sin(latitude) * Math.sin(d.lat * RAD) + Math.cos(latitude) * Math.cos(d.lat * RAD) * Math.cos(d.lon * RAD - longitude);
    return facing > 1 / (1 + view.altitude);
  }
  function buildDestinationMesh(panel, markers, selectedId) {
    // Reuse the Three constructors already owned by the local globe library.
    // All quiet marks share one geometry and one material, including their shapes.
    let sphere;
    panel.globe.scene().traverse(object => { if (object.isMesh && object.material === panel.globe.globeMaterial()) sphere = object; });
    if (!sphere) return;
    let prototype = Object.getPrototypeOf(sphere.geometry);
    while (prototype && !Object.prototype.hasOwnProperty.call(prototype, 'setAttribute')) prototype = Object.getPrototypeOf(prototype);
    if (!prototype) return;
    const Geometry = prototype.constructor, Attribute = sphere.geometry.getAttribute('position').constructor;
    const positions = [], normalize = vector => { const length = Math.hypot(...vector); return vector.map(value => value / length); };
    const coordinate = (lat, lon) => { const v = panel.globe.getCoords(lat, lon, .012); return [v.x, v.y, v.z]; };
    for (const d of markers.filter(item => item.id !== selectedId)) {
      const centre = coordinate(d.lat, d.lon), eastPoint = coordinate(d.lat, d.lon + .01), northPoint = coordinate(d.lat + .01, d.lon);
      const east = normalize(eastPoint.map((v, i) => v - centre[i])), north = normalize(northPoint.map((v, i) => v - centre[i]));
      const radius = panel.globe.getGlobeRadius() * (panel.body === 'moon' ? .0035 : .026);
      const vertices = shapeVertices(d.shape).map(([x, y]) => centre.map((value, i) => value + radius * (east[i] * x + north[i] * y)));
      for (let i = 0; i < vertices.length; i++) positions.push(...centre, ...vertices[i], ...vertices[(i + 1) % vertices.length]);
    }
    const geometry = new Geometry(); geometry.setAttribute('position', new Attribute(positions, 3)); geometry.computeVertexNormals();
    const material = panel.globe.globeMaterial().clone(); material.map = null; material.bumpMap = null;
    material.color.set(panel.body === 'moon' ? '#efc56e' : '#e89673'); material.emissive?.copy(material.color); material.emissiveIntensity = .7; material.side = 2;
    if (panel.markMesh) { panel.globe.scene().remove(panel.markMesh); panel.markMesh.geometry.dispose(); panel.markMesh.material.dispose(); }
    panel.markMesh = new sphere.constructor(geometry, material); panel.markMesh.name = 'destination-marks';
    panel.globe.scene().add(panel.markMesh);
    panel.box.dataset.mergedMarks = String(markers.filter(item => item.id !== selectedId).length);
  }
  function updateDestinationMarks() {
    if (!alive || failed) return;
    const s = current();
    for (const [panel, markers] of [[moonPanel, moonMarkers], [marsPanel, marsMarkers]]) {
      if (!panel.globe) continue;
      const selectedId = panel.body === 'moon' ? s.target : s.msite;
      if (panel.markSelection !== selectedId) { buildDestinationMesh(panel, markers, selectedId); panel.markSelection = selectedId; }
      const labels = markers.filter(d => d.id === selectedId || d.id === highlighted[panel.body]);
      const key = labels.map(d => d.id).join('|');
      if (panel.labelSelection !== key) { panel.globe.htmlElementsData(labels); panel.labelSelection = key; }
      for (const d of labels) { d.element?.classList.toggle('gb-chosen', d.id === selectedId); d.element?.classList.toggle('gb-highlight', d.id === highlighted[panel.body]); }
      panel.box.dataset.markCount = String(markers.length); panel.box.dataset.labelCount = String(labels.length);
    }
    scheduleLabels();
  }
  function wireDestinationGlobe(panel, markers) {
    const mode = panel.body;
    panel.host.tabIndex = 0; panel.host.setAttribute('aria-label', `${mode === 'moon' ? 'Lunar regions' : 'Mars sites'}. Use the arrow keys to read names. Press Enter to select.`);
    const nearest = event => {
      const bounds = panel.host.getBoundingClientRect(), x = event.clientX - bounds.left, y = event.clientY - bounds.top;
      let found = null, distance = 14;
      for (const d of markers) {
        if (!visibleDestination(panel, d)) continue;
        const point = panel.globe.getScreenCoords(d.lat, d.lon, .012), next = Math.hypot(point.x - x, point.y - y);
        if (next < distance) { found = d; distance = next; }
      }
      return found;
    };
    panel.host.addEventListener('pointermove', event => { const id = nearest(event)?.id || null; if (highlighted[mode] !== id) { highlighted[mode] = id; updateDestinationMarks(); } }, { signal: lifecycle.signal });
    panel.host.addEventListener('pointerleave', () => { if (document.activeElement !== panel.host) clearUnfocused(mode); }, { signal: lifecycle.signal });
    panel.host.addEventListener('click', event => { if (event.target.closest('.gb-marker')) return; const d = nearest(event); if (d) selectDestination(d); }, { signal: lifecycle.signal });
    panel.host.addEventListener('focus', () => { highlighted[mode] = (mode === 'moon' ? current().target : current().msite) || markers[0]?.id; updateDestinationMarks(); }, { signal: lifecycle.signal });
    panel.host.addEventListener('blur', () => clearUnfocused(mode), { signal: lifecycle.signal });
    panel.host.addEventListener('keydown', event => {
      if (event.target !== panel.host) return;
      if (!markers.length || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'Enter', ' '].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation(); stopRotation();
      const at = markers.findIndex(d => d.id === highlighted[mode]);
      if (event.key === 'Enter' || event.key === ' ') { const d = markers[Math.max(0, at)]; selectDestination(d); return; }
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? markers.length - 1 : (at + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -1 : 1) + markers.length) % markers.length;
      const d = markers[index]; highlighted[mode] = d.id;
      if (mode === 'mars') panel.globe.pointOfView({ lat: d.lat, lng: d.lon, altitude: 2.2 }, motion.matches ? 0 : 250);
      api.announce?.(d.name + (d.has_model === false ? '. No terrain model.' : '')); updateDestinationMarks();
    }, { signal: lifecycle.signal });
  }
  function markState() {
    const s = current();
    for (const d of [...moonMarkers, ...marsMarkers, ...pins]) {
      const chosen = d.destination ? d.id === (d.mode === 'moon' ? s.target : s.msite)
        : d.mode === 'moon' ? d.id === s.place : d.id === s.msquare;
      d.element?.classList.toggle('gb-chosen', chosen);
      d.button?.setAttribute('aria-pressed', String(chosen));
    }
    for (const menu of destinationMenus) for (const b of menu.rows.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.destination === (b.dataset.mode === 'moon' ? s.target : s.msite)));
    updateDestinationMarks(); scheduleLabels();
  }

  function fallback() {
    if (failed) return;
    failed = true; scene.hidden = true; status.textContent = UNAVAILABLE;
    wrapper.insertBefore(status, scene);
    wrapper.classList.add('gb-fallback');
    globes.forEach(g => { try { g.globe._destructor(); } catch { /* Keep the page usable. */ } });
    for (const { node, hidden } of oldNodes) node.hidden = hidden;
  }

  async function textureFor(body) {
    const item = textures?.images?.find(t => t.body.toLowerCase() === body);
    if (!item || !/^[a-z0-9_.-]+$/i.test(item.file) || !finite(item.centre_lon_deg)) return null;
    try {
      const response = await fetch(new URL(`./vendor/textures/${item.file}`, import.meta.url), { redirect: 'error' });
      if (!response.ok) return null;
      const url = URL.createObjectURL(await response.blob()); textureURLs.push(url);
      // Decode first so an invalid image cannot hold globe startup open.
      const image = new Image(); image.src = url; await image.decode();
      return { ...item, url };
    } catch { return null; }
  }

  try {
    const probe = document.createElement('canvas'), context = probe.getContext('webgl2');
    if (!context) throw new Error('WebGL unavailable.');
    context.getExtension('WEBGL_lose_context')?.loseContext();
    const Globe = await library();
    const pictures = await Promise.all(['earth', 'moon', 'mars'].map(textureFor));
    async function create(p, picture) {
      const globe = Globe({ animateIn: false, waitForGlobeReady: true,
        rendererConfig: { alpha: true, antialias: true } })(p.host);
      p.globe = globe; globes.push(p);
      globe.width(Math.max(1, p.host.clientWidth)).height(Math.max(1, p.host.clientHeight))
        .backgroundColor('rgba(0,0,0,0)').backgroundImageUrl(null).bumpImageUrl(null).globeTileEngineUrl(null)
        .showAtmosphere(p.body === 'earth').atmosphereColor('#8bc9d8').atmosphereAltitude(.1)
        .showGraticules(false).htmlLat('lat').htmlLng('lon').htmlAltitude(.025)
        .htmlElement(htmlMarker).htmlTransitionDuration(0)
        .htmlElementVisibilityModifier((node, visible) => { node.hidden = !visible; })
        .pointsMerge(true).pointsTransitionDuration(0).pointResolution(5)
        .pointLat('lat').pointLng('lon').pointColor('color').pointAltitude('height').pointRadius('radius');
      globe.renderer().setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      const material = globe.globeMaterial(), color = material.color.clone();
      const baseColor = p.body === 'earth' ? '#142a35' : p.body === 'moon' ? '#8a8881' : '#9e5d43';
      color.set(picture ? (p.body === 'earth' ? '#a2a8b3' : '#ffffff') : baseColor);
      material.color = color; material.shininess = p.body === 'earth' ? 6 : 0;
      await new Promise(resolve => {
        globe.onGlobeReady(() => {
          material.color = color;
          globe.scene().traverse(obj => {
            if (obj.isMesh && obj.material === material) obj.rotation.y = -Math.PI / 2 + (picture?.centre_lon_deg || 0) * RAD;
          });
          resolve();
        }).globeImageUrl(picture?.url || null);
      });
      if (p.body === 'earth' && !picture) {
        const style = getComputedStyle(wrapper);
        const landColor = style.getPropertyValue('--land').trim() || '#40544d';
        const coastColor = style.getPropertyValue('--coast').trim() || '#7b8c80';
        globe.polygonsData(landFeatures(land)).polygonCapColor(() => landColor).polygonSideColor(() => landColor)
          .polygonStrokeColor(() => coastColor).polygonAltitude(.002).polygonsTransitionDuration(0);
      }
      const c = globe.controls(); c.enableZoom = false; c.enablePan = false; c.autoRotateSpeed = .22;
      globe.onZoom(scheduleLabels);
      c.autoRotate = !motion.matches && !touched; c.enableDamping = !motion.matches;
      p.host.addEventListener('pointerdown', () => { c.enableZoom = true; }, { signal: lifecycle.signal });
      const release = () => { c.enableZoom = false; };
      window.addEventListener('pointerup', release, { signal: lifecycle.signal });
      window.addEventListener('pointercancel', release, { signal: lifecycle.signal });
      window.addEventListener('blur', release, { signal: lifecycle.signal });
      globe.renderer().domElement.addEventListener('webglcontextlost', event => { event.preventDefault(); fallback(); }, { signal: lifecycle.signal });
      return globe;
    }
    earth = await create(earthPanel, pictures[0]);
    moonGlobe = await create(moonPanel, pictures[1]);
    marsGlobe = await create(marsPanel, pictures[2]);
    const polarExtent = Math.max(1, ...moonMarkers.map(d => 90 + d.lat));
    const lunarAltitude = Math.max(.18, Math.sin(polarExtent * RAD) * 1.25 * Math.max(1, moonPanel.host.clientHeight / moonPanel.host.clientWidth) / Math.tan(moonGlobe.camera().fov * RAD / 2));
    moonGlobe.pointOfView({ lat: -90, lng: 0, altitude: lunarAltitude }, 0);
    const firstMars = marsMarkers.find(d => d.id === current().msite) || marsMarkers[0];
    marsGlobe.pointOfView({ lat: firstMars?.lat || 0, lng: firstMars?.lon || 0, altitude: 2.2 }, 0);
    wireDestinationGlobe(moonPanel, moonMarkers); wireDestinationGlobe(marsPanel, marsMarkers);
    updateDestinationMarks();
    earth.onGlobeClick(({ lat, lng }) => surfacePress(lat, lng));
    // A texture-free outline can receive the ray before the sphere does.
    earth.onPolygonClick((_polygon, _event, coordinate) => {
      if (coordinate) surfacePress(coordinate.lat, coordinate.lng);
    });
    for (const { node } of oldNodes) node.hidden = true;
    root.dataset.gbReady = 'true';
    status.textContent = 'Select a destination. Drag the Earth to turn it. Use + or − to change its size.';
    if (!pictures[0] && land?.limit_deg) status.append(` The land outline starts at ${num(land.limit_deg)}° north and south.`);
    resizeObserver = new ResizeObserver(() => {
      if (!alive || failed) return;
      for (const p of globes) {
        const w = p.host.clientWidth, h = p.host.clientHeight;
        if (w && h) p.globe.width(w).height(h);
      }
      scheduleLabels();
      clearTimeout(labelResizeTimer); labelResizeTimer = setTimeout(scheduleLabels, 100);
    });
    globes.forEach(p => resizeObserver.observe(p.host));
    visibilityObserver = new IntersectionObserver(entries => {
      for (const entry of entries) { const p = globes.find(g => g.host === entry.target); if (p) p.visible = entry.isIntersecting; }
      syncAnimation();
    });
    globes.forEach(p => visibilityObserver.observe(p.host));
  } catch { fallback(); }

  function syncAnimation() {
    if (failed || !alive) return;
    for (const p of globes) {
      const active = p.visible && !document.hidden && current().stage !== 'flat';
      p.globe.controls().autoRotate = !touched && !motion.matches;
      p.globe.controls().enableDamping = !motion.matches;
      if (active) p.globe.resumeAnimation(); else p.globe.pauseAnimation();
    }
    clearTimeout(labelResizeTimer); labelResizeTimer = setTimeout(scheduleLabels, 100);
  }
  document.addEventListener('visibilitychange', syncAnimation, { signal: lifecycle.signal });
  motion.addEventListener('change', syncAnimation, { signal: lifecycle.signal });

  function surfacePress(lat, lon) {
    const s = current();
    if (s.dest === 'mars') {
      const half = mars?.meta?.square_deg / 2;
      const found = squares.find(a => lat >= a.lat - half && lat < a.lat + half && wrap(lon - a.lon) >= -half && wrap(lon - a.lon) < half);
      if (found) activate({ ...found, mode: 'mars' });
      return;
    }
    // A short angular hit radius prevents an ocean click from selecting distant land.
    let nearest = null, distance = .35 * RAD;
    for (const a of areas) {
      if (Math.abs(a.lat - lat) > .35) continue;
      const h = Math.sin((a.lat - lat) * RAD / 2) ** 2 + Math.cos(lat * RAD) * Math.cos(a.lat * RAD)
        * Math.sin(wrap(a.lon - lon) * RAD / 2) ** 2;
      const d = 2 * Math.asin(Math.sqrt(clamp(h, 0, 1)));
      if (d < distance) { nearest = a; distance = d; }
    }
    if (nearest) activate({ ...nearest, mode: 'moon' });
  }

  function showPins(s) {
    const all = pins.slice();
    selected = s.dest === 'moon' ? areas.find(a => a.id === s.place) : squareById.get(s.msquare);
    if (selected && !all.some(p => p.id === selected.id)) all.push({ ...selected, mode: s.dest,
      label: s.dest === 'moon' ? nameArea(selected) : nameSquare(selected), order: all.length });
    earthPins = all;
    if (!failed) earth?.htmlElementsData(all);
    // Include the extra selected pin in the same state marks.
    for (const p of all) {
      const chosen = p.id === (s.dest === 'moon' ? s.place : s.msquare);
      p.element?.classList.toggle('gb-chosen', chosen); p.button?.setAttribute('aria-pressed', String(chosen));
    }
  }

  function renderPlaces() {
    places.replaceChildren(...pins.map((pin, i) => {
      const item = el('li', 'gb-place'); item.hidden = !showAllPlaces && i >= 5;
      const name = pin.listLabel || pin.label;
      item.append(button(pin.result ? `${i + 1}. ${name}` : name, () => activate(pin), 'gb-place-button'));
      return item;
    }));
    morePlaces.hidden = pins.length <= 5;
    morePlaces.textContent = showAllPlaces ? 'Show less' : 'Show all';
    morePlaces.setAttribute('aria-expanded', String(showAllPlaces));
  }

  function render(rawState) {
    if (!alive) return;
    const s = stateOf(rawState), request = ++scoreRequest;
    wrapper.dataset.dest = s.dest;
    globeButton.setAttribute('aria-pressed', String(s.stage !== 'flat'));
    flatButton.setAttribute('aria-pressed', String(s.stage === 'flat'));
    scene.hidden = failed || s.stage === 'flat';
    moonPanel.box.classList.toggle('gb-inactive', s.dest !== 'moon');
    marsPanel.box.classList.toggle('gb-inactive', s.dest !== 'mars');
    poleControls.hidden = s.dest !== 'moon';
    syncAnimation();
    if (s.dest === 'mars' && readSquare) {
      const column = mars.squares.columns[`sites.${s.msite}.${s.mgoal}`];
      const file = column && (column.file || mars.squares.file);
      if (file && !squareBuffers.has(file)) {
        working.hidden = false;
        if (squareFailed.has(file)) {
          working.textContent = 'The scores for this site are unknown. The data file is unavailable.';
          wrapper.removeAttribute('aria-busy');
        } else {
          working.textContent = 'Working'; wrapper.setAttribute('aria-busy', 'true');
          loadSquareFile(file).then(() => { if (alive && request === scoreRequest) render(api.getState()); });
        }
        return;
      }
    }
    working.hidden = true; wrapper.removeAttribute('aria-busy');
    const answer = api.answer?.(s.target) || [];
    const key = [s.dest, s.target, s.step, s.msite, s.mgoal, api.theme(), JSON.stringify(answer), matchVersion].join('|');
    const activeMatches = matches?.mode === s.dest ? matches : null;
    if (key !== dataKey) {
      const ramp = palette(wrapper, s.dest); points = []; pins = []; let unknown = 0, minimum = Infinity, maximum = -Infinity;
      let title, scaleMin = 0, scaleMax, note;
      if (s.dest === 'moon') {
        title = api.targets.find(t => t.id === s.target)?.name || 'Lunar region';
        const values = areas.map(a => ({ ...a, value: api.hours(a.area, s.target, s.step, 'year') }));
        scaleMax = finite(meta?.scale?.year_h) ? meta.scale.year_h : Math.max(0, ...values.map(a => finite(a.value) ? a.value : 0));
        for (const a of values) {
          if (!finite(a.value)) { unknown++; continue; }
          if (a.value <= 0) continue;
          minimum = Math.min(minimum, a.value); maximum = Math.max(maximum, a.value);
          const ratio = scaleMax > 0 ? clamp(a.value / scaleMax, 0, 1) : 0;
          points.push({ ...a, color: ramp(ratio), height: .004 + .19 * ratio, radius: .13 });
        }
        for (const row of answer) {
          const a = api.area(row.area);
          if (a && finite(a.lat) && finite(a.lon)) pins.push({ ...a, mode: 'moon', label: a.named || a.region || a.id,
            listLabel: nameArea(a), fullLabel: `${row.label}: ${nameArea(a)}`, order: pins.length });
        }
        note = `${num(unknown)} ${unknown === 1 ? 'area has' : 'areas have'} unknown hours. The height of each column also shows the hours.`;
      } else {
        title = marsSites.find(t => t.id === s.msite)?.name || 'Mars site';
        [scaleMin, scaleMax] = mars?.meta?.score_scale || [null, null];
        for (const a of squares) {
          const value = readSquare(`sites.${s.msite}.${s.mgoal}`, a.index);
          if (!finite(value)) { unknown++; continue; }
          minimum = Math.min(minimum, value); maximum = Math.max(maximum, value);
          points.push({ ...a, value, color: ramp(scaleMax > scaleMin ? (value - scaleMin) / (scaleMax - scaleMin) : 0), height: 0,
            radius: finite(mars?.meta?.square_deg) ? mars.meta.square_deg / 2 : .2 });
        }
        for (const row of mars?.best_places?.[s.msite]?.[s.mgoal] || []) {
          if (finite(row.lat) && finite(row.lon)) pins.push({ ...row, mode: 'mars', label: row.region || row.id,
            listLabel: nameSquare(row), fullLabel: nameSquare(row), order: pins.length });
        }
        note = readSquare ? `${num(unknown)} ${unknown === 1 ? 'square has' : 'squares have'} unknown scores. ${squareSize()}.` : 'The square scores are unknown. The data file is unavailable.';
      }
      const normalCount = points.length;
      let matched = [];
      if (activeMatches) {
        const byIndex = s.dest === 'mars' ? squareByIndex : areaByIndex, seen = new Set();
        for (const index of activeMatches.areas || []) {
          const a = Number.isInteger(index) ? byIndex.get(index) : null;
          if (!a || seen.has(index)) continue;
          seen.add(index); matched.push(a);
        }
        pins = matched.slice(0, 10).map((a, order) => ({ ...a, mode: s.dest, result: true, order,
          label: s.dest === 'moon' ? nameArea(a) : nameSquare(a),
          listLabel: s.dest === 'moon' ? nameArea(a) : nameSquare(a),
          fullLabel: `${order + 1}. ${s.dest === 'moon' ? nameArea(a) : nameSquare(a)}` }));
        // The merged base layer stays visible, while result points have their own bright colour.
        points = points.map(p => ({ ...p, color: '#344356', height: .002, radius: p.radius * .65 }));
        points.push(...matched.map(a => ({ ...a, color: '#b6f3ff', height: .008, radius: .22 })));
      }
      wrapper.classList.toggle('gb-has-matches', !!activeMatches);
      if (!failed) earth?.pointsData(points);
      const rampBar = el('span', 'gb-ramp'); rampBar.style.background = `linear-gradient(90deg, ${ramp(0)}, ${ramp(1)})`;
      const scaleText = s.dest === 'moon' ? `${num(scaleMin)}–${num(scaleMax)}+ hours in a year · step ${num(s.step)}`
        : `${num(scaleMin, 0)}–${num(scaleMax, 0)} score · ${{ full: 'All factors', landscape: 'Landscape', environment: 'Environment' }[s.mgoal]}`;
      const resultLegend = pins.length ? `Rings + numbers: first ${num(pins.length)} · bright points: other matches`
        : 'No places match · dim points: normal layer';
      legend.replaceChildren(...(activeMatches ? [el('span', 'gb-result-key', '◉'), el('span', 'gb-scale', resultLegend)]
        : [rampBar, el('span', 'gb-scale', scaleText)]));
      if (s.dest === 'mars') legend.append(el('span', 'gb-first-pass', squareSize()));
      unknownNote.textContent = note;
      const range = finite(minimum) ? `${num(minimum, s.dest === 'moon' ? 1 : 4)}–${num(maximum, s.dest === 'moon' ? 1 : 4)}` : 'unknown';
      description.textContent = `${title}. ${num(normalCount)} ${s.dest === 'moon' ? 'area' : 'square'}${normalCount === 1 ? '' : 's'} on the Earth ${normalCount === 1 ? 'has' : 'have'} `
        + (s.dest === 'moon' ? `hours of low Sun at step ${num(s.step)}. Hours in a year: ${range}.` : `a known score. Scores: ${range}. ${squareSize()}.`);
      summary.textContent = activeMatches
        ? (activeMatches.label || `${title}: ${num(matched.length)} ${s.dest === 'moon' ? 'areas' : 'squares'} match the criteria.`)
        : `${title}: ${num(normalCount)} ${s.dest === 'moon' ? 'areas with low Sun' : 'squares with a known score'}.`;
      summary.title = summary.textContent;
      renderPlaces();
      dataKey = key;
    }
    showPins(s); markState();
    const destinationChanged = !previous || s.dest !== previous.dest || s.target !== previous.target || s.msite !== previous.msite || s.mgoal !== previous.mgoal;
    const placeChanged = !previous || s.place !== previous.place || s.msquare !== previous.msquare;
    const resultsChanged = shownMatchVersion !== matchVersion;
    const focus = resultsChanged && activeMatches ? pins[0] : placeChanged && selected ? selected : destinationChanged ? pins[0] : null;
    if (focus) turn(focus.lat, focus.lon, earthAltitude(), previous ? 1200 : 0);
    if (!failed && marsGlobe && (!previous || s.msite !== previous.msite || s.dest === 'mars' && previous.dest !== 'mars')) {
      const site = marsMarkers.find(d => d.id === s.msite);
      if (site) marsGlobe.pointOfView({ lat: site.lat, lng: site.lon, altitude: 2.2 }, motion.matches || !previous ? 0 : 1200);
    }
    shownMatchVersion = matchVersion; previous = { ...s }; syncAnimation();
  }
  render(api.getState());
  // The restore hook renders after the saved state and Ask matches are both back.
  // A module mounted during a tour has no snapshot and still renders normally.
  const restoringTour = () => tourSnapshotActive && document.body.classList.contains('tl-tour-restoring');
  const off = api.onState(state => { if (!restoringTour()) render(state); }); if (typeof off === 'function') cleanups.push(off);
  if (typeof api.onMatches === 'function') {
    const offMatches = api.onMatches(value => {
      matches = value; matchVersion++; showAllPlaces = false;
      if (!restoringTour()) render(api.getState());
    });
    if (typeof offMatches === 'function') cleanups.push(offMatches);
  }
  // Shared state restores the data; these local values restore the reader's
  // camera positions and controls after the tour changes destinations.
  const tourActions = {
    snapshot() {
      tourSnapshotActive = true;
      return { touched, selected, showAllPlaces, highlighted: { ...highlighted }, aboutOpen: about.open, lunarOpen: lunarChoices.open,
        menus: destinationMenus.map(menu => ({ open: menu.fold.open, filter: menu.input.value })),
        cameras: failed ? [] : globes.map(p => ({ body: p.body, view: { ...p.globe.pointOfView() } })) };
    },
    restore(saved) {
      if (!alive || !saved) return;
      tourSnapshotActive = false;
      render(api.getState());
      touched = saved.touched; selected = saved.selected; showAllPlaces = saved.showAllPlaces; highlighted = saved.highlighted || { moon: null, mars: null };
      about.open = saved.aboutOpen;
      destinationMenus.forEach((menu, i) => {
        const state = saved.menus?.[i] || (i === 0 ? { open: saved.lunarOpen, filter: menu.input.value } : null);
        if (!state) return;
        if (menu.fold.open !== state.open) { menu.skipToggle = true; menu.fold.open = state.open; }
        menu.input.value = state.filter; menu.filter();
      });
      renderPlaces();
      if (!failed) for (const camera of saved.cameras) {
        const p = globes.find(item => item.body === camera.body);
        // A zero-duration move also ends an unfinished tour camera animation.
        if (p) p.globe.pointOfView(camera.view, 0);
      }
      updateDestinationMarks(); syncAnimation(); scheduleLabels();
    },
  };
  root.tourActions = tourActions;
  return { destroy() {
    if (!alive) return; alive = false; lifecycle.abort(); cleanups.forEach(fn => fn());
    if (root.tourActions === tourActions) delete root.tourActions;
    cancelAnimationFrame(labelFrame); clearTimeout(labelResizeTimer);
    resizeObserver?.disconnect(); visibilityObserver?.disconnect();
    for (const p of globes) { p.markMesh?.geometry.dispose(); p.markMesh?.material.dispose(); }
    if (!failed) globes.forEach(p => { try { p.globe._destructor(); } catch { /* Already disposed. */ } });
    textureURLs.forEach(url => URL.revokeObjectURL(url)); wrapper.remove(); delete root.dataset.gbReady;
    for (const { node, hidden } of oldNodes) node.hidden = hidden;
  } };
}
