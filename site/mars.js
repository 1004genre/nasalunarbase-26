/* Mount with: import { mountMars } from './mars.js'; mountMars(element, { theme: 'dark' }).
 * Returns { destroy() }; options.api shares the page's Mars state and data cache.
 * Loads local Mars data, Moon area ids and licence metadata,
 * relative to this module, after mountMars is called. No images or remote services are loaded.
 */

const CAPTION = 'Drawn by code from open data; the code was written with AI assistance.';
const GOALS = [['landscape', 'Landscape'], ['environment', 'Environment'], ['full', 'All factors together']];
const FACTORS = [['terrain', 'Landscape slopes'], ['dry', 'Dryness'], ['cold', 'Cold'], ['bare', 'Bare ground'], ['sun', 'Noon Sun height']];
const finite = value => typeof value === 'number' && Number.isFinite(value);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const number = (value, unit = '', digits = 2, fixed = false) => finite(value) ? `${value.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: fixed ? digits : 0 })}${unit}` : 'unknown';
const scoreNumber = value => number(value, '', 2, true);
const text = value => value == null || value === '' ? 'unknown' : String(value);
const coordinate = (value, positive, negative) => finite(value) ? `${number(Math.abs(value))}° ${value < 0 ? negative : positive}` : 'unknown';
const position = (lat, lon) => `${coordinate(lat, 'N', 'S')}, ${coordinate(lon, 'E', 'W')}`;
const siteLists = site => Array.isArray(site.lists) ? site.lists.filter(list => typeof list === 'string' && list.trim()) : [];
// Keep these list groups in step with the page's destination control.
const siteGroup = site => ['NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones']
  .find((name, i) => siteLists(site).some(tag => i === 0 ? /NASA landing sites?/i.test(tag) : i === 1 ? /2021/.test(tag) : /2015/.test(tag))) || 'Mars';

// Keep stored wording intact, including its cautions and source credits.
function shortProse(value) {
  return value == null || value === '' ? 'unknown' : String(value);
}

function safeURL(value) {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
function link(url, label) {
  const href = safeURL(url);
  return href ? `<a href="${escapeHTML(href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(label)}</a>` : escapeHTML(label);
}
function facts(rows) {
  return `<dl>${rows.map(([label, value, note]) => `<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}${note ? `<small>${escapeHTML(shortProse(note))}</small>` : ''}</dd></div>`).join('')}</dl>`;
}
function scoreColor(score, surface = 'var(--surface, #111620)', mars = 'var(--mars, #e2693b)') {
  return `color-mix(in srgb, ${mars} ${20 + Math.max(0, Math.min(1, score)) * 80}%, ${surface})`;
}

async function squareStore(manifest, load) {
  if (manifest.count !== manifest.ids.length) throw new Error('Square order differs.');
  const squares = manifest.ids.map(id => ({ id, sites: {} }));
  const methods = { int8: ['getInt8', 1], uint8: ['getUint8', 1], uint16: ['getUint16', 2], uint32: ['getUint32', 4], int16: ['getInt16', 2], int32: ['getInt32', 4], float32: ['getFloat32', 4], float64: ['getFloat64', 8] };
  const views = new Map(), siteJobs = new Map();
  async function decode(entries) {
    await Promise.all([...new Set(entries.map(([, column]) => column.file || manifest.file))].map(async file => {
      if (!views.has(file)) views.set(file, new DataView(await load(file)));
    }));
    for (const [name, column] of entries) {
      const view = views.get(column.file || manifest.file), [method, bytes] = methods[column.type] || [];
      if (!method || !finite(column.scale) || column.scale <= 0 || !Number.isInteger(column.offset) || column.offset < 0
        || column.offset + manifest.count * bytes > view.byteLength) throw new Error('Invalid square data layout.');
      const path = name.split('.');
      const parents = path.slice(0, -1), key = path.at(-1);
      for (let index = 0; index < manifest.count; index++) {
        const raw = view[method](column.offset + index * bytes, true);
        let target = squares[index];
        for (const parent of parents) target = target[parent] ||= {};
        target[key] = raw === column.unknown || !finite(raw) ? null : raw / column.scale;
      }
    }
  }
  const entries = Object.entries(manifest.columns);
  await decode(entries.filter(([name]) => !name.startsWith('sites.')));
  for (const square of squares) square.region = square.region == null ? null : manifest.regions[square.region];
  const ensureSite = id => {
    if (!siteJobs.has(id)) siteJobs.set(id, decode(entries.filter(([name]) => name.startsWith(`sites.${id}.`))).then(() => {
      for (const square of squares) {
        const site = square.sites[id] ||= {};
        site.best_months = site.best_months_count == null ? null : Array.from({ length: site.best_months_count }, (_, month) => {
          const value = site[`best_month_${month}`];
          return value == null ? null : manifest.months[value];
        });
      }
    }).catch(error => { siteJobs.delete(id); throw error; }));
    return siteJobs.get(id);
  };
  return { squares, ensureSite };
}

// Extra columns use the same square order as the main manifest. Decode only the open card.
function extraReader(manifest, buffer, ids) {
  if (!manifest || !buffer) return () => ({});
  const layout = manifest.squares;
  if (layout.count !== ids.length || layout.ids.some((id, index) => id !== ids[index])) throw new Error('Extra square order differs.');
  const view = new DataView(buffer);
  const methods = { int8: ['getInt8', 1], uint8: ['getUint8', 1], uint16: ['getUint16', 2], uint32: ['getUint32', 4], int16: ['getInt16', 2], int32: ['getInt32', 4], float32: ['getFloat32', 4], float64: ['getFloat64', 8] };
  const columns = Object.entries(layout.columns).map(([path, column]) => {
    const [method, bytes] = methods[column.type] || [];
    if (!method || column.offset + layout.count * bytes > buffer.byteLength) throw new Error('Invalid extra data layout.');
    return { path: path.split('.'), column, method, bytes };
  });
  return index => {
    const result = {};
    for (const { path, column, method, bytes } of columns) {
      const raw = view[method](column.offset + index * bytes, true);
      const value = raw === column.unknown || !Number.isFinite(raw) ? null : column.lookup ? column.lookup[raw] : raw / column.scale;
      let target = result;
      for (const key of path.slice(0, -1)) target = target[key] ||= {};
      target[path.at(-1)] = value;
    }
    return result;
  };
}

const EXTRA_KIND = { nasa: 'NASA model, coarse grid', map: 'coarse map', list: 'list of settlements', estimate: 'rough estimate by our own rule', catalogue: 'earthquake catalogue' };
const yesNo = value => value === true ? 'yes' : value === false ? 'no' : 'unknown';
const extraWords = value => value == null || value === '' ? 'unknown' : shortProse(Array.isArray(value) ? value.join('; ') : value);
const extraNote = value => value ? `<p class="mars-note">${escapeHTML(shortProse(value))}</p>` : '';
function extraRow(label, value, kind, note = '') {
  return `<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}<small class="mars-kind tag">${escapeHTML(kind)}</small>${note ? `<small>${escapeHTML(shortProse(note))}</small>` : ''}</dd></div>`;
}
function extraGroup(title, summary, rows, notes = '') {
  return `<details class="mars-extra-group fold"><summary><span>${escapeHTML(title)}</span><small>${escapeHTML(summary)}</small></summary><div class="mars-extra-body"><dl>${rows.join('')}</dl>${notes}</div></details>`;
}
function extraSquareCard(extra, manifest) {
  if (!manifest) return '<p class="mars-note">Extra figures are unavailable. The scores are still available.</p>';
  const meta = manifest.input_meta || {};
  const env = extra.mars_environment || {}, power = extra.mars_power || {}, climate = extra.mars_power_extra || {};
  const rock = extra.mars_rock_frozen?.rock || {}, frozen = extra.mars_rock_frozen?.permafrost || {};
  const ground = extra.mars_ground || {}, estimates = extra.mars_estimates || {};
  const steady = extra.mars_steady_effects || {}, tremors = extra.mars_tremors || {}, hazards = extra.mars_hazards_people || {};
  const { nasa, map, list, estimate, catalogue } = EXTRA_KIND;
  const from = source => (...args) => meta[source] ? extraRow(...args) : '';
  const skyRow = from('mars_environment'), powerRow = from('mars_power'), climateRow = from('mars_power_extra');
  const rockRow = from('mars_rock_frozen'), groundRow = from('mars_ground'), estimateRowValue = from('mars_estimates');
  const steadyRow = from('mars_steady_effects'), tremorRow = from('mars_tremors'), hazardRow = from('mars_hazards_people');
  const siteDistance = item => item ? `${text(item.name)} · ${number(item.km, ' km')}` : 'unknown';
  const best = (value, month, unit) => finite(value) ? `${number(value, unit)} · ${month || 'month unknown'}` : 'unknown';
  const rules = (meta.mars_estimates?.rules || []);
  const estimateRow = (id, label, note = '') => estimateRowValue(label, extraWords(estimates[id]?.estimate), estimate, note || meta.mars_estimates?.what_it_is_not?.[id]);
  const groups = [];
  if (meta.mars_environment || meta.mars_power) groups.push(extraGroup('Sky and power',
    `Sunlight ${number(env.sun_kwh_m2_day_year, ' kWh/m²/day')} · solar ${text(power.solar?.class)} · wind ${text(power.wind?.class)}`,
    [
      skyRow('Sunlight on level ground · yearly', number(env.sun_kwh_m2_day_year, ' kWh/m²/day'), nasa),
      skyRow('Sunlight · brightest month', best(env.sun_best_month_kwh_m2_day, env.sun_best_month, ' kWh/m²/day'), nasa),
      skyRow('UV index · yearly', number(env.uv_index_year, ' index'), nasa, 'This mean includes the day and the night.'),
      skyRow('UV index · highest month', best(env.uv_best_month_index, env.uv_best_month, ' index'), nasa, 'This mean includes the day and the night.'),
      skyRow('UV index · brightest hour of the highest month', best(env.uv_brightest_hour_max, env.uv_brightest_hour_month, ' index'), nasa),
      skyRow('Clear-sky days', number(env.clear_days_year, ' days/year'), nasa, meta.mars_environment?.parameters?.CLRSKY_DAYS?.definition_in_the_service),
      ...(!finite(env.clear_days_year) ? [skyRow('Alternative · sunlight at the ground', number(env.clearness_index_year, ' fraction'), nasa, 'This alternative is a fraction of sunlight. It is not a count of clear days.')] : []),
      skyRow('Haze · yearly', number(env.aod_550_year, ' optical depth'), nasa, 'This value includes all fine particles in the air, not only dust.'),
      powerRow('Solar class', text(power.solar?.class), estimate),
      powerRow('Panel yield', number(power.solar?.panel_kwh_per_kw_day_year, ' kWh/kW/day'), estimate, meta.mars_power?.what_it_is_not?.solar),
      powerRow('Wind class', text(power.wind?.class), estimate),
      powerRow('Wind at 50 m', number(power.wind?.ws50m_ms_year, ' m/s'), nasa),
      powerRow('Power carried by wind', number(power.wind?.power_w_m2, ' W/m²'), estimate, 'This value is power per rotor area. It is not turbine output.'),
      powerRow('Geothermal class', text(power.geothermal?.class), estimate, meta.mars_power?.what_it_is_not?.geothermal),
      powerRow('Nearest geothermal plant', siteDistance(power.geothermal?.plant), 'list of power plants'),
      powerRow('Nearest volcano with a recent eruption', siteDistance(power.geothermal?.volcano_since_1990), 'volcano catalogue'),
      powerRow('Nearest Holocene volcano', siteDistance(power.geothermal?.holocene_volcano), 'volcano catalogue')
    ], extraNote(meta.mars_environment?.uv_rule)));
  if (meta.mars_ground || meta.mars_rock_frozen || meta.mars_estimates) groups.push(extraGroup('Ground',
    `${text(rock.class)} · relief ${number(ground.relief_m, ' m')}`,
    [
      rockRow('Rock class', text(rock.class), map, rock.box === 'neighbour' ? 'This data comes from the box next to this one.' : ''),
      rockRow('Volcanic rock', yesNo(rock.volcanic), map), rockRow('Basalt and related volcanic rock', yesNo(rock.basic_volcanic), map),
      rockRow('Loose sediment', yesNo(rock.loose_sediment), map),
      groundRow('Median slope', number(ground.median_slope_deg, '°', 1, true), map, ground.why_null),
      groundRow('Upper slope', number(ground.p90_slope_deg, '°', 1, true), map, meta.mars_ground?.fields?.p90_slope_deg),
      groundRow('Relief', `${number(ground.relief_m, ' m')} · ${text(ground.relief_class)}`, map, meta.mars_ground?.fields?.relief_m),
      estimateRow('rockiness', 'Rockiness'),
      estimateRowValue('How fast the ground heats and cools', text(meta.mars_estimates?.heat_response_reads?.[estimates.heat_response?.estimate] || estimates.heat_response?.estimate), estimate, meta.mars_estimates?.what_it_is_not?.heat_response),
      estimateRow('mineral_family', 'Mineral family'), estimateRow('sand_dust', 'Movement of sand and dust'),
      estimateRow('ilmenite', 'Rock with ilmenite')
    ], extraNote(meta.mars_ground?.fields?.median_slope_deg)));
  if (meta.mars_power_extra || meta.mars_rock_frozen || meta.mars_estimates) groups.push(extraGroup('Climate and below the ground',
    `Daily temperature range ${number(climate.t2m_range_c_year, ' °C', 0)} · permafrost ${text(frozen.zone)}`,
    [
      climateRow('Daily air temperature range · yearly', number(climate.t2m_range_c_year, ' °C', 0), nasa, 'This value describes the air above the ground. It does not describe the ground surface.'),
      climateRow('Surface brightness (albedo) · yearly', number(climate.albedo_year, ' fraction'), nasa, 'The source gives the yearly value. Near the poles, the value includes only the months with sunlight.'),
      climateRow('Soil wetness · yearly', number(climate.soil_wetness_top_year, ' fraction'), nasa,
        climate.soil_wetness_ice_flag === true ? 'Ice flag: the model grid point is ice. This value does not mean wet soil.' : meta.mars_power_extra?.fields?.soil_wetness_top?.service_definition),
      climateRow('Wind at 10 m · yearly', number(climate.wind_10m_ms_year, ' m/s'), nasa),
      estimateRow('topsoil_water', 'Water in the top soil'),
      estimateRowValue('Ground ice', text(estimates.topsoil_water?.ground_ice), estimate, estimates.topsoil_water?.figures?.ground_ice_basis),
      rockRow('Permafrost zone', text(frozen.zone), map, frozen.note),
      rockRow('Permafrost probability', number(frozen.prob_mean, ' fraction'), map),
      estimateRow('frozen_ground_depth', 'Depth to frozen ground', 'Only the class is known. The depth in metres is unknown.')
    ]));
  if (meta.mars_steady_effects || meta.mars_tremors || meta.mars_hazards_people) {
    const volcanic = steady.volcanic || {}, human = steady.human || {}, small = steady.small_tremors || {};
    const steadyRule = name => (meta.mars_steady_effects?.rules || []).find(rule => rule.result === name && rule.outcome === steady[name]?.class)?.when;
    const volcanicBasis = volcanic.decided_by ? siteDistance(volcanic.decided_by) : volcanic.class ? 'No listed volcano met the influence rules.' : 'unknown';
    const humanBasis = human.why?.length ? human.why.join('; ') : human.class ? 'No listed feature met the rules for human influence.' : 'unknown';
    groups.push(extraGroup('Steady influences',
      `${text(volcanic.class)} · ${text(human.class)} · ${text(small.class)}`,
      [
        steadyRow('Volcanic influence', text(volcanic.class), estimate, volcanicBasis),
        steadyRow('Nearest Holocene volcano', siteDistance(volcanic.nearest_holocene || hazards.volcano), 'volcano catalogue'),
        steadyRow('Human influence', text(human.class), estimate, humanBasis),
        steadyRow('Nearest listed settlement', siteDistance(human.nearest_settlement || hazards.people?.nearest), list),
        steadyRow('People listed nearby', number(human.population_within_25km, ' people'), list, meta.mars_steady_effects?.fields?.human?.population_within_25km),
        hazardRow('People in the wider area', number(hazards.people?.population_within_100km, ' people'), list, meta.mars_hazards_people?.record?.people?.population_within_100km),
        steadyRow('Small tremors', text(small.class), small.source === 'catalogue' ? catalogue : estimate, small.source_words || small.source),
        steadyRow('What decided the tremor class', small.source === 'catalogue' ? text(tremors.verdict) : extraWords(small.our_estimate_why), small.source === 'catalogue' ? catalogue : estimate),
        tremorRow('Catalogue coverage', text(tremors.status || small.catalogue_status), catalogue),
        tremorRow('Small tremors nearby', number(tremors.small_per_year_100km, ' events/year'), catalogue, [meta.mars_tremors?.fields?.small_per_year_50km, meta.mars_tremors?.fields?.small_per_year_100km].filter(Boolean).join(' ')),
        tremorRow('Years with small tremors', number(tremors.years_with_events_100km, ' years'), catalogue, meta.mars_tremors?.fields?.years_with_events_100km),
        hazardRow('Large earthquakes nearby', number(hazards.quakes_m5_200km?.count, hazards.quakes_m5_200km?.count === 1 ? ' event' : ' events'), catalogue, meta.mars_hazards_people?.what_this_is_not?.quakes_m5_200km)
      ], extraNote(meta.mars_tremors?.rule_of_thumb?.words) + extraNote(steadyRule('volcanic')) + extraNote(steadyRule('human')) + extraNote(meta.mars_steady_effects?.fields?.human?.is_not)));
  }
  const ruleDetails = rules.length ? `<details class="mars-sources fold"><summary>Rules behind the rough estimates</summary>${rules.map(rule => `<h4>${escapeHTML(rule.name)}</h4>${extraNote(rule.rule)}${extraNote(rule.note)}`).join('')}</details>` : '';
  return `<div class="mars-extras">${groups.join('')}${ruleDetails}<p class="mars-note">These extra figures do not change the scores.</p></div>`;
}

function planetExtraCard(manifest, siteId) {
  const factors = manifest?.planet_factors?.factors;
  if (!factors) return '<p class="mars-note">Mars-only figures are unavailable.</p>';
  const related = { thermal_inertia: 'How fast the ground heats and cools', rock_abundance: 'Rockiness', hydrogen: 'Water in the top soil', ice_depth: 'Depth to frozen ground', surface_activity: 'Movement of sand and dust', quakes: 'Small tremors', albedo: 'Surface brightness (albedo)', daily_temperature_swing: 'Daily air temperature range' };
  const rows = factors.filter(factor => factor.mars?.[siteId]).map(factor => {
    const item = factor.mars[siteId];
    const digits = factor.id === 'daily_temperature_swing' ? 0 : 2;
    const value = Array.isArray(item.value) ? item.value.map(value => number(value, '', digits)).join(' to ') : number(item.value, '', digits);
    const unit = factor.unit?.includes('Mars:') ? factor.unit.split('Mars:').at(-1).trim() : factor.unit;
    const display = item.value == null ? 'We found no public figure for this site.' : `${value} ${unit || ''}`;
    const proxy = ['thermal_inertia', 'rock_abundance', 'hydrogen', 'ice_depth', 'surface_activity'].includes(factor.id);
    const comparison = proxy ? `These files have no open Earth data for this quantity. Earth card: ${related[factor.id]}, a rough estimate.` : `Earth card: ${related[factor.id] || 'no open Earth data'}.`;
    const note = factor.id === 'daily_temperature_swing'
      ? `Ground temperature range: ${number(item.ground?.mean_K, ' K', 0)}. Air temperature range: ${number(item.air_2m?.mean_K, ' K', 0)}. Compare Earth air with Mars air.`
      : item.note;
    return `<article><h4>${escapeHTML(factor.name)}</h4><p>${escapeHTML(display)}</p>${item.kind ? `<p class="mars-kind">${escapeHTML(item.kind)}${item.scope ? ` · ${escapeHTML(item.scope)}` : ''}</p>` : ''}${item.value_text ? extraNote(`Published context: ${item.value_text}`) : ''}${extraNote(note)}${extraNote(comparison)}${item.url ? `<p>${link(item.url, shortProse(item.source || 'Source'))}</p>` : ''}</article>`;
  });
  return `<details class="mars-extra-group mars-planet-extra fold"><summary><span>Figures that exist only on Mars</span><small>These figures come from measurements, models and published sources. Each figure has limits.</small></summary><div class="mars-extra-body">${extraNote('The source file does not state which Earth data are available. The Earth files give the related figures below.')}${rows.join('')}</div></details>`;
}

/** Mount an independent Mars section. Importing this module performs no requests. */
export function mountMars(rootElement, options = {}) {
  if (!rootElement || typeof rootElement.append !== 'function') throw new TypeError('A root element is required.');
  const section = document.createElement('section');
  section.className = 'mars-module';
  const api = options.api;
  // The shell keeps its finding hooks; the mounted module supplies the visible head.
  const hasPageHead = !!api && !!rootElement.querySelector(':scope > .section-head');
  if (hasPageHead) rootElement.classList.add('mars-mounted');
  section.setAttribute('aria-label', 'Earth places for Mars');
  section.innerHTML = '<p role="status">Working</p>';
  rootElement.append(section);
  const lifecycle = new AbortController();
  const { signal } = lifecycle;
  let destroyed = false;
  let observer;
  let themeObserver;
  let unsubscribe;
  let frame = 0;
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let redraw = () => {};
  const themeChanged = () => redraw();
  media.addEventListener('change', themeChanged);
  const on = (element, event, handler, config = {}) => element.addEventListener(event, handler, { ...config, signal });
  const files = new Map();
  const load = filename => {
    if (typeof filename !== 'string' || !/^[\w./-]+\.(?:bin|json)$/.test(filename) || filename.startsWith('/') || filename.split('/').includes('..')) return Promise.reject(new Error('Only local data files are allowed.'));
    if (!files.has(filename)) files.set(filename, (async () => {
      if (api) return filename.endsWith('.bin') ? api.loadBin(filename) : api.loadJSON(filename);
      const url = new URL(`./data/${filename}`, import.meta.url);
      const request = target => fetch(target, { signal, credentials: 'same-origin', redirect: 'error' });
      let response;
      if (typeof DecompressionStream === 'function') response = await request(`${url}.gz`);
      if (!response?.ok) response = await request(url);
      if (!response.ok) throw new Error('The Mars data could not be loaded.');
      let buffer = await response.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      if (bytes[0] === 0x1f && bytes[1] === 0x8b) buffer = await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      return filename.endsWith('.bin') ? buffer : JSON.parse(new TextDecoder().decode(buffer));
    })().catch(error => { files.delete(filename); throw error; }));
    return files.get(filename);
  };

  const extras = Promise.all([load('mars_extra.json'), load('mars_extra.bin')]).catch(error => {
    if (error.name === 'AbortError') throw error;
    return [null, null];
  });
  const moonAreas = load('cells.json').catch(() => null);
  const lunarSites = load('moon.json').catch(() => null);
  const sources = load('sources.json').catch(() => null);
  Promise.all([load('mars.json'), load('mars_world.json'), extras, moonAreas, sources, lunarSites]).then(async ([data, world, [extraManifest, extraBinary], cells, credits, lunar]) => {
    if (destroyed) return;
    const store = await squareStore(data.squares, load), { squares } = store;
    const squareById = new Map(squares.map(square => [square.id, square]));
    const indexById = new Map(squares.map((square, index) => [square.id, index]));
    let readExtra = () => ({});
    try { readExtra = extraReader(extraManifest, extraBinary, data.squares.ids); }
    catch { extraManifest = null; }
    let initial = api?.getState() || { msite: options.site, mgoal: options.goal, msquare: options.square };
    const validSite = value => data.sites.some(site => site.id === value) ? value : data.sites[0]?.id;
    const validGoal = value => GOALS.some(([id]) => id === value) ? value : 'full';
    const validSquare = value => squareById.has(value) ? value : null;
    let siteId = validSite(initial.msite);
    while (!destroyed) {
      await store.ensureSite(siteId);
      initial = api?.getState() || initial;
      const latestSite = validSite(initial.msite);
      if (latestSite === siteId) break;
      siteId = latestSite;
    }
    if (destroyed) return;
    let goal = validGoal(initial.mgoal);
    let selectedId = validSquare(initial.msquare);
    let requestNumber = 0, pendingSelection = null;
    const publish = () => {
      if (!api || destroyed) return;
      const state = api.getState();
      const next = { msite: siteId, mgoal: goal, msquare: selectedId || '' };
      if (Object.entries(next).some(([key, value]) => (state[key] ?? '') !== value)) api.setState(next);
    };
    const meta = data.meta;
    const scale = meta.score_scale;
    const SCORE_CAUTION = ['This is not a climate match.', meta.score_caution].filter(Boolean).join(' ');
    const scoreCaution = () => `<small class="mars-score-caution">${escapeHTML(SCORE_CAUTION)}</small>`;
    const compactPass = `First pass · squares approximately ${number(meta.square_km_about)} km wide`;
    // IDs are labels rounded away from some centres. Prefer the coordinate columns used by the page.
    const decimals = value => String(value).split('.')[1]?.length || 0;
    const coordinateScale = field => cells?.units?.[field] === 'hundredths of a degree' ? 100 : null;
    const hasCentres = ['lat', 'lon'].every(field => coordinateScale(field) && cells?.[field]?.length === cells?.ids?.length);
    const unknownCoordinate = Number(String(cells?.unknown).match(/(-?\d+) in the whole-number columns/)?.[1]);
    const areaCoordinates = (cells?.ids || []).map((id, index) => ({
      id,
      values: hasCentres ? ['lat', 'lon'].map(field => {
        const raw = cells[field][index];
        return finite(raw) && raw !== unknownCoordinate ? raw / coordinateScale(field) : null;
      }) : id.split('_').map(Number)
    }));
    const coordinateDigits = areaCoordinates.reduce((digits, area) => Math.max(digits, ...area.values.map(decimals)), decimals(meta.square_deg));
    const precision = 10 ** data.squares.ids.reduce((digits, id) =>
      Math.max(digits, ...id.split('_').slice(-2).map(decimals)), coordinateDigits);
    const squareUnits = Math.round(meta.square_deg * precision);
    const gridKey = (lat, lon) => {
      const latitude = Math.round((lat + 90) * precision);
      const longitude = ((Math.round((lon + 180) * precision) % (360 * precision)) + 360 * precision) % (360 * precision);
      return `${Math.min(Math.ceil(180 * precision / squareUnits) - 1, Math.floor(latitude / squareUnits))}_${Math.floor(longitude / squareUnits)}`;
    };
    const areasBySquare = new Map();
    for (const area of areaCoordinates) {
      const [lat, lon] = area.values;
      if (!finite(lat) || !finite(lon)) continue;
      const key = gridKey(lat, lon);
      const entry = areasBySquare.get(key);
      if (entry) entry.count++;
      else areasBySquare.set(key, { count: 1, first: area.id, lat });
    }
    const moonLink = square => {
      if (!finite(square.lat) || !finite(square.lon)) return '';
      const areas = areasBySquare.get(gridKey(square.lat, square.lon));
      if (!areas) return '';
      const fragment = new URLSearchParams(location.hash.slice(1));
      for (const key of ['only', 'x', 'y', 'z', 'moon']) fragment.delete(key);
      fragment.set('place', areas.first); fragment.set('go', 'map'); fragment.set('dest', 'moon');
      fragment.set('view', areas.lat < 0 ? 'antarctic' : 'arctic');
      const destination = new URL('./index.html', import.meta.url);
      destination.hash = fragment.toString();
      return `<p class="mars-moon-link">${number(areas.count)} ${areas.count === 1 ? 'area of the Moon part lies' : 'areas of the Moon part lie'} in this square. <a href="${escapeHTML(destination.href)}">Open the first area in the Moon part</a>.</p>`;
    };
    const currentSite = () => data.sites.find(site => site.id === siteId);
    const topPlaces = () => data.best_places?.[siteId]?.[goal] || [];
    const chosenSquare = () => squareById.get(selectedId);
    const shortName = site => site.name.split(',')[0].split(' (')[0];
    const months = values => values == null ? 'unknown' : values.length ? values.map(text).join(', ') : 'No month has a positive calendar score.';
    const pass = `First pass · ${number(meta.square_deg)}° squares (approximately ${number(meta.square_km_about)} km) · Coarser than the Moon part`;
    section.innerHTML = `
      <div class="mars-pass">${escapeHTML(pass)}</div>
      <header class="mars-header section-head">
        <span class="step-number" aria-hidden="true">2</span><div>
        <p class="mars-kicker eyebrow">LuniMartian Atlas / Mars</p>
        <h2>Where does Earth compare with Mars?</h2><p class="mars-finding finding"></p>
        <details class="mars-sources fold"><summary>What this first pass compares</summary><p>This first pass compares Earth places with the landscapes and environments of Mars sites.</p>
        <p>Its squares span ${number(meta.square_deg)} degrees, approximately ${number(meta.square_km_about)} km. They are larger than the areas in the Moon part.</p>
        <p>The scores compare sunlight, ground and climate. A high score does not mean that Earth has the climate of Mars.</p></details>
        </div>
      </header>
      <div class="mars-section" id="mars-site">
        <h3>Which Mars site do you want to compare?</h3>
        <p class="mars-work mars-note" role="status" aria-live="polite" hidden></p>
        <details class="mars-site-picker fold"><summary><span class="mars-site-choice"></span><small>${number(data.sites.length)} Mars sites</small></summary>
          <label class="mars-site-filter-label">Filter Mars sites<input class="mars-site-filter" type="search" autocomplete="off" placeholder="Site name or list"></label>
          <p class="mars-site-count" role="status"></p>
          <div class="mars-site-options">${['NASA landing sites', '2021 shortlist for human landings', '2015 exploration zones', 'Mars'].filter(group => data.sites.some(site => siteGroup(site) === group)).map(group => `<div class="mars-site-group" role="group" aria-label="${escapeHTML(group)}"><h4>${escapeHTML(group)}</h4>${data.sites.filter(site => siteGroup(site) === group).map(site => `<button type="button" class="mars-button mars-site-option" data-site="${escapeHTML(site.id)}" data-search="${escapeHTML([site.name, site.id, ...siteLists(site), site.display_status, site.why].filter(Boolean).join(' ').toLowerCase())}"><span>${escapeHTML(site.name)}</span>${siteLists(site).length ? `<small>${siteLists(site).map(escapeHTML).join(' · ')}</small>` : ''}</button>`).join('')}</div>`).join('')}</div>
        </details>
        <article class="mars-site-card card"></article>
      </div>
      <div class="mars-section mars-goals" id="mars-goal">
        <h3>What matters most?</h3>
        <div class="mars-picker" role="group" aria-label="Comparison goal">${GOALS.map(([id, label]) => `<button type="button" class="mars-button btn chip" data-goal="${id}">${label}</button>`).join('')}</div>
        <p class="mars-formula"></p>
        ${scoreCaution()}
      </div>
      <div class="mars-section mars-search" role="search" aria-label="Find an Earth region">
        <h3>Find an Earth region</h3>
        <label class="mars-search-label">Region name
          <input class="mars-search-input" type="search" autocomplete="off" placeholder="Atacama, Tibet, Antarctica" aria-label="Region name">
        </label>
        <p class="mars-search-help">Each result opens the best square in that region for this Mars site and goal. Equal scores keep the order in the file.</p>
        <p class="mars-search-context"></p>
        <p class="mars-search-status" role="status" aria-live="polite"></p>
        <ul class="mars-search-results"></ul><button type="button" class="mars-button mars-search-all btn" aria-expanded="false" hidden>Show all</button>
      </div>
      <figure class="mars-map-figure card" id="mars-map">
        <h3>Where are the Earth squares?</h3><p class="mars-note">${escapeHTML(compactPass)}</p>
        <div class="mars-map-toolbar" role="group" aria-label="Map controls">
          <button type="button" class="mars-button btn" data-map="in" aria-label="Zoom in">Zoom in</button>
          <button type="button" class="mars-button btn" data-map="out" aria-label="Zoom out">Zoom out</button>
          <button type="button" class="mars-button btn" data-map="reset">Whole world</button>
          <button type="button" class="mars-button btn" data-map="previous">Previous square</button>
          <button type="button" class="mars-button btn" data-map="next">Next square</button>
          <button type="button" class="mars-button btn" data-map="open">Open square</button>
        </div>
        <details class="mars-sources fold"><summary>How to use this map</summary><p>Drag the map to move it. Use the scroll wheel or pinch to change the scale.</p><p>Use the arrow keys to move the map. Use plus or minus to change the scale.</p><p>Press Page Up or Page Down to select a square. Press Enter to open its card. Press Home to see the world.</p></details><p class="mars-map-help">Region names describe rough boxes, not mapped boundaries.</p>
        <div class="mars-map-wrap"><canvas class="mars-map" tabindex="0" role="group" aria-label="World map of Mars comparison scores"></canvas><div class="mars-tooltip" hidden></div></div>
        <div class="mars-legend legend"><div><span class="mars-ramp-title">Goal score</span><div class="mars-ramp"></div><div class="mars-scale"><span>${scoreNumber(scale[0])}</span><span>${scoreNumber(scale[1])}</span></div></div><span class="mars-unknown-key">Grey: score unknown</span></div>${scoreCaution()}
        <p class="mars-map-status" role="status" aria-live="polite"></p>
        <figcaption class="mars-caption">${CAPTION}</figcaption>
      </figure>
      <article class="mars-square-card card" id="mars-square" tabindex="-1" aria-label="Earth square details"></article>
      <div class="mars-section" id="mars-list"><h3>Which places have the highest scores?</h3><p class="mars-note">${escapeHTML(compactPass)}</p><details class="mars-sources fold"><summary>The order of these places</summary><p class="mars-top-note"></p></details><ol class="mars-top-list"></ol><button type="button" class="mars-button mars-show-all btn" aria-expanded="false" hidden>Show all</button><button type="button" class="mars-button mars-download btn">Download this list (CSV)</button><p class="mars-download-status" role="status" aria-live="polite"></p></div>
      <details class="mars-section mars-evidence fold" id="mars-evidence"><summary>What can Earth not copy?</summary><p class="mars-cold-limit"></p><div class="mars-cannot-grid"></div></details>
      <details class="mars-section mars-validation fold"><summary>Where do known Mars analog sites rank?</summary><div class="mars-validation-note"></div><div class="mars-validation-results"></div></details>
      <details class="mars-section fold"><summary>Where are the planetary sites?</summary><div class="mars-locators"></div></details>
      <details class="mars-export-notes fold"><summary>Data and first-pass limits</summary><div></div></details>
      <p class="mars-screen-reader mars-announcement" aria-live="polite"></p>`;

    const $ = selector => section.querySelector(selector);
    const canvas = $('.mars-map');
    const context = canvas.getContext('2d');
    if (!context) throw new Error('This browser cannot draw the Mars map.');
    const tooltip = $('.mars-tooltip');
    const mapStatus = $('.mars-map-status');
    const ramp = $('.mars-ramp');
    ramp.style.background = `linear-gradient(to right, ${scoreColor(0)}, ${scoreColor(1)})`;
    const camera = { zoom: 1, x: 0, y: 0 };
    let width = 0;
    let height = 0;
    let plotScale = 1;
    let hoverId = null;
    const pointers = new Map();
    let gesture = null;
    let moved = false;
    let pointerStart = null;
    let canvasWasDragged = false;

    function siteCard() {
      const site = currentSite();
      const sun = site.sun || {};
      const landscape = site.landscape || {};
      const climate = site.climate || {};
      const kind = key => climate.kind_by_field?.[key] || climate.kind || 'Source kind unknown';
      const picture = site.picture;
      const pictureURL = picture && (picture.page || picture.url);
      const sources = (site.sources || []).map(source => `<li>${link(source.url, shortProse(source.what || 'Source'))}</li>`).join('');
      const climateLinks = [...new Set([climate.url, ...(climate.urls || [])])].filter(safeURL).map(url => `<li>${link(url, `Climate source: ${new URL(url).hostname}`)}</li>`).join('');
      $('.mars-site-card').innerHTML = `
        <p class="mars-note">${escapeHTML(compactPass)}</p><div class="mars-site-title"><h3>${escapeHTML(site.name)}</h3><span>${escapeHTML(position(site.lat, site.lon_east))}</span></div>
        <p class="mars-status">${escapeHTML(site.display_status || site.kind)}</p>
        ${siteLists(site).length ? `<p class="mars-note mars-site-tags">${siteLists(site).map(escapeHTML).join(' · ')}</p>` : ''}
        <p class="mars-note">The human landing regions are candidates for study.</p>
        <details class="mars-sources fold"><summary>Why compare this site?</summary><p class="mars-why">${escapeHTML(shortProse(site.why_sentences?.join(' ') || site.why))}</p></details>
        <div class="mars-facts">
          <div><h4>Sun through the Mars year</h4>${facts([
            ['Lowest noon Sun', number(sun.noon_elev_min_deg, '°')], ['Highest noon Sun', number(sun.noon_elev_max_deg, '°')],
            ['Shortest daylight', number(sun.day_length_min_h, ' h')], ['Longest daylight', number(sun.day_length_max_h, ' h')]
          ])}<p class="mars-note">These values use latitude and a flat horizon.</p></div>
          <div><h4>Landscape</h4>${facts([
            ['Median slope', number(landscape.median_slope_deg, '°', 1, true)], ['Upper slope', number(landscape.p90_slope_deg, '°', 1, true)],
            ['Relief', number(landscape.relief_m, ' m')], ['Within-site overlap', scoreNumber(landscape.self_overlap), SCORE_CAUTION]
          ])}<p class="mars-note">Height samples are approximately ${number(meta.height_spacing_km_about ?? meta.slope_baseline_km_about)} km apart. Slopes span approximately ${number(meta.slope_span_km_about)} km. This data cannot show small features near a rover.</p></div>
          <div><h4>Climate and its basis</h4>${facts([
            ['Yearly mean air temperature', number(climate.annual_mean_c, ' °C', 0), kind('annual_mean_c')],
            ['Warm-season daily high', number(climate.warm_season_daily_max_c, ' °C', 0), kind('warm_season_daily_max_c')],
            ['Cold-season daily low', number(climate.cold_season_daily_min_c, ' °C', 0), kind('cold_season_daily_min_c')],
            ['Air pressure', number(climate.pressure_pa, ' Pa', 0), kind('pressure_pa')]
          ])}${climate.citation_note ? `<p class="mars-note mars-climate-citation">${escapeHTML(shortProse(climate.citation_note))}</p>` : ''}</div>
        </div>
        <details class="mars-sources fold"><summary>Sources and methods</summary><p>${escapeHTML(shortProse(sun.how))}</p><p>${escapeHTML(shortProse(climate.source))}</p><ul>${sources}${climateLinks}</ul></details>
        ${safeURL(pictureURL) ? `<p class="mars-picture">${link(pictureURL, picture.title || 'NASA picture of this site')}${picture.credit ? `<br><small>${escapeHTML(picture.credit)}</small>` : ''}</p>` : ''}
        ${planetExtraCard(extraManifest, siteId)}`;
    }

    function renderSquare(focus = false) {
      const square = chosenSquare();
      const card = $('.mars-square-card');
      if (!square) { card.innerHTML = '<h3>Which Earth square do you want to inspect?</h3><p>Select a square on the map or in the list of best places.</p>'; return; }
      const site = square.sites[siteId] || {};
      const gap = site.falls_short || {};
      card.innerHTML = `<p class="mars-note">${escapeHTML(compactPass)}</p><p class="mars-kicker eyebrow">Earth square / ${escapeHTML(GOALS.find(([id]) => id === goal)[1])}</p>
        <h3>${escapeHTML(square.region || 'Region unknown')}</h3><p>${escapeHTML(position(square.lat, square.lon))}</p>${moonLink(square)}
        <p class="mars-square-score">Goal score: <strong>${scoreNumber(site[goal])}</strong>${scoreCaution()}</p>
        <div class="mars-factor-list">${FACTORS.map(([key, label]) => {
          const value = site[key];
          return `<div class="mars-factor"><span>${label}</span><span class="mars-track${finite(value) ? '' : ' mars-track-unknown'}" aria-hidden="true">${finite(value) ? `<i style="width:${Math.max(0, Math.min(1, value)) * 100}%;background:${scoreColor(value)}"></i>` : ''}</span><output>${scoreNumber(value)}</output></div>`;
        }).join('')}</div>
        <p class="mars-caption">${CAPTION}</p>
        <div class="mars-facts">${facts([
          ['Bare share of land', number(square.bare)], ['Yearly temperature', number(square.t2m_year_c, ' °C', 0)],
          ['Yearly rain and snow', number(square.precip_mm_year, ' mm')], ['Air pressure', number(square.pressure_kpa, ' kPa', 1, true)]
        ])}</div>
        <p class="mars-note">Earth climate comes from a model of a grid box, not a weather station at this point.</p>
        <p class="mars-note">In Antarctica, bare ground comes from mapped rock outcrops and is a lower bound.</p>
        <h4>What does this square not copy?</h4><ul class="mars-shortfalls">
          <li>${finite(gap.colder_on_mars_by_c) ? `Mars is ${number(gap.colder_on_mars_by_c, '', 0)} °C colder in the yearly mean.` : 'Yearly temperature gap: unknown.'}</li>
          <li>${finite(gap.times_wetter_than_25_mm) ? `The amount of rain and snow here is ${number(gap.times_wetter_than_25_mm, '', 1)} times the dry reference of ${number(meta.dry_reference_mm)} mm in a year.` : 'Rain and snow gap: unknown.'}</li>
          <li>${finite(gap.pressure_mars_over_square) ? `Mars air pressure is approximately ${number(gap.pressure_mars_over_square * 100, '', 1, true)} percent of this place’s.` : 'Pressure comparison: unknown.'}</li>
        </ul><h4>Best Earth months</h4><p class="mars-months">${escapeHTML(months(site.best_months))}</p>
        <p class="mars-note">The month scores compare cold, rain and snow, and the height of the noon Sun. These months do not have the climate of Mars.</p>
        <details class="mars-sources fold"><summary>How we score the factors and months</summary><ul>${[...FACTORS.map(([key, label]) => [key, label]), ['month', 'Month score'], ['best_months', 'Best months']].map(([key, label]) => `<li>${escapeHTML(shortProse(`${label}: ${meta.formulas?.[key] || 'unknown'}`))}</li>`).join('')}</ul></details>
        ${finite(square.lat) && finite(square.lon) ? `<p>${link(`https://www.openstreetmap.org/?mlat=${square.lat}&mlon=${square.lon}#map=8/${square.lat}/${square.lon}`, 'Open these coordinates in OpenStreetMap')}</p>` : ''}
        ${extraSquareCard(readExtra(indexById.get(square.id)), extraManifest)}`;
      if (focus) card.focus({ preventScroll: false });
    }

    function limitRows(list, control, expanded = false) {
      const rows = [...list.children];
      rows.forEach((row, index) => { row.hidden = !expanded && index >= 5; });
      control.hidden = rows.length <= 5;
      control.setAttribute('aria-expanded', String(expanded));
      control.textContent = expanded ? 'Show five' : 'Show all';
    }
    for (const [list, control] of [['.mars-top-list', '.mars-show-all'], ['.mars-search-results', '.mars-search-all']]) {
      $(control).addEventListener('click', () => limitRows($(list), $(control), $(control).getAttribute('aria-expanded') !== 'true'), { signal: lifecycle.signal });
    }
    function renderTop() {
      $('.mars-download-status').textContent = '';
      $('.mars-download').disabled = !topPlaces().length;
      const tied = currentSite().best_places_tied_at_top?.[goal] ?? meta.best_places_tied_at_top?.[siteId]?.[goal];
      $('.mars-top-note').textContent = goal === 'landscape'
        ? `Squares with the highest score: ${number(tied)}. If scores are equal, the amount of bare ground sets the order. These places are examples with equal scores.`
        : 'The list shows the highest scores among Earth squares. These scores do not measure how much a place is like Mars.';
      $('.mars-top-list').innerHTML = topPlaces().map(place => `<li><button type="button" class="mars-place-button btn btn-ghost" data-square="${escapeHTML(place.id)}"><span class="mars-place">${escapeHTML(place.region || 'Region unknown')}<small>${escapeHTML(position(place.lat, place.lon))}</small></span><span class="mars-score">${scoreNumber(place.score)}</span><small>${escapeHTML(compactPass)}</small>${goal === 'landscape' ? `<small>Squares with this exact score: ${number(place.squares_with_this_score)}.</small>` : ''}<small class="mars-list-months">${escapeHTML(months(place.best_months))}</small></button></li>`).join('') || '<li>No ranked places are available for this goal.</li>';
      limitRows($('.mars-top-list'), $('.mars-show-all'));
    }

    function renderSearch() {
      const query = $('.mars-search-input').value.trim().toLocaleLowerCase('en-US');
      const results = $('.mars-search-results');
      $('.mars-search-context').textContent = `${shortName(currentSite())} · ${GOALS.find(([id]) => id === goal)[1]} · ${compactPass}`;
      if (!query) {
        results.replaceChildren();
        limitRows(results, $('.mars-search-all'));
        $('.mars-search-status').textContent = 'Type a region name to find its best square.';
        return;
      }
      const regions = data.squares.regions.filter(region => region.toLocaleLowerCase('en-US').includes(query));
      const bestByRegion = new Map(regions.map(region => [region, null]));
      for (const square of squares) {
        if (!bestByRegion.has(square.region)) continue;
        const score = square.sites[siteId]?.[goal];
        if (!finite(score)) continue;
        const previous = bestByRegion.get(square.region);
        if (!previous || score > previous.sites[siteId][goal]) bestByRegion.set(square.region, square);
      }
      $('.mars-search-status').textContent = regions.length ? `${number(regions.length)} ${regions.length === 1 ? 'region' : 'regions'}.` : 'No region has that name.';
      results.innerHTML = regions.map(region => {
        const square = bestByRegion.get(region);
        return square ? `<li><button type="button" class="mars-place-button btn btn-ghost" data-search-square="${escapeHTML(square.id)}"><span class="mars-place">${escapeHTML(region)}<small>${escapeHTML(position(square.lat, square.lon))}</small></span><span class="mars-score">${scoreNumber(square.sites[siteId][goal])}</span><small>${escapeHTML(compactPass)}</small></button></li>`
          : `<li>${escapeHTML(region)}<small>No ranked square has a known score for this goal.</small></li>`;
      }).join('');
      limitRows(results, $('.mars-search-all'));
    }

    function downloadList() {
      const rows = topPlaces();
      if (!rows.length) { $('.mars-download-status').textContent = 'No rows are available to download.'; return; }
      const csvValue = value => {
        if (value == null || (typeof value === 'number' && !finite(value))) return '';
        return `"${String(value).replace(/"/g, '""')}"`;
      };
      const columns = [
        ['rank', place => place.rank], ['square_id', place => place.id], ['earth_region', place => place.region],
        ['latitude_deg', place => place.lat], ['longitude_deg', place => place.lon], ['goal_score_unitless', place => place.score],
        ...[...FACTORS, ...GOALS].map(([key]) => [`${key}_score_unitless`, place => place.scores?.[key]]),
        ['bare_land_fraction', place => place.bare], ['yearly_mean_air_temperature_degC', place => place.t2m_year_c],
        ['yearly_precipitation_mm', place => place.precip_mm_year], ['air_pressure_kPa', place => place.pressure_kpa],
        ['mean_elevation_m', place => place.elev_mean_m], ['median_slope_deg', place => place.median_slope_deg],
        ['bare_ground_km2', place => place.bare_km2], ['squares_with_this_score_count', place => place.squares_with_this_score],
        ['best_months', place => place.best_months?.map(month => month ?? '').join('; ')],
        ...data.squares.months.map((month, index) => [`${month}_score_unitless`, place => place.month_scores?.[index]])
      ];
      const notes = [
        'LuniMartian Atlas: this list shows the best places for this Mars site and goal.',
        `Mars site: ${currentSite().name}.`, `Goal: ${GOALS.find(([id]) => id === goal)[1]}.`,
        `First pass: squares of ${meta.square_deg} degree, approximately ${meta.square_km_about} km wide.`,
        meta.climate_caution, meta.score_caution, credits?.licence_line || 'See the page for the licence.'
      ].filter(Boolean);
      const csv = notes.map(note => `# ${String(note).replace(/[\r\n]+/g, ' ')}`).join('\r\n') + '\r\n'
        + columns.map(([label]) => csvValue(label)).join(',') + '\r\n'
        + rows.map(place => columns.map(([, value]) => csvValue(value(place))).join(',')).join('\r\n') + '\r\n';
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `mars-${siteId}-${goal}-first-pass.csv`;
      section.append(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
      $('.mars-download-status').textContent = `${number(rows.length)} rows are ready to download.`;
    }

    function renderCannot() {
      const site = currentSite();
      const coldest = site.factor_summary?.coldest_square || meta.factor_summary?.[siteId]?.coldest_square;
      $('.mars-cold-limit').textContent = coldest
        ? `The coldest ranked square has a yearly mean of ${number(coldest.t2m_year_c, ' °C', 0)}. This Mars site is ${number(coldest.colder_on_mars_by_c, ' °C', 0)} colder.`
        : 'The yearly temperature gap is unknown.';
      $('.mars-cannot-grid').innerHTML = (site.cannot_match || []).map(item => {
        const dose = item.unit === 'mSv per day';
        const unit = dose ? 'µSv per day' : item.unit;
        const display = value => finite(value) ? number(dose ? value * 1000 : value, '', unit === 'Pa' ? 0 : 2) : shortProse(value);
        const ratio = item.number_is?.includes('/');
        return `<article class="card"><h4>${escapeHTML(item.what)}</h4>${facts([
        ['Mars', display(item.mars)],
        ['Earth', display(item.earth)],
        [ratio ? `${item.number_is} (percent)` : item.number_is || 'Comparison', ratio && finite(item.number) ? number(item.number * 100, ' %', 1) : number(item.number)]
      ])}<p class="mars-note">${escapeHTML(shortProse(unit))}</p>
      ${item.note ? `<p>${escapeHTML(shortProse(item.note))}</p>` : ''}
      ${item.source ? `<p class="mars-note">${escapeHTML(shortProse(item.source))}</p>` : ''}
      ${item.url ? `<p>${link(item.url, 'Source')}</p>` : ''}</article>`;
      }).join('') || '<p>No comparison list is available.</p>';
    }

    function renderValidation() {
      const validation = data.validation || {};
      const caution = meta.validation_caution || ['This check shows where known analog sites rank.', 'It does not show that a top square is a better analog than a known site.'];
      $('.mars-validation-note').innerHTML = `<p>${escapeHTML(compactPass)}</p>` + caution.map(line => `<p>${escapeHTML(shortProse(line))}</p>`).join('');
      const tests = [['test_against_all_land', 'Against all land'], ['test_against_bare_squares', 'Against bare squares']];
      const summary = tests.map(([key, label]) => {
        const check = validation[key]?.[siteId]?.[goal] || {};
        return `<div><h4>${label}</h4>${facts([['Share of higher scores, with equal scores shared', scoreNumber(check.auc)], ['Known squares', number(check.known)], ['Control squares', number(check.controls)]])}</div>`;
      }).join('');
      const table = entries => `<div class="mars-table-wrap"><table><thead><tr><th scope="col">Known place</th><th scope="col">Score</th><th scope="col">Percentile</th><th scope="col">Ranked</th></tr></thead><tbody>${entries.map(entry => {
        const check = entry.sites?.[siteId] || {};
        return `<tr><th scope="row">${escapeHTML(entry.named_in_job || entry.name)}${entry.on_square_edge ? '<small>Point on square edge</small>' : ''}</th><td data-label="Score">${scoreNumber(check[goal])}<small>${escapeHTML(compactPass)}</small></td><td data-label="Percentile">${number(check.percentile?.[goal])}</td><td data-label="Ranked">${entry.ranked === true ? 'Yes' : entry.ranked === false ? 'No' : 'unknown'}</td></tr>`;
      }).join('')}</tbody></table></div>`;
      const entries = validation.sites || [];
      const named = entries.filter(entry => entry.named_in_job);
      const other = entries.filter(entry => !entry.named_in_job);
      $('.mars-validation-results').innerHTML = `<div class="mars-facts">${summary}</div>
        <p class="mars-note">Percentile shows the share of ranked squares with lower scores. Equal scores share their rank.</p>
        <p class="mars-note">A place outside the bare ground limit can still have a score. Missing measurements stay unknown.</p>
        ${table(named.length ? named : other)}${named.length && other.length ? `<details class="fold"><summary>More known analog places</summary>${table(other)}</details>` : ''}`;
    }

    function renderLocators() {
      const lunarPoints = new Map((data.locators?.moon || []).map(point => [point.id, point]));
      for (const card of lunar?.cards || []) if (finite(card.centre?.lat) && finite(card.centre?.lon_east)) lunarPoints.set(card.id, { ...lunarPoints.get(card.id), ...card.centre, id: card.id, name: card.official_name || lunarPoints.get(card.id)?.name || card.id });
      const moon = api?.targets?.length ? api.targets.map(target => ({ ...lunarPoints.get(target.id), ...target,
        lat: target.lat ?? target.moon_lat ?? lunarPoints.get(target.id)?.lat, lon_east: target.lon_east ?? target.lon ?? lunarPoints.get(target.id)?.lon_east })) : [...lunarPoints.values()];
      const marsPointsById = new Map((data.locators?.mars || []).map(point => [point.id, point]));
      const mars = data.sites.map(site => ({ ...marsPointsById.get(site.id), ...site,
        lat: site.lat ?? marsPointsById.get(site.id)?.lat, lon_east: site.lon_east ?? marsPointsById.get(site.id)?.lon_east }));
      const moonId = api?.getState().target || moon[0]?.id;
      const svg = (label, contents) => `<svg viewBox="0 0 560 320" role="img" aria-label="${escapeHTML(label)}" xmlns="http://www.w3.org/2000/svg">${contents}</svg>`;
      const mark = (point, x, y, active) => `<circle data-locator-site="${escapeHTML(point.id)}" cx="${x}" cy="${y}" r="${active ? 7 : 3.5}" class="mars-locator-dot${active ? ' mars-locator-active' : ''}"><title>${escapeHTML(point.name)}</title></circle>`;
      const moonExtent = Math.max(...moon.filter(point => finite(point.lat)).map(point => 90 + point.lat), 1) * 1.35;
      const moonPoints = moon.map(point => {
        if (!finite(point.lat) || !finite(point.lon_east)) return '';
        const radius = (90 + point.lat) / moonExtent * 118;
        const angle = point.lon_east * Math.PI / 180;
        const x = 280 + radius * Math.sin(angle);
        const y = 150 - radius * Math.cos(angle);
        return mark(point, x, y, point.id === moonId);
      }).join('');
      const moonFrame = `<circle cx="280" cy="150" r="118" class="mars-locator-ground"/><circle cx="280" cy="150" r="59" class="mars-locator-grid"/><path d="M162,150H398 M280,32V268" class="mars-locator-grid"/><text x="280" y="296" text-anchor="middle">South pole at the centre</text>`;
      const marsGrid = `<rect x="20" y="22" width="520" height="260" class="mars-locator-ground"/>${[85, 150, 215].map(y => `<path d="M20,${y}H540" class="mars-locator-grid"/>`).join('')}${[150, 280, 410].map(x => `<path d="M${x},22V282" class="mars-locator-grid"/>`).join('')}`;
      const marsPoints = mars.map(point => {
        if (!finite(point.lat) || !finite(point.lon_east)) return '';
        const x = 20 + ((point.lon_east % 360 + 360) % 360) / 360 * 520;
        const y = 22 + (90 - point.lat) / 180 * 260;
        return mark(point, x, y, point.id === siteId);
      }).join('');
      const locatorCoordinates = (points, id) => {
        const active = points.find(point => point.id === id);
        const table = rows => `<div class="mars-table-wrap"><table><thead><tr><th scope="col">Site</th><th scope="col">Coordinates</th></tr></thead><tbody>${rows.map(point => `<tr><th scope="row">${escapeHTML(point.name)}</th><td>${escapeHTML(position(point.lat, point.lon_east))}</td></tr>`).join('')}</tbody></table></div>`;
        return `<p class="mars-locator-name">${escapeHTML(active?.name || 'Site unknown')}</p><p class="mars-note">The outlined mark shows this site.</p><details class="mars-locator-coordinates fold"><summary>Site coordinates</summary>${table(active ? [active] : [])}<details class="fold"><summary>Show all sites (${number(points.length)})</summary>${table(points)}</details></details>`;
      };
      const open = [...$('.mars-locators').querySelectorAll('details')].map(details => details.open);
      $('.mars-locators').innerHTML = `<figure class="card mars-moon-locator"><h4>Moon: south polar cap</h4>${svg('Moon south polar cap with lunar regions', moonFrame + moonPoints)}${locatorCoordinates(moon, moonId)}<figcaption class="mars-caption">${CAPTION}</figcaption></figure><figure class="card mars-mars-locator"><h4>Mars: latitude and longitude</h4>${svg('Mars latitude and longitude frame with the Mars sites',marsGrid + marsPoints)}${locatorCoordinates(mars, siteId)}<figcaption class="mars-caption">${CAPTION}</figcaption></figure>`;
      [...$('.mars-locators').querySelectorAll('details')].forEach((details, i) => { details.open = open[i] || false; });
    }

    function selectedText() {
      const square = chosenSquare();
      return square ? `${square.region || 'Region unknown'} · ${position(square.lat, square.lon)} · Score ${scoreNumber(square.sites[siteId]?.[goal])}.` : 'Select a square to inspect its scores.';
    }
    function project(lon, lat) { return [width / 2 + (lon + camera.x) * plotScale, height / 2 + (-lat + camera.y) * plotScale]; }
    function constrain() {
      const nextScale = Math.min(width / 360, height / 180) * camera.zoom;
      if (!nextScale) return;
      const horizontal = Math.max(0, 180 - width / (2 * nextScale));
      const vertical = Math.max(0, 90 - height / (2 * nextScale));
      camera.x = Math.max(-horizontal, Math.min(horizontal, camera.x));
      camera.y = Math.max(-vertical, Math.min(vertical, camera.y));
    }
    function draw() {
      if (destroyed) return;
      const rect = canvas.getBoundingClientRect();
      width = rect.width; height = rect.height;
      if (!width || !height) return;
      const density = Math.min(window.devicePixelRatio || 1, 3);
      const pixelWidth = Math.round(width * density), pixelHeight = Math.round(height * density);
      if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) { canvas.width = pixelWidth; canvas.height = pixelHeight; }
      context.setTransform(density, 0, 0, density, 0, 0);
      plotScale = Math.min(width / 360, height / 180) * camera.zoom;
      const style = getComputedStyle(section);
      const fallbacks = { '--ocean': '#0c111a', '--graticule': 'rgba(160,180,220,0.2)', '--land': '#262d3a', '--coast': '#46506a', '--unknown': '#7b8497', '--surface': '#111620', '--ui': '#5cc8f5', '--mars': '#e2693b' };
      const variable = name => style.getPropertyValue(name).trim() || fallbacks[name];
      context.fillStyle = variable('--ocean'); context.fillRect(0, 0, width, height);
      context.lineWidth = 0.7;
      context.strokeStyle = variable('--graticule');
      context.beginPath();
      for (let lat = -60; lat <= 60; lat += 30) {
        const a = project(-180, lat), b = project(180, lat); context.moveTo(...a); context.lineTo(...b);
      }
      for (let lon = -180; lon <= 180; lon += 60) {
        const a = project(lon, -90), b = project(lon, 90); context.moveTo(...a); context.lineTo(...b);
      }
      context.stroke();
      context.fillStyle = variable('--land'); context.strokeStyle = variable('--coast');
      for (const polygon of world.coordinates || []) {
        context.beginPath();
        for (const ring of polygon) {
          ring.forEach(([lon, lat], index) => { const point = project(lon, lat); if (!index) context.moveTo(...point); else context.lineTo(...point); });
          context.closePath();
        }
        context.fill('evenodd'); context.stroke();
      }
      const mark = Math.max(1.8, meta.square_deg * plotScale);
      for (const square of squares) {
        if (!finite(square.lat) || !finite(square.lon)) continue;
        const [x, y] = project(square.lon, square.lat);
        if (x < -mark || x > width + mark || y < -mark || y > height + mark) continue;
        const score = square.sites[siteId]?.[goal];
        context.fillStyle = finite(score) ? scoreColor(score, variable('--surface'), variable('--mars')) : variable('--unknown');
        context.fillRect(x - mark / 2, y - mark / 2, mark, mark);
      }
      const square = squareById.get(hoverId || selectedId);
      if (square && finite(square.lat) && finite(square.lon)) {
        const [x, y] = project(square.lon, square.lat);
        context.beginPath(); context.arc(x, y, Math.max(mark, 6), 0, Math.PI * 2);
        context.strokeStyle = variable('--surface'); context.lineWidth = 5; context.stroke();
        context.strokeStyle = variable('--ui'); context.lineWidth = 2; context.stroke();
      }
    }
    redraw = () => {
      if (frame || destroyed) return;
      frame = requestAnimationFrame(() => { frame = 0; draw(); });
    };
    function zoom(factor, anchorX = width / 2, anchorY = height / 2) {
      const previous = camera.zoom;
      camera.zoom = Math.max(1, Math.min(28, previous * factor));
      const ratio = camera.zoom / previous;
      camera.x += (anchorX - width / 2) / plotScale * (1 / ratio - 1);
      camera.y += (anchorY - height / 2) / plotScale * (1 / ratio - 1);
      plotScale *= ratio;
      constrain(); redraw();
    }
    function select(id, { focus = false, centre = false, write = true } = {}) {
      if (id != null && !squareById.has(id)) return;
      selectedId = id;
      if (centre && selectedId) {
        const square = chosenSquare();
        camera.x = -square.lon; camera.y = square.lat; constrain();
      }
      renderSquare(focus); mapStatus.textContent = selectedText();
      canvas.setAttribute('aria-label', `World map. ${selectedText()} Press Enter to open the details.`);
      redraw();
      if (write) publish();
    }
    function browse(delta) {
      const index = indexById.get(selectedId) ?? 0;
      select(squares[(index + delta + squares.length) % squares.length]?.id, { centre: true });
    }
    function nearest(x, y) {
      let match = null, distance = Math.max(9, meta.square_deg * plotScale) ** 2;
      for (const square of squares) {
        if (!finite(square.lat) || !finite(square.lon)) continue;
        const [sx, sy] = project(square.lon, square.lat);
        const next = (sx - x) ** 2 + (sy - y) ** 2;
        if (next < distance) { match = square; distance = next; }
      }
      return match;
    }
    function pointerPoint(event) {
      const rect = canvas.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    }
    function resetGesture() {
      const values = [...pointers.values()];
      gesture = values.length >= 2 ? { distance: Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y), x: (values[0].x + values[1].x) / 2, y: (values[0].y + values[1].y) / 2 } : values[0] || null;
    }
    on(canvas, 'pointerdown', event => {
      if (event.button !== 0) return;
      canvas.focus({ preventScroll: true });
      const point = pointerPoint(event);
      pointers.set(event.pointerId, point); pointerStart = point;
      moved = false; canvasWasDragged = false;
      canvas.setPointerCapture(event.pointerId); resetGesture(); tooltip.hidden = true;
    });
    on(canvas, 'pointermove', event => {
      const point = pointerPoint(event);
      if (pointers.has(event.pointerId)) {
        pointers.set(event.pointerId, point);
        if (pointers.size >= 2) {
          const old = gesture; resetGesture();
          if (old?.distance && gesture?.distance) {
            zoom(gesture.distance / old.distance, gesture.x, gesture.y);
            camera.x += (gesture.x - old.x) / plotScale;
            camera.y += (gesture.y - old.y) / plotScale;
          }
          moved = true;
        } else if (gesture) {
          camera.x += (point.x - gesture.x) / plotScale;
          camera.y += (point.y - gesture.y) / plotScale;
          if (pointerStart && Math.hypot(point.x - pointerStart.x, point.y - pointerStart.y) > 4) moved = true;
          gesture = point;
        }
        canvasWasDragged ||= moved;
        constrain(); redraw(); return;
      }
      const square = nearest(point.x, point.y);
      hoverId = square?.id || null;
      tooltip.hidden = !square;
      if (square) {
        tooltip.textContent = `${square.region || 'Region unknown'} · ${scoreNumber(square.sites[siteId]?.[goal])}. ${compactPass}.`;
        tooltip.style.left = `${Math.max(8, Math.min(width - tooltip.offsetWidth - 8, point.x + 12))}px`;
        tooltip.style.top = `${Math.max(8, Math.min(height - tooltip.offsetHeight - 8, point.y + 14))}px`;
      }
      redraw();
    });
    const endPointer = event => {
      if (!pointers.has(event.pointerId)) return;
      const point = pointerPoint(event);
      const click = !canvasWasDragged && pointers.size === 1 && event.type === 'pointerup';
      pointers.delete(event.pointerId); resetGesture();
      if (click) { const square = nearest(point.x, point.y); if (square) select(square.id, { focus: true }); }
    };
    on(canvas, 'pointerup', endPointer); on(canvas, 'pointercancel', endPointer);
    on(canvas, 'lostpointercapture', event => { pointers.delete(event.pointerId); resetGesture(); });
    on(canvas, 'pointerleave', () => { hoverId = null; tooltip.hidden = true; redraw(); });
    on(canvas, 'wheel', event => { event.preventDefault(); const point = pointerPoint(event); zoom(Math.exp(-event.deltaY * 0.002), point.x, point.y); }, { passive: false });
    on(canvas, 'keydown', event => {
      const move = 60 / plotScale;
      const actions = {
        ArrowLeft: () => { camera.x += move; }, ArrowRight: () => { camera.x -= move; },
        ArrowUp: () => { camera.y += move; }, ArrowDown: () => { camera.y -= move; },
        '+': () => zoom(1.5), '=': () => zoom(1.5), '-': () => zoom(1 / 1.5),
        Home: () => Object.assign(camera, { zoom: 1, x: 0, y: 0 }),
        PageUp: () => browse(-1), PageDown: () => browse(1), Enter: () => renderSquare(true),
        Escape: () => { hoverId = null; tooltip.hidden = true; }
      };
      if (actions[event.key]) { event.preventDefault(); actions[event.key](); constrain(); redraw(); }
    });

    function renderSelection({ centre = false } = {}) {
      for (const button of section.querySelectorAll('[data-site]')) button.setAttribute('aria-pressed', String(button.dataset.site === siteId));
      $('.mars-site-choice').textContent = currentSite().name;
      for (const button of section.querySelectorAll('[data-goal]')) button.setAttribute('aria-pressed', String(button.dataset.goal === goal));
      $('.mars-formula').textContent = `${GOALS.find(([id]) => id === goal)[1]}: ${shortProse(meta.formulas?.[goal])}.`.replace(/\.\.$/, '.');
      siteCard(); renderTop(); renderSearch(); renderCannot(); renderValidation(); renderLocators();
      if (!api && !selectedId) selectedId = topPlaces()[0]?.id || squares[0]?.id;
      select(selectedId, { write: false, centre });
      const best = topPlaces()[0];
      $('.mars-finding').textContent = best
        ? `${best.region || 'An unnamed region'} has the highest listed score for ${shortName(currentSite())}: ${scoreNumber(best.score)}.`
        : `No square has a known score for ${shortName(currentSite())} with this goal.`;
      $('.mars-announcement').textContent = `${shortName(currentSite())}. ${GOALS.find(([id]) => id === goal)[1]}. The map and lists now show this choice.`;
    }
    async function requestSelection(state, { write = false, centre = false } = {}) {
      const next = { site: validSite(state.msite), goal: validGoal(state.mgoal), square: validSquare(state.msquare) };
      if (pendingSelection && Object.keys(next).every(key => next[key] === pendingSelection[key])) return;
      const request = ++requestNumber;
      pendingSelection = next;
      $('.mars-work').hidden = false;
      $('.mars-work').textContent = `Working: ${data.sites.find(site => site.id === next.site).name}`;
      section.setAttribute('aria-busy', 'true');
      if (write && api) api.setState({ msite: next.site, mgoal: next.goal, msquare: next.square || '' });
      try {
        await store.ensureSite(next.site);
        if (destroyed || request !== requestNumber) return;
        siteId = next.site; goal = next.goal; selectedId = next.square;
        pendingSelection = null;
        hoverId = null; tooltip.hidden = true;
        renderSelection({ centre });
        $('.mars-work').hidden = true;
        section.removeAttribute('aria-busy');
        if (write) publish();
      } catch (error) {
        if (destroyed || request !== requestNumber || error.name === 'AbortError') return;
        pendingSelection = null;
        section.removeAttribute('aria-busy');
        $('.mars-work').textContent = 'The site data is unavailable. Try this site again.';
      }
    }
    on(section, 'click', event => {
      const button = event.target.closest('button');
      if (!button || !section.contains(button)) return;
      if (button.dataset.site) { requestSelection({ msite: button.dataset.site, mgoal: pendingSelection?.goal || goal }, { write: true }); $('.mars-site-picker').open = false; $('.mars-site-picker > summary').focus(); }
      if (button.dataset.goal) requestSelection({ msite: pendingSelection?.site || siteId, mgoal: button.dataset.goal }, { write: true });
      if (button.dataset.square) select(button.dataset.square, { focus: true, centre: true });
      if (button.dataset.searchSquare) select(button.dataset.searchSquare, { focus: true, centre: true });
      if (button.classList.contains('mars-download')) downloadList();
      const action = button.dataset.map;
      if (action === 'in') zoom(1.5);
      if (action === 'out') zoom(1 / 1.5);
      if (action === 'reset') { Object.assign(camera, { zoom: 1, x: 0, y: 0 }); redraw(); }
      if (action === 'previous') browse(-1);
      if (action === 'next') browse(1);
      if (action === 'open') renderSquare(true);
    });
    function filterSites() {
      const terms = $('.mars-site-filter').value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      let count = 0;
      for (const option of section.querySelectorAll('.mars-site-option')) { option.hidden = !terms.every(term => option.dataset.search.includes(term)); if (!option.hidden) count++; }
      for (const group of section.querySelectorAll('.mars-site-group')) group.hidden = !group.querySelector('.mars-site-option:not([hidden])');
      $('.mars-site-count').textContent = `${number(count)} of ${number(data.sites.length)} sites`;
    }
    on($('.mars-site-filter'), 'input', filterSites);
    on($('.mars-site-picker'), 'keydown', event => {
      const options = [...section.querySelectorAll('.mars-site-option:not([hidden])')], index = options.indexOf(event.target);
      if (event.key === 'Escape') { event.preventDefault(); $('.mars-site-picker').open = false; $('.mars-site-picker > summary').focus(); }
      if (event.key === 'ArrowDown' && (index >= 0 || event.target.matches('.mars-site-filter'))) { event.preventDefault(); (options[index + 1] || options.at(-1))?.focus(); }
      if (event.key === 'ArrowUp' && index >= 0) { event.preventDefault(); (options[index - 1] || $('.mars-site-filter')).focus(); }
      if (event.key === 'Enter' && event.target.matches('.mars-site-filter') && options.length === 1) { event.preventDefault(); options[0].click(); }
    });
    filterSites();
    on($('.mars-search-input'), 'input', renderSearch);
    on($('.mars-search-input'), 'keydown', event => {
      if (event.key === 'ArrowDown' || event.key === 'Enter') {
        const first = $('.mars-search-results button');
        if (first) { event.preventDefault(); event.key === 'Enter' ? first.click() : first.focus(); }
      }
      if (event.key === 'Escape') { event.preventDefault(); event.currentTarget.value = ''; renderSearch(); }
    });
    on($('.mars-search-results'), 'keydown', event => {
      const buttons = [...section.querySelectorAll('.mars-search-results li:not([hidden]) button')];
      const index = buttons.indexOf(event.target);
      if (index < 0) return;
      if (['ArrowUp', 'ArrowDown', 'Home', 'End', 'Escape'].includes(event.key)) event.preventDefault();
      if (event.key === 'ArrowUp') (buttons[index - 1] || $('.mars-search-input')).focus();
      if (event.key === 'ArrowDown') (buttons[index + 1] || buttons[index]).focus();
      if (event.key === 'Home') buttons[0].focus();
      if (event.key === 'End') buttons.at(-1).focus();
      if (event.key === 'Escape') $('.mars-search-input').focus();
    });
    const notes = [meta.first_pass, meta.climate_caution, meta.score_caution, ...(data.warnings || [])].filter(Boolean);
    $('.mars-export-notes div').innerHTML = notes.map(note => `<p>${escapeHTML(shortProse(note))}</p>`).join('')
      + (extraManifest ? `<p>The extra figures keep the definitions, rules, units, credits and limits of their sources.</p><p><a href="${new URL('./data/mars_extra.json', import.meta.url)}" download>Download the extra-data guide and source metadata</a></p>${(extraManifest.missing_inputs || []).map(name => extraNote(`Missing input: ${name}. The page does not show its figures.`)).join('')}${extraNote(extraManifest.input_meta?.mars_rock_frozen?.credit_line)}${extraNote(extraManifest.input_meta?.mars_power_extra?.credit)}` : extraNote('The extra data is unavailable. The original scores are still available.'));
    renderSelection();
    let lunarTarget = api?.getState().target;
    unsubscribe = api?.onState(state => {
      if (destroyed) return;
      const nextSite = validSite(state.msite), nextGoal = validGoal(state.mgoal), nextSquare = validSquare(state.msquare);
      if (nextSite !== siteId || nextGoal !== goal || pendingSelection) requestSelection(state, { centre: true });
      else if (nextSquare !== selectedId) select(nextSquare, { centre: true, write: false });
      if (state.target !== lunarTarget) { lunarTarget = state.target; renderLocators(); }
      redraw();
    });
    observer = new ResizeObserver(redraw); observer.observe(canvas);
    themeObserver = new MutationObserver(redraw);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class', 'style'] });
    redraw(); section.dataset.ready = 'true';
    section.dispatchEvent(new CustomEvent('mars:ready', { bubbles: true }));
  }).catch(error => {
    if (destroyed || error.name === 'AbortError') return;
    section.innerHTML = '<h2>Mars first pass</h2><p role="alert">The Mars section cannot load its local data. Reload this page.</p>';
    section.dataset.error = 'true';
  });

  return {
    destroy() {
      if (destroyed) return;
      destroyed = true; lifecycle.abort(); observer?.disconnect(); themeObserver?.disconnect(); unsubscribe?.();
      media.removeEventListener('change', themeChanged);
      if (frame) cancelAnimationFrame(frame);
      section.remove();
      if (hasPageHead) rootElement.classList.remove('mars-mounted');
    }
  };
}
