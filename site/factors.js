// Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
// Factor matrix module: the table of every factor and its status (in root), and a folded
// "More about this place" part of the place card. Every figure and word comes from
// data/factors.json and data/factors.bin; nothing is fetched from any other host.

const READ = { u8: 'getUint8', u16: 'getUint16', u32: 'getUint32' };
const NO_MODEL = 'unknown: NASA has no 5 m terrain model of this region';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (tag === 'details') node.classList.add('fold');
  if (className?.split(' ').some(name => ['fx-status', 'fx-tag'].includes(name))) node.classList.add('tag');
  if (text != null) node.textContent = text;
  return node;
}

function finite(x) { return typeof x === 'number' && Number.isFinite(x); }

// The per-place reader for one layout (factors.bin or mars_factors.bin).
function reader(layout, buffer) {
  const view = new DataView(buffer);
  const fields = new Map(layout.fields.map((f) => [f.id, f]));
  function raw(f, i) {
    if (!f || i < 0 || i >= layout.count) return null;
    const at = f.offset + i * f.size;
    if (at + f.size > view.byteLength) return null;
    const stored = view[READ[f.type]](at, true);
    return stored === f.unknown ? null : stored;
  }
  return {
    fields,
    // { value, words } with value a number, words a string, or both null when unknown
    get(id, i, tables, months) {
      const f = fields.get(id);
      const stored = raw(f, i);
      if (stored == null) return { value: null, words: null, field: f };
      if (f.codes) return { value: null, words: f.codes[stored] ?? null, field: f };
      if (f.ref) return { value: null, words: null, ref: tables[f.ref]?.[stored] ?? null, field: f };
      if (f.mask) return { value: null, words: f.mask.filter((m, b) => (stored >> b) & 1).join(', ') || 'none', field: f };
      if (f.beyond && stored === f.beyond.stored) return { value: null, words: f.beyond.words, field: f };
      return { value: stored / f.scale, words: null, field: f };
    },
  };
}

export async function mount(root, api) {
  const offs = [];
  let doc, data, pageMeta;
  try {
    [doc, data, pageMeta] = await Promise.all([api.loadJSON('factors.json'), api.loadBin('factors.bin'), api.loadJSON('meta.json').catch(() => null)]);
  } catch (error) {
    if (root) root.replaceChildren(el('p', 'fx-note', 'The factor table is unavailable.'));
    return { destroy() { if (root) root.replaceChildren(); } };
  }
  const meta = doc.meta;
  const unknown = meta.unknown_word;
  const read = doc.layout ? reader(doc.layout, data) : null;
  const regionName = (id) => meta.region_names?.[id] || api.targets.find((t) => t.id === id)?.name || id;
  const noModel = id => (api.targets.find(t => t.id === id)?.has_model ?? pageMeta?.targets?.find(t => t.id === id)?.has_model) === false;
  const terrainRows = new Set(doc.matrix.filter(row => /(?:LOLA.*5 m|5 m.*LOLA)/i.test(row.moon_figure_from || '')).map(row => row.id));
  const needsTerrain = (rowId, figure) => terrainRows.has(rowId) || /measured terrain/i.test(figure?.kind || '');
  const kindTag = (kind) => meta.kind_tags?.[kind] || kind || null;
  let keepOpen = false;

  function show(x, digits) {
    if (!finite(x)) return unknown;
    return api.fmtNumber(x, digits ?? 0);
  }
  function figureText(fig) {
    if (!fig) return unknown;
    if (fig.ref) {
      const bits = [fig.ref.name, fig.ref.country].filter(Boolean);
      return bits.join(', ');
    }
    if (fig.words) return fig.words;
    if (!finite(fig.value)) return unknown;
    const unit = fig.field?.unit;
    const plain = unit && !['class', 'words', 'yes or no', 'name', 'count'].includes(unit);
    return show(fig.value, fig.field?.digits) + (plain ? ` ${unit}` : '');
  }
  function planetText(p) {
    if (!p) return null;
    if (finite(p.value)) return show(p.value, p.digits ?? meta.planet_digits) + (p.unit ? ` ${p.unit}` : '');
    if (Array.isArray(p.range) && p.range.every(finite)) return `${p.range.map((v) => show(v, meta.planet_digits)).join(' to ')}${p.unit ? ` ${p.unit}` : ''}`;
    if (p.text) return p.text;
    return unknown;
  }

  // ---- the matrix, in root ----
  function drawMatrix() {
    if (!root) return;
    root.replaceChildren();
    const counts = new Map();
    for (const row of doc.matrix) counts.set(row.status, (counts.get(row.status) || 0) + 1);
    const heading = el('header', 'section-head fx-section-head');
    const headingText = el('div');
    headingText.append(el('p', 'eyebrow', 'Go deeper'), el('h2', null, 'Which factors do we know?'),
      el('p', 'finding fx-finding', `The data gives the status of ${api.fmtNumber(doc.matrix.length)} factors.`));
    heading.append(headingText);
    const wrap = el('div', 'fx-matrix card');
    const totals = el('ul', 'fx-counts');
    for (const [status, count] of counts) totals.append(el('li', null, `${api.fmtNumber(count)}: ${status}`));
    const guide = el('details', 'fx-guide');
    guide.append(el('summary', null, 'How to read this'), totals);
    if (meta.left_out) guide.append(el('p', 'fx-note', meta.left_out));
    wrap.append(guide);
    const table = el('table', 'fx-table');
    const head = el('thead'), hr = el('tr');
    for (const h of ['Factor', 'Status'])
      { const th = el('th', null, h); th.scope = 'col'; hr.append(th); }
    head.append(hr); table.append(head);
    const matrixRows = [];
    for (const group of meta.groups) {
      const rows = doc.matrix.filter((r) => r.group === group);
      if (!rows.length) continue;
      const body = el('tbody');
      const gr = el('tr', 'fx-group'), gh = el('th', null, group);
      gh.colSpan = hr.children.length; gh.scope = 'colgroup';
      gr.append(gh); body.append(gr);
      for (const row of rows) {
        const tr = el('tr');
        const name = el('td', 'fx-name'); name.dataset.label = 'Factor';
        name.append(el('b', null, row.name));
        const meaning = el('details', 'fx-detail');
        meaning.append(el('summary', null, 'What this is and its sources'), el('span', 'fx-what', row.what_it_is));
        if (row.what_it_is_not) meaning.append(el('span', 'fx-not', row.what_it_is_not));
        name.append(meaning);
        meaning.append(el('span', 'fx-line', `Earth: ${row.earth_figure_from}`),
          el('span', 'fx-line fx-moon-source', `Moon: ${row.moon_figure_from}`),
          el('span', 'fx-line fx-mars-source', `Mars: ${row.mars_figure_from}`));
        const status = el('td', 'fx-status-cell'); status.dataset.label = 'Status';
        const badge = el('span', 'fx-status', row.status); badge.dataset.status = row.status;
        status.append(badge);
        const coverage = el('details', 'fx-detail');
        coverage.append(el('summary', null, 'Data coverage'));
        if (row.status_reason) coverage.append(el('span', 'fx-line', row.status_reason));
        const c = row.coverage || {};
        if (c.moon_part_areas) coverage.append(el('span', 'fx-line', `${api.fmtNumber(c.moon_part_areas.known)} of ${api.fmtNumber(c.moon_part_areas.of)} areas`));
        if (c.mars_squares) coverage.append(el('span', 'fx-line', `${api.fmtNumber(c.mars_squares.known)} of ${api.fmtNumber(c.mars_squares.of)} Mars squares`));
        if (c.lunar_regions) coverage.append(el('span', 'fx-line', `${api.fmtNumber(c.lunar_regions.known)} of ${api.fmtNumber(c.lunar_regions.of)} lunar regions`));
        if (c.mars_sites) coverage.append(el('span', 'fx-line', `${api.fmtNumber(c.mars_sites.known)} of ${api.fmtNumber(c.mars_sites.of)} Mars sites`));
        status.append(coverage);
        tr.append(name, status);
        body.append(tr);
        matrixRows.push(tr);
      }
      table.append(body);
    }
    const scroller = el('div', 'fx-table-wrap');
    scroller.append(table);
    wrap.append(scroller);
    if (matrixRows.length > 5) {
      const more = el('button', 'btn fx-show-all', 'Show all');
      more.type = 'button'; more.setAttribute('aria-expanded', 'false');
      const setExpanded = expanded => {
        matrixRows.forEach((row, index) => { row.hidden = !expanded && index >= 5; });
        table.querySelectorAll('tbody').forEach(body => {
          body.hidden = ![...body.children].some(row => !row.classList.contains('fx-group') && !row.hidden);
        });
        more.textContent = expanded ? 'Show fewer' : 'Show all';
        more.setAttribute('aria-expanded', String(expanded));
      };
      more.addEventListener('click', () => setExpanded(more.getAttribute('aria-expanded') !== 'true'));
      setExpanded(false); wrap.append(more);
    }
    wrap.append(el('p', 'caption fx-caption', meta.caption));
    root.append(heading, wrap);
  }

  // ---- the card part ----
  function figureLine(label, areaText, tag, moonText, moonLabel) {
    const li = el('li', 'fx-fig');
    li.append(el('span', 'fx-label', label));
    const val = el('span', 'fx-val', areaText);
    if (areaText === unknown) val.classList.add('fx-unknown');
    li.append(val);
    if (tag) li.append(el('span', 'fx-tag', tag));
    if (moonText != null) li.append(el('span', 'fx-moon', `${moonLabel}: ${moonText}`));
    return li;
  }

  function navBlock(i, targetId) {
    const target = api.targets.find((t) => t.id === targetId);
    const region = doc.lunar_regions?.[targetId] || {};
    const box = el('div', 'fx-nav card');
    box.append(el('h5', null, 'What affects navigation by sight?' ));
    const table = el('table', 'fx-navtable');
    const head = el('tr');
    head.append(el('th', null, 'Part'), el('th', null, 'This area'), el('th', null, regionName(targetId)));
    const thead = el('thead'); thead.append(head); table.append(thead);
    const body = el('tbody');
    const add = (part, here, there) => {
      const tr = el('tr');
      const a = el('td', here === unknown ? 'fx-unknown' : null, here), b = el('td', there === unknown ? 'fx-unknown' : null, there);
      a.dataset.label = 'This area'; b.dataset.label = regionName(targetId);
      tr.append(el('th', null, part), a, b);
      body.append(tr);
    };
    const ceiling = (region.sun_low_hours || [])[0];
    const limit = target ? `above the horizon, up to ${show(target.limitDeg, 2)} degrees` : unknown;
    add('Sun height during low Sun', limit, ceiling ? `up to ${planetText(ceiling)}` : unknown);
    const share = read.get(`shadow_share@${targetId}`, i, doc.tables);
    const hours = read.get(`low_sun_hours@${targetId}`, i, doc.tables);
    const shadowHere = finite(share.value) ? `${show(share.value, share.field.digits)} of ${figureText(hours)}` : unknown;
    const shadowThere = (region.visual_navigation || [])[0];
    add('Share of ground in shadow during low Sun', shadowHere, noModel(targetId) ? NO_MODEL : shadowThere ? `${planetText(shadowThere)} (all hours)` : unknown);
    const rough = read.get('rough_90', i, doc.tables);
    const ratio = noModel(targetId) ? { value: null } : read.get(`rough_vs_region_90@${targetId}`, i, doc.tables);
    const regionRough = (region.roughness || []).find((p) => p.base === '90');
    const roughHere = finite(rough.value) ? `${figureText(rough)}${finite(ratio.value) ? `, ${show(ratio.value, ratio.field.digits)} times the lunar region's` : ''}` : unknown;
    add('Roughness at 90 m', roughHere, noModel(targetId) ? NO_MODEL : regionRough ? planetText(regionRough) : unknown);
    const haze = read.get('aod_year', i, doc.tables);
    const air = (region.haze || [])[0];
    add('Haze (aerosol optical depth)', figureText(haze), air ? planetText(air) : unknown);
    table.append(body);
    const wrap = el('div', 'fx-table-wrap'); wrap.append(table);
    box.append(wrap, el('p', 'fx-note', meta.nav_sentence));
    if (noModel(targetId)) box.append(el('p', 'fx-note', 'Lunar terrain comparison: cannot tell.'));
    return box;
  }

  function tremorNote(i) {
    const verdict = read.get('tremor_verdict', i, doc.tables).words;
    const box = el('div', 'fx-notes');
    if (verdict === 'cannot tell' && meta.tremor_cannot_tell) box.append(el('p', 'fx-note', meta.tremor_cannot_tell));
    if (meta.tremor_blind_spots) box.append(el('p', 'fx-note', meta.tremor_blind_spots));
    return box;
  }

  function regionFigures(rowId, targetId) {
    const figures = (doc.lunar_regions?.[targetId]?.[rowId]) || [];
    return noModel(targetId) ? figures.map(figure => needsTerrain(rowId, figure) ? { ...figure, value: null, range: null, text: NO_MODEL, kind: 'unknown' } : figure) : figures;
  }

  function renderCard(i, targetId) {
    if (!read || i == null || i < 0 || i >= doc.layout.count) return null;
    const area = api.area(i);
    const fold = el('details', 'fx-fold');
    fold.open = keepOpen;
    fold.addEventListener('toggle', () => { keepOpen = fold.open; });
    fold.append(el('summary', null, 'Read the figures'));
    const inner = el('div', 'fx-inner');
    inner.append(el('p', 'fx-note', meta.card_lead), el('p', 'fx-note', meta.coarse_warning), el('p', 'fx-note', meta.existing_rows_note));
    if (noModel(targetId)) inner.append(el('p', 'fx-note fx-model-note', `Lunar terrain comparison: cannot tell. ${NO_MODEL}.`));
    const moonLabel = regionName(targetId);
    for (const group of meta.groups) {
      const rows = doc.matrix.filter((r) => r.group === group && (r.fields_on_page || []).length);
      if (!rows.length) continue;
      const sec = el('section', 'fx-group-part');
      sec.append(el('h5', null, group));
      for (const row of rows) {
        if (row.id === 'visual_navigation') { sec.append(navBlock(i, targetId)); continue; }
        const part = el('div', 'fx-row');
        const title = el('p', 'fx-row-title');
        title.append(el('b', null, row.name), el('span', 'fx-status', row.status));
        title.lastChild.dataset.status = row.status;
        part.append(title);
        const list = el('ul', 'fx-figs');
        const planet = regionFigures(row.id, targetId).slice();
        for (const id of row.fields_on_page) {
          const f = read.fields.get(id);
          if (!f) continue;
          if (f.target && f.target !== targetId) continue;
          const fig = read.get(id, i, doc.tables);
          let moonText = noModel(targetId) && terrainRows.has(row.id) ? NO_MODEL : null;
          const match = planet.findIndex((p) => p.field === id || (p.base && id === `rough_${p.base}`));
          if (match >= 0) { moonText = planetText(planet[match]); planet.splice(match, 1); }
          const label = f.target ? `${f.label} (${regionName(f.target)})` : f.label;
          list.append(figureLine(label, figureText(fig), kindTag(f.kind), moonText, moonLabel));
        }
        for (const p of planet) {
          const li = el('li', 'fx-fig fx-planet');
          li.append(el('span', 'fx-label', `${moonLabel}: ${p.label}`), el('span', 'fx-val', planetText(p)));
          if (p.kind) li.append(el('span', 'fx-tag', p.kind));
          if (p.note) li.append(el('span', 'fx-moon', p.note));
          list.append(li);
        }
        part.append(list);
        if (row.id === 'small_tremors') part.append(tremorNote(i));
        if (row.id === 'permafrost' && area?.hemisphere === 'S' && meta.south_permafrost_note) part.append(el('p', 'fx-note', meta.south_permafrost_note));
        if (row.what_it_is_not) part.append(el('p', 'fx-note fx-not', row.what_it_is_not));
        sec.append(part);
      }
      inner.append(sec);
    }
    fold.append(inner);
    return fold;
  }

  function cardSummary(i, targetId) {
    if (!read || i == null || i < 0 || i >= doc.layout.count) return 'The figures for this area are unknown.';
    const fields = [...read.fields.values()].filter(field => !field.target || field.target === targetId);
    const known = fields.filter(field => {
      if (noModel(targetId) && field.id.startsWith('rough_vs_region_')) return false;
      const figure = read.get(field.id, i, doc.tables);
      return finite(figure.value) || figure.words != null || figure.ref != null;
    }).length;
    return `${api.fmtNumber(known)} of ${api.fmtNumber(fields.length)} figures are known for this area.`;
  }

  drawMatrix();
  const off = api.addCardSection('fx-more', meta.card_title, renderCard, cardSummary);
  if (typeof off === 'function') offs.push(off);
  return {
    destroy() {
      for (const fn of offs) fn();
      offs.length = 0;
      if (root) root.replaceChildren();
    },
  };
}
