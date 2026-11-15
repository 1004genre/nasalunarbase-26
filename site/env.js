// Sunlight, UV, clear days and haze: one part of the place card, a short note in the lists, and a
// section that says what the four figures are and are not. Every figure and sentence comes from
// data/environment.json and data/environment.bin (scripts/export_site_environment.py) or from api.
// Unknown reads "unknown", never 0.

const CARD_ID = 'env';
const CARD_TITLE = 'Sunlight, UV, clear days and haze here';
const ABOUT_TITLE = 'What do sunlight, UV, clear days and haze show?';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (tag === 'details') node.classList.add('fold');
  if (className === 'env-about-part') node.classList.add('card');
  if (className === 'env-tag') node.classList.add('tag');
  if (text != null) node.textContent = text;
  return node;
}

function sentencesList(sentences, className) {
  const list = el('ul', className);
  for (const sentence of sentences || []) list.append(el('li', null, sentence));
  return list;
}

export async function mount(root, api) {
  const [doc, buffer] = await Promise.all([api.loadJSON('environment.json'), api.loadBin('environment.bin')]);
  const layout = doc.layout;
  const [count, fieldCount, monthCount] = layout.shape;
  const added = [];
  const stops = [];
  const oldNodes = [...root.childNodes];
  const headingTag = 'h2', subTag = 'h3';

  const lined = count === api.areaCount && api.area(0)?.id === doc.areas.first_id
    && api.area(count - 1)?.id === doc.areas.last_id && buffer.byteLength === layout.bytes;
  if (!lined) {
    const line = el('p', 'status env-status', 'The environment file does not match the areas on this page. Thus, these figures are unavailable.');
    root.append(line); added.push(line);
    return { destroy() { for (const node of added) node.remove(); } };
  }

  const view = new DataView(buffer);
  const fieldIndex = new Map(layout.fields.map((name, k) => [name, k]));
  const bytes = Uint16Array.BYTES_PER_ELEMENT;
  const value = (i, field, month) => {
    const k = fieldIndex.get(field);
    if (k == null || !Number.isInteger(i) || i < 0 || i >= count) return null;
    const raw = view.getUint16(((i * fieldCount + k) * monthCount + month) * bytes, layout.byte_order === 'little-endian');
    return raw === layout.unknown ? null : raw / layout.divide_by[field];
  };
  const months = (i, field) => Array.from({ length: monthCount }, (_, m) => value(i, field, m));
  const groups = new Map(doc.groups.map((group) => [group.key, group]));
  const strip = doc.strip;
  const fmt = (x, digits) => api.fmtNumber(x, digits);
  const monthName = (m) => layout.months[m];

  // The area's best ten-day periods for a lunar region: the terrain step, or the snow-free step when the
  // area has no terrain hours at all. Ties keep the calendar order.
  function bestPeriods(i, targetId) {
    let step = strip.best_from_step, hours = api.periodHours(i, targetId, step), fellBack = false;
    if (!Array.from(hours).some(Number.isFinite)) {
      step = strip.fallback_step; hours = api.periodHours(i, targetId, step); fellBack = true;
    }
    const ranked = Array.from(hours, (h, index) => ({ h, index }))
      .filter((p) => Number.isFinite(p.h) && p.h > 0)
      .sort((a, b) => b.h - a.h || a.index - b.index)
      .slice(0, strip.best_periods);
    const monthsOfBest = [];
    for (const p of ranked) {
      const m = api.periods[p.index].month - 1;
      if (!monthsOfBest.includes(m)) monthsOfBest.push(m);
    }
    return { step, fellBack, periods: ranked.map((p) => api.periods[p.index]), months: monthsOfBest };
  }

  // A small twelve-month strip: one bar a month, an outline bar behind for a second series, unknown
  // drawn as a dashed box with a question mark, a month without sunlight drawn pale.
  function drawStrip(series, behind, marked, sunless, digits, label, scaleTop) {
    const figure = el('figure', 'env-strip-figure');
    const known = [...series, ...(behind || [])].filter((x) => x != null);
    const top = scaleTop ?? (known.length ? Math.max(...known) : null);
    const box = el('div', 'env-strip');
    box.style.setProperty('--env-months', String(monthCount));
    const said = [];
    for (let m = 0; m < monthCount; m += 1) {
      const cell = el('div', 'env-month');
      if (marked.includes(m)) cell.classList.add('env-best');
      if (sunless[m]) cell.classList.add('env-sunless');
      const bars = el('div', 'env-bars');
      if (behind) {
        const back = el('span', 'env-bar env-bar-behind');
        if (behind[m] == null) back.classList.add('env-bar-none');
        else back.style.setProperty('--env-h', String(top ? behind[m] / top : 0));
        bars.append(back);
      }
      const bar = el('span', 'env-bar');
      if (series[m] == null) { bar.classList.add('env-unknown'); bar.textContent = '?'; }
      else bar.style.setProperty('--env-h', String(top ? series[m] / top : 0));
      if (series[m] === 0) bar.classList.add('env-zero');
      bars.append(bar);
      cell.append(bars, el('span', 'env-month-name', monthName(m).slice(0, 1)));
      box.append(cell);
      said.push(`${monthName(m)} ${series[m] == null ? strip.unknown_words : fmt(series[m], digits)}`
        + (behind ? ` (${behind[m] == null ? strip.unknown_words : fmt(behind[m], digits)})` : '')
        + (sunless[m] ? ', no sunlight' : ''));
    }
    box.setAttribute('role', 'img');
    box.setAttribute('aria-label', `${label} by month: ${said.join(', ')}.`);
    figure.append(box, el('figcaption', 'env-caption', strip.caption));
    return figure;
  }

  function row(group, i, best, sunless, targetId) {
    const wrap = el('div', 'env-row');
    wrap.dataset.envRow = group.key;
    const title = el('h5', 'env-row-title', group.heading);
    wrap.append(title);
    const [field, second] = group.fields;
    const main = months(i, field), behind = second ? months(i, second) : null;
    let shown = main, unit = group.unit, words = group.label_words, fallback = false;
    if (group.key === 'clear_days' && best.months.some((m) => main[m] == null)) {
      const cloud = months(i, doc.clear_days_fallback.field);
      if (best.months.some((m) => main[m] == null && cloud[m] != null)) {
        shown = main.map((x, m) => (x == null ? cloud[m] : x)); fallback = true;
        unit = group.fallback_unit; words = group.fallback_words;
      }
    }
    const values = el('p', 'env-values');
    if (!best.months.length) values.textContent = strip.no_best_words;
    else {
      values.textContent = best.months.map((m) => {
        let text = `${monthName(m)}: ${shown[m] == null ? strip.unknown_words : fmt(shown[m], group.digits)}`;
        if (shown[m] != null && (group.unit_inline || fallback)) text += ` ${unit}`;
        if (behind) text += ` (clear sky ${behind[m] == null ? strip.unknown_words : fmt(behind[m], group.digits)})`;
        return text;
      }).join('; ');
    }
    const unitLine = el('p', 'env-unit');
    unitLine.append(el('span', 'env-unit-name', unit), el('span', 'env-tag', doc.tag));
    wrap.append(values, el('p', 'env-words', words), unitLine);
    if (fallback) wrap.classList.add('env-fallback');
    wrap.append(drawStrip(shown, behind, best.months, sunless, group.digits, group.heading, fallback ? null : group.scale_top));
    const moon = group.moon_by_target ? group.moon_by_target[targetId] : group.moon;
    if (moon && moon.length) {
      const line = el('p', 'env-moon');
      line.append(el('span', 'env-moon-label', 'On the Moon: '), document.createTextNode(moon.join(' ')));
      if ((moon.join(' ').match(/[.!?](?:\s|$)/g) || []).length > 2) {
        const more = el('details', 'env-source');
        more.append(el('summary', null, 'On the Moon'), sentencesList(moon));
        wrap.append(more);
      } else wrap.append(line);
    }
    return wrap;
  }

  function cardPart(i, targetId) {
    if (!Number.isInteger(i) || i < 0 || i >= count) return null;
    const part = el('div', 'env-card');
    const best = bestPeriods(i, targetId);
    const clearSun = months(i, 'sun_clear_kwh_m2_day');
    const sunless = clearSun.map((x) => x === 0);
    const lead = el('p', 'env-lead');
    if (best.periods.length) lead.textContent = `Best ten-day periods here: ${best.periods.map((p) => p.label).join(', ')}.`;
    else lead.textContent = strip.no_best_words;
    part.append(lead);
    if (best.fellBack) part.append(el('p', 'env-note', strip.step_fallback_words));
    for (const key of ['sunlight', 'uv', 'clear_days', 'haze']) {
      const group = groups.get(key);
      if (group) part.append(row(group, i, best, sunless, targetId));
    }
    const notes = [strip.best_words, strip.scale_words];
    if (sunless.some(Boolean)) notes.push(strip.sunless_words);
    const guide = el('details', 'env-source');
    guide.append(el('summary', null, 'How to read this'), el('p', 'env-note', notes.join(' ')));
    part.append(guide);
    part.append(el('p', 'env-note', doc.general[0]));
    return part;
  }

  function cardSummary(i, targetId) {
    if (!Number.isInteger(i) || i < 0 || i >= count) return 'The environment figures are unknown for this area.';
    const best = bestPeriods(i, targetId);
    return best.periods.length ? `Of the ten-day periods with known hours, the best here is ${best.periods[0].label}.` : strip.no_best_words;
  }

  function listNote(i, targetId) {
    if (!Number.isInteger(i) || i < 0 || i >= count) return null;
    const best = bestPeriods(i, targetId);
    if (!best.months.length) return null;
    const m = best.months[0], days = value(i, 'clear_days', m);
    if (days == null) return null;
    return `Clear-sky days in ${monthName(m)}: ${fmt(days, groups.get('clear_days').digits)} a month`;
  }

  // the section in root: what the figures are and are not, from the data file's own sentences
  const about = el('section', 'env-about');
  about.setAttribute('aria-labelledby', 'env-about-heading');
  function drawAbout() {
    const state = api.getState ? api.getState() : {};
    about.replaceChildren();
    const heading = el(headingTag, 'env-about-heading', ABOUT_TITLE);
    heading.id = 'env-about-heading';
    const head = el('header', 'section-head');
    const words = el('div');
    words.append(heading, el('p', 'env-finding finding', `The file has data for ${fmt(count, 0)} areas and ${fmt(groups.size, 0)} environment factors.`));
    head.append(el('span', 'step-number', '+'), words);
    const general = el('details', 'env-source env-general');
    general.append(el('summary', null, 'How to read these figures'), sentencesList(doc.general));
    about.append(head, general);
    const grid = el('div', 'env-about-grid');
    for (const key of ['sunlight', 'uv', 'clear_days', 'haze']) {
      const group = groups.get(key);
      if (!group) continue;
      const box = el('div', 'env-about-part');
      box.append(el(subTag, 'env-about-title', group.heading));
      const guide = el('details', 'env-source');
      guide.append(el('summary', null, 'How to read this'), el('p', 'env-about-label', 'What it is'),
        sentencesList(group.is), el('p', 'env-about-label', 'What it is not'), sentencesList(group.is_not));
      const moon = group.moon_by_target ? group.moon_by_target[state.target] : group.moon;
      if (moon && moon.length) guide.append(el('p', 'env-about-label', 'On the Moon'), sentencesList(moon));
      box.append(guide);
      const more = el('details', 'env-source');
      more.append(el('summary', null, 'Source and definition'));
      for (const name of group.fields) {
        const field = doc.fields[name];
        if (!field) continue;
        const dl = el('dl', 'env-source-list');
        const add = (term, text) => { if (text) dl.append(el('dt', null, term), el('dd', null, text)); };
        add('Parameter', `${field.parameter} (${field.name_in_the_service})`);
        add('In the service\'s words', field.definition_in_the_service);
        add('Unit in the service', field.unit_in_the_service);
        add('Unit on this page', field.unit_words);
        add('Data set', (field.source_named_by_the_service || []).join(', '));
        add('Grid', field.grid);
        add('Years that the service names', field.period_named_by_the_service);
        more.append(dl);
      }
      more.append(el('p', 'env-tag', `${doc.tag}. ${doc.service}.`));
      box.append(more);
      grid.append(box);
    }
    about.append(grid);
  }
  drawAbout();
  root.replaceChildren(about); added.push(about);

  stops.push(api.addCardSection(CARD_ID, CARD_TITLE, cardPart, cardSummary));
  stops.push(api.addListNote(listNote));
  if (api.onState) {
    let target = api.getState().target;
    stops.push(api.onState((state) => { if (state.target !== target) { target = state.target; drawAbout(); } }));
  }

  return {
    destroy() {
      for (const stop of stops) if (typeof stop === 'function') stop();
      for (const node of added) node.remove();
      root.replaceChildren(...oldNodes);
    },
  };
}
