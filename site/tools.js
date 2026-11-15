// Tools for LuniMartian Atlas. All data enters through the page's module API.
const DRAWN = 'Drawn by code from open data; the code was written with AI assistance.';
const NO_MODEL = 'unknown: NASA has no 5 m terrain model of this region';
const valid = (x) => typeof x === 'number' && Number.isFinite(x);
const esc = (x) => String(x ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
const fold = (x) => String(x ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (tag === 'button') node.classList.add('btn');
  if (tag === 'details') node.classList.add('fold');
  if (['tl-site', 'tl-count'].includes(cls)) node.classList.add('card');
  if (cls === 'tl-eyebrow') node.classList.add('eyebrow');
  if (text != null) node.textContent = text;
  return node;
};
// Stored prose stays unchanged; its source keys are listed in the handoff report.
const prose = text => String(text ?? '');

export async function mount(root, api) {
  const life = new AbortController(), cleanups = [], cache = new Map();
  let destroyed = false, index, pageMeta, famous, winter, airfields, access, reachKm, lastTarget;
  let tour = null, tourStrip = null, searchData = null, exportURL = null, linkTimer = 0;
  const number = (x, digits = 0) => valid(x) ? api.fmtNumber(x, digits) : 'unknown';
  const hours = (x) => valid(x) ? api.fmtHours(x) : 'unknown';
  const target = (id = api.getState().target) => api.targets.find((t) => t.id === id);
  const noModel = (id = api.getState().target) => (target(id)?.has_model ?? pageMeta?.targets?.find(t => t.id === id)?.has_model) === false;
  const modelNote = id => `Lunar terrain comparison: cannot tell. ${NO_MODEL}.`;
  const coords = (a) => valid(a.lat) && valid(a.lon) ? `${number(Math.abs(a.lat), 2)}° ${a.lat < 0 ? 'S' : 'N'}, ${number(Math.abs(a.lon), 2)}° ${a.lon < 0 ? 'W' : 'E'}` : 'coordinates unknown';
  const nameOf = (a) => typeof a.named === 'string' && a.named ? a.named : a.region || 'Area';
  const on = (node, event, fn, options = {}) => node.addEventListener(event, fn, { ...options, signal: life.signal });
  const own = (result) => { if (typeof result === 'function') cleanups.push(result); };
  const json = (name) => {
    if (!cache.has(name)) cache.set(name, Promise.resolve().then(() => api.loadJSON(name)).catch(() => null));
    return cache.get(name);
  };
  const file = (name) => index?.files?.[name] ? json(name) : Promise.resolve(null);
  const button = (text, fn) => { const b = el('button', 'tl-button', text); b.type = 'button'; on(b, 'click', fn); return b; };
  const compactList = (list, limit = 5) => {
    const extra = [...list.children].slice(limit);
    if (!extra.length) return null;
    extra.forEach(row => { row.hidden = true; });
    const toggle = button('Show all', () => {
      const expanded = toggle.getAttribute('aria-expanded') !== 'true';
      extra.forEach(row => { row.hidden = !expanded; });
      toggle.setAttribute('aria-expanded', String(expanded));
      toggle.textContent = expanded ? 'Show less' : 'Show all';
    });
    toggle.setAttribute('aria-expanded', 'false');
    return toggle;
  };
  const explanation = (title, text) => {
    const node = el('details', 'tl-inner-fold');
    node.append(el('summary', '', title), el('p', 'tl-note', text));
    return node;
  };
  const toolsButton = (id, label, fn) => own(api.addToolsButton(id, label, () => { if (!destroyed) fn(); }));
  const shell = el('div', 'tl-module');
  root.replaceChildren(shell);
  const intro = el('header', 'tl-heading section-head');
  const headingText = el('div');
  headingText.append(el('p', 'tl-eyebrow', 'Tools'), el('h2', '', 'Where do you want to go?'),
    el('p', 'tl-finding finding', `The page has ${number(api.areaCount)} areas for ${number(api.targets.length)} lunar regions.`));
  intro.append(el('span', 'step-number', '5'), headingText);
  shell.append(intro);
  const terrainNote = el('p', 'tl-note tl-model-note'); terrainNote.hidden = true; shell.append(terrainNote);
  function panel(id, title, open = false) {
    const d = el('details', 'tl-panel'); d.id = `tl-${id}`; d.open = open;
    const s = el('summary', '', title), body = el('div', 'tl-panel-body');
    d.append(s, body); shell.append(d); return { node: d, body, summary: s };
  }
  function show(p, focus = p.summary) {
    const state = api.getState();
    if (state.place || state.moon) api.setState({ place: null, moon: null });
    p.node.open = true; p.node.scrollIntoView({ block: 'start', behavior: 'instant' });
    focus.focus({ preventScroll: true });
  }
  function moveMap(lat, lon) {
    api.setState({ place: null, moon: null, only: null, go: 'map' });
    api.flyTo(lat, lon);
  }
  const searchPanel = panel('search', 'Find a place');
  const basisPanel = panel('basis', 'What supports the figures?');
  const glossaryPanel = panel('glossary', 'What do these words mean?');
  const famousPanel = panel('famous', 'Why not the famous sites?');
  const winterPanel = panel('winter', 'Winter on small bare patches');
  const takePanel = panel('take', 'Take the areas away');
  const printCard = el('article', 'tl-print-card'); shell.append(printCard);
  [index, pageMeta] = await Promise.all([json('tools.json'), json('meta.json')]);
  if (destroyed) return { destroy };
  if (!index) {
    shell.append(el('p', 'tl-note', 'The Tools data index is missing.'));
    return { destroy };
  }

  // Search keeps DOM focus in its combobox while a list option is active.
  const label = el('label', 'tl-label', 'Place, airfield or lunar region'); label.htmlFor = 'tl-place-input';
  const input = el('input', 'tl-input'); input.id = 'tl-place-input'; input.type = 'search'; input.autocomplete = 'off';
  input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false'); input.setAttribute('aria-controls', 'tl-search-results');
  const results = el('ul', 'tl-results'); results.id = 'tl-search-results'; results.setAttribute('role', 'listbox'); results.hidden = true;
  const searchStatus = el('p', 'tl-note', 'Search the names stored with this page.'); searchStatus.id = 'tl-search-help';
  input.setAttribute('aria-describedby', searchStatus.id);
  const moreResults = button('Show all', () => {
    const expanded = moreResults.getAttribute('aria-expanded') !== 'true';
    [...results.children].forEach((row, i) => { row.hidden = !expanded && i >= 5; });
    moreResults.setAttribute('aria-expanded', String(expanded));
    moreResults.textContent = expanded ? 'Show less' : 'Show all';
    if (!expanded && active >= 5) selectActive(0);
  });
  moreResults.hidden = true; moreResults.setAttribute('aria-expanded', 'false');
  searchPanel.body.append(label, input, results, moreResults, searchStatus);
  let matches = [], active = -1, searchRequest = 0;
  function closeResults() { results.hidden = true; moreResults.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); active = -1; }
  function selectActive(k) {
    if (!matches.length) return;
    const count = moreResults.getAttribute('aria-expanded') === 'true' ? matches.length : Math.min(5, matches.length);
    active = (k + count) % count;
    [...results.children].forEach((item, i) => item.setAttribute('aria-selected', String(i === active)));
    input.setAttribute('aria-activedescendant', results.children[active].id);
    results.children[active].scrollIntoView({ block: 'nearest' });
  }
  function choose(row) {
    const kind = searchData.kinds[row.kind], state = Object.fromEntries(new URLSearchParams(row.view || ''));
    closeResults(); input.value = row.name;
    const distance = valid(row.km) && row.km > 0 ? ` The nearest area is ${number(row.km, 1)} km from this place.` : '';
    searchStatus.textContent = row.name + '.' + distance; api.announce(searchStatus.textContent);
    if (kind === 'lunar region') api.setState(state);
    else if (kind === 'lower-latitude site') show(famousPanel);
    else if (kind !== 'airfield' && kind !== 'Earth region' && row.area && api.areaIndex(row.area) >= 0) api.openPlace(row.area);
    else if (valid(row.lat) && valid(row.lon)) moveMap(row.lat, row.lon);
  }
  async function search() {
    const request = ++searchRequest, query = fold(input.value).trim();
    searchData ||= await file('search.json');
    if (destroyed || request !== searchRequest) return;
    results.replaceChildren(); moreResults.hidden = true; moreResults.setAttribute('aria-expanded', 'false'); moreResults.textContent = 'Show all'; matches = []; active = -1; input.removeAttribute('aria-activedescendant');
    if (!searchData) { searchStatus.textContent = 'The place-name index is missing.'; closeResults(); return; }
    if (!query) { closeResults(); searchStatus.textContent = 'Search the names stored with this page.'; return; }
    const rows = searchData.entries.map((r) => Object.fromEntries(searchData.columns.map((c, i) => [c, r[i]])));
    matches = rows.filter((r) => query.split(/\s+/).every((word) => fold(`${r.key} ${r.name} ${r.ascii || ''}`).includes(word)));
    matches.sort((a, b) => Number(fold(b.name).startsWith(query)) - Number(fold(a.name).startsWith(query)));
    matches.forEach((row, i) => {
      const option = el('li', 'tl-option'); option.id = `tl-option-${i}`; option.setAttribute('role', 'option'); option.setAttribute('aria-selected', 'false');
      option.hidden = i >= 5;
      option.append(el('strong', '', row.name), el('small', '', searchData.kinds[row.kind]));
      if (valid(row.km) && row.km > 0) option.append(el('small', '', `Nearest area: ${number(row.km, 1)} km away.`));
      on(option, 'mousedown', (e) => e.preventDefault()); on(option, 'click', () => choose(row)); results.append(option);
    });
    searchStatus.textContent = `${number(matches.length)} ${matches.length === 1 ? 'result' : 'results'}. Use the arrow keys to select a result. Then press Enter.`;
    api.announce(searchStatus.textContent); moreResults.hidden = matches.length <= 5; results.hidden = !matches.length; input.setAttribute('aria-expanded', String(!!matches.length));
  }
  on(input, 'input', search); on(input, 'focus', () => { if (input.value) search(); });
  on(input, 'keydown', (e) => {
    if (e.key === 'Escape') { ++searchRequest; closeResults(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); if (matches.length) { results.hidden = false; moreResults.hidden = matches.length <= 5; input.setAttribute('aria-expanded', 'true'); selectActive(active < 0 ? (e.key === 'ArrowDown' ? 0 : -1) : active + (e.key === 'ArrowDown' ? 1 : -1)); } }
    else if (e.key === 'Enter' && active >= 0 && !results.hidden) { e.preventDefault(); choose(matches[active]); }
  });
  on(searchPanel.node, 'focusout', (e) => { if (!searchPanel.node.contains(e.relatedTarget)) closeResults(); });
  const openSearch = () => {
    if (destroyed) return;
    api.setState({ dest: 'moon', only: null, go: 'tools', place: null, moon: null });
    show(searchPanel, input);
    file('search.json').then((data) => { if (!destroyed) searchData = data; });
  };
  toolsButton('search', 'Find a place', openSearch);
  if (typeof api.registerAction === 'function') own(api.registerAction('search', openSearch));

  async function loadBasis() {
    if (basisPanel.body.childElementCount) return;
    const data = await file('basis.json'); if (destroyed || basisPanel.body.childElementCount) return;
    if (!data) { basisPanel.body.append(el('p', 'tl-note', 'The basis notes are missing.')); return; }
    basisPanel.body.append(el('p', 'tl-basis-line', prose(data.line)));
    const checks = data.check_figures || {}, checkParts = [];
    if (valid(checks.recount_largest_difference_h_a_year)) checkParts.push(`An independent recount differs by ${number(checks.recount_largest_difference_h_a_year, 3)} hours a year or less.`);
    if (valid(checks.horizons_median_abs_difference_pct)) checkParts.push(`JPL Horizons differs by a median of ${number(checks.horizons_median_abs_difference_pct, 3)}%.`);
    if (checkParts.length) basisPanel.body.append(el('p', 'tl-note', checkParts.join(' ')));
    const list = el('dl', 'tl-definitions');
    for (const step of data.steps || []) list.append(el('dt', '', step.name), el('dd', '', prose(step.line)));
    basisPanel.body.append(list);
    const link = el('a', 'tl-link', data.link?.text || 'How accurate are the results?'); link.href = `#${data.link?.fragment || 'go=sure'}`;
    on(link, 'click', (e) => { e.preventDefault(); api.setState(Object.fromEntries(new URLSearchParams(data.link?.fragment || 'go=sure'))); });
    basisPanel.body.append(link);
    const assumptions = el('details', 'tl-inner-fold'); assumptions.append(el('summary', '', 'Assumptions'));
    const ul = el('ul', 'tl-cautions'); for (const item of data.assumptions || []) ul.append(el('li', '', prose(item.text)));
    assumptions.append(ul); basisPanel.body.append(assumptions);
  }
  on(basisPanel.node, 'toggle', () => { if (basisPanel.node.open) loadBasis(); });
  toolsButton('basis', 'What supports the figures?', () => { show(basisPanel); loadBasis(); });
  async function loadGlossary() {
    if (glossaryPanel.body.childElementCount) return;
    const data = await file('glossary.json'); if (destroyed || glossaryPanel.body.childElementCount) return;
    const dl = el('dl', 'tl-definitions');
    for (const item of data?.terms || []) dl.append(el('dt', '', item.term), el('dd', '', prose(item.text)));
    glossaryPanel.body.append(data ? dl : el('p', 'tl-note', 'The glossary is missing.'));
    const more = compactList(dl, 10); if (more) glossaryPanel.body.append(more);
  }
  on(glossaryPanel.node, 'toggle', () => { if (glossaryPanel.node.open) loadGlossary(); });
  toolsButton('glossary', 'Glossary', () => { show(glossaryPanel); loadGlossary(); });

  function drawFamous() {
    famousPanel.body.replaceChildren();
    if (!famous) { famousPanel.body.append(el('p', 'tl-note', 'The famous-site figures are missing.')); return; }
    const tid = api.getState().target;
    famousPanel.body.append(el('p', 'tl-context', `These figures are for the lunar region ${target()?.name || tid}.`), el('p', 'tl-note', prose(famous.hours_what)));
    const groups = [
      ['Lower latitudes', famous.sites.filter((s) => s.basis === 'latitude')],
      ['Arctic analog sites', famous.sites.filter((s) => s.basis !== 'latitude' && s.hemisphere === 'N')],
      ['Antarctic analog sites', famous.sites.filter((s) => s.basis !== 'latitude' && s.hemisphere === 'S')],
    ];
    for (const [title, sites] of groups) {
      if (!sites.length) continue;
      const group = el('details', 'tl-site-group'); group.open = title === 'Lower latitudes';
      group.append(el('summary', '', `${title} · ${number(sites.length)}`));
      if (title === 'Lower latitudes' && sites.every((s) => s.targets[tid]?.has_a_2h_spell === false)) group.append(el('p', 'tl-note', 'At these latitudes, no spell of low Sun for this lunar region lasts 2 hours.'));
      const list = el('div', 'tl-site-grid');
      for (const site of sites) {
        const values = site.targets?.[tid]; if (!values) continue;
        const item = el('article', 'tl-site'), titleNode = el('h3');
        titleNode.append(site.area && api.areaIndex(site.area) >= 0 ? button(site.name, () => api.openPlace(site.area)) : el('span', '', site.name));
        item.append(titleNode);
        const labels = site.hemisphere === 'S' ? famous.step_labels_south : famous.step_labels;
        if (labels?.[values.step]) item.append(el('p', 'tl-verdict', labels[values.step]));
        const dl = el('dl', 'tl-values');
        for (const [key, labelText] of [['sun', 'Sun only'], ['snow', site.hemisphere === 'S' ? 'Rock season' : 'After snow'], ['hills', 'After terrain'], ['cloud', 'Typical cloud']]) {
          if (valid(values.hours?.[key])) dl.append(el('dt', '', labelText), el('dd', '', hours(values.hours[key])));
        }
        if (valid(values.hours_in_spells_of_2h)) dl.append(el('dt', '', 'In spells of 2 hours'), el('dd', '', hours(values.hours_in_spells_of_2h)));
        if (dl.childElementCount) item.append(dl);
        item.append(el('p', 'tl-reason', prose(values.sentence)), el('p', 'tl-caption', prose(site.basis_text)));
        list.append(item);
      }
      group.append(list);
      const more = compactList(list); if (more) group.append(more);
      famousPanel.body.append(group);
    }
    famousPanel.body.append(explanation('The rules', prose(famous.rule)), el('p', 'tl-caption', DRAWN));
  }

  async function loadWinter() {
    winter ||= await file('winter_leads.json'); if (destroyed) return; drawWinter();
  }
  function drawWinter() {
    winterPanel.body.replaceChildren();
    if (!winter) { winterPanel.body.append(el('p', 'tl-note', 'The winter areas are missing.')); return; }
    const data = winter.targets.find((t) => t.id === api.getState().target); if (!data) return;
    winterPanel.body.append(el('p', 'tl-context', `These areas are for the lunar region ${data.name}.`), el('p', 'tl-note', prose(winter.what)));
    const counts = el('div', 'tl-counts');
    for (const threshold of winter.count_thresholds_h || []) {
      const before = data.counts_by_region?.[threshold] || {}, after = data.counts_by_region_after_terrain?.[threshold] || {};
      const regions = [...new Set([...Object.keys(before), ...Object.keys(after)])];
      if (!regions.length) continue;
      const block = el('div', 'tl-count'); block.append(el('h3', '', `${number(threshold)} winter hours or more`));
      for (const region of regions) {
        const parts = [region];
        if (valid(before[region])) parts.push(`${number(before[region])} ${before[region] === 1 ? 'area' : 'areas'} before terrain`);
        if (valid(after[region])) parts.push(`${number(after[region])} ${after[region] === 1 ? 'area' : 'areas'} after terrain`);
        block.append(el('p', 'tl-note', parts.join(' · ')));
      }
      const more = compactList(block, 6); if (more) block.append(more);
      counts.append(block);
    }
    winterPanel.body.append(counts);
    if (!data.leads.length) winterPanel.body.append(el('p', 'tl-note', 'No small bare patches meet the stored winter rule for this lunar region.'));
    const list = el('ol', 'tl-winter-list');
    for (const lead of data.leads) {
      const item = el('li', 'tl-winter-item');
      item.append(button(`${lead.region} · ${coords(lead)}`, () => moveMap(lead.lat, lead.lon)));
      const parts = [];
      for (const [key, labelText] of [['winter_hours_flat', 'Sun only'], ['winter_hours_snow_free', 'After snow'], ['winter_hours_after_terrain', 'After terrain']]) if (valid(lead[key])) parts.push(`${labelText}: ${hours(lead[key])}`);
      item.append(el('p', '', parts.join(' · ')));
      if (valid(lead.bare_km2)) item.append(el('p', 'tl-note', `Bare ground: ${number(lead.bare_km2, 2)} km².`));
      if (valid(lead.snow_land_pixels) && valid(lead.snow_block_pixels)) item.append(el('p', 'tl-note', `Snow maps: ${number(lead.snow_land_pixels)} land pixels out of ${number(lead.snow_block_pixels)} nearby pixels.`));
      const dates = (lead.best_ten_day_periods || []).map((b) => api.periods.find((p) => p.index === b.bin)?.label || b.starts).filter(Boolean);
      if (dates.length) item.append(el('p', 'tl-note', `Best ten-day periods: ${dates.join('; ')}.`));
      list.append(item);
    }
    if (data.leads.length) { const all = el('details', 'tl-inner-fold'); all.open = true; all.append(el('summary', '', `${number(data.leads.length)} ${data.leads.length === 1 ? 'small bare patch' : 'small bare patches'}`), list); const more = compactList(list); if (more) all.append(more); winterPanel.body.append(all); }
    const cautions = el('details', 'tl-inner-fold'); cautions.append(el('summary', '', 'Read the limits before you use these areas'));
    const ul = el('ul', 'tl-cautions'); (winter.cautions || []).forEach((s) => ul.append(el('li', '', prose(s))));
    cautions.append(ul); winterPanel.body.append(cautions, el('p', 'tl-caption', DRAWN));
  }
  on(winterPanel.node, 'toggle', () => { if (winterPanel.node.open) loadWinter(); });

  // Access is only usable when its complete area order agrees with the page.
  async function loadAccess() {
    const layout = index.files?.['access.bin']?.layout;
    if (!layout || index.areas?.count !== api.areaCount) return;
    const [names, buffer, cells, plan] = await Promise.all([file('airfields.json'), api.loadBin('access.bin').catch(() => null), json('cells.json'), json('yearplan.json')]);
    if (destroyed || !names || !buffer || !cells || buffer.byteLength !== api.areaCount * layout.columns.length * 2) return;
    if (cells.ids.length !== api.areaCount || !cells.ids.every((id, i) => api.area(i)?.id === id)) return;
    if (index.areas.ids_sha256 && globalThis.crypto?.subtle) {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(cells.ids.join('\n')));
      const hash = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, '0')).join('');
      if (hash !== index.areas.ids_sha256) return;
    }
    if (destroyed) return;
    airfields = names; access = { view: new DataView(buffer), layout }; reachKm = valid(plan?.reach_km) ? plan.reach_km : null;
    own(api.addListNote((i) => destroyed ? null : accessText(i)));
    if (valid(reachKm)) own(api.addListFilter('reachable', `Reachable only · ${number(reachKm)} km or less from an airfield with scheduled flights; in Antarctica, from any listed airfield`, (i) => {
      const data = nearest(i); return destroyed || (!!data && data.km <= reachKm);
    }));
  }
  function nearest(i) {
    if (!access || i < 0 || i >= api.areaCount) return null;
    const south = api.area(i).hemisphere === 'S', columns = access.layout.columns;
    const read = (key) => access.view.getUint16((i * columns.length + columns.indexOf(key)) * 2, true);
    const n = read(south ? 'any_index' : 'scheduled_index'), km = read(south ? 'any_km' : 'scheduled_km');
    if (n === access.layout.unknown || km === access.layout.unknown || !airfields.airfields[n]) return null;
    return { ...airfields.airfields[n], km, south };
  }
  function accessText(i) {
    const a = nearest(i); return a ? `${a.name}: ${number(a.km)} km in a straight line. ${a.south ? 'In Antarctica, this is the nearest listed airfield of any type.' : 'The airfield file lists scheduled flights here. We did not examine the timetable.'} This distance gives no route or permit.` : null;
  }

  // The page owns the state. Modules supply the preset and playback actions.
  // Absolute deadlines include module waits; late work cannot extend a recording.
  const strip = tourStrip = el('aside', 'tl-tour'); strip.hidden = true;
  strip.setAttribute('aria-label', 'Guided tour');
  const tourPosition = el('strong', 'tl-tour-position'), tourCaption = el('p', 'tl-tour-caption');
  const progress = el('progress', 'tl-progress'); progress.setAttribute('aria-label', 'Tour progress');
  const next = button('Next', () => advanceTour()), stop = button('Stop', () => stopTour());
  const tourActions = el('div', 'tl-actions'); tourActions.append(next, stop);
  strip.append(tourPosition, tourCaption, progress, tourActions);
  // Keep the strip outside Tools: its Plan tab can be hidden during the tour.
  (document.getElementById('topbar') || document.body.firstElementChild).after(strip);
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const hook = (id) => document.getElementById(id + '-root')?.tourActions;
  const stripSize = new ResizeObserver(() => {
    if (tour) document.documentElement.style.setProperty('--tl-tour-height', strip.getBoundingClientRect().height + 'px');
  });
  stripSize.observe(strip); own(() => stripSize.disconnect());
  function nodeSelector(node) {
    if (!(node instanceof Element)) return null;
    const path = [];
    while (node) {
      if (node.id) { path.unshift('#' + CSS.escape(node.id)); break; }
      if (node.dataset.cardFold && node.closest('#card')) {
        path.unshift(`#card [data-card-fold="${CSS.escape(node.dataset.cardFold)}"]`); break;
      }
      const siblings = node.parentElement ? [...node.parentElement.children].filter((child) => child.localName === node.localName) : [node];
      path.unshift(`${node.localName}:nth-of-type(${siblings.indexOf(node) + 1})`);
      node = node.parentElement;
    }
    return path.join(' > ');
  }
  const locate = (saved) => saved.node?.isConnected ? saved.node : saved.selector ? document.querySelector(saved.selector) : null;
  const remember = (node) => ({ node, selector: nodeSelector(node) });
  function snapshot() {
    return {
      state: structuredClone(api.getState()), view: api.captureView?.(),
      focus: remember(document.activeElement), scrollX: window.scrollX, scrollY: window.scrollY,
      folds: [...document.querySelectorAll('details')].map((node) => ({ ...remember(node), open: node.open })),
      scrolls: [...document.querySelectorAll('body *')].filter((node) => node.scrollTop || node.scrollLeft ||
        node.matches('.hero-copy,.hero-stage,#card')).map((node) => ({ ...remember(node), top: node.scrollTop, left: node.scrollLeft })),
      modules: ['ask', 'sky', 'globes'].map((id) => ({ id, value: hook(id)?.snapshot?.() })),
      height: document.documentElement.style.getPropertyValue('--tl-tour-height'),
    };
  }
  function stopTour(completed = false) {
    if (!tour) return;
    const saved = tour; tour = null;
    const restoreStarted = performance.now(), restoreTiming = {};
    clearTimeout(saved.timer); clearTimeout(saved.deadline); clearInterval(saved.clock); saved.events.abort();
    hook('sky')?.stop(); strip.hidden = true;
    document.body.classList.add('tl-tour-restoring');
    document.body.classList.remove('tl-touring', 'tl-tour-demo', 'tl-tour-sky');
    document.documentElement.style.setProperty('--tl-tour-height', saved.height);
    strip.dataset.completed = String(completed);
    // Restoration owns navigation; do not let a deferred go scroll after it.
    const added = Object.fromEntries(Object.keys(api.getState()).filter((key) => !(key in saved.state)).map((key) => [key, null]));
    if (api.restoreView && saved.view) api.restoreView(saved.view, { ...added, ...saved.state });
    else api.setState({ ...added, ...saved.state });
    restoreTiming.state = performance.now() - restoreStarted;
    for (const item of saved.modules) if (item.value !== undefined) {
      const before = performance.now();
      hook(item.id)?.restore(item.value);
      restoreTiming[item.id] = performance.now() - before;
    }
    const restoreDOM = (restoreFocus = false) => {
      if (tour || destroyed) return;
      for (const fold of saved.folds) {
        const node = locate(fold); if (node instanceof HTMLDetailsElement) node.open = fold.open;
      }
      for (const item of saved.scrolls) {
        const node = locate(item); if (node) { node.scrollTop = item.top; node.scrollLeft = item.left; }
      }
      if (restoreFocus) locate(saved.focus)?.focus({ preventScroll: true });
      // The shell can reveal a focused board control. Restore the reader's
      // scroll after that focus handler, including its deferred layout pass.
      window.scrollTo({ left: saved.scrollX, top: saved.scrollY, behavior: 'instant' });
    };
    restoreDOM();
    api.announce(completed ? 'The tour ended. The page shows your original view.' : 'The tour stopped. The page shows your original view.');
    // Include restoration and a painted frame in the reported duration.
    requestAnimationFrame(() => {
      restoreDOM();
      requestAnimationFrame(() => {
        restoreDOM(true);
        document.body.classList.remove('tl-tour-restoring');
        const elapsed = performance.now() - saved.started;
        restoreTiming.total = performance.now() - restoreStarted;
        strip.dataset.elapsedMs = elapsed.toFixed(1);
        document.dispatchEvent(new CustomEvent('earth-twin:tour', { detail: { phase: 'stop', mode: saved.mode, completed, elapsed, restoreTiming } }));
      });
    });
  }
  function current(run, step) { return tour === run && run.at === step; }
  async function waitFor(run, step, read) {
    while (current(run, step)) {
      const value = read(); if (value) return value;
      if (!run.manual && performance.now() >= run.stepEnd - 100) return null;
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
    return null;
  }
  function atTop() {
    document.querySelector('.hero-copy')?.scrollTo({ top: 0, behavior: 'instant' });
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }
  function showStage() {
    // The board now precedes Places on every screen size.
    const stage = document.querySelector('#places-section .hero-stage') || document.querySelector('.hero-stage');
    if (stage) stage.scrollIntoView({ block: 'start', behavior: 'instant' });
    else atTop();
  }
  function stageReady() {
    return hook('globes') && !document.querySelector('#globes-root [aria-busy="true"]');
  }
  function frame(patch = {}) {
    api.setState({ dest: 'moon', stage: 'globe', tab2: 'best', place: null, moon: null,
      only: null, go: null, ask: null, filters: '', order: '', little: false, step: 3,
      period: 'year', z: 1, x: 0, y: 0, ...patch });
  }
  function lunarPlace(run) {
    const row = api.answer(run.target).find((item) => api.area(item.area));
    return row ? api.area(row.area) : null;
  }
  async function showDay(run, step) {
    const area = await waitFor(run, step, () => lunarPlace(run));
    if (!area || !current(run, step)) return;
    document.body.classList.add('tl-tour-sky');
    const values = api.periodHours(api.areaIndex(area.id), run.target, 3);
    const best = api.periods.filter((p) => valid(values?.[p.index])).sort((a, b) => values[b.index] - values[a.index])[0];
    api.setState({ dest: 'moon', target: run.target, place: area.id, skyPeriod: best?.index ?? null, skyTime: 0, go: 'sky' });
    const sky = await waitFor(run, step, () => hook('sky'));
    if (!sky || !current(run, step)) return;
    document.getElementById('sky-root')?.scrollIntoView({ block: 'start', behavior: 'instant' });
    if (!run.manual) sky.play();
  }
  async function makeExperiment(run, step) {
    frame({ target: run.target, tab2: 'make' });
    const ask = await waitFor(run, step, () => hook('ask'));
    if (!ask || !current(run, step)) return;
    ask.applyPreset('rover-camera');
    // A preset can include a destination; keep its own data-derived selection.
    run.experiment = structuredClone(api.getState().ask);
    document.getElementById('ask-root')?.scrollIntoView({ block: 'start', behavior: 'instant' });
    // Show the preset on the board before its numbered places. This pause is
    // inside the step's deadline; a slow module never extends the recording.
    if (run.manual) return;
    const showPlacesAt = Math.min(performance.now() + 2000, run.stepEnd - 800);
    await waitFor(run, step, () => performance.now() >= showPlacesAt && stageReady()
      && document.querySelector('#globes-root .gb-has-matches'));
    if (current(run, step)) showStage();
  }
  async function showMars(run, step) {
    const data = await waitFor(run, step, () => run.mars);
    if (!data?.sites?.length || !current(run, step)) return;
    const site = data.sites[0];
    frame({ dest: 'mars', msite: site.id, msquare: '', mgoal: 'full' });
    // Places keeps the squares, their size and "first pass" together.
    await waitFor(run, step, () => document.querySelector('[data-answer-square]') &&
      document.querySelector('#answer-mars-scale')?.textContent.includes('First pass') && stageReady());
    if (current(run, step)) showStage();
  }
  function stepsFor(run) {
    const first = { caption: 'Select a base and set what your experiment needs.', show() { frame(); atTop(); } };
    const lunar = { caption: 'The Earth turns to places with low Sun for this lunar region.', async show(step) {
      frame({ target: run.target }); atTop();
      await waitFor(run, step, () => lunarPlace(run) && stageReady());
      if (current(run, step)) showStage();
    } };
    const day = { caption: 'Watch a day of low Sun at this place.', show: (step) => showDay(run, step) };
    const make = { caption: 'The rover camera preset marks the best places with numbers.', show: (step) => makeExperiment(run, step) };
    const mars = { caption: 'These squares compare Earth with a Mars site in a first pass.', show: (step) => showMars(run, step) };
    if (run.mode === '30') return [first, lunar, day, make, mars];
    return [first, lunar,
      { caption: 'Open a best place to see its light, ground and limits.', async show(step) {
        frame({ target: run.target }); atTop();
        const area = await waitFor(run, step, () => lunarPlace(run));
        if (area && current(run, step)) {
          showStage();
          api.openPlace(area.id);
          if (run.manual) requestAnimationFrame(() => { if (current(run, step)) next.focus({ preventScroll: true }); });
        }
      } }, day, make,
      { caption: 'Compare the destinations for the same experiment.', async show(step) {
        const ask = await waitFor(run, step, () => hook('ask'));
        if (!ask || !current(run, step)) return;
        ask.openDestinations();
        const table = await waitFor(run, step, () => document.querySelector('.ak-destinations table'));
        if (table && current(run, step)) table.closest('details').scrollIntoView({ block: 'center', behavior: 'instant' });
      } }, mars,
      { caption: 'Go deeper to read each factor, its source and its limits.', async show(step) {
        frame({ target: run.target, go: 'factors' });
        const table = await waitFor(run, step, () => document.querySelector('#factors-root .fx-table'));
        if (table && current(run, step)) document.getElementById('factors-root').scrollIntoView({ block: 'start', behavior: 'instant' });
      } },
    ];
  }
  function updateProgress() {
    if (!tour) return;
    progress.max = tour.manual ? tour.steps.length : tour.duration;
    progress.value = tour.manual ? Math.max(0, tour.at + 1) : Math.min(tour.duration, performance.now() - tour.started);
  }
  function advanceTour() {
    const run = tour; if (!run) return;
    clearTimeout(run.timer); hook('sky')?.stop(); document.body.classList.remove('tl-tour-sky');
    run.at = run.manual ? run.at + 1 : Math.max(run.at + 1, Math.floor((performance.now() - run.started) / run.slot));
    if (run.at >= run.steps.length) { stopTour(true); return; }
    const step = run.steps[run.at], at = run.at;
    run.stepEnd = run.started + (at + 1) * run.slot;
    tourPosition.textContent = `${run.mode === '30' ? 'Demo' : 'Tour'} · ${number(at + 1)} of ${number(run.steps.length)}`;
    tourCaption.textContent = step.caption; next.hidden = !run.manual;
    updateProgress(); api.announce(`${tourPosition.textContent}. ${step.caption}`);
    strip.dataset.step = String(at + 1);
    document.dispatchEvent(new CustomEvent('earth-twin:tour', { detail: { phase: 'step', mode: run.mode, step: at + 1 } }));
    // Arm the next deadline before any module work can start.
    if (!run.manual && at + 1 < run.steps.length) run.timer = setTimeout(advanceTour, Math.max(0, run.stepEnd - performance.now()));
    Promise.resolve().then(() => { if (current(run, at)) return step.show(at); }).catch(() => { /* Missing optional data does not stop the tour clock. */ });
  }
  function startTour(mode = '60') {
    if (destroyed || tour) return;
    clearTimeout(linkTimer);
    const saved = snapshot(), duration = mode === '30' ? 30000 : 60000;
    const other = api.targets.find((t) => t.id === 'malapert' && t.id !== saved.state.target) || api.targets.find((t) => t.id !== saved.state.target) || api.targets[0];
    const run = tour = { ...saved, mode, duration, target: other?.id || saved.state.target,
      at: -1, events: new AbortController(), manual: motion.matches, started: performance.now(), mars: null };
    run.steps = stepsFor(run); run.slot = duration / run.steps.length;
    json('mars.json').then((data) => { if (tour === run) run.mars = data; });
    hook('sky')?.stop();
    document.body.classList.add('tl-touring'); document.body.classList.toggle('tl-tour-demo', mode === '30');
    strip.hidden = false; strip.dataset.tourMode = mode; strip.dataset.completed = 'false';
    next.hidden = !run.manual;
    if (!run.manual) stop.focus({ preventScroll: true });
    document.dispatchEvent(new CustomEvent('earth-twin:tour', { detail: { phase: 'start', mode, duration } }));
    if (run.manual) {
      tourPosition.textContent = `${mode === '30' ? 'Demo' : 'Tour'} · Next`;
      tourCaption.textContent = 'Press Next to start. Each step waits for Next.';
      updateProgress(); next.focus({ preventScroll: true });
    } else {
      // Reserve the end of the final slot for restoring and painting the page.
      // The full board and globe need more time than the former tabbed shell.
      const restoreReserve = mode === '30' ? 2500 : 1500;
      run.deadline = setTimeout(() => { if (tour === run) stopTour(true); }, duration - restoreReserve);
      run.clock = setInterval(updateProgress, 100); advanceTour();
    }
    const halt = (event) => {
      if (!event.isTrusted) return;
      const control = event.target instanceof Element ? event.target.closest('.tl-tour button') : null;
      if (control && (event.type !== 'keydown' || ['Enter', ' '].includes(event.key))) return;
      if (run.manual && event.type === 'keydown' && event.key === 'Tab' && strip.contains(event.target)) {
        event.preventDefault(); (document.activeElement === next ? stop : next).focus(); return;
      }
      event.stopImmediatePropagation(); if (event.cancelable) event.preventDefault();
      if (event.type === 'pointerdown' || event.type === 'touchstart') {
        const swallow = (click) => { click.preventDefault(); click.stopImmediatePropagation(); };
        window.addEventListener('click', swallow, { capture: true, once: true, signal: life.signal });
        setTimeout(() => window.removeEventListener('click', swallow, true), 1000);
      }
      stopTour();
    };
    for (const name of ['keydown', 'pointerdown', 'click', 'touchstart', 'wheel'])
      window.addEventListener(name, halt, { capture: true, passive: false, signal: run.events.signal });
  }
  on(motion, 'change', () => {
    if (!tour || !motion.matches) return;
    clearTimeout(tour.timer); clearTimeout(tour.deadline); clearInterval(tour.clock);
    tour.manual = true; hook('sky')?.stop(); next.hidden = false; updateProgress();
    next.focus({ preventScroll: true });
  });
  function scheduleLink() {
    const mode = String(api.getState().tour);
    if (!['30', '60'].includes(mode)) return;
    // The shell calls this mount when a tour key is present, after core readiness.
    const readyAt = api.readyAt ?? Number(document.documentElement.dataset.readyAt);
    const delay = Number.isFinite(readyAt) ? Math.max(0, readyAt + 2000 - performance.now()) : 2000;
    linkTimer = setTimeout(() => { if (!destroyed) startTour(mode); }, delay);
    const cancel = () => clearTimeout(linkTimer);
    for (const name of ['keydown', 'pointerdown', 'touchstart', 'wheel']) on(window, name, cancel, { once: true, passive: true });
  }

  function periodName(state) {
    const bin = state.period === 'bin' ? state.bin : /^\d+$/.test(String(state.period)) ? +state.period : null;
    return bin != null ? api.periods.find((p) => p.index === bin)?.label || 'Selected period' : ({ year: 'Whole year', winter: 'Winter half', summer: 'Summer half', rock: 'Rock season' }[state.period] || String(state.period));
  }
  function bestPeriods(i, tid, step) {
    const values = api.periodHours(i, tid, step);
    if (!values) return [];
    return api.periods.map((p) => ({ ...p, hours: values[p.index] })).filter((p) => valid(p.hours) && p.hours > 0).sort((a, b) => b.hours - a.hours).slice(0, 3);
  }
  function viewLink(state) {
    const base = new URL(location.href); base.search = ''; base.hash = '';
    if (base.pathname.endsWith('/tools-dev.html')) base.pathname = base.pathname.replace(/tools-dev.html$/, 'index.html');
    // The host owns URL encodings, including its map centre and list switches.
    const params = new URLSearchParams(location.hash.slice(1));
    for (const key of ['target', 'place', 'view', 'step', 'period']) if (state[key] != null) params.set(key, String(state[key]));
    if (state.period === 'bin') params.set('period', String(state.bin));
    base.hash = params.toString(); return base.href;
  }
  async function summary(i, tid) {
    const a = api.area(i), state = { ...api.getState(), target: tid, place: a.id, view: a.hemisphere === 'S' ? 'antarctic' : 'arctic' };
    const south = a.hemisphere === 'S', step = Number(state.step), best = bestPeriods(i, tid, step);
    const selectedPeriod = state.period === 'bin' ? state.bin : state.period;
    const stepHours = [1, 2, 3, 4].map((s) => api.hours(i, tid, s, selectedPeriod)), link = viewLink(state);
    const [cells, flat, sources, moon, oddsBuffer] = await Promise.all([json('cells.json'), json('flat.json'), json('sources.json'), json('moon.json'), api.loadBin('snowodds.bin').catch(() => null), accessReady]);
    const lines = [nameOf(a), `Lunar region: ${target(tid)?.name || tid}.`, `Area centre: ${coords(a)}.`, `Period: ${periodName(state)}.`];
    if (noModel(tid)) lines.push(modelNote(tid), 'The light figures and Earth terrain figures remain available.');
    if (best.length) lines.push('Best ten-day periods of the year:', ...best.map((p) => `- ${p.label.replace('-', ' to ')}`));
    const ordered = cells?.ids?.[i] === a.id;
    let poleward = ordered ? flat?.targets?.[tid]?.poleward?.[cells.flat_row[i]] : null;
    if (south && step >= 2 && ordered) poleward = cells.south?.targets?.[tid]?.poleward?.[cells.south.cells.indexOf(i)];
    if (valid(poleward) && poleward >= 0) {
      const share = poleward / 1000;
      lines.push(`Time of day, for the ${south && step >= 2 ? 'rock season' : 'whole year'}:`);
      lines.push(`During ${number(share * 100)}% of the hours of low Sun, the Sun is to the ${south ? 'south' : 'north'}, near local solar midnight.`);
      if (Math.round((1 - share) * 100) > 0) lines.push(`The other ${number((1 - share) * 100)}% of these hours are near dawn, dusk or a low noon.`);
      lines.push('These are solar times, not civil clock times.');
    }
    for (const [s, labelText] of [[1, 'Sun only'], [2, south ? 'Rock season; snow not measured' : 'On snow-free ground'], [3, 'After terrain'], [4, 'Typical cloud']]) {
      const value = stepHours[s - 1]; if (valid(value)) lines.push(`${labelText}: ${hours(value)}.`);
    }
    if (south) lines.push('The page has no measured snow-free odds for Antarctica.');
    else if (ordered && oddsBuffer?.byteLength === api.areaCount * api.periods.length && best.length) {
      const odds = new Uint8Array(oddsBuffer);
      for (const p of best) { const value = odds[i * api.periods.length + p.index]; if (value !== 255) lines.push(`Snow-free odds, ${p.label}: ${number(value)}%.`); }
      if (a.snowStatus && a.snowStatus !== 'measured') lines.push(`Snow status: ${a.snowStatus}.`);
    }
    const differences = moon?.cards?.find((c) => c.id === tid)?.earth_cannot_match || [];
    if (differences.length) lines.push('What Earth cannot match:', ...differences.map((d) => '- ' + d.what));
    for (const difference of differences.filter((d) => ['black shadows', 'slow Sun'].includes(d.what))) lines.push(prose(difference.earth));
    const accessLine = accessText(i); if (accessLine) lines.push(accessLine, prose(airfields.what_it_is_not), prose(airfields.scheduled_what));
    if (sources?.notices?.copernicus_dem) lines.push('Terrain credit: ' + sources.notices.copernicus_dem);
    if (sources?.licence_line) lines.push(sources.licence_line);
    lines.push('Link to this view: ' + link);
    return lines.join('\n');
  }
  const accessReady = loadAccess();
  own(api.addCardSection('take-away', 'Take this place away', (i, tid) => {
    if (destroyed) return null;
    const node = el('div', 'tl-card-tools'), actions = el('div', 'tl-actions'), status = el('p', 'tl-note'); status.setAttribute('role', 'status');
    if (noModel(tid)) node.append(el('p', 'tl-note tl-model-note', modelNote(tid)));
    const preview = el('details', 'tl-inner-fold'); preview.append(el('summary', '', 'Read the plain-text summary'));
    const text = el('pre', 'tl-summary'); preview.append(text);
    const ready = summary(i, tid).then((value) => { if (!destroyed) text.textContent = value; return value; }).catch(() => { status.textContent = 'The page cannot prepare the summary.'; return null; });
    const copy = button('Copy summary', async () => {
      const value = await ready; if (!value || destroyed) return;
      try { await navigator.clipboard.writeText(value); status.textContent = 'The page copied the summary.'; }
      catch {
        const field = el('textarea', 'tl-copy-fallback'); field.value = value; field.readOnly = true; field.setAttribute('aria-label', 'Place summary to copy');
        node.append(field); field.focus(); field.select(); status.textContent = 'The page cannot use the clipboard. Select this summary. Then copy the text.';
      }
    });
    const print = button('Print this place', async () => {
      const value = await ready; if (!value || destroyed) return;
      printCard.replaceChildren(el('p', 'tl-eyebrow', 'LuniMartian Atlas · Place card'), el('h1', '', nameOf(api.area(i))), el('pre', 'tl-print-text', value.split('\n').slice(1).join('\n')));
      printCard.dataset.ready = 'true'; window.print();
    });
    actions.append(copy, print); node.append(actions, status, preview);
    const note = accessText(i); if (note) node.append(el('p', 'tl-note', note), el('p', 'tl-caption', prose(airfields.what_it_is_not)));
    return node;
  }, (i, tid) => `Copy or print this area's figures for ${target(tid)?.name || 'the selected lunar region'}.`));
  on(window, 'afterprint', () => { delete printCard.dataset.ready; });

  const exportStatus = el('p', 'tl-note'); exportStatus.setAttribute('role', 'status');
  takePanel.body.append(el('p', 'tl-note', 'Save the current short list as KML. Its rows, order and figures match the CSV and GeoJSON downloads.'));
  async function saveKML() {
    exportStatus.textContent = 'The page will prepare the KML file.';
    const sources = await json('sources.json'); if (destroyed) return;
    if (!sources?.licence_line) { exportStatus.textContent = 'The licence line is missing. The page cannot save this file.'; show(takePanel); return; }
    let snapshot;
    try { snapshot = await api.exportList(); }
    catch (error) { exportStatus.textContent = error.message || 'The page cannot save the current list.'; return; }
    if (destroyed) return;
    const state = api.getState(), { notes, rows } = snapshot;
    const marks = rows.map((row) => {
      const fields = Object.entries(row).map(([key, value]) => `<Data name="${esc(key)}"><value>${esc(value)}</value></Data>`).join('');
      const point = valid(row.longitude_deg_east) && valid(row.latitude_deg_north) ? `<Point><coordinates>${row.longitude_deg_east},${row.latitude_deg_north}</coordinates></Point>` : '';
      return `<Placemark><name>${esc(row.place_name || row.region || 'Area')}</name><description>${esc(row.list)}</description><ExtendedData>${fields}</ExtendedData>${point}</Placemark>`;
    }).join('\n');
    const description = Object.entries(notes).map(([key, value]) => `${key}: ${value}`).join('\n');
    const kml = `<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>${esc(notes.title)}</name><description>${esc(description)}</description>${marks}</Document></kml>\n`;
    if (exportURL) URL.revokeObjectURL(exportURL);
    exportURL = URL.createObjectURL(new Blob([kml], { type: 'application/vnd.google-earth.kml+xml;charset=utf-8' }));
    const link = el('a', 'tl-download', 'Download the KML file'); link.href = exportURL; link.download = `lunimartian-atlas_${state.tab}_${state.target}.kml`;
    takePanel.body.querySelector('.tl-download')?.remove(); takePanel.body.append(link); link.click();
    exportStatus.textContent = `The page saved ${number(rows.length)} ${rows.length === 1 ? 'row' : 'rows'} from the current short list.`;
    api.announce(exportStatus.textContent);
  }
  takePanel.body.append(button('Save KML', saveKML), exportStatus);
  toolsButton('kml', 'Save KML', () => { show(takePanel); saveKML(); });
  const unsubscribe = api.onState((state) => {
    if (destroyed) return;
    terrainNote.textContent = noModel(state.target) ? modelNote(state.target) : ''; terrainNote.hidden = !terrainNote.textContent;
    if (state.target !== lastTarget) { lastTarget = state.target; drawFamous(); if (winterPanel.node.open && winter) drawWinter(); }
  }); own(unsubscribe);
  terrainNote.textContent = noModel() ? modelNote() : ''; terrainNote.hidden = !terrainNote.textContent;
  toolsButton('tour', 'Tour (60 s)', () => startTour('60'));
  toolsButton('demo', 'Demo (30 s)', () => startTour('30'));
  if (typeof api.registerAction === 'function') {
    own(api.registerAction('tour', () => startTour('60')));
    own(api.registerAction('demo', () => startTour('30')));
  }
  // Linked tours do not wait for unrelated search and airfield data.
  scheduleLink();
  const loaded = await Promise.all([file('famous.json'), accessReady]);
  if (!destroyed) {
    [famous] = loaded; lastTarget = api.getState().target; drawFamous();
  }
  function destroy() {
    if (destroyed) return;
    stopTour(); clearTimeout(linkTimer); tourStrip?.remove(); destroyed = true; life.abort(); cleanups.reverse().forEach((fn) => fn());
    if (exportURL) URL.revokeObjectURL(exportURL); shell.remove();
  }
  return { destroy };
}
