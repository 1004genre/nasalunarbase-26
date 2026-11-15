// Power and steady influences: a dependency-free page API extension.
const CREDIT = 'Drawn by code from open data; the code was written with AI assistance.';
const ESTIMATE = 'rough estimate by our own rule';
const finite = value => typeof value === 'number' && Number.isFinite(value);
const element = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (tag === 'details') node.classList.add('fold');
  if (className?.split(' ').some(name => ['ex-block', 'ex-count-group', 'ex-low-sun'].includes(name))) node.classList.add('card');
  if (className?.split(' ').some(name => ['ex-badge', 'ex-source-tag'].includes(name))) node.classList.add('tag');
  if (className === 'ex-eyebrow') node.classList.add('eyebrow');
  if (text != null) node.textContent = text;
  return node;
};
function fold(title, content) {
  const node = element('details', 'ex-details');
  node.append(element('summary', '', title), content);
  return node;
}
function paragraphs(lines, className = 'ex-copy') {
  const node = element('div', className);
  for (const line of lines || []) node.append(element('p', '', line));
  return node;
}

export async function mount(root, api) {
  const cleanups = [];
  root.classList.add('ex-module');
  root.replaceChildren(element('p', 'ex-status', 'Power and steady influences: please wait.'));
  const destroy = () => {
    for (const cleanup of cleanups.splice(0)) if (typeof cleanup === 'function') cleanup();
    root.replaceChildren();
    root.classList.remove('ex-module');
  };
  const read = async (name, binary = false) => {
    try { return await (binary ? api.loadBin(name) : api.loadJSON(name)); }
    catch { return null; }
  };
  const [data, prose] = await Promise.all([read('extra.json'), read('extra-prose.json')]);
  if (!data) {
    root.replaceChildren(element('p', 'ex-status', 'The data for power and steady influences is unavailable.'));
    return { destroy };
  }
  const buffer = await read(data.binary, true);
  let valid = data.area_count === api.areaCount && buffer?.byteLength === data.binary_bytes;
  if (valid && data.ids_sha256 && globalThis.crypto?.subtle) {
    const ids = Array.from({ length: api.areaCount }, (_, i) => api.area(i)?.id).join('\n');
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ids));
    valid = Array.from(new Uint8Array(hash), value => value.toString(16).padStart(2, '0')).join('') === data.ids_sha256;
  }
  if (!valid) {
    root.replaceChildren(element('p', 'ex-status', 'The data is unavailable or does not match these areas.'));
    return { destroy };
  }
  const view = new DataView(buffer);
  const types = { u8: ['getUint8', 1], u16: ['getUint16', 2], u32: ['getUint32', 4], f32: ['getFloat32', 4] };
  const expand = value => Array.isArray(value) ? value.map(expand) : typeof value === 'string'
    ? value.replace(/\{@n:(\d+)\}/g, (_, index) => data.lookups?.names?.[index] ?? 'unknown') : value;
  const get = (path, i) => {
    const field = data.fields[path];
    if (!field || !Number.isInteger(i) || i < 0 || i >= api.areaCount) return null;
    const [method, size] = types[field.type] || [];
    if (!method) return null;
    const values = field.values || data.lookups?.[field.lookup];
    const one = j => {
      const raw = view[method](field.offset + (i * field.width + j) * size, true);
      if (!Number.isFinite(raw) || raw === field.unknown) return null;
      return values ? expand(values[raw] ?? null) : field.boolean ? Boolean(raw) : raw;
    };
    return field.width > 1 ? Array.from({ length: field.width }, (_, j) => one(j)) : one(0);
  };
  const number = (value, digits = 1) => finite(value) ? api.fmtNumber(value, digits) : 'unknown';
  const year = value => finite(value) ? String(value) : 'unknown';
  const quantity = (value, unit, digits = 1) => finite(value) ? `${number(value, digits)} ${unit}` : 'unknown';
  const percentage = value => finite(value) ? `${number(value * 100)}%` : 'unknown';
  const target = id => api.targets.find(item => item.id === id);
  const power = data.meta?.power || {};
  const steady = data.meta?.steady || {};
  const catalogue = data.meta?.tremors || {};
  const recentYear = power.rules?.geo_recent_year?.value;
  const months = Array.from({ length: 12 }, (_, month) => ({
    short: new Intl.DateTimeFormat('en', { month: 'short', timeZone: 'UTC' }).format(new Date(Date.UTC(2000, month))),
    long: new Intl.DateTimeFormat('en', { month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2000, month)))
  }));
  function badge(word, kind) {
    const categories = Object.keys(power.counts?.[kind] || {});
    const rank = word == null ? -1 : categories.indexOf(word);
    const mark = rank >= 0 ? ['✓', '≈', '×'][rank] || '•' : word == null ? '?' : '•';
    const node = element('span', `ex-badge${word == null ? ' ex-unknown' : ''}`);
    const symbol = element('span', 'ex-mark', mark);
    symbol.setAttribute('aria-hidden', 'true');
    node.append(symbol, document.createTextNode(word ?? 'unknown'));
    return node;
  }
  function caveat(kind) {
    return fold('What this cannot tell us', paragraphs(prose?.caveats?.[kind] || ['The detailed limits are unavailable.']));
  }
  function sunless(i) {
    const values = get('power.solar.months_without_sun', i);
    if (!Array.isArray(values)) return 'Months with no Sun: unknown.';
    if (!values.length) return 'The data lists no month without Sun.';
    const dark = new Set(values.map(value => months.findIndex(month => month.short === value)).filter(value => value >= 0));
    if (dark.size === months.length) return 'The data shows no Sun in any month.';
    const start = [...dark].find(month => !dark.has((month + months.length - 1) % months.length));
    const groups = [];
    for (let offset = 0; offset < months.length; offset++) {
      const month = (start + offset) % months.length;
      if (!dark.has(month)) continue;
      let last = month;
      while (offset + 1 < months.length && dark.has((last + 1) % months.length)) {
        offset++;
        last = (last + 1) % months.length;
      }
      groups.push(last === month ? `in ${months[month].long}` : `from ${months[month].long} to ${months[last].long}`);
    }
    return `The data shows no Sun ${groups.join(' and ')}.`;
  }
  function monthStrip(values, label, unit) {
    const wrapper = element('div', 'ex-months');
    const series = Array.isArray(values) ? values : months.map(() => null);
    const known = series.filter(finite);
    const maximum = known.length ? Math.max(...known) : null;
    const chart = element('div', 'ex-strip');
    chart.setAttribute('role', 'img');
    chart.setAttribute('aria-label', `${label}. A table below gives the value for each month.`);
    series.forEach((value, j) => {
      const column = element('div', 'ex-month');
      const track = element('div', 'ex-month-track');
      if (finite(value)) {
        const bar = element('span', 'ex-month-bar');
        bar.style.height = `${maximum > 0 ? value / maximum * 100 : 0}%`;
        track.append(bar);
        if (value === 0) track.append(element('span', 'ex-zero', '0'));
      } else track.append(element('span', 'ex-month-unknown', '?'));
      column.title = `${months[j].long}: ${quantity(value, unit, 2)}`;
      column.append(track, element('span', 'ex-month-label', months[j].short));
      chart.append(column);
    });
    wrapper.append(element('p', 'ex-small', label), chart, element('p', 'ex-caption', CREDIT));
    const table = element('table', 'ex-table');
    const head = element('thead'), row = element('tr');
    for (const title of ['Month', unit]) { const th = element('th', '', title); th.scope = 'col'; row.append(th); }
    head.append(row); table.append(head);
    const body = element('tbody');
    months.forEach((month, j) => {
      const tr = element('tr'), th = element('th', '', month.long);
      th.scope = 'row'; tr.append(th, element('td', '', number(series[j], 2))); body.append(tr);
    });
    table.append(body); wrapper.append(fold('Read monthly values', table));
    return wrapper;
  }
  function row(title, word, kind) {
    const node = element('section', 'ex-row');
    const heading = element('div', 'ex-row-heading');
    heading.append(element('h4', '', title), badge(word, kind));
    node.append(heading);
    return node;
  }
  function namedDistance(i, path) {
    return `${get(`${path}.name`, i) ?? 'unknown'} · ${quantity(get(`${path}.km`, i), 'km')}`;
  }
  function powerSummary(i) {
    return ['solar', 'wind', 'geothermal'].map(kind => `${kind}: ${get(`power.${kind}.class`, i) ?? 'unknown'}`).join(' · ');
  }
  function steadySummary(i) {
    return ['volcanic', 'human', 'small_tremors'].map(kind => get(`steady.${kind}.class`, i) ?? 'unknown').join(' · ');
  }
  const separateSummary = api.addCardSection.length >= 4;
  function powerCard(i, id) {
    const card = element('div', 'ex-card');
    if (!separateSummary) card.append(element('p', 'ex-summary', powerSummary(i)));
    card.append(element('p', 'ex-disclaimer', `Each class is a ${ESTIMATE}.`));
    card.append(element('p', 'ex-small', 'The solar and wind figures come from a model with large grid boxes. One box contains this area.'));
    const solar = row('Solar', get('power.solar.class', i), 'solar');
    solar.append(element('p', 'ex-value', quantity(get('power.solar.sun_kwh_m2_day_year', i), 'kWh/m²/day', 2)));
    solar.append(element('p', 'ex-small', 'This is the yearly mean sunlight on level ground.'));
    solar.append(element('p', '', sunless(i)));
    solar.append(element('p', 'ex-small', `Panel yield estimate: ${quantity(get('power.solar.panel_kwh_per_kw_day_year', i), 'kWh/day per kW of panels', 2)}.`));
    solar.append(monthStrip(get('power.solar.sun_kwh_m2_day', i), 'Monthly sunlight on level ground', 'kWh/m²/day'), caveat('solar'));
    const wind = row('Wind', get('power.wind.class', i), 'wind');
    wind.append(element('p', 'ex-value', quantity(get('power.wind.power_w_m2', i), 'W/m² of rotor area', 0)));
    wind.append(element('p', 'ex-small', 'This is the power in the wind. A turbine gets only a part of it.'));
    wind.append(element('p', '', `Yearly mean wind: ${quantity(get('power.wind.ws50m_ms_year', i), 'm/s', 2)}.`));
    // Height is encoded in the source field name and described in its metadata.
    const height = data.fields['power.wind.ws50m_ms']?.height_m;
    wind.append(monthStrip(get('power.wind.ws50m_ms', i), height ? `Monthly wind at ${number(height, 0)} m` : 'Monthly wind above the ground', 'm/s'), caveat('wind'));
    const geo = row('Geothermal', get('power.geothermal.class', i), 'geothermal');
    geo.append(element('p', 'ex-value', quantity(get('power.geothermal.plant.km', i), 'km to the nearest active plant')));
    geo.append(element('p', '', namedDistance(i, 'power.geothermal.plant')));
    geo.append(element('p', 'ex-small', `Nearest volcano with a recent eruption: ${namedDistance(i, 'power.geothermal.volcano_since_1990')}.`));
    geo.append(caveat('geothermal'));
    card.append(solar);
    const low = element('section', 'ex-low-sun');
    const table = power.clear_sky_low_sun_table?.[id];
    const clear = get(`power.low_sun.${id}.clear_sky_w_m2`, i)?.[0];
    const cloudy = get(`power.low_sun.${id}.w_m2`, i)?.[0];
    const share = get(`power.low_sun.${id}.share_of_moon`, i)?.[0];
    low.append(element('h4', '', 'A panel under the same low Sun'));
    low.append(element('p', '', `${target(id)?.name ?? 'Lunar region unknown'} · Sun ceiling ${quantity(table?.ceiling_deg, 'degrees', 2)}.`));
    const stats = element('dl', 'ex-low-values');
    const moon = table?.moon_w_m2;
    for (const [label, value, ratio] of [['Clear air', clear, finite(clear) && finite(moon) && moon > 0 ? clear / moon : null], ['Typical cloud here', cloudy, share]]) {
      const group = element('div'); group.append(element('dt', '', label), element('dd', '', quantity(value, 'W/m²', 0)), element('dd', 'ex-small', finite(ratio) ? `${percentage(ratio)} of the Moon` : 'Moon share unknown')); stats.append(group);
    }
    low.append(stats, element('p', 'ex-small', 'The panel faces the Sun at the Sun ceiling of the lunar region. The cloud figure is the mean during the best ten-day periods.'));
    low.append(caveat('low_sun')); card.append(low, wind, geo);
    return card;
  }
  function list(values, emptyText) {
    if (!Array.isArray(values)) return element('p', 'ex-small', 'unknown');
    if (!values.length) return element('p', 'ex-small', emptyText);
    const node = element('ul', 'ex-effects');
    for (const value of values) node.append(element('li', '', value));
    return node;
  }
  function steadyCard(i) {
    const card = element('div', 'ex-card');
    if (!separateSummary) card.append(element('p', 'ex-summary', steadySummary(i)));
    card.append(element('p', 'ex-disclaimer', `Each class is a ${ESTIMATE}.`));
    const volcanic = row('Volcanic', get('steady.volcanic.class', i));
    volcanic.append(list(get('steady.volcanic.effects', i), 'These rules predict no steady volcanic effects.'));
    const deciding = get('steady.volcanic.decided_by.name', i) != null;
    const volcanoPath = `steady.volcanic.${deciding ? 'decided_by' : 'nearest_erupted_since_1990'}`;
    volcanic.append(element('p', '', `${deciding ? 'Volcano that sets this class' : 'Nearest volcano with a recent eruption'}: ${namedDistance(i, volcanoPath)}.`));
    const eruptionYears = get(`${volcanoPath}.years_erupting_since_1990`, i);
    volcanic.append(element('p', 'ex-small', `The data lists eruptions in ${number(eruptionYears, 0)} calendar ${eruptionYears === 1 ? 'year' : 'years'} from ${year(recentYear)} onward.`));
    volcanic.append(element('p', 'ex-small', `Last listed eruption year: ${year(get(`${volcanoPath}.last_eruption_year`, i))}.`));
    if (get('steady.volcanic.young_volcanic_ground', i) === true || get('steady.volcanic.young_volcanic_ground', i) === 1)
      volcanic.append(element('p', 'ex-useful', 'Young volcanic ground can represent basalt soil.'));
    volcanic.append(caveat('volcanic'));
    const human = row('Human', get('steady.human.class', i));
    human.append(list(get('steady.human.effects', i), 'These lists show no human disturbance.'));
    human.append(element('h5', '', 'What decided the class'));
    human.append(list(get('steady.human.why', i), 'None of the disturbance rules matched.'));
    human.append(element('p', 'ex-small', `Nearest settlement: ${namedDistance(i, 'steady.human.nearest_settlement')}.`));
    const roadPath = 'steady.human.nearest_main_road_or_railway';
    const roadDistance = get(`${roadPath}.km`, i), roadLimit = get(`${roadPath}.none_within_km`, i);
    human.append(element('p', 'ex-small', finite(roadLimit) && !finite(roadDistance)
      ? `The lists show no main road or railway within ${quantity(roadLimit, 'km', 0)}.`
      : `Nearest main road or railway: ${quantity(roadDistance, 'km')}.`));
    human.append(element('p', 'ex-small', `Nearest airfield: ${namedDistance(i, 'steady.human.nearest_airfield')}.`));
    human.append(element('p', 'ex-small', `Nearest airfield with scheduled flights: ${namedDistance(i, 'steady.human.nearest_airfield_with_scheduled_flights')}.`));
    if (get('steady.human.help_within_reach', i) === true || get('steady.human.help_within_reach', i) === 1) {
      human.append(element('p', 'ex-useful', 'Help is within reach.'));
      human.append(list(get('steady.human.help_within_reach_why', i), ''));
    }
    human.append(caveat('human'));
    const from = get('steady.small_tremors.source', i);
    const tremors = row('Small tremors', get('steady.small_tremors.class', i) ?? get('tremors.verdict', i));
    const catalogueUsed = from === 'catalogue' || (from == null && get('tremors.verdict', i) != null);
    tremors.append(element('p', 'ex-source-tag', catalogueUsed ? 'from the earthquake catalogue'
      : from ? 'rough estimate: the catalogue cannot detect small tremors here' : 'source unknown'));
    if (catalogueUsed) {
      const radius = catalogue.fields?.small_per_year_100km?.match(/\d+(?= km)/)?.[0];
      tremors.append(element('p', '', `Catalogued events per year${radius ? ` within ${radius} km` : ''}: ${number(get('tremors.small_per_year_100km', i), 2)}.`));
      tremors.append(element('p', 'ex-small', `Years with events: ${number(get('tremors.years_with_events_100km', i), 0)}. Catalogue period: ${catalogue.years ?? 'unknown'}.`));
    } else {
      tremors.append(list(get('steady.small_tremors.our_estimate_why', i), 'The data lists no trigger for this estimate.'));
      const count = get('tremors.catalogued_anyway_100km.events', i);
      if (finite(count)) {
        const radius = catalogue.fields?.catalogued_anyway_100km?.match(/\d+(?= km)/)?.[0];
        tremors.append(element('p', 'ex-evidence', `The catalogue still lists ${number(count, 0)} larger events${radius ? ` within ${radius} km` : ' nearby'}.`));
        tremors.append(element('p', 'ex-small', `Smallest listed magnitude: ${number(get('tremors.catalogued_anyway_100km.smallest_magnitude', i))}. This is not a rate of small tremors.`));
      }
    }
    tremors.append(caveat(catalogueUsed ? 'catalogue' : 'small_tremors'));
    card.append(volcanic, human, tremors); return card;
  }
  function lowSunChart() {
    const block = element('section', 'ex-block');
    block.append(element('p', 'ex-eyebrow', 'The light is alike. The power differs.'), element('h3', '', 'How much power does the low Sun give?'));
    block.append(fold('How to read this', paragraphs(['These bars compare power for the same panel on Earth and the Moon. Each panel faces the Sun. Earth has clear air.'])));
    const chart = element('div', 'ex-comparison');
    const entries = Object.entries(power.clear_sky_low_sun_table || {});
    for (const [id, entry] of entries) {
      const line = element('div', 'ex-comparison-row'); line.dataset.target = id;
      const header = element('div', 'ex-comparison-label');
      header.append(element('strong', '', target(id)?.name ?? entry.name), element('span', 'ex-small', `${quantity(entry.ceiling_deg, 'degrees', 2)} Sun ceiling`));
      const track = element('div', 'ex-comparison-track');
      if (finite(entry.share_of_moon)) {
        const bar = element('span', 'ex-comparison-fill');
        bar.style.width = `${entry.share_of_moon * 100}%`;
        track.append(bar);
      } else track.append(element('span', 'ex-unknown', '?'));
      track.setAttribute('aria-hidden', 'true');
      line.append(header, element('p', 'ex-comparison-value', `${quantity(entry.at_ceiling_w_m2, 'W/m²')} · ${percentage(entry.share_of_moon)} of the Moon`), track);
      chart.append(line);
    }
    block.append(chart);
    if (entries.length > 5) {
      const more = element('button', 'btn ex-show-all', 'Show all');
      more.type = 'button'; more.setAttribute('aria-expanded', 'false');
      const setExpanded = expanded => {
        [...chart.children].forEach((line, index) => { line.hidden = !expanded && index >= 5; });
        more.textContent = expanded ? 'Show fewer' : 'Show all';
        more.setAttribute('aria-expanded', String(expanded));
      };
      more.addEventListener('click', () => setExpanded(more.getAttribute('aria-expanded') !== 'true'));
      setExpanded(false); block.append(more);
    }
    if (!entries.length) block.append(element('p', 'ex-status', 'The clear-air table is unavailable.'));
    else block.append(element('p', 'ex-small', `A full bar shows the panel power on the Moon: ${quantity(entries[0][1].moon_w_m2, 'W/m²', 0)}.`));
    block.append(element('p', 'ex-caption', CREDIT));
    block.append(fold('What this cannot tell us', paragraphs(prose?.caveats?.low_sun || ['The detailed limits are unavailable.'], 'ex-chart-caveat')));
    if (entries.length) {
      const half = element('div', 'ex-copy');
      for (const [id, entry] of entries) half.append(element('p', '', `${target(id)?.name ?? entry.name}: ${quantity(entry.half_ceiling_deg, 'degrees', 3)}; ${quantity(entry.at_half_ceiling_w_m2, 'W/m²')}; ${percentage(entry.share_of_moon_at_half)} of the Moon.`));
      block.append(fold('At half the Sun ceiling', half));
    }
    return block;
  }
  function counts() {
    const block = element('section', 'ex-block');
    block.append(element('h3', '', 'How many areas are in each class?'));
    block.append(element('p', 'ex-disclaimer', `Each class is a ${ESTIMATE}.`));
    block.append(element('p', 'ex-small', `The counts include ${number(api.areaCount, 0)} areas. Areas with an unknown class have a separate count.`));
    const grid = element('div', 'ex-count-grid');
    const groups = [['Solar', 'power.solar.class'], ['Wind', 'power.wind.class'], ['Geothermal', 'power.geothermal.class'],
      ['Volcanic influences', 'steady.volcanic.class'], ['Human influences', 'steady.human.class'], ['Small tremors', 'steady.small_tremors.class']];
    for (const [title, path] of groups) {
      const totals = new Map();
      for (let i = 0; i < api.areaCount; i++) { const word = get(path, i) ?? 'unknown'; totals.set(word, (totals.get(word) || 0) + 1); }
      const schema = data.fields[path];
      const order = path.startsWith('power.') ? Object.keys(power.counts?.[path.split('.')[1]] || {}) : schema?.values || [];
      for (const word of order) if (!totals.has(word)) totals.set(word, 0);
      const group = element('section', 'ex-count-group'); group.append(element('h4', '', title));
      const dl = element('dl', 'ex-counts');
      const words = [...new Set([...order, ...totals.keys()])];
      for (const word of words) {
        const pair = element('div'); pair.append(element('dt', '', word), element('dd', '', number(totals.get(word), 0))); dl.append(pair);
      }
      group.append(dl);
      if (words.length > 5) {
        const more = element('button', 'btn ex-show-all', 'Show all');
        more.type = 'button'; more.setAttribute('aria-expanded', 'false');
        const setExpanded = expanded => {
          [...dl.children].forEach((line, index) => { line.hidden = !expanded && index >= 5; });
          more.textContent = expanded ? 'Show fewer' : 'Show all';
          more.setAttribute('aria-expanded', String(expanded));
        };
        more.addEventListener('click', () => setExpanded(more.getAttribute('aria-expanded') !== 'true'));
        setExpanded(false); group.append(more);
      }
      grid.append(group);
    }
    block.append(grid); return block;
  }
  function rules() {
    const block = element('details', 'ex-block ex-rules');
    block.append(element('summary', '', 'The rules that we used'));
    block.append(element('p', 'ex-disclaimer', 'These are rough estimates by our own rules. They are not measurements or engineering studies.'));
    if (!prose) block.append(element('p', 'ex-status', 'The file with the rules in plain words is unavailable.'));
    for (const group of prose?.rule_groups || []) block.append(fold(group.title, paragraphs(group.paragraphs)));
    const comparisons = element('div', 'ex-comparisons-copy');
    for (const item of prose?.comparisons || []) {
      const section = element('section'); section.append(element('h4', '', item.title), paragraphs(item.paragraphs)); comparisons.append(section);
    }
    block.append(fold('The Moon and Mars compared with Earth', comparisons));
    return block;
  }
  const heading = element('header', 'section-head ex-section-head');
  const finding = element('p', 'finding ex-finding');
  const headingText = element('div');
  headingText.append(element('p', 'eyebrow', 'Go deeper'), element('h2', '', 'What power and steady influences can we expect?'), finding);
  heading.append(headingText);
  root.replaceChildren(heading);
  root.append(element('p', 'ex-intro', 'Use these estimates with the list of low Sun areas to plan field work.'));
  for (const missing of data.missing_inputs || []) root.append(element('p', 'ex-status', `Missing input: ${typeof missing === 'string' ? missing : missing.file ?? missing.name}. Its figures are unknown.`));
  root.append(lowSunChart(), counts(), rules());
  const registrations = [
    api.addCardSection('extra-power', 'Power here', powerCard, powerSummary),
    api.addCardSection('extra-steady', 'Steady influences here', steadyCard, steadySummary),
    api.addListNote(i => `Geothermal ${get('power.geothermal.class', i) ?? 'unknown'} · Wind ${get('power.wind.class', i) ?? 'unknown'} · ${ESTIMATE}`),
    api.addListFilter('quiet', 'Undisturbed and quiet only', i => get('steady.human.class', i) === 'undisturbed as far as our lists show'
      && get('steady.volcanic.class', i) === 'none expected')
  ];
  cleanups.push(...registrations);
  const update = state => {
    const entry = power.clear_sky_low_sun_table?.[state.target];
    finding.textContent = finite(entry?.share_of_moon)
      ? `At the Sun ceiling for ${target(state.target)?.name ?? 'this lunar region'}, an Earth panel receives approximately ${percentage(entry.share_of_moon)} of the Moon’s power in clear air.`
      : 'The comparison of panel power for this lunar region is unknown.';
    for (const line of root.querySelectorAll('.ex-comparison-row')) {
      if (line.dataset.target === state.target) line.setAttribute('aria-current', 'true');
      else line.removeAttribute('aria-current');
    }
  };
  cleanups.push(api.onState(update)); update(api.getState());
  return { destroy };
}
