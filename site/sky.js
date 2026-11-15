// Watch a day: a local, dependency-free consumer of the page API.
const DRAWN = 'Drawn by code from open data; the code was written with AI assistance.';
const NO_MODEL = 'unknown: NASA has no 5 m terrain model of this region';
const NS = 'http://www.w3.org/2000/svg';
const RAD = Math.PI / 180;
const finite = x => typeof x === 'number' && Number.isFinite(x);
const wrap = (x, n = 360) => ((x % n) + n) % n;
let serial = 0;
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (tag === 'details') n.classList.add('fold');
  if (cls === 'sk-chart' || cls === 'sk-moon-chart') n.classList.add('card');
  if (text != null) n.textContent = text;
  return n;
}
function svg(tag, attrs = {}, text) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text != null) n.textContent = text;
  return n;
}
function button(text, action) {
  const n = el('button', 'sk-button btn btn-ghost', text);
  n.type = 'button'; n.addEventListener('click', action); return n;
}
function timeText(minutes) {
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(Math.floor(minutes % 60)).padStart(2, '0')}`;
}
function dateText(day) {
  // A non-leap reference calendar maps the data's ordinal days to month names.
  return new Intl.DateTimeFormat('en-GB', {day: 'numeric', month: 'long', timeZone: 'UTC'})
    .format(new Date(Date.UTC(2001, 0, day)));
}
const direction = az => ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'][Math.round(az / 45) % 8];
function solarTerms(julianDay) {
  // NOAA solar calculator, Julian-century/Meeus form. Constants are astronomical.
  const t = (julianDay - 2451545) / 36525;
  const longitude = wrap(280.46646 + t * (36000.76983 + .0003032*t)) * RAD;
  const anomaly = (357.52911 + t * (35999.05029 - .0001537*t)) * RAD;
  const eccentricity = .016708634 - t * (.000042037 + .0000001267*t);
  const centre = Math.sin(anomaly) * (1.914602 - t * (.004817 + .000014*t))
    + Math.sin(2*anomaly) * (.019993 - .000101*t) + Math.sin(3*anomaly) * .000289;
  const omega = (125.04 - 1934.136*t) * RAD;
  const apparentLongitude = longitude + (centre - .00569 - .00478*Math.sin(omega)) * RAD;
  const obliquity = (23 + (26 + (21.448 - t*(46.815 + t*(.00059 - .001813*t)))/60)/60
    + .00256*Math.cos(omega)) * RAD;
  const y = Math.tan(obliquity/2) ** 2;
  const equation = 4 / RAD * (y*Math.sin(2*longitude) - 2*eccentricity*Math.sin(anomaly)
    + 4*eccentricity*y*Math.sin(anomaly)*Math.cos(2*longitude) - .5*y*y*Math.sin(4*longitude)
    - 1.25*eccentricity*eccentricity*Math.sin(2*anomaly));
  return {decl:Math.asin(Math.sin(obliquity)*Math.sin(apparentLongitude)), equation};
}
function sunAt(lat, lon, midnight, minutes) {
  // Find the instant belonging to this apparent local solar time, including EOT.
  let instant = midnight + (minutes - 4*lon)/1440, terms;
  for (let j=0; j<3; j++) {
    terms = solarTerms(instant);
    instant = midnight + (minutes - 4*lon - terms.equation)/1440;
  }
  const {decl, equation} = solarTerms(instant);
  // The hour angle already uses apparent solar time; do not add EOT a second time.
  const hour = (minutes / 4 - 180) * RAD, phi = lat * RAD;
  const geometric = Math.asin(Math.max(-1, Math.min(1,
    Math.sin(phi)*Math.sin(decl) + Math.cos(phi)*Math.cos(decl)*Math.cos(hour)))) / RAD;
  // Bennett-family refraction, Saemundsson's form for geometric altitude, standard atmosphere.
  // Below -1 degree it is smoothly tapered to zero at -2; deep-night positions stay geometric.
  const base = Math.max(-1, geometric);
  const correction = geometric > -2 && geometric < 89.9
    ? Math.max(0, 1.02 / Math.tan((base + 10.3/(base + 5.11))*RAD) / 60)
      * Math.min(1, geometric + 2) : 0;
  const az = wrap(Math.atan2(Math.sin(hour), Math.cos(hour)*Math.sin(phi) - Math.tan(decl)*Math.cos(phi))/RAD + 180);
  return {height: geometric + correction, az, equation};
}

export async function mount(root, api) {
  if (api.version !== 1) throw new Error('Watch a day needs page API version one.');
  const uid = `sk-${++serial}`, cleanups = [], summaries = new Map(), defaults = new Map();
  const oldNodes = [...root.childNodes];
  let alive = true, frame = 0, playing = false, lastFrame = null, elapsed = 0;
  let current = null, previousState = null, plot = null, dayStats = null;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  root.classList.add('sk-module');
  root.replaceChildren(el('p', 'sk-note', 'The page will show the sky data here.'));
  const read = async (name, bin = false) => {
    try { return await (bin ? api.loadBin(name) : api.loadJSON(name)); } catch { return null; }
  };
  const [manifest, lunar, meta] = await Promise.all([read('planner.json'), read('sunpath.json'), read('meta.json')]);
  const referenceYear = Number(String(meta?.generated || meta?.pipeline_written || '').slice(0,4));
  if (!Number.isInteger(referenceYear) || referenceYear < 1) throw new Error('The data export year is unavailable.');
  // Use calendar month and day from the non-leap period labels, even in a leap reference year.
  const midnightFor = day => {
    const date = new Date(Date.UTC(2001,0,day));
    return Date.UTC(referenceYear,date.getUTCMonth(),date.getUTCDate())/86400000 + 2440587.5;
  };
  let valid = false;
  if (manifest?.areas?.count === api.areaCount && globalThis.crypto?.subtle) {
    const ids = Array.from({length: api.areaCount}, (_, i) => api.area(i)?.id).join('\n');
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ids));
    valid = Array.from(new Uint8Array(hash), x => x.toString(16).padStart(2, '0')).join('') === manifest.areas.ids_sha256;
  }
  const checked = async name => {
    if (!valid || !manifest.files?.[name]) return null;
    const b = await read(name, true);
    return b?.byteLength === manifest.files[name].bytes ? new Uint8Array(b) : null;
  };
  const [rose, skyline] = await Promise.all([checked('rose.bin'), checked('skyline.bin')]);
  const rl = manifest?.files?.['rose.bin']?.layout, sl = manifest?.files?.['skyline.bin']?.layout;
  const sectors = sl?.shape?.[1] || 36, edges = sl?.elevation_bin_edges_deg;
  const maxHeight = 2 * Math.max(...api.targets.map(t => t.limitDeg));
  const number = (n, digits = 1) => finite(n) ? api.fmtNumber(n, digits) : 'unknown';
  const titleFor = i => {
    const a = api.area(i);
    return a.named || `${a.region || 'Area'} · ${a.id}`;
  };
  const targetFor = id => api.targets.find(t => t.id === id) || api.targets[0];
  const noModel = id => (targetFor(id)?.has_model ?? meta?.targets?.find(t => t.id === id)?.has_model) === false;
  const modelNote = id => noModel(id) ? `Lunar terrain comparison: cannot tell. ${NO_MODEL}.` : '';
  const bestPeriod = (i, id) => {
    const hours = api.periodHours(i, id, 3);
    let best = null;
    api.periods.forEach((p, j) => {
      if (finite(hours[p.index]) && (best === null || hours[p.index] > hours[api.periods[best].index])) best = j;
    });
    return best;
  };
  function defaultArea(id) {
    if (defaults.has(id)) return defaults.get(id);
    let best = -1, most = -Infinity;
    for (let i = 0; i < api.areaCount; i++) {
      const h = api.hours(i, id, 3, 'year');
      if (finite(h) && h > most) { best = i; most = h; }
    }
    defaults.set(id, best); return best;
  }
  function skyRange(i, sector) {
    if (!skyline || !edges) return null;
    const code = skyline[i * sectors + sector], last = edges.length - 1;
    if (code === sl.unknown || code > last) return null;
    if (code === 0) return {lo: null, hi: edges[0]};
    return {lo: edges[code - 1], hi: code === last ? null : edges[code]};
  }
  function roseCentre(i, id) {
    const ti = manifest?.targets?.indexOf(id) ?? -1;
    if (!rose || ti < 0) return {az: 0, note: 'Direction shares are unknown. The picture centres on north.'};
    const offset = (i * manifest.targets.length + ti) * rl.shape[2];
    const status = rose[offset + sectors], values = Array.from(rose.slice(offset, offset + sectors));
    if (status !== 0 || values.some(x => x === rl.unknown) || !values.some(x => x > 0)) {
      return {az: 0, note: status === 1 ? 'The page counts no hours of low Sun here. The picture centres on north.' : 'Direction shares are unknown. The picture centres on north.'};
    }
    const k = values.indexOf(Math.max(...values));
    return {az: (k + .5) * 360 / sectors,
      note: `The picture centres on ${number((k + .5) * 360 / sectors, 0)}° ${direction((k + .5) * 360 / sectors)}. This sector has the most counted hours of low Sun.`};
  }
  function sample(i, target, day, minute) {
    const area = api.area(i), s = sunAt(area.lat, area.lon, midnightFor(day), minute);
    const range = skyRange(i, Math.min(sectors - 1, Math.floor(s.az / 360 * sectors)));
    const behind = !range ? 'unknown' : range.hi !== null && s.height >= range.hi ? 'no'
      : range.lo !== null && s.height < range.lo ? 'yes' : 'unknown';
    const band = s.height >= 0 && s.height <= target.limitDeg;
    return {...s, minute, behind, band, clear: band && behind === 'no'};
  }
  function stats(i, target, day) {
    const samples = Array.from({length: 1440}, (_, minute) => sample(i, target, day, minute + .5));
    const clear = samples.filter(s => s.clear), uncertain = samples.filter(s => s.band && s.behind === 'unknown');
    return {samples, clear, hours: clear.length / 60, uncertain: uncertain.length / 60};
  }
  function shadow(s) {
    if (s.height < 0) return 'Sun below the horizon';
    if (s.height === 0 || 1 / Math.tan(s.height * RAD) > 100) return 'longer than 100 m';
    return `${number(1 / Math.tan(s.height * RAD))} m`;
  }
  const heading = el('h2', 'sk-heading', 'Where does the low Sun move in a day?'); heading.tabIndex = -1;
  const head = el('header', 'section-head'), finding = el('p', 'sk-finding finding'), headWords = el('div');
  headWords.append(heading, finding);
  head.append(el('span', 'step-number', '4'), headWords);
  const place = el('p', 'sk-place'), context = el('p', 'sk-note');
  const terrainNote = el('p', 'sk-note sk-model-note'); terrainNote.hidden = true;
  const controls = el('div', 'sk-controls');
  const dateLabel = el('label', 'sk-control'), dateTitle = el('span', 'sk-label', 'Middle day of the period');
  const dateOutput = el('output', 'sk-value'), dateInput = el('input', 'sk-range');
  dateInput.type = 'range'; dateInput.min = 0; dateInput.max = api.periods.length - 1; dateInput.step = 1;
  dateInput.id = `${uid}-date`; dateLabel.htmlFor = dateInput.id;
  dateOutput.htmlFor = dateInput.id; dateLabel.append(dateTitle, dateOutput, dateInput);
  const timeLabel = el('label', 'sk-control'), timeOutput = el('output', 'sk-value'), timeInput = el('input', 'sk-range');
  timeInput.type = 'range'; timeInput.min = 0; timeInput.max = 1440; timeInput.step = 10;
  timeInput.id = `${uid}-time`; timeLabel.htmlFor = timeInput.id; timeOutput.htmlFor = timeInput.id;
  timeLabel.append(el('span', 'sk-label', 'Local solar time'), timeOutput, timeInput);
  const playback = el('div', 'sk-playback');
  const back = button('−10 min', () => moveTime(-10)), play = button('Play', () => playing ? stop() : start());
  const forward = button('+10 min', () => moveTime(10));
  back.setAttribute('aria-label', 'Move back 10 minutes'); forward.setAttribute('aria-label', 'Move forward 10 minutes');
  play.setAttribute('aria-pressed', 'false');
  playback.append(back, play, forward); controls.append(dateLabel, timeLabel, playback);
  const reduced = el('p', 'sk-note', 'Your device asks for reduced motion. Use the time slider or the 10-minute buttons.');
  const main = el('div', 'sk-main'), earth = el('figure', 'sk-earth'), chart = el('div', 'sk-chart');
  const earthCredit = el('figcaption', 'sk-caption', `${DRAWN} The disc is larger than the real Sun, which is approximately 0.5 degrees across.`);
  earth.append(chart, earthCredit);
  const readouts = el('dl', 'sk-readouts'), fields = {};
  for (const [key, label] of [['time','Local solar time'],['height','Sun’s height'],['az','Compass direction'],['band','In the band'],['behind','Behind the hills'],['shadow','Shadow of a 1 m rock']]) {
    const group = el('div', 'sk-reading'); fields[key] = el('dd'); group.append(el('dt', '', label), fields[key]); readouts.append(group);
  }
  main.append(earth, readouts);
  const offscreen = el('p', 'sk-offscreen');
  const bandLabel = el('p', 'sk-band-label'), legend = el('p', 'sk-note legend', 'Thick line: in the band and clear of hills. Thin line: other daylight. Dotted line: below the horizon.');
  const dayFigure = el('figure', 'sk-day'), bar = el('div', 'sk-day-chart'), totals = el('div', 'sk-totals');
  const totalDrawn = el('p'), totalPage = el('p'), uncertainText = el('p', 'sk-note');
  totals.append(totalDrawn, totalPage); dayFigure.append(bar, totals, uncertainText, el('figcaption', 'sk-caption', DRAWN));
  const compareNote = el('p', 'sk-note', 'The drawing uses a simple Sun formula for one day. The page counts the hours for the full period of the data.');
  const periodNote = el('p', 'sk-note');
  const moonBox = el('section', 'sk-moon'), moonDetails = el('details', 'sk-details');
  moonDetails.append(el('summary', '', 'Compare with the Moon'), moonBox);
  const info = el('details', 'sk-details'), infoBody = el('div', 'sk-info');
  info.append(el('summary', '', 'How to read this drawing'), infoBody);
  infoBody.append(
    context,
    el('p', '', `The Earth drawing uses the year ${referenceYear}, the year of the data export.`),
    el('p', '', 'The NOAA solar formula gives the path of the Sun. The Bennett refraction formula, in Saemundsson’s form, adds the refraction of light near the horizon.'),
    el('p', '', 'Local solar noon is 12:00. The formula includes the equation of time. Solar time is different from clock time.'),
    el('p', '', 'The drawing makes the disc larger than the real Sun, thus it is easy to see. The real Sun is approximately 0.5 degrees across.'),
    el('p', '', 'In each direction, at least half of the ground in the area can see the sky above the skyline. The filled shape follows the upper edge of each known range. The shape stops at the Sun ceiling.'),
    el('p', '', 'A plus sign shows terrain above the band, or an unknown upper limit. A question mark shows a gap where the terrain is unknown.'),
    el('p', '', 'If the Sun is inside a skyline range, the page cannot tell if hills hide the Sun. Diagonal lines show these uncertain times. The total includes only the minutes when the Sun is clear of the hills.'),
    el('p', '', 'Snow and cloud do not change this drawing. The page counts the hours after snow and terrain. In Antarctica, the count uses the rock season in place of snow.')
  );
  const tableDetails = el('details', 'sk-details'), table = el('table', 'sk-table');
  tableDetails.append(el('summary', '', 'Read the day hour by hour'), table);
  root.replaceChildren(head, place, terrainNote, controls, reduced, bandLabel, main, offscreen, legend, dayFigure, compareNote, periodNote, moonDetails, info, tableDetails);
  moonDetails.addEventListener('toggle', () => { if (moonDetails.open && current) drawMoon(); });
  if (!valid || !rose || !skyline) infoBody.prepend(el('p', 'sk-status', 'Some area data is unavailable, or it does not match the page. The page shows missing skylines and direction shares as unknown.'));

  function layout(container, height, key, centre, ceiling, label) {
    const width = Math.max(270, Math.round(container.getBoundingClientRect().width || 720));
    const x0 = 38, x1 = width - 14, y0 = 22, y1 = height - 29, span = x1 - x0;
    const x = az => x0 + wrap(az - centre + 180) / 360 * span;
    const y = h => y1 - (h + 2) / (maxHeight + 2) * (y1 - y0);
    const drawing = svg('svg', {viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': label, class: 'sk-strip'});
    drawing.append(svg('title', {}, label));
    const defs = svg('defs'), clip = svg('clipPath', {id: `${uid}-${key}`});
    clip.append(svg('rect', {x:x0, y:y0, width:span, height:y1-y0})); defs.append(clip); drawing.append(defs);
    const layer = svg('g', {'clip-path': `url(#${uid}-${key})`});
    layer.append(svg('rect', {x:x0, y:y(ceiling), width:span, height:y(0)-y(ceiling), class:'sk-band'}));
    for (const h of [-2, 0, ceiling, maxHeight]) {
      layer.append(svg('line', {x1:x0, x2:x1, y1:y(h), y2:y(h), class: h === 0 ? 'sk-horizon' : 'sk-grid'}));
      drawing.append(svg('text', {x:x0-6, y:y(h)+4, 'text-anchor':'end', class:'sk-axis-text'}, `${number(h, h === ceiling ? 2 : h === maxHeight ? 1 : 0)}°`));
    }
    for (const [az, name] of [[0,'N'],[90,'E'],[180,'S'],[270,'W']]) {
      const px = x(az);
      layer.append(svg('line', {x1:px, x2:px, y1:y0, y2:y1, class:'sk-grid'}));
      drawing.append(svg('text', {x:px, y:height-7, 'text-anchor':'middle', class:'sk-cardinal'}, name));
    }
    drawing.append(layer);
    return {drawing, layer, x, y, x0, x1, y0, y1, span, width};
  }
  function segment(paths, key, p, q, geom) {
    let a = geom.x(p.az), b = geom.x(q.az);
    if (b - a > geom.span/2) b -= geom.span;
    if (a - b > geom.span/2) b += geom.span;
    for (const offset of [-geom.span, 0, geom.span]) {
      if (Math.max(a,b)+offset < geom.x0 || Math.min(a,b)+offset > geom.x1) continue;
      const start = `${(a+offset).toFixed(2)},${geom.y(p.height).toFixed(2)}`;
      const end = `${(b+offset).toFixed(2)},${geom.y(q.height).toFixed(2)}`;
      // Keep adjacent samples joined, so short night segments do not restart each dash.
      paths[key] += paths[key].endsWith(`L${start}`) ? `L${end}` : `M${start}L${end}`;
    }
  }
  function drawEarth() {
    if (!current) return;
    const {i, target, day, centre} = current;
    plot = layout(chart, 270, 'earth', centre, target.limitDeg, `The path of the Sun on ${dateText(day)} at ${titleFor(i)}. The drawing shows a full compass, centred on ${number(centre,0)} degrees.`);
    const {layer, x0, x1, y, span} = plot;
    const width = 360 / sectors;
    for (let k = 0; k < sectors; k++) {
      const range = skyRange(i, k), start = wrap(k * width - centre + 180);
      for (const shift of [-360, 0]) {
        const left = x0 + (start+shift)/360*span, right = left + width/360*span;
        if (right <= x0 || left >= x1) continue;
        const midpoint = (Math.max(left,x0) + Math.min(right,x1))/2;
        if (!range) {
          layer.append(svg('text', {x:midpoint,y:y(-1)+4,'text-anchor':'middle',class:'sk-gap'}, '?')); continue;
        }
        const top = Math.min(target.limitDeg, range.hi ?? target.limitDeg);
        const shape = svg('rect', {x:left, y:y(top), width:right-left+.2, height:y(-2)-y(top),class:'sk-terrain'});
        const label = range.lo === null ? `below ${number(range.hi)}°` : range.hi === null ? `at least ${number(range.lo)}°; upper limit unknown` : `${number(range.lo,2)}° to ${number(range.hi,2)}°`;
        shape.append(svg('title', {}, `${number(k*width,0)}° to ${number((k+1)*width,0)}°: skyline ${label}`)); layer.append(shape);
        if (range.hi === null || range.lo >= target.limitDeg || range.hi > target.limitDeg) {
          layer.append(svg('text', {x:midpoint,y:y(target.limitDeg)-4,'text-anchor':'middle',class:'sk-plus'}, '+'));
        }
      }
    }
    const paths = {night:'', other:'', clear:''};
    for (let m = 0; m < 1440; m += 2) {
      const p = sample(i,target,day,m), q = sample(i,target,day,m+2), mid = sample(i,target,day,m+1);
      segment(paths, mid.height < 0 ? 'night' : mid.clear ? 'clear' : 'other', p, q, plot);
    }
    for (const [key,d] of Object.entries(paths)) layer.append(svg('path', {d, class:`sk-track sk-track-${key}`}));
    const halo = svg('radialGradient', {id:`${uid}-sun-halo`});
    halo.append(svg('stop', {offset:0,'stop-opacity':.5,class:'sk-halo-stop'}),svg('stop', {offset:1,'stop-opacity':0,class:'sk-halo-stop'}));
    plot.drawing.querySelector('defs').append(halo);
    plot.sun = svg('g', {class:'sk-sun'});
    plot.sun.append(svg('circle', {r:15,fill:`url(#${uid}-sun-halo)`}), svg('circle', {r:5,class:'sk-disc'}));
    layer.append(plot.sun);
    plot.edge = svg('text', {'text-anchor':'middle',class:'sk-edge'}); plot.drawing.append(plot.edge);
    chart.replaceChildren(plot.drawing); updateTime();
  }
  function drawBar() {
    const width = Math.max(270, Math.round(bar.getBoundingClientRect().width || 900)), x0 = 12, span = width-24;
    const drawing = svg('svg', {viewBox:`0 0 ${width} 50`, role:'img', 'aria-label':'A bar of 24 hours. Solid blocks show low Sun that is clear of the hills. Diagonal lines show times when the terrain clearance is unknown.'});
    const defs = svg('defs'), pattern = svg('pattern', {id:`${uid}-hatch`,width:6,height:6,patternUnits:'userSpaceOnUse'});
    pattern.append(svg('path',{d:'M-1 1L1 -1M0 6L6 0M5 7L7 5',class:'sk-hatch-line'})); defs.append(pattern); drawing.append(defs);
    drawing.append(svg('rect',{x:x0,y:5,width:span,height:14,rx:3,class:'sk-bar-base'}));
    let start = 0;
    const kind = s => s.clear ? 'clear' : s.band && s.behind === 'unknown' ? 'unknown' : 'other';
    while (start < 1440) {
      let end = start+1; const key = kind(dayStats.samples[start]);
      while (end < 1440 && kind(dayStats.samples[end]) === key) end++;
      if (key !== 'other') drawing.append(svg('rect',{x:x0+start/1440*span,y:5,width:(end-start)/1440*span,height:14,
        class:key === 'clear' ? 'sk-bar-clear' : 'sk-bar-unknown', ...(key === 'unknown' ? {fill:`url(#${uid}-hatch)`} : {})}));
      start = end;
    }
    for (const h of [0,6,12,18,24]) drawing.append(svg('text',{x:x0+h/24*span,y:40,'text-anchor':h===0?'start':h===24?'end':'middle',class:'sk-axis-text'},`${String(h).padStart(2,'0')}:00`));
    const cursor = svg('line',{y1:2,y2:23,class:'sk-time-marker'}); drawing.append(cursor); bar.replaceChildren(drawing);
    current.bar = {cursor,x0,span};
  }
  function drawMoon() {
    const mo = lunar?.moon, path = mo?.path;
    const fits = mo?.name && finite(mo.ceiling_deg) && path?.azimuth_deg?.length > 1
      && path.azimuth_deg.length === path.elevation_deg?.length
      && path.azimuth_deg.every(finite) && path.elevation_deg.every(finite);
    if (!fits) { moonBox.replaceChildren(el('p','sk-note','The local data has no suitable Sun track for the Moon.')); return; }
    const figure = el('figure','sk-moon-figure'), drawingBox = el('div','sk-moon-chart'), words = el('div','sk-moon-words');
    words.append(el('h3','',`On the Moon · ${mo.name}`));
    const slow = lunar.shows?.find(s => s.includes(mo.name) && /days.*horizon/.test(s));
    if (slow) words.append(el('p','',slow));
    words.append(el('p','sk-note',`JPL Horizons · ${mo.start_utc} to ${mo.end_utc}.`));
    words.append(el('p','sk-note','This path includes the highest Sun of the year. The calculation uses a smooth Moon. Real lunar hills can hide the Sun.'));
    words.append(el('p','sk-note','The two strips use the same height limits. The lunar strip is centred on north.'));
    if (mo.id !== current.target.id) words.append(el('p','sk-note',`This stored track is for ${mo.name}. The page has no stored track for ${current.target.name}.`));
    figure.append(drawingBox,el('figcaption','sk-caption',DRAWN)); moonBox.replaceChildren(figure,words);
    const g = layout(drawingBox, 190, 'moon', 0, mo.ceiling_deg, `The Sun track from JPL Horizons at ${mo.name}, for ${number(mo.path_trip_days)} Earth days.`);
    const paths = {night:'',other:'',clear:''};
    for (let j = 1; j < path.azimuth_deg.length; j++) {
      const p = {az:path.azimuth_deg[j-1],height:path.elevation_deg[j-1]}, q={az:path.azimuth_deg[j],height:path.elevation_deg[j]};
      segment(paths, (p.height+q.height)/2 < 0 ? 'night' : 'clear',p,q,g);
    }
    for (const [key,d] of Object.entries(paths)) g.layer.append(svg('path',{d,class:`sk-track sk-track-${key}`}));
    const marks = mo.marks;
    if (marks?.azimuth_deg?.length === marks?.elevation_deg?.length) marks.azimuth_deg.forEach((az,j) => {
      g.layer.append(svg('circle',{cx:g.x(az),cy:g.y(marks.elevation_deg[j]),r:2.5,class:'sk-moon-dot'}));
    });
    words.append(el('p','sk-note',`The dots are ${number(mo.marks?.every_hours,0)} hours apart. The curve follows the centre of the Sun.`));
    drawingBox.append(g.drawing);
  }
  function drawTable() {
    const heads = ['Solar time','Height','Direction','In the band','Behind hills','Shadow of a 1 m rock'];
    const cap = el('caption','',`${dateText(current.day)} · ${titleFor(current.i)}`), thead=el('thead'), hr=el('tr'), tbody=el('tbody');
    heads.forEach(t => {const th=el('th','',t);th.scope='col';hr.append(th);});thead.append(hr);
    for (let h = 0; h <= 24; h++) {
      const s = sample(current.i,current.target,current.day,h*60), tr=el('tr');
      const values=[timeText(h*60),`${number(s.height)}°`,`${direction(s.az)} · ${number(s.az,0)}°`,s.band?'yes':'no',s.behind,shadow(s)];
      values.forEach((v,j)=>{const cell=el(j===0?'th':'td','',v);if(j===0)cell.scope='row';cell.dataset.label=heads[j];tr.append(cell);});tbody.append(tr);
    }
    table.replaceChildren(cap,thead,tbody);
  }
  function updateTime() {
    if (!current || !plot) return;
    const s = sample(current.i,current.target,current.day,current.minute), t=timeText(current.minute);
    timeInput.value = current.minute; timeInput.setAttribute('aria-valuetext', `${t} local solar time`); timeOutput.value = t;
    fields.time.textContent=t; fields.height.textContent=`${number(s.height)}°`;
    fields.az.textContent=`${direction(s.az)} · ${number(s.az,0)}°`; fields.band.textContent=s.band?'yes':'no';
    fields.behind.textContent=s.behind; fields.shadow.textContent=shadow(s);
    fields.band.dataset.active=String(s.clear);
    const visible=s.height>=-2 && s.height<=maxHeight;
    plot.sun.setAttribute('visibility',visible?'visible':'hidden');
    plot.sun.setAttribute('transform',`translate(${plot.x(s.az)},${plot.y(s.height)})`);
    plot.sun.classList.toggle('sk-sun-hidden',s.behind==='yes');
    plot.edge.textContent=visible?'':s.height>maxHeight?'↑':'↓';
    plot.edge.setAttribute('x',plot.x(s.az)); plot.edge.setAttribute('y',s.height>maxHeight?plot.y0+11:plot.y1-2);
    offscreen.textContent = s.height > maxHeight ? `The Sun is above this strip, at ${number(s.height)}°.`
      : s.height < -2 ? 'The Sun is below the horizon and this strip.' : s.height < 0 ? 'The Sun is below the horizon.'
      : s.behind === 'yes' ? 'The Sun is behind the hills.' : s.behind === 'unknown' ? 'The skyline does not show if hills hide the Sun.' : 'The centre of the Sun is clear of the skyline.';
    if (current.bar) {
      const x=current.bar.x0+current.minute/1440*current.bar.span;
      current.bar.cursor.setAttribute('x1',x);current.bar.cursor.setAttribute('x2',x);
    }
  }
  function drawDay() {
    const {i,target,period} = current, p=api.periods[period];
    current.day = Math.round((p.firstDay+p.lastDay)/2);
    dayStats=stats(i,target,current.day);
    finding.textContent = `On ${dateText(current.day)}, this drawing counts ${dayStats.uncertain > 0 ? 'at least ' : ''}${number(dayStats.hours)} hours of low Sun that are clear of the hills.`;
    dateInput.value=period;dateInput.setAttribute('aria-valuetext',`${dateText(current.day)}; ${p.label}`);
    dateOutput.value=`${dateText(current.day)} · ${p.label}`;
    bandLabel.textContent=`${target.name} · horizon to ${number(target.limitDeg,2)}°`;
    const h=api.periodHours(i,target.id,3)[p.index];
    totalDrawn.replaceChildren(el('strong','',`${dayStats.uncertain>0?'at least ':''}${number(dayStats.hours)} h`),document.createTextNode(' in this drawing'));
    totalPage.replaceChildren(el('strong','',finite(h)?`${number(h)} h`:'unknown'),document.createTextNode(' · the count of the page for this ten-day period'));
    uncertainText.textContent=dayStats.uncertain>0 ? `${number(dayStats.uncertain)} more hours in the band have an unknown terrain clearance. Diagonal lines show those times.` : 'The terrain clearance is known for each minute in the band.';
    periodNote.textContent=p.lastDay-p.firstDay+1 !== 10 ? `In the data of the page, this last period has ${p.lastDay-p.firstDay+1} days.` : '';
    drawEarth();drawBar();drawMoon();drawTable();updateTime();
  }
  function sync(state) {
    if (!alive) return;
    const target=targetFor(state.target), chosen=api.areaIndex(state.place), i=chosen>=0?chosen:defaultArea(target.id);
    terrainNote.textContent=modelNote(target.id);terrainNote.hidden=!terrainNote.textContent;
    if (i<0) {context.textContent='For this lunar region, no area has a known number of hours in a year.';return;}
    const initial=!current, changed=initial || current.i!==i || current.target.id!==target.id;
    const explicitPeriod=state.skyPeriod!=null && state.skyPeriod!=='' && Number.isInteger(+state.skyPeriod) && +state.skyPeriod>=0 && +state.skyPeriod<api.periods.length;
    const explicitTime=state.skyTime!=null && state.skyTime!=='' && finite(+state.skyTime);
    const best=bestPeriod(i,target.id), centre=roseCentre(i,target.id);
    context.textContent=`${chosen<0?'No place is open. This area has the most counted hours in a year. ':''}${centre.note}${best===null?' The best period is unknown.':''}`;
    if(changed) {
      stop();
      const allowSaved=!current || state.skyPeriod!==previousState?.skyPeriod;
      current={i,target,period:allowSaved&&explicitPeriod?+state.skyPeriod:best??0,minute:explicitTime?Math.max(0,Math.min(1440,Math.round(+state.skyTime/10)*10)):0,centre:centre.az};
      place.textContent=titleFor(i);
      drawDay();
    } else if(explicitPeriod && state.skyPeriod!==previousState?.skyPeriod && current.period!==+state.skyPeriod) {
      stop();current.period=+state.skyPeriod;drawDay();
    }
    if(!changed && explicitTime && state.skyTime!==previousState?.skyTime) {stop();current.minute=Math.max(0,Math.min(1440,Math.round(+state.skyTime/10)*10));updateTime();}
    previousState={...state};
    // Initial mounting reads defaults without changing the shared link. A late
    // mount after a stopped tour must not add state to the restored view.
    if(!initial && changed && (!explicitPeriod || +state.skyPeriod!==current.period)) api.setState({skyPeriod:current.period});
  }
  function commitTime() {if(current)api.setState({skyTime:current.minute});}
  function stop() {
    playing=false;cancelAnimationFrame(frame);frame=0;lastFrame=null;elapsed=0;
    play.textContent='Play';play.setAttribute('aria-pressed','false');
  }
  function tick(now) {
    if(!playing || !alive)return;
    if(lastFrame!==null)elapsed+=now-lastFrame;
    lastFrame=now;
    if(elapsed>=12000/144) {
      const steps=Math.floor(elapsed/(12000/144));elapsed-=steps*(12000/144);
      current.minute=wrap(current.minute+steps*10,1440);updateTime();
    }
    frame=requestAnimationFrame(tick);
  }
  function start() {if(!alive||playing||motion.matches||!current)return;playing=true;play.textContent='Pause';play.setAttribute('aria-pressed','true');frame=requestAnimationFrame(tick);}
  function moveTime(delta) {if(!current)return;stop();current.minute=Math.max(0,Math.min(1440,current.minute+delta));updateTime();commitTime();}
  dateInput.addEventListener('input',()=>{if(!current)return;stop();current.period=+dateInput.value;drawDay();});
  dateInput.addEventListener('change',()=>{if(current)api.setState({skyPeriod:current.period});});
  timeInput.addEventListener('input',()=>{if(!current)return;stop();current.minute=+timeInput.value;updateTime();});
  timeInput.addEventListener('change',commitTime);
  const motionChange=()=>{if(motion.matches)stop();play.disabled=motion.matches;reduced.hidden=!motion.matches;};
  motion.addEventListener('change',motionChange);cleanups.push(()=>motion.removeEventListener('change',motionChange));motionChange();
  const hide=()=>{if(document.hidden)stop();};document.addEventListener('visibilitychange',hide);cleanups.push(()=>document.removeEventListener('visibilitychange',hide));
  function summary(i,id) {
    const key=`${i}:${id}`;if(summaries.has(key))return summaries.get(key);
    const best=bestPeriod(i,id);let text;
    if(best===null)text='The best period is unknown for this area.';
    else {
      const p=api.periods[best],day=Math.round((p.firstDay+p.lastDay)/2),s=stats(i,targetFor(id),day);
      if(s.hours===0)text=s.uncertain>0?`On ${dateText(day)}, the terrain clearance is unknown for ${number(s.uncertain)} hours of low Sun.`:`On ${dateText(day)}, this drawing finds no hours of low Sun that are known to be clear of the hills.`;
      else {
        const sx=s.clear.reduce((v,p)=>v+Math.sin(p.az*RAD),0),sy=s.clear.reduce((v,p)=>v+Math.cos(p.az*RAD),0);
        const dir=Math.hypot(sx,sy)/s.clear.length>.35?`mostly towards the ${direction(wrap(Math.atan2(sx,sy)/RAD))}`:'in several directions';
        text=`On ${dateText(day)}, ${number(s.hours)} hours are in the band and clear of the hills. In these hours, the Sun is ${dir}.`;
      }
    }
    if(noModel(id))text+=` ${modelNote(id)}`;
    summaries.set(key,text);return text;
  }
  const card=api.addCardSection('sky','Watch a day here',(i,id)=>{
    if(!alive)return null;
    const content=el('div','sk-card');content.append(el('p','',summary(i,id)));
    content.append(button('Watch a day here',()=>{
      stop();const best=bestPeriod(i,id);
      api.setState({place:api.area(i).id,target:id,skyPeriod:best,skyTime:0,go:'sky'});
      root.scrollIntoView({behavior:'auto',block:'start'});heading.focus({preventScroll:true});
    }));return content;
  },summary);
  if(typeof card==='function')cleanups.push(card);
  const unsubscribe=api.onState(sync);if(typeof unsubscribe==='function')cleanups.push(unsubscribe);
  sync(api.getState());
  let lastWidth=0;
  const observer=new ResizeObserver(()=>{
    const width=Math.round(chart.getBoundingClientRect().width);
    if(current && width!==lastWidth) {lastWidth=width;drawEarth();drawBar();drawMoon();updateTime();}
  });observer.observe(chart);cleanups.push(()=>observer.disconnect());
  const tourActions={
    play:start,stop,
    snapshot(){return {current:current?{...current}:null,playing};},
    restore(saved){
      if(!alive||!saved)return;stop();
      const state=api.getState(),target=targetFor(state.target),chosen=api.areaIndex(state.place),i=chosen>=0?chosen:defaultArea(target.id);
      // Shared state is restored first. Preserve the local time even when the
      // animation or an unfinished slider change did not write it to the link.
      if(saved.current&&saved.current.i===i&&saved.current.target.id===target.id){
        current={...saved.current};previousState={...state};place.textContent=titleFor(i);drawDay();
        if(saved.playing)start();
      }
    },
  };
  root.tourActions=tourActions;
  return {destroy(){if(!alive)return;alive=false;stop();if(root.tourActions===tourActions)delete root.tourActions;cleanups.reverse().forEach(fn=>fn());root.classList.remove('sk-module');root.replaceChildren(...oldNodes);}};
}
