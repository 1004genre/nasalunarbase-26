// Planner: a dependency-free extension of the page's version-one API.
const DRAWN = 'Drawn by code from open data; the code was written with AI assistance.';
const NO_MODEL = 'unknown: NASA has no 5 m terrain model of this region';
const SVG = 'http://www.w3.org/2000/svg';
const PIN_LIMIT = 3;
// Display limits for poor months; these are reading rules, not measured data.
const POOR_MONTH = Object.freeze({ hours: 20, snowPercent: 25 });
const finite = value => typeof value === 'number' && Number.isFinite(value);
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (tag === 'button') node.classList.add('btn');
  if (tag === 'details') node.classList.add('fold');
  if (/^pl-(?:panel|activity)(?: |$)/.test(className || '')) node.classList.add('card');
  if (className === 'pl-choice') node.classList.add('chip');
  if (['pl-tag', 'pl-verdict', 'pl-selected-label'].includes(className)) node.classList.add('tag');
  if (className === 'pl-legend') node.classList.add('legend');
  if (text != null) node.textContent = text;
  return node;
}
function button(text, action, className = 'pl-btn') {
  const node = el('button', className, text);
  node.type = 'button'; node.addEventListener('click', action);
  return node;
}
function svgNode(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text != null) node.textContent = text;
  return node;
}
function details(label, content) {
  const node = el('details', 'pl-data-table');
  node.append(el('summary', '', label), content);
  return node;
}
function table(headers, rows, className = '') {
  const node = el('table', `pl-table ${className}`.trim());
  const head = el('thead'), hr = el('tr');
  headers.forEach(text => { const th = el('th', '', text); th.scope = 'col'; hr.append(th); });
  head.append(hr); node.append(head);
  const body = el('tbody');
  rows.forEach(row => {
    const tr = el('tr');
    row.forEach((value, j) => {
      const cell = el(j === 0 ? 'th' : 'td');
      if (j === 0) cell.scope = 'row';
      cell.dataset.label = headers[j];
      if (value instanceof Node) cell.append(value); else cell.textContent = value;
      tr.append(cell);
    });
    body.append(tr);
  });
  node.append(body);
  const extra = [...body.children].slice(5);
  if (extra.length) {
    extra.forEach(row => { row.hidden = true; });
    const foot = el('tfoot'), row = el('tr'), cell = el('td'); cell.colSpan = headers.length;
    const more = button('Show all', () => {
      const expanded = more.getAttribute('aria-expanded') !== 'true';
      extra.forEach(item => { item.hidden = !expanded; });
      more.setAttribute('aria-expanded', String(expanded));
      more.textContent = expanded ? 'Show less' : 'Show all';
    });
    more.setAttribute('aria-expanded', 'false'); cell.append(more); row.append(cell); foot.append(row); node.append(foot);
  }
  return node;
}
function caption() { return el('p', 'pl-caption', DRAWN); }

export async function mount(root, api) {
  if (api.version !== 1) throw new Error('The Planner must use page API version 1.');
  let alive = true;
  const cleanups = [];
  root.classList.add('pl-planner');
  root.replaceChildren(el('p', 'pl-status', 'The Planner will open.'));
  const read = async (name, binary = false) => {
    try { return await (binary ? api.loadBin(name) : api.loadJSON(name)); }
    catch { return null; }
  };
  const [index, tools, rules, year, airfields, basis, pageMeta] = await Promise.all([
    read('planner.json'), read('tools.json'), read('rehearsal_rules.json'),
    read('yearplan.json'), read('airfields.json'), read('basis.json'), read('meta.json')
  ]);
  if (!index) { root.textContent = 'The Planner data index is unavailable.'; return { destroy() { root.replaceChildren(); } }; }
  const ids = Array.from({length: api.areaCount}, (_, i) => api.area(i).id);
  let digest = null;
  if (globalThis.crypto?.subtle) {
    digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ids.join('\n')))))
      .map(v => v.toString(16).padStart(2, '0')).join('');
  }
  const matches = manifest => manifest?.areas?.count === api.areaCount && digest === manifest.areas.ids_sha256;
  const valid = matches(index);
  const loadChecked = async (manifest, name) => {
    if (!matches(manifest) || !manifest.files?.[name]) return null;
    const buffer = await read(name, true);
    return buffer?.byteLength === manifest.files[name].bytes ? buffer : null;
  };
  const [rehearsal, roseBuffer, skylineBuffer, accessBuffer] = await Promise.all([
    loadChecked(index, 'rehearsal.bin'), loadChecked(index, 'rose.bin'),
    loadChecked(index, 'skyline.bin'), loadChecked(tools, 'access.bin')
  ]);
  const rLayout = index.files['rehearsal.bin']?.layout;
  const blocks = Object.fromEntries((rLayout?.blocks || []).map(block => [block.name, block]));
  const rView = rehearsal ? new DataView(rehearsal) : null;
  const rose = roseBuffer ? new Uint8Array(roseBuffer) : null;
  const skyline = skylineBuffer ? new Uint8Array(skylineBuffer) : null;
  const access = accessBuffer ? new DataView(accessBuffer) : null;
  const roseLayout = index.files['rose.bin']?.layout;
  const skyLayout = index.files['skyline.bin']?.layout;
  const accessLayout = tools?.files?.['access.bin']?.layout;
  const activities = rules?.activities || [];
  const codes = blocks.verdicts?.codes || {};
  const targetIndex = id => index.targets.indexOf(id);
  const target = id => api.targets.find(item => item.id === id) || api.targets[0];
  const noModel = id => (target(id)?.has_model ?? pageMeta?.targets?.find(item => item.id === id)?.has_model) === false;
  const modelNote = id => noModel(id) ? `Lunar terrain comparison: cannot tell. ${NO_MODEL}.` : '';
  const needsLunarTerrain = activity => (activity.inputs || []).some(input =>
    /lunar|\bMoon\b/i.test(`${input.name || ''} ${input.source || ''}`) && /slope|terrain|roughness/i.test(`${input.name || ''} ${input.source || ''}`));
  const number = (value, digits = 1) => finite(value) ? api.fmtNumber(value, digits) : 'unknown';
  const hours = value => finite(value) ? api.fmtHours(value) : 'unknown';
  const south = i => api.area(i).lat < 0;
  const name = i => {
    const a = api.area(i);
    return typeof a.named === 'string' && a.named ? a.named : `${a.region || 'Area'} · ${a.id}`;
  };
  const areaButton = i => button(name(i), () => api.openPlace(api.area(i).id), 'pl-link');
  const pairIndex = (i, id) => i * index.targets.length + targetIndex(id);
  function h30(i, id) {
    if (!rView || targetIndex(id) < 0) return null;
    const raw = rView.getUint16(blocks.h30.offset_bytes + pairIndex(i, id) * Uint16Array.BYTES_PER_ELEMENT, true);
    return raw === blocks.h30.unknown ? null : raw / 10; // layout: tenths of an hour
  }
  function firstPeriod(i, id) {
    if (!rView || targetIndex(id) < 0) return null;
    const raw = rView.getUint8(blocks.first_period.offset_bytes + pairIndex(i, id));
    return raw === blocks.first_period.unknown ? null : raw;
  }
  function bestDates(i, id) {
    const first = firstPeriod(i, id);
    if (first == null) return h30(i, id) === 0 ? 'No period to name' : 'unknown';
    // H30 is defined by the file as three consecutive ten-day periods.
    return Array.from({length: 3}, (_, j) => api.periods[(first + j) % api.periods.length]?.label || 'unknown').join('; ');
  }
  function verdict(i, id, activity) {
    if (noModel(id) && needsLunarTerrain(activity)) return { code: codes['cannot tell'], word: 'cannot tell', kind: 'unknown' };
    let code = codes['cannot tell'];
    if (rView && targetIndex(id) >= 0) {
      const a = blocks.verdicts.activities.indexOf(activity.id);
      if (a >= 0) code = rView.getUint8(blocks.verdicts.offset_bytes + pairIndex(i, id) * blocks.verdicts.shape[2] + a);
    }
    // The handoff explicitly requires a cautious snow verdict for southern areas.
    if (south(i) && activity.inputs.some(input => input.key === 'S')) code = codes['cannot tell'];
    const word = rules?.verdicts.find(item => item.code === code)?.word || 'cannot tell';
    return { code, word: word === 'near' ? 'nearly passes' : word,
      kind: word === 'pass' ? 'pass' : word === 'near' ? 'near' : word === 'does not pass' ? 'fail' : 'unknown' };
  }
  function nearest(i) {
    if (!access || !airfields) return null;
    const cols = accessLayout.columns, prefix = south(i) ? 'any' : 'scheduled';
    const get = column => access.getUint16((i * accessLayout.shape[1] + cols.indexOf(column)) * Uint16Array.BYTES_PER_ELEMENT, true);
    const ai = get(`${prefix}_index`), km = get(`${prefix}_km`);
    return { airfield: ai === accessLayout.unknown ? null : airfields.airfields[ai], km: km === accessLayout.unknown ? null : km };
  }
  function accessText(i) {
    const a = nearest(i);
    if (!a?.airfield) return 'Airfield unknown; distance unknown';
    return `${a.airfield.name} · ${number(a.km, 0)}${a.km == null ? '' : ' km'}`;
  }
  function inputValue(i, id, key) {
    if (key === 'H30') return h30(i, id);
    // The API supplies bare share; the access file supplies whole kilometres.
    if (key === 'B') return finite(api.area(i).bare) && api.area(i).bare >= 0 ? api.area(i).bare : null;
    if (key === 'D') return nearest(i)?.km ?? null;
    if (key === 'S' && south(i)) return null;
    return undefined; // The export has no exact value: never rebuild it from rounded arrays.
  }
  function choice() { return activities.find(activity => activity.id === api.getState().rehearse); }
  function pins() {
    const value = api.getState().compare;
    return [...new Set((Array.isArray(value) ? value : String(value || '').split(',')).filter(id => api.areaIndex(id) >= 0))].slice(-PIN_LIMIT);
  }
  let notice = '';
  function togglePin(i) {
    const id = api.area(i).id, next = pins();
    const at = next.indexOf(id);
    if (at >= 0) { next.splice(at, 1); notice = `The page removed ${name(i)} from the comparison.`; }
    else {
      const old = next.length === PIN_LIMIT ? next.shift() : null;
      next.push(id);
      notice = old ? `${name(i)} replaces ${name(api.areaIndex(old))} in the comparison.` : `The page added ${name(i)} to the comparison.`;
    }
    const focusedPin = document.activeElement?.dataset.plPin;
    const focusedControl = document.activeElement?.dataset.plControl;
    api.announce(notice); api.setState({compare: next.join(',')});
    if (focusedPin) queueMicrotask(() => {
      const replacement = [...document.querySelectorAll('[data-pl-pin]')].find(node => node.dataset.plPin === focusedPin && node.dataset.plControl === focusedControl && node.getClientRects().length);
      if (replacement) replacement.focus({preventScroll:true});
      else { const heading = comparePanel.querySelector('h3'); heading.tabIndex = -1; heading.focus({preventScroll:true}); }
    });
  }
  const choicePanel = el('section', 'pl-panel'); choicePanel.id = 'pl-choices';
  const fieldset = el('fieldset', 'pl-choices'); fieldset.append(el('legend', '', 'What do you want to rehearse?'));
  const radios = [];
  for (const activity of [{id: '', activity: 'No activity'}, ...activities]) {
    const label = el('label', 'pl-choice'), input = el('input');
    input.type = 'radio'; input.name = 'pl-rehearse'; input.value = activity.id;
    input.addEventListener('change', () => api.setState({rehearse: activity.id, order: activity.id ? 'rehearse' : ''}));
    label.append(input, el('span', 'pl-choice-label', activity.activity)); fieldset.append(label); radios.push(input);
  }
  const choiceRule = el('div', 'pl-rule');
  const terrainNote = el('p', 'pl-muted pl-model-note'); terrainNote.hidden = true;
  choicePanel.append(fieldset, terrainNote, details('The rules', choiceRule));
  if (!rules || !rView) choicePanel.append(el('p', 'pl-muted', 'The rehearsal data is unavailable.'));
  const comparePanel = el('section', 'pl-panel'); comparePanel.id = 'pl-compare';
  const yearPanel = el('section', 'pl-panel'); yearPanel.id = 'pl-year';
  const heading = el('header', 'pl-heading section-head');
  const finding = el('p', 'pl-finding finding'), headingText = el('div');
  headingText.append(el('p', 'eyebrow', 'Plan'), el('h2', '', 'What can you rehearse here?'), finding);
  heading.append(el('span', 'step-number', '5'), headingText);
  root.replaceChildren(heading, choicePanel, comparePanel, yearPanel);
  if (!valid) root.prepend(el('p', 'pl-status', 'The area index does not match the areas on this page. Thus, the Planner cannot show figures for these areas.'));

  function renderChoices() {
    const selected = choice();
    terrainNote.textContent = modelNote(api.getState().target); terrainNote.hidden = !terrainNote.textContent;
    radios.forEach(radio => { radio.checked = radio.value === (selected?.id || ''); });
    choiceRule.replaceChildren();
    if (selected) {
      choiceRule.append(el('p', 'pl-muted', selected.label), el('p', '', selected.pass_rule), el('p', '', selected.near_rule));
      // The rule sentences use short symbols; say what each one stands for, from the rules file.
      const key = el('ul', 'pl-key');
      for (const input of selected.inputs || []) key.append(el('li', '', `${input.symbol}: ${input.name} (${input.unit}).`));
      if (key.children.length) choiceRule.append(key);
      choiceRule.append(el('p', 'pl-muted', 'Areas that pass the rule come first. Areas that nearly pass come next. In each group, the hours in the best three ten-day periods set the order.'));
    } else choiceRule.append(el('p', 'pl-muted', 'Select an activity. Its rule sets the order of the short lists. Each place card also shows the rule.'));
  }
  function rehearsalCard(i, id) {
    if (!alive || !rules || !rView) return null;
    const node = el('div', 'pl-rehearsal');
    node.append(el('p', 'pl-muted', target(id).name), details('What the files give', el('p', 'pl-muted', 'The files do not give all rule inputs. They also do not show which input caused a failure. Below, the card shows only the available figures.')));
    if (noModel(id)) node.append(el('p', 'pl-muted pl-model-note', modelNote(id)), el('p', 'pl-muted', 'These rehearsal rules use the terrain of the Earth area. They do not compare lunar slopes.'));
    const grid = el('div', 'pl-activities');
    const chosen = choice();
    const ordered = [...activities].sort((a, b) => Number(b === chosen) - Number(a === chosen));
    for (const activity of ordered) {
      const article = el('section', `pl-activity${activity === chosen ? ' pl-selected' : ''}`);
      article.dataset.activity = activity.id;
      article.append(el('h4', '', activity.activity));
      if (activity === chosen) article.append(el('span', 'pl-selected-label', 'Selected activity'));
      const v = verdict(i, id, activity), badge = el('p', 'pl-verdict', v.word);
      badge.dataset.kind = v.kind; article.append(badge, el('p', 'pl-muted', activity.label));
      const rulesHere = el('div', 'pl-rule');
      rulesHere.append(el('p', '', activity.pass_rule), el('p', '', activity.near_rule));
      article.append(details('The rules', rulesHere));
      const inputs = el('dl', 'pl-inputs');
      for (const input of activity.inputs) {
        const value = inputValue(i, id, input.key);
        if (value === undefined) continue;
        const row = el('div', 'pl-input');
        const dt = el('dt', '', input.symbol); dt.append(el('small', '', input.name));
        const digits = input.key === 'B' ? 2 : input.key === 'D' ? 0 : 1;
        row.append(dt, el('dd', '', `${number(value, digits)}${finite(value) ? ' ' + input.unit : ''}`)); inputs.append(row);
      }
      article.append(inputs);
      if (v.kind === 'fail') {
        const failed = activity.near.find(near => {
          const pass = activity.pass.find(rule => rule.input === near.input);
          const value = inputValue(i, id, near.input);
          const misses = rule => rule.op === '>=' ? value < rule.value : rule.op === '<=' ? value > rule.value : false;
          return pass && finite(value) && misses(near) && misses(pass);
        });
        if (failed) {
          const input = activity.inputs.find(item => item.key === failed.input);
          article.append(el('p', 'pl-failure', `${input.symbol} is ${number(inputValue(i,id,input.key), input.key === 'B' ? 2 : 1)} ${input.unit}. This value does not meet the pass rule or the near rule.`));
        }
      }
      if (south(i) && activity.inputs.some(input => input.key === 'S')) {
        article.append(el('p', 'pl-muted', rules.notes.find(note => /^(In Antarctica the snow|Snow is not measured in Antarctica|We do not measure snow in Antarctica)/.test(note)) || 'Snow is not measured in Antarctica.'));
        article.append(el('p', 'pl-muted', 'The rule of this activity uses snow-free odds. Thus, the result here is unknown.'));
      }
      const suggestions = el('ul', 'pl-suggestions');
      for (const suggestion of activity.suggestions || []) {
        const li = el('li'); li.append(el('span', 'pl-tag', suggestion.tag), document.createTextNode(` ${suggestion.text}`));
        if (suggestion.done_how) li.append(el('p', 'pl-muted', suggestion.done_how));
        if (suggestion.source?.link) {
          const link = el('a', '', suggestion.source.name);
          link.href = suggestion.source.link; link.rel = 'noopener noreferrer'; li.append(link);
        }
        suggestions.append(li);
      }
      if (suggestions.children.length) article.append(details('How to rehearse', suggestions)); grid.append(article);
    }
    node.append(grid);
    const notes = el('ul', 'pl-suggestions');
    (rules.notes || []).forEach(note => { if (!/^(In that case, )?a rule that needs S/i.test(note)) notes.append(el('li', '', note)); });
    node.append(details('How to read these rules', notes));
    return node;
  }
  function pinCard(i) {
    if (!alive) return null;
    const node = el('div', 'pl-actions');
    const pinned = pins().includes(api.area(i).id);
    const pin = button(pinned ? 'Unpin from the comparison' : 'Pin to compare', () => togglePin(i));
    pin.dataset.plPin = api.area(i).id; pin.dataset.plControl = 'card'; pin.setAttribute('aria-pressed', String(pinned)); node.append(pin);
    node.append(button('See the comparison', () => {
      api.setState({place: null, only: null, go: null});
      comparePanel.scrollIntoView({block: 'start', behavior: 'instant'});
      const heading = comparePanel.querySelector('h3'); heading.tabIndex = -1; heading.focus({preventScroll:true});
    }, 'pl-link'));
    if (notice) node.append(el('p', 'pl-status', notice));
    return node;
  }
  function renderCompare() {
    const state = api.getState(), id = state.target, indices = pins().map(value => api.areaIndex(value));
    comparePanel.replaceChildren(el('h3', '', 'Compare areas'));
    const status = el('p', 'pl-status', notice); status.setAttribute('role', 'status'); comparePanel.append(status);
    if (!indices.length) { comparePanel.append(el('p', 'pl-muted', `Press “Pin to compare” in a place card. You can keep a maximum of ${PIN_LIMIT} areas.`)); return; }
    comparePanel.append(el('p', 'pl-muted', `${target(id).name} · ${basis?.steps?.find(s => s.step === Number(state.step))?.name || 'Current step'}`));
    if (noModel(id)) comparePanel.append(el('p', 'pl-muted pl-model-note', modelNote(id)));
    const pinList = el('div', 'pl-pin-list');
    indices.forEach((i, j) => {
      const pin = el('div', `pl-pin pl-line-${j}`), remove = button('Remove', () => togglePin(i));
      remove.dataset.plPin = api.area(i).id; remove.dataset.plControl = 'compare'; remove.setAttribute('aria-label', `Remove ${name(i)} from the comparison`);
      pin.append(areaButton(i), remove); pinList.append(pin);
    }); comparePanel.append(pinList);
    const series = indices.map(i => Array.from(api.periodHours(i, id, Number(state.step))));
    const known = series.flat().filter(finite), max = known.length ? Math.max(...known) : null;
    const svg = svgNode('svg', {viewBox: '0 0 720 290', role: 'img', 'aria-label': 'The hours of low Sun in each ten-day period for the pinned areas. A gap shows an unknown period.'});
    svg.append(svgNode('title', {}, 'The hours of low Sun for the pinned areas, on one shared axis'));
    const width = 640, height = 196, left = 58, top = 20;
    const x = j => left + (j + 0.5) / api.periods.length * width;
    const y = value => top + height - (max > 0 ? value / max * height : 0);
    svg.append(svgNode('line', {x1:left,y1:top+height,x2:left+width,y2:top+height,class:'pl-axis'}));
    if (max != null) [0, max].filter((v,j,a) => a.indexOf(v) === j).forEach(value => {
      svg.append(svgNode('text', {x:left-8,y:y(value)+4,'text-anchor':'end'}, number(value, 1)));
      if (value > 0) svg.append(svgNode('line',{x1:left,y1:y(value),x2:left+width,y2:y(value),class:'pl-axis'}));
    });
    const seen = new Set();
    api.periods.forEach((period, j) => {
      if (seen.has(period.month)) return; seen.add(period.month);
      svg.append(svgNode('text',{x:x(j),y:top+height+24,'text-anchor':'middle',class:'pl-month-tick','data-alternate':String(seen.size % 2 === 0)},year?.months?.[period.month-1]?.slice(0,3) || period.label));
    });
    series.forEach((values, s) => {
      let path = '', pen = false;
      values.forEach((value, j) => {
        if (!finite(value)) { pen = false; return; }
        path += `${pen ? 'L' : 'M'}${x(j).toFixed(2)},${y(value).toFixed(2)} `; pen = true;
        const dot = svgNode('circle', {cx:x(j), cy:y(value), r:2.7,class:`pl-dot-${s}`});
        dot.append(svgNode('title',{},`${name(indices[s])}: ${api.periods[j].label}, ${hours(value)}`)); svg.append(dot);
      });
      svg.append(svgNode('path',{d:path,fill:'none',class:`pl-line-${s}`}));
    });
    const chart = el('div','pl-chart'); chart.append(el('p','pl-muted','Hours of low Sun'),svg,caption());
    comparePanel.append(chart, el('p','pl-muted','A gap shows an unknown period. A dot on the baseline shows a known value of zero hours.'));
    if (!known.length) comparePanel.append(el('p','pl-muted','All periods are unknown at this step.'));
    if (indices.some(south)) comparePanel.append(el('p','pl-muted','From the snow step onward, Antarctic areas use the rock season. Snow is not measured there.'));
    const factors = [];
    for (const step of basis?.steps || []) factors.push([step.step === 2 && indices.some(south) ? 'Snow-free ground, or the rock season in the south' : step.name, ...indices.map(i => hours(api.hours(i,id,step.step,'year')))]);
    factors.push(['Best three ten-day periods after terrain',...indices.map(i => bestDates(i,id))],['Hours in those three periods',...indices.map(i=>hours(h30(i,id)))]);
    for (const activity of activities) factors.push([`${activity.activity} — ${activity.label}`,...indices.map(i=>verdict(i,id,activity).word)]);
    if (access) factors.push(['Nearest airfield',...indices.map(accessText)]);
    comparePanel.append(table(['Factor',...indices.map(name)],factors,'pl-compare-table'));
    if (access && airfields?.what_it_is_not) comparePanel.append(el('p','pl-muted',airfields.what_it_is_not));
    comparePanel.append(details('Read each ten-day period',table(['Period',...indices.map(name)],api.periods.map((period,j)=>[period.label,...series.map(values=>hours(values[j]))]))));
  }
  function renderYear() {
    const id = api.getState().target, data = year?.targets?.[id];
    yearPanel.replaceChildren(el('h3', '', 'Year plan'));
    if (!data) { yearPanel.append(el('p','pl-muted','The year plan is unavailable for this lunar region.')); return; }
    yearPanel.append(el('p','pl-muted',data.name));
    const isPoor = entry => entry && ((finite(entry.hours) && entry.hours < POOR_MONTH.hours)
      || (finite(entry.snow_free_odds) && entry.snow_free_odds * 100 < POOR_MONTH.snowPercent));
    const snowText = entry => entry.snow === 'snow not measured' ? 'snow not measured'
      : finite(entry.snow_free_odds) ? `${number(entry.snow_free_odds * 100,0)}% snow-free odds` : 'snow-free odds unknown';
    const usefulMonths = year.months.filter((month,j) => {
      const entry = data.north?.[j];
      return entry && finite(entry.hours) && finite(entry.snow_free_odds) && !isPoor(entry);
    });
    yearPanel.append(el('p','pl-year-summary',`In ${number(usefulMonths.length,0)} of ${number(year.months.length,0)} months, the best northern area meets the two limits for hours and snow-free odds.`));
    if (usefulMonths.length) {
      const months = el('ul','pl-key');
      usefulMonths.forEach(month => months.append(el('li','',month)));
      yearPanel.append(details('Which months meet the two limits?',months));
    }
    yearPanel.append(el('p','pl-muted',`A poor month has less than ${number(POOR_MONTH.hours,0)} hours, or snow-free odds of less than ${number(POOR_MONTH.snowPercent,0)}%. The page shows unknown odds as unknown.`));
    const guide = el('div', 'pl-rule');
    guide.append(el('p', '', year.words.hours), el('p', '', year.words.reachable));
    yearPanel.append(details('How to read this', guide));
    const strip = el('div','pl-year-strip');
    year.months.forEach((month,j)=>{
      const best = [data.north?.[j], data.south?.[j]].filter(Boolean)
        .sort((a,b) => (finite(b.hours) ? b.hours : -Infinity) - (finite(a.hours) ? a.hours : -Infinity))[0];
      const poor = isPoor(best);
      const panel = el('details',`pl-month${poor ? ' pl-poor-month' : ''}`);
      const summary = el('summary');
      summary.append(el('span','pl-month-name',month));
      const brief = !best ? 'The page lists no area.' : poor ? `Poor month · ${hours(best.hours)}`
        : `${hours(best.hours)} · ${finite(best.snow_free_odds) ? number(best.snow_free_odds * 100,0) + '% snow-free' : 'snow unknown'}`;
      summary.append(el('span','pl-month-brief',brief));
      panel.append(summary);
      for (const [side,title] of [['north','North'],['south','South']]) {
        const group = el('div','pl-year-side'); group.append(el('h4','',title));
        for (const [key,label] of [[side,'Best'],[`${side}_reachable`,'Best reachable']]) {
          const entry = data[key]?.[j], row = el('div',`pl-year-entry${isPoor(entry) ? ' pl-poor-entry' : ''}`);
          row.append(el('strong','',label));
          if (!entry) row.append(el('p','pl-muted',`No area has more than ${number(year.min_hours,0)} hours.`));
          else {
            const i = api.areaIndex(entry.id);
            if (isPoor(entry)) row.append(el('p','pl-poor-label','Poor month'));
            row.append(i >= 0 ? areaButton(i) : el('span','',entry.region));
            row.append(el('p','pl-year-figure',hours(entry.hours)));
            row.append(el('p','pl-muted pl-year-figure',snowText(entry)));
            if (access && i >= 0) row.append(el('p','pl-muted',accessText(i)));
          }
          group.append(row);
        }
        panel.append(group);
      }
      strip.append(panel);
    });
    yearPanel.append(strip,caption());
    if (access && airfields?.what_it_is_not) yearPanel.append(el('p','pl-muted',airfields.what_it_is_not));
    const notes = el('div','pl-rule');
    for (const key of ['ranked','south','none']) if (year.words[key]) notes.append(el('p','',year.words[key]));
    yearPanel.append(details('What the year plan counts',notes));
  }

  function compassCard(i,id) {
    if (!alive || !rose || !skyline || targetIndex(id) < 0) return null;
    const node = el('div','pl-compass');
    const count = skyLayout.shape[1], stride = roseLayout.shape[2], offset = pairIndex(i,id)*stride;
    const values = Array.from(rose.slice(offset,offset+count)), status = rose[offset+count];
    const knownRose = status === 0 && values.every(value=>value !== roseLayout.unknown);
    const total = knownRose ? values.reduce((a,b)=>a+b,0) : null;
    const maximum = knownRose ? Math.max(...values) : null;
    const codesHere = Array.from(skyline.slice(i*count,(i+1)*count));
    const edges = skyLayout.elevation_bin_edges_deg, lastCode = edges.length-1;
    const ceiling = target(id).limitDeg;
    function skyRange(code) {
      if (code === skyLayout.unknown || code > lastCode) return null;
      if (code === 0) return {lo:edges[0],hi:edges[0],text:`below ${number(edges[0])}°`};
      if (code === lastCode) return {lo:edges[lastCode-1],hi:null,text:`at least ${number(edges[lastCode-1],2)}°; upper limit unknown`};
      return {lo:edges[code-1],hi:edges[code],text:`${number(edges[code-1],2)}–${number(edges[code],2)}°`};
    }
    const bandText = range => !range ? 'unknown' : range.lo >= ceiling ? 'above the band' : range.hi == null || range.hi > ceiling ? 'can extend above the band' : 'within or below the band';
    node.append(el('p','pl-muted',`${target(id).name} · Sun band ${number(edges[0])}–${number(ceiling,2)}°`));
    const svg = svgNode('svg',{viewBox:'0 0 400 400',role:'img','aria-label':'A compass of the low Sun. North is at the top. The terrain skyline is around the direction shares.'});
    svg.append(svgNode('title',{},'Where the low Sun stands'));
    const center=200, inner=114, outer=166, full=360, sector=full/count;
    const radius=height=>inner+height/edges.at(-1)*(outer-inner);
    const point=(r,degrees)=>[center+r*Math.sin(degrees*Math.PI/180),center-r*Math.cos(degrees*Math.PI/180)];
    const arc=(r,a,b)=>{const p=point(r,a),q=point(r,b);return `M${p} A${r},${r} 0 0 1 ${q}`;};
    const wedge=(r,a,b)=>{const p=point(r,a),q=point(r,b);return `M${center},${center} L${p} A${r},${r} 0 0 1 ${q} Z`;};
    svg.append(svgNode('circle',{cx:center,cy:center,r:(inner+radius(ceiling))/2,fill:'none','stroke-width':radius(ceiling)-inner,class:'pl-sky-band'}));
    [inner,radius(ceiling)].forEach(r=>svg.append(svgNode('circle',{cx:center,cy:center,r,fill:'none',class:'pl-axis'})));
    values.forEach((value,k)=>{
      const start=k*sector, end=(k+1)*sector;
      if (knownRose && total > 0 && value > 0) {
        const path=svgNode('path',{d:wedge(98*Math.sqrt(value/maximum),start+0.7,end-0.7),class:'pl-sector'});
        path.append(svgNode('title',{},`${number(start,0)}–${number(end,0)}°: ${number(value/total*100,1)}% of hours`));svg.append(path);
      }
      const range=skyRange(codesHere[k]);
      if (range) {
        const low=radius(range.lo),high=radius(range.hi ?? edges.at(-1));
        const path=svgNode('path',{d:arc((low+high)/2,start+0.7,end-0.7),fill:'none','stroke-width':Math.max(2,high-low),class:`pl-skyline${range.hi == null ? ' pl-open-skyline' : ''}`});
        path.append(svgNode('title',{},`${number(start,0)}–${number(end,0)}°: ${range.text}; ${bandText(range)}`));svg.append(path);
        if (range.lo >= ceiling) {const p=point(outer+8,start+sector/2);svg.append(svgNode('text',{x:p[0],y:p[1]+3,'text-anchor':'middle',class:'pl-above'},'+'));}
      }
    });
    [['N',200,16],['E',385,204],['S',200,392],['W',15,204]].forEach(([text,x,y])=>svg.append(svgNode('text',{x,y,'text-anchor':'middle',class:'pl-cardinal'},text)));
    if (!knownRose || total === 0) svg.append(svgNode('text',{x:center,y:center,'text-anchor':'middle'},status === 1 ? 'No hours of low Sun' : 'Hours unknown'));
    node.append(svg,caption());
    node.append(el('p','pl-muted','The inner sectors show the share of the hours of low Sun in each direction. The shaded ring shows the Sun band. The outer marks show the skyline ranges.'));
    node.append(el('p','pl-muted','A plus sign shows a skyline above the band. A dashed mark has no known upper limit. A gap shows an unknown skyline sector.'));
    node.append(el('p','pl-muted','In each direction, at least half of the ground in the area can see the sky above the skyline.'));
    if (knownRose && total > 0) {
      const thirds=Array.from({length:3},(_,j)=>values.slice(j*count/3,(j+1)*count/3).reduce((a,b)=>a+b,0));
      const largest=Math.max(...thirds), winners=thirds.map((value,j)=>value===largest?j:null).filter(value=>value!=null);
      if(winners.length===1) {
        const j=winners[0],ranges=codesHere.slice(j*count/3,(j+1)*count/3).map(skyRange);
        const sky=ranges.some(range=>!range) ? 'the skyline is partly unknown there' : ranges.every(range=>range.hi!=null && range.hi<=ceiling) ? 'the skyline stays within or below the band there' : 'some skyline heights can extend above the band there';
        node.append(el('p','pl-finding',`The compass third from ${number(j*full/3,0)}° to ${number((j+1)*full/3,0)}° has the largest share of the hours (${number(largest/total*100,1)}%). ${sky[0].toUpperCase() + sky.slice(1)}.`));
      } else node.append(el('p','pl-finding','Several compass thirds share the largest number of hours of low Sun.'));
    } else node.append(el('p','pl-finding',status===1?'This area has no hours of low Sun after terrain in the counted season.':'The direction shares are unknown for this area.'));
    if(south(i)) node.append(el('p','pl-muted','These are the hours of the rock season, after terrain. Snow is not measured in Antarctica.'));
    const rows=values.map((value,k)=>{const range=skyRange(codesHere[k]);return [`${number(k*sector,0)}–${number((k+1)*sector,0)}°`,knownRose&&total>0?`${number(value/total*100,1)}%`:status===1?'No such hours':'unknown',range?.text||'unknown',bandText(range)];});
    node.append(details('Read the compass numbers',table(['Direction, clockwise from north','Share of hours','Skyline height','Skyline compared with the Sun band'],rows)));
    return node;
  }
  const keep = cleanup => { if (typeof cleanup === 'function') cleanups.push(cleanup); };
  keep(api.addCardSection('pl-compare-pin','Compare this area',pinCard,
    i => pins().includes(api.area(i).id) ? 'The comparison includes this area.' : 'Pin this area to compare its hours with other areas.'));
  keep(api.addCardSection('pl-rehearsal','Rehearsal rules',rehearsalCard, (i,id) => {
    const selected = choice();
    return selected ? `${selected.activity}: ${verdict(i,id,selected).word}.` : 'Select an activity to see how this area meets its rules.';
  }));
  keep(api.addCardSection('pl-compass','Where the low Sun stands',compassCard,
    (i,id) => `The directions of the low Sun and the terrain skyline for ${target(id).name}.`));
  keep(api.setListOrder('rehearse','Selected activity', (i,id)=>{
    const selected=choice(); if(!alive||!selected||!rView)return null;
    const v=verdict(i,id,selected),h=h30(i,id);
    if(v.kind==='unknown'||h==null)return null;
    const group=v.kind==='pass'?3:v.kind==='near'?2:1;
    return group+h/(blocks.h30.unknown/10+1);
  }));
  let lastCompare='',lastYear='';
  const render=()=>{
    if(!alive)return;
    const state=api.getState(); renderChoices();
    const counts = index.summary?.rehearsal?.[state.target]?.north;
    const selected = choice();
    const activity = selected || activities[0];
    const passed = counts?.[activity?.id]?.pass;
    finding.textContent = finite(passed) ? `For ${target(state.target).name}, ${number(passed,0)} northern ${passed === 1 ? 'area passes' : 'areas pass'} ${selected ? 'the selected' : 'the first'} rehearsal rule.`
      : `The plan compares ${number(activities.length,0)} ${activities.length === 1 ? 'activity' : 'activities'} in ${number(api.periods.length,0)} ten-day periods.`;
    const c=JSON.stringify([state.target,state.step,state.compare,state.rehearse]);
    if(c!==lastCompare){renderCompare();lastCompare=c;}
    if(state.target!==lastYear){renderYear();lastYear=state.target;}
  };
  keep(api.onState(render)); render();
  return {destroy(){alive=false;cleanups.reverse().forEach(fn=>fn());root.replaceChildren();root.classList.remove('pl-planner');}};
}
