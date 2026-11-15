// Earth Twin Finder: one module, no dependencies. Every number shown is read from data/*.
// The map squares are called "areas" on the page (the data files still say "cells").
// State lives in the URL fragment, for example
//   #view=arctic&step=2&period=summer&go=map

const NB = 36;
const $ = (id) => document.getElementById(id);
const D = {};                       // the data files
const S = { view: 'arctic', target: null, step: null, period: 'year', bin: 21, place: null, little: false,
  dest: 'moon', msite: '', mgoal: 'full', msquare: '', stage: 'globe',
  tab: 'summer', tab2: 'best', theme: 'dark', z: 1, x: 0, y: 0, go: null, only: null, moon: null, filters: '', order: null };
const DEFAULT_STATE = structuredClone(S);
const STATE_KEYS = new Set(Object.keys(S));
const stateListeners = new Set();
let restoringView = false;
const matchListeners = new Set();
let matches = null, matchesDestination = '', planTab = 'rehearse';
function deliverMatches(fn) {
  try { Promise.resolve(fn(matches && structuredClone(matches))).catch(() => {}); } catch { /* Keep other subscribers usable. */ }
}
function setMatches(value) {
  let next = null;
  if (value && value.mode === S.dest && Array.isArray(value.areas) && Array.isArray(value.scores)) {
    const count = value.mode === 'mars' ? answerData.mars?.squares?.count : D.n;
    if (value.areas.length === value.scores.length && value.areas.every((i) => Number.isInteger(i) && i >= 0 && (count == null || i < count))
      && value.scores.every((n) => Number.isFinite(n) && n >= 0 && n <= 1)) {
      next = { label: String(value.label || ''), areas: [...value.areas], scores: [...value.scores], mode: value.mode };
    }
  }
  if (JSON.stringify(matches) === JSON.stringify(next)) return;
  matches = next;
  for (const fn of [...matchListeners]) deliverMatches(fn);
  if (D.ready) { renderExperimentResults(); drawMap(); drawStage(); refreshMarsMatches(); }
}
let lastState = '', centreOnPlace = false;
const stateCopy = () => structuredClone(S);
const sectionFor = (id) => id === 'ask' ? $(S.tab2 === 'words' ? 'ask-words' : 'ask-root') : $(id + '-section') || $(id + '-root') || $(id);
function notifyState(force = false) {
  const now = JSON.stringify([S, isDark()]);
  if (!force && now === lastState) return;
  lastState = now;
  const mars = $('mars-root')?.querySelector('[data-theme]');
  if (mars) mars.dataset.theme = isDark() ? 'dark' : 'light';
  for (const fn of [...stateListeners]) {
    try { Promise.resolve(fn(stateCopy())).catch(() => {}); } catch { /* A module callback cannot stop the page. */ }
  }
}
const NUM = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const STEPS = [
  { n: 1, name: 'Sun only', tiny: 'Sun', small: 'flat horizon' },
  { n: 2, name: 'Snow-free ground', tiny: 'Snow-free', small: 'without snow hours' },
  { n: 3, name: 'Terrain', tiny: 'Terrain', small: 'without the hours that hills hide' },
  { n: 4, name: 'Typical cloud', tiny: 'Cloud', small: 'without cloud hours' },
];
const LON0 = -40;                   // meridian at the bottom of the Arctic view
const CELL_UNIT = 0.00185;          // a cell of 0.1 degrees of latitude in map units
const nf = new Intl.NumberFormat('en-US');

// ---------- small helpers ----------
const words = (n) => (Number.isInteger(n) && n >= 0 && n < NUM.length ? NUM[n] : String(n));
const fInt = (x) => Number.isFinite(x) ? nf.format(Math.round(x)) : 'unknown';
const fH = (x) => (x == null || Number.isNaN(x) ? 'unknown' : x > 0 && x < 9.95 ? (Math.round(x * 10) / 10).toFixed(1) : fInt(x));
const fPct = (x) => (x == null || !Number.isFinite(x) ? 'unknown' : (x > 0 && x < 0.0995) || (x > 0.9005 && x < 1) ? (x * 100).toFixed(1) + '%' : Math.round(x * 100) + '%');
const fLat = (v) => Math.abs(v).toFixed(2) + '° ' + (v >= 0 ? 'N' : 'S');
const fLon = (v) => Math.abs(v).toFixed(2) + '° ' + (v >= 0 ? 'E' : 'W');
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sum = (a) => a?.some(Number.isFinite) ? a.reduce((p, v) => p + (Number.isFinite(v) ? v : 0), 0) : NaN;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const isDark = () => S.theme !== 'light';
const target = () => D.meta.targets.find((t) => t.id === S.target) || D.meta.targets[0];
const tIndex = () => D.meta.targets.findIndex((t) => t.id === S.target);
const north = () => S.view !== 'antarctic';
const binLabel = (b) => D.meta.bins[b].label.replace('-', ' to ');
const stepName = (n) => (n === 2 && !north() ? 'Rock season only' : STEPS[n - 1].name);
const stepSmall = (n) => (n === 2 && !north() ? 'snow not measured' : STEPS[n - 1].small);
const stepTitle = (n) => (n === 1 ? 'Sun only' : n === 2 ? (north() ? 'snow-free ground' : 'rock season only') : n === 3 ? 'after terrain' : 'typical cloud');
const DRAWN = 'Drawn by code from open data; the code was written with AI assistance.';
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const areasN = (n) => `${fInt(n)} ${n === 1 ? 'area' : 'areas'}`;
const halfLevel = () => (D.meta.scoring.full_hours ? D.meta.scoring.full_hours / 2 : 100);
const defaultTarget = () => {
  const current = D.meta.targets.filter((t) => lunarListGroup(t) === 'NASA 2024 list').sort((a, b) => a.limit_deg - b.limit_deg);
  return current[0]?.id || D.meta.targets.find((t) => t.id === 'malapert')?.id || D.meta.targets[0]?.id;
};
const hasLunarModel = (t = target()) => t?.has_model !== false;
const NO_LUNAR_MODEL = 'unknown: NASA has no 5 m terrain model of this region';
const hardest = () => D.meta.targets.reduce((a, t) => (t.limit_deg < a.limit_deg ? t : a), D.meta.targets[0]);   // the lowest Sun

function niceCeil(v) {
  const steps = [5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000];
  return steps.find((s) => s >= v) || Math.ceil(v / 500) * 500;
}
function quantile(values, q) {
  if (!values.length) return 0;
  const a = Float64Array.from(values).sort();
  return a[Math.min(a.length - 1, Math.floor(q * (a.length - 1)))];
}
function oklch(L, C, h) {
  const hr = (h * Math.PI) / 180, a = C * Math.cos(hr), b = C * Math.sin(hr);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3,
    s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const f = (x) => { x = Math.min(1, Math.max(0, x)); return Math.round(255 * (x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055)); };
  return `rgb(${f(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s)},${f(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s)},${f(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s)})`;
}
// One ramp for hours, one hue family (straw to brown, or brown to yellow in the dark theme): lightness runs one
// way only, so it survives colour blindness and grey print. colours[0] is for zero hours: visible but quiet.
// colours[1] is the weakest filled mark. It is pale on purpose, so that a place with a few hours looks nearly
// empty: its contrast against the land colour is 1.4 (light) and 1.6 (dark). Lightness is linear in hours; the
// colour itself builds up over the first third of the scale.
function ramp() {
  const dark = isDark(), out = [dark ? oklch(0.37, 0.012, 70) : oklch(0.86, 0.012, 85)];
  for (let i = 1; i < 64; i++) {
    const t = (i - 1) / 62;
    const c = 0.03 + 0.1 * Math.min(1, t / 0.3);
    out.push(dark ? oklch(0.42 + 0.51 * t, c, 55 + 37 * t) : oklch(0.83 - 0.5 * t, c, 88 - 40 * t));
  }
  return out;
}

// ---------- state in the URL fragment ----------
function readHash() {
  cancelNavigation();
  clearTimeout(hashTimer);
  const p = new URLSearchParams(location.hash.replace(/^#/, ''));
  for (const key of Object.keys(S)) if (!STATE_KEYS.has(key)) delete S[key];
  for (const [key, value] of p) if (!STATE_KEYS.has(key) && !['__proto__', 'constructor', 'prototype'].includes(key)) {
    try { S[key] = value.startsWith('~') ? JSON.parse(value.slice(1)) : value; } catch { S[key] = value; }
  }
  const ids = D.meta.targets.map((t) => t.id);
  S.view = p.get('view') === 'antarctic' ? 'antarctic' : 'arctic';
  S.target = ids.includes(p.get('target')) ? p.get('target') : defaultTarget();
  const step = parseInt(p.get('step'), 10);
  S.step = step >= 1 && step <= 4 ? step : null;
  const per = p.get('period');
  if (per && /^\d+$/.test(per) && +per < NB) { S.period = 'bin'; S.bin = +per; }
  else S.period = ['year', 'winter', 'summer', 'rock'].includes(per) ? per : 'year';
  S.place = p.get('place') || null;
  centreOnPlace = !!S.place && !p.has('x') && !p.has('y');
  S.little = p.get('little') === '1';
  S.tab = p.get('tab') || 'summer';
  S.tab2 = p.get('tab2') || (p.get('go') === 'ask' || p.get('only') === 'ask' ? 'words' : p.has('ask') ? 'make' : 'best');
  planTab = p.get('only') === 'tools' || p.get('go') === 'tools' ? 'tools' : p.get('go') === 'pl-compare' ? 'compare' : p.get('go') === 'pl-year' ? 'year' : 'rehearse';
  S.theme = p.get('theme') === 'light' ? 'light' : 'dark';
  S.dest = p.get('dest') || (p.get('go')?.startsWith('mars') || p.get('only')?.startsWith('mars') ? 'mars' : 'moon');
  S.msite = p.get('msite') || ''; S.mgoal = p.get('mgoal') || 'full';
  S.msquare = p.get('msquare') || ''; S.stage = p.get('stage') || 'globe';
  S.z = Math.min(60, Math.max(1, parseFloat(p.get('z')) || 1));
  S.x = (parseFloat(p.get('x')) || 0) / 1000;
  S.y = (parseFloat(p.get('y')) || 0) / 1000;
  S.go = p.get('go');
  S.only = p.get('only');   // show one section alone (for slides and screenshots)
  S.moon = ids.includes(p.get('moon')) ? p.get('moon') : null;   // an open lunar region card
  S.filters = p.get('filters') || '';
  S.order = p.get('order');
  fixState();
}
function fixState() {
  if (!D.meta.targets.some((t) => t.id === S.target)) S.target = defaultTarget();
  S.view = S.view === 'antarctic' ? 'antarctic' : 'arctic';
  S.step = [1, 2, 3, 4].includes(+S.step) ? +S.step : defaultStep();
  S.little = S.little === true || S.little === 1 || S.little === '1';
  S.theme = S.theme === 'light' ? 'light' : 'dark';
  S.dest = S.dest === 'mars' ? 'mars' : 'moon';
  S.mgoal = ['full', 'landscape', 'environment'].includes(S.mgoal) ? S.mgoal : 'full';
  S.stage = S.stage === 'flat' ? 'flat' : 'globe';
  S.tab2 = ['best', 'make', 'words'].includes(S.tab2) ? S.tab2 : 'best';
  const marsSites = answerData.mars?.sites;
  if (marsSites?.length && !marsSites.some((site) => site.id === S.msite)) S.msite = marsSites[0].id;
  S.msquare = typeof S.msquare === 'string' ? S.msquare : ''; 
  S.moon = D.meta.targets.some((t) => t.id === S.moon) ? S.moon : null;
  if (!['winter', 'belt', 'summer', 'famous', 'antarctica'].includes(S.tab)) S.tab = 'summer';
  if (/^\d+$/.test(String(S.period)) && +S.period < NB) { S.bin = +S.period; S.period = 'bin'; }
  if (!['year', 'winter', 'summer', 'rock', 'bin'].includes(S.period)) S.period = 'year';
  S.bin = Math.min(NB - 1, Math.max(0, Math.floor(+S.bin || 0)));
  S.z = Math.min(60, Math.max(1, +S.z || 1));
  S.x = Number.isFinite(+S.x) ? +S.x : 0; S.y = Number.isFinite(+S.y) ? +S.y : 0;
  if (D.ready && centreOnPlace) {
    const i = D.idx.get(S.place);
    if (i != null) {
      S.view = D.isN[i] ? 'arctic' : 'antarctic';
      [S.x, S.y] = proj(D.lat[i], D.lon[i], !!D.isN[i]);
      if (S.z <= 1.01) S.z = 5;
    }
    centreOnPlace = false;
  }
  if (north() && S.period === 'rock') S.period = 'year';
  if (!north() && (S.period === 'winter' || S.period === 'summer')) S.period = 'year';
  if (S.step === 4 && !D.meta.has_cloud) S.step = 3;
  if (S.step == null) S.step = defaultStep();
  document.documentElement.dataset.theme = S.theme;
  document.documentElement.dataset.dest = S.dest;
  const destination = [S.dest, S.target, S.msite].join(':');
  if (matchesDestination !== destination) { matchesDestination = destination; setMatches(null); }
  updateVisibility();
}
function defaultStep() {
  const c = D.meta.counts;
  return c.with_horizon_north >= 0.9 * c.north_cells ? 3 : 2;
}
let hashTimer = 0;
function hashString() {   // the present view as a URL fragment (without the #)
  const p = new URLSearchParams();
  p.set('view', S.view); p.set('target', S.target); p.set('step', S.step);
  p.set('period', S.period === 'bin' ? String(S.bin) : S.period);
  if (S.place) p.set('place', S.place);
  if (S.little) p.set('little', '1');
  if (S.tab !== 'summer') p.set('tab', S.tab);
  p.set('tab2', S.tab2);
  p.set('theme', S.theme);
  p.set('dest', S.dest); if (S.msite) p.set('msite', S.msite);
  p.set('mgoal', S.mgoal); if (S.msquare) p.set('msquare', S.msquare);
  p.set('stage', S.stage);
  if (S.only) p.set('only', S.only);
  if (S.moon) p.set('moon', S.moon);
  if (S.go) p.set('go', S.go);
  if (S.filters) p.set('filters', S.filters);
  if (S.order != null) p.set('order', S.order);
  if (S.z > 1.01 || S.x || S.y) { p.set('z', S.z.toFixed(2)); p.set('x', Math.round(S.x * 1000)); p.set('y', Math.round(S.y * 1000)); }
  for (const [key, value] of Object.entries(S)) if (!STATE_KEYS.has(key) && value != null) {
    p.set(key, typeof value === 'string' && !value.startsWith('~') ? value : '~' + JSON.stringify(value));
  }
  return p.toString();
}
function writeHash(immediate = false) {
  clearTimeout(hashTimer);
  const write = () => history.replaceState(null, '', '#' + hashString());
  if (immediate) write(); else hashTimer = setTimeout(write, 120);
  queueMicrotask(() => notifyState());
}
// The buttons are drawn again after every change; keep the keyboard focus on the one that was pressed.
function focusKey() {
  const a = document.activeElement;
  if (!a || a === document.body || !a.dataset) return null;
  const name = ['pickTarget', 'pickMsite', 'answerPlace', 'answerSquare'].find((key) => key in a.dataset) || Object.keys(a.dataset)[0], host = a.parentElement && a.parentElement.closest('[id]');
  return name && host ? { host: host.id, sel: `${a.tagName.toLowerCase()}[data-${name.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())}="${a.dataset[name]}"]` } : null;
}
function set(patch, opts = {}) {
  const key = focusKey();
  if ('go' in patch) cancelNavigation();
  for (const [name, value] of Object.entries(patch)) if (!['__proto__', 'constructor', 'prototype'].includes(name)) S[name] = structuredClone(value);
  if (patch.place && !('x' in patch) && !('y' in patch)) centreOnPlace = true;
  fixState();
  writeHash(true);
  renderAll(opts);
  notifyState();
  if ('go' in patch && S.go) goToSection(S.go);
  if (key && document.activeElement === document.body) {
    const again = $(key.host) && $(key.host).querySelector(key.sel);
    if (again) again.focus({ preventScroll: true });
  }
}

// ---------- loading ----------
const fileCache = new Map(), jsonCache = new Map();
function dataName(name) {
  if (typeof name !== 'string' || !/^[\w.-]+(?:\/[\w.-]+)*$/.test(name) || name.split('/').some((part) => part === '.' || part === '..')) {
    throw new Error('Use a file name inside data.');
  }
  return name;
}
function getBin(name) {
  try {
    const f = dataName(name);
    if (!fileCache.has(f)) fileCache.set(f, (async () => {
      const canInflate = typeof DecompressionStream === 'function';
      let r = canInflate ? await fetch('data/' + f + '.gz', { redirect: 'error' }) : null;
      if (!r?.ok) r = await fetch('data/' + f, { redirect: 'error' });
      if (!r.ok) throw new Error(f + ': ' + r.status);
      const buffer = await r.arrayBuffer(), bytes = new Uint8Array(buffer);
      // A host can decode Content-Encoding before these bytes reach the page.
      if (canInflate && bytes[0] === 0x1f && bytes[1] === 0x8b) {
        return new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      }
      return buffer;
    })());
    return fileCache.get(f);
  } catch (error) { return Promise.reject(error); }
}
function getJSON(name) {
  try {
    const f = dataName(name);
    if (!jsonCache.has(f)) jsonCache.set(f, getBin(f).then((buffer) => JSON.parse(new TextDecoder().decode(buffer))));
    return jsonCache.get(f);
  } catch (error) { return Promise.reject(error); }
}

// ---------- version 1 module API: the page's values, state and extension points ----------
const actions = new Map();
function renderTourActions() {
  for (const name of ['tour', 'demo']) {
    const button = document.querySelector(`#topbar [data-action="${name}"]`);
    if (button) button.hidden = !actions.has(name);
  }
}
const extensions = { buttons: new Map(), cards: new Map(), notes: new Set(), filters: new Map(), orders: new Map() };
const validArea = (i) => Number.isInteger(i) && i >= 0 && i < D.n;
const activeFilters = () => String(S.filters || '').split(',').filter(Boolean);
const pendingListSettings = () => activeFilters().some((id) => !extensions.filters.has(id)) || !!S.order && !extensions.orders.has(S.order);
function moduleCall(fn, args, fallback = null) {
  try { return fn(...args); } catch { return fallback; }
}
function announce(text) { $('page-announcement').textContent = String(text); }
function listEntries(rows, targetId, indexOf = (row) => row.cell) {
  if (pendingListSettings()) return [];
  const filters = activeFilters().map((id) => extensions.filters.get(id)).filter(Boolean);
  const order = extensions.orders.get(S.order);
  const kept = rows.filter((row) => filters.every((filter) => moduleCall(filter.test, [indexOf(row), targetId], false)));
  if (!order) return kept;
  const scores = new Map(kept.map((row) => [row, moduleCall(order.score, [indexOf(row), targetId])]));
  return kept.sort((a, b) => {
    const x = scores.get(a), y = scores.get(b), haveX = Number.isFinite(x), haveY = Number.isFinite(y);
    return haveX && haveY ? y - x : haveX ? -1 : haveY ? 1 : 0;
  });
}
function renderListControls() {
  const host = $('list-extensions');
  const pending = pendingListSettings();
  host.hidden = !extensions.filters.size && !extensions.orders.size && !pending;
  const active = activeFilters();
  host.innerHTML = [...extensions.filters].map(([id, filter]) => `<label class="check"><input type="checkbox" data-list-filter="${esc(id)}"${active.includes(id) ? ' checked' : ''}><span>${esc(filter.label)}</span></label>`).join('')
    + (extensions.orders.size ? `<label>Order <select data-list-order="order"><option value="">Page order</option>${S.order && !extensions.orders.has(S.order) ? `<option value="${esc(S.order)}" selected>Saved order: its module is not open</option>` : ''}${[...extensions.orders].map(([id, order]) => `<option value="${esc(id)}"${S.order === id ? ' selected' : ''}>${esc(order.label)}</option>`).join('')}</select></label>` : '')
    + (pending ? '<p class="list-pending" role="status">The saved list settings use a module. <a href="#go=tools" data-open-module="tools">Open Tools</a> or <a href="#go=planner" data-open-module="planner">open Planner</a>.</p>' : '');
  host.querySelectorAll('[data-open-module]').forEach((link) => link.addEventListener('click', (event) => {
    event.preventDefault(); set({ only: null, go: link.dataset.openModule });
  }));
  host.querySelectorAll('[data-list-filter]').forEach((input) => input.addEventListener('change', () => {
    const ids = new Set(activeFilters());
    if (input.checked) ids.add(input.dataset.listFilter); else ids.delete(input.dataset.listFilter);
    set({ filters: [...ids].join(',') });
  }));
  const select = host.querySelector('select');
  if (select) select.addEventListener('change', () => set({ order: select.value }));
}
function cardSummary(text) {
  const plain = String(text || '').replace(/\s+/g, ' ').trim();
  const sentence = plain.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim() || plain;
  return sentence.split(/\s+/).slice(0, MAX_WORDS).join(' ') || 'Open this part to see the available figures and their limits.';
}
function renderCardExtensions(i, targetId) {
  for (const [id, part] of extensions.cards) {
    const content = moduleCall(part.render, [i, targetId]);
    if (!(content instanceof Element)) continue;
    const section = document.createElement('details'), summary = document.createElement('summary');
    const title = document.createElement('span'), line = document.createElement('span');
    section.className = 'card-extension card-fold'; section.dataset.more = 'module-' + id;
    section.dataset.cardSection = id;
    title.className = 'card-fold-title'; title.textContent = part.title;
    line.className = 'card-fold-summary';
    line.textContent = cardSummary(typeof part.summary === 'function' ? moduleCall(part.summary, [i, targetId])
      : content.querySelector('p')?.textContent || content.textContent);
    summary.append(title, line); section.append(summary, content); $('card').append(section);
  }
}
// Keep the reading order independent of download and registration order.
const CARD_ORDER = [
  ['pl-rehearsal', /rehearsal (rules|verdicts)/i],
  ['pl-compass', /where the low Sun stands/i],
  ['sky', /watch a day here/i],
  ['extra-power', /power here/i],
  ['extra-steady', /steady influences here/i],
  ['cross', /this place as a Mars stand-in/i],
  ['env', /sunlight, UV, clear days and haze/i],
  ['ask-similar', /places like this one/i],
  ['fx-more', /more about this place/i],
  ['take-away', /take (?:this place|it) away/i],
];
function orderCardSections(card) {
  const rank = (part) => {
    const title = part.querySelector(':scope > summary .card-fold-title')?.textContent || '';
    const at = CARD_ORDER.findIndex(([id, pattern]) => part.dataset.cardSection === id || pattern.test(title));
    return at < 0 ? CARD_ORDER.length : at;
  };
  const folds = [...card.querySelectorAll(':scope > details.card-fold')];
  folds.sort((a, b) => rank(a) - rank(b));
  card.append(...folds);
}

function makeAPI(owner) {
  const cleanup = (fn) => {
    if (owner) (modules[owner].cleanups ||= []).push(fn);
    return fn;
  };
  return Object.freeze({
    version: 1,
    get readyAt() { return D.readyAt ?? null; },
    registerAction(name, fn) {
      if (!['tour', 'demo', 'search'].includes(name) || typeof fn !== 'function') return () => {};
      actions.set(name, fn);
      renderTourActions();
      return cleanup(() => {
        if (actions.get(name) === fn) actions.delete(name);
        renderTourActions();
      });
    },
    answer(targetId = S.target) {
      if (!D.ready || !D.meta.targets.some((t) => t.id === targetId)) return [];
      return answerLunarRows(targetId).filter((row) => validArea(row.i)).flatMap((row) => row.rules.map((rule) => ({ label: rule.label, area: row.i })));
    },
    setMatches,
    onMatches(fn) {
      if (typeof fn !== 'function') return () => {};
      matchListeners.add(fn); deliverMatches(fn);
      return cleanup(() => matchListeners.delete(fn));
    },
    getState: stateCopy,
    setState: (partial) => { if (!restoringView) set(partial); },
    captureView,
    restoreView,
    onState(fn) { stateListeners.add(fn); return cleanup(() => stateListeners.delete(fn)); },
    targets: Object.freeze(D.meta.targets.map((t) => Object.freeze({ id: t.id, name: t.name, limitDeg: t.limit_deg }))),
    periods: Object.freeze(D.meta.bins.map((b, index) => Object.freeze({ index, label: b.label, firstDay: b.first_day, lastDay: b.last_day, month: b.month }))),
    areaCount: D.n,
    areaIndex: (id) => D.idx.get(id) ?? -1,
    area(i) {
      if (!validArea(i)) return null;
      const use = earlierUse(i);
      return { id: D.cells.ids[i], lat: +D.lat[i].toFixed(2), lon: +D.lon[i].toFixed(2), hemisphere: D.isN[i] ? 'N' : 'S',
        region: D.cells.regions[D.cells.region[i]], bare: D.cells.bare[i] >= 0 ? D.cells.bare[i] / 100 : null,
        snowStatus: D.status[i], named: D.cells.site[i] || null,
        littleKnown: use === 'unassessed' || !X.places && D.cells.known[i] < 0 ? null : !isKnown(i) };
    },
    hours(i, targetId = S.target, step = S.step, period = S.period) {
      const t = D.meta.targets.findIndex((item) => item.id === targetId);
      if (!validArea(i) || t < 0 || ![1, 2, 3, 4].includes(+step)) return null;
      const bin = typeof period === 'number' || /^\d+$/.test(String(period)) ? +period : null;
      if (bin != null) return Number.isInteger(bin) && bin >= 0 && bin < NB ? binValue(i, bin, +step, t) : null;
      return ['year', 'winter', 'summer', 'rock', 'bin'].includes(period) ? cellValue(i, +step, period, t) : null;
    },
    periodHours(i, targetId = S.target, step = S.step) {
      const t = D.meta.targets.findIndex((item) => item.id === targetId);
      return Float32Array.from({ length: NB }, (_, b) => validArea(i) && t >= 0 && [1, 2, 3, 4].includes(+step) ? binValue(i, b, +step, t) ?? NaN : NaN);
    },
    openPlace(id) { const i = D.idx.get(id); if (i != null) openPlace(i, true); },
    flyTo(lat, lon, zoom) {
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90) return;
      const [x, y] = proj(lat, lon, lat >= 0);
      set({ view: lat >= 0 ? 'arctic' : 'antarctic', x, y, ...(zoom == null ? {} : { z: zoom }) });
    },
    loadJSON: getJSON,
    loadBin: getBin,
    async exportList() {
      if (pendingListSettings()) throw new Error('Open Tools or Planner to restore the saved list settings first.');
      await extraWait('sources.json');
      return structuredClone({ notes: takeNotes(), rows: listRows().map((row) =>
        Object.fromEntries(TAKE_COLUMNS.map(([name, value]) => [name, value(row)]))) });
    },
    fmtHours: (x) => x == null || !Number.isFinite(x) ? 'unknown' : fH(x) + ' h',
    fmtNumber: (x, digits = 0) => x == null || !Number.isFinite(x) ? 'unknown' : x.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }),
    theme: () => isDark() ? 'dark' : 'light',
    addToolsButton(id, label, onPress) {
      extensions.buttons.get(id)?.remove();
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'btn'; button.dataset.tool = id; button.textContent = label;
      button.addEventListener('click', async () => {
        try { if (owner) await loadModule(owner); await onPress(); } catch { announce('This part is unavailable.'); }
      });
      extensions.buttons.set(id, button); $('tools-buttons').append(button); $('tools-row').hidden = !!S.only;
      return cleanup(() => { button.remove(); if (extensions.buttons.get(id) === button) extensions.buttons.delete(id); $('tools-row').hidden = !extensions.buttons.size || !!S.only; });
    },
    addCardSection(id, title, render, summary) {
      const entry = { title, render, summary };
      extensions.cards.set(id, entry); renderCard();
      return cleanup(() => { if (extensions.cards.get(id) === entry) extensions.cards.delete(id); renderCard(); });
    },
    addListNote(fn) {
      extensions.notes.add(fn); renderTabs();
      return cleanup(() => { extensions.notes.delete(fn); renderTabs(); });
    },
    addListFilter(id, label, test) {
      const entry = { label, test };
      extensions.filters.set(id, entry); renderTabs();
      return cleanup(() => { if (extensions.filters.get(id) === entry) extensions.filters.delete(id); renderTabs(); });
    },
    setListOrder(id, label, score) {
      if (typeof score !== 'function') { extensions.orders.delete(id); if (S.order === id) set({ order: '' }); else renderTabs(); return; }
      const entry = { label, score };
      extensions.orders.set(id, entry);
      if (S.order == null) set({ order: id }); else renderTabs();
      return cleanup(() => { if (extensions.orders.get(id) === entry) extensions.orders.delete(id); renderTabs(); });
    },
    announce,
  });
}

// The new modules have no look-ahead margin: their code and CSS wait for an actual view.
const modules = {
  globes: { import: () => import('./globes.js'), optional: true },
  ask: { import: () => import('./ask.js'), optional: true },
  tools: { import: () => import('./tools.js') },
  planner: { import: () => import('./planner.js') },
  factors: { import: () => import('./factors.js'), optional: true },
  extra: { import: () => import('./extra.js'), optional: true },
  sky: { import: () => import('./sky.js'), optional: true },
  env: { import: () => import('./env.js'), optional: true },
  cross: { import: () => import('./cross.js'), optional: true },
  mars: { import: () => import('./mars.js') },
};
function loadModule(id) {
  const part = modules[id], root = $(id + '-root');
  if (!part || !root || !D.ready) return Promise.resolve();
  if (part.promise) return part.promise;
  root.setAttribute('aria-busy', 'true');
  part.promise = (async () => {
    try {
      const module = await part.import();
      await new Promise((done, reject) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet'; link.href = './' + id + '.css';
        link.onload = done; link.onerror = reject; document.head.append(link);
      });
      part.instance = id === 'mars' ? await module.mountMars(root, { theme: isDark() ? 'dark' : 'light', api: makeAPI(id) }) : await module.mount(root, makeAPI(id));
      const sectionTitle = { factors: 'Every factor', extra: 'Power and steady influences',
        sky: 'Watch a day of low Sun', env: 'Sunlight, UV, clear days and haze' }[id];
      if (sectionTitle && !root.querySelector('h2')) { const heading = document.createElement('h2'); heading.textContent = sectionTitle; root.prepend(heading); }
      if (id === 'sky' && !root.querySelector(':scope > .lede')) {
        const lede = document.createElement('p'); lede.className = 'lede';
        lede.textContent = 'Select a place and a date. Then see where the Sun goes.';
        root.querySelector('h2').after(lede);
      }
      part.theme = isDark() ? 'dark' : 'light'; part.status = 'ready';
      if (id === 'sky') compactSky(root);
      if (id === 'globes') {
        const stageAbout = root.querySelector('.stage-about'), moduleAbout = root.querySelector('.gb-about');
        if (stageAbout && moduleAbout) {
          for (const node of [...stageAbout.children].filter((child) => child.tagName !== 'SUMMARY')) {
            if (node.textContent.trim() === DRAWN && moduleAbout.textContent.includes(DRAWN)) continue;
            node.classList.remove('caption'); node.classList.add('gb-caption'); moduleAbout.append(node);
          }
          stageAbout.closest('figcaption')?.remove();
        }
      }
      renderPageTabs();
    } catch {
      part.status = 'failed';
      for (const cleanup of part.cleanups || []) moduleCall(cleanup, []);
      const heading = document.createElement('h2'), line = document.createElement('p');
      heading.textContent = cap(id); line.className = 'status'; line.textContent = 'This part is unavailable.';
      if (id === 'globes') { restoreStage(); }
      else if (part.optional && id !== 'ask') { root.dataset.moduleMissing = 'true'; root.hidden = true; }
      else root.replaceChildren(heading, line);
    } finally { root.removeAttribute('aria-busy'); keepModuleNext(id, root); holdGo(); }
    return part.instance;
  })();
  return part.promise;
}
function watchModules() {
  const show = (root) => loadModule(root.id.replace('-root', ''));
  const roots = Object.keys(modules).filter((id) => !['globes', 'ask'].includes(id)).map((id) => $(id + '-root')).filter(Boolean);
  if (window.IntersectionObserver) {
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting && !entry.target.hidden) { observer.unobserve(entry.target); show(entry.target); }
    });
    roots.forEach((root) => observer.observe(root));
  } else {
    const check = () => roots.forEach((root) => {
      const box = root.getBoundingClientRect();
      if (!root.hidden && box.bottom > 0 && box.top < innerHeight) show(root);
    });
    window.addEventListener('scroll', check, { passive: true }); window.addEventListener('resize', check); check();
  }
}
let pendingMarsAnchor = null, navigationGeneration = 0;
function cancelNavigation() {
  navigationGeneration++;
  pendingMarsAnchor = null;
  goHold = null;
}
async function goToSection(id) {
  const focusPlaces = document.activeElement?.id === 'results-bar-show';
  cancelNavigation();
  const generation = navigationGeneration;
  if (!await prepareSection(id, generation) || generation !== navigationGeneration) return;
  if (id.startsWith('mars')) {
    if (S.dest !== 'mars') set({ dest: 'mars' });
    await loadModule('mars');
    if (generation !== navigationGeneration) return;
    if (!sectionFor(id)) { pendingMarsAnchor = { id, generation }; return; }
  }
  const root = sectionFor(id);
  if (!root) return;
  const mode = root.closest('[data-mode]')?.dataset.mode;
  if (mode && mode !== S.dest) set({ dest: mode });
  revealSection(root);
  root.scrollIntoView({ block: 'start' });
  if (focusPlaces && root.id === 'places-section') {
    const heading = $('places-heading') || root;
    heading.tabIndex = -1; heading.focus({ preventScroll: true });
  }
  goHold = { id, generation, until: performance.now() + 5000 };
  const moduleId = root.id.replace(/-root$/, '');
  if (modules[moduleId]) await loadModule(moduleId);
  if (generation !== navigationGeneration) return;
  updateRail();
}
function keepModuleNext(id, root) {
  if (!['factors', 'extra', 'env', 'mars'].includes(id) || root.dataset.moduleMissing) return;
  const ensure = () => {
    let next = root.querySelector(':scope > .next-step');
    if (!next) { next = document.createElement('button'); next.type = 'button'; next.className = 'btn next-step'; next.dataset.next = 'deeper'; next.textContent = 'Return to Go deeper'; }
    if (root.lastElementChild !== next) root.append(next);
  };
  ensure();
  if (!modules[id].nextObserver) { const observer = new MutationObserver(ensure); observer.observe(root, { childList: true }); modules[id].nextObserver = observer; }
}

// ---------- the extra files: read only when a card or a list needs them, so the first screen stays fast ----------
// extras.json lists what the last run of scripts/export_site_extras.py made. A file it does not list counts as
// missing, and so does a per-area file made for another list of areas. The part of the page that wanted the file
// then says so in one plain line, and the rest of the page works.
const X = { index: undefined, got: {}, asked: {}, places: undefined };
function extra(name, perArea) {     // undefined: still on its way; null: missing; otherwise the file
  if (name in X.got) return X.got[name];
  if (!X.asked[name]) {
    X.asked[name] = true;
    if (!X.indexP) X.indexP = getJSON('extras.json').catch(() => null).then((ix) => (X.index = ix));
    X.indexP.then((ix) => {
      if (!ix || !ix.files || !ix.files[name]) return null;
      if (perArea && !(ix.areas && ix.areas.count === D.n)) return null;
      return (name.endsWith('.bin') ? getBin(name) : getJSON(name)).catch(() => null);
    }).then((data) => { X.got[name] = data; extraArrived(name); });
  }
  return undefined;
}
let extraTimer = 0;
function extraArrived(name) {
  if (name === 'places.json') { X.places = undefined; X.placesNew = true; }
  if (D.ready && FILE_PARTS[name]) { FILE_PARTS[name](); holdGo(); }   // the section that asked for this file
  clearTimeout(extraTimer);
  extraTimer = setTimeout(() => {
    if (!D.ready) return;
    const key = focusKey();
    if (X.placesNew) { X.placesNew = false; computeMap(); renderMapChrome(); drawMap(); renderTabs(); renderAnswer(); }
    renderCard();
    renderMoon(true);
    if (key && document.activeElement === document.body) {
      const again = $(key.host) && $(key.host).querySelector(key.sel);
      if (again) again.focus({ preventScroll: true });
    }
  }, 25);
}
// What places.json knows about an area: published analog work (so it is not little known), the top place it
// belongs to, an Antarctic site with its nearest station. Areas are matched by id, never by position in a list.
function placesIndex() {   // undefined: still on its way; null: missing
  const file = extra('places.json');
  if (!file) return file;
  if (X.places) return X.places;
  const at = (id) => (D.idx.has(id) ? D.idx.get(id) : -1);
  const nlk = new Map(), near = new Map(), ant = new Map();
  const nl = file.not_little_known || {};
  for (const id of nl.ids || []) { const i = at(id); if (i >= 0) nlk.set(i, []); }
  for (const b of nl.because || []) for (const id of b.ids || []) { const i = at(id); if (i >= 0) { if (!nlk.has(i)) nlk.set(i, []); nlk.get(i).push(b); } }
  for (const pl of file.places || []) for (const a of pl.areas || []) { const i = at(a.id); if (i >= 0) near.set(i, { place: pl, point: (pl.points || [])[a.point] || null, km: a.km_to_point }); }
  for (const s of file.antarctic_sites || []) for (const id of s.ids || []) { const i = at(id); if (i >= 0) ant.set(i, s); }
  return (X.places = { nlk, near, ant, file });
}
// What we know of earlier space-analog use of an area. An area that places.json lists as not little known is
// never called little known, whatever the older list in cells.json says.
function earlierUse(i) {
  const k = D.cells.known[i], P = placesIndex();
  if (k >= 0) return 'known';
  if (P && P.nlk.has(i)) return 'published';
  if (k === -2) return 'unassessed';
  if (P && P.near.has(i) && P.near.get(i).place.analog_use_found === false) return 'searched';
  return 'unlisted';
}
const isKnown = (i) => { const u = earlierUse(i); return u === 'known' || u === 'published'; };

async function start() {
  const t0 = performance.now();
  try {
    [D.meta, D.copy, D.calendar, D.profile] = await Promise.all(['meta.json', 'copy.json', 'calendar.json', 'profile.json'].map(getJSON));
  } catch (e) {
    $('load-status').textContent = 'The page cannot read the data files (' + e.message + '). Run scripts/export_site.py. Then serve this folder from a web server.';
    return;
  }
  readHash();
  renderStatic();
  renderTop();
  const rest = await Promise.all([getJSON('cells.json'), getBin('yearly.bin'), getJSON('flat.json'), getJSON('sites.json'),
    getJSON('land.json'), getBin('snowfree.bin'), getBin('open.bin'), getBin('snowodds.bin'),
    D.meta.has_cloud ? getBin('cloud.bin') : Promise.resolve(null)]).catch((e) => { $('load-status').textContent = 'A data file is missing: ' + e.message; return null; });
  if (!rest) return;
  [D.cells, D.yearlyBuf, D.flat, D.sites, D.land] = rest;
  D.yearly = new Uint16Array(D.yearlyBuf);
  D.sf = new Uint8Array(rest[5]); D.open = new Uint8Array(rest[6]); D.odds = new Uint8Array(rest[7]);
  D.cloud = rest[8] ? new Uint8Array(rest[8]) : null;
  prepareCells();
  D.ready = true;
  fixState();
  $('load-status').textContent = '';
  $('load-status').dataset.ms = Math.round(performance.now() - t0);
  document.documentElement.dataset.loadMs = Math.round(performance.now() - t0);
  initMap();
  renderAll({ fromHash: true });
  D.readyAt = performance.now();
  document.documentElement.dataset.readyAt = String(D.readyAt);
  loadAnswerData();
  if (S.only) await prepareSection(S.only);
  if (S.go) goToSection(S.go);
  ['wheel', 'touchstart', 'keydown', 'pointerdown'].forEach((ev) => window.addEventListener(ev, () => { goHold = null; }, { passive: true }));
  document.documentElement.dataset.ready = '1';
  watchSections();
  watchModules();
  requestAnimationFrame(() => requestAnimationFrame(() => { loadModule('globes'); loadModule('ask'); loadModule('tools'); }));
  renderShell();
  if (S.stage === 'flat' && !S.go && !S.only) goToSection(S.dest === 'mars' ? 'mars-map' : 'map');
  notifyState();
  setTimeout(() => extra('places.json'), 0);   // after the first screen: which areas are not little known
}

// ---------- per-cell values ----------
function prepareCells() {
  const c = D.cells, n = c.n;
  D.n = n;
  D.lat = Float32Array.from(c.lat, (v) => v / 100);
  D.lon = Float32Array.from(c.lon, (v) => v / 100);
  D.isN = Uint8Array.from(c.hemisphere, (ch) => (ch === 'N' ? 1 : 0));
  D.idx = new Map(c.ids.map((id, i) => [id, i]));
  D.fields = c.yearly.fields; D.nf = D.fields.length; D.nt = D.meta.targets.length;
  D.southAt = new Map(c.south.cells.map((cell, k) => [cell, k]));
  // width of a cell in longitude: the id names its south-west corner, the centre is half a cell east of it
  D.dlon = Float32Array.from(c.ids, (id, i) => { const w = 2 * (D.lon[i] - parseFloat(id.split('_')[1])); return w > 0.05 && w < 3 ? w : 0.3; });
  const status = c.snow_statuses;
  D.status = c.snow.map((s) => status[s]);
}
function yr(i, field, t = tIndex()) {
  if (!hasLunarModel(D.meta.targets[t]) && ['terrain', 'full'].includes(field)) return null;
  const raw = D.yearly[(i * D.nt + t) * D.nf + D.fields.indexOf(field)];
  return raw === D.cells.yearly.unknown ? null : raw / D.cells.yearly.scale[field];
}
const flatRow = (i, t = tIndex()) => D.flat.targets[D.meta.targets[t].id].bins[D.cells.flat_row[i]];
const flatBin = (i, b, t = tIndex()) => { const raw = flatRow(i, t)[b]; return raw == null || raw < 0 ? null : raw / 10; };
const flatYear = (i, t = tIndex()) => { const v = D.flat.targets[D.meta.targets[t].id].year[D.cells.flat_row[i]]; return !Number.isFinite(v) || v < 0 ? null : v / 10; };
const byteBin = (arr, i, b, t = tIndex()) => { const raw = arr[(i * D.nt + t) * NB + b]; return raw === 255 ? null : raw * D.meta.encoding.unit_h; };
const clearShare = (i, b) => { if (!D.cloud) return null; const raw = D.cloud[i * 12 + D.meta.bins[b].month - 1]; return raw === 255 ? null : 1 - raw / 100; };
const oddsBin = (i, b) => { const raw = D.odds[i * NB + b]; return raw === 255 ? null : raw / 100; };
function southYear(i, key, t = tIndex()) {
  const k = D.southAt.get(i); if (k == null) return null;
  const v = D.cells.south.targets[D.meta.targets[t].id][key][k];
  return !Number.isFinite(v) || v < 0 ? null : v / (key === 'poleward' ? 1000 : 10);
}
function periodBins() {
  const s = D.meta.seasons;
  if (S.period === 'bin') return [S.bin];
  if (S.period === 'winter') return s.winter_bins_north;
  if (S.period === 'summer') return s.summer_bins_north;
  if (S.period === 'rock') return s.rock_season_bins_south;
  return null;                       // the whole year
}
// Hours of one cell in one ten-day period at a step; null is unknown.
function binValue(i, b, step, t = tIndex()) {
  if (step === 1) return flatBin(i, b, t);
  if (!D.isN[i]) {
    if (!D.meta.seasons.rock_season_bins_south.includes(b)) return 0;
    if (step === 2) return flatBin(i, b, t);
    const open = byteBin(D.open, i, b, t);
    if (step === 3 || open == null) return open;
    const share = clearShare(i, b);
    return open === 0 ? 0 : share == null ? null : open * share;
  }
  if (step === 2) return byteBin(D.sf, i, b, t);
  const open = byteBin(D.open, i, b, t);
  if (step === 3 || open == null) return open;
  const share = clearShare(i, b);
  return open === 0 ? 0 : share == null ? null : open * share;
}
function sumBins(i, bins, step, t) {
  let total = 0;
  for (const b of bins) { const v = binValue(i, b, step, t); if (v == null) return null; total += v; }
  return total;
}
// Hours of one cell over the chosen period at a step, using the exact yearly figures where they exist.
function cellValue(i, step, period = S.period, t = tIndex()) {
  const s = D.meta.seasons;
  if (period === 'bin') return binValue(i, S.bin, step, t);
  if (step === 1) {
    if (period === 'year') return flatYear(i, t);
    return sumBins(i, period === 'winter' ? s.winter_bins_north : period === 'summer' ? s.summer_bins_north : s.rock_season_bins_south, 1, t);
  }
  if (!D.isN[i]) return southYear(i, step === 2 ? 'rock_flat' : step === 3 ? 'rock_open' : 'rock_clear', t);
  const f = step === 2 ? 'snow_free' : step === 3 ? 'open' : 'clear';
  const year = yr(i, f, t);
  if (period === 'year') return year;
  const winter = yr(i, f + '_winter', t);
  if (period === 'winter') return winter;
  // the summer half is the pipeline's own figure; year minus winter (rounded to the stored tenth) only for older data files
  if (D.fields.includes(f + '_summer')) return yr(i, f + '_summer', t);
  return year == null || winter == null ? null : Math.max(0, Math.round((year - winter) * 10) / 10);
}
// How a cell is drawn at a step: 'fill', 'hollow' (snow doubtful or not measured) or 'grey' (no figure).
function cellMark(i, step, v) {
  if (step === 1) return v == null ? 'grey' : 'fill';
  const st = D.status[i];
  if (st === 'doubtful' || st === 'unmeasured') return 'hollow';
  return v == null ? 'grey' : 'fill';
}
function whyUnknown(i, step) {
  const st = D.status[i];
  if (step >= 2 && st === 'no data') return 'no snow data';
  if (step >= 2 && D.isN[i] && yr(i, 'snow_free') == null) return 'snow odds missing for part of the year';   // keep in step with the legend
  if (step >= 3 && D.cells.horizon_n[i] == null) return D.cells.horizon_note[i] != null ? D.cells.horizon_note_labels[D.cells.horizon_note[i]] : 'no terrain figure';
  if (step === 4) return 'no cloud figure for this area';
  return 'no figure';
}

// ---------- static text built from the data ----------
function renderStatic() {
  const m = D.meta;
  $('headline').textContent = "Find places on Earth for Moon and Mars tests.";
  $('purpose').textContent = 'Select a base. Set what your experiment needs. The page finds the places and the dates.';
  $('subline').textContent = '';
  document.title = 'Earth Twin Finder';
  document.querySelectorAll('.drawn').forEach((p) => { p.textContent = DRAWN; });
  const lastStep = m.has_cloud ? STEPS.length : STEPS.length - 1;   // the cloud step is off when cloud is not in the data
  $('when-press').textContent = `Press steps 1 to ${lastStep} in the bar. First, snow removes hours. Then hills remove hours.${m.has_cloud ? ' Last, mean cloud decreases the hours by a rough estimate.' : ''}`;
  $('year').textContent = m.generated.slice(0, 4);
  $('generated').textContent = 'Our code wrote the data of this page on ' +m.generated.replace('T', ' ').replace('Z', ' UTC') + '. Rule for long spells: ' + m.long_rule.text + ' This is not a NASA product.';
  $('sources').innerHTML = m.sources.map((s) => `<li><a href="${esc(s.url)}" rel="noopener">${esc(s.name)}</a>: ${esc(s.used_for)}.</li>`).join('');
  const spell = m.long_rule.spell_h, nSites = words(m.targets.length);
  $('light-lede').innerHTML = `Near the Moon's south pole, the Sun stays close to the horizon. NASA's LRO terrain maps give the highest Sun for each of the ${nSites} lunar regions. If the Sun's centre is above the horizon and at or below that ceiling, the hour counts on Earth. It must be part of a spell of ${spell} hours or more. These places copy the Sun's height and the length of the shadows. They do not copy the light of a world without air, or the slow motion of the lunar Sun. <a href="#limits-section">See what Earth cannot copy</a>.`;
  $('light-caption').textContent = 'Drawings to scale: a 1 m rock and the shortest shadow it throws under each lunar region\'s highest Sun. Lunar terrain: NASA LRO LOLA. ' + DRAWN;
  $('map-keys').innerHTML = `<p>Each mark is one area of bare ground. There are ${fInt(m.counts.north_cells)} in the Arctic and ${fInt(m.counts.south_cells)} in Antarctica. A stronger colour means more hours.</p>
    <ul><li>Select a calculation step in the bar.</li><li>Select the winter or summer half.</li><li>Drag the map to move it.</li><li>Use the arrow keys to move the map with the keyboard.</li><li>Use the wheel or pinch to zoom.</li><li>Press + or &minus; to zoom with the keyboard.</li><li>Select a mark to open its place card.</li><li>Press Enter to open the mark at the centre.</li></ul>`;
  const sh = m.targets.map((t) => t.shadow_m);
  const sm = m.sun_motion, smLats = sm ? Object.keys(sm.earth_deg_per_hour) : [], smLo = smLats[0], smHi = smLats[smLats.length - 1];
  const pace = sm ? `<p>They do not copy the <strong>speed</strong> of the lunar Sun. Near Earth's horizon, the Sun's direction changes approximately ${sm.earth_deg_per_hour[smLo].toFixed(1)}° per hour at ${smLo}° latitude. It changes ${sm.earth_deg_per_hour[smHi].toFixed(1)}° per hour at ${smHi}° latitude. At the Moon's south pole, it changes ${sm.moon_deg_per_hour.toFixed(2)}° per hour.</p><p>In a ${sm.swing_in_one_spell_deg.spell_h}-hour spell, Earth's shadows turn through ${sm.swing_in_one_spell_deg.earth[0]}° to ${sm.swing_in_one_spell_deg.earth[1]}°. Lunar shadows turn through approximately ${sm.swing_in_one_spell_deg.moon.toFixed(1)}°. At these places, a test cannot copy the slow motion of lunar shadows.</p>` : '';
  $('limits-text').innerHTML = `<p>These places copy the <strong>geometry</strong> of the low Sun. They have the same Sun height and shadow length for hours at a time. For these lunar regions, a 1 m rock has a shortest shadow of ${Math.min(...sh).toFixed(1)} m to ${Math.max(...sh).toFixed(1)} m. The shadows can be longer.</p>
  ${pace}
  <p>They do not copy lunar <strong>contrast</strong>. Earth's air scatters light into shadows. It also makes the low Sun darker and redder. On the Moon, shadows are black and the Sun is at full strength. This page does not measure that difference.</p><p>On the lunar ridges, the Sun stays near the horizon for weeks. Earth has the same Sun height for hours at a time. The calendar shows these hours in ten-day periods.</p>`;
  const c = m.counts, st = c.north_by_snow_status;
  let cloud = 'Cloud is not in the data. Thus, the last step is unavailable.';
  if (m.has_cloud) {
    const cm = m.cloud_by_month_north, known = cm ? cm.map((v, k) => [v, k]).filter(([v]) => v != null) : [];
    const lo = known.reduce((a, b) => (b[0] < a[0] ? b : a), known[0]), hi = known.reduce((a, b) => (b[0] > a[0] ? b : a), known[0]);
    cloud = `Cloud is the monthly mean share of sky that clouds cover (NASA POWER, from CERES satellite data${m.cloud_years ? ', ' + esc(m.cloud_years) : ''}). ${m.cloud_grid_km ? `Each box is approximately ${fInt(m.cloud_grid_km)} km from north to south. Its mean includes day and night. ` : ''}${known.length ? `The northern mean is ${Math.round(lo[0])}% in ${MONTH_LONG[lo[1]]} and ${Math.round(hi[0])}% in ${MONTH_LONG[hi[1]]}. These are its lowest and highest monthly values. ` : ''}Mean cloud is not the chance that a low Sun is visible. The last step is a rough estimate by our own rule. It is not a forecast.`;
  }
  $('sure-text').innerHTML = `<ul>
  <li><strong>Snow.</strong> The odds come from ${esc(m.snow.maps)} satellite snow maps, ${esc(m.snow.period)}. Areas with measured snow use ${esc(m.snow.measured_cells_use)}. ${cap(areasN(st.doubtful || 0))} in the north ${st.doubtful === 1 ? 'is' : 'are'} doubtful. Their maps kept the value "snow-free" through a polar winter. ${cap(areasN(st['no data'] || 0))} ${st['no data'] === 1 ? 'has' : 'have'} no snow data. Both kinds have hollow or grey marks and no rank. No open product measures snow on Antarctic rock. Thus, all ${fInt(c.south_cells)} southern areas count only the rock season (${esc(m.seasons.rock_season_text)}). The rock maps show bare ground during that season.</li>
  <li><strong>Terrain.</strong> A terrain figure gives the height of the hills along an area's horizon. ${fInt(c.with_horizon_north)} of ${fInt(c.north_cells)} northern areas have one. In the south, ${fInt(c.with_horizon_south)} of ${fInt(c.south_cells)} areas have one. An area without one is grey from the terrain step onward. It never shows zero. Ranked areas must have a terrain figure, measured snow, and sufficient bare ground. The ranked counts are ${fInt(c.ranked_north)} in the north and ${fInt(c.ranked_south)} in the south.</li>
  <li><strong>Long spells.</strong> ${esc(m.long_rule.text)}</li>
  <li><strong>Cloud.</strong> ${cloud}</li>
  <li><strong>The Sun's height.</strong> The calculation uses a standard value for how air bends light. Real polar air can bend light more or less. This difference is most important for the lowest Sun ceiling.</li>
  <li><strong>What the search covers.</strong> The search covers bare ground from ${fLat(D.profile.search_band.north[0])} to ${fLat(D.profile.search_band.north[1])}. It also covers ${fLat(D.profile.search_band.south[1])} to ${fLat(D.profile.search_band.south[0])}. The data stores the hours of each ten-day period in units of ${m.encoding.unit_h} h.</li></ul>`;
}

// ---------- the one control bar: lunar region and step, for the calendar, the map and the lists ----------
function renderBar() {
  const m = D.meta;
  $('bar-step').innerHTML = STEPS.map((s) => {
    const off = s.n === 4 && !m.has_cloud;
    return `<button type="button" data-step="${s.n}" aria-pressed="${S.step === s.n}" ${off ? 'disabled' : ''} title="${esc(stepName(s.n) + ': ' + stepSmall(s.n))}">${s.n === 1 ? 'Sun only' : s.n === 2 && !north() ? 'Rock season' : s.tiny}</button>`;
  }).join('');
  $('bar-step').querySelectorAll('button').forEach((b) => b.addEventListener('click', () => set({ step: +b.dataset.step })));
}

function renderTop() {
  const m = D.meta, t = target(), h = m.headline[t.id], c = m.counts;
  renderBar();
  const half = halfLevel();
  const reach = (h.measured_cells_reaching[String(half)] || {});
  const tiles = [
    `<div class="figure-tile"><div class="value">${fInt(c.north_cells + c.south_cells)}</div><div class="label">areas of bare polar ground in the search. Each area is approximately ${m.scoring.cell_km} km across.</div></div>`,
    `<div class="figure-tile"><div class="value">${reach.summer != null ? fInt(reach.summer) : 'unknown'} <span class="against">against</span> ${reach.winter != null ? fInt(reach.winter) : 'unknown'}</div><div class="label">Arctic areas with ${fInt(half)} hours or more of ${esc(t.short)}'s low Sun on snow-free ground: summer half against winter half, without the effect of hills.</div></div>`,
    h.best_open_hours != null
      ? `<button type="button" class="figure-tile tile-btn" id="tile-best" data-cell="${h.best_open_cell != null ? h.best_open_cell : ''}"><div class="value">${fH(h.best_open_hours)} h</div><div class="label">a year of Sun this low at the Arctic area with the most hours, without the hours that snow and hills hide. <u>Open its place card</u>.</div></button>`
      : `<div class="figure-tile"><div class="value">${h.first_latitude_with_spells}°</div><div class="label">lowest latitude where the low Sun lasts ${m.long_rule.spell_h} hours in one spell.</div></div>`,
  ];
  $('figures').innerHTML = tiles.join('');
  const best = $('tile-best');
  if (best) best.addEventListener('click', () => { if (D.ready && best.dataset.cell !== '') openPlace(+best.dataset.cell, true); });
  renderShort();
  renderSunCards();
  renderWhere();
  renderWhen();
}

// ---------- in short: three statements of one line each ----------
function renderShort() {
  const m = D.meta, t = target(), ti = tIndex(), h = m.headline[t.id];
  const half = halfLevel(), reach = (h.measured_cells_reaching[String(half)] || {});
  let where = '';
  if (D.ready && reach.winter > 0) {
    const regions = {};
    for (let i = 0; i < D.n; i++) {
      if (!D.isN[i] || D.status[i] !== 'measured' || D.cells.gridded[i] !== '1') continue;
      const w = yr(i, 'snow_free_winter', ti);
      if (w != null && w >= half) { const r = D.cells.regions[D.cells.region[i]]; regions[r] = (regions[r] || 0) + 1; }
    }
    const names = Object.entries(regions).sort((a, b) => b[1] - a[1]).map(([r]) => r);
    if (names.length === 1) where = `, all in ${esc(names[0])}`;
    else if (names.length > 1) where = `, most in ${esc(names[0])}`;
  }
  const found = reach.summer != null
    ? `Winter has the low Sun but not bare ground. For ${esc(t.short)}, ${areasN(reach.summer)} ${reach.summer === 1 ? 'has' : 'have'} ${fInt(half)} hours or more in summer and ${reach.winter === 0 ? 'none' : fInt(reach.winter)} in winter${where}. These counts do not include the effect of hills.`
    : `Winter has the low Sun but not bare ground. On snow-free ground, ${fPct(h.summer_share_snow_free)} of the hours occur in the summer half.`;
  $('short').innerHTML = `<h2 class="sr-only">In short</h2><dl>
    <dt>What this is</dt><dd>The search covers ${fInt(m.counts.north_cells + m.counts.south_cells)} areas of bare polar ground. It finds hours with the same low Sun as ${m.targets.length} lunar south-pole regions.</dd>
    <dt>What we found</dt><dd>${found}</dd>
    <dt>What is new</dt><dd>We read earlier entries and archives. None of them puts these ${m.targets.length} lunar Sun ceilings on a map of Earth and also counts hills and snow.</dd></dl>`;
}

// ---------- the light we want to copy ----------
function sunDrawing(t) {
  const longest = Math.max(...D.meta.targets.map((x) => x.shadow_m));
  const W = 340, s = (W - 70) / longest, ground = 44, rockX = 44;
  const rock = s, tip = rockX + rock + t.shadow_m * s, top = ground - rock;
  const slope = Math.tan((t.limit_deg * Math.PI) / 180);
  const sunX = 14, sunY = top - (rockX + rock - sunX) * slope;
  return `<svg viewBox="0 0 ${W} 64" role="img" aria-label="Sun ${t.limit_deg.toFixed(2)} degrees above a flat horizon; a 1 m rock with a ${t.shadow_m.toFixed(1)} m shadow">
        <line x1="${sunX}" y1="${sunY.toFixed(1)}" x2="${tip.toFixed(1)}" y2="${ground}" stroke="var(--accent)" stroke-width="1"/>
        <circle cx="${sunX}" cy="${sunY.toFixed(1)}" r="7" fill="var(--accent)"/>
        <rect x="${(rockX + rock).toFixed(1)}" y="${ground - 4}" width="${(t.shadow_m * s).toFixed(1)}" height="4" fill="var(--ink)" opacity="0.78"/>
        <rect x="${rockX}" y="${top.toFixed(1)}" width="${rock.toFixed(1)}" height="${rock.toFixed(1)}" fill="var(--ghost2)" stroke="var(--ink)" stroke-width="1"/>
        <line x1="0" y1="${ground + 0.5}" x2="${W}" y2="${ground + 0.5}" stroke="var(--axis)" stroke-width="1"/>
        <text x="${(rockX + rock).toFixed(1)}" y="${ground + 15}" text-anchor="end" font-size="12" fill="var(--ink2)">rock 1 m</text>
        <text x="${(rockX + rock + 10).toFixed(1)}" y="${ground + 15}" text-anchor="start" font-size="12" fill="var(--ink2)">shadow ${t.shadow_m.toFixed(1)} m</text>
      </svg>`;
}
function renderSunCards() {
  const m = D.meta, half = halfLevel();
  const bestOf = (t) => m.headline[t.id].best_open_hours;
  const bestMax = Math.max(...m.targets.map((t) => bestOf(t) || 0), 1);
  $('sun-cards').innerHTML = m.targets.map((t) => {
    const h = m.headline[t.id], reach = (h.measured_cells_reaching[String(half)] || {}).summer, note = t.list_line || t.why;
    const onEarth = h.best_open_hours != null
      ? `<div class="on-earth"><span class="meter"><i style="width:${Math.max(1, (h.best_open_hours / bestMax) * 100).toFixed(1)}%"></i></span><span>On Earth: ${fH(h.best_open_hours)} h a year at the Arctic area with the most hours${reach != null ? `. ${cap(areasN(reach))} ${reach === 1 ? 'reaches' : 'reach'} ${fInt(half)} h in summer, without the effect of hills` : ''}.</span></div>` : '';
    return `<div class="sun-card${t.id === S.target ? ' current' : ''}">
      <button type="button" class="sun-pick" data-target="${t.id}" aria-pressed="${t.id === S.target}">
      <div class="name">${esc(t.name)}</div>
      <div class="limit">The Sun stays at or below ${t.limit_deg.toFixed(2)}°. A 1 m rock throws a shadow of ${t.shadow_m.toFixed(1)} m or longer.</div>
      ${sunDrawing(t)}
      ${onEarth}
      ${note ? `<div class="why">${esc(note)}</div>` : ''}
      </button>
      <button type="button" class="btn sun-about" data-about="${t.id}" aria-haspopup="dialog">About ${esc(t.name)}: the lunar region card</button>
    </div>`;
  }).join('');
  $('sun-cards').querySelectorAll('button[data-target]').forEach((b) => b.addEventListener('click', () => set({ target: b.dataset.target })));
  $('sun-cards').querySelectorAll('button[data-about]').forEach((b) => b.addEventListener('click', () => openMoon(b.dataset.about)));
}

// ---------- chart plumbing ----------
function chartTip(host, html, x, y) {
  let tip = host.querySelector('.chart-tip');
  if (!html) { if (tip) tip.remove(); return; }
  if (!tip) { tip = document.createElement('div'); tip.className = 'chart-tip'; host.appendChild(tip); }
  tip.innerHTML = html;
  const w = host.clientWidth, tw = tip.offsetWidth;
  tip.style.left = Math.max(0, Math.min(w - tw, x + 12)) + 'px';
  tip.style.top = Math.max(0, y - tip.offsetHeight - 8) + 'px';
}
function yTicks(max) {
  const step = niceStep(max / 4);
  const out = [];
  for (let v = 0; v <= max * 1.0001; v += step) out.push(v);
  return out;
}
function niceStep(raw) {
  const p = 10 ** Math.floor(Math.log10(raw || 1)), f = raw / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;
}
const fTick = (v, step) => (step < 1 ? v.toFixed(1) : fInt(v));

// ---------- where: hours against latitude ----------
function renderWhere() {
  const host = $('where-plot'), t = target(), P = D.profile, m = D.meta;
  if (!P.lat.length) { host.textContent = 'The latitude profile is not in the data.'; return; }
  const rows = P.lat.map((lat, k) => ({ lat, all: P.targets[t.id].all[k], long: P.targets[t.id].long[k], longest: P.targets[t.id].longest[k] })).filter((r) => r.lat >= 0);
  const spell = m.long_rule.spell_h;
  const first = (((P.thresholds[t.id] || {}).N || {}).spells || {})[String(m.long_rule.spell_h)];
  const eq = rows[0];
  const peak = rows.reduce((a, r) => (r.long > a.long ? r : a), rows[0]);
  $('where-title').textContent = `${t.short}: spells of ${spell} hours or more start at ${first != null ? first.toFixed(2) + '°' : 'high latitudes'}. The greatest total is ${fInt(peak.long)} hours per year near ${peak.lat.toFixed(1)}°.`;
  $('where-howto').textContent = `The grey line counts each hour with the Sun above a flat horizon and at or below ${t.limit_deg.toFixed(2)}°. The coloured line counts only the hours in spells of ${spell} hours or more. Low Sun occurs at each latitude. It gives ${fInt(eq.all)} hours per year at ${eq.lat === 0 ? 'the equator' : eq.lat.toFixed(1) + '°'}. The shaded band is the range of latitudes that the search covers. The chart shows the north. The south has the same pattern.`;
  $('where-legend').innerHTML = `<span class="key"><span class="line" style="border-color:var(--ghost2)"></span>all low-Sun hours</span><span class="key"><span class="line" style="border-color:var(--accent)"></span>hours in spells of ${spell} hours or more</span><span class="key"><span class="swatch" style="background:var(--season)"></span>latitudes in the search</span>`;
  const W = Math.max(300, host.clientWidth), narrow = W < 520, H = narrow ? 230 : 290;
  const L = 44, R = narrow ? 14 : 24, T = 26, B = 34, pw = W - L - R, ph = H - T - B;
  const topAll = Math.max(...rows.map((r) => r.all)), ymax = Math.ceil(topAll / niceStep(topAll / 4)) * niceStep(topAll / 4);
  const X = (lat) => L + (lat / 90) * pw, Y = (v) => T + ph - (v / ymax) * ph;
  const ticks = yTicks(ymax), step = ticks[1] - ticks[0];
  const path = (key) => rows.map((r, k) => (k ? 'L' : 'M') + X(r.lat).toFixed(1) + ' ' + Y(r[key]).toFixed(1)).join('');
  const band = P.search_band.north;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc($('where-title').textContent)}">`;
  if (band) svg += `<rect x="${X(band[0])}" y="${T}" width="${X(band[1]) - X(band[0])}" height="${ph}" fill="var(--season)"/>`;
  svg += ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${fTick(v, step)}</text>`).join('');
  for (let lat = 0; lat <= 90; lat += narrow ? 30 : 10) svg += `<text x="${X(lat)}" y="${H - 14}" text-anchor="middle">${lat}°</text>`;
  svg += `<text x="${L + pw / 2}" y="${H - 1}" text-anchor="middle">latitude north</text><text x="${L - 38}" y="${T - 12}" text-anchor="start">hours a year</text>`;
  svg += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--axis)"/>`;
  svg += `<path d="${path('long')}L${X(90)} ${Y(0)}L${X(0)} ${Y(0)}Z" fill="var(--accent)" opacity="0.1"/>`;
  svg += `<path d="${path('all')}" fill="none" stroke="var(--ghost2)" stroke-width="2" stroke-linejoin="round"/>`;
  svg += `<path d="${path('long')}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round"/>`;
  if (first != null) {
    const anchor = X(first) > W * 0.6 ? 'end' : 'start', dx = anchor === 'end' ? -6 : 6;
    svg += `<line x1="${X(first)}" x2="${X(first)}" y1="${T}" y2="${Y(0)}" stroke="var(--ink2)" stroke-width="1"/><circle cx="${X(first)}" cy="${Y(0)}" r="4" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"/>`;
    svg += `<text class="direct" x="${X(first) + dx}" y="${T + 11}" text-anchor="${anchor}">${first.toFixed(2)}°: first ${spell}-hour spells</text>`;
  }
  svg += `<line id="where-cross" x1="0" x2="0" y1="${T}" y2="${Y(0)}" stroke="var(--ink2)" stroke-width="1" visibility="hidden"/><rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="transparent" id="where-hit"/></svg>`;
  host.innerHTML = svg;
  const hit = host.querySelector('#where-hit'), cross = host.querySelector('#where-cross');
  hit.addEventListener('pointermove', (e) => {
    const box = host.getBoundingClientRect(), x = e.clientX - box.left;
    const lat = Math.max(0, Math.min(90, ((x - L) / pw) * 90));
    const r = rows.reduce((a, b) => (Math.abs(b.lat - lat) < Math.abs(a.lat - lat) ? b : a), rows[0]);
    cross.setAttribute('x1', X(r.lat)); cross.setAttribute('x2', X(r.lat)); cross.setAttribute('visibility', 'visible');
    chartTip(host, `<b>${r.lat.toFixed(1)}° N</b>All low-Sun hours: ${fInt(r.all)} a year<br>In spells of ${spell} h or more: ${fInt(r.long)}<br>Typical longest spell at best: ${r.longest.toFixed(1)} h`, X(r.lat), e.clientY - box.top);
  });
  hit.addEventListener('pointerleave', () => { cross.setAttribute('visibility', 'hidden'); chartTip(host, null); });
  $('where-table').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Latitude</th><th class="num">All low-Sun hours a year</th><th class="num">In spells of ${spell} h or more</th><th class="num">Typical longest spell, h</th></tr></thead><tbody>` +
    rows.filter((r) => Math.abs(r.lat % 5) < 1e-6 || Math.abs(r.lat - 89.5) < 1e-6).map((r) => `<tr><td>${r.lat.toFixed(1)}° N</td><td class="num">${fInt(r.all)}</td><td class="num">${fInt(r.long)}</td><td class="num">${r.longest.toFixed(2)}</td></tr>`).join('') + '</tbody></table></div>';
}

// ---------- when: the calendar in four steps ----------
// Once nearly every measured area has a terrain figure (calendar.json says when: one_set), all four steps are
// summed over the same areas. Until then steps 1 and 2 count every measured area and steps 3 and 4 the ones
// with a terrain figure; the line under the chart says so.
function calendarData(targetId = S.target) {
  const side = north() ? 'north' : 'south', c = D.calendar[side], s = c.targets[targetId];
  const per = (arr, km) => (arr ? arr.map((v) => (v != null && Number.isFinite(v) && km > 0 ? v / km : null)) : null);
  const rock = D.meta.seasons.rock_season_bins_south;
  const mask = (arr) => (arr ? arr.map((v, b) => (rock.includes(b) ? v : null)) : null);
  const all = c.bare_km2, hk = c.bare_km2_with_horizon, oneSet = !!c.one_set && hk > 0;
  const out = { side, c, oneSet, sunAll: per(s.sun, all), sunH: per(s.sun_h, hk), open: per(s.open, hk), clear: per(s.clear, hk) };
  if (side === 'north') { out.snowAll = per(s.snow_free, all); out.snowH = per(s.snow_free_h, hk); }
  else { out.snowAll = mask(out.sunAll); out.snowH = mask(out.sunH); out.open = mask(out.open); out.clear = mask(out.clear); }
  if (oneSet) { out.sunAll = out.sunH; out.snowAll = out.snowH; }
  return out;
}
function renderWhen() {
  const host = $('when-plot'), t = target(), m = D.meta, d = calendarData(), isN = d.side === 'north';
  const step = S.step, seas = m.seasons;
  const cur = step === 1 ? d.sunAll : step === 2 ? d.snowAll : step === 3 ? d.open : d.clear;
  const sunGhost = step <= 2 ? d.sunAll : d.sunH;
  const prev = step === 3 ? d.snowH : step === 4 ? d.open : null;
  const share = (arr, bins) => { const tot = sum(arr); return tot > 0 ? sum(bins.map((b) => arr[b])) / tot : null; };
  const peakBin = (arr) => arr.reduce((best, v, b) => ((v || 0) > (arr[best] || 0) ? b : best), 0);
  let title;
  if (!cur) title = 'this step is not in the data';
  else if (isN) {
    const w = share(cur, seas.winter_bins_north), su = share(cur, seas.summer_bins_north);
    if (step === 1) title = `with the Sun alone, low-Sun hours occur through the year (${fPct(w)} in the winter half)`;
    else if (step === 2) title = `${w != null && w < 0.1 ? 'snow removes most winter hours' : 'on snow-free ground'}. ${fPct(su)} of the hours left occur in the summer half`;
    else if (step === 3) title = `after snow and hills, ${fPct(su)} of the hours left occur in the summer half. Hills hide ${fPct(1 - sum(d.open) / sum(d.snowH))}`;
    else title = `step 4 is a rough estimate by our own rule. After mean cloud, approximately ${fPct(sum(d.clear) / sum(d.open))} of the hours after terrain are left`;
  } else {
    const rockBins = seas.rock_season_bins_south;
    if (step === 1) title = `Antarctica, Sun alone. ${fPct(share(d.sunAll, rockBins))} of the low-Sun hours occur in the rock season (${seas.rock_season_text})`;
    else if (step === 2) title = `no open product measures snow on Antarctic rock. From this step, only the rock season counts (${seas.rock_season_text})`;
    else if (step === 3) title = `Antarctica: hills hide ${fPct(1 - sum(d.open) / sum(d.snowH))} of the rock-season hours`;
    else title = `in Antarctica, step 4 is a rough estimate by our own rule. After mean cloud, approximately ${fPct(sum(d.clear) / sum(d.open))} of the rock-season hours after terrain are left`;
  }
  $('when-title').textContent = `${t.short}: ${title}`;
  const spell = m.long_rule.spell_h, cc = d.c;
  let how = `How to read this: the chart has one bar for each ten-day period of the year. The height of a bar is the average hours of low Sun on the bare ground in the search. Low Sun means a Sun no higher than ${t.limit_deg.toFixed(2)}°, in spells of ${spell} hours or more. Grey bars show earlier steps. Coloured bars show the hours that are left. For this lunar region, the axis does not change between steps.`;
  if (isN) how += ` Snow-free odds come from daily satellite snow maps, ${m.snow.period}.`;
  if (cc.cells_with_horizon < cc.cells) {
    how += d.oneSet ? ` All four steps count the ${fInt(cc.cells_with_horizon)} of ${fInt(cc.cells)} areas that have a terrain figure.`
      : step >= 3 ? ` From step 3 on, only ${fInt(cc.cells_with_horizon)} of ${fInt(cc.cells)} areas have a terrain figure. Thus, the grey bars change a little.`
        : ` Steps 3 and 4 count only the ${fInt(cc.cells_with_horizon)} of ${fInt(cc.cells)} areas that have a terrain figure.`;
  }
  if (step === 4) how += ` Cloud is the monthly mean share of sky that clouds cover.${m.cloud_grid_km ? ` There is one figure for each box of approximately ${fInt(m.cloud_grid_km)} km from north to south.` : ''} Mean cloud is not the chance that a low Sun is visible.`;
  $('when-howto').textContent = how;
  const peak = (id) => {
    const series = calendarData(id);
    const values = (step === 1 ? series.sunAll : step === 2 ? series.snowAll : step === 3 ? series.open : series.clear)?.filter(Number.isFinite) || [];
    return values.length ? Math.max(...values) : null;
  };
  const byCeiling = m.targets.filter((item) => Number.isFinite(item.limit_deg)).sort((a, b) => a.limit_deg - b.limit_deg);
  const hard = byCeiling[0], easy = byCeiling.at(-1);
  const peakText = (item) => item ? `${item.name}, ${fH(peak(item.id))}${peak(item.id) == null ? '' : ' h'}` : 'unknown';
  $('when-comparison').textContent = `Highest average hours at this step: ${peakText(t)}. Lowest Sun ceiling: ${peakText(hard)}. Highest Sun ceiling: ${peakText(easy)}.`;
  const names = { 1: 'Sun only', 2: isN ? 'on snow-free ground' : 'rock season only (snow not measured)', 3: 'after terrain', 4: 'under typical cloud' };
  let legend = `<span class="key"><span class="swatch" style="background:var(--accent)${!isN && step === 2 ? ';opacity:.45' : ''}"></span>now: ${names[step]}</span>`;
  if (step > 1) legend += `<span class="key"><span class="swatch" style="background:var(--ghost1)"></span>Sun only</span>`;
  if (prev) legend += `<span class="key"><span class="swatch" style="background:var(--ghost2)"></span>previous step: ${names[step - 1]}</span>`;
  legend += `<span class="key"><span class="swatch" style="background:var(--season)"></span>${isN ? 'winter half (' + seas.winter_text + ')' : 'rock season (' + seas.rock_season_text + ')'}</span>`;
  $('when-legend').innerHTML = legend;

  const W = Math.max(300, host.clientWidth), narrow = W < 560, H = narrow ? 240 : 300;
  const L = 40, R = 8, T = 22, B = 30, pw = W - L - R, ph = H - T - B, band = pw / NB, bw = Math.max(2, Math.min(24, band - 2));
  // Include every step and ghost series, but only for the chosen lunar region.
  const top = Math.max(...[d.sunAll, d.sunH, d.snowAll, d.snowH, d.open, d.clear].flatMap((a) => a || []).filter(Number.isFinite), 0.001);
  const stepY = niceStep(top / 5), ymax = Math.ceil(top / stepY) * stepY || 1;
  const Y = (v) => T + ph - (v / ymax) * ph, X = (b) => L + b * band + (band - bw) / 2;
  const shaded = isN ? seas.winter_bins_north : seas.rock_season_bins_south;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc($('when-title').textContent)}">`;
  for (let b = 0; b < NB; b++) if (shaded.includes(b)) svg += `<rect x="${L + b * band}" y="${T}" width="${band + 0.5}" height="${ph}" fill="var(--season)"/>`;
  const ticks = [];
  for (let v = 0; v <= ymax * 1.0001; v += stepY) ticks.push(v);
  svg += ticks.map((v) => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${fTick(v, stepY)}</text>`).join('');
  svg += `<text x="${L - 34}" y="${T - 9}" text-anchor="start">average hours of low Sun in each ten-day period</text>`;
  const bar = (b, v, fill, extra = '') => {
    if (v == null || v <= 0) return '';
    const h = Math.max(1, Y(0) - Y(v)), r = Math.min(4, bw / 2, h);
    const x = X(b), y = Y(0) - h;
    return `<path d="M${x} ${Y(0)}V${y + r}Q${x} ${y} ${x + r} ${y}H${x + bw - r}Q${x + bw} ${y} ${x + bw} ${y + r}V${Y(0)}Z" fill="${fill}" ${extra}/>`;
  };
  for (let b = 0; b < NB; b++) {
    if (step > 1) svg += bar(b, sunGhost[b], 'var(--ghost1)');
    if (prev) svg += bar(b, prev[b], 'var(--ghost2)');
    if (cur) svg += bar(b, cur[b], 'var(--accent)', !isN && step === 2 ? 'opacity="0.45"' : '');
  }
  svg += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--axis)"/>`;
  let day = 1;
  const monthDays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  MONTH.forEach((name, k) => {
    const x = L + Math.min(NB, (day - 1) / 10) * band;
    svg += `<line x1="${x}" x2="${x}" y1="${Y(0)}" y2="${Y(0) + 4}" stroke="var(--axis)"/><text x="${x + 3}" y="${H - 10}" text-anchor="start">${narrow ? name[0] : name}</text>`;
    day += monthDays[k];
  });
  if (isN && !narrow) {
    const mid = (bins) => L + ((Math.min(...bins) + Math.max(...bins) + 1) / 2) * band;
    svg += `<text x="${mid(seas.summer_bins_north)}" y="${T + 13}" text-anchor="middle">summer half</text>`;
    svg += `<text x="${L + 4}" y="${T + 13}">winter half</text><text x="${W - R - 4}" y="${T + 13}" text-anchor="end">winter half</text>`;
  }
  if (cur && step > 1) {   // the Sun-only year has no single peak worth a label
    const pb = peakBin(cur);
    if (cur[pb] > 0) {
      const tx = Math.max(L + 60, Math.min(W - R - 60, X(pb) + bw / 2));
      svg += `<text class="direct halo" x="${tx}" y="${Math.max(T + 26, Y(cur[pb]) - 6)}" text-anchor="middle">${D.meta.bins[pb].label}: ${cur[pb] < 9.95 ? cur[pb].toFixed(1) : fInt(cur[pb])} h left</text>`;
    }
  }
  svg += `<rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="transparent" id="when-hit"/></svg>`;
  host.innerHTML = svg;
  const f1 = (v) => (v == null ? 'not counted' : v.toFixed(v < 9.95 ? 1 : 0) + ' h');
  const hit = host.querySelector('#when-hit');
  hit.addEventListener('pointermove', (e) => {
    const box = host.getBoundingClientRect(), b = Math.max(0, Math.min(NB - 1, Math.floor((e.clientX - box.left - L) / band)));
    let html = `<b>${D.meta.bins[b].label}</b>Sun only: ${f1(sunGhost[b])}`;
    if (step >= 2) html += `<br>${isN ? 'Snow-free ground' : 'Rock season'}: ${f1((step <= 2 ? d.snowAll : d.snowH)[b])}`;
    if (step >= 3) html += `<br>After terrain: ${f1(d.open[b])}`;
    if (step >= 4 && d.clear) html += `<br>Under typical cloud: ${f1(d.clear[b])}`;
    chartTip(host, html, X(b), e.clientY - box.top);
  });
  hit.addEventListener('pointerleave', () => chartTip(host, null));
  const cell = (arr, b) => (arr && arr[b] != null ? arr[b].toFixed(2) : 'unknown');
  const star = d.oneSet || cc.cells_with_horizon >= cc.cells ? '' : '*';
  const s = cc.targets[S.target], gaps = [];
  if (s.snow_free_unknown_cell_periods) gaps.push(`${fInt(s.snow_free_unknown_cell_periods)} for snow`);
  if (s.clear_unknown_cell_periods) gaps.push(`${fInt(s.clear_unknown_cell_periods)} for cloud`);
  $('when-table').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Ten-day period</th><th class="num">Sun only</th><th class="num">${isN ? 'Snow-free ground' : 'Rock season only'}</th><th class="num">After terrain${star}</th><th class="num">Under typical cloud${star}</th></tr></thead><tbody>` +
    D.meta.bins.map((bn, b) => `<tr><td>${bn.label}</td><td class="num">${cell(d.sunAll, b)}</td><td class="num">${cell(d.snowAll, b)}</td><td class="num">${cell(d.open, b)}</td><td class="num">${cell(d.clear, b)}</td></tr>`).join('') +
    `</tbody></table></div><p class="caption">Each value is the average hours of low Sun in one ten-day period. Places with more bare ground have more weight in the average.${star ? ` *Over the ${fInt(cc.cells_with_horizon)} of ${fInt(cc.cells)} areas that have a terrain figure.` : cc.cells_with_horizon < cc.cells ? ` All columns count the ${fInt(cc.cells_with_horizon)} of ${fInt(cc.cells)} areas that have a terrain figure.` : ''}${gaps.length ? ` Some single periods have no figure. They add nothing to the average: ${gaps.join(' and ')}.` : ''}</p>`;
}

// ---------- the map ----------
const M = { zoomTo: null };
function proj(lat, lon, isNorth) {
  const r = 2 * Math.tan(((90 - Math.abs(lat)) * Math.PI) / 360);
  const a = ((lon - (isNorth ? LON0 : 0)) * Math.PI) / 180;
  return isNorth ? [r * Math.sin(a), r * Math.cos(a)] : [r * Math.sin(a), -r * Math.cos(a)];
}
const R_DISC = 2 * Math.tan((39.4 * Math.PI) / 360);
const rFit = () => 2 * Math.tan(((north() ? 32.5 : 29) * Math.PI) / 360);   // fits 57.5 N, or 61 S
function initMap() {
  const canvas = $('map'), wrap = $('map-wrap');
  M.canvas = canvas; M.ctx = canvas.getContext('2d');
  M.px = new Float32Array(D.n); M.py = new Float32Array(D.n);
  M.val = new Float32Array(D.n); M.mk = new Uint8Array(D.n); M.col = new Uint8Array(D.n);
  M.projectedFor = null; M.hover = -1; M.pointers = new Map();
  const ro = new ResizeObserver(() => { sizeMap(); drawMap(); });
  ro.observe(wrap);
  sizeMap();
  canvas.addEventListener('wheel', (e) => { e.preventDefault(); zoomAt(Math.exp(-e.deltaY * 0.0016), e.offsetX, e.offsetY); }, { passive: false });
  canvas.addEventListener('pointerdown', (e) => {
    try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* a pointer that cannot be captured still works */ }
    M.pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
    M.down = { x: e.offsetX, y: e.offsetY, moved: false };
    M.pinch = M.pointers.size === 2 ? pinchState() : null;
  });
  canvas.addEventListener('pointermove', (e) => {
    const p = M.pointers.get(e.pointerId);
    if (!p) { hoverAt(e.offsetX, e.offsetY); return; }
    const dx = e.offsetX - p.x, dy = e.offsetY - p.y;
    p.x = e.offsetX; p.y = e.offsetY;
    if (M.pointers.size === 2 && M.pinch) {
      const now = pinchState();
      zoomAt(now.d / M.pinch.d, now.cx, now.cy, true);
      M.pinch = now; M.down.moved = true;
    } else if (M.pointers.size === 1) {
      if (Math.abs(e.offsetX - M.down.x) + Math.abs(e.offsetY - M.down.y) > 5) M.down.moved = true;
      if (M.down.moved) { S.x -= dx / scale(); S.y -= dy / scale(); clampView(); showTip(-1); drawMap(); writeHash(); }
    }
  });
  const up = (e) => {
    const had = M.pointers.delete(e.pointerId);
    if (had && M.pointers.size === 0 && M.down && !M.down.moved) {
      const i = cellAt(e.offsetX, e.offsetY);
      if (i >= 0) openPlace(i, false);
    }
    M.pinch = null;
  };
  canvas.addEventListener('pointerup', up);
  canvas.addEventListener('pointercancel', (e) => { M.pointers.delete(e.pointerId); M.pinch = null; });
  canvas.addEventListener('pointerleave', () => showTip(-1));
  canvas.addEventListener('keydown', (e) => {
    const stepPx = 60;
    if (e.key === 'ArrowLeft') S.x -= stepPx / scale();
    else if (e.key === 'ArrowRight') S.x += stepPx / scale();
    else if (e.key === 'ArrowUp') S.y -= stepPx / scale();
    else if (e.key === 'ArrowDown') S.y += stepPx / scale();
    else if (e.key === '+' || e.key === '=') { zoomAt(1.5, M.w / 2, M.h / 2); e.preventDefault(); return; }
    else if (e.key === '-' || e.key === '_') { zoomAt(1 / 1.5, M.w / 2, M.h / 2); e.preventDefault(); return; }
    else if (e.key === '0') { S.z = 1; S.x = 0; S.y = 0; }
    else if (e.key === 'Enter' || e.key === ' ') { const i = cellAt(M.w / 2, M.h / 2, 40); if (i >= 0) openPlace(i, false); e.preventDefault(); return; }
    else return;
    e.preventDefault(); clampView(); drawMap(); writeHash(); centreTip();
  });
  canvas.addEventListener('focus', () => { M.focused = canvas.matches(':focus-visible'); drawMap(); centreTip(); });   // the centre cross is for the keyboard only
  canvas.addEventListener('blur', () => { M.focused = false; showTip(-1); drawMap(); });
  $('zoom-in').addEventListener('click', () => zoomAt(1.6, M.w / 2, M.h / 2));
  $('zoom-out').addEventListener('click', () => zoomAt(1 / 1.6, M.w / 2, M.h / 2));
  $('zoom-reset').addEventListener('click', () => { S.z = 1; S.x = 0; S.y = 0; drawMap(); writeHash(); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { renderAll(); notifyState(true); });
}
function pinchState() {
  const [a, b] = [...M.pointers.values()];
  return { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
}
function sizeMap() {
  const c = M.canvas, box = c.getBoundingClientRect();
  M.dpr = Math.min(2, window.devicePixelRatio || 1);
  M.w = Math.max(200, box.width); M.h = Math.max(200, box.height);
  c.width = Math.round(M.w * M.dpr); c.height = Math.round(M.h * M.dpr);
}
const scale = () => (Math.min(M.w, M.h) / 2 / rFit()) * S.z;
const sx = (x) => (x - S.x) * scale() + M.w / 2;
const sy = (y) => (y - S.y) * scale() + M.h / 2;
function clampView() { const lim = R_DISC; S.x = Math.max(-lim, Math.min(lim, S.x)); S.y = Math.max(-lim, Math.min(lim, S.y)); }
function zoomAt(factor, x, y, quiet) {
  const before = scale(), z = Math.min(60, Math.max(1, S.z * factor));
  const wx = (x - M.w / 2) / before + S.x, wy = (y - M.h / 2) / before + S.y;
  S.z = z;
  const after = scale();
  S.x = wx - (x - M.w / 2) / after; S.y = wy - (y - M.h / 2) / after;
  if (S.z <= 1.001) { S.x = 0; S.y = 0; }
  clampView(); showTip(-1); drawMap(); if (!quiet) writeHash(); else writeHash();
}
function projectCells() {
  const isNorth = north();
  if (M.projectedFor === S.view) return;
  for (let i = 0; i < D.n; i++) { const p = proj(D.lat[i], D.lon[i], isNorth); M.px[i] = p[0]; M.py[i] = p[1]; }
  const side = isNorth ? D.land.north : D.land.south, sc = D.land.scale;
  M.land = side.map((ring) => {
    const out = new Float32Array(ring.length), seam = new Uint8Array(ring.length / 2);
    for (let k = 0; k < ring.length; k += 2) {
      const lon = ring[k] / sc, lat = ring[k + 1] / sc, p = proj(lat, lon, isNorth);
      out[k] = p[0]; out[k + 1] = p[1];
      seam[k / 2] = Math.abs(Math.abs(lon) - 180) < 0.02 || Math.abs(Math.abs(lat) - D.land.limit_deg) < 0.02 ? 1 : 0;
    }
    return { p: out, seam };
  });
  M.projectedFor = S.view;
}
// Colour scale: one fixed scale of hours for all lunar regions, every step and both poles (meta.scale), so
// that the hardest site looks as pale as it is. A single ten-day period has its own, equally fixed, scale.
function legendMax() {
  const sc = D.meta.scale || {}, fixed = S.period === 'bin' ? sc.period_h : sc.year_h;
  if (fixed) return fixed;
  // older data files: the 99th percentile over all sites, worked out here
  const key = S.period === 'bin' ? 'bin' : 'long';
  M.maxCache = M.maxCache || {};
  if (M.maxCache[key]) return M.maxCache[key];
  const vals = [];
  for (let t = 0; t < D.nt; t++) {
    for (let i = 0; i < D.n; i++) {
      let v;
      if (S.period === 'bin') { v = 0; for (let b = 0; b < NB; b++) { const x = binValue(i, b, 2, t); if (x != null && x > v) v = x; } }
      else v = D.isN[i] ? (D.status[i] === 'measured' ? yr(i, 'snow_free', t) : null) : southYear(i, 'rock_flat', t);
      if (v != null && v > 0) vals.push(v);
    }
  }
  return (M.maxCache[key] = niceCeil(Math.max(5, quantile(vals, 0.99))));
}
function computeMap() {
  projectCells();
  const isNorth = north(), step = S.step, max = legendMax();
  const count = { fill: 0, hollow: 0, hollowSearch: 0, grey: 0, zero: 0, hiddenKnown: 0, notAssessed: 0, reach: 0, shown: 0, firm: 0, before: 0, after: 0 };
  const inSearch = D.cells.gridded;
  const greyWhy = {}, reachCells = [];
  const half = halfLevel();
  for (let i = 0; i < D.n; i++) {
    if (!!D.isN[i] !== isNorth) { M.mk[i] = 3; continue; }
    if (S.little) {
      const k = D.cells.known[i];
      if (isKnown(i)) { M.mk[i] = 3; count.hiddenKnown++; continue; }
      if (k === -2) count.notAssessed++;
    }
    const v = cellValue(i, step);
    let mark = cellMark(i, step, v);
    if (mark === 'hollow' && v == null) { mark = 'grey'; }
    M.val[i] = v == null ? NaN : v;
    M.mk[i] = mark === 'fill' ? 0 : mark === 'hollow' ? 1 : 2;
    M.col[i] = v == null || v <= 0 ? 0 : 1 + Math.min(62, Math.floor((v / max) * 62.999));
    count[mark]++; count.shown++;
    if (mark === 'hollow' && inSearch[i] === '1') count.hollowSearch++;
    if (mark === 'grey') { const w = whyUnknown(i, step); greyWhy[w] = (greyWhy[w] || 0) + 1; }
    if (mark !== 'grey' && v === 0) count.zero++;
    if (mark === 'fill' && inSearch[i] === '1') { count.firm++; if (v >= half) { count.reach++; reachCells.push(i); } }
    if (step === 4 && v != null && inSearch[i] === '1' && mark !== 'grey') {   // the share of hours that cloud leaves
      const b = cellValue(i, 3);
      // weighted by bare ground, as the calendar is, so that the two titles give the same share
      if (b != null) { const w = D.cells.bare_km2[i] > 0 ? D.cells.bare_km2[i] : 0; count.before += b * w; count.after += v * w; }
    }
  }
  M.count = count; M.greyWhy = greyWhy; M.max = max; M.half = half; M.reachCells = reachCells;
  // draw order: low values first so that the bright areas stay on top
  const order = [];
  for (let i = 0; i < D.n; i++) if (M.mk[i] !== 3) order.push(i);
  order.sort((a, b) => (M.mk[a] === 2 ? -1 : M.col[a]) - (M.mk[b] === 2 ? -1 : M.col[b]));
  M.order = order;
}
function quad(ctx, i, isNorth) {
  const dl = D.dlon[i] / 2, la = D.lat[i], lo = D.lon[i];
  const c = [proj(la - 0.05, lo - dl, isNorth), proj(la - 0.05, lo + dl, isNorth), proj(la + 0.05, lo + dl, isNorth), proj(la + 0.05, lo - dl, isNorth)];
  ctx.beginPath();
  ctx.moveTo(sx(c[0][0]), sy(c[0][1]));
  for (let k = 1; k < 4; k++) ctx.lineTo(sx(c[k][0]), sy(c[k][1]));
  ctx.closePath();
}
function drawMap() {
  if (!D.ready || !M.order) return;
  const ctx = M.ctx, w = M.w, h = M.h, k = scale(), isNorth = north(), colours = ramp();
  const C = { ocean: css('--ocean'), land: css('--land'), coast: css('--coast'), grat: css('--graticule'), unknown: css('--unknown'), ink: css('--ink'), ink2: css('--ink2'), surface: css('--surface'), select: css('--select') };
  ctx.setTransform(M.dpr, 0, 0, M.dpr, 0, 0);
  ctx.fillStyle = C.surface; ctx.fillRect(0, 0, w, h);
  ctx.save();
  ctx.beginPath(); ctx.arc(sx(0), sy(0), R_DISC * k, 0, 2 * Math.PI); ctx.clip();
  ctx.fillStyle = C.ocean; ctx.fillRect(0, 0, w, h);
  // land
  ctx.fillStyle = C.land; ctx.beginPath();
  for (const ring of M.land) {
    const p = ring.p;
    ctx.moveTo(sx(p[0]), sy(p[1]));
    for (let j = 2; j < p.length; j += 2) ctx.lineTo(sx(p[j]), sy(p[j + 1]));
    ctx.closePath();
  }
  ctx.fill();
  ctx.strokeStyle = C.coast; ctx.lineWidth = 0.6; ctx.beginPath();
  for (const ring of M.land) {
    const p = ring.p, seam = ring.seam;
    let pen = false;
    for (let j = 0; j < p.length; j += 2) {
      const skip = j > 0 && seam[j / 2] && seam[j / 2 - 1];
      if (!pen || skip) ctx.moveTo(sx(p[j]), sy(p[j + 1])); else ctx.lineTo(sx(p[j]), sy(p[j + 1]));
      pen = true;
    }
  }
  ctx.stroke();
  // graticule
  ctx.strokeStyle = C.grat; ctx.lineWidth = 1; ctx.fillStyle = C.ink2; ctx.font = '11px system-ui, sans-serif';
  for (const lat of [60, 70, 80]) {
    const r = 2 * Math.tan(((90 - lat) * Math.PI) / 360) * k;
    ctx.beginPath(); ctx.arc(sx(0), sy(0), r, 0, 2 * Math.PI); ctx.stroke();
    const lp = proj(isNorth ? lat : -lat, isNorth ? LON0 + 180 : 180, isNorth);
    ctx.fillText(lat + '°' + (isNorth ? 'N' : 'S'), sx(lp[0]) + 3, sy(lp[1]) - 3);
  }
  for (let lon = -180; lon < 180; lon += 30) {
    const a = proj(isNorth ? 89 : -89, lon, isNorth), b = proj(isNorth ? 50.6 : -50.6, lon, isNorth);
    ctx.beginPath(); ctx.moveTo(sx(a[0]), sy(a[1])); ctx.lineTo(sx(b[0]), sy(b[1])); ctx.stroke();
  }
  // areas
  const cellPx = k * CELL_UNIT, rectMode = cellPx < 3.2, size = Math.max(1.5, cellPx * 1.12), halfSize = size / 2;
  const hollows = [], greys = [];
  let last = '';
  for (const i of M.order) {
    const x = sx(M.px[i]), y = sy(M.py[i]);
    if (x < -30 || y < -30 || x > w + 30 || y > h + 30) continue;
    const mk = M.mk[i];
    if (mk === 1 && (isNorth || cellPx >= 7)) { hollows.push(i); continue; }
    if (mk === 2 && cellPx >= 5) greys.push(i);
    const colour = mk === 2 ? C.unknown : colours[M.col[i]];
    if (colour !== last) { ctx.fillStyle = colour; last = colour; }
    if (rectMode) ctx.fillRect(x - halfSize, y - halfSize, size, size);
    else { quad(ctx, i, isNorth); ctx.fill(); }
  }
  if (greys.length) {   // a second cue besides colour for "no figure": a stroke across the area
    ctx.strokeStyle = C.land; ctx.lineWidth = Math.max(1, cellPx * 0.14); ctx.beginPath();
    const d = cellPx * 0.36;
    for (const i of greys) { const x = sx(M.px[i]), y = sy(M.py[i]); ctx.moveTo(x - d, y + d); ctx.lineTo(x + d, y - d); }
    ctx.stroke();
  }
  // doubtful snow (and, zoomed in, unmeasured snow): hollow, and never louder than the filled marks
  for (const i of hollows) {
    const x = sx(M.px[i]), y = sy(M.py[i]), s = Math.max(4, cellPx * 0.86), lw = Math.max(1, s * 0.16);
    ctx.lineWidth = lw; ctx.strokeStyle = Number.isNaN(M.val[i]) ? C.unknown : colours[M.col[i]];
    ctx.fillStyle = C.land; ctx.fillRect(x - s / 2, y - s / 2, s, s);
    ctx.strokeRect(x - s / 2 + lw / 2, y - s / 2 + lw / 2, s - lw, s - lw);
  }
  // labels
  M.sel = S.place && D.idx.has(S.place) ? D.idx.get(S.place) : -1;
  let labels = isNorth ? [['Greenland', 74, -41], ['Iceland', 66.6, -18.5], ['Svalbard', 80.6, 18], ['Arctic Canada', 64.5, -98], ['Alaska', 64.2, -152], ['Siberia', 64.5, 105], ['Scandinavia', 62.5, 16], ['Novaya Zemlya', 76.6, 62], ['Ellesmere I.', 82.6, -78]]
    : [['Antarctic Peninsula', -66.5, -60], ['Transantarctic Mts', -85.5, 150], ['Dronning Maud Land', -73.5, 8], ['Wilkes Land', -68.5, 118], ['Victoria Land', -73, 158], ['Enderby Land', -68.5, 52], ['Ellsworth Mts', -79, -86], ['East Antarctica', -78, 80]];
  if (!isNorth && w < 560 && S.z <= 1.5) labels = labels.slice(0, 4);   // a phone has no room for eight
  ctx.font = '600 12px system-ui, sans-serif'; ctx.textAlign = 'center'; ctx.lineJoin = 'round';
  for (const [name, la, lo] of labels) {
    const p = proj(la, lo, isNorth), half = ctx.measureText(name).width / 2 + 4, y = sy(p[1]);
    let x = sx(p[0]);
    if (S.z <= 1.01) x = Math.max(half, Math.min(w - half, x));   // keep whole names on a narrow screen
    else if (x - half < 0 || x + half > w || y < 12 || y > h - 4) continue;   // zoomed in: no name cut at the edge
    const controls = $('zoom-in').parentElement, left = controls.offsetLeft, top = controls.offsetTop;
    if (w < 560 && x + half >= left && y + 4 >= top && y - 12 <= top + controls.offsetHeight) continue;
    ctx.lineWidth = 3; ctx.strokeStyle = C.ocean; ctx.globalAlpha = 0.85; ctx.strokeText(name, x, y); ctx.globalAlpha = 1;
    ctx.fillStyle = C.ink; ctx.fillText(name, x, y);
  }
  if (S.z >= 3 && D.sites) {
    ctx.font = '11px system-ui, sans-serif'; ctx.textAlign = 'left';
    for (const site of D.sites.named) {
      if ((site.hemisphere === 'N') !== isNorth || site.lat == null) continue;
      const p = proj(site.lat, site.lon, isNorth), x = sx(p[0]), y = sy(p[1]);
      if (x < 0 || y < 0 || x > w || y > h) continue;
      ctx.beginPath(); ctx.arc(x, y, 3.5, 0, 2 * Math.PI); ctx.fillStyle = C.surface; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = C.ink; ctx.stroke();
      const short = site.name.split(',')[0];
      const dx = site.cell === M.sel ? Math.max(9, cellPx * 0.9) + 8 : 7;   // clear of the ring round a chosen place
      ctx.lineWidth = 3; ctx.strokeStyle = C.ocean; ctx.strokeText(short, x + dx, y + 4); ctx.fillStyle = C.ink; ctx.fillText(short, x + dx, y + 4);
    }
  }
  ctx.textAlign = 'start';
  // the chosen place and the hovered one
  const ring = (i, colour, r) => {
    if (i < 0 || M.mk[i] === 3 && i !== M.sel) return;
    const x = sx(M.px[i]), y = sy(M.py[i]), rr = Math.max(r, cellPx * 0.9);
    ctx.beginPath(); ctx.arc(x, y, rr + 1.5, 0, 2 * Math.PI); ctx.lineWidth = 4; ctx.strokeStyle = C.ocean; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, rr + 1.5, 0, 2 * Math.PI); ctx.lineWidth = 2; ctx.strokeStyle = colour; ctx.stroke();
  };
  if (M.hover >= 0) ring(M.hover, C.ink2, 6);
  if (M.sel >= 0 && !!D.isN[M.sel] === isNorth) ring(M.sel, C.select, 9);
  M.matchPins = matches?.mode === 'moon' ? drawMatchPins(ctx, matches.areas.slice(0, 10).flatMap((i, index) =>
    validArea(i) && !!D.isN[i] === isNorth ? [{ x: sx(M.px[i]), y: sy(M.py[i]), rank: index + 1, area: i }] : [])) : [];
  ctx.restore();
  // a few areas that reach the level would be a speck on this view: ring them and say what they are
  // (drawn after the disc's clip is lifted, so that the words are never cut at the rim)
  const rc = M.reachCells || [];
  if (S.step >= 2 && S.period !== 'bin' && rc.length > 0 && rc.length <= 200) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    const regions = {};
    for (const i of rc) {
      const x = sx(M.px[i]), y = sy(M.py[i]);
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      const r = D.cells.regions[D.cells.region[i]]; regions[r] = (regions[r] || 0) + 1;
    }
    const span = Math.hypot(x1 - x0, y1 - y0);
    if (span < 44) {
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rr = Math.max(13, span / 2 + 7);
      ctx.beginPath(); ctx.arc(cx, cy, rr, 0, 2 * Math.PI); ctx.lineWidth = 4; ctx.strokeStyle = C.ocean; ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, rr, 0, 2 * Math.PI); ctx.lineWidth = 1.8; ctx.strokeStyle = C.ink; ctx.stroke();
      const names = Object.keys(regions), where = names.length === 1 ? ': ' + names[0] : '';
      ctx.font = '600 12px system-ui, sans-serif';
      // the full label where it fits beside the ring, a short one on a narrow map
      let text = '', tx = 0, ty = cy + 4;
      for (const cand of [`${areasN(rc.length)} with ${fInt(M.half)} h or more${where}`, `${areasN(rc.length)}${where}`]) {
        const tw = ctx.measureText(cand).width;
        if (cx + rr + 8 + tw < w - 4) { text = cand; ctx.textAlign = 'left'; tx = cx + rr + 8; break; }
        if (cx - rr - 8 - tw > 4) { text = cand; ctx.textAlign = 'right'; tx = cx - rr - 8; break; }
      }
      if (text) { ctx.lineWidth = 4; ctx.strokeStyle = C.ocean; ctx.strokeText(text, tx, ty); ctx.fillStyle = C.ink; ctx.fillText(text, tx, ty); }
    }
  }
  ctx.textAlign = 'start';
  if (M.focused) {
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.5; ctx.beginPath();
    ctx.moveTo(w / 2 - 12, h / 2); ctx.lineTo(w / 2 + 12, h / 2); ctx.moveTo(w / 2, h / 2 - 12); ctx.lineTo(w / 2, h / 2 + 12); ctx.stroke();
  }
}
function drawMatchPin(ctx, x, y, rank) {
  ctx.save();
  ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2);
  ctx.fillStyle = css('--surface'); ctx.fill();
  ctx.lineWidth = 5; ctx.strokeStyle = css('--surface'); ctx.stroke();
  ctx.lineWidth = 2; ctx.strokeStyle = css('--ui'); ctx.stroke();
  ctx.font = 'bold 11px system-ui, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = css('--ink'); ctx.fillText(String(rank), x, y);
  ctx.restore();
}
function drawMatchPins(ctx, points) {
  const occupied = [];
  for (const point of points) {
    let x = point.x, y = point.y;
    for (let attempt = 0; occupied.some((p) => Math.hypot(x - p.x, y - p.y) < 24) && attempt < 80; attempt++) {
      const angle = attempt * Math.PI / 4, radius = 24 * (1 + Math.floor(attempt / 8));
      x = point.x + Math.cos(angle) * radius; y = point.y + Math.sin(angle) * radius;
    }
    if (x !== point.x || y !== point.y) {
      ctx.save(); ctx.strokeStyle = css('--ui'); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(point.x, point.y); ctx.lineTo(x, y); ctx.stroke();
      ctx.beginPath(); ctx.arc(point.x, point.y, 3, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
    }
    occupied.push({ ...point, x, y }); drawMatchPin(ctx, x, y, point.rank);
  }
  return occupied;
}
function cellAt(x, y, reach) {
  const match = M.matchPins?.find((pin) => Math.hypot(x - pin.x, y - pin.y) <= 12);
  if (match) return match.area;
  const k = scale(), limit = Math.max(reach || 9, k * CELL_UNIT * 0.75);
  let best = -1, bd = limit * limit;
  for (let i = 0; i < D.n; i++) {
    if (M.mk[i] === 3) continue;
    const dx = sx(M.px[i]) - x, dy = sy(M.py[i]) - y, d = dx * dx + dy * dy;
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}
function periodWords(dates = true) {
  const s = D.meta.seasons;
  if (S.period === 'bin') return binLabel(S.bin);
  if (S.period === 'winter') return 'winter half' + (dates ? ' (' + s.winter_text + ')' : '');
  if (S.period === 'summer') return 'summer half' + (dates ? ' (' + s.summer_text + ')' : '');
  if (S.period === 'rock') return 'rock season' + (dates ? ' (' + s.rock_season_text + ')' : '');
  return 'whole year';
}
function stepWords(i) {
  if (S.step === 1) return 'Sun only';
  if (!D.isN[i]) return S.step === 2 ? 'rock season only, snow not measured' : S.step === 3 ? 'rock season, after terrain' : 'rock season, after terrain and typical cloud';
  return S.step === 2 ? 'on snow-free ground' : S.step === 3 ? 'after snow and terrain' : 'after snow, terrain and typical cloud';
}
function tipHtml(i) {
  const v = Number.isNaN(M.val[i]) ? null : M.val[i], mk = M.mk[i];
  const name = D.cells.site[i] ? esc(D.cells.site[i]) + ' · ' : '';
  let line = v == null ? 'No figure: ' + whyUnknown(i, S.step) : `${fH(v)} h of low Sun, ${stepWords(i)}`;
  if (mk === 1 && D.status[i] === 'doubtful') line += ' (snow doubtful: the lower of two estimates)';
  return `<b>${name}${esc(D.cells.regions[D.cells.region[i]])}</b>${fLat(D.lat[i])}, ${fLon(D.lon[i])}<br>${line}<br><span style="color:var(--ink2)">${esc(periodWords())}</span>`;
}
function showTip(i, x, y) {
  const tip = $('tip');
  if (i < 0) { tip.hidden = true; if (M.hover !== -1) { M.hover = -1; drawMap(); } return; }
  tip.innerHTML = tipHtml(i); tip.hidden = false;
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  tip.style.left = Math.max(4, Math.min(M.w - tw - 4, x + 14)) + 'px';
  tip.style.top = Math.max(4, Math.min(M.h - th - 4, y - th - 10)) + 'px';
  if (M.hover !== i) { M.hover = i; drawMap(); }
}
function hoverAt(x, y) { const i = cellAt(x, y); showTip(i, x, y); }
function centreTip() { if (!M.focused) return; const i = cellAt(M.w / 2, M.h / 2, 40); showTip(i, M.w / 2, M.h / 2); }

// ---------- guided views: each button sets the whole state through the URL fragment ----------
function todayBin() {
  const now = new Date(), day = Math.min(365, Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(now.getFullYear(), 0, 1)) / 864e5) + 1);
  const b = D.meta.bins.findIndex((x) => day >= x.first_day && day <= x.last_day);
  return b < 0 ? NB - 1 : b;
}
// Where to look: the middle of a group of areas, and a zoom at which the group fills about a third of the map.
function frame(cellsIn, isNorth, zMin, zMax) {
  if (!cellsIn.length) return null;
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const i of cellsIn) { const p = proj(D.lat[i], D.lon[i], isNorth); x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  const span = Math.max(x1 - x0, y1 - y0, 1e-4), fit = 2 * Math.tan(((isNorth ? 32.5 : 29) * Math.PI) / 360);
  return { z: Math.max(zMin, Math.min(zMax, (0.7 * fit) / span)), x: (x0 + x1) / 2, y: (y0 + y1) / 2 };
}
function guideViews() {
  if (M.guides && M.guidesFor === D.meta.generated) return M.guides;
  const m = D.meta, def = defaultTarget(), dt = m.targets.findIndex((t) => t.id === def), hard = hardest();
  const half = halfLevel(), lastStep = defaultStep();
  const measuredN = (i) => D.isN[i] && D.status[i] === 'measured' && D.cells.gridded[i] === '1';
  // the winter exception: the measured areas that keep the level in the winter half (or, failing that, the top of the winter list)
  let winterCells = [];
  for (let i = 0; i < D.n; i++) if (measuredN(i)) { const w = yr(i, 'snow_free_winter', dt); if (w != null && w >= half) winterCells.push(i); }
  if (!winterCells.length) winterCells = (D.sites.top[def].winter || []).slice(0, 3).map((r) => r.cell);
  const winterRegion = winterCells.length ? D.cells.regions[D.cells.region[winterCells[0]]] : null;
  const wf = frame(winterCells, true, 4, 12);
  const haughton = D.sites.named.find((s) => /Haughton/i.test(s.name));
  const view = (label, small, tip, st) => ({ label, small, tip, st });
  const dn = m.targets[dt].short;
  const out = [
    view('Winter, Sun only', 'low Sun everywhere', `The winter half with the Sun alone: ${dn}'s low Sun is everywhere.`, { view: 'arctic', target: def, step: 1, period: 'winter' }),
    view('Winter, snow-free', 'almost nothing left', 'The winter half on snow-free ground: almost nothing is left.', { view: 'arctic', target: def, step: 2, period: 'winter' }),
  ];
  if (wf && winterRegion) out.push(view(`${winterRegion} in winter`, 'the exception', `${winterRegion}, the winter exception. The view zooms in on the areas that keep their hours.`, { view: 'arctic', target: def, step: 2, period: 'winter', ...wf }));
  out.push(view('Summer nights', 'where the hours are', 'The summer half: the hours of low Sun are here.', { view: 'arctic', target: def, step: lastStep, period: 'summer' }));
  // the hardest site is shown whole: on the one colour scale the whole Arctic is pale, and that is the point
  if (hard.id !== def) out.push(view('The most difficult lunar region', hard.short, `${hard.name} has the lowest Sun. On the same colour scale, the whole Arctic is pale.`, { view: 'arctic', target: hard.id, step: 2, period: 'summer' }));
  if (haughton) {
    const p = proj(D.lat[haughton.cell], D.lon[haughton.cell], true);
    out.push(view('Devon Island', 'rover test, July 2001', 'Devon Island: in July 2001, a team tested a rover here that followed the Sun. The view opens its place card.', { view: 'arctic', target: def, step: lastStep, period: 'summer', place: D.cells.ids[haughton.cell], z: 6, x: p[0], y: p[1] }));
  }
  out.push(view('Antarctica', 'snow not measured', 'Antarctica in its rock season. Snow is not measured there.', { view: 'antarctic', target: def, step: Math.min(3, Math.max(2, lastStep)), period: 'rock' }));
  out.push(view('This ten-day period', binLabel(todayBin()), `The ten-day period that holds today's date: ${binLabel(todayBin())}.`, { view: 'arctic', target: def, step: lastStep, period: String(todayBin()) }));
  M.guides = out; M.guidesFor = D.meta.generated;
  return out;
}
function guideHref(st) {
  const p = new URLSearchParams();
  p.set('view', st.view); p.set('target', st.target); p.set('step', st.step); p.set('period', st.period);
  if (st.place) p.set('place', st.place);
  p.set('theme', S.theme);
  p.set('dest', S.dest); if (S.msite) p.set('msite', S.msite);
  p.set('mgoal', S.mgoal); if (S.msquare) p.set('msquare', S.msquare);
  p.set('stage', S.stage); p.set('tab2', S.tab2);
  if (S.only) p.set('only', S.only);
  if (st.z) { p.set('z', st.z.toFixed(2)); p.set('x', Math.round(st.x * 1000)); p.set('y', Math.round(st.y * 1000)); }
  return '#' + p.toString();
}
function renderGuides() {
  const now = (st) => st.view === S.view && st.target === S.target && +st.step === S.step && String(st.period) === (S.period === 'bin' ? String(S.bin) : S.period)
    && (st.place || null) === (S.place || null) && (st.z ? Math.abs(st.z - S.z) < 0.02 && Math.abs(st.x - S.x) < 0.002 && Math.abs(st.y - S.y) < 0.002 : S.z <= 1.01);
  $('guides').innerHTML = '<span class="guides-label">Views</span>' + guideViews().map((g, k) =>
    `<a class="guide" data-guide="${k}" href="${guideHref(g.st)}" title="${esc(g.tip)}"${now(g.st) ? ' aria-current="true"' : ''}>${esc(g.label)}<small>${esc(g.small)}</small></a>`).join('');
}

function renderMapChrome() {
  const m = D.meta, t = target(), isNorth = north(), seas = m.seasons;
  const mk = (host, items, current, key) => {
    host.innerHTML = items.map(([value, label, small, off]) => `<button type="button" data-v="${value}" aria-pressed="${String(value) === String(current)}" ${off ? 'disabled' : ''}>${label}${small ? `<small>${small}</small>` : ''}</button>`).join('');
    host.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
      const patch = { [key]: b.dataset.v };
      if (key === 'view') Object.assign(patch, { z: 1, x: 0, y: 0 });
      set(patch);
    }));
  };
  mk($('ctl-view'), [['arctic', 'Arctic'], ['antarctic', 'Antarctic', 'snow not measured']], S.view, 'view');
  const shortDates = (s) => s.replace(/(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]+/g, '$1');
  const periods = isNorth ? [['year', 'Whole year'], ['winter', 'Winter half', shortDates(seas.winter_text)], ['summer', 'Summer half', shortDates(seas.summer_text)], ['bin', 'One ten-day period']]
    : [['year', 'Whole year'], ['rock', 'Rock season', shortDates(seas.rock_season_text)], ['bin', 'One ten-day period']];
  mk($('ctl-period'), periods, S.period, 'period');
  $('slider-control').hidden = S.period !== 'bin';
  $('ctl-bin').value = S.bin; $('bin-label').textContent = binLabel(S.bin);
  $('ctl-bin').setAttribute('aria-valuetext', binLabel(S.bin));
  $('ctl-little').checked = S.little;
  renderGuides();
  // title: one clause, one figure
  const c = M.count, per = periodWords(), place = isNorth ? 'Arctic' : 'Antarctic';
  const lead = !isNorth && S.step === 2 && S.period === 'rock' ? 'Rock season only' : `${cap(periodWords(false))}, ${stepTitle(S.step)}`;
  const outside = c.hollow - c.hollowSearch;   // named places outside the search
  const andOutside = outside > 0 ? `, and ${words(outside)} named ${outside === 1 ? 'place' : 'places'} outside the search` : '';
  let title;
  if (S.period === 'bin') {
    const d = calendarData();
    const series = S.step === 1 ? d.sunAll : S.step === 2 ? d.snowAll : S.step === 3 ? d.open : d.clear;
    const tot = series ? sum(series) : 0;
    title = `${lead}: this ten-day period holds ${tot > 0 ? fPct((series[S.bin] || 0) / tot) : 'none'} of the year's low-Sun hours for ${t.short}`;
  } else if (S.step === 4) {
    // never "0 areas after cloud" on its own: the share of hours kept says more, and says it honestly
    title = `${lead}: a rough estimate by our own rule. For ${t.short}, ${c.before > 0 ? 'approximately ' + fPct(c.after / c.before) : 'none'} of the hours after terrain are left`;
  } else if (!isNorth && S.step >= 2) {
    title = `${lead}: ${areasN(c.hollowSearch)} in Antarctica, snow not measured`;
  } else {
    title = `${lead}: ${fInt(c.reach)} of ${fInt(c.firm)} ${place} measured areas reach ${fInt(M.half)} hours of ${t.short}'s low Sun`;
  }
  $('map-title').textContent = title;
  $('map-summary').textContent = title + `. ${cap(areasN(c.grey))} ${c.grey === 1 ? 'has' : 'have'} no figure.`;
  // note on the map
  const note = [];
  if (!isNorth && S.step >= 2) note.push(`Snow is not measured in Antarctica. Colours show the rock season only (${seas.rock_season_text}).`);
  if (S.step === 4) note.push(`Mean cloud is not the chance that a low Sun is visible.${m.cloud_grid_km ? ` Each box, approximately ${fInt(m.cloud_grid_km)} km from north to south, has one cloud figure for each month. The figure includes day and night.` : ''}`);
  if (S.little) note.push(`The page hides ${areasN(c.hiddenKnown)} in or near known analog sites.` + (c.notAssessed ? ` The page still shows ${areasN(c.notAssessed)} that we did not check against the list of known sites.` : ''));
  $('map-note').hidden = !note.length; $('map-note').textContent = note.join(' ');
  // legend
  const colours = ramp();
  document.documentElement.style.setProperty('--zero', colours[0]);
  const spell = m.long_rule.spell_h;
  let marks = `<div class="key"><span class="mark zero"></span><span>Faintest colour: in the search, but ${S.period === 'bin' ? 'no such hours in this period' : 'no such hours'} (${areasN(c.zero)})</span></div>`;
  if (c.hollow && isNorth) {
    marks += `<div class="key"><span class="mark hollow"></span><span>Hollow: snow doubtful (${areasN(c.hollowSearch)}${andOutside}). The snow maps kept the same value through a polar winter. The colour is the lower of two estimates. Hollow areas have no rank.</span></div>`;
  } else if (c.hollow) {
    marks += `<div class="key"><span class="mark" style="background:${colours[32]}"></span><span>All Antarctic marks: snow not measured (${areasN(c.hollowSearch)}${andOutside}). The colour counts the rock season only. At a close view, the marks are hollow.</span></div>`;
  }
  if (c.grey) {
    const why = {};   // one entry for each kind of reason: the words before a colon
    for (const [w, k] of Object.entries(M.greyWhy)) { const kind = w.split(':')[0]; why[kind] = (why[kind] || 0) + k; }
    marks += `<div class="key"><span class="mark grey"></span><span>Grey: no figure, not zero (${areasN(c.grey)}). Why: ${Object.entries(why).sort((a, b) => b[1] - a[1]).map(([w, k]) => `${esc(w)} (${fInt(k)})`).join('; ')}.</span></div>`;
  }
  $('map-legend').innerHTML = `<div class="ramp"><div class="ramp-title">Hours of low Sun in spells of ${spell} hours or more, ${esc(per)}. The scale is the same for all ${m.targets.length} lunar regions.</div><canvas id="ramp-canvas" width="252" height="12" role="img" aria-label="Colour scale from 0 to ${M.max} hours"></canvas><div class="ticks"><span>above 0 h</span><span>${fInt(M.max / 2)}</span><span>${fInt(M.max)} or more</span></div></div><details class="fold map-marks"><summary>Map marks: zero, hollow and unknown</summary><div class="marks">${marks}</div></details>`;
  const rc = $('ramp-canvas').getContext('2d');
  for (let x = 0; x < 252; x++) { rc.fillStyle = colours[1 + Math.floor(x / 4)]; rc.fillRect(x, 0, 1, 12); }
  $('little-label').textContent = 'Hide known analog sites';
}

// ---------- place card ----------
function bestRanges(values) {
  const max = Math.max(...values.map((v) => v || 0));
  if (!(max > 0.25)) return null;
  let bins = values.map((v, b) => [b, v || 0]).filter(([, v]) => v >= 0.5 * max).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([b]) => b).sort((a, b) => a - b);
  const runs = [];
  for (const b of bins) { const last = runs[runs.length - 1]; if (last && b === last[1] + 1) last[1] = b; else runs.push([b, b]); }
  if (runs.length > 1 && runs[0][0] === 0 && runs[runs.length - 1][1] === NB - 1) { const tail = runs.pop(); runs[0][0] = tail[0]; }
  const B = D.meta.bins;
  // at most three ranges are named, the ones with the most hours, so the sentence stays short
  const inRun = ([a, b], k) => (a <= b ? k >= a && k <= b : k >= a || k <= b), hoursIn = (r) => sum(bins.filter((k) => inRun(r, k)).map((k) => values[k]));
  const named = runs.length > MAX_RANGES ? runs.filter((r) => runs.slice().sort((x, y) => hoursIn(y) - hoursIn(x)).slice(0, MAX_RANGES).includes(r)) : runs;
  const text = named.map(([a, b]) => `${B[a].label.split('-')[0]} to ${B[b].label.split('-')[1]}`);
  return { text: text.length > 1 ? text.slice(0, -1).join(', ') + ' and ' + text[text.length - 1] : text[0], total: sum(bins.map((b) => values[b])), bins };
}
function timeOfDay(i) {
  const isN = !!D.isN[i], tid = S.target;
  let p = D.flat.targets[tid].poleward[D.cells.flat_row[i]];
  p = !Number.isFinite(p) || p < 0 ? null : p / 1000;
  if (!isN && S.step >= 2) { const sp = southYear(i, 'poleward'); if (sp != null) p = sp; }
  if (p == null) return null;
  const pole = isN ? 'north' : 'south', other = isN ? 'south' : 'north';
  if (p >= 0.5) return { p, text: `Mostly near midnight, with the Sun in the ${pole} (${fPct(p)} of the hours).` };
  if (p <= 0.2) return { p, text: `At dawn, dusk and low noon, with the Sun in the ${other} (${fPct(1 - p)} of the hours).` };
  return { p, text: `Partly near midnight, with the Sun in the ${pole} (${fPct(p)}), and partly at dawn and dusk.` };
}
const winters = (n) => (n === 1 ? 'one whole winter' : `${words(n)} whole winters`);
const MAX_WORDS = 25;   // no sentence on the page is longer than this
const MAX_RANGES = 3;   // a "best dates" line names at most this many date ranges
const POLAR_CIRCLE = 66.56;   // poleward of this latitude the Sun stays down for part of the winter
const fT = (v) => (v < 0 ? '−' + Math.abs(v) : String(v));   // a temperature with a true minus sign
const wordCount = (s) => s.trim().split(/\s+/).filter(Boolean).length;
const aboutKm = (km) => !Number.isFinite(km) ? 'distance unknown' : (km < 0.5 ? 'less than 1 km' : `approximately ${fInt(km)} km`);   // a station at the place itself is not "0 km" away
const listWords = (a) => (a.length > 1 ? a.slice(0, -1).join(', ') + ' or ' + a[a.length - 1] : a[0] || '');
function scienceText(text) {
  const superscript = { '-': '⁻', '+': '⁺', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };
  return String(text ?? '').replace(/\b(\d+(?:\.\d+)?) x 10\^([+-]?\d+)/g, (_, n, exponent) => `${n} × 10${[...exponent].map((digit) => superscript[digit]).join('')}`)
    .replace(/\bm\/s2\b/g, 'm/s²').replace(/(^|[\s(])-(?=\d)/g, '$1−').replace(/(\d) degrees\b/g, '$1°');
}
function sentences(text) {
  const out = [], s = String(text == null ? '' : text);
  let cur = '';
  for (let k = 0; k < s.length; k++) {
    cur += s[k];
    if ('.!?'.includes(s[k]) && (k + 1 === s.length || (/\s/.test(s[k + 1]) && /[A-Z0-9'"(]/.test(s[k + 2] || 'A')))) { out.push(cur.trim()); cur = ''; }
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}
// The sentences of a stored text that are short enough to print. A long one is cut at its semicolons, and then
// at ", and the" or ", but the", where a new clause begins. A piece that is still too long, or only a word or
// two ("Yes, both."), is left out.
function fit(text, skip) {
  const out = [];
  for (const s of sentences(scienceText(text))) {
    const pieces = (wordCount(s) > MAX_WORDS ? s.split(/;\s+/) : [s]).flatMap((p) => (wordCount(p) > MAX_WORDS ? p.split(/, (?:and|but) (?=the )/) : [p]));
    for (let p of pieces) {
      p = p.trim().replace(/[.;]+$/, '');
      const n = wordCount(p);
      if (n >= 3 && n <= MAX_WORDS && !(skip && skip.test(p))) out.push(cap(p) + '.');
    }
  }
  return out.join(' ');
}
// Each value on a card says what it rests on.
const TAG = { m: ['measured', 'This figure uses satellite measurements of this area.'], w: ['worked out', 'The code calculates this figure. It is not a measurement at this place.'], u: ['unknown', 'No figure. The page never counts an unknown value as zero.'] };
const tag = (k) => `<span class="tag tag-${k}" title="${TAG[k][1]}">${TAG[k][0]}</span>`;
const outLink = (href, text) => `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(text)}</a>`;

// ---------- NASA Worldview link ----------
// The format was read from Worldview itself (its configuration and the address it writes back): p names the polar
// view, v the corners of the view in metres of that view's map projection, l the layers from top to bottom, t the
// day. The projections are WGS84 polar stereographic: true scale at 70° N with 45° W pointing down (arctic), and
// true scale at 71° S with 0° pointing up (antarctic). Tested on one Arctic and one Antarctic area.
const WV = { base: 'https://worldview.earthdata.nasa.gov/', layers: 'Coastlines_15m,MODIS_Terra_NDSI_Snow_Cover,MODIS_Terra_CorrectedReflectance_TrueColor', halfWidthM: 110000, halfHeightM: 66000 };
function polarXY(lat, lon) {
  const a = 6378137, f = 1 / 298.257223563, e2 = 2 * f - f * f, e = Math.sqrt(e2), rad = Math.PI / 180;
  const isN = lat >= 0, phi = Math.abs(lat) * rad, phiC = (isN ? 70 : 71) * rad, lam = (lon - (isN ? -45 : 0)) * rad;
  const tf = (p) => Math.tan(Math.PI / 4 - p / 2) / (((1 - e * Math.sin(p)) / (1 + e * Math.sin(p))) ** (e / 2));
  const rho = (a * (Math.cos(phiC) / Math.sqrt(1 - e2 * Math.sin(phiC) ** 2)) * tf(phi)) / tf(phiC);
  return isN ? [rho * Math.sin(lam), -rho * Math.cos(lam)] : [rho * Math.sin(lam), rho * Math.cos(lam)];
}
function worldview(lat, lon, bin) {
  const year = new Date().getUTCFullYear() - 1;   // the last full year
  const b = D.meta.bins[bin], d = new Date(Date.UTC(year, 0, Math.round((b.first_day + b.last_day) / 2)));
  const [x, y] = polarXY(lat, lon);
  const v = [x - WV.halfWidthM, y - WV.halfHeightM, x + WV.halfWidthM, y + WV.halfHeightM].map(Math.round).join(',');
  return { href: `${WV.base}?v=${v}&p=${lat >= 0 ? 'arctic' : 'antarctic'}&l=${WV.layers}&t=${d.toISOString().slice(0, 10)}-T12:00:00Z`, day: `${d.getUTCDate()} ${MONTH_LONG[d.getUTCMonth()]} ${year}` };
}

// ---------- what you could rehearse: two or three suggestions picked by rule from the area's own figures ----------
const LIKE = 0.6;   // slopes count as "like the lunar region's" from this likeness on (scale 0 to 1)
function gentleSlope() {   // "gentle" ground is no steeper than the middle area among those with a slope figure
  if (M.gentle == null) M.gentle = quantile(D.cells.slope.filter((v) => v >= 0), 0.5) / 10;
  return M.gentle;
}
function rehearse(i, a) {   // a: figures the card has worked out already
  const m = D.meta, t = target(), c = D.cells, half = halfLevel(), H = a.OP != null ? a.OP : a.SF;
  if (H == null || H < 1) return [];
  const out = [], slope = c.slope[i] >= 0 ? c.slope[i] / 10 : null, terr = yr(i, 'terrain'), sm = m.sun_motion, P = placesIndex();
  if (H >= half && slope != null && slope <= gentleSlope()) out.push(`Rehearse navigation in long shadows. This place has ${fH(H)} hours a year on gentle ground (typical slope ${slope.toFixed(1)}°).`);
  if (c.rock[i]) out.push('Collect samples of anorthosite. Use tools on this pale rock of the lunar highlands.');
  if (H >= half / 2 && sm) out.push(`Test how the rover drives relative to the Sun. The direction of the Sun changes by ${sm.swing_in_one_spell_deg.earth[0]}° to ${sm.swing_in_one_spell_deg.earth[1]}° in a ${sm.swing_in_one_spell_deg.spell_h}-hour spell.`);
  if (terr != null && terr >= LIKE) out.push(`Test the rover on slopes like ${t.short}'s. Their likeness is ${terr.toFixed(2)} on a scale from 0 to 1.`);
  // a lamp simulator needs gear and power: suggested where a station is near or teams have worked before
  if (P) {
    const ant = P.ant.get(i), near = P.near.get(i), radius = P.file.radius_km;
    const st = ant && ant.nearest_station_km <= radius ? { name: ant.nearest_station, km: ant.nearest_station_km }
      : near && near.point && near.point.station && near.point.station.km <= radius ? near.point.station : null;
    if (st) out.push(`Compare a lamp simulator with the real Sun. The nearest station, ${st.name}, is ${aboutKm(st.km)} away.`);
    else if (isKnown(i)) out.push('Compare a lamp simulator with the real Sun. Field teams worked in this region before.');
  }
  out.push(`Test camera exposure against a low Sun. The Sun stays below ${t.limit_deg.toFixed(2)}° for ${m.long_rule.spell_h} hours or more in one spell.`);
  if (a.tod && a.tod.p <= 0.2) out.push('Do the tests in the day. The low Sun comes at dawn, dusk and low noon.');
  else if (a.tod && a.tod.p >= 0.5) out.push('Rehearse crew work at night. Most of these hours occur near midnight.');
  return out.slice(0, 3);
}

// ---------- place card: the challenge's three questions, what to rehearse, practical notes, links ----------
function tempChart(earth, lunar, name) {
  const W = 340, H = 66, L = 14, R = 14, lo = Math.floor((Math.min(lunar, earth) - 10) / 50) * 50, hi = Math.ceil((Math.max(lunar, earth, 0) + 10) / 50) * 50;
  const X = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R), y = 40;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Temperature scale: ${fT(earth)} degrees Celsius here, ${fT(lunar)} at ${esc(name)}">`;
  s += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="var(--axis)"/>`;
  for (let v = lo; v <= hi; v += 50) s += `<line x1="${X(v)}" x2="${X(v)}" y1="${y}" y2="${y + 4}" stroke="var(--axis)"/><text x="${X(v)}" y="${H - 4}" text-anchor="middle">${fT(v)}°</text>`;
  s += `<line x1="${X(lunar)}" x2="${X(earth)}" y1="${y}" y2="${y}" stroke="var(--ghost2)" stroke-width="3"/>`;
  s += `<circle cx="${X(lunar)}" cy="${y}" r="5" fill="var(--ink)"/><text class="direct" x="${Math.max(L - 6, X(lunar) - 8)}" y="26" text-anchor="start">${esc(name)} ${fT(lunar)} °C</text>`;
  s += `<circle cx="${X(earth)}" cy="${y}" r="5" fill="var(--accent)" stroke="var(--surface)" stroke-width="1.5"/><text class="direct" x="${Math.min(W - R + 6, X(earth) + 8)}" y="12" text-anchor="end">here ${fT(earth)} °C</text>`;
  return s + '</svg>';
}
function renderCard() {
  const card = $('card'), layout = card.parentElement;
  const i = S.place && D.idx.has(S.place) ? D.idx.get(S.place) : -1;
  if (i < 0 || S.dest !== 'moon') { card.hidden = true; drawerVisible(false); M.cardFor = null; return; }
  for (const id of ['tools', 'planner', 'factors', 'extra', 'sky', 'env', 'cross', 'ask']) loadModule(id);
  const c = D.cells, m = D.meta, t = target(), isN = !!D.isN[i], st = D.status[i], spell = m.long_rule.spell_h;
  const F = flatYear(i), SF = isN ? yr(i, 'snow_free') : southYear(i, 'rock_flat'), OP = isN ? yr(i, 'open') : southYear(i, 'rock_open'), CL = isN ? yr(i, 'clear') : southYear(i, 'rock_clear');
  const hasH = c.horizon_n[i] != null;
  const lastStep = OP != null ? 3 : SF != null ? 2 : 1;
  const perBin = Array.from({ length: NB }, (_, b) => binValue(i, b, lastStep));
  const flatBins = Array.from({ length: NB }, (_, b) => flatBin(i, b));
  const best = bestRanges(perBin), tod = timeOfDay(i);
  const site = c.site[i], region = c.regions[c.region[i]];
  const rock = c.rock[i], known = c.known[i], use = earlierUse(i), P = placesIndex();
  const noteH = c.horizon_note[i] != null ? c.horizon_note_labels[c.horizon_note[i]] : 'no terrain figure';
  const limit = t.limit_deg.toFixed(2);
  // the one-sentence verdict
  let verdict;
  if (!isN) {
    verdict = OP != null && OP >= 1 && best
      ? `Snow is not measured here. Thus, this place can be a match in summer only. Best dates: ${best.text}. In the rock season, the hills do not hide approximately ${fH(OP)} hours of ${t.short}'s low Sun.`
      : SF != null && SF >= 1 && best ? `Snow is not measured here. In the rock season, the Sun gives ${fH(SF)} hours of ${t.short}'s low Sun. ${OP != null ? `After the hills, ${fH(OP)} of these hours are left.` : 'This area has no terrain figure. Thus, the hours do not include the effect of hills.'} Best dates: ${best.text}.`
        : `This place is not a match for ${t.short}. In the rock season (${m.seasons.rock_season_text}), the Sun here is not this low for ${spell} hours in one spell.`;
  } else if (F === 0) {
    verdict = `This place is not a match for ${t.short}. At this latitude, the Sun is never this low for ${spell} hours in one spell.`;
  } else if (st === 'no data') {
    verdict = `The page gives no verdict. The Sun gives ${fH(F)} hours a year of ${t.short}'s low Sun here. The snow maps have no land pixel for this area. Thus, the hours on snow-free ground are unknown.`;
  } else if (st === 'doubtful') {
    const d = (c.doubtful[i] || {})[t.id] || [];
    const lo = d[0] >= 0 ? d[0] / 10 : SF, hi = d[1] >= 0 ? d[1] / 10 : null;
    verdict = `The snow data is doubtful. Between ${fH(lo)}${hi != null ? ' and ' + fH(hi) : ''} hours per year of ${t.short}'s low Sun reach snow-free ground.${OP != null ? ` After terrain, the lower figure is ${fH(OP)}.` : ''}${best ? ` Best dates: ${best.text}.` : ''} The snow maps kept the value "snow-free" through ${winters(c.stuck_winters[i] || 0)} here. Thus, the area has no rank.`;
  } else if (SF == null) {
    verdict = `The page gives no verdict. The snow odds for part of the year are missing here. The Sun alone gives ${fH(F)} hours a year.`;
  } else if (!best || (OP != null ? OP : SF) < 1) {
    verdict = F > 0 ? `This place is not a match for ${t.short}. The Sun gives ${fH(F)} hours per year of this low Sun. But ${SF < 1 ? 'the ground has snow then' : 'the hills hide it'}.`
      : `This place is not a match for ${t.short}. At this latitude, the Sun is never this low for ${spell} hours in one spell.`;
  } else if (OP != null) {
    verdict = `Best dates: ${best.text}. Approximately ${fH(OP)} hours a year of ${t.short}'s low Sun reach ${c.bare[i] > 0 ? 'bare, snow-free' : 'snow-free'} ground here.${c.bare[i] === 0 ? ' The map shows no bare ground in this area.' : ''}`;
  } else {
    verdict = `Best dates: ${best.text}. Approximately ${fH(SF)} hours per year of ${t.short}'s low Sun reach snow-free ground over a flat horizon. This area has no terrain figure. Thus, the true number of hours is lower.`;
  }
  // the ten-day period with the most hours: its month and date serve the cloud, temperature and satellite lines
  const series = best ? perBin : flatBins;
  let bb = series.reduce((k, v, b) => ((v || 0) > (series[k] || 0) ? b : k), 0);
  const noBest = !(series[bb] > 0);
  if (noBest) bb = todayBin();
  const mo = m.bins[bb].month - 1;

  // 1. what is the same
  const lines = (rows) => `<ul class="lines">${rows.map(([k, v, tg]) => `<li><b>${k}.</b> ${v}${tg ? ' ' + tag(tg) : ''}</li>`).join('')}</ul>`;
  const deg = (v) => fT(+(v / 100).toFixed(1)) + '°';   // a horizon height
  let same;
  if (F > 0) {
    same = lines([
      ['Sun height', `The Sun is up to ${limit}° above the horizon, as at ${esc(t.short)}.`],
      ['Shadows', `A 1 m rock makes a shadow of ${t.shadow_m.toFixed(1)} m or longer.`],
      // where only the Sun is known (no snow figure), these are not "hours left": say what they are
      ['Dates', (OP ?? SF) != null && (OP ?? SF) < 1 ? 'Less than 1 hour remains over the year. Thus, the page suggests no dates.' : best ? `${cap(best.text)}, the periods with the most hours ${lastStep === 1 ? 'of low Sun. The page does not count snow' : 'left'}.` : 'No ten-day period keeps these hours.'],
      ...(tod ? [['Time of day', esc(tod.text)]] : []),
    ]);
  } else same = `<p class="line">The Sun is never this low for ${spell} hours in one spell here. Thus, this place does not match ${esc(t.short)}.</p>`;
  // strip: grey bars Sun only, coloured bars what is left; a row for snow-free odds and a row for cloud
  const W = 340, L = 2, bw = (W - 4) / NB, H = 64, top2 = Math.max(...flatBins, 1);
  let strip = `<svg viewBox="0 0 ${W} ${H + 50}" role="img" aria-label="Hours in each ten-day period of the year, with snow-free odds and cloud">`;
  for (let b = 0; b < NB; b++) {
    const x = L + b * bw, hf = (flatBins[b] / top2) * H, v = perBin[b];
    if (hf > 0) strip += `<rect x="${x + 0.5}" y="${H - hf}" width="${bw - 1}" height="${hf}" fill="${lastStep === 1 ? 'var(--ghost2)' : 'var(--ghost1)'}"/>`;
    if (lastStep > 1 && v != null && v > 0) strip += `<rect x="${x + 0.5}" y="${H - (v / top2) * H}" width="${bw - 1}" height="${(v / top2) * H}" fill="var(--accent)"/>`;
    const o = oddsBin(i, b);
    strip += o == null ? `<rect x="${x + 1}" y="${H + 7}" width="${bw - 2}" height="9" fill="none" stroke="var(--ghost2)" stroke-width="0.6"/>`
      : `<rect x="${x + 0.5}" y="${H + 6}" width="${bw - 1}" height="10" fill="var(--snow)" opacity="${(0.08 + 0.92 * o).toFixed(2)}"/>`;
    const cs = clearShare(i, b);
    strip += cs == null ? `<rect x="${x + 1}" y="${H + 23}" width="${bw - 2}" height="9" fill="none" stroke="var(--ghost2)" stroke-width="0.6"/>`
      : `<rect x="${x + 0.5}" y="${H + 22}" width="${bw - 1}" height="10" fill="var(--cloud)" opacity="${(0.08 + 0.92 * (1 - cs)).toFixed(2)}"/>`;
  }
  strip += `<line x1="0" x2="${W}" y1="${H + 0.5}" y2="${H + 0.5}" stroke="var(--axis)"/>`;
  let day = 1; const md = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  MONTH.forEach((name, k) => { strip += `<text x="${L + Math.min(NB, (day - 1) / 10) * bw + 1}" y="${H + 46}">${name[0]}</text>`; day += md[k]; });
  strip += '</svg>';
  const left = lastStep === 3 ? 'after ' + (isN ? 'snow and ' : '') + 'terrain' : isN ? 'on snow-free ground' : 'in the rock season';
  const stripKey = `Hours in each ten-day period. Grey: Sun only. ${lastStep > 1 ? `Colour: what is left ${left}.` : 'No colour: the hours left are unknown here.'} Cyan row: how often the ground is snow-free. Grey row: cloud.`;
  const stripMore = `Cyan row: how often the ground is snow-free${isN ? '' : ' (not measured here)'}. A darker box means more often. An empty box means no snow figure. Grey row: typical cloud${m.has_cloud ? '. A darker box means more cloud' : ' (not in the data)'}.`;

  // 2. how much
  const top = Math.max(F || 0, 1), doubt = isN && st === 'doubtful';
  const row = (label, v, unknown, lower, kind) => `<div class="row${lower && v != null ? ' doubt' : ''}"><span>${label}</span><span class="fbar${v == null ? ' unknown' : ''}">${v == null ? '' : `<i style="width:${Math.min(100, (v / top) * 100).toFixed(1)}%"></i>`}</span><span class="v">${v == null ? unknown : fH(v) + ' h' + (lower ? ', lower estimate' : '')}</span>${lower && v != null ? '<span></span>' : tag(v == null ? 'u' : kind)}</div>`;
  const funnel = row('Sun only', F, 'no figure', false, 'w')
    + row(isN ? 'Snow-free ground' : 'Rock season only', SF, isN && st === 'no data' ? 'no snow data' : 'no figure', doubt, isN ? 'm' : 'w')
    + row('After terrain', OP, hasH ? 'no figure' : 'no terrain figure', doubt, isN ? 'm' : 'w')
    + row('Typical cloud', CL, m.has_cloud ? 'no figure' : 'not in the data', doubt, 'w');
  const terr = yr(i, 'terrain'), light = yr(i, 'lighting'), full = yr(i, 'full'), full_h = m.scoring.full_hours;
  const whyNot = c.ranked[i] === '1' ? '' : 'Not ranked' + (c.why_not[i] >= 0 ? ': ' + esc(c.why_not_labels[c.why_not[i]]) : '') + '.';
  const scoreLine = light != null ? `Score for light and bare ground: ${light.toFixed(2)} on a scale from 0 to 1. ${tag('w')}${whyNot ? ' ' + whyNot : ''}` : whyNot || 'There is no score because a necessary figure is unknown.';
  const lightShare = OP != null && full_h ? Math.min(1, OP / full_h) : null;
  const factors = `<dl class="factor">
    <dt>Light</dt><dd>${lightShare != null ? `${lightShare.toFixed(2)} of 1 ${tag('w')} The value is the hours left after ${isN ? 'snow and ' : ''}terrain, as a share of the ${fInt(full_h)} h for the maximum score.` : SF != null ? `${fH(SF)} h a year before terrain. There is no share without a terrain figure ${tag('u')}` : `no figure ${tag('u')}`}</dd>
    <dt>Bare ground</dt><dd>${c.bare[i] >= 0 ? `${c.bare[i]}% of the land in the area${c.bare_km2[i] >= 0 ? ` (${fH(c.bare_km2[i] / 10)} km²)` : ''} ${tag('m')}` : `no figure ${tag('u')}`}</dd>
    <dt>Terrain</dt><dd>${hasH ? `Horizon ${deg(c.horizon_n[i])} north, ${deg(c.horizon_s[i])} south ${tag('m')}` : `No terrain figure ${tag('u')}`}${c.slope[i] >= 0 ? ` Typical slope ${(c.slope[i] / 10).toFixed(1)}°.` : ''}${!hasLunarModel(t) ? ` Slopes like this lunar region: ${NO_LUNAR_MODEL}. ${tag('u')}` : terr != null ? ` Slopes like ${esc(t.short)}'s: ${terr.toFixed(2)} of 1 ${tag('w')}` : ''}</dd>
    <dt>Rock</dt><dd>${rock ? `${esc(rock[1])}: match ${(rock[0] / 1000).toFixed(2)} of 1, from a published list` : known === -2 ? `not assessed ${tag('u')}` : 'no listed anorthosite body'}</dd>
    <dt>Light and bare ground</dt><dd>${light != null ? `${light.toFixed(2)} of 1 ${tag('w')} The value is the square root of the light share times the bare share.` : `no score ${tag('u')}`}</dd>
    <dt>All four</dt><dd>${!hasLunarModel(t) ? `${NO_LUNAR_MODEL}. ${tag('u')}` : full != null ? `${full.toFixed(2)} of 1 ${tag('w')} The value is the fourth root of the product of light, terrain, rock and bare ground.` : `no score ${tag('u')} The score must have all four factors.`}</dd>
  </dl>`;

  // 3. what is different
  const diff = [];
  if (!isN) diff.push(['Snow', `Snow is not measured here. The page counts only the rock season (${m.seasons.rock_season_text}).`, 'u']);
  else if (st === 'no data') diff.push(['Snow', 'The snow maps have no land pixel here.', 'u']);
  else if (st === 'doubtful') diff.push(['Snow', `Doubtful: the maps kept the value "snow-free" through ${winters(c.stuck_winters[i] || 0)}.`, 'u']);
  else if (SF != null && F > 0) diff.push(['Snow', `The ground is snow-free for ${fPct(SF / F)} of the low-Sun hours.`, 'm']);
  else diff.push(['Snow', F > 0 ? 'The snow odds are missing for part of the year.' : 'There are no hours of low Sun for snow to hide.', F > 0 ? 'u' : null]);
  if (!hasH) diff.push(['Hills', `${cap(noteH)}. Thus, the hours do not include the effect of hills.`, 'u']);
  else if (OP != null && SF > 0) diff.push(['Hills', `They hide ${fPct(1 - OP / SF)} of those hours (horizon ${deg(c.horizon_n[i])} north, ${deg(c.horizon_s[i])} south).`, 'm']);
  else diff.push(['Hills', `The horizon is ${deg(c.horizon_n[i])} high to the north and ${deg(c.horizon_s[i])} high to the south.`, 'm']);
  const cs = clearShare(i, bb);
  diff.push(['Cloud', cs != null ? `Clouds cover ${Math.round((1 - cs) * 100)}% of the sky in ${MONTH_LONG[mo]}. This is a coarse monthly mean.` : m.has_cloud ? 'There is no cloud figure for this area.' : 'Cloud is not in the data.', cs != null ? 'w' : 'u']);
  // temperature: NASA POWER for the month of the best ten-day period, against the lunar region's Diviner figure
  const tb = extra('temperature.bin', true), moon = extra('moon.json'), ix = X.index;
  const mc = moon ? (moon.cards || []).find((x) => x.id === t.id) : null;
  const lunarMean = mc?.diviner?.annual_mean_temp_2cm_C?.mean;
  const lunar = Number.isFinite(lunarMean) ? Math.round(lunarMean) : null;
  let earth = null, chart = '';
  if (tb === undefined || moon === undefined) diff.push(['Temperature', 'The page will read the temperature figures.']);
  else if (!tb) diff.push(['Temperature', 'The temperature file is not on this copy of the page.', 'u']);
  else {
    const raw = new Int8Array(tb)[i * 12 + mo];
    earth = raw === -128 ? null : raw;
    diff.push(['Temperature', (earth == null ? 'There is no temperature figure for this area.' : `The temperature is approximately ${fT(earth)} °C in ${MONTH_LONG[mo]} (NASA POWER, a model value).`)
      + (lunar != null ? ` At ${esc(t.short)}, it is ${fT(lunar)} °C just under the surface.` : ' The lunar figure is not on this copy of the page.'), earth == null ? 'u' : 'w']);
    if (earth != null && lunar != null) chart = `<div class="tchart">${tempChart(earth, lunar, t.short)}</div>`;
  }
  diff.push(['Rock', rock ? `The area is on a listed anorthosite body: ${esc(rock[1])}.` : known === -2 ? 'We did not assess the rock of this area.' : 'There is no listed anorthosite here. Anorthosite is the pale rock of the lunar highlands.', rock || known !== -2 ? null : 'u']);
  const cannot = mc && mc.earth_cannot_match ? mc.earth_cannot_match.map((e) => e.what) : null;
  diff.push(['Everywhere', (cannot ? `No place on Earth has the Moon's ${esc(listWords(cannot))}.` : 'Air softens shadows. Thus, no place on Earth matches lunar contrast.')
    + ` <button type="button" class="linkish" data-about="${t.id}">See the ${esc(t.short)} card</button>`]);
  // the longer list, behind "more"
  const no = [];
  if (!c.gridded || c.gridded[i] === '0') no.push('This area has insufficient bare ground or land for the search. The page shows it because it is a named place.');
  if (st === 'doubtful') no.push(`The snow data is doubtful. The satellite maps kept the value "snow-free" through ${winters(c.stuck_winters[i] || 0)}. The hours are the lower of two estimates.`);
  if (st === 'unmeasured') no.push(`No open product measures winter snow on Antarctic rock. The page counts only ${m.seasons.rock_season_text}.`);
  if (isN && c.snow_pixels[i] >= 0 && c.snow_block[i] > 0 && c.snow_pixels[i] / c.snow_block[i] < 0.45 && st !== 'no data') no.push(`The snow odds use few map pixels. Only ${fInt(c.snow_pixels[i])} of ${fInt(c.snow_block[i])} nearby pixels are land. The area is on a coast or a small island.`);
  if (terr != null && terr < 0.3) no.push(`The slopes are only a little like the slopes of ${t.short}. Their likeness is ${terr.toFixed(2)} on a scale from 0 to 1.`);
  if (CL != null && OP > 0) no.push(`Typical cloud leaves approximately ${fPct(CL / OP)} of the hours after terrain. Mean cloud is not the chance that a low Sun is visible.`);
  const cr = extra('cloud_regions.json');
  if (cr) {
    const side = isN ? cr.north : cr.south, r = side && (side.regions || []).find((x) => x.region === region);
    if (r && r.median_pct && r.median_pct.both != null) no.push(`In ${region}, the median cloud in ${side.months.join(' and ')} is ${Math.round(r.median_pct.both)}%, against ${Math.round(side.all.median_pct.both)}% for all ${isN ? 'northern' : 'southern'} areas.`);
  }
  if (earth != null) {
    const tm = ix && ix.temperature, gh = tm && tm.grid_height_m ? tm.grid_height_m[i] : null;
    no.push(`The temperature is a mean over all hours of ${MONTH_LONG[mo]}, not over the low-Sun hours. No score uses it.`);
    if (tm && tm.grid_deg) no.push(`It is a model value for a box of ground approximately ${fInt(tm.grid_deg[0] * 111)} km from north to south.${gh != null ? ` Its mean height is ${fInt(gh)} m.` : ''} If a box is much higher than the area, its value is too cold.`);
  }
  if (lunar != null) no.push(`The lunar temperature is ${esc(mc.diviner.label)}: a yearly mean just under the surface, over the whole lunar region.`);
  if (c.bare[i] >= 0 && m.scoring.rank_min_bare != null && c.bare[i] < m.scoring.rank_min_bare * 100) no.push(`The area has little bare ground: ${c.bare[i]}% of its land.`);
  if (c.layers_disagree.includes(i)) no.push('The two maps of rock outcrops do not agree about how much rock is here.');
  no.push('Air softens shadows at each place on Earth. Thus, no place matches lunar contrast.');

  // 4. what you could rehearse, 5. practical notes
  const ideas = rehearse(i, { OP, SF, tod });
  const leftUnknown = F > 0 && OP == null && SF == null;   // the Sun is low here, but no figure says what snow leaves
  const notes = [];
  let credit = '';
  if (known >= 0) notes.push('Known use. ' + esc(c.known_labels[known].split('; ').map(cap).join('. ')) + '.');
  if (P === undefined) notes.push('The page will read the practical notes.');
  else if (P === null) notes.push('The practical notes are not on this copy of the page.');
  else {
    const near = P.near.get(i), ant = P.ant.get(i), why = P.nlk.get(i) || [];
    for (const b of why.slice(0, 2)) notes.push(`Published analog work: ${esc(b.name)}. ${esc(fit(b.why))}${b.source_url ? ' ' + outLink(b.source_url, 'Source') : ''}`);
    if (near) {
      const pl = near.place, pt = near.point || {};
      if (use === 'searched') notes.push(esc(pl.wording) + ' That result comes from one search.');
      if (!ant && pt.station) notes.push(`Nearest station: ${esc(pt.station.name)}, ${aboutKm(pt.station.km)} from the middle of this group of areas.${pt.station.note ? ' ' + esc(fit(pt.station.note)) : ''}`);
      if (pt.airfield) notes.push(`Nearest airfield: ${esc(pt.airfield.name)}, ${aboutKm(pt.airfield.km)} from the middle of this group of areas.`);
      if (!isN && !ant && pt.station) credit = P.file.comnap_credit || '';
    }
    if (ant) {
      notes.push(`Nearest station: ${esc(ant.nearest_station)} (${esc(String(ant.nearest_station_seasonality || '').toLowerCase())}), ${aboutKm(ant.nearest_station_km)} from ${esc(ant.name)}.`);
      if (!ant.station_year_round && ant.nearest_year_round_station && ant.nearest_year_round_station !== ant.nearest_station) notes.push(`Nearest year-round station: ${esc(ant.nearest_year_round_station)}, ${aboutKm(ant.nearest_year_round_station_km)} away.`);
      if (ant.winter_snow_evidence) notes.push(`Other evidence about the ground in winter: ${esc(ant.winter_snow_evidence)}. This is not a measurement of the snow odds for this area.`);
      credit = P.file.comnap_credit || '';
    }
  }
  const pn = P ? (P.ant.get(i) || (P.near.get(i) || {}).place || (P.nlk.get(i) || [])[0]) : null, placeName = pn ? pn.name : '';
  const useBadge = { known: 'known analog region', published: 'published analog work here', unassessed: 'earlier use not assessed', searched: 'no published analog use found', unlisted: 'not near a listed analog site' }[use];
  const lat = D.lat[i], lon = D.lon[i], wv = worldview(lat, lon, bb);
  const dark = isN && Math.abs(lat) >= POLAR_CIRCLE && m.seasons.winter_bins_north.includes(bb);
  // keep what the reader had open when the same card is drawn again
  const sameCard = M.cardFor === S.place;
  const openMore = sameCard ? new Set([...card.querySelectorAll('details[open]')].map((d) => d.dataset.cardFold)) : new Set();
  const focused = sameCard && card.contains(document.activeElement) ? focusKey() : null;
  const scrolled = sameCard ? card.scrollTop : 0;
  const more = (key, label, html, summary) => `<details class="more card-fold" data-more="${key}"><summary><span class="card-fold-title">${label}</span><span class="card-fold-summary">${esc(summary || 'Open this part to see the figures and how the page counts them.')}</span></summary>${html}</details>`;
  card.hidden = false; card.classList.add('sheet');
  card.innerHTML = `<div class="drawer-controls"><button type="button" class="btn close" id="card-close" data-act="close" aria-label="Close the place card">Close</button></div>
    <h3>${esc(site || region)}</h3>
    <div class="where">${site ? esc(region) + ' · ' : ''}${fLat(lat)}, ${fLon(lon)}${placeName && !site ? ' · ' + esc(placeName) : ''}</div>
    <div><span class="badge">${useBadge}</span><span class="badge">${isN ? 'snow ' + (st === 'measured' ? 'measured' : st) : 'snow not measured'}</span><span class="badge">for ${esc(t.short)} (Sun up to ${limit}°)</span></div>
    <p class="verdict">${esc(verdict)}</p>
    <h4>What is the same</h4>${same}
    ${F > 0 ? `${more('same', 'The year at this area', `<div class="strip">${strip}</div><p class="caption">${stripKey}</p><p class="caption">${stripMore}</p><p class="caption">${DRAWN}</p>`, best ? `Most hours: ${best.text}.` : 'There are no known best dates.')}` : ''}
    <h4>How much</h4><div class="funnel">${funnel}</div>
    <p class="line">${scoreLine}</p>
    ${more('much', 'More: the scores and how the page calculates them', factors + `<p class="caption">The hours are per year, in spells of ${spell} hours or more. Measured: from satellite maps of this area. Worked out: calculated, not measured here.</p>`, 'Scores combine hours, bare ground, terrain and rock. Unknown inputs stay unknown.')}
    ${more('different', 'What is different', lines(diff) + chart + (chart ? `<p class="caption">${DRAWN}</p>` : '') + more('diff', 'More: everything that does not match', `<ul>${no.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>`, 'This part gives the limits from snow and terrain, cloud, and model temperatures.'), 'Snow, hills, cloud and temperature differ. Air softens the shadows.')}
    ${more('rehearsal', 'What you can rehearse here',
      ideas.length ? `<ul class="ideas">${ideas.map((x) => `<li>${esc(x)}</li>`).join('')}</ul><p class="caption">The suggestions come from the figures on this card. They are not a plan of any agency.</p>`
        : `<p class="line">${leftUnknown ? 'The hours left after snow are unknown. Thus, the page suggests no rehearsal.' : `The page suggests no rehearsal under ${esc(t.short)}'s light.`}</p>`,
      ideas.length ? ideas[0] : 'The available figures give no rehearsal suggestion.')}
    ${notes.length ? more('practical', 'Practical notes', `<ul class="notes">${notes.map((x) => `<li>${x}</li>`).join('')}</ul>${credit ? `<p class="caption">Station names and distances: ${esc(fit(credit))}</p>` : ''}`, cap(useBadge) + '. Check the access locally.') : ''}
    ${more('links', 'Maps and satellite views', `
    <div class="links"><a href="https://www.openstreetmap.org/?mlat=${lat.toFixed(4)}&amp;mlon=${lon.toFixed(4)}#map=8/${lat.toFixed(4)}/${lon.toFixed(4)}" target="_blank" rel="noopener">Open in OpenStreetMap</a>
      <a href="${esc(wv.href)}" target="_blank" rel="noopener" data-wv="1">NASA Worldview, ${wv.day}</a></div>
    <p class="caption">The link opens a NASA satellite view of the ground on this date, with the MODIS snow-cover layer. ${noBest ? 'The date is in the present ten-day period, because this area has no best period.' : best && lastStep > 1 ? 'The date is in the best ten-day period of this area.' : 'The date is in the ten-day period with the most low-Sun hours here, without the effect of snow.'} The satellite takes the image when it passes, not at the low-Sun hour.${dark ? ' This far north, a winter image can be dark.' : ''}</p>`, 'Open this area in OpenStreetMap or NASA Worldview.')}
    <p class="caption">${DRAWN}</p>`;
  M.cardFor = S.place;
  renderCardExtensions(i, t.id);
  orderCardSections(card);
  card.querySelectorAll('details').forEach((detail, index) => {
    const owner = detail.closest('[data-card-section]');
    const nestedIndex = owner ? [...owner.querySelectorAll('details')].indexOf(detail) : index;
    const key = detail.dataset.more || `${owner?.dataset.cardSection || 'core'}-${nestedIndex}`;
    detail.dataset.cardFold = key; detail.open = openMore.has(key);
    detail.querySelector(':scope > summary')?.setAttribute('data-card-toggle', key);
  });
  if (focused) card.querySelector(focused.sel)?.focus({ preventScroll: true });
  if (scrolled) card.scrollTop = scrolled;
  $('card-close').addEventListener('click', closePlace);
  drawerVisible(true);
  card.querySelectorAll('[data-about]').forEach((b) => b.addEventListener('click', () => openMoon(b.dataset.about)));
}
// The card remembers what opened it, so that closing it puts the keyboard back where it was.
function openPlace(i, move) {
  M.openerElement = document.activeElement;
  M.opener = focusKey() || (document.activeElement === M.canvas ? 'map' : null);
  const patch = { dest: 'moon', place: D.cells.ids[i], x: S.x, y: S.y };
  const wantNorth = !!D.isN[i];
  if (wantNorth !== north()) { patch.view = wantNorth ? 'arctic' : 'antarctic'; move = true; }
  if (move) {
    goHold = null;
    const p = proj(D.lat[i], D.lon[i], wantNorth);
    Object.assign(patch, { z: Math.max(S.z, 6), x: p[0], y: p[1], only: S.only === 'map' ? S.only : null });
  }
  set(patch);

}
function closePlace() {
  const back = M.opener;
  M.opener = null;
  set({ place: null });
  const el = back && back !== 'map' && $(back.host) ? $(back.host).querySelector(back.sel) : null;
  (el || (M.openerElement?.isConnected ? M.openerElement : null) || $('hero-next')).focus({ preventScroll: true });
  M.openerElement = null;
}

// ---------- lunar region cards: one per site, from moon.json ----------
// Opened from the bar ("About this lunar region") and from the section "The light we want to copy". A modal dialog:
// Escape closes it and the keyboard goes back to the button that opened it.
function openMoon(id) {
  M.moonOpener = focusKey();
  set({ moon: id });
}
function closeMoon() {
  if (!S.moon) return;
  const back = M.moonOpener;
  M.moonOpener = null;
  set({ moon: null });
  const el = back && $(back.host) ? $(back.host).querySelector(back.sel) : null;
  if (el) el.focus({ preventScroll: true });
}
const hostLabel = (u) => {
  try { const h = new URL(u).hostname.replace(/^www\./, ''); return { 'nasa.gov': 'NASA news release', 'svs.gsfc.nasa.gov': 'NASA visualization', 'ntrs.nasa.gov': 'NASA technical report' }[h] || h; } catch (e) { return 'source'; }
};
function cannotItems(card) {   // the things no place on Earth has, as list items; used by the lunar region card and by "What Earth cannot copy"
  const ix = X.index, lc = ix && ix.temperature ? ix.temperature.lunar_comparison : null;
  return (card.earth_cannot_match || []).map((e) => {
    const earthText = e.what === 'temperature' && lc && lc.earth_low_c != null && lc.earth_high_c != null
      ? `In their best ten-day periods, the named places have temperatures from ${fT(Math.round(lc.earth_low_c))} °C to ${fT(Math.round(lc.earth_high_c))} °C (NASA POWER).` : fit(e.earth);
    return `<li><b>${esc(cap(e.what))}.</b> ${esc(fit(e.moon, e.what === 'black shadows' ? /m shadow/ : null))}${e.number == null ? ' <span class="tag tag-u">no number</span>' : ''}<span class="earth"><b>Earth.</b> ${esc(earthText)}</span></li>`;
  }).join('');
}
function moonCardHtml(card, t) {
  const ix = X.index, d = card.diviner || {}, lit = card.lit || {}, ps = card.permanent_shadow || {}, sc = card.sun_ceiling || {}, pic = card.picture || {}, nl = card.nasa_list || {};
  const lat = card.centre ? card.centre.lat : null, lonE = card.centre ? card.centre.lon_east : null, lon = lonE == null ? null : lonE > 180 ? lonE - 360 : lonE;
  const ceiling = sc.deg != null ? sc.deg : t.limit_deg;
  const tilt = lat != null && sc.deg != null ? sc.deg - (90 - Math.abs(lat)) : null;
  const kind = (text) => (text ? ` <span class="tag">${esc(text)}</span>` : '');
  const src = (u) => (u ? ' ' + outLink(u, 'Source') : '');
  const C = (o) => (o && o.mean != null ? Math.round(o.mean) : null);
  const rows = [];
  rows.push(['Highest Sun', `${ceiling.toFixed(2)}° above a level horizon${kind(sc.kind)}`,
    (tilt != null ? `It is 90° minus the lunar region's latitude (${fLat(lat)}) plus the tilt of the Moon's axis (${tilt.toFixed(2)}°). ` : '')
    + 'The value does not count hills or the width of the Sun\'s disc.' + (sc.range_deg ? ` Across the lunar region, the value is between ${sc.range_deg[0].toFixed(2)}° and ${sc.range_deg[1].toFixed(2)}°.` : '')]);
  if (!hasLunarModel(t)) rows.push(['Ground at 5 m scale', NO_LUNAR_MODEL + kind('unknown'), 'The page counts the light in full. The slope comparison and combined ground score are unknown.']);
  rows.push(['Shadow of a 1 m object', `${t.shadow_m.toFixed(1)} m or longer${kind('worked out')}`, esc(fit(card.shadow_how))]);
  if (lit.mean_share != null) rows.push(['Time in sunlight', `${fPct(lit.mean_share)} of the time, averaged over the lunar region${lit.best_point_share != null ? `, and ${fPct(lit.best_point_share)} at its best point` : ''}${kind(lit.kind)}`,
    'The value comes from the map of average sunlight by NASA Goddard. The map uses the LOLA laser terrain.' + src(lit.source)]);
  if (ps.share != null) rows.push(['Never lit', `${fPct(ps.share)} of the lunar region is in permanent shadow${kind(ps.kind)}`, '']);
  const mean = C(d.annual_mean_temp_2cm_C), a2 = d.annual_mean_temp_2cm_C || {}, mx = d.annual_max_temp_surface_C || {};
  if (mean != null) rows.push(['Temperature', `${fT(mean)} °C: the yearly mean just under the surface, averaged over the lunar region${kind(d.label)}`,
    (a2.min != null && a2.max != null ? `Across the lunar region, the value is between ${fT(Math.round(a2.min))} and ${fT(Math.round(a2.max))} °C. ` : '')
    + (mx.mean != null && mx.max != null ? `The mean of the yearly maximum at the surface is ${fT(Math.round(mx.mean))} °C. At the hottest point, it is ${fT(Math.round(mx.max))} °C.` : '') + src(d.source)]);
  const ice = d.ice || {};
  if (ice.stable_within_reach_share != null) {
    const wo = ice.stable_within_reach_share_without_undocumented_value;
    rows.push(['Ice', `The model permits stable water ice near the surface in ${fPct(ice.stable_within_reach_share)} of the lunar region${kind(d.label)}`,
      '"Near the surface" means within the depth that the product covers.'
      + (wo == null || wo === ice.stable_within_reach_share ? '' : fPct(wo) === fPct(ice.stable_within_reach_share) ? ' A value that the product\'s label does not explain changes this share only a little.' : ` Without a value that the product's label does not explain, the share is ${fPct(wo)}.`)
      + ' We do not map ice on Earth.']);
  }
  let picture;
  if (pic.page) {
    const sh = pic.sun_heights_of_images;
    picture = [`${outLink(pic.page, pic.title || 'Low-Sun picture')}`, `Credit: ${esc(pic.credit || '')}.` + (sh && sh.images_listed ? ` The Sun was between ${fT(sh.sun_height_min_deg)}° and ${fT(sh.sun_height_max_deg)}° in its ${fInt(sh.images_listed)} images.` : '') + ' The link opens the page of the camera team. This page stores no image.'];
  } else {
    const alt = pic.alternative;
    picture = ['The data names no low-Sun picture for this lunar region.', alt && alt.page ? `${outLink(alt.page, alt.title || 'A terrain model')}. ${esc(fit(alt.what))} Credit: ${esc(alt.credit || '')}.` : ''];
  }
  rows.push(['A real low-Sun picture', picture[0], picture[1]]);
  const seen = {};   // two links of one kind get a number
  const links = (nl.links || []).map((u) => { const l = hostLabel(u); seen[l] = (seen[l] || 0) + 1; return outLink(u, seen[l] > 1 ? `${l} ${seen[l]}` : l); }).join(' · ');
  const cannot = cannotItems(card);
  return `<p class="where">Near the Moon's south pole · ${lat != null ? fLat(lat) + ', ' + fLon(lon) : ''}${hasLunarModel(t) && card.extent_km ? ` · our terrain model is ${fInt(card.extent_km[0])} km across` : ''}</p>
    <p class="list">${esc(fit(nl.summary))} ${links}</p>
    ${card.why && card.why.sourced && card.why.text ? `<p class="list"><b>Why this lunar region.</b> ${esc(fit(card.why.text))}</p>` : ''}
    <div class="draw">${sunDrawing(t)}</div>
    <dl class="facts">${rows.map(([k, v, more]) => `<dt>${k}</dt><dd>${v}${more ? `<small>${more}</small>` : ''}</dd>`).join('')}</dl>
    <h3>What Earth cannot match there</h3>
    <ul class="cannot">${cannot}</ul>
    <p class="actions">${t.id === S.target ? `<span class="caption">The calendar, the map and the lists now show ${esc(t.name)}.</span>` : `<button type="button" class="btn" data-pick="${t.id}">Show ${esc(t.name)} on the calendar and the map</button>`}</p>
    <p class="caption">${hasLunarModel(t) ? 'Lunar terrain: NASA LRO LOLA.' : NO_LUNAR_MODEL + '.'} Sunlight and shadow: NASA Goddard maps. Temperature and ice: ${esc(d.label || 'model-based')}, model values, not measurements. ${DRAWN}</p>`;
}
function renderMoon(force) {
  const dlg = $('moon');
  if (!dlg) return;
  if (!S.moon) { if (dlg.open) dlg.close(); M.moonFor = null; return; }
  if (M.moonFor === S.moon && dlg.open && !force) return;
  const t = D.meta.targets.find((x) => x.id === S.moon), file = extra('moon.json');
  const card = file ? (file.cards || []).find((x) => x.id === S.moon) : null;
  const body = file === undefined ? '<p class="status">The page will read the lunar region card.</p>'
    : card ? moonCardHtml(card, t)
      : `<div class="draw">${sunDrawing(t)}</div><p class="status">The lunar region cards are unavailable because moon.json is missing. The rest of the page works without it.</p>`;
  const keep = M.moonFor === S.moon ? $('moon-body').scrollTop : 0;
  $('moon-body').innerHTML = `<p class="eyebrow">Lunar region card</p><h2 id="moon-title">${esc(card ? card.official_name : t.name)}</h2>` + body;
  $('moon-body').querySelectorAll('[data-pick]').forEach((b) => b.addEventListener('click', () => { M.moonOpener = null; set({ target: b.dataset.pick, moon: null }); }));
  M.moonFor = S.moon;
  if (!dlg.open) { try { dlg.showModal(); } catch (e) { dlg.setAttribute('open', ''); } }
  $('moon-body').scrollTop = keep;
}

// ---------- the short answer: fixed rules, always at the terrain step ----------
const answerData = { access: undefined, mars: undefined, reachable: new Map() };
async function loadAnswerAccess() {
  const index = await getJSON('tools.json');
  const layout = index.files?.['access.bin']?.layout;
  if (!layout || index.areas?.count !== D.n || !index.files?.['airfields.json']) return null;
  const [names, buffer, plan] = await Promise.all([
    getJSON('airfields.json'), getBin('access.bin'), getJSON('yearplan.json').catch(() => null),
  ]);
  const columns = layout.columns;
  if (!Array.isArray(columns) || buffer.byteLength !== D.n * columns.length * Uint16Array.BYTES_PER_ELEMENT) return null;
  if (!['scheduled_index', 'scheduled_km', 'any_index', 'any_km'].every((key) => columns.includes(key))) return null;
  if (index.areas.ids_sha256 && globalThis.crypto?.subtle) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(D.cells.ids.join('\n')));
    const hash = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, '0')).join('');
    if (hash !== index.areas.ids_sha256) return null;
  }
  return { names: names.airfields, view: new DataView(buffer), layout,
    reachKm: Number.isFinite(plan?.reach_km) ? plan.reach_km : null };
}
function loadAnswerData() {
  getJSON('factors.json').catch(() => null).then((data) => {
    answerData.factorCount = Array.isArray(data?.matrix) ? data.matrix.length : null;
    renderInfoStrip();
  });
  loadAnswerAccess().catch(() => null).then((data) => { answerData.access = data; renderAnswer(); renderShell(); notifyState(true); holdGo(); });
  getJSON('mars.json').catch(() => null).then(async (data) => {
    answerData.mars = data; fixState(); renderAnswer(); renderShell(); writeHash(true); notifyState(true); holdGo();
    if (data?.squares?.file) {
      const [world, buffer] = await Promise.all([getJSON('mars_world.json'), getBin(data.squares.file)]).catch(() => []);
      if (world && buffer) { answerData.world = world; answerData.squares = new DataView(buffer); drawStage(); refreshMarsMatches(); renderExperimentResults(); }
    }
  });
  getJSON('sources.json').catch(() => null).then((data) => { if (data?.licence_line && $('footer-licence')) $('footer-licence').textContent = data.licence_line; });
}
function answerAirfield(i) {
  const access = answerData.access;
  if (!access) return null;
  const { columns, unknown } = access.layout;
  const read = (key) => access.view.getUint16((i * columns.length + columns.indexOf(key)) * Uint16Array.BYTES_PER_ELEMENT, true);
  const prefix = D.isN[i] ? 'scheduled' : 'any', n = read(prefix + '_index'), km = read(prefix + '_km');
  return n === unknown || km === unknown || !access.names?.[n] ? null : { ...access.names[n], km };
}
function answerReachable(ti) {
  if (answerData.reachable.has(ti)) return answerData.reachable.get(ti);
  if (!Number.isFinite(answerData.access?.reachKm)) return null;
  let best = null, most = -Infinity;
  for (let i = 0; i < D.n; i++) {
    const airfield = answerAirfield(i);
    if (!airfield || airfield.km > answerData.access.reachKm) continue;
    const hours = cellValue(i, 3, 'year', ti);
    if (Number.isFinite(hours) && hours > most) { best = i; most = hours; }
  }
  answerData.reachable.set(ti, best);
  return best;
}
const placeName = (i) => D.cells.site[i] || D.cells.regions[D.cells.region[i]];
function answerLunarRows(targetId = S.target) {
  const ti = D.meta.targets.findIndex((t) => t.id === targetId), top = D.sites.top[targetId], rows = []; 
  const add = (label, i, period = 'year') => {
    if (!validArea(i)) return;
    const item = { label, period };
    rows.push({ i, rules: [item] });
  };
  add('Best light score', top.north_lighting?.[0]?.cell);
  const reachable = answerReachable(ti);
  if (reachable != null) add('Easiest to reach', reachable);
  else rows.push({ note: answerData.access === undefined ? 'Easiest to reach: the page will read the access figures.'
    : Number.isFinite(answerData.access?.reachKm) ? 'Easiest to reach: no area has known terrain hours within the access limit.'
      : 'Easiest to reach: access figures or their limit are unavailable.' });
  const winter = top.winter?.[0], winterHours = winter ? cellValue(winter.cell, 3, 'winter', ti) : null;
  const floor = D.meta.scoring.full_hours / 2;
  if (winter && Number.isFinite(winterHours) && winterHours >= floor) add('Winter', winter.cell, 'winter');
  else rows.push({ note: !winter ? 'Winter: the page has no winter-list place for this lunar region.'
    : !Number.isFinite(winterHours) ? 'Winter: the hours after terrain for the first place in the winter list are unknown.'
      : `Winter: the first place in the winter list has ${fH(winterHours)} h after terrain. The limit for the winter half is ${fH(floor)} h.` });
  add('Antarctica', top.south_lighting?.[0]?.cell, 'rock');
  if (hasLunarModel(D.meta.targets[ti])) add('Most Moon-like ground', top.north_full?.[0]?.cell);
  else rows.push({ note: 'Most Moon-like ground — ' + NO_LUNAR_MODEL + '.' });
  return rows;
}
function answerLunarRow(row) {
  if (row.note) return `<p class="answer-note">${esc(row.note)}</p>`;
  const { i, rules } = row, ti = tIndex(), seasons = D.meta.seasons;
  const periods = [...new Set(rules.map((r) => D.isN[i] ? r.period : 'rock'))];
  const hours = periods.map((period) => {
    const h = cellValue(i, 3, period, ti);
    const season = period === 'winter' ? `winter half (${seasons.winter_text})`
      : period === 'rock' ? `rock season (${seasons.rock_season_text})` : 'year';
    return `${Number.isFinite(h) ? fH(h) + ' h' : 'hours unknown'} / ${season}`;
  }).join('; ');
  const shortHours = periods.map((period) => {
    const h = cellValue(i, 3, period, ti);
    return `${Number.isFinite(h) ? fH(h) + ' h' : 'unknown'} / ${period === 'rock' ? 'rock season' : period === 'winter' ? 'winter' : 'year'}`;
  }).join('; ');
  const dates = periods.map((period) => {
    const counted = period === 'winter' ? seasons.winter_bins_north : period === 'rock' ? seasons.rock_season_bins_south : null;
    const haveHours = Array.from({ length: NB }, (_, b) => (!counted || counted.includes(b)) ? binValue(i, b, 3, ti) : null).some(Number.isFinite);
    return haveHours ? bestText(i, 3, ti, counted) : 'unknown';
  });
  const airfield = answerAirfield(i);
  const point = !airfield ? placesIndex()?.near.get(i)?.point?.airfield : null;
  const access = airfield ? `${airfield.name}, ${fInt(airfield.km)} km in a straight line`
    : point && Number.isFinite(point.km) ? `${point.name}, ${aboutKm(point.km)} from the middle of the group` : 'nearest airfield unknown';
  const labels = rules.map((r) => r.label).join(' + ');
  const ruleNotes = {
    'Best light score': 'This area has the highest score in the northern list for light. The score uses hours and bare ground.',
    'Easiest to reach': `This area has the most hours after terrain in a year within ${fInt(answerData.access?.reachKm)} km of scheduled flights. In Antarctica, the rule uses all listed airfields, not only airfields with scheduled flights. It does not show that a route or a permit is available.`,
    Winter: 'This is the first row of the winter list, after terrain. Its hours must reach the limit for the winter half.',
    Antarctica: 'This is the first row of the southern list for light. Only the rock season counts. Snow is not measured.',
    'Most Moon-like ground': 'This is the first row of the combined list. It uses light, slope likeness, rock and bare ground.',
  };
  const description = rules.map((r) => ruleNotes[r.label]).join(' ');
  return `<button type="button" class="answer-row" aria-expanded="${S.place === D.cells.ids[i]}" data-answer-place="${i}" title="${esc(description)}" aria-description="${esc(description)}">
    <span class="answer-main"><span class="answer-rule">${esc(labels)}</span> <strong>${esc(placeName(i))}</strong> <span>${esc(shortHours)}</span></span>
    <span class="answer-detail">${esc(hours)} · Best: ${esc([...new Set(dates)].join('; '))} · ${esc(access)}</span>
  </button>`;
}
function renderAnswer() {
  if (!D.ready) return;
  const focused = $('answer-section').contains(document.activeElement) ? focusKey() : null;
  $('answer-moon-title').textContent = `For the light of ${target().name}`;
  const rows = answerLunarRows().map(answerLunarRow);
  $('answer-moon-first').innerHTML = rows.shift() || '<p class="answer-note">No short-list places are available.</p>';
  $('answer-moon-rest').innerHTML = rows.join('') + '<p class="answer-foot">Rules select these places from the data of the page. Press a place to see the evidence. <a href="#go=lists" data-answer-go="lists">Short lists</a></p>';
  const mars = answerData.mars;
  $('answer-moon').hidden = S.dest !== 'moon';
  $('answer-mars').hidden = S.dest !== 'mars';
  if (mars) {
    const site = mars.sites.find((item) => item.id === S.msite) || mars.sites[0];
    $('answer-mars-scale').textContent = `First pass · squares of approximately ${fInt(mars.meta.square_km_about)} km · ${goalLabel(S.mgoal)}`;
    const marsRows = (mars.best_places?.[site.id]?.[S.mgoal] || []).slice(0, 5).map((place) => {
      const coords = Number.isFinite(place.lat) && Number.isFinite(place.lon) ? `${fLat(place.lat)}, ${fLon(place.lon)}` : 'position unknown';
      const months = Array.isArray(place.best_months) ? place.best_months.join(', ') || 'no month meets the rule' : 'months unknown';
      return `<button type="button" class="answer-row" aria-expanded="${S.msquare === place.id}" data-answer-square="${esc(place.id)}"><span class="answer-main"><span class="answer-rule">${esc(place.region)}</span><strong>${coords}</strong><span>Score ${Number.isFinite(place.score) ? place.score.toFixed(2) : 'unknown'}</span></span><span class="answer-detail">Best months: ${esc(months)}</span></button>`;
    });
    $('answer-mars-first').innerHTML = marsRows.shift() || '<p class="answer-note">No ranked square is available.</p>';
    $('answer-mars-rest').innerHTML = marsRows.join('') + `<details class="answer-foot"><summary>This is not a climate match.</summary><p>${esc(mars.meta.climate_caution || '')} ${esc(mars.meta.score_caution || '')}</p></details>`;
    $('answer-mars').querySelectorAll('[data-answer-square]').forEach((button) => button.addEventListener('click', () => set({ msquare: button.dataset.answerSquare, go: 'mars-square', only: null })));
  } else if (S.dest === 'mars') {
    $('answer-mars-first').innerHTML = '<p class="answer-note">The Mars data is unavailable.</p>';
  }
  $('answer-section').querySelectorAll('[data-answer-place]').forEach((button) => button.addEventListener('click', () => openPlace(+button.dataset.answerPlace, true)));
  $('answer-section').querySelectorAll('[data-answer-go]').forEach((link) => link.addEventListener('click', (event) => {
    event.preventDefault(); set({ only: null, go: link.dataset.answerGo });
  }));
  if (focused) $(focused.host)?.querySelector(focused.sel)?.focus({ preventScroll: true });
}

// ---------- short lists ----------
const tabList = () => [['winter', 'Winter exceptions'], ['belt', `The ${hardest().short} belt`], ['summer', 'Top summer areas'], ['famous', 'Why not the famous sites?'], ['antarctica', 'Antarctica']];
function placeCell(i) {
  const name = placeName(i);
  return `<button type="button" class="place-btn" data-cell="${i}">${esc(name)}<small>${fLat(D.lat[i])}, ${fLon(D.lon[i])}</small></button>`;
}
function bestText(i, step, t, only) {   // only: count just these ten-day periods (the winter half, say)
  const vals = Array.from({ length: NB }, (_, b) => (only && !only.includes(b) ? 0 : binValue(i, b, step, t)));
  const r = bestRanges(vals);
  return r ? r.text : 'none';
}
function knownText(i) { const u = earlierUse(i); return u === 'unassessed' ? 'not assessed' : u === 'known' || u === 'published' ? 'yes' : 'none found'; }
function renderTabs() {
  const m = D.meta, t = target(), ti = tIndex(), tabs = $('tabs'), panel = $('tab-panel'), TABS = tabList();
  renderListControls();
  if (!TABS.some(([k]) => k === S.tab)) S.tab = 'summer';
  tabs.innerHTML = TABS.map(([k, label]) => `<button type="button" class="tab" role="tab" id="tab-${k}" aria-selected="${S.tab === k}" tabindex="${S.tab === k ? 0 : -1}" aria-controls="tab-panel" data-tab="${k}">${esc(label)}</button>`).join('');
  tabs.querySelectorAll('button').forEach((b) => {
    b.addEventListener('click', () => set({ tab: b.dataset.tab }));

  });
  panel.setAttribute('aria-labelledby', 'tab-' + S.tab);
  const top = D.sites.top[t.id], spell = m.long_rule.spell_h, half = halfLevel();
  const table = (head, rows) => {
    if (pendingListSettings()) return '<p class="status">Open the module above to restore this list.</p>';
    const tid = listTarget().id, indexOf = (row) => +row[0].match(/data-cell="(\d+)"/)[1];
    const selected = listEntries(rows, tid, indexOf);
    return `<div class="table-wrap"><table><thead><tr>${head.map(([h, cls]) => `<th class="${cls || ''}">${h}</th>`).join('')}</tr></thead><tbody>${selected.map((r) => {
      const i = indexOf(r), notes = [...extensions.notes].map((fn) => moduleCall(fn, [i, tid])).filter((note) => note != null && note !== '');
      const lastVisible = head.reduce((last, [, cls], k) => !cls?.includes('hide-narrow') || !matchMedia('(max-width: 560px)').matches ? k : last, 0);
      return `<tr data-area="${esc(D.cells.ids[i])}">${r.map((value, k) => `<td class="${head[k][1] || ''}">${value}${k === lastVisible && notes.length ? `<span class="list-note">${notes.map(esc).join(' · ')}</span>` : ''}</td>`).join('')}</tr>`;
    }).join('') || `<tr><td colspan="${head.length}">No place meets the rules.</td></tr>`}</tbody></table></div>`;
  };
  const hrs = (v) => (v == null ? 'unknown' : fH(v));
  const score = (v) => (v != null ? v.toFixed(2) : 'unknown');
  const used = '“Used before?” gives the result of our search for published analog use. Its values are “yes”, “none found”, or “not assessed”.';
  let html = '';
  if (S.tab === 'summer') {
    html = `<p>These areas have the best scores for ${esc(t.name)}. Ranked areas have a terrain figure, measured snow, and at least ${fPct(m.scoring.rank_min_bare)} bare ground. The listed areas are at least ${fInt(D.sites.same_site_km)} km apart. The score combines the hours left after snow and terrain with the share of bare ground. ${fInt(m.scoring.full_hours)} hours per year give the maximum light score. Thus, the first row can have fewer hours than another row.</p><p>${used}</p>` +
      table([['Place'], ['Score', 'num hide-narrow'], ['Hours a year left', 'num'], ['Bare', 'num hide-narrow'], ['Best dates'], ['Sun', 'hide-narrow'], ['Used before?', 'hide-narrow']],
        top.north_lighting.map((r) => { const i = r.cell, tod = timeOfDay(i); return [placeCell(i), score(r.score), hrs(yr(i, 'open', ti)), D.cells.bare[i] + '%', bestText(i, 3, ti), tod ? (tod.p >= 0.5 ? 'near midnight' : tod.p <= 0.2 ? 'dawn, dusk, low noon' : 'mixed') : 'unknown', knownText(i)]; }));
    if (!hasLunarModel(t)) html += `<h3>Most Moon-like ground</h3><p>${NO_LUNAR_MODEL}.</p>`;
    else if (top.north_full.length) html += `<h3>With rock that also matches</h3><p>These ranked areas have a listed anorthosite body. Anorthosite is the pale rock of the lunar highlands. Their score combines light, terrain, rock, and bare ground.</p>` +
      table([['Place'], ['Score', 'num'], ['Hours left', 'num'], ['Rock', 'wrap']],
        top.north_full.map((r) => { const i = r.cell, rock = D.cells.rock[i]; return [placeCell(i), r.score.toFixed(2), hrs(yr(i, 'open', ti)), rock ? esc(rock[1]) : 'unknown']; }));
  } else if (S.tab === 'winter') {
    const reach = (m.headline[t.id].measured_cells_reaching[String(half)] || {});
    html = `<p>In the winter half (${esc(m.seasons.winter_text)}), nearly all bare Arctic ground is under snow when the Sun is low. These are the exceptions for ${esc(t.name)}: the measured areas with the most winter-half hours on snow-free ground. The listed areas are at least ${fInt(D.sites.same_site_km)} km apart. ${reach.winter == null ? 'An unknown number of areas' : cap(areasN(reach.winter))} ${reach.winter === 1 ? 'reaches' : 'reach'} ${fInt(half)} hours in the winter half, against ${fInt(reach.summer)} in the summer half. In winter, the low Sun is in the south at dawn, dusk and a low noon. It is not a midnight Sun.</p>` +
      table([['Place'], ['Winter-half hours, snow-free ground', 'num'], ['The same after terrain', 'num'], ['Best winter dates'], ['Used before?', 'hide-narrow']],
        top.winter.map((r) => { const i = r.cell; return [placeCell(i), hrs(yr(i, 'snow_free_winter', ti)), hrs(yr(i, 'open_winter', ti)), bestText(i, D.cells.horizon_n[i] != null ? 3 : 2, ti, m.seasons.winter_bins_north), knownText(i)]; }));
  } else if (S.tab === 'belt') {
    const ridge = hardest(), ri = m.targets.indexOf(ridge), rtop = D.sites.top[ridge.id];
    const lats = [];
    for (let i = 0; i < D.n; i++) if (D.isN[i] && D.status[i] === 'measured' && D.cells.gridded[i] === '1') { const su = cellValue(i, 2, 'summer', ri); if (su != null && su >= half / 2) lats.push(D.lat[i]); }
    const outside = rtop.north_lighting.filter((r) => D.lat[r.cell] < quantile(lats, 0.1) || D.lat[r.cell] > quantile(lats, 0.9)).length;
    html = `<p>${esc(ridge.name)} has the lowest Sun ceiling of these ${m.targets.length} lunar regions: ${ridge.limit_deg.toFixed(2)}°. ${lats.length ? `Most of the ${areasN(lats.length)} with ${fInt(half / 2)} summer hours or more are between ${fLat(quantile(lats, 0.1))} and ${fLat(quantile(lats, 0.9))}. ` : ''}The list shows the ${rtop.north_lighting.length} best areas in score order. The score also uses the share of bare ground. Thus, ${outside > rtop.north_lighting.length / 2 ? 'most' : 'some'} listed areas are outside this range.</p>` +
      table([['Place'], ['Score', 'num'], ['Hours a year left', 'num'], ['On snow-free ground, flat horizon', 'num hide-narrow'], ['Bare', 'num hide-narrow'], ['Best dates'], ['Used before?', 'hide-narrow']],
        rtop.north_lighting.map((r) => { const i = r.cell; return [placeCell(i), score(r.score), hrs(yr(i, 'open', ri)), hrs(yr(i, 'snow_free', ri)), D.cells.bare[i] + '%', bestText(i, 3, ri), knownText(i)]; }));
  } else if (S.tab === 'famous') {
    const kc = knownCounts(extra('validation.json', true), t);   // counted from the file; until it is there the sentence is left out
    html = `<p>This list gives named places for ${esc(t.name)}. The page reports each place on the area that holds it. The columns give the hours a year in spells of ${spell} hours or more: Sun only, on snow-free ground, and after terrain. ${kc.n ? knownSentence(kc, 'here') + ' ' : ''}Earlier teams selected known analog sites for their geology, not for their light.</p>` +
      table([['Place'], ['Sun only', 'num'], ['Snow-free ground', 'num'], ['After terrain', 'num'], ['Snow', 'hide-narrow'], ['Rock match, 0 to 1', 'num hide-narrow']],
        D.sites.named.filter((s) => s.hemisphere === 'N').map((s) => { const i = s.cell, rock = D.cells.rock[i]; return [placeCell(i), hrs(flatYear(i, ti)), hrs(yr(i, 'snow_free', ti)), hrs(yr(i, 'open', ti)), esc(D.status[i]) + (D.cells.gridded[i] === '0' ? ', outside the search' : ''), rock ? (rock[0] / 1000).toFixed(2) : D.cells.known[i] === -2 ? 'unknown' : '0']; }));
  } else {
    html = `<p>No open product measures winter snow on Antarctic rock. Thus, the ${fInt(m.counts.south_cells)} southern areas count only the rock season (${esc(m.seasons.rock_season_text)}). The rock maps show bare ground during that season. These areas have a separate rank from the north. The list shows the best scores for ${esc(t.name)}.</p>` +
      table([['Place'], ['Score', 'num'], ['Rock-season hours after terrain', 'num'], ['Sun only, rock season', 'num hide-narrow'], ['Bare', 'num hide-narrow'], ['Used before?', 'hide-narrow']],
        top.south_lighting.map((r) => { const i = r.cell; return [placeCell(i), score(r.score), hrs(southYear(i, 'rock_open', ti)), hrs(southYear(i, 'rock_flat', ti)), D.cells.bare[i] + '%', knownText(i)]; })) +
      `<h3>Named Antarctic places and what is known about their winter snow</h3>` +
      table([['Place'], ['Winter-snow evidence'], ['Rock-season hours after terrain', 'num'], ['Sun only, rock season', 'num hide-narrow']],
        D.sites.named.filter((s) => s.hemisphere === 'S').map((s) => { const i = s.cell; return [placeCell(i), esc(s.winter_snow_evidence || 'no evidence on file'), hrs(southYear(i, 'rock_open', ti)), hrs(southYear(i, 'rock_flat', ti))]; }));
  }
  panel.innerHTML = html + `<p class="caption">Select a place to open its place card. ${DRAWN}</p>`;
  compactLists(panel);
  panel.querySelectorAll('.place-btn').forEach((b) => b.addEventListener('click', () => openPlace(+b.dataset.cell, true)));
}

// ---------- sections that read an extra file only when the reader comes near them ----------
// The Sun-path picture, "What Earth cannot copy", "How sure are we", the closing sections and the files to save
// each need one extra file. watchSections() notes when the reader comes near a section; its part then asks for the
// file with extra(), and extraArrived() draws the part when the file is there (or says in one line that it is missing).
const NEAR = {};
let goHold = null;
function holdGo() {   // until the reader moves: stay on the section a link with &go= asked for
  if (!goHold || goHold.generation !== navigationGeneration || performance.now() > goHold.until) return;
  const el = sectionFor(goHold.id);
  if (el) el.scrollIntoView();
}
function watchSections() {
  const parts = { light: renderSunPath, limits: renderCannot, sure: renderSure, more: renderClosing, map: renderMapCredit, lists: renderTake };
  const near = (id) => { if (NEAR[id]) return; NEAR[id] = true; parts[id](); };
  if (!window.IntersectionObserver) { Object.keys(parts).forEach(near); return; }
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { io.unobserve(e.target); near(e.target.id.replace('-section', '')); }
  }, { rootMargin: '800px 0px' });
  Object.keys(parts).forEach((id) => { const el = $(id + '-section'); if (el) io.observe(el); });
}
const FILE_PARTS = {
  'sunpath.json': () => renderSunPath(),
  'moon.json': () => renderCannot(),
  'validation.json': () => { renderSure(); if (S.tab === 'famous') renderTabs(); },
  'sources.json': () => { renderClosing(); renderMapCredit(); renderSunPath(); renderTake(); },
};
const missingLine = (what, file) => `<p class="status">${what} not on this copy of the page. The file ${file} is missing. The rest of the page works without it.</p>`;
// The notice the Copernicus licence asks for beside anything computed from its elevation data ('' until sources.json is read).
const copernicusNotice = () => { const s = X.got['sources.json']; return s && s.notices && s.notices.copernicus_dem ? s.notices.copernicus_dem : ''; };
function renderMapCredit() {
  const el = $('map-credit');
  if (!el || !NEAR.map) return;
  extra('sources.json');
  const notice = copernicusNotice();
  el.hidden = !notice;
  el.textContent = notice ? 'Terrain figures: ' + notice + '.' : '';
}

// ---------- the Sun-path picture: one trip of the Sun at a lunar region and one day at an Earth place, on the same axes ----------
const hm = (min) => { const h = Math.floor(min / 60), m = Math.round(min - h * 60); return (h ? `${h} h` : '') + (h && m ? ' ' : '') + (m || !h ? `${m} min` : ''); };
const clock = (h) => { const hh = ((Math.round(h) % 24) + 24) % 24; return hh === 0 ? 'midnight' : hh === 12 ? 'noon' : String(hh).padStart(2, '0') + ':00'; };
function renderSunPath() {
  const host = $('sunpath-plot');
  if (!host || !NEAR.light || !D.ready) return;
  const f = extra('sunpath.json', true);
  if (f === undefined) { host.innerHTML = '<p class="status">The page will draw the Sun-path picture.</p>'; return; }
  const mo = f && f.moon, ea = f && f.earth;
  if (!mo || !mo.path || !mo.marks || !ea || !ea.path || !ea.marks) {
    host.innerHTML = missingLine('The Sun-path picture is', 'sunpath.json');
    ['sunpath-legend', 'sunpath-howto', 'sunpath-cautions', 'sunpath-caption'].forEach((id) => { $(id).textContent = ''; });
    $('sunpath-more').hidden = true; $('sunpath-table-wrap').hidden = true;
    return;
  }
  const band = f.band_deg || [0, mo.ceiling_deg], south = f.axis_centre === 'south';
  // sideways: degrees from the direction in the middle of the picture (north, unless the file says south), -180 to 180
  const xOf = (az) => ((((south ? az - 180 : az) + 180) % 360) + 360) % 360 - 180;
  const W = Math.max(300, host.clientWidth), narrow = W < 560, wide = W >= 760, H = narrow ? 310 : 400;
  const L = narrow ? 30 : 44, R = narrow ? 8 : 16, T = 24, B = 46, pw = W - L - R, ph = H - T - B;
  const y0 = Math.floor(Math.min(0, ...mo.path.elevation_deg)), y1 = Math.ceil(band[1] * 1.6);
  const X1 = (x) => L + ((x + 180) / 360) * pw, Y1 = (v) => T + ph - ((v - y0) / (y1 - y0)) * ph;
  const xs = (a) => X1(xOf(a)).toFixed(1);
  // a curve as one or more lines: a new line starts where the direction jumps across the edge of the picture
  const line = (az, el) => { let d = '', prev = null; az.forEach((a, k) => { const x = xOf(a); d += (prev == null || Math.abs(x - prev) > 180 ? 'M' : 'L') + X1(x).toFixed(1) + ' ' + Y1(el[k]).toFixed(1); prev = x; }); return d; };
  const arrow = (az, el, k, cls) => {
    if (k < 0 || k + 1 >= az.length || Math.abs(xOf(az[k + 1]) - xOf(az[k])) > 180) return '';
    const ax = X1(xOf(az[k])), ay = Y1(el[k]), bx = X1(xOf(az[k + 1])), by = Y1(el[k + 1]);
    return `<path d="M-6 -4.5L6 0L-6 4.5Z" class="${cls}" transform="translate(${((ax + bx) / 2).toFixed(1)} ${((ay + by) / 2).toFixed(1)}) rotate(${(Math.atan2(by - ay, bx - ax) * 180 / Math.PI).toFixed(0)})"/>`;
  };
  const nearest = (az, want, el, lo, hi) => { let best = -1, gap = 1e9; az.forEach((a, k) => { const g = Math.abs(xOf(a) - want); if (g < gap && (el == null || (el[k] >= lo && el[k] <= hi))) { gap = g; best = k; } }); return best; };
  const mp = mo.path, ep = ea.path, mm = mo.marks, em = ea.marks;
  const moLeft = xOf(mp.azimuth_deg[1]) < xOf(mp.azimuth_deg[0]), eaLeft = xOf(ep.azimuth_deg[1]) < xOf(ep.azimuth_deg[0]);
  const inBand = ea.minutes_above_terrain != null ? ea.minutes_above_terrain : ea.minutes_in_band;
  const days = mo.path_days_in_band != null ? mo.path_days_in_band : mo.path_days_above_level_horizon;
  const title = `The same band of sky: ${days != null ? days.toFixed(1) + ' days' : 'days'} at ${mo.name}, ${inBand != null ? hm(inBand) : 'hours'} at ${ea.name}`;
  $('sunpath-title').textContent = title;
  $('sunpath-legend').innerHTML = `<span class="key"><span class="line dotted" style="border-color:var(--accent);color:var(--accent)"></span>the Sun at ${esc(mo.name)}, on the Moon: one dot a day${mo.mean_trip_days ? `, ${mo.mean_trip_days.toFixed(1)} days for one full circle` : ''}</span>`
    + `<span class="key"><span class="line dotted" style="border-color:var(--snow);color:var(--snow)"></span>the Sun at ${esc(ea.name)}, on ${esc(ea.date || 'one day')}: one dot an hour</span>`
    + `<span class="key"><span class="swatch band-key"></span>the band we copy: from the horizon up to ${band[1].toFixed(2)}°</span>`
    + (ea.terrain_horizon ? `<span class="key"><span class="swatch" style="background:var(--ghost2)"></span>the ground seen from the Earth place</span>` : '');

  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title + '. ' + (f.shows || []).join(' '))}"><defs><clipPath id="sp-clip"><rect x="${L}" y="${T}" width="${pw}" height="${ph}"/></clipPath></defs>`;
  // the band, the level horizon and what lies below it
  svg += `<rect x="${L}" y="${Y1(band[1]).toFixed(1)}" width="${pw}" height="${(Y1(band[0]) - Y1(band[1])).toFixed(1)}" fill="var(--accent-soft)"/>`;
  svg += `<rect x="${L}" y="${Y1(0).toFixed(1)}" width="${pw}" height="${(T + ph - Y1(0)).toFixed(1)}" fill="var(--ghost1)" opacity="0.55"/>`;
  const step = y1 - y0 <= 8 ? 1 : y1 - y0 <= 16 ? 2 : 5;
  for (let v = Math.ceil(y0 / step) * step; v <= y1; v += step) svg += `<line x1="${L}" x2="${W - R}" y1="${Y1(v).toFixed(1)}" y2="${Y1(v).toFixed(1)}" stroke="var(--grid)"/><text x="${L - 6}" y="${(Y1(v) + 4).toFixed(1)}" text-anchor="end">${v}°</text>`;
  const th = ea.terrain_horizon;
  if (th && th.centre_deg && th.sector_centres_deg) {   // the Earth ground: how high the land stands in each direction
    const pts = th.sector_centres_deg.map((a, k) => [xOf(a), th.centre_deg[k]]).filter((p) => p[1] != null).sort((a, b) => a[0] - b[0]);
    if (pts.length) {
      const edge = (pts[0][1] + pts[pts.length - 1][1]) / 2;
      pts.unshift([-180, edge]); pts.push([180, edge]);
      svg += `<path d="M${X1(-180)} ${Y1(0).toFixed(1)}${pts.map((p) => `L${X1(p[0]).toFixed(1)} ${Y1(Math.max(0, p[1])).toFixed(1)}`).join('')}L${X1(180)} ${Y1(0).toFixed(1)}Z" fill="var(--ghost2)"/>`;
    }
  }
  svg += `<line x1="${L}" x2="${W - R}" y1="${Y1(0).toFixed(1)}" y2="${Y1(0).toFixed(1)}" stroke="var(--ink2)" stroke-width="1"/>`;
  svg += `<line x1="${L}" x2="${W - R}" y1="${Y1(band[1]).toFixed(1)}" y2="${Y1(band[1]).toFixed(1)}" stroke="var(--accent)" stroke-width="1" stroke-dasharray="5 4"/>`;
  // the two curves, with dots that show time
  svg += `<g clip-path="url(#sp-clip)"><path class="mo-line" d="${line(mp.azimuth_deg, mp.elevation_deg)}"/><path class="ea-line" d="${line(ep.azimuth_deg, ep.elevation_deg)}"/>`;
  if (wide) {
    svg += arrow(mp.azimuth_deg, mp.elevation_deg, nearest(mp.azimuth_deg, 139), 'mo-arrow') + arrow(mp.azimuth_deg, mp.elevation_deg, nearest(mp.azimuth_deg, -139), 'mo-arrow');
    const mid = (band[1] + y1) / 2;
    svg += arrow(ep.azimuth_deg, ep.elevation_deg, nearest(ep.azimuth_deg, 60, ep.elevation_deg, mid - 1, mid + 1), 'ea-arrow') + arrow(ep.azimuth_deg, ep.elevation_deg, nearest(ep.azimuth_deg, -60, ep.elevation_deg, mid - 1, mid + 1), 'ea-arrow');
  }
  const dayOf = (k) => Math.round(mm.hours_since_start[k] / 24);
  mm.azimuth_deg.forEach((a, k) => {
    const el = mm.elevation_deg[k];
    svg += `<circle class="mo-dot${el < 0 ? ' under' : ''}" cx="${xs(a)}" cy="${Y1(el).toFixed(1)}" r="${narrow ? 2.6 : 3.4}"><title>${esc(mo.name)}, day ${dayOf(k)}: the Sun's centre is ${Math.abs(el).toFixed(1)}° ${el < 0 ? 'below' : 'above'} a level horizon</title></circle>`;
  });
  em.azimuth_deg.forEach((a, k) => {
    const el = em.elevation_deg[k];
    if (el <= y1 + 1) svg += `<circle class="ea-dot" cx="${xs(a)}" cy="${Y1(el).toFixed(1)}" r="${narrow ? 2.6 : 3.4}"><title>${esc(ea.name)}, ${clock(em.solar_time_h[k])} by the Sun: ${el.toFixed(1)}° above a level horizon</title></circle>`;
  });
  svg += '</g>';
  // times beside some dots: every fifth day on the Moon's curve, the hours inside the band on the Earth's curve
  mm.azimuth_deg.forEach((a, k) => {
    const d = dayOf(k), x = xOf(a);
    if (d > 0 && d % 5 === 0 && Math.abs(x) > 25 && Math.abs(x) < 165) svg += `<text class="halo" x="${xs(a)}" y="${(Y1(mm.elevation_deg[k]) - (d === 5 ? 21 : 9)).toFixed(1)}" text-anchor="middle">day ${d}</text>`;
  });
  const inside = em.elevation_deg.map((el, k) => k).filter((k) => em.elevation_deg[k] <= band[1] && em.elevation_deg[k] > 0);
  if (inside.length) {
    const low = inside.reduce((a, k) => (em.elevation_deg[k] < em.elevation_deg[a] ? k : a), inside[0]);
    const xsIn = inside.map((k) => xOf(em.azimuth_deg[k])), left = inside[xsIn.indexOf(Math.min(...xsIn))], right = inside[xsIn.indexOf(Math.max(...xsIn))];
    const lab = (k) => `<text class="halo ea-text" x="${xs(em.azimuth_deg[k])}" y="${(Y1(em.elevation_deg[k]) + 17).toFixed(1)}" text-anchor="middle">${clock(em.solar_time_h[k])}</text>`;
    svg += lab(low);
    if (pw * (Math.max(...xsIn) - Math.min(...xsIn)) / 360 > 110) { if (left !== low) svg += lab(left); if (right !== low) svg += lab(right); }
  }
  // labels on the picture itself
  const moWord = (moLeft ? '← ' : '') + 'one dot a day' + (moLeft ? '' : ' →'), eaWord = (eaLeft ? '← ' : '') + 'one dot an hour' + (eaLeft ? '' : ' →');
  const bandY = Y1(band[1]);
  if (wide) {
    svg += `<text class="halo mo-text" x="${L + 8}" y="${(bandY + 17).toFixed(1)}">the Moon, ${esc(mo.name)}: ${moWord}</text>`;
    svg += `<text class="halo ea-text" x="${W - R - 8}" y="${T + 16}" text-anchor="end">Earth, ${esc(ea.name)}: ${eaWord}</text>`;
    svg += `<text class="halo" x="${W - R - 8}" y="${(bandY + 17).toFixed(1)}" text-anchor="end">highest Sun at ${esc(mo.name)}: ${band[1].toFixed(2)}°</text>`;
  } else {
    svg += `<text class="halo mo-text" x="${L + pw / 2}" y="${(Y1(0) + 17).toFixed(1)}" text-anchor="middle">the Moon: ${moWord}</text>`;
    svg += `<text class="halo ea-text" x="${W - R - 4}" y="${T + 14}" text-anchor="end">Earth</text><text class="halo ea-text" x="${W - R - 4}" y="${T + 28}" text-anchor="end">${eaWord}</text>`;
    svg += `<text class="halo" x="${W - R - 4}" y="${(bandY + 15).toFixed(1)}" text-anchor="end">ceiling ${band[1].toFixed(2)}°</text>`;
  }
  if (ea.day_max_elevation_deg > y1) svg += `<text class="halo ea-text" x="${L + (wide ? 8 : 5)}" y="${T + (wide ? 16 : 14)}">↑ ${wide ? 'up ' : ''}to ${Math.round(ea.day_max_elevation_deg)}° at noon</text>`;
  svg += `<text class="halo" x="${L + pw / 2}" y="${T + ph - 7}" text-anchor="middle">below a level horizon</text>`;
  // the axes
  const dirs = south ? ['north', 'east', 'south', 'west', 'north'] : ['south', 'west', 'north', 'east', 'south'];
  dirs.forEach((d, k) => { const x = X1(-180 + 90 * k); svg += `<line x1="${x}" x2="${x}" y1="${T + ph}" y2="${T + ph + 5}" stroke="var(--axis)"/><text x="${x}" y="${H - 26}" text-anchor="${k === 0 ? 'start' : k === 4 ? 'end' : 'middle'}">${d}</text>`; });
  svg += `<text x="${L + pw / 2}" y="${H - 6}" text-anchor="middle">direction of the Sun along the horizon</text><text x="0" y="${T - 10}" text-anchor="start">Sun's height above a level horizon</text>`;
  svg += `<rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="none" stroke="var(--axis)"/></svg>`;
  host.innerHTML = svg;

  const card = ea.area != null && D.cells.ids[ea.area] === ea.cell_id;
  $('sunpath-howto').innerHTML = `How to read this. ${esc((f.shows || []).join(' '))}${south ? '' : ' The times on the Earth curve are by the Sun. At midnight, the Sun is due north.'}${card ? `<br><button type="button" class="linkish" data-cell="${ea.area}">Open the place card of ${esc(ea.name)}</button>` : ''}`;
  const open = $('sunpath-howto').querySelector('[data-cell]');
  if (open) open.addEventListener('click', () => openPlace(+open.dataset.cell, true));
  const cautions = f.cautions || [], main = cautions.filter((c) => c.main), rest = cautions.filter((c) => !c.main);
  $('sunpath-cautions').innerHTML = main.length ? `<b>${cap(words(main.length))} cautions.</b> ${esc(main.map((c) => c.sentences.join(' ')).join(' '))}` : '';
  $('sunpath-more').hidden = !rest.length;
  $('sunpath-more-list').innerHTML = rest.map((c) => `<li>${esc(c.sentences.join(' '))}</li>`).join('');
  const deg = (v) => v.toFixed(1) + '°';
  $('sunpath-table-wrap').hidden = false;
  $('sunpath-table').innerHTML = `<div class="two-tables"><div><h4>${esc(mo.name)}, on the Moon: one row a day</h4><div class="table-wrap"><table><thead><tr><th>Day</th><th class="num">Direction, clockwise from north</th><th class="num">Sun's height</th></tr></thead><tbody>${mm.azimuth_deg.map((a, k) => `<tr><td>${dayOf(k)}</td><td class="num">${Math.round(a)}°</td><td class="num">${mm.elevation_deg[k] <= -0.05 ? '−' : ''}${Math.abs(mm.elevation_deg[k]).toFixed(1)}°</td></tr>`).join('')}</tbody></table></div></div>`
    + `<div><h4>${esc(ea.name)}, ${esc(ea.date || '')}: one row an hour</h4><div class="table-wrap"><table><thead><tr><th>Time by the Sun</th><th class="num">Direction, clockwise from north</th><th class="num">Sun's height</th></tr></thead><tbody>${em.azimuth_deg.map((a, k) => `<tr><td>${clock(em.solar_time_h[k])}</td><td class="num">${Math.round(a)}°</td><td class="num">${deg(em.elevation_deg[k])}</td></tr>`).join('')}</tbody></table></div></div></div>`;
  if (th) extra('sources.json');   // for the notice that goes with the Earth ground
  const notice = copernicusNotice();
  $('sunpath-caption').textContent = (f.caption ? f.caption.replace(/\.\s*$/, '') + ' (Claude).' : DRAWN) + (notice && th ? ' Earth ground: ' + notice + '.' : '');
}

// ---------- what Earth cannot copy: the list for the chosen lunar region, from moon.json ----------
function renderCannot() {
  const host = $('cannot');
  if (!host || !NEAR.limits || !D.ready) return;
  const file = extra('moon.json'), t = target();
  if (file === undefined) { host.innerHTML = '<p class="status">The page will read the list for this lunar region.</p>'; return; }
  const card = file ? (file.cards || []).find((x) => x.id === t.id) : null, items = card ? card.earth_cannot_match || [] : [];
  if (!items.length) { host.innerHTML = missingLine('The list of what no place on Earth has is', 'moon.json'); return; }
  if (host.dataset.for === t.id + (X.index ? '+' : '')) return;   // already drawn for this site
  host.dataset.for = t.id + (X.index ? '+' : '');
  host.innerHTML = `<h3>${cap(words(items.length))} things no place on Earth has, at ${esc(card.official_name || t.name)}</h3>
    <ul class="cannot">${cannotItems(card)}</ul>
    <p class="actions"><button type="button" class="btn" data-about="${t.id}" aria-haspopup="dialog">About ${esc(t.name)}: the lunar region card</button></p>
    <p class="caption">Moon figures: NASA Moon Fact Sheet, NASA Goddard sunlight maps, and Diviner. Diviner gives model values, not measurements.</p>`;
  host.querySelector('[data-about]').addEventListener('click', (e) => openMoon(e.currentTarget.dataset.about));
}

// ---------- how sure are we: checks from validation.json, each with a one-line finding, for the chosen lunar region ----------
const areasWord = (s) => String(s).replace(/\bcells\b/g, 'areas').replace(/\bcell\b/g, 'area').replace(/terrain horizon/g, 'terrain figure');
const signed = (x) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(Math.round(x * 100)) + '%';
const points = (x) => String(Math.round(Math.abs(x) * 100));   // a share as percentage points, sign dropped
const surePart = (n, kicker, finding, body, caption) => `<details class="sure-part"><summary><span class="kicker">Check ${n}: ${kicker}</span><h3>${finding}</h3></summary>${body}<p class="caption">${caption}</p></details>`;
const numTable = (head, rows) => `<div class="table-wrap"><table><thead><tr>${head.map((h, k) => `<th class="${k ? 'num' : ''}">${h}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c, k) => `<td class="${k ? 'num' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
function renderSure() {
  const host = $('sure');
  if (!host || !NEAR.sure || !D.ready) return;
  const v = extra('validation.json', true), t = target();
  if (v === undefined) { host.innerHTML = '<p class="status">The page will read the checks.</p>'; return; }
  if (!v) { host.dataset.for = ''; $('sure-lede').textContent = ''; host.innerHTML = missingLine('These checks are', 'validation.json'); return; }
  if (host.dataset.for === t.id) return;   // already drawn for this lunar region
  host.dataset.for = t.id;
  const parts = [sureLower, sureFunnel, sureKnown, sureSensitivity, sureSnow];
  let n = 0;
  const html = parts.map((part) => {
    let out = '';
    try { out = part(v, t, n + 1); } catch (e) { out = `<div class="sure-part"><p class="status">The page cannot draw one check from validation.json (${esc(e.message)}).</p></div>`; }
    if (out) n += 1;
    return out;
  }).join('');
  const was = [...host.querySelectorAll('details.sure-part')].map((d) => d.open), wideScreen = matchMedia('(min-width: 701px)').matches;
  $('sure-lede').textContent = `This part gives ${words(n)} ${n === 1 ? 'check' : 'checks'} of the result for ${t.name}. Open a check to see its picture and numbers. Select another lunar region in the bar. The checks change with it.`;
  host.innerHTML = html;
  host.querySelectorAll('table').forEach((table) => {
    const headings = [...table.querySelectorAll('thead th')].map((cell) => cell.textContent);
    table.querySelectorAll('tbody tr').forEach((row) => [...row.querySelectorAll('td')].forEach((cell, index) => { cell.dataset.label = headings[index] || ''; }));
  });
  host.querySelectorAll('details.sure-part').forEach((d, k) => { d.open = was.length ? !!was[k] : wideScreen && k === 0; });   // on a wide screen the first check is open; every other check shows its finding until opened
  host.querySelectorAll('.place-btn').forEach((b) => b.addEventListener('click', () => openPlace(+b.dataset.cell, true)));
}
// 1. what the lower-latitude places other searches land on get: minutes at dawn and dusk, never two hours
function sureLower(v, t, n) {
  const low = v.lower_latitude_sites || {}, rule = ((v.meta || {}).stretch_min_h || D.meta.long_rule.spell_h) * 60, spell = rule / 60;
  const rows = (low.sites || []).map((s) => ({ s, x: (s.targets || {})[t.id] })).filter((r) => r.x && r.x.longest_spell_minutes != null);
  if (!rows.length) return '';
  const hrs = rows.map((r) => r.x.hours_a_year_in_band), longest = Math.max(...rows.map((r) => r.x.longest_spell_minutes));
  const reach = rows.filter((r) => r.x.has_a_2h_spell).length;
  const P = D.profile, pr = P.lat.map((lat, k) => ({ lat, long: P.targets[t.id].long[k], longest: P.targets[t.id].longest[k] })).filter((r) => r.lat >= 0);
  const peak = pr.length ? pr.reduce((a, r) => (r.long > a.long ? r : a), pr[0]) : null, peakMin = peak && peak.longest ? peak.longest * 60 : null;
  const scale = Math.max(rule, longest, peakMin || 0) * 1.04;
  const finding = reach === 0
    ? `At ${rows.length} places at lower latitudes, this low Sun lasts ${fInt(Math.min(...hrs))} to ${fInt(Math.max(...hrs))} hours a year. No spell lasts longer than ${fInt(longest)} minutes.`
    : `${cap(words(reach))} of ${rows.length} places at lower latitudes ${reach === 1 ? 'has' : 'have'} a spell of ${spell} hours or more for ${esc(t.name)}.`;
  const row = (name, sub, min, cls) => `<div class="row"><span class="name">${esc(name)}<small>${esc(sub)}</small></span><span class="track"><i class="${cls}" style="width:${Math.min(100, (min / scale) * 100).toFixed(1)}%"></i><span class="rule" style="left:${((rule / scale) * 100).toFixed(1)}%"></span></span><span class="v">${fInt(min)} min</span></div>`;
  const body = `<p class="note">Each bar shows the year's longest spell of low Sun, in minutes. Low Sun here means a Sun as low as at ${esc(t.name)}. The vertical line shows our rule: ${fInt(rule)} minutes. These places get their low Sun at dawn and dusk, a few minutes at a time.</p>
    <div class="rows">${rows.map((r) => row(r.s.name, `${fLat(r.s.lat)}, ${r.s.kind}`, r.x.longest_spell_minutes, '')).join('')}
    ${peakMin ? `<div class="group">For comparison, in the band of latitudes that the search covers</div>${row(fLat(peak.lat), 'the latitude with the most hours in long spells, and its typical longest spell', peakMin, 'other')}` : ''}</div>
    <details class="table-view"><summary>Show these numbers as a table</summary>${numTable(['Place', 'Latitude', 'Hours a year this low', 'Minutes a day, on average', 'Longest spell, minutes', `Hours a year in spells of ${spell} hours or more`],
    rows.map((r) => [esc(r.s.name) + `<small> (${esc(r.s.kind)})</small>`, fLat(r.s.lat), fInt(r.x.hours_a_year_in_band), r.x.mean_minutes_a_day_in_band != null ? fInt(r.x.mean_minutes_a_day_in_band) : 'unknown', fInt(r.x.longest_spell_minutes), r.x.hours_in_spells_of_2h != null ? fH(r.x.hours_in_spells_of_2h) : 'unknown']))}</details>`;
  return surePart(n, 'the places at lower latitudes from other searches', finding, body, `The code worked this out for a flat horizon at the latitude of each place. It is not a measurement of the site of another team. ${DRAWN}`);
}
// 2. latitude alone against the full method, as a funnel
function sureFunnel(v, t, n) {
  const F = v.latitude_against_full_method || {}, ft = (F.targets || {})[t.id], fl = v.flags || {}, m = v.meta || {};
  if (!ft || !ft.summer_half) return '';
  const census = fl.terrain_step_is_a_census === true, spell = D.meta.long_rule.spell_h;
  const all = ft.summer_half.all_measured_cells, hz = ft.summer_half.measured_cells_with_a_horizon, last = census ? all : hz;
  const N = all.scope.cells, M = hz.scope.cells;
  const finding = census
    ? `For ${esc(t.name)}, latitude alone passes ${fInt(all.sun_alone.cells)} of ${fInt(N)} measured areas. Snow and terrain leave ${all.after_terrain.cells === 0 ? 'none' : fInt(all.after_terrain.cells)}.`
    : `For ${esc(t.name)}, latitude alone passes ${fInt(hz.sun_alone.cells)} of the ${fInt(M)} areas checked for terrain. Snow and terrain leave ${hz.after_terrain.cells === 0 ? 'none' : fInt(hz.after_terrain.cells)}.`;
  const bar = (label, sub, step, scope) => `<div class="row"><span class="name">${label}<small>${sub}</small></span><span class="track">${step.cells > 0 ? `<i style="width:${((100 * step.cells) / scope).toFixed(1)}%"></i>` : ''}</span><span class="v">${fInt(step.cells)}</span></div>`;   // no areas: no bar at all
  let rows;
  if (census) {
    rows = `<div class="group">All ${fInt(N)} measured Arctic areas</div>` + bar('1. Sun alone', 'the result from latitude alone', all.sun_alone, N) + bar('2. After snow', 'hours on snow-free ground', all.after_snow, N) + bar('3. After snow and terrain', 'without the hours that hills hide', all.after_terrain, N);
  } else {
    rows = `<div class="group">All ${fInt(N)} measured Arctic areas</div>` + bar('1. Sun alone', 'the result from latitude alone', all.sun_alone, N) + bar('2. After snow', 'hours on snow-free ground', all.after_snow, N)
      + `<div class="group">The ${fInt(M)} of them that had a terrain figure when this check ran</div>` + bar('1. Sun alone', 'the result from latitude alone', hz.sun_alone, M) + bar('2. After snow', 'hours on snow-free ground', hz.after_snow, M) + bar('3. After snow and terrain', 'without the hours that hills hide', hz.after_terrain, M);
  }
  const c = last.after_cloud, keep = c && c.still_at_least_h ? Object.keys(c.still_at_least_h).sort((a, b) => b - a) : [];
  const cloud = c && c.median_share_of_hours_kept != null
    ? `<p class="note"><b>4. Typical cloud</b> is not a count of areas. The middle area keeps ${fPct(c.median_share_of_hours_kept)} of its hours${keep.length ? `. ${cap(keep.map((k) => `${areasN(c.still_at_least_h[k])} ${c.still_at_least_h[k] === 1 ? 'keeps' : 'keep'} ${k} hours or more`).join(' and '))}` : ''}. Mean cloud is not the chance that a low Sun is visible.</p>` : '';
  const w = ft.winter_half ? ft.winter_half.all_measured_cells : null;
  const winter = w ? `<p class="note">In the winter half${m.winter_half ? ` (${esc(m.winter_half)})` : ''}, latitude alone passes ${fInt(w.sun_alone.cells)} areas. Snow leaves ${w.after_snow.cells === 0 ? 'none' : fInt(w.after_snow.cells)}.</p>` : '';
  const partly = census ? '' : `<p class="note">The terrain step does not count all areas. ${fPct(M / N)} of the measured areas had a terrain figure when this check ran.</p>`;
  const tableRows = [];
  for (const [half, label] of [['summer_half', 'Summer half'], ['winter_half', 'Winter half']]) {
    if (!ft[half]) continue;
    for (const [scope, name] of census ? [['all_measured_cells', 'all measured areas']] : [['all_measured_cells', 'all measured areas'], ['measured_cells_with_a_horizon', 'areas with a terrain figure']]) {
      const s = ft[half][scope];
      for (const [key, step] of [['sun_alone', 'Sun alone'], ['after_snow', 'after snow'], ['after_terrain', 'after snow and terrain']]) {
        if (scope === 'all_measured_cells' && key === 'after_terrain' && !census) continue;
        tableRows.push([`${label}, ${name}: ${step}`, fInt(s[key].cells), fInt(s.scope.cells), s[key].bare_km2 != null ? fInt(s[key].bare_km2) : 'unknown']);
      }
    }
  }
  const body = `<p class="note">An area passes if it keeps at least ${fInt(F.threshold_h)} hours in the summer half${m.summer_half ? ` (${esc(m.summer_half)})` : ''}. Only the hours in spells of ${spell} hours or more count. Each bar shows the number of areas that still pass.</p>
    <div class="rows">${rows}</div>${cloud}${winter}${partly}
    <details class="table-view"><summary>Show these numbers as a table</summary>${numTable(['Step', 'Areas that pass', 'Out of', 'Bare ground in them, km²'], tableRows)}</details>`;
  return surePart(n, 'latitude alone against the full method', finding, body, `The count uses the measured Arctic areas. ${DRAWN}`);
}
// How many known analog sites come out high, middling and low for a lunar region (the verdicts are in validation.json).
function knownCounts(v, t) {
  const rows = ((((v || {}).known_sites || {}).sites || {}).known_analogs_poleward_of_59 || []).map((r) => (r.targets || {})[t.id] || {}).filter((x) => x.percentile_among_ranked != null);
  const count = (w) => rows.filter((x) => x.verdict === w).length;
  return { n: rows.length, hi: count('high'), mid: count('middling'), lo: count('low') };
}
const knownSentence = (k, where) => `Of ${fInt(k.n)} known analog sites, ${words(k.hi)} ${k.hi === 1 ? 'has' : 'have'} a high result ${where}. ${cap(words(k.mid))} ${k.mid === 1 ? 'has' : 'have'} a middle result, and ${words(k.lo)} ${k.lo === 1 ? 'has' : 'have'} a low result.`;
// 3. the results for known analog sites among the ranked areas
function sureKnown(v, t, n) {
  const K = v.known_sites || {}, lists = K.sites || {};
  const rows = (lists.known_analogs_poleward_of_59 || []).map((r) => ({ r, x: (r.targets || {})[t.id] || {} }));
  if (!rows.length) return '';
  const got = rows.filter((o) => o.x.percentile_among_ranked != null).sort((a, b) => b.x.percentile_among_ranked - a.x.percentile_among_ranked);
  const none = rows.filter((o) => o.x.percentile_among_ranked == null);
  const finding = knownSentence(knownCounts(v, t), `for ${esc(t.name)}`);
  const name = (r) => (r.area != null && D.cells.ids[r.area] === r.cell ? `<button type="button" class="place-btn" data-cell="${r.area}">${esc(r.name)}</button>` : esc(r.name));
  const hours = (o) => (o.x.long_open_hours != null ? `${fH(o.x.long_open_hours)} h${o.r.hemisphere === 'S' ? ' in the rock season' : ' a year'}` : 'no figure');
  const row = (o) => (o.x.percentile_among_ranked != null
    ? `<div class="row"><span class="name">${name(o.r)}<small>${hours(o)}</small></span><span class="track thirds"><b style="left:${o.x.percentile_among_ranked.toFixed(1)}%"></b></span><span class="v">${Math.round(o.x.percentile_among_ranked)}%</span></div>`
    : `<div class="row"><span class="name">${name(o.r)}<small>${o.r.in_the_search === false ? 'outside the search' : 'no figure'}</small></span><span class="track unknown"></span><span class="v">unknown</span></div>`);
  const all = [['known_analogs_poleward_of_59', 'Known analog site'], ['named_sites_north', 'Named place, north'], ['antarctic_sites', 'Named place, Antarctica']];
  const tableRows = [];
  for (const [key, label] of all) for (const r of lists[key] || []) {
    const x = (r.targets || {})[t.id] || {};
    tableRows.push([esc(r.name) + `<small> (${label})</small>`, x.long_open_hours != null ? fH(x.long_open_hours) : 'unknown', x.percentile_among_ranked != null ? Math.round(x.percentile_among_ranked) + '%' : 'unknown', x.verdict === 'middling' ? 'middle' : (x.verdict || 'unknown'), r.cell_ranked ? 'yes' : 'no']);
  }
  const body = `<p class="note">The dot shows the share of ranked areas in the same hemisphere with fewer hours after snow and terrain. In Antarctica, the hours are those of the rock season. Snow is not measured there.</p>
    <p class="note">Earlier teams selected these sites for factors other than the Sun's height: geology, landforms, life or logistics. This is a general check. It does not test the order of the list.</p>
    <div class="rows"><div class="row scale"><span></span><span class="ends thirds"><span>bottom third</span><span>middle</span><span>top third</span></span><span></span></div>
    ${got.map(row).join('')}${none.length ? `<div class="group">No figure: the page shows these as unknown, never as zero</div>${none.map(row).join('')}` : ''}</div>
    <details class="table-view"><summary>Show each known and named place in a table</summary>${numTable(['Place', 'Hours after snow and terrain', 'Ranked areas with fewer hours', 'Verdict', 'Is its own area ranked?'], tableRows)}</details>`;
  return surePart(n, 'the results for known analog sites', finding, body, `Select a place to open its place card. ${DRAWN}`);
}
// 4. how much each choice we made moves the count
function sureSensitivity(v, t, n) {
  const st = ((v.sensitivity || {}).targets || {})[t.id];
  if (!st || !st.table || !st.table.length) return '';
  const isCloud = (r) => /cloud/.test(r.choice);
  const plain = (s) => areasWord(s).replace('no refraction', 'no change in light direction from air').replace('with the stale-flag rule', 'with our rule for maps with unchanged snow values').replace('as the maps read', 'as the snow maps read').replace('Sun geometry alone', 'the Sun alone');
  const moved = st.table.filter((r) => r.change != null), calm = moved.filter((r) => r.moves_more_than_a_quarter === false);   // the file's own mark, not a threshold typed here
  const big = moved.filter((r) => !isCloud(r)).reduce((a, r) => (a == null || Math.abs(r.change) > Math.abs(a.change) ? r : a), null);
  const finding = !moved.length ? `We did not change any choice for ${esc(t.name)}.`
    : calm.length === 0 ? `Each of the ${moved.length} choices changes the count for ${esc(t.name)} by more than a quarter. This result changes strongly with our choices.`
      : `Of ${moved.length} choices that we changed for ${esc(t.name)}, ${calm.length} ${calm.length === 1 ? 'changes' : 'change'} the count by a quarter or less.${big ? ` The largest change is ${signed(big.change)}.` : ''}`;
  const F = ((v.latitude_against_full_method || {}).targets || {})[t.id], fl = v.flags || {};
  const cl = F && F.summer_half ? (fl.terrain_step_is_a_census === true ? F.summer_half.all_measured_cells : F.summer_half.measured_cells_with_a_horizon).after_cloud : null;
  let html = '', scope = null;
  for (const r of st.table) {
    if (r.scope !== scope) { scope = r.scope; html += `<tr><th colspan="3">${esc(cap(plain(scope)))}</th></tr>`; }
    const kept = isCloud(r) && cl && cl.median_share_of_hours_kept != null ? `<small class="sub">The middle area keeps ${fPct(cl.median_share_of_hours_kept)} of its hours.</small>` : '';   // a count after cloud is never shown on its own
    const change = isCloud(r) ? `keeps ${cl && cl.median_share_of_hours_kept != null ? fPct(cl.median_share_of_hours_kept) : 'an unknown share'} of the hours` : r.change == null ? 'baseline' : `<span class="chg"><i style="${r.change >= 0 ? 'left' : 'right'}:50%;width:${Math.min(50, Math.abs(r.change) * 50).toFixed(1)}%"></i></span><span class="chg-v">${signed(r.change)}</span>`;
    html += `<tr><td>${esc(cap(plain(r.choice.replace(/^baseline: /, ''))))}${r.moves_more_than_a_quarter ? ' <span class="tag">more than a quarter</span>' : ''}${kept}</td><td class="num">${isCloud(r) ? 'not a count' : fInt(r.cells)}</td><td class="num">${change}</td></tr>`;
  }
  const body = `<p class="note">Each row changes one choice. The code counts areas again if they keep at least ${fInt((v.sensitivity || {}).threshold_h)} hours in the summer half. The code compares each change with the first row of its group.${big ? ` The largest change comes from this choice: ${esc(plain(big.choice))}.` : ''}</p>
    <div class="table-wrap"><table><thead><tr><th>The changed choice</th><th class="num">Areas that pass</th><th class="num">Change</th></tr></thead><tbody>${html}</tbody></table></div>`;
  return surePart(n, 'how much our own choices matter', finding, body, `The count uses the measured Arctic areas. ${DRAWN}`);
}
// 5. the snow maps against weather stations
function sureSnow(v, t, n) {
  const c = v.snow_station_check;
  if (!c || !c.overall || c.overall.stations == null) return '';
  // The file holds the comparison for both kinds of snow odds. Shown is the kind the measured areas use
  // (meta.json > snow.measured_cells_rule); the rows of the calibration exist for the stale-flag rule only.
  const per = c.periods || {}, STALE = 'with_stale_flag_rule', rule = (D.meta.snow || {}).measured_cells_rule, me = c.method || {}, sel = c.selection || {};
  const year = per.whole_year || {}, use = rule && year[rule] && year[rule].mean_bias != null ? rule : STALE;
  const o = use === STALE ? c.overall : year[use];
  const apart = use !== STALE && year[STALE] && year[STALE].mean_bias != null ? Math.abs(year[STALE].mean_bias - o.mean_bias) * 100 : null;
  const w = per.winter_half && per.winter_half[use], s = per.summer_half && per.summer_half[use];
  const often = (x) => `${points(x)} points ${x < 0 ? 'less' : 'more'} often`;
  const finding = w && s && w.mean_bias != null && s.mean_bias != null
    ? `In winter, the snow maps show snow-free ground ${often(w.mean_bias)} than ${fInt(o.stations)} weather stations do. In summer, they show it ${often(s.mean_bias)}.`
    : `Over the year, the snow maps show snow-free ground ${often(o.mean_bias)} than ${fInt(o.stations)} weather stations do.`;
  const cal = (c.calibration || []).map((r) => {
    const label = `maps say ${Math.round(r.ims_low * 100)} to ${Math.round(r.ims_high * 100)}%`, sub = `${fInt(r.n_station_bins)} comparisons`;
    return r.mean_station_snow_free == null || r.mean_ims == null
      ? `<div class="row"><span class="name">${label}<small>${sub}</small></span><span class="track unknown"></span><span class="v">unknown</span></div>`
      : `<div class="row"><span class="name">${label}<small>${sub}</small></span><span class="track"><i style="width:${(r.mean_station_snow_free * 100).toFixed(1)}%"></i><span class="rule" style="left:${(r.mean_ims * 100).toFixed(1)}%"></span></span><span class="v">${Math.round(r.mean_station_snow_free * 100)}%</span></div>`;
  }).join('');
  const period = me.period ? me.period.split(';')[0] : '';
  const body = `<p class="note">A point is 1 percent of the days. ${o.mean_bias < 0 ? 'The maps show snow more often than the stations. Thus, on average, our hours on snow-free ground are too low.' : 'The maps show snow less often than the stations. Thus, on average, our hours on snow-free ground are too high.'}</p>
    ${cal ? `<p class="note">Each row takes the ten-day periods in which the maps gave those odds of snow-free ground. The bar shows how often the stations then reported no snow. The vertical line is the mean from the maps.${apart != null ? ` These rows use our rule for maps with unchanged snow values. Over the year, this rule changes the difference by ${apart.toFixed(1)} points.` : ''}</p><div class="rows">${cal}</div>` : ''}
    <p class="note">The check uses ${fInt(o.n)} comparisons at ${fInt(o.stations)} stations${me.min_lat != null ? ` north of ${me.min_lat}°` : ''}${period ? `, ${esc(period)}` : ''}. A comparison is one station in one ten-day period.${o.mean_abs_difference != null ? ` The mean difference, without the sign, is ${points(o.mean_abs_difference)} points.` : ''}${sel.examined != null && sel.kept != null ? ` We examined ${fInt(sel.examined)} stations and kept ${fInt(sel.kept)} that report snow depth on most winter days.` : ''}</p>
    <details class="table-view"><summary>Show these numbers as a table</summary>${numTable(['Part of the year', 'Stations', 'Comparisons', 'Maps minus stations, points', 'Difference without the sign, points'],
    Object.values(per).filter((p) => p[use]).map((p) => [esc(cap((p.what || '').replace(/\bbins\b/, 'ten-day periods'))) + (p.days ? `<small> (${esc(p.days)})</small>` : ''), p[use].stations != null ? fInt(p[use].stations) : 'unknown', p[use].n != null ? fInt(p[use].n) : 'unknown', p[use].mean_bias != null ? fT(+(p[use].mean_bias * 100).toFixed(1)) : 'unknown', p[use].mean_abs_difference != null ? (p[use].mean_abs_difference * 100).toFixed(1) : 'unknown']))}</details>`;
  return surePart(n, 'the snow maps against weather stations', finding, body, `Stations: NOAA GHCN-Daily snow depth. Snow maps: IMS daily maps, 4 km. ${DRAWN}`);
}

// ---------- closing sections: sources with their exact credit lines, and the licence line, from sources.json ----------
const linkify = (text) => esc(text).replace(/https?:\/\/[^\s<"]+/g, (u) => { const tail = (u.match(/[.,;:)]+$/) || [''])[0], url = tail ? u.slice(0, -tail.length) : u; return `<a href="${url}" rel="noopener">${url}</a>${tail}`; });
// A "Used for" line comes from data/SOURCES.md, which also names our own files and scripts. The page leaves those
// names out and prints the rest, in sentences of at most MAX_WORDS words.
const plainUse = (text) => fit(areasWord(String(text || '')
  .replace(/\s*\((?:[^()]|\([^()]*\))*\)/g, (p) => (/[\w-]+\.(?:json|py|md|csv|tab)\b|\w\/\w/.test(p) ? '' : p))
  .replace(/,? fetched by \S+ into \S+/g, '').replace(/ typed into \S+\.py/g, '')));
function renderClosing() {
  const host = $('sources-full');
  if (!host || !NEAR.more) return;
  const s = extra('sources.json');
  if (!s || !s.sources || host.dataset.done) return;   // until the file is there (or if it is missing) the short list from meta.json stays
  host.dataset.done = '1';
  const groups = [['NASA', 'NASA data'], ['partner agency', 'Data of a partner space agency (ESA)'], ['other', 'Other open data']];
  const wv = (s.nasa_data || []).find((x) => /Worldview/.test(x.name || ''));
  let html = '';
  for (const [key, label] of groups) {
    const list = s.sources.filter((x) => x.group === key);
    if (!list.length) continue;
    html += `<h3>${label}</h3><ul class="src-list">` + list.map((x) => `<li><span class="src-name">${x.link ? `<a href="${esc(x.link)}" rel="noopener">${esc(x.name)}</a>` : esc(x.name)}</span><small>${esc(x.provider || '')}. Used for: ${esc(plainUse(x.used_for) || areasWord(x.used_for || '') + '.')}${x.credit_ref ? ` Credit line ${esc(x.credit_ref)} below.` : ''}</small></li>`).join('')
      + (key === 'NASA' && wv ? `<li><span class="src-name"><a href="${esc(wv.link)}" rel="noopener">NASA Worldview</a></span><small>Each place card links to it for a satellite view of the ground. Our own figures do not use it.</small></li>` : '') + '</ul>';
  }
  html += `<h3>Credit lines, as the providers ask for them</h3><ul class="credit-list">${(s.credits || []).filter((c) => c.text).map((c) => `<li><b>${esc(c.ref)}. ${esc(c.title)}.</b> ${linkify(c.text)}</li>`).join('')}</ul>`;
  host.innerHTML = html;
  $('sources').hidden = true;
  if (s.licence_line) {
    const n = s.notices || {};
    $('licence-line').innerHTML = esc(s.licence_line) + [n.copernicus_liability, n.comnap].filter(Boolean).map((x) => `</p><p>${esc(x)}${/[.!?]$/.test(x) ? '' : '.'}`).join('');
  }
}

// ---------- take the data away: the list on screen as CSV or GeoJSON, and the link to the present view ----------
// Both files are built here, in the browser, from the data the page has loaded. Unknown is left empty (null in
// GeoJSON), never zero. The column names carry the units. The source and licence lines are inside the file.
function listRows() {   // the rows of the short list now on screen: {i: area, list, row, score, t: lunar region index}
  const m = D.meta, t = target(), ti = tIndex(), top = D.sites.top[t.id], out = [];
  const add = (list, rows, tix = ti) => listEntries(rows, m.targets[tix].id).forEach((r, k) => out.push({ i: r.cell, list, row: k + 1, score: r.score != null ? r.score : null, t: tix }));
  if (S.tab === 'summer') { add('top summer areas', top.north_lighting); add('top summer areas with rock that also matches', top.north_full); }
  else if (S.tab === 'winter') add('winter exceptions', top.winter);
  else if (S.tab === 'belt') { const ridge = hardest(); add(`the ${ridge.short} belt`, D.sites.top[ridge.id].north_lighting, m.targets.indexOf(ridge)); }
  else if (S.tab === 'famous') add('famous places checked', D.sites.named.filter((s) => s.hemisphere === 'N'));
  else { add('Antarctica, best ranked areas', top.south_lighting); add('Antarctica, named places', D.sites.named.filter((s) => s.hemisphere === 'S')); }
  return out;
}
const listTarget = () => (S.tab === 'belt' ? hardest() : target());   // the belt list is about the site with the lowest Sun, whatever the bar says
const r1 = (v) => (v == null || Number.isNaN(v) ? null : Math.round(v * 10) / 10);
const TAKE_COLUMNS = [   // [name with its unit, value]; null means unknown or not measured
  ['list', (r) => r.list],
  ['row_in_list', (r) => r.row],
  ['place_name', (r) => D.cells.site[r.i] || null],
  ['region', (r) => D.cells.regions[D.cells.region[r.i]] || null],
  ['latitude_deg_north', (r) => +D.lat[r.i].toFixed(2)],
  ['longitude_deg_east', (r) => +D.lon[r.i].toFixed(2)],
  ['area_id', (r) => D.cells.ids[r.i]],
  ['lunar_region', (r) => D.meta.targets[r.t].name],
  ['sun_ceiling_deg', (r) => D.meta.targets[r.t].limit_deg],
  ['score_0_to_1', (r) => (r.score == null ? null : Math.round(r.score * 1000) / 1000)],
  ['sun_only_h_per_year', (r) => r1(flatYear(r.i, r.t))],
  ['on_snow_free_ground_h_per_year', (r) => (D.isN[r.i] ? r1(yr(r.i, 'snow_free', r.t)) : null)],
  ['after_snow_and_terrain_h_per_year', (r) => (D.isN[r.i] ? r1(yr(r.i, 'open', r.t)) : null)],
  ['winter_half_on_snow_free_ground_h', (r) => (D.isN[r.i] ? r1(yr(r.i, 'snow_free_winter', r.t)) : null)],
  ['winter_half_after_snow_and_terrain_h', (r) => (D.isN[r.i] ? r1(yr(r.i, 'open_winter', r.t)) : null)],
  ['rock_season_sun_only_h', (r) => (D.isN[r.i] ? null : r1(southYear(r.i, 'rock_flat', r.t)))],
  ['rock_season_after_terrain_h', (r) => (D.isN[r.i] ? null : r1(southYear(r.i, 'rock_open', r.t)))],
  ['bare_ground_percent', (r) => (D.cells.bare[r.i] >= 0 ? D.cells.bare[r.i] : null)],
  ['snow_status', (r) => D.status[r.i] || null],
  ['best_ten_day_periods', (r) => { const b = bestText(r.i, D.cells.horizon_n[r.i] != null ? 3 : 2, r.t); return b === 'none' ? null : b; }],
  ['published_analog_use', (r) => knownText(r.i)],
  ['place_card_link', (r) => location.href.split('#')[0] + '#' + new URLSearchParams({ view: D.isN[r.i] ? 'arctic' : 'antarctic', target: D.meta.targets[r.t].id, place: D.cells.ids[r.i], go: 'map' }).toString()],
];
function takeNotes() {   // what the file is, where it comes from and how it may be used: the same lines in both formats
  const m = D.meta, t = listTarget(), s = X.got['sources.json'], tab = (tabList().find(([k]) => k === S.tab) || [])[1] || S.tab;
  const notice = copernicusNotice();
  return {
    title: `Earth Twin Finder: ${tab}, for the lunar region ${t.name} (Sun ceiling ${t.limit_deg.toFixed(2)} degrees)`,
    saved_from: location.href.split('#')[0] + '#' + hashString(),
    data_written: m.generated,
    what: `Each row is one area of approximately ${m.scoring.cell_km} km across. Latitude and longitude give its centre. The hours are the hours with the Sun above the horizon and no higher than the Sun ceiling of the lunar region. ${m.long_rule.text}`,
    unknown: 'An empty field (null in GeoJSON) means unknown, not measured or not applicable. It never means zero. Snow is not measured in Antarctica. Thus, only the columns for the rock season contain figures there.',
    source: 'The Earth Twin Finder team (NASA Space Apps Challenge ' + m.generated.slice(0, 4) + ') calculated these figures from open data: ' + m.sources.map((x) => x.name).join('; ') + '.' + (notice ? ' Terrain figures: ' + notice + '.' : ''),
    licence: s && s.licence_line ? s.licence_line : 'See the section "Licence" of the page that you saved this file from.',
  };
}
function takeCsv() {
  const q = (v) => (v == null ? '' : /[",\n\r]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const notes = takeNotes(), rows = listRows();
  const head = ['Lines that start with # are notes. The table starts at the first line without #.', notes.title, 'Saved from: ' + notes.saved_from, 'Data written: ' + notes.data_written, notes.what, notes.unknown, 'Source: ' + notes.source, 'Licence: ' + notes.licence];
  return head.map((l) => '# ' + String(l).replace(/[\r\n]+/g, ' ')).join('\n') + '\n' + TAKE_COLUMNS.map((c) => c[0]).join(',') + '\n' + rows.map((r) => TAKE_COLUMNS.map((c) => q(c[1](r))).join(',')).join('\n') + '\n';
}
function takeGeoJson() {
  const notes = takeNotes();
  return JSON.stringify({
    type: 'FeatureCollection', name: notes.title, saved_from: notes.saved_from, data_written: notes.data_written, description: notes.what, unknown: notes.unknown,
    source: notes.source, licence: notes.licence,
    features: listRows().map((r) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [+D.lon[r.i].toFixed(2), +D.lat[r.i].toFixed(2)] }, properties: Object.fromEntries(TAKE_COLUMNS.map((c) => [c[0], c[1](r)])) })),
  }, null, 1) + '\n';
}
function saveText(name, type, text) {
  const url = URL.createObjectURL(new Blob([text], { type })), a = document.createElement('a');
  a.href = url; a.download = name; a.hidden = true;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
const extraWait = (name) => new Promise((done) => { const tick = () => { const got = extra(name); if (got !== undefined) done(got); else setTimeout(tick, 40); }; tick(); });
async function saveList(kind, status) {
  if (pendingListSettings()) { if (status) status.textContent = 'Open Tools or Planner to restore the saved list settings first.'; return; }
  await extraWait('sources.json');   // the licence line; the file is saved without it only if sources.json is missing
  const rows = listRows(), base = `earth-twin-finder_${S.tab}_${listTarget().id}`;
  if (kind === 'csv') saveText(base + '.csv', 'text/csv;charset=utf-8', takeCsv());
  else saveText(base + '.geojson', 'application/geo+json', takeGeoJson());
  if (status) status.textContent = `The page saved ${base}.${kind === 'csv' ? 'csv' : 'geojson'} with ${rows.length} ${rows.length === 1 ? 'row' : 'rows'}.`;
}
async function copyLink(status) {
  const url = location.href.split('#')[0] + '#' + hashString();
  let ok = false;
  try { await navigator.clipboard.writeText(url); ok = true; } catch (e) { /* no clipboard access: try the older way */ }
  if (!ok) {
    const box = document.createElement('textarea');
    box.value = url; box.setAttribute('readonly', ''); box.style.cssText = 'position:fixed;left:-999px;top:0';
    document.body.appendChild(box); box.select();
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    box.remove();
  }
  if (!status) return;
  if (ok) status.textContent = 'The page copied the link. The link restores the destination, the view and the open card.';
  else { status.innerHTML = '<label>Copy the link from here: <input type="text" readonly></label>'; const input = status.querySelector('input'); input.value = url; input.focus(); input.select(); }
}
function renderTake() {
  const note = $('take-note');
  if (!note || !NEAR.lists || !D.ready) return;
  extra('sources.json');   // read ahead, so that a saved file carries the licence line
  note.textContent = 'The file holds the list on the screen. The column names give the units. An unknown value is empty. The source and licence lines are in the file.';
}
function wireTake() {
  const menu = $('save-menu');
  if (menu) {
    const status = $('take').querySelector('.take-status');
    menu.querySelectorAll('[data-save]').forEach((b) => b.addEventListener('click', () => { menu.open = false; if (D.ready) saveList(b.dataset.save, status); menu.querySelector('summary').focus(); }));
    menu.addEventListener('keydown', (e) => { if (e.key === 'Escape' && menu.open) { e.stopPropagation(); menu.open = false; menu.querySelector('summary').focus(); } });
    document.addEventListener('click', (e) => { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  }
  document.querySelectorAll('[data-copy-link]').forEach((b) => b.addEventListener('click', () => { if (D.meta) copyLink(b.parentElement.querySelector('.take-status')); }));
}

// ---------- the destination shell ----------
const deepOpen = new Set(), onlyHidden = new Set();
const goalLabel = (goal) => ({ full: 'All factors', landscape: 'Landscape', environment: 'Environment' }[goal] || 'All factors');
const expandedLists = new Set();
const viewSnapshots = new WeakMap();
function captureView() {
  const token = Object.freeze({});
  viewSnapshots.set(token, {
    state: stateCopy(), deepOpen: [...deepOpen], planTab, expandedLists: [...expandedLists],
    pendingMarsAnchor: pendingMarsAnchor && { ...pendingMarsAnchor },
    goHold: goHold && { ...goHold }, navigationGeneration,
  });
  return token;
}
function restoreView(token, state) {
  const saved = viewSnapshots.get(token);
  if (!saved) return false;
  const restored = structuredClone(state ?? saved.state);
  // Keep the generation monotonic: saved navigation must not resume after the tour.
  cancelNavigation();
  restoringView = true;
  try {
    for (const key of Object.keys(S)) delete S[key];
    Object.assign(S, structuredClone(DEFAULT_STATE));
    for (const [key, value] of Object.entries(restored)) {
      if (!['__proto__', 'constructor', 'prototype'].includes(key) && (STATE_KEYS.has(key) || value != null)) S[key] = value;
    }
    centreOnPlace = false;
    deepOpen.clear(); saved.deepOpen.forEach((id) => deepOpen.add(id));
    expandedLists.clear(); saved.expandedLists.forEach((id) => expandedLists.add(id));
    planTab = saved.planTab;
    fixState();
    writeHash(true);
    renderAll();
    document.querySelectorAll('[data-deep]').forEach((button) => {
      const root = sectionFor(button.dataset.deep);
      button.setAttribute('aria-expanded', String(!!root && !root.hidden && (root.tagName !== 'DETAILS' || root.open)));
    });
    // Subscribers can redraw, but cannot add default extension keys to the saved state.
    notifyState(true);
  } finally {
    restoringView = false;
  }
  return true;
}
function compactLists(panel) {
  const paragraphs = [...panel.querySelectorAll(':scope > p:not(.caption)')];
  if (paragraphs.length) {
    const fold = document.createElement('details'), summary = document.createElement('summary');
    fold.className = 'fold list-explanation'; summary.textContent = 'How to read this list';
    paragraphs[0].before(fold); fold.append(summary, ...paragraphs);
  }
  panel.querySelectorAll('.table-wrap').forEach((wrap, index) => {
    const rows = [...wrap.querySelectorAll('tbody > tr')];
    if (rows.length <= 5) return;
    const key = [S.target, S.tab, index].join(':'), button = document.createElement('button');
    button.type = 'button'; button.className = 'btn btn-ghost show-all';
    wrap.id = 'short-list-' + index; button.setAttribute('aria-controls', wrap.id);
    const draw = () => {
      const all = expandedLists.has(key);
      rows.forEach((row, i) => { row.hidden = !all && i >= 5; });
      button.textContent = all ? 'Show five' : `Show all (${rows.length})`;
      button.setAttribute('aria-expanded', String(all));
    };
    button.addEventListener('click', () => { if (expandedLists.has(key)) expandedLists.delete(key); else expandedLists.add(key); draw(); });
    wrap.after(button); draw();
  });
  panel.querySelectorAll(':scope > h3').forEach((heading) => {
    const fold = document.createElement('details'), summary = document.createElement('summary');
    fold.className = 'fold'; summary.textContent = heading.textContent;
    heading.before(fold); fold.append(summary); heading.remove();
    while (fold.nextElementSibling && !fold.nextElementSibling.matches('h3,.caption,details')) fold.append(fold.nextElementSibling);
  });
}
function compactSky(root) {
  if (root.querySelector('.sky-support')) return;
  const main = root.querySelector('.sk-main'), day = root.querySelector('.sk-day');
  if (!main || !day) return;
  const fold = document.createElement('details'), summary = document.createElement('summary');
  fold.className = 'fold sky-support'; summary.textContent = 'The Sun at this time and the hours in this day';
  fold.append(summary);
  const readouts = main.querySelector('.sk-readouts');
  if (readouts) fold.append(readouts);
  const following = [...root.children].slice([...root.children].indexOf(main) + 1).filter((node) => !node.matches('details,.next-step'));
  main.after(fold); fold.append(...following);
}
function lunarListGroup(t) {
  if (Array.isArray(t.lists)) return t.lists.some((list) => /\b2024\b/.test(list)) ? 'NASA 2024 list' : 'NASA 2022 list only';
  const lines = String(t.list_summary || '').split(/(?<=[.!?])\s+/);
  return lines.some((line) => /\b2024\b/.test(line) && !/\b(?:not|no longer|removed)\b/i.test(line))
    ? 'NASA 2024 list' : 'NASA 2022 list only';
}
function destinationItems() {
  const marsGroups = ['NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones'];
  const moon = [...D.meta.targets].sort((a, b) => (a.limit_deg ?? Infinity) - (b.limit_deg ?? Infinity)).map((t) => {
    const group = lunarListGroup(t), tags = Array.isArray(t.lists) ? t.lists.filter((tag) => typeof tag === 'string')
      : t.list_summary ? [group] : [];
    if (t.has_model === false) tags.push('no terrain model');
    return { mode: 'moon', id: t.id, name: t.name, ceiling: t.limit_deg, group, tags,
      note: [t.list_line, t.list_summary].filter((value) => typeof value === 'string').join(' ') };
  });
  const mars = (answerData.mars?.sites || []).map((t) => {
    const tags = Array.isArray(t.lists) ? t.lists.filter((tag) => typeof tag === 'string') : [];
    const group = marsGroups.find((name, i) => tags.some((tag) => i === 0 ? /NASA landing sites?/i.test(tag)
      : i === 1 ? /2021/.test(tag) : /2015/.test(tag))) || 'Mars';
    return { mode: 'mars', id: t.id, name: t.name, ceiling: t.sun?.noon_elev_max_deg, lat: t.lat,
      lon: t.lon_east ?? t.lon, region: t.region || '', group, tags, note: t.why || '' };
  });
  return [...moon, ...mars];
}
function destinationDetail(item) {
  if (item.mode === 'moon') return Number.isFinite(item.ceiling) ? `Sun up to ${item.ceiling.toFixed(2)}°` : 'Sun ceiling unknown';
  const lat = Number.isFinite(item.lat) ? `${Math.abs(item.lat).toFixed(2)}°${item.lat < 0 ? 'S' : 'N'}` : 'latitude unknown';
  const lon = Number.isFinite(item.lon) ? `${Math.abs(item.lon).toFixed(2)}°${item.lon < 0 ? 'W' : 'E'}` : 'longitude unknown';
  return `${lat} · ${lon}`;
}
function filterDestinations(host) {
  const query = host.querySelector('.destination-search').value.trim().toLocaleLowerCase();
  const terms = query.split(/\s+/).filter(Boolean);
  let count = 0;
  host.querySelectorAll('.destination-option').forEach((option) => {
    option.hidden = !terms.every((term) => option.dataset.search.includes(term));
    if (!option.hidden) count++;
  });
  host.querySelectorAll('.destination-list-group').forEach((group) => {
    const total = group.querySelectorAll('.destination-option').length;
    const visible = group.querySelectorAll('.destination-option:not([hidden])').length;
    group.hidden = !visible;
    group.querySelector('.destination-count').textContent = query ? `${visible} of ${total}` : String(total);
  });
  host.querySelector('.destination-empty').hidden = count > 0;
  host.querySelector('.destination-result-count').textContent = `${count} ${count === 1 ? 'destination' : 'destinations'}`;
  host.querySelector('.destination-list').scrollTop = 0;
}
function renderDestinations() {
  const items = destinationItems(), selected = items.find((item) => item.mode === S.dest && item.id === (S.dest === 'moon' ? S.target : S.msite));
  const groups = ['NASA 2024 list', 'NASA 2022 list only', 'NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones', 'Mars'];
  for (const id of ['destination-picker', 'bar-dest']) {
    const host = $(id); if (!host) continue;
    const signature = JSON.stringify(items);
    if (host.dataset.options !== signature) {
      const wasOpen = host.querySelector('.destination-trigger')?.getAttribute('aria-expanded') === 'true';
      const query = host.querySelector('.destination-search')?.value || '';
      host.dataset.options = signature;
      host.innerHTML = `<button type="button" class="destination-trigger" aria-haspopup="dialog" aria-expanded="false" aria-controls="${id}-menu" data-destination-open="${id}"></button>
        <button type="button" class="destination-backdrop" data-destination-close aria-label="Close destinations" tabindex="-1" hidden></button>
        <div class="destination-menu" id="${id}-menu" role="dialog" aria-label="Select a destination" hidden>
          <div class="destination-search-row"><label class="sr-only" for="${id}-search">Filter destinations by name, list or region</label>
            <input class="destination-search" id="${id}-search" type="search" placeholder="Filter destinations" autocomplete="off" spellcheck="false" aria-controls="${id}-list">
            <button type="button" class="btn btn-ghost destination-close" data-destination-close>Close</button></div>
          <p class="sr-only destination-result-count" role="status" aria-live="polite"></p>
          <div class="destination-list" id="${id}-list" role="listbox" aria-label="Destinations">${groups.map((group, gi) => {
            const rows = items.filter((item) => item.group === group); if (!rows.length) return '';
            return `<div class="destination-list-group" role="group" aria-labelledby="${id}-group-${gi}"><p class="destination-group-label" id="${id}-group-${gi}"><span>${rows[0].mode === 'moon' ? 'Moon · ' : group === 'Mars' ? '' : 'Mars · '}${esc(group)}</span><span class="destination-count">${rows.length}</span></p>${rows.map((item) => {
              const search = [item.name, item.mode, item.region, ...item.tags].join(' ').toLocaleLowerCase();
              return `<button type="button" class="destination-option" role="option" tabindex="-1" data-search="${esc(search)}" data-destination="${item.mode}" data-${item.mode === 'moon' ? 'pick-target' : 'pick-msite'}="${esc(item.id)}" title="${esc(item.note || item.name)}"><span class="destination-name">${esc(item.name)}</span><span class="destination-ceiling">${destinationDetail(item)}</span>${item.tags.map((tag) => `<small class="destination-tag">${esc(tag)}</small>`).join('')}${item.region ? `<small class="destination-region">${esc(item.region)}</small>` : ''}</button>`;
            }).join('')}</div>`;
          }).join('')}</div><p class="destination-empty" hidden>No destinations match this filter.</p></div>`;
      host.querySelector('.destination-search').value = query;
      filterDestinations(host);
      if (wasOpen) openDestination(host, false);
    }
    host.querySelector('.destination-trigger').textContent = selected ? `${cap(selected.mode)} · ${selected.name} · ${destinationDetail(selected)}` : 'Select a destination';
    host.querySelectorAll('[role=option]').forEach((option) => {
      const active = option.dataset.destination === S.dest && (option.dataset.pickTarget === S.target || option.dataset.pickMsite === S.msite);
      option.setAttribute('aria-selected', String(active));
    });
  }
}
function closeDestinations(returnFocus = false) {
  document.querySelectorAll('.destination-menu:not([hidden])').forEach((menu) => {
    menu.hidden = true;
    const host = menu.parentElement, trigger = host.querySelector('.destination-trigger');
    host.querySelector('.destination-backdrop').hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    if (returnFocus) trigger.focus({ preventScroll: true });
  });
  document.documentElement.classList.remove('destination-sheet-open');
  updateResultsBar();
}
function positionDestinationMenu(host) {
  const menu = host.querySelector('.destination-menu');
  if (menu.hidden) return;
  if (matchMedia('(max-width: 760px)').matches) { menu.removeAttribute('style'); return; }
  const rect = host.querySelector('.destination-trigger').getBoundingClientRect();
  const below = innerHeight - rect.bottom - 12, above = rect.top - 12;
  const upwards = below < Math.min(240, innerHeight * .6) && above > below;
  const width = Math.min(Math.max(rect.width, 320), innerWidth - 24);
  Object.assign(menu.style, { left: `${Math.max(12, Math.min(rect.left, innerWidth - width - 12))}px`, width: `${width}px`,
    top: upwards ? 'auto' : `${rect.bottom + 5}px`, bottom: upwards ? `${innerHeight - rect.top + 5}px` : 'auto',
    maxHeight: `${Math.min(innerHeight * .6, Math.max(80, upwards ? above : below))}px` });
}
function scrollDestinationIntoView(option) {
  const list = option?.closest('.destination-list'); if (!list) return;
  const row = option.getBoundingClientRect(), box = list.getBoundingClientRect();
  if (row.top < box.top) list.scrollTop += row.top - box.top;
  else if (row.bottom > box.bottom) list.scrollTop += row.bottom - box.bottom;
}
function openDestination(host, resetFilter = true) {
  closeDestinations();
  const menu = host.querySelector('.destination-menu'), input = host.querySelector('.destination-search');
  if (resetFilter) { input.value = ''; filterDestinations(host); }
  menu.hidden = false; host.querySelector('.destination-backdrop').hidden = false;
  host.querySelector('.destination-trigger').setAttribute('aria-expanded', 'true');
  document.documentElement.classList.add('destination-sheet-open');
  updateResultsBar();
  positionDestinationMenu(host);
  input.focus({ preventScroll: true });
  scrollDestinationIntoView(menu.querySelector('[aria-selected=true]:not([hidden])') || menu.querySelector('[role=option]:not([hidden])'));
}
function renderPageTabs() {
  // tab2 remains in saved links, but the board, words, and places now share one page.
  renderExperimentResults();
  document.querySelectorAll('[data-plan-tab]').forEach((button) => {
    const active = button.dataset.planTab === planTab;
    button.setAttribute('aria-selected', String(active)); button.tabIndex = active ? 0 : -1;
    const panel = $(button.getAttribute('aria-controls'));
    if (panel) {
      panel.hidden = S.only === 'planner' && panel.closest('#planner-root') ? false : !active;
      panel.classList.add('tab-panel'); panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', button.id); panel.tabIndex = 0;
    }
  });
  if ($('planner-root')) $('planner-root').hidden = planTab === 'tools';
  if ($('tools-row')) $('tools-row').hidden = planTab !== 'tools' || !extensions.buttons.size || !!S.only;
}
async function prepareSection(id, generation = navigationGeneration) {
  if (id === 'experiment' || id === 'experiment-section') await loadModule('ask');
  if (id === 'ask') { if (S.tab2 === 'best') S.tab2 = 'words'; await loadModule('ask'); }
  if (id === 'ask-words') { S.tab2 = 'words'; await loadModule('ask'); }
  if (id === 'ask-root' || id === 'ask-results') { if (S.tab2 === 'best') S.tab2 = 'make'; await loadModule('ask'); }
  if (id === 'answer' || id === 'answer-section') S.tab2 = 'best';
  if (['planner', 'planner-root', 'pl-choices', 'pl-compare', 'pl-year'].includes(id)) {
    planTab = id === 'pl-compare' ? 'compare' : id === 'pl-year' ? 'year' : 'rehearse';
    await loadModule('planner');
  }
  if (id === 'tools' || id === 'tools-root') { planTab = 'tools'; await loadModule('tools'); }
  if (id.startsWith('mars')) { if (S.dest !== 'mars') set({ dest: 'mars' }); await loadModule('mars'); }
  if (generation !== navigationGeneration) return false;
  updateVisibility(); writeHash(true);
  return true;
}
function updateVisibility() {
  for (const node of onlyHidden) node.hidden = false;
  onlyHidden.clear();
  renderPageTabs();
  const only = S.only && sectionFor(S.only);
  document.body.classList.toggle('isolated-view', !!only);
  document.body.dataset.only = S.only || '';
  document.querySelectorAll('.hero, main > section, main > .time-row, .deep-section, [data-mode]').forEach((section) => {
    const mode = section.dataset.mode;
    const inOnly = !only || section === only || section.contains(only) || only.contains(section);
    const deep = section.classList.contains('deep-section');
    section.hidden = section.dataset.moduleMissing === 'true' || !!mode && mode !== S.dest || !inOnly
      || deep && !deepOpen.has(section.id) && !(only && inOnly);
  });
  if (only) {
    for (let node = only; node && node !== document.body; node = node.parentElement) node.hidden = false;
    for (let node = only; node && node.parentElement && node !== document.querySelector('main'); node = node.parentElement) {
      for (const sibling of node.parentElement.children) if (sibling !== node && !sibling.hidden) { sibling.hidden = true; onlyHidden.add(sibling); }
    }
  }
  if ($('topbar')) $('topbar').hidden = !!only;
  if ($('bar')) $('bar').hidden = !!only;
  if ($('footer')) $('footer').hidden = !!only;
  if ($('tools-row')) $('tools-row').hidden = planTab !== 'tools' || !extensions.buttons.size || !!only;
}
function revealSection(root) {
  for (let node = root; node && node !== document.body; node = node.parentElement) {
    if (node.classList.contains('deep-section')) deepOpen.add(node.id);
    if (node.tagName === 'DETAILS') node.open = true;
  }
  updateVisibility();
  if (root.tagName === 'DETAILS') root.open = true;
  document.querySelectorAll('[data-deep]').forEach((button) => { const target = sectionFor(button.dataset.deep); button.setAttribute('aria-expanded', String(!!target && !target.hidden && (target.tagName !== 'DETAILS' || target.open))); });
}
function railItems() {
  return S.dest === 'mars'
    ? [['experiment', 'Experiment'], ['places', 'Places'], ['mars-square', 'A square'], ['mars-list', 'Take it away'], ['deeper', 'Go deeper']]
    : [['experiment', 'Experiment'], ['places', 'Places'], ['when', 'When'], ['plan', 'Plan'], ['deeper', 'Go deeper']];
}
function renderInfoStrip() {
  if (!D.ready) return;
  if ($('info-destinations')) $('info-destinations').textContent = `${fInt(D.meta.targets.length)} Moon · ${answerData.mars ? fInt(answerData.mars.sites.length) : 'unknown'} Mars`;
  if ($('info-areas')) {
    $('info-areas').textContent = fInt(S.dest === 'mars' ? answerData.mars?.squares?.count : D.n);
    $('info-areas').previousElementSibling.textContent = S.dest === 'mars' ? 'Squares on Earth' : 'Areas on Earth';
  }
  if ($('info-factors')) $('info-factors').textContent = fInt(answerData.factorCount);
}
function firstMatchName() {
  const i = matches?.areas[0];
  if (i == null) return '';
  if (matches.mode === 'moon') return validArea(i) ? placeName(i) : 'Name unknown';
  const squares = answerData.mars?.squares, field = squares?.columns?.region, view = answerData.squares;
  if (field && view && (!field.file || field.file === squares.file)) {
    const offset = field.offset + i;
    if (field.type === 'uint8' && offset >= 0 && offset < view.byteLength) {
      const value = view.getUint8(offset);
      if (value !== field.unknown && squares.regions?.[value]) return squares.regions[value];
    }
  }
  return squares?.ids?.[i] ? `Square ${squares.ids[i]}` : 'Name unknown';
}
function renderExperimentResults() {
  if (!D.ready) return;
  if ($('answer-section')) $('answer-section').hidden = matches !== null;
  if ($('ask-results')) $('ask-results').hidden = matches === null;
  const label = $('results-bar-label'), place = $('results-bar-place');
  const count = matches?.areas.length || 0, unit = matches?.mode === 'mars' ? 'square' : 'area';
  const countText = `${fInt(count)} ${unit}${count === 1 ? '' : 's'}`;
  const summary = matches ? matches.label || `${countText} ${count === 1 ? 'passes' : 'pass'}.` : '';
  if (label) label.textContent = summary;
  if (place) {
    const prefix = summary.includes(`${fInt(count)} ${unit}`) || summary.includes(`${count} ${unit}`) ? '' : countText;
    place.textContent = matches ? [prefix, ...(count ? [firstMatchName(), fPct(matches.scores[0])] : [])].filter(Boolean).join(' · ') : '';
  }
  updateResultsBar();
}
function updateResultsBar() {
  const bar = $('results-bar'); if (!bar) return;
  const wasHidden = bar.hidden;
  const top = $('topbar')?.offsetHeight || 0;
  const inView = (node) => {
    if (!node || node.hidden || !node.getClientRects().length) return false;
    const box = node.getBoundingClientRect();
    return box.bottom > top && box.top < innerHeight;
  };
  bar.hidden = !matches || !!S.only || !!S.moon || document.body.classList.contains('drawer-open') || document.documentElement.classList.contains('destination-sheet-open')
    || ![...document.querySelectorAll('#ask-root, #ask-words')].some(inView) || inView($('places-section'));
  document.body.classList.toggle('results-bar-visible', !bar.hidden);
  if (wasHidden && !bar.hidden && !document.body.matches('.tl-touring, .tl-tour-restoring')) {
    requestAnimationFrame(keepExperimentFocusVisible);
  }
}
function keepExperimentFocusVisible() {
  // Check at execution too: a queued frame must not move the restored tour view.
  if (document.body.matches('.tl-touring, .tl-tour-restoring')) return;
  const bar = $('results-bar'), control = document.activeElement;
  if (bar && !bar.hidden && control?.closest('#ask-root, #ask-words')
    && control.getBoundingClientRect().bottom > bar.getBoundingClientRect().top) {
    control.scrollIntoView({ block: 'center' });
  }
}
function renderShell() {
  if (!D.ready || !$('destination-picker')) return;
  renderDestinations();
  renderInfoStrip();
  renderPageTabs();
  if ($('bar-mgoal')) $('bar-mgoal').innerHTML = ['full', 'landscape', 'environment'].map((goal) => `<button type="button" class="chip" data-mgoal="${goal}" aria-pressed="${S.mgoal === goal}">${goalLabel(goal)}</button>`).join('');
  $('step-rail').innerHTML = railItems().map(([id, label]) => `<a href="#go=${id}" data-rail="${id}">${label}</a>`).join('');
  $('theme-toggle').textContent = isDark() ? 'Light' : 'Dark';
  $('theme-toggle').setAttribute('aria-label', isDark() ? 'Use the light look' : 'Use the dark look');
  $('theme-toggle').setAttribute('aria-pressed', String(!isDark()));
  $('hero-next').textContent = S.dest === 'mars' ? 'See a square' : 'See when to go';
  $('hero-next').dataset.next = S.dest === 'mars' ? 'mars-square' : 'when';
  document.querySelectorAll('[data-stage]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.stage === S.stage)));
  const t = target(), floor = halfLevel();
  if (S.dest === 'moon') {
    let count = 0;
    for (let i = 0; i < D.n; i++) { const v = cellValue(i, 3, 'year'); if (Number.isFinite(v) && v >= floor) count++; }
    $('stage-finding').textContent = `${t.name}: ${fInt(count)} areas keep at least ${fH(floor)} h below ${t.limit_deg.toFixed(2)}° after snow and terrain.`;
    if ($('lists-finding')) $('lists-finding').textContent = `${answerLunarRows().filter((row) => validArea(row.i)).length} result rows link to the evidence for ${t.name}.`;
    if ($('map-finding')) $('map-finding').textContent = `${fInt(D.meta.counts.north_cells + D.meta.counts.south_cells)} areas show where the low Sun lasts. Each area is approximately ${D.meta.scoring.cell_km} km across.`;
    if ($('when-finding')) $('when-finding').textContent = `${fPct(D.meta.headline[t.id].summer_share_snow_free)} of the snow-free hours occur in the summer half for ${t.name}.`;
  } else {
    const mars = answerData.mars, site = mars?.sites.find((item) => item.id === S.msite), top = mars?.best_places?.[S.msite]?.[S.mgoal]?.[0];
    $('stage-finding').textContent = site ? `${site.name.split(',')[0]}: ${top?.region || 'no ranked square'}. First pass: squares of approximately ${fInt(mars.meta.square_km_about)} km. This is not a climate match.` : 'The Mars data is unavailable. Select a lunar region to see its Earth areas.';
    if ($('mars-finding')) $('mars-finding').textContent = $('stage-finding').textContent;
  }
  const i = D.idx.get(S.place);
  if (validArea(i) && $('place-summary')) {
    $('place-summary').textContent = `${placeName(i)} · ${fLat(D.lat[i])}, ${fLon(D.lon[i])}. ${fH(cellValue(i, 3, 'year'))} h a year after snow and terrain.`;
    const bt = bestText(i, 3, tIndex());
    if ($('place-finding')) $('place-finding').textContent = bt === 'none' ? `For ${t.name}, this place has no best ten-day periods.` : `For ${t.name}, the best ten-day periods here are ${bt}.`;
  } else {
    if ($('place-summary')) $('place-summary').textContent = 'No place card is open. The day below shows an example area.';
    if ($('place-finding')) $('place-finding').textContent = `${t.name} has a Sun ceiling of ${t.limit_deg.toFixed(2)}°. Select a place to see its dates and its day.`;
  }
  if ($('plan-finding')) $('plan-finding').textContent = `${fInt(D.meta.bins.length)} ten-day periods give dates to compare. Check access, permits and the local weather.`;
  drawStage(); refreshMarsMatches(); updateRail();
}
function updateRail() {
  const list = railItems(); let active = list[0][0];
  const offset = ($('bar')?.getBoundingClientRect().height || 0) + ($('topbar')?.offsetHeight || 72) + 80;
  for (const [id] of list) { const node = sectionFor(id); if (node && !node.hidden && node.getBoundingClientRect().top <= offset) active = id; }
  document.querySelectorAll('[data-rail]').forEach((link) => { if (link.dataset.rail === active) link.setAttribute('aria-current', 'step'); else link.removeAttribute('aria-current'); });
  const rail = $('step-rail'), current = rail?.querySelector('[aria-current=step]');
  if (rail && current) {
    const box = rail.getBoundingClientRect(), item = current.getBoundingClientRect();
    if (item.left < box.left) rail.scrollLeft += item.left - box.left;
    else if (item.right > box.right) rail.scrollLeft += item.right - box.right;
  }
  const hero = $('places-section');
  document.body.classList.toggle('past-hero', !!hero && hero.getBoundingClientRect().bottom <= ($('topbar')?.offsetHeight || 72));
  updateResultsBar();
}
function restoreStage() {
  const root = $('globes-root');
  root.innerHTML = '<div class="stage-still"><p class="eyebrow">Earth · polar map</p><canvas id="stage-fallback" role="img" aria-label="A still polar map of Earth"></canvas><p class="caption">Select a destination from the list. Open Flat maps to see the exact areas.</p><p class="caption">' + DRAWN + '</p></div>';
  root.hidden = false; drawStage();
}
function drawStage() {
  const canvas = $('stage-fallback'); if (!canvas || !D.ready) return;
  const ctx = canvas.getContext('2d'), w = 600, h = 520, r = 224, cx = w / 2, cy = h / 2;
  canvas.width = w; canvas.height = h;
  if (S.dest === 'mars' && answerData.world && answerData.squares) {
    drawMarsStage(ctx, w, h);
    canvas.setAttribute('aria-label', `A still world map of Earth. ${matches?.mode === 'mars' ? 'Rings and numbers show the first ten experiment matches.' : 'Rings show the best squares.'} First pass: squares of approximately ${fInt(answerData.mars.meta.square_km_about)} km.`);
    return;
  }
  const polarNorth = S.dest === 'mars' || north();
  const point = (lat, lon) => { const p = proj(lat, lon, polarNorth); return [cx + p[0] * r / R_DISC, cy + p[1] * r / R_DISC]; };
  ctx.clearRect(0, 0, w, h); ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
  ctx.fillStyle = css('--ocean'); ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = css('--land'); ctx.strokeStyle = css('--coast'); ctx.lineWidth = .7;
  for (const ring of polarNorth ? D.land.north : D.land.south) {
    ctx.beginPath();
    for (let j = 0; j < ring.length; j += 2) { const p = point(ring[j + 1] / D.land.scale, ring[j] / D.land.scale); if (j) ctx.lineTo(...p); else ctx.moveTo(...p); }
    ctx.closePath(); ctx.fill(); ctx.stroke();
  }
  ctx.strokeStyle = css('--graticule');
  for (const lat of [60, 70, 80]) { const p = point(polarNorth ? lat : -lat, 0); ctx.beginPath(); ctx.arc(cx, cy, Math.hypot(p[0] - cx, p[1] - cy), 0, Math.PI * 2); ctx.stroke(); }
  for (let lon = -180; lon < 180; lon += 30) { ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(...point(polarNorth ? 50 : -50, lon)); ctx.stroke(); }
  if (S.dest === 'moon') {
    const colours = ramp(), max = D.meta.scale.year_h;
    for (let i = 0; i < D.n; i++) {
      if (!!D.isN[i] !== polarNorth) continue;
      const v = cellValue(i, 3, 'year'); if (!Number.isFinite(v) || v <= 0) continue;
      const p = point(D.lat[i], D.lon[i]); ctx.fillStyle = colours[Math.max(1, Math.min(63, Math.round(v / max * 63)))]; ctx.fillRect(p[0], p[1], 1.5, 1.5);
    }
    ctx.strokeStyle = css('--moon'); ctx.lineWidth = 2;
    for (const row of answerLunarRows()) if (validArea(row.i) && !!D.isN[row.i] === polarNorth) { const p = point(D.lat[row.i], D.lon[row.i]); ctx.beginPath(); ctx.arc(...p, 5, 0, Math.PI * 2); ctx.stroke(); }
    if (matches?.mode === 'moon') drawMatchPins(ctx, matches.areas.slice(0, 10).flatMap((i, index) => {
      if (!validArea(i) || !!D.isN[i] !== polarNorth) return [];
      const [x, y] = point(D.lat[i], D.lon[i]); return [{ x, y, rank: index + 1 }];
    }));
  }
  ctx.restore(); ctx.strokeStyle = css('--hair'); ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
  canvas.setAttribute('aria-label', `A still map of the ${polarNorth ? 'Arctic' : 'Antarctic'}. Select Flat maps to examine the areas.`);
}
function drawMarsStage(ctx, width, height, camera = { zoom: 1, x: 0, y: 0 }) {
  const mars = answerData.mars, data = answerData.squares;
  const read = (name, i) => {
    const field = mars.squares.columns[name]; if (!field) return null;
    const types = { int16: ['getInt16', 2], uint16: ['getUint16', 2], uint8: ['getUint8', 1], float32: ['getFloat32', 4] };
    const type = types[field.type]; if (!type) return null;
    const raw = data[type[0]](field.offset + i * type[1], true);
    return raw === field.unknown || !Number.isFinite(raw) ? null : raw / (field.scale || 1);
  };
  const k = Math.min((width - 24) / 360, (height - 24) / 180) * camera.zoom;
  const point = (lat, lon) => [width / 2 + (lon + camera.x) * k, height / 2 + (-lat + camera.y) * k];
  ctx.fillStyle = css('--ocean'); ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = css('--land'); ctx.strokeStyle = css('--coast'); ctx.lineWidth = .7;
  for (const polygon of answerData.world.coordinates || []) {
    ctx.beginPath();
    for (const ring of polygon) {
      ring.forEach(([lon, lat], index) => { const xy = point(lat, lon); if (index) ctx.lineTo(...xy); else ctx.moveTo(...xy); }); ctx.closePath();
    }
    ctx.fill('evenodd'); ctx.stroke();
  }
  ctx.fillStyle = css('--mars');
  const mark = Math.max(1, mars.meta.square_deg * k);
  const rgb = (color) => {
    let hex = color.replace('#', ''); if (hex.length === 3) hex = [...hex].map((ch) => ch + ch).join('');
    return hex.match(/.{2}/g).map((pair) => parseInt(pair, 16));
  };
  const low = rgb(css('--surface')), high = rgb(css('--mars')), range = mars.meta.score_scale;
  for (let i = 0; i < mars.squares.count; i++) {
    const lat = read('lat', i), lon = read('lon', i), score = read(`sites.${S.msite}.${S.mgoal}`, i);
    if (![lat, lon, score].every(Number.isFinite)) continue;
    const [x, y] = point(lat, lon), mix = range?.[1] > range?.[0] ? Math.max(0, Math.min(1, (score - range[0]) / (range[1] - range[0]))) : 0;
    ctx.fillStyle = `rgb(${low.map((v, channel) => Math.round(v + (high[channel] - v) * mix)).join(',')})`;
    ctx.globalAlpha = matches?.mode === 'mars' ? .25 : 1; ctx.fillRect(x - mark / 2, y - mark / 2, mark, mark);
  }
  ctx.globalAlpha = 1;
  if (matches?.mode === 'mars') for (const i of matches.areas) {
    const lat = read('lat', i), lon = read('lon', i);
    if (![lat, lon].every(Number.isFinite)) continue;
    const [x, y] = point(lat, lon); ctx.fillStyle = css('--ui'); ctx.fillRect(x - 1, y - 1, 2, 2);
  }
  let pins = [];
  if (matches?.mode === 'mars') pins = drawMatchPins(ctx, matches.areas.slice(0, 10).flatMap((i, rank) => {
    const lat = read('lat', i), lon = read('lon', i);
    if (![lat, lon].every(Number.isFinite)) return [];
    const [x, y] = point(lat, lon); return [{ x, y, rank: rank + 1 }];
  }));
  else for (const place of (mars.best_places?.[S.msite]?.[S.mgoal] || []).slice(0, 5)) {
    if (![place.lat, place.lon].every(Number.isFinite)) continue;
    ctx.beginPath(); ctx.arc(...point(place.lat, place.lon), 5, 0, Math.PI * 2); ctx.lineWidth = 2; ctx.strokeStyle = css('--mars'); ctx.stroke();
  }
  const selected = mars.squares.ids.indexOf(S.msquare);
  if (selected >= 0) {
    const lat = read('lat', selected), lon = read('lon', selected);
    if ([lat, lon].every(Number.isFinite)) {
      ctx.beginPath(); ctx.arc(...point(lat, lon), 14, 0, Math.PI * 2);
      ctx.strokeStyle = css('--ink'); ctx.lineWidth = 2; ctx.stroke();
    }
  }
  return pins;
}
// The Mars module keeps its camera private. Its result view has a separate canvas
// and camera, so normal map controls and the module's original view remain intact.
let marsMatchMap = null;
function refreshMarsMatches() {
  const native = $('mars-root')?.querySelector('canvas.mars-map');
  if (!native || !answerData.squares || !answerData.world) return;
  if (!marsMatchMap || marsMatchMap.native !== native) {
    marsMatchMap?.observer.disconnect();
    const canvas = document.createElement('canvas'), note = document.createElement('p');
    canvas.className = 'mars-match-map'; canvas.tabIndex = 0; canvas.setAttribute('role', 'application');
    canvas.setAttribute('aria-label', 'Experiment matches on Earth. Use arrows to move, plus and minus to zoom, and Enter to open a square.');
    note.className = 'caption mars-match-note';
    note.textContent = 'Rings and numbers show the first 10 matches. Bright points show the other matches. ' + DRAWN;
    native.parentElement.append(canvas); native.parentElement.after(note);
    const map = marsMatchMap = { native, canvas, note, camera: { zoom: 1, x: 0, y: 0 }, active: false, drag: null, index: 0, pointers: new Map() };
    const zoom = (factor) => { map.camera.zoom = Math.max(1, Math.min(28, map.camera.zoom * factor)); refreshMarsMatches(); };
    const pick = (delta, open = false) => {
      const rows = matches?.mode === 'mars' ? matches.areas : [];
      if (!rows.length) return;
      map.index = (map.index + delta + rows.length) % rows.length;
      const id = answerData.mars.squares.ids[rows[map.index]];
      set({ msquare: id, ...(open ? { go: 'mars-square', only: null } : {}) });
      if (!open) announce(`Match ${map.index + 1}: ${id}. Press Enter to open the square.`);
    };
    canvas.addEventListener('keydown', (event) => {
      const move = 20 / map.camera.zoom;
      const keys = {
        ArrowLeft: () => { map.camera.x += move; }, ArrowRight: () => { map.camera.x -= move; },
        ArrowUp: () => { map.camera.y += move; }, ArrowDown: () => { map.camera.y -= move; },
        '+': () => zoom(1.5), '=': () => zoom(1.5), '-': () => zoom(1 / 1.5),
        Home: () => { map.camera = { zoom: 1, x: 0, y: 0 }; },
        PageDown: () => pick(1), PageUp: () => pick(-1), Enter: () => pick(0, true),
      };
      if (keys[event.key]) { event.preventDefault(); keys[event.key](); refreshMarsMatches(); }
    });
    canvas.addEventListener('wheel', (event) => { event.preventDefault(); zoom(Math.exp(-event.deltaY * .002)); }, { passive: false });
    const pinchDistance = () => { const [a, b] = [...map.pointers.values()]; return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0; };
    canvas.addEventListener('pointerdown', (event) => {
      canvas.focus({ preventScroll: true }); map.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      map.drag = { x: event.clientX, y: event.clientY, moved: map.pointers.size > 1 };
      map.pinch = pinchDistance(); canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!map.drag) return;
      map.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (map.pointers.size > 1) {
        const distance = pinchDistance(); if (map.pinch && distance) zoom(distance / map.pinch);
        map.pinch = distance; map.drag.moved = true; return;
      }
      const scale = Math.min((canvas.clientWidth - 24) / 360, (canvas.clientHeight - 24) / 180) * map.camera.zoom;
      const dx = event.clientX - map.drag.x, dy = event.clientY - map.drag.y;
      map.drag.moved ||= Math.abs(dx) + Math.abs(dy) > 3;
      map.camera.x += dx / scale; map.camera.y += dy / scale;
      map.drag.x = event.clientX; map.drag.y = event.clientY; refreshMarsMatches();
    });
    canvas.addEventListener('pointerup', (event) => {
      const gesture = map.drag; map.drag = null;
      map.pointers.delete(event.pointerId);
      if (!gesture || gesture.moved || map.pointers.size || !matches?.areas.length) return;
      const box = canvas.getBoundingClientRect(), scale = Math.min((box.width - 24) / 360, (box.height - 24) / 180) * map.camera.zoom;
      const pin = map.hitPoints?.find((p) => Math.hypot(event.clientX - box.left - p.x, event.clientY - box.top - p.y) <= 12);
      if (pin) { map.index = pin.rank - 1; pick(0, true); return; }
      const view = answerData.squares, fields = answerData.mars.squares.columns;
      let best = -1, distance = 20 ** 2;
      matches.areas.forEach((i, index) => {
        const lat = view.getInt16(fields.lat.offset + i * 2, true) / fields.lat.scale, lon = view.getInt16(fields.lon.offset + i * 2, true) / fields.lon.scale;
        const x = box.width / 2 + (lon + map.camera.x) * scale, y = box.height / 2 + (-lat + map.camera.y) * scale;
        const d = (event.clientX - box.left - x) ** 2 + (event.clientY - box.top - y) ** 2;
        if (d < distance) { distance = d; best = index; }
      });
      if (best >= 0) { map.index = best; pick(0, true); }
    });
    canvas.addEventListener('pointercancel', (event) => { map.drag = null; map.pointers.delete(event.pointerId); });
    $('mars-root').addEventListener('click', (event) => {
      const button = event.target.closest('[data-map]'); if (!button || !map.active) return;
      event.preventDefault(); event.stopImmediatePropagation();
      const action = button.dataset.map;
      if (action === 'in' || action === 'out') zoom(action === 'in' ? 1.5 : 1 / 1.5);
      if (action === 'reset') { map.camera = { zoom: 1, x: 0, y: 0 }; refreshMarsMatches(); }
      if (action === 'previous' || action === 'next') pick(action === 'previous' ? -1 : 1);
      if (action === 'open') pick(0, true);
    }, true);
    map.observer = new ResizeObserver(() => refreshMarsMatches()); map.observer.observe(native);
  }
  const map = marsMatchMap, active = matches?.mode === 'mars' && S.dest === 'mars';
  if (active && !map.active) { map.camera = { zoom: 1, x: 0, y: 0 }; map.index = 0; }
  map.active = active; map.canvas.hidden = !active; map.note.hidden = !active;
  const legend = native.closest('figure')?.querySelector('.mars-legend'); if (legend) legend.hidden = active;
  native.style.visibility = active ? 'hidden' : '';
  native.tabIndex = active ? -1 : 0; native.setAttribute('aria-hidden', String(active));
  if (!active) return;
  const count = Math.min(10, matches.areas.length);
  map.note.textContent = (count ? `Rings and numbers show the first ${count} ${count === 1 ? 'match' : 'matches'}. Bright points show the other matches. ` : 'No squares match these criteria. ') + DRAWN;
  map.index = Math.max(0, matches.areas.indexOf(answerData.mars.squares.ids.indexOf(S.msquare)));
  const box = native.getBoundingClientRect(); if (!box.width || !box.height) return;
  map.camera.x = Math.max(-180, Math.min(180, map.camera.x)); map.camera.y = Math.max(-90, Math.min(90, map.camera.y));
  const ratio = Math.min(devicePixelRatio || 1, 2);
  map.canvas.width = Math.round(box.width * ratio); map.canvas.height = Math.round(box.height * ratio);
  const ctx = map.canvas.getContext('2d'); ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  map.hitPoints = drawMarsStage(ctx, box.width, box.height, map.camera);
}
async function runAction(name) {
  if (!actions.has(name)) await loadModule('tools');
  try {
    if (actions.has(name)) await actions.get(name)();
    else {
      const button = [...extensions.buttons].find(([id]) => id.includes(name))?.[1];
      if (button) button.click(); else { await goToSection('tools'); announce('Open the Tools section for this action.'); }
    }
  } catch { announce('This action is unavailable. Open Tools to continue.'); }
}
function wireShell() {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('button, a'); if (!button || !D.ready) return;
    if (button.dataset.destinationOpen) {
      const host = $(button.dataset.destinationOpen);
      if (button.getAttribute('aria-expanded') === 'true') closeDestinations(); else openDestination(host);
    }
    else if (button.hasAttribute('data-destination-close')) closeDestinations(true);
    else if (button.dataset.tab2) { set({ tab2: button.dataset.tab2 }); }
    else if (button.dataset.planTab) { planTab = button.dataset.planTab; renderPageTabs(); loadModule(planTab === 'tools' ? 'tools' : 'planner'); }
    else if (button.dataset.destination) { closeDestinations(true); set({ dest: button.dataset.destination, ...(button.dataset.pickTarget ? { target: button.dataset.pickTarget } : {}), ...(button.dataset.pickMsite ? { msite: button.dataset.pickMsite, msquare: '' } : {}) }); }
    else if (button.dataset.mgoal) set({ mgoal: button.dataset.mgoal, msquare: '' });
    else if (button.dataset.action) runAction(button.dataset.action);
    else if (button.id === 'theme-toggle') set({ theme: isDark() ? 'light' : 'dark' });
    else if (button.dataset.stage) { set({ stage: button.dataset.stage }); if (S.stage === 'flat') goToSection(S.dest === 'mars' ? 'mars-map' : 'map'); }
    else if (button.dataset.rail || button.dataset.next) {
      event.preventDefault(); const go = button.dataset.rail || button.dataset.next;
      const square = go === 'mars-square' && !S.msquare ? answerData.mars?.best_places?.[S.msite]?.[S.mgoal]?.[0]?.id : null;
      set({ only: null, go, ...(button.id === 'results-bar-show' ? { stage: 'globe' } : {}), ...(square ? { msquare: square } : {}) });
    }
    else if (button.dataset.deep) { event.preventDefault(); const root = sectionFor(button.dataset.deep); if (root) { revealSection(root); set({ only: null, go: button.dataset.deep }); } }
    else if (button.hasAttribute('data-open-current')) { const i = D.idx.get(S.place) ?? answerLunarRows().find((row) => validArea(row.i))?.i; if (validArea(i)) openPlace(i, true); }
    else if (button.hash && !button.hash.includes('=')) {
      const root = $(button.hash.slice(1)); if (root) { event.preventDefault(); goToSection(root.id); }
    }
  });
  document.addEventListener('pointerdown', (event) => { if (!event.target.closest('.destination-control')) closeDestinations(); });
  document.addEventListener('focusin', (event) => { if (!event.target.closest('.destination-control')) closeDestinations(); });
  document.addEventListener('input', (event) => {
    if (event.target.matches('.destination-search')) filterDestinations(event.target.closest('.destination-control'));
  });
  const positionOpenDestination = () => document.querySelectorAll('.destination-menu:not([hidden])').forEach((menu) => positionDestinationMenu(menu.parentElement));
  window.addEventListener('resize', positionOpenDestination);
  document.addEventListener('scroll', (event) => { if (!event.target.closest?.('.destination-menu')) positionOpenDestination(); }, true);
  document.addEventListener('keydown', (event) => {
    const host = event.target.closest('.destination-control');
    if (host) {
      const menu = host.querySelector('.destination-menu');
      if (!menu) return;
      if (event.key === 'Escape' && !menu.hidden) { event.preventDefault(); event.stopPropagation(); closeDestinations(true); return; }
      const input = event.target.matches('.destination-search');
      const options = [...host.querySelectorAll('[role=option]:not([hidden])')];
      if (event.key === 'Enter' && input && !menu.hidden) {
        event.preventDefault();
        const selected = !event.target.value.trim() && options.find((option) => option.getAttribute('aria-selected') === 'true');
        (selected || options[0])?.click(); return;
      }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) && !(input && ['Home', 'End'].includes(event.key))) {
        event.preventDefault();
        if (menu.hidden) { openDestination(host); return; }
        const at = options.indexOf(document.activeElement), selected = options.findIndex((option) => option.getAttribute('aria-selected') === 'true');
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : at < 0
          ? (selected >= 0 ? selected : event.key === 'ArrowUp' ? options.length - 1 : 0)
          : (at + (event.key === 'ArrowUp' ? -1 : 1) + options.length) % options.length;
        options[next]?.focus({ preventScroll: true }); scrollDestinationIntoView(options[next]); return;
      }
      if (event.key === 'Tab' && !menu.hidden && matchMedia('(max-width: 760px)').matches) {
        const search = host.querySelector('.destination-search'), close = host.querySelector('.destination-close');
        if (event.shiftKey && event.target === search) { event.preventDefault(); close.focus({ preventScroll: true }); }
        else if (!event.shiftKey && (event.target === close || event.target.matches('[role=option]'))) { event.preventDefault(); search.focus({ preventScroll: true }); }
        return;
      }
    }
    const tab = event.target.closest('.tabs [role=tab]');
    if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...tab.closest('.tabs').querySelectorAll('[role=tab]')], at = tabs.indexOf(tab);
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (at + (event.key === 'ArrowLeft' ? -1 : 1) + tabs.length) % tabs.length;
    const next = tabs[index], id = next.id; next.click(); ($(id) || next).focus({ preventScroll: true });
  });
  document.addEventListener('mars:ready', () => {
    const pending = pendingMarsAnchor; pendingMarsAnchor = null;
    keepModuleNext('mars', $('mars-root'));
    refreshMarsMatches();
    if (pending && pending.generation === navigationGeneration && S.dest === 'mars') goToSection(pending.id);
    else holdGo();
  });
  $('drawer-backdrop')?.addEventListener('click', closePlace);
  let railFrame = 0;
  window.addEventListener('scroll', () => { if (!railFrame) railFrame = requestAnimationFrame(() => { railFrame = 0; if (D.ready) updateRail(); }); }, { passive: true });
  window.addEventListener('resize', updateResultsBar);
  if (window.ResizeObserver) {
    const observer = new ResizeObserver(updateResultsBar);
    for (const id of ['ask-root', 'ask-words', 'places-section']) if ($(id)) observer.observe($(id));
  }
  document.addEventListener('focusin', keepExperimentFocusVisible);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab' || $('card').hidden || S.moon) return;
    const all = [...$('card').querySelectorAll('button, a[href], input, select, textarea, summary, [tabindex="0"]')].filter((el) => {
      if (!el.getClientRects().length || el.disabled || getComputedStyle(el).visibility === 'hidden') return false;
      for (let parent = el.parentElement; parent && parent !== $('card'); parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS' && !parent.open && !parent.querySelector(':scope > summary')?.contains(el)) return false;
      }
      return true;
    });
    const first = all[0], last = all.at(-1);
    if (event.shiftKey && (document.activeElement === first || document.activeElement === $('card'))) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
}
function drawerVisible(show) {
  const wasOpen = document.body.classList.contains('drawer-open');
  document.body.classList.toggle('drawer-open', show);
  updateResultsBar();
  if ($('drawer-backdrop')) $('drawer-backdrop').hidden = !show;
  document.querySelectorAll('main, header, footer, #bar').forEach((node) => { if (!node.contains($('card'))) node.inert = show; });
  if (show && !wasOpen) requestAnimationFrame(() => $('card-close')?.focus({ preventScroll: true }));
}

// ---------- everything ----------
let playTimer = 0;
function renderAll(opts = {}) {
  renderTop();
  if (!D.ready) return;
  renderAnswer();
  computeMap();
  renderMapChrome();
  drawMap();
  renderCard();
  renderTabs();
  renderMoon();
  renderCannot();
  renderSure();
  renderShell();
}
function wire() {
  wireShell();
  document.querySelectorAll('[data-answer-toggle]').forEach((button) => button.addEventListener('click', () => {
    const expanded = $('answer-' + button.dataset.answerToggle).classList.toggle('expanded');
    button.setAttribute('aria-expanded', String(expanded)); button.textContent = expanded ? 'Show less' : 'Show all';
  }));
  $('ctl-bin').addEventListener('input', (e) => set({ period: 'bin', bin: +e.target.value }));
  $('ctl-little').addEventListener('change', (e) => set({ little: e.target.checked }));
  $('ctl-play').addEventListener('click', () => {
    const on = !playTimer;
    $('ctl-play').setAttribute('aria-pressed', String(on)); $('ctl-play').textContent = on ? 'Pause' : 'Play';
    if (on) playTimer = setInterval(() => set({ period: 'bin', bin: (S.bin + 1) % NB }), reduced() ? 1800 : 800);
    else { clearInterval(playTimer); playTimer = 0; }
  });
  window.addEventListener('hashchange', () => { if (!D.meta) return; readHash(); renderAll({ fromHash: true }); notifyState(); if (S.only) prepareSection(S.only); if (S.go) goToSection(S.go); });
  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => {
    if (D.meta) { renderWhere(); renderWhen(); renderSunPath(); }
    if (D.ready) { renderTabs(); renderCard(); }
  }, 150); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && S.place && !S.moon) closePlace(); });
  // the lunar region card: its own button, a click beside it, or Escape (the dialog's own "close") shuts it
  const moon = $('moon');
  if (moon) {
    $('moon-close').addEventListener('click', closeMoon);
    moon.addEventListener('click', (e) => { if (e.target === moon) closeMoon(); });
    moon.addEventListener('close', () => { if (S.moon) closeMoon(); });
  }
  wireTake();
  if (window.ResizeObserver) {
    const measure = () => {
      const root = document.documentElement;
      const top = ($('topbar')?.offsetHeight || 0) + 'px', bar = ($('bar')?.offsetHeight || 0) + 'px';
      if (root.style.getPropertyValue('--topbar-h') !== top) root.style.setProperty('--topbar-h', top);
      if (root.style.getPropertyValue('--bar-h') !== bar) root.style.setProperty('--bar-h', bar);
    };
    const observer = new ResizeObserver(measure);
    for (const id of ['topbar', 'bar']) if ($(id)) observer.observe($(id));
    measure();
  }
}
wire();
start();
