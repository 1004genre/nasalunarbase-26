// Place-card extension. All data comes through the page's module API.
const CREDIT = 'Drawn by code from open data; the code was written with AI assistance.';
const GOALS = [['landscape', 'Landscape'], ['environment', 'Environment'], ['full', 'All factors together']];
const finite = value => typeof value === 'number' && Number.isFinite(value);
const node = (tag, className, text) => {
  const element = document.createElement(tag);
  element.className = className || 'cx-text';
  if (['cx-context', 'cx-site'].includes(className)) element.classList.add('card');
  if (className === 'cx-link') element.classList.add('btn', 'btn-ghost');
  if (className === 'cx-pass') element.classList.add('tag');
  if (text != null) element.textContent = text;
  return element;
};
const decimals = value => {
  const [digits, exponent = '0'] = String(value).split('e');
  return Math.max(0, (digits.split('.')[1]?.length || 0) - Number(exponent));
};

// Half-open bounds: south/west included, north/east excluded. The date line wraps.
function squareLookup(manifest, step) {
  if (!finite(step) || step <= 0) throw new Error('Square size is unavailable.');
  const parsed = manifest.ids.map(id => /^(.*?)_(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)$/.exec(id));
  if (parsed.some(parts => !parts)) throw new Error('Square IDs are unavailable.');
  const precision = Math.max(decimals(step), ...parsed.flatMap(parts => [decimals(parts[2]), decimals(parts[3])]));
  const key = (lat, lon) => {
    if (!finite(lat) || !finite(lon) || lat < -90 || lat > 90) return null;
    const unit = 10 ** Math.max(precision, decimals(lat), decimals(lon));
    const width = Math.round(step * unit), halfTurn = 180 * unit, fullTurn = 360 * unit;
    const longitude = ((Math.round(lon * unit) + halfTurn) % fullTurn + fullTurn) % fullTurn;
    const latitude = Math.round((lat + 90) * unit);
    const row = Math.min(Math.floor(latitude / width), Math.ceil(180 * unit / width) - 1);
    return `${row}_${Math.floor(longitude / width)}`;
  };
  const indexes = new Map(parsed.map((parts, i) => [key(Number(parts[2]), Number(parts[3])), i]));
  return area => area ? indexes.get(key(area.lat, area.lon)) ?? -1 : -1;
}

function reader(manifest, loadBin) {
  if (manifest.count !== manifest.ids.length) throw new Error('Square order does not match.');
  const views = new Map(), pending = new Map();
  const types = { uint8: ['getUint8', 1], int8: ['getInt8', 1], uint16: ['getUint16', 2], int16: ['getInt16', 2],
    uint32: ['getUint32', 4], int32: ['getInt32', 4], float32: ['getFloat32', 4], float64: ['getFloat64', 8] };
  const columns = new Map();
  for (const [name, column] of Object.entries(manifest.columns)) {
    const [method, bytes] = types[column.type] || [];
    if (!method || !finite(column.scale) || column.scale <= 0 || !Number.isInteger(column.offset) || column.offset < 0) throw new Error('Invalid square layout.');
    columns.set(name, { ...column, file: column.file || manifest.file, method, bytes });
  }
  async function load(file) {
    if (!pending.has(file)) pending.set(file, Promise.resolve().then(() => loadBin(file)).then(buffer => {
      for (const column of columns.values()) if (column.file === file && column.offset + manifest.count * column.bytes > buffer.byteLength) throw new Error('Invalid square layout.');
      views.set(file, new DataView(buffer));
    }).catch(error => { pending.delete(file); throw error; }));
    return pending.get(file);
  }
  const get = (name, i) => {
    const column = columns.get(name);
    if (!column || !Number.isInteger(i) || i < 0 || i >= manifest.count) return null;
    const view = views.get(column.file);
    if (!view) return null;
    const raw = view[column.method](column.offset + i * column.bytes, true);
    return !finite(raw) || raw === column.unknown ? null : raw / column.scale;
  };
  return { get, load, async site(id) {
    const files = new Set([...columns].filter(([name]) => name.startsWith(`sites.${id}.`)).map(([, column]) => column.file));
    for (const file of files) await load(file);
  } };
}

export async function mount(root, api) {
  // The page owns this hidden root. This module registers only a card section.
  let removeSection;
  const lifecycle = new AbortController();
  const destroy = () => { lifecycle.abort(); if (typeof removeSection === 'function') removeSection(); };
  const separateSummary = api.addCardSection.length >= 4;
  const title = 'How does this place compare with Mars?';
  const number = (value, digits = 0) => finite(value) ? api.fmtNumber(value, digits) : 'unknown';
  try {
    const [data, moon] = await Promise.all([api.loadJSON('mars.json'), api.loadJSON('meta.json').catch(() => null)]);
    const manifest = data.squares, meta = data.meta;
    const files = reader(manifest, name => api.loadBin(name)), read = files.get;
    await files.load(manifest.file);
    if (lifecycle.signal.aborted) return { destroy };
    const locate = squareLookup(manifest, meta.square_deg);
    const pass = `First pass · squares of approximately ${number(meta.square_km_about)} km (${number(meta.square_deg, decimals(meta.square_deg))}°)`;
    const ranks = new Map();
    const siteLoads = new Map(), readySites = new Set();
    const loadSite = site => {
      if (!siteLoads.has(site.id)) siteLoads.set(site.id, files.site(site.id).then(() => {
        if (lifecycle.signal.aborted) return;
        for (const [goal] of GOALS) {
          const path = `sites.${site.id}.${goal}`;
          const scores = Array.from({ length: manifest.count }, (_, i) => read(path, i)).filter(finite).sort((a, b) => b - a);
          const percents = new Map();
          scores.forEach((score, i) => { if (!percents.has(score)) percents.set(score, Math.ceil((i + 1) / scores.length * 100)); });
          ranks.set(path, percents);
        }
        readySites.add(site.id);
      }).catch(error => { siteLoads.delete(site.id); throw error; }));
      return siteLoads.get(site.id);
    };
    const hasNearest = [0, 1, 2].every(rank => manifest.columns[`nearest_site_${rank}`] && manifest.columns[`nearest_full_${rank}`]);
    const nearest = i => hasNearest ? [0, 1, 2].map(rank => ({ site: data.sites[read(`nearest_site_${rank}`, i)], value: read(`nearest_full_${rank}`, i) }))
      .filter(item => item.site && finite(item.value))
      : data.sites.map(site => ({ site, value: read(`sites.${site.id}.full`, i) })).filter(item => finite(item.value)).sort((a, b) => b.value - a.value).slice(0, 3);
    const closest = i => nearest(i)[0];
    function summary(i) {
      const square = locate(api.area(i));
      if (square < 0) return `This area is not in the Mars first pass. The squares of the first pass are approximately ${number(meta.square_km_about)} km wide.`;
      const best = closest(square);
      return best
        ? `Closest Mars site: ${best.site.name}. Score for all factors together: ${number(best.value, 2)} (first pass, squares of approximately ${number(meta.square_km_about)} km).`
        : `The scores for all factors together are unknown for this square (first pass, squares of approximately ${number(meta.square_km_about)} km).`;
    }
    function months(i, id) {
      const path = `sites.${id}`, count = read(`${path}.best_months_count`, i);
      if (count == null) return 'Best Earth months: unknown.';
      if (count === 0) return 'No month has a score above zero.';
      const names = Array.from({ length: count }, (_, month) => {
        const value = read(`${path}.best_month_${month}`, i);
        return value == null ? 'unknown' : manifest.months[value] ?? 'unknown';
      });
      return `Best Earth months: ${names.join(', ')}.`;
    }
    function render(i) {
      const card = node('div', 'cx-card');
      const area = api.area(i), square = locate(area);
      if (!separateSummary) card.append(node('p', 'cx-summary', summary(i)));
      const note = node('div', 'cx-context');
      note.append(node('p', 'cx-pass', pass));
      const explanation = node('details', 'cx-rules fold');
      explanation.append(node('summary', '', 'How to read these scores'));
      const ratio = meta.square_km_about / moon?.scoring?.cell_km;
      if (finite(ratio)) explanation.append(node('p', 'cx-note', `The square is approximately ${number(ratio)} times as wide as the area. Thus, its scores describe the wider surroundings.`));
      else explanation.append(node('p', 'cx-note', 'These scores describe the wider surroundings. The area width is unavailable.'));
      note.append(node('p', 'cx-note', 'This is not a climate match.'));
      for (const caution of [meta.score_caution, meta.climate_caution].filter(Boolean)) explanation.append(node('p', 'cx-note', caution));
      note.append(explanation);
      card.append(note);
      if (!area) card.append(node('p', 'cx-unavailable', 'The area coordinates are unavailable.'));
      else if (square < 0) {
        card.append(node('p', 'cx-unavailable', 'This square is not in the Mars first pass.'));
        card.append(node('p', 'cx-note', `Each square in the first pass must have at least ${number(meta.min_bare * 100)} percent bare ground.`));
        card.append(node('p', 'cx-note', 'If a square has insufficient bare ground or no data, it is not in the first pass. The file does not give the exact reason for this square.'));
      } else {
        const region = read('region', square);
        card.append(node('p', 'cx-square', `${region == null ? 'Region unknown' : manifest.regions[region] ?? 'Region unknown'} · ${manifest.ids[square]}`));
        const orderSites = goal => data.sites.filter(site => readySites.has(site.id)).sort((a, b) => {
          const first = read(`sites.${a.id}.${goal}`, square), second = read(`sites.${b.id}.${goal}`, square);
          return goal === 'name' ? a.name.localeCompare(b.name) : !finite(first) ? (finite(second) ? 1 : 0)
            : !finite(second) ? -1 : second - first;
        });
        const sites = node('div', 'cx-sites');
        sites.setAttribute('aria-label', 'Nearest Mars sites on all factors together');
        const live = () => !lifecycle.signal.aborted && card.isConnected;
        for (const { site, value } of nearest(square)) {
          const panel = node('details', 'cx-site');
          panel.dataset.site = site.id;
          const heading = node('summary', 'cx-site-heading');
          heading.append(node('span', 'cx-site-title', site.name), node('span', 'cx-value', number(value, 2)));
          const content = node('div', 'cx-site-content'); panel.append(heading, content);
          let loaded = false, working = false;
          const drawSite = () => {
            content.replaceChildren(node('p', 'cx-status', site.display_status || site.kind), node('p', 'cx-pass', pass));
            const drawing = node('div', 'cx-scores');
            for (const [goal, label] of GOALS) {
              const path = `sites.${site.id}.${goal}`, score = read(path, square);
              const row = node('div', 'cx-score'); row.dataset.goal = goal;
              row.append(node('span', 'cx-label', label), node('span', 'cx-value', number(score, 2)));
              if (finite(score)) {
                const track = node('span', 'cx-track'), fill = node('span', 'cx-fill');
                track.setAttribute('aria-hidden', 'true');
                const [low, high] = meta.score_scale || [];
                if (finite(low) && finite(high) && high > low) {
                  fill.style.width = `${Math.max(0, Math.min(1, (score - low) / (high - low))) * 100}%`;
                  track.append(fill); row.append(track);
                }
                row.append(node('span', 'cx-rank', `in the top ${number(ranks.get(path)?.get(score))} percent`));
              } else row.append(node('span', 'cx-rank', 'Rank unknown'));
              drawing.append(row);
            }
            content.append(drawing, node('p', 'cx-caption', CREDIT), node('p', 'cx-months', months(square, site.id)));
          };
          panel.addEventListener('toggle', async () => {
            if (!panel.open || loaded || working || !live()) return;
            working = true; const status = node('p', 'cx-working', 'Working'); status.setAttribute('role', 'status'); content.replaceChildren(status);
            try { await loadSite(site); if (!live()) return; drawSite(); loaded = true; }
            catch { if (live()) content.replaceChildren(node('p', 'cx-unavailable', 'The site figures are unavailable. Close and open this row to try again.')); }
            finally { working = false; }
          }, { signal: lifecycle.signal });
          sites.append(panel);
        }
        if (!sites.children.length) sites.append(node('p', 'cx-note', 'The scores for all factors together are unknown for this square.'));
        else card.append(node('p', 'cx-note', `Nearest ${number(sites.children.length)} sites · all factors together`));
        const all = node('details', 'cx-all-sites cx-rules fold');
        all.append(node('summary', '', `Show all ${number(data.sites.length)} sites`), node('p', 'cx-pass', pass));
        const loading = node('div', 'cx-loading'), progress = node('p', 'cx-working'), stop = node('button', 'cx-load-button btn', 'Stop'), resume = node('button', 'cx-load-button btn', 'Continue');
        progress.setAttribute('role', 'status'); stop.type = resume.type = 'button'; stop.hidden = resume.hidden = true; loading.append(progress, stop, resume); all.append(loading);
        const sortLabel = node('label', 'cx-sort', 'Order sites by');
        const sort = node('select', 'cx-sort-control');
        for (const [value, label] of [['full', 'All factors together'], ['landscape', 'Landscape'], ['environment', 'Environment'], ['name', 'Site name']]) {
          const option = node('option', '', label); option.value = value; sort.append(option);
        }
        sortLabel.append(sort); all.append(sortLabel);
        const tableWrap = node('div', 'cx-table-wrap'), table = node('table', 'cx-table');
        const caption = node('caption', '', `Mars site scores · ${pass}`); table.append(caption);
        const head = node('thead'), header = node('tr');
        const columns = [['name', 'Site'], ['full', 'All factors together'], ['landscape', 'Landscape'], ['environment', 'Environment']];
        for (const [key, label] of columns) { const cell = node('th', '', label); cell.scope = 'col'; cell.dataset.sort = key; header.append(cell); }
        const monthsHead = node('th', '', 'Best Earth months'); monthsHead.scope = 'col'; header.append(monthsHead); head.append(header);
        const body = node('tbody'); table.append(head, body); tableWrap.append(table); all.append(tableWrap);
        const drawTable = () => {
          body.replaceChildren();
          for (const site of orderSites(sort.value)) {
            const row = node('tr'); row.dataset.site = site.id;
            const name = node('th', '', site.name); name.scope = 'row';
            if (site.display_status) name.append(node('small', 'cx-status', site.display_status));
            row.append(name);
            for (const goal of ['full', 'landscape', 'environment']) {
              const path = `sites.${site.id}.${goal}`, score = read(path, square);
              const cell = node('td', 'cx-value', number(score, 2));
              cell.append(node('small', 'cx-rank', finite(score) ? `Top ${number(ranks.get(path)?.get(score))} percent` : 'Rank unknown')); row.append(cell);
            }
            row.append(node('td', 'cx-months', months(square, site.id).replace(/^Best Earth months: /, ''))); body.append(row);
          }
          for (const cell of header.querySelectorAll('[data-sort]')) {
            if (cell.dataset.sort === sort.value) cell.setAttribute('aria-sort', sort.value === 'name' ? 'ascending' : 'descending');
            else cell.removeAttribute('aria-sort');
          }
        };
        let run = 0, running = false;
        const countText = () => `${number(readySites.size)} of ${number(data.sites.length)} sites`;
        const pause = () => {
          run++; running = false; stop.hidden = true; resume.hidden = readySites.size === data.sites.length;
          progress.textContent = `Stopped. ${countText()} ready.`;
        };
        const loadAll = async () => {
          if (running || !live()) return;
          running = true; const token = ++run; stop.hidden = false; resume.hidden = true; progress.textContent = `Working · ${countText()} ready.`;
          drawTable();
          try {
            for (const site of data.sites) {
              if (!live() || token !== run) return;
              if (!readySites.has(site.id)) await loadSite(site);
              if (!live() || token !== run) return;
              progress.textContent = `Working · ${countText()} ready.`; drawTable();
              await new Promise(resolve => setTimeout(resolve, 0));
            }
            progress.textContent = `${countText()} ready.`;
          } catch {
            if (live() && token === run) { progress.textContent = `The next site is unavailable. ${countText()} ready.`; resume.hidden = false; }
          } finally {
            if (live() && token === run) { running = false; stop.hidden = true; }
          }
        };
        stop.addEventListener('click', pause, { signal: lifecycle.signal });
        resume.addEventListener('click', loadAll, { signal: lifecycle.signal });
        all.addEventListener('toggle', () => { if (all.open) loadAll(); else if (running) pause(); }, { signal: lifecycle.signal });
        sort.addEventListener('change', drawTable, { signal: lifecycle.signal });
        const rules = node('details', 'cx-rules fold');
        rules.append(node('summary', '', 'How to read the ranks'), node('p', 'cx-note', 'Each rank uses all the squares with a known score for that Mars site and goal. Equal scores have the same rank. The page rounds each percentage up.'));
        card.append(sites, all, rules);
      }
      const link = node('a', 'cx-link', 'Open the Mars section');
      const next = { dest: 'mars', go: 'mars', only: null, mgoal: 'full' };
      if (square >= 0) { next.msquare = manifest.ids[square]; const best = closest(square); if (best) next.msite = best.site.id; }
      const params = new URLSearchParams(location.hash.slice(1));
      for (const [key, value] of Object.entries(next)) { if (value == null) params.delete(key); else params.set(key, value); }
      link.href = `#${params}`;
      link.addEventListener('click', event => {
        if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault(); api.setState(next);
      }, { signal: lifecycle.signal });
      card.append(link);
      return card;
    }
    if (!lifecycle.signal.aborted) removeSection = api.addCardSection('cross', title, render, summary);
  } catch {
    const message = 'The local data for the Mars first pass is unavailable.';
    if (!lifecycle.signal.aborted) removeSection = api.addCardSection('cross', title, () => node('p', 'cx-unavailable', message), () => message);
  }
  return { destroy };
}
