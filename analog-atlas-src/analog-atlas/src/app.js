(() => {
  "use strict";
  const M = MODEL;
  const $ = (s, r = document) => r.querySelector(s);
  const h = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "html") n.innerHTML = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(k));
    return n;
  };
  const reduceMotion = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PBY = Object.fromEntries(M.PARAMS.map((p) => [p.id, p]));
  const pct = (x) => Math.round(x * 100);
  const fmtLat = (v) => `${Math.abs(v).toFixed(2)}° ${v < 0 ? "S" : "N"}`;
  const fmtLon = (v) => `${Math.abs(v).toFixed(2)}° ${v < 0 ? "W" : "E"}`;
  const STATUS = {
    established: { label: "Long-running analog site", short: "Long-running analog" },
    studied: { label: "Studied as an analog", short: "Studied" },
    candidate: { label: "Under-studied candidate", short: "Under-studied" },
  };

  /* ---------- State ---------- */
  const state = {
    body: "moon",
    targetId: "m-gerlache",
    preset: "balanced",
    weights: M.presetWeights("balanced"),
    preferAccess: false,
    focus: null,
    selected: null,
    hover: null,
    onlyCandidates: false,
    layers: { deserts: true, ice: true, night: true },
    spin: !reduceMotion,
    sites: M.SITES,
    targets: M.TARGETS,
    results: [],
  };
  const target = () => state.targets.find((t) => t.id === state.targetId) || state.targets[0];
  const shown = () => state.results.filter((r) => !state.onlyCandidates || r.site.status === "candidate");

  /* ---------- Colour ---------- */
  const RAMP = ["#2d3b66", "#3b78a2", "#6cc0b0", "#f1e8a6"];
  let lo = 0.3, hi = 0.75;
  let scoreScale = d3.scaleLinear().domain([0.3, 0.45, 0.6, 0.75]).range(RAMP).interpolate(d3.interpolateLab).clamp(true);
  function rescale() {
    const v = shown().map((r) => r.score);
    lo = Math.min(...v); hi = Math.max(...v); if (hi - lo < 0.05) { lo -= 0.025; hi += 0.025; }
    scoreScale = d3.scaleLinear().domain([0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3)).range(RAMP).interpolate(d3.interpolateLab).clamp(true);
  }
  const simScale = d3.scaleLinear().domain([0, 0.33, 0.66, 1]).range(RAMP).interpolate(d3.interpolateLab).clamp(true);
  const colorOf = (r) => (state.focus ? (r.sims[state.focus] == null ? "#55627d" : simScale(r.sims[state.focus])) : scoreScale(r.score));
  const valOf = (r) => (state.focus ? r.sims[state.focus] ?? 0 : r.score);

  /* ---------- Compute ---------- */
  function compute() {
    const t = target();
    state.results = state.sites
      .map((s) => ({ site: s, ...M.score(s, t, state.weights, { preferAccess: state.preferAccess }) }))
      .sort((a, b) => b.score - a.score);
    state.results.forEach((r, i) => (r.rank = i + 1));
    rescale();
  }

  /* ---------- Left panel ---------- */
  function renderBodyToggle() {
    document.body.dataset.body = state.body;
    document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.body === state.body)));
  }
  function renderTargets() {
    const ul = $("#targets");
    ul.replaceChildren(
      ...state.targets
        .filter((t) => t.body === state.body)
        .map((t) =>
          h("li", {},
            h("button", { "aria-pressed": String(t.id === state.targetId), onclick: () => setTarget(t.id) },
              h("span", { class: "t-name" }, t.name),
              h("span", { class: "t-meta" }, `${t.kind}, ${fmtLat(t.lat)}`)
            )
          )
        )
    );
  }
  function renderPresets() {
    $("#presets").replaceChildren(
      ...M.PRESETS.map((p) =>
        h("button", { class: "chip", "aria-pressed": String(state.preset === p.id), onclick: () => applyPreset(p.id) }, p.name)
      )
    );
  }
  function renderWeights() {
    const wrap = $("#weights");
    wrap.replaceChildren(
      ...M.GROUPS.map((g, gi) => {
        const rows = M.PARAMS.filter((p) => p.g === g.id).map((p) => {
          const w = state.weights[p.id];
          const out = h("output", { class: "num", for: `w-${p.id}`, id: `o-${p.id}` }, fmtW(w));
          const name = h("button", { class: "wname", id: `n-${p.id}`, "aria-pressed": String(state.focus === p.id), title: p.scale,
            onclick: () => setFocus(state.focus === p.id ? null : p.id) }, p.name);
          const range = h("input", { type: "range", id: `w-${p.id}`, min: 0, max: 3, step: 0.5, value: w, "aria-labelledby": `n-${p.id}`,
            oninput: (e) => { state.weights[p.id] = +e.target.value; out.textContent = fmtW(+e.target.value); row.classList.toggle("off", +e.target.value === 0); state.preset = null; renderPresets(); scheduleUpdate(); } });
          const row = h("div", { class: `wrow${w === 0 ? " off" : ""}`, "data-id": p.id }, name, range, out);
          if (state.focus === p.id) row.append(describe(p));
          return row;
        });
        return h("details", { class: "wg", open: gi < 2 || M.PARAMS.some((p) => p.g === g.id && p.id === state.focus) }, h("summary", {}, g.name), ...rows);
      })
    );
  }
  const fmtW = (w) => (w === 0 ? "off" : `×${w}`);
  function describe(p) {
    const d = h("div", { class: "wdesc" },
      h("div", {}, h("b", {}, "Scale: "), p.scale),
      h("div", {}, h("b", {}, "Earth: "), p.src.earth),
      h("div", {}, h("b", {}, "Moon: "), p.src.moon),
      h("div", {}, h("b", {}, "Mars: "), p.src.mars)
    );
    if (p.invertible) {
      const cb = h("input", { type: "checkbox", id: "prefer-access", checked: state.preferAccess, onchange: (e) => { state.preferAccess = e.target.checked; scheduleUpdate(); } });
      d.append(h("label", { for: "prefer-access" }, cb, "Reward easy access instead of isolation"));
    }
    return d;
  }
  function renderGaps() {
    const g = M.GAPS[state.body];
    const tName = state.body === "moon" ? "Moon" : "Mars";
    const card = (name, tv, ev, how) =>
      h("div", { class: "gap" }, h("span", { class: "g-name" }, name),
        h("div", { class: "g-row" }, h("span", {}, tName), h("span", {}, tv)),
        h("div", { class: "g-row" }, h("span", {}, "Best on Earth"), h("span", {}, ev)),
        h("p", {}, how));
    $("#gaps").replaceChildren(
      card("Gravity", g.gravity, "9.81 m/s² everywhere", "Bridge with parabolic flights (tens of seconds per parabola) and offload rigs such as NASA's ARGOS."),
      card("Air pressure", g.pressure, "≈ 330 mbar on Everest", "Bridge with thermal-vacuum chambers. Stratospheric balloons near 35 km sit at about 6 mbar, the Mars surface value."),
      card("Radiation", g.radiation, M.GAPS.earth.radiation, "Earth's field and air shield every site. Bridge with heavy-ion beams at NASA's Space Radiation Laboratory.")
    );
  }

  /* ---------- Right panel ---------- */
  function shapeSVG(status, color, size = 12) {
    const c = size / 2;
    const inner = status === "candidate"
      ? `<rect x="${c - 3.6}" y="${c - 3.6}" width="7.2" height="7.2" transform="rotate(45 ${c} ${c})" fill="${color}"/>`
      : status === "studied"
        ? `<circle cx="${c}" cy="${c}" r="3.8" fill="none" stroke="${color}" stroke-width="2"/>`
        : `<circle cx="${c}" cy="${c}" r="4.4" fill="${color}"/>`;
    const s = h("span", { "aria-hidden": "true" });
    s.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${inner}</svg>`;
    return s;
  }
  function renderRanking() {
    const list = shown();
    $("#rank-count").textContent = `${list.length} sites`;
    $("#ranking").replaceChildren(
      ...list.map((r, i) => {
        const col = colorOf(r);
        const v = valOf(r);
        return h("li", {},
          h("button", { "aria-current": String(r.site.id === state.selected), onclick: () => select(r.site.id, true) },
            h("span", { class: "rk num" }, String(i + 1)),
            shapeSVG(r.site.status, col),
            h("span", { class: "rn" }, h("b", {}, r.site.name), h("span", {}, r.site.place)),
            h("span", { class: "bar" }, h("i", { style: `width:${pct(v)}%;background:${col}` })),
            h("span", { class: "rs num" }, String(pct(v)))
          )
        );
      })
    );
  }

  function topMinerals(min) {
    const tot = min.reduce((a, b) => a + b, 0) || 1;
    return min.map((a, i) => [M.MINERALS[i], a / tot]).sort((a, b) => b[1] - a[1]).filter((x) => x[1] > 0.04).slice(0, 3).map(([n, a]) => `${n} ${pct(a)}%`).join(", ");
  }
  function detail(p, site, t) {
    if (p.kind === "num") {
      const a = site.x[p.id], b = t.x[p.id];
      if (a == null || b == null) return "no data";
      return `Site ${p.raw(a)}; target ${p.raw(b)}`;
    }
    if (p.kind === "tags") {
      const dict = p.tagKey === "lf" ? M.LANDFORMS : M.MATERIALS;
      const S = new Set(site[p.tagKey].split(" "));
      const tt = t[p.tagKey].split(" ");
      const have = tt.filter((x) => S.has(x)).map((x) => dict[x]);
      const miss = tt.filter((x) => !S.has(x)).map((x) => dict[x]);
      return [have.length ? `Shares ${have.join(", ")}` : "", miss.length ? `missing ${miss.join(", ")}` : ""].filter(Boolean).join("; ");
    }
    if (p.kind === "vec") return `Site ${topMinerals(site.min)}; target ${topMinerals(t.min)}`;
    return "Modelled 0.4–2.5 µm reflectance; see the spectra chart";
  }

  function renderDossier() {
    const box = $("#dossier");
    const r = state.results.find((x) => x.site.id === state.selected);
    if (!r) { box.replaceChildren(h("p", { class: "hint" }, "Select a site on the globe or in the list to see how it compares.")); return; }
    const s = r.site, t = target();
    const active = M.PARAMS.filter((p) => state.weights[p.id] > 0 && r.sims[p.id] != null);
    const byBest = [...active].sort((a, b) => r.sims[b.id] - r.sims[a.id] || state.weights[b.id] - state.weights[a.id]);
    const strong = byBest.slice(0, 4);
    const weak = [...active].sort((a, b) => r.sims[a.id] - r.sims[b.id] || state.weights[b.id] - state.weights[a.id]).filter((p) => r.sims[p.id] < 0.6).slice(0, 4);
    const kv = (list, cls) => h("div", { class: `kv ${cls}` }, ...list.map((p) =>
      h("div", { class: "kv-row" }, h("span", { class: "k" }, p.name), h("span", { class: "s num" }, `${pct(r.sims[p.id])}%`), h("span", { class: "d" }, detail(p, s, t)))));

    const st = STATUS[s.status];
    const head = h("div", { class: "ds-head" },
      h("h2", {}, s.name),
      h("span", { class: "ds-meta" }, `${s.place}. ${fmtLat(s.lat)}, ${fmtLon(s.lon)}. ${s.elev < 0 ? `${Math.abs(s.elev)} m below sea level` : `${s.elev.toLocaleString()} m elevation`}`),
      h("span", { class: "status" }, shapeSVG(s.status, scoreScale(r.score)), st.label)
    );
    const score = h("div", { class: "ds-score" },
      h("span", { class: "big" }, String(pct(r.score))),
      h("span", { class: "lab" }, h("b", {}, `Match with ${t.name}`), h("br"), `Rank ${r.rank} of ${state.results.length}${r.coverage < 0.999 ? `. Data for ${pct(r.coverage)}% of weighted parameters` : ""}`)
    );
    const parts = [head, score, h("p", { class: "ds-blurb" }, s.blurb)];
    if (s.mode === "subsurface") parts.push(h("p", { class: "note" }, "Values describe the underground environment rather than the surface above it."));
    parts.push(h("section", { class: "kv-wrap" }, h("h3", {}, "Strongest matches"), kv(strong, "")));
    if (weak.length) parts.push(h("section", {}, h("h3", {}, "Where the analogy breaks down"), kv(weak, "weak")));
    parts.push(h("section", {}, h("h3", {}, "Use it to test"), h("p", { class: "ds-blurb" }, s.use)));
    parts.push(profile(r, t));
    parts.push(spectra(s, t));
    parts.push(siteGaps(s));
    box.replaceChildren(...parts);
  }

  function profile(r, t) {
    const wrap = h("section", { class: "prof" }, h("h3", {}, "Parameter profile"),
      h("div", { class: "key" }, h("span", {}, h("i", { class: "t" }), `${t.name}`), h("span", {}, h("i", { class: "s" }), "this site, coloured by similarity")));
    for (const g of M.GROUPS) {
      wrap.append(h("h3", {}, g.name));
      for (const p of M.PARAMS.filter((q) => q.g === g.id)) {
        const sim = r.sims[p.id];
        const col = sim == null ? "#55627d" : simScale(sim);
        let viz;
        if (p.kind === "num") {
          const a = r.site.x[p.id], b = t.x[p.id];
          if (a == null || b == null) viz = h("div", { class: "track" }, h("span", { class: "na" }, "no data"));
          else viz = h("div", { class: "track" },
            h("span", { class: "tl", style: `left:${Math.min(a, b) * 100}%;width:${Math.abs(a - b) * 100}%;background:${col}` }),
            h("span", { class: "tt", style: `left:${b * 100}%` }),
            h("span", { class: "ts", style: `left:${a * 100}%;background:${col}` }));
        } else viz = h("div", { class: "simbar" }, h("i", { style: `width:${pct(sim ?? 0)}%;background:${col}` }));
        wrap.append(h("div", { class: `prow${state.weights[p.id] === 0 ? " zero" : ""}`, title: `${p.name}: ${detail(p, r.site, t)}${sim != null ? ` (similarity ${pct(sim)}%)` : ""}` },
          h("span", { class: "pn" }, p.name), viz));
      }
    }
    return wrap;
  }

  function spectra(s, t) {
    const W = 340, H = 168, L = 30, R = 10, T = 10, B = 26;
    const a = M.spectrum(s.min, "earth"), b = M.spectrum(t.min, t.body);
    const ymax = Math.max(0.6, ...a, ...b) * 1.05;
    const x = (l) => L + ((l - 0.4) / 2.1) * (W - L - R);
    const y = (v) => H - B - (v / ymax) * (H - T - B);
    const line = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${x(M.WL[i]).toFixed(1)},${y(v).toFixed(1)}`).join("");
    const area = (arr) => `${line(arr)}L${x(2.5)},${y(0)}L${x(0.4)},${y(0)}Z`;
    const tcol = getComputedStyle(document.body).getPropertyValue("--accent").trim();
    const scol = RAMP[2];
    const guides = [[1.0, "Fe²⁺ 1 µm"], [1.9, "H₂O 1.9"], [2.3, "M–OH / CO₃"]];
    const yt = [0, 0.2, 0.4, 0.6, 0.8].filter((v) => v <= ymax);
    const svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Modelled reflectance spectra of the site and the target">
      ${yt.map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#24395f" stroke-width="1"/><text x="${L - 5}" y="${y(v) + 3.5}" text-anchor="end">${v.toFixed(1)}</text>`).join("")}
      ${guides.map(([l, n]) => `<line x1="${x(l)}" x2="${x(l)}" y1="${T}" y2="${H - B}" stroke="#3a5283" stroke-dasharray="2 3"/><text x="${x(l) + 3}" y="${T + 9}">${n}</text>`).join("")}
      <path d="${area(a)}" fill="${scol}" opacity="0.12"/>
      <path d="${line(b)}" fill="none" stroke="${tcol}" stroke-width="2" stroke-dasharray="5 3"/>
      <path d="${line(a)}" fill="none" stroke="${scol}" stroke-width="2"/>
      ${[0.5, 1.0, 1.5, 2.0, 2.5].map((l) => `<text x="${x(l)}" y="${H - 8}" text-anchor="middle">${l.toFixed(1)}</text>`).join("")}
      <text x="${W - R}" y="${H - 8 - 11}" text-anchor="end">µm</text>
    </svg>`;
    const sec = h("section", { class: "spec" }, h("h3", {}, `Spectra, ${pct(state.results.find((r) => r.site.id === s.id).sims.spectral)}% match`));
    const fig = h("div", { html: svg });
    sec.append(fig,
      h("div", { class: "key" }, h("span", {}, h("i", { class: "s", style: `background:${scol};border-radius:2px;height:3px;width:14px` }), s.name), h("span", {}, h("i", { class: "t", style: "width:14px;height:0;border-top:2px dashed var(--accent)" }), t.name)),
      h("p", { class: "note" }, `Modelled from mineral mixtures${t.body === "moon" ? " with space weathering" : " with Martian dust"}. Swap in EMIT reflectance and ${t.body === "moon" ? "M³" : "CRISM"} spectra from your pipeline.`));
    return sec;
  }

  function siteGaps(s) {
    const p = 1013.25 * Math.exp(-s.elev / 8400);
    const g = M.GAPS[state.body];
    const ratio = state.body === "mars" ? `about ${Math.round(p / 6)}× Mars` : "a vacuum it can't approach";
    return h("section", {}, h("h3", {}, "What this site can't reproduce"),
      h("div", { class: "ds-gaps" },
        h("div", {}, h("span", {}, "Air pressure"), h("span", {}, `≈ ${Math.round(p)} mbar here, ${ratio}`)),
        h("div", {}, h("span", {}, "Gravity"), h("span", {}, `9.81 m/s² vs ${g.gravity}`)),
        h("div", {}, h("span", {}, "Radiation dose"), h("span", {}, `${M.GAPS.earth.radiation.replace(" natural background", "")} vs ${g.radiation.split(" (")[0]}`))));
  }

  /* ---------- Globe ---------- */
  const canvas = $("#globe"), ctx = canvas.getContext("2d");
  const inset = $("#inset"), ictx = inset.getContext("2d");
  let W = 0, H = 0, dpr = 1, zoom = 1;
  let rot = [20, -12, 0];
  let fly = null, dragging = false, lastInteract = -1e9, dirty = true, marks = [];
  const proj = d3.geoOrthographic().clipAngle(90).precision(0.5);
  const path = d3.geoPath(proj, ctx);
  const sphere = { type: "Sphere" };
  const grat = d3.geoGraticule().step([15, 15])();
  const land = { type: "GeometryCollection", geometries: BASEMAP.land };
  const antarctic = [];
  for (const g of BASEMAP.land) {
    const polys = g.type === "MultiPolygon" ? g.coordinates : [g.coordinates];
    for (const poly of polys) { const ring = poly[0]; const mlat = ring.reduce((s, c) => s + c[1], 0) / ring.length; if (mlat < -60) antarctic.push(poly); }
  }
  const ice = { type: "GeometryCollection", geometries: [...BASEMAP.ice, { type: "MultiPolygon", coordinates: antarctic }] };
  const deserts = { type: "GeometryCollection", geometries: BASEMAP.deserts.map((d) => d.g) };
  const pattern = (size, drawFn) => { const c = document.createElement("canvas"); c.width = c.height = size; drawFn(c.getContext("2d"), size); return ctx.createPattern(c, "repeat"); };
  let hatch, stipple;
  function makePatterns() {
    hatch = pattern(Math.round(7 * dpr), (g, n) => { g.strokeStyle = "rgba(214,190,146,0.55)"; g.lineWidth = 1 * dpr; g.beginPath(); g.moveTo(0, n); g.lineTo(n, 0); g.moveTo(-1, 1); g.lineTo(1, -1); g.moveTo(n - 1, n + 1); g.lineTo(n + 1, n - 1); g.stroke(); });
    stipple = pattern(Math.round(5 * dpr), (g, n) => { g.fillStyle = "rgba(230,238,250,0.6)"; g.beginPath(); g.arc(n / 2, n / 2, 0.75 * dpr, 0, Math.PI * 2); g.fill(); });
  }
  function subsolar(d = new Date()) {
    const N = (d - Date.UTC(d.getUTCFullYear(), 0, 0)) / 864e5;
    const decl = -23.44 * Math.cos(((2 * Math.PI) / 365) * (N + 10));
    const hrs = d.getUTCHours() + d.getUTCMinutes() / 60;
    return [((-15 * (hrs - 12) + 540) % 360) - 180, decl];
  }
  let night;
  function updateNight() { const [lon, lat] = subsolar(); night = d3.geoCircle().center([lon + 180, -lat]).radius(90)(); dirty = true; }
  updateNight(); setInterval(updateNight, 60000);

  function resize() {
    const b = canvas.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    W = b.width; H = b.height;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    makePatterns(); dirty = true;
  }
  new ResizeObserver(resize).observe(canvas);

  const radius = () => (Math.min(W, H) / 2) * 0.84 * zoom;
  function draw(now) {
    if (!W) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const r = radius(), cx = W / 2, cy = H / 2;
    proj.scale(r).translate([cx, cy]).rotate(rot);
    const halo = ctx.createRadialGradient(cx, cy, r * 0.96, cx, cy, r * 1.14);
    halo.addColorStop(0, "rgba(120,170,255,0.22)"); halo.addColorStop(1, "rgba(120,170,255,0)");
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cx, cy, r * 1.14, 0, Math.PI * 2); ctx.fill();
    const ocean = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.1, cx, cy, r);
    ocean.addColorStop(0, "#1b3a6b"); ocean.addColorStop(1, "#0f2142");
    ctx.beginPath(); path(sphere); ctx.fillStyle = ocean; ctx.fill();
    ctx.beginPath(); path(grat); ctx.strokeStyle = "rgba(160,190,240,0.11)"; ctx.lineWidth = 0.7; ctx.stroke();
    ctx.beginPath(); path(land); ctx.fillStyle = "#2c4170"; ctx.fill();
    if (state.layers.deserts) { ctx.beginPath(); path(deserts); ctx.fillStyle = "rgba(210,187,143,0.12)"; ctx.fill(); ctx.fillStyle = hatch; ctx.fill(); }
    if (state.layers.ice) { ctx.beginPath(); path(ice); ctx.fillStyle = "rgba(225,234,248,0.18)"; ctx.fill(); ctx.fillStyle = stipple; ctx.fill(); }
    ctx.beginPath(); path(land); ctx.strokeStyle = "rgba(190,210,245,0.42)"; ctx.lineWidth = 0.7; ctx.stroke();
    if (state.layers.night) { ctx.beginPath(); path(night); ctx.fillStyle = "rgba(4,9,22,0.42)"; ctx.fill(); }
    ctx.beginPath(); path(sphere); ctx.strokeStyle = "rgba(170,200,255,0.4)"; ctx.lineWidth = 1; ctx.stroke();
    drawMarks(now, r);
  }

  function drawMarks(now, r) {
    const center = [-rot[0], -rot[1]];
    marks = [];
    const list = shown();
    for (const res of list) {
      const s = res.site;
      if (d3.geoDistance([s.lon, s.lat], center) > Math.PI / 2 - 0.03) continue;
      const [x, y] = proj([s.lon, s.lat]);
      const v = valOf(res);
      const size = 3.2 + 6 * Math.pow(Math.max(0, Math.min(1, state.focus ? v : (v - lo) / (hi - lo))), 1.3);
      marks.push({ x, y, size, res });
    }
    marks.sort((a, b) => valOf(a.res) - valOf(b.res));
    for (const m of marks) {
      const col = colorOf(m.res), st = m.res.site.status;
      ctx.save(); ctx.translate(m.x, m.y);
      ctx.lineWidth = 1.6; ctx.strokeStyle = "rgba(6,12,28,0.9)";
      if (st === "candidate") { ctx.rotate(Math.PI / 4); const k = m.size * 1.5; ctx.beginPath(); ctx.rect(-k / 2, -k / 2, k, k); ctx.fillStyle = col; ctx.fill(); ctx.stroke(); }
      else if (st === "studied") { ctx.beginPath(); ctx.arc(0, 0, m.size, 0, Math.PI * 2); ctx.lineWidth = 4.2; ctx.stroke(); ctx.lineWidth = 2.4; ctx.strokeStyle = col; ctx.stroke(); }
      else { ctx.beginPath(); ctx.arc(0, 0, m.size, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill(); ctx.stroke(); }
      ctx.restore();
      if (m.res.site.id === state.selected) {
        const pulse = reduceMotion ? 0 : (Math.sin(now / 380) + 1) * 2;
        ctx.beginPath(); ctx.arc(m.x, m.y, m.size + 6 + pulse, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(234,240,248,0.95)"; ctx.lineWidth = 1.5; ctx.stroke();
      }
    }
    // labels: top five shown, selected, hovered
    const ranked = list.slice(0, 5).map((x) => x.site.id);
    const want = marks.filter((m) => ranked.includes(m.res.site.id) || m.res.site.id === state.selected || m.res.site.id === state.hover)
      .sort((a, b) => (b.res.site.id === state.selected) - (a.res.site.id === state.selected) || a.res.rank - b.res.rank);
    const boxes = [];
    ctx.font = `600 12.5px ${getComputedStyle(document.body).getPropertyValue("--f-body")}`;
    ctx.textBaseline = "middle";
    for (const m of want) {
      const idx = list.indexOf(m.res) + 1;
      const label = `${idx}  ${m.res.site.name.split(",")[0]}`;
      const w = ctx.measureText(label).width;
      let lx = m.x + m.size + 8, ly = m.y;
      if (lx + w > W - 8) lx = m.x - m.size - 8 - w;
      const box = [lx - 3, ly - 9, w + 6, 18];
      if (boxes.some((b) => !(box[0] > b[0] + b[2] || box[0] + box[2] < b[0] || box[1] > b[1] + b[3] || box[1] + box[3] < b[1]))) continue;
      boxes.push(box);
      ctx.lineWidth = 4; ctx.strokeStyle = "rgba(8,15,33,0.88)"; ctx.lineJoin = "round"; ctx.strokeText(label, lx, ly);
      ctx.fillStyle = m.res.site.id === state.selected ? "#ffffff" : "#dfe7f4"; ctx.fillText(label, lx, ly);
    }
  }

  function tick(now) {
    const idle = now - lastInteract > 6000;
    let moving = false;
    if (fly) {
      const k = Math.min(1, (now - fly.t0) / fly.dur);
      const e = d3.easeCubicInOut(k);
      rot = [fly.from[0] + (fly.to[0] - fly.from[0]) * e, fly.from[1] + (fly.to[1] - fly.from[1]) * e, 0];
      moving = true;
      if (k >= 1) { fly = null; lastInteract = now; }
    } else if (state.spin && !dragging && idle) {
      rot[0] = ((rot[0] + 0.07 + 180) % 360) - 180;
      moving = true;
    }
    if (moving || dirty || (state.selected && !reduceMotion)) { draw(now); dirty = false; }
    requestAnimationFrame(tick);
  }

  function flyTo(lon, lat) {
    const from = [rot[0], rot[1]];
    let tl = -lon; while (tl - from[0] > 180) tl -= 360; while (tl - from[0] < -180) tl += 360;
    const to = [tl, Math.max(-75, Math.min(75, -lat))];
    if (reduceMotion) { rot = [to[0], to[1], 0]; dirty = true; lastInteract = performance.now(); return; }
    fly = { from, to, t0: performance.now(), dur: 1200 };
  }

  // Pointer interaction
  const pointers = new Map();
  let downAt = null, pinch0 = null;
  const hit = (x, y) => { let best = null, bd = 14; for (const m of marks) { const d = Math.hypot(m.x - x, m.y - y); if (d < Math.max(bd, m.size + 4) && (!best || d < best.d)) best = { m, d }; } return best && best.m; };
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch0 = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), z: zoom }; }
    downAt = [e.offsetX, e.offsetY]; dragging = true; fly = null; lastInteract = performance.now();
    canvas.classList.add("dragging");
  });
  canvas.addEventListener("pointermove", (e) => {
    const prev = pointers.get(e.pointerId);
    if (prev) {
      pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
      if (pointers.size === 2 && pinch0) {
        const [a, b] = [...pointers.values()];
        zoom = Math.max(0.8, Math.min(6, pinch0.z * Math.hypot(a[0] - b[0], a[1] - b[1]) / pinch0.d));
      } else {
        const k = 57 / radius();
        rot[0] += (e.offsetX - prev[0]) * k;
        rot[1] = Math.max(-90, Math.min(90, rot[1] - (e.offsetY - prev[1]) * k));
      }
      lastInteract = performance.now(); dirty = true; hideTip();
      return;
    }
    const m = hit(e.offsetX, e.offsetY);
    const id = m ? m.res.site.id : null;
    canvas.classList.toggle("pointing", !!m);
    if (id !== state.hover) { state.hover = id; dirty = true; }
    if (m) showTip(m, e.offsetX, e.offsetY); else hideTip();
  });
  const up = (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch0 = null;
    if (pointers.size === 0) {
      dragging = false; canvas.classList.remove("dragging");
      if (downAt && Math.hypot(e.offsetX - downAt[0], e.offsetY - downAt[1]) < 5) { const m = hit(e.offsetX, e.offsetY); if (m) select(m.res.site.id, true); }
      downAt = null; lastInteract = performance.now();
    }
  };
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("pointerleave", () => { if (state.hover) { state.hover = null; dirty = true; } hideTip(); });
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); zoom = Math.max(0.8, Math.min(6, zoom * Math.exp(-e.deltaY * 0.0012))); lastInteract = performance.now(); dirty = true; }, { passive: false });

  const tip = $("#tip");
  function showTip(m, x, y) {
    const r = m.res;
    tip.replaceChildren(h("b", {}, r.site.name), ` ${pct(valOf(r))}${state.focus ? `% on ${PBY[state.focus].name.toLowerCase()}` : "% match"}`);
    tip.style.left = `${x}px`; tip.style.top = `${y}px`; tip.hidden = false;
  }
  function hideTip() { tip.hidden = true; }

  // Target inset (Moon / Mars locator)
  const craters = (() => { let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647); return Array.from({ length: 70 }, () => d3.geoCircle().center([rnd() * 360 - 180, Math.asin(rnd() * 2 - 1) * 180 / Math.PI]).radius(1.5 + rnd() * rnd() * 14)()); })();
  function drawInset() {
    const t = target();
    const css = inset.getBoundingClientRect().width || 132;
    const d = Math.min(2, window.devicePixelRatio || 1);
    inset.width = inset.height = Math.round(css * d);
    ictx.setTransform(d, 0, 0, d, 0, 0); ictx.clearRect(0, 0, css, css);
    const p = d3.geoOrthographic().scale(css / 2 - 3).translate([css / 2, css / 2]).rotate([-t.lon, -t.lat * 0.92]).clipAngle(90);
    const pp = d3.geoPath(p, ictx);
    const moon = t.body === "moon";
    const g = ictx.createRadialGradient(css * 0.36, css * 0.32, 2, css / 2, css / 2, css / 2);
    if (moon) { g.addColorStop(0, "#b7bfcb"); g.addColorStop(1, "#3c4352"); } else { g.addColorStop(0, "#d9894f"); g.addColorStop(1, "#5b2a17"); }
    ictx.beginPath(); pp({ type: "Sphere" }); ictx.fillStyle = g; ictx.fill();
    if (moon) { ictx.beginPath(); craters.forEach((c) => pp(c)); ictx.strokeStyle = "rgba(20,24,34,0.28)"; ictx.lineWidth = 0.8; ictx.stroke(); }
    else { ictx.beginPath(); pp(d3.geoCircle().center([0, 90]).radius(8)()); pp(d3.geoCircle().center([0, -90]).radius(5)()); ictx.fillStyle = "rgba(245,240,232,0.8)"; ictx.fill(); }
    ictx.beginPath(); pp(d3.geoGraticule().step([30, 30])()); ictx.strokeStyle = "rgba(255,255,255,0.13)"; ictx.lineWidth = 0.6; ictx.stroke();
    const center = [t.lon, t.lat * 0.92];
    for (const o of state.targets.filter((x) => x.body === t.body)) {
      if (d3.geoDistance([o.lon, o.lat], center) > Math.PI / 2 - 0.02) continue;
      const [x, y] = p([o.lon, o.lat]); const sel = o.id === t.id;
      ictx.beginPath(); ictx.arc(x, y, sel ? 3.6 : 2.4, 0, Math.PI * 2); ictx.fillStyle = sel ? "#ffffff" : "rgba(255,255,255,0.6)"; ictx.fill();
      if (sel) { ictx.beginPath(); ictx.arc(x, y, 8, 0, Math.PI * 2); ictx.strokeStyle = moon ? "#c9d6ec" : "#ffd59a"; ictx.lineWidth = 1.5; ictx.stroke(); }
    }
    $("#inset-cap").textContent = `${t.name}, ${fmtLat(t.lat)} ${fmtLon(t.lon)}`;
  }

  /* ---------- Stage overlays ---------- */
  function renderOverlay() {
    const t = target();
    const tl = $("#ov-tl");
    const card = h("div", { class: "target-card" },
      h("span", { class: "tc-label" }, `Earth sites ranked against ${t.body === "moon" ? "the Moon" : "Mars"}`),
      h("span", { class: "tc-name" }, t.name),
      h("span", { class: "tc-label" }, t.note));
    const kids = [card];
    if (state.focus) kids.push(h("span", { class: "focus-pill" }, `Coloured by ${PBY[state.focus].name.toLowerCase()}`, h("button", { "aria-label": "Show overall match", onclick: () => setFocus(null) }, "Overall")));
    tl.replaceChildren(...kids);
    const lg = $("#legend");
    const a = state.focus ? 0 : pct(lo), b = state.focus ? 100 : pct(hi);
    lg.replaceChildren(
      h("span", {}, state.focus ? `Similarity on ${PBY[state.focus].name.toLowerCase()}, %` : "Match score, stretched to this target's range"),
      h("div", { class: "ramp", style: `background:linear-gradient(90deg,${RAMP.join(",")})` }),
      h("div", { class: "ticks num" }, h("span", {}, String(a)), h("span", {}, String(Math.round((a + b) / 2))), h("span", {}, String(b))),
      h("div", { class: "shapes" }, h("span", {}, shapeSVG("established", "#c8d3e6"), "Long-running"), h("span", {}, shapeSVG("studied", "#c8d3e6"), "Studied"), h("span", {}, shapeSVG("candidate", "#c8d3e6"), "Under-studied")),
      h("div", { class: "layers" }, h("span", {}, h("i", { style: "background:repeating-linear-gradient(135deg,rgba(214,190,146,.7) 0 1px,transparent 1px 4px)" }), "Deserts"), h("span", {}, h("i", { style: "background:radial-gradient(rgba(230,238,250,.8) 0.8px,transparent 1px) 0 0/4px 4px" }), "Ice"), h("span", {}, h("i", { style: "background:rgba(4,9,22,.75);border:1px solid #24395f" }), "Night now"))
    );
  }
  function renderToggles() {
    const mk = (label, on, fn) => h("button", { class: "tog", "aria-pressed": String(on), onclick: fn }, label);
    $("#ov-tr").replaceChildren(
      mk("Spin", state.spin, () => { state.spin = !state.spin; lastInteract = -1e9; renderToggles(); }),
      mk("Under-studied only", state.onlyCandidates, () => { state.onlyCandidates = !state.onlyCandidates; rescale(); renderToggles(); renderRanking(); renderOverlay(); dirty = true; }),
      mk("Deserts", state.layers.deserts, () => { state.layers.deserts = !state.layers.deserts; renderToggles(); dirty = true; }),
      mk("Ice", state.layers.ice, () => { state.layers.ice = !state.layers.ice; renderToggles(); dirty = true; }),
      mk("Night side", state.layers.night, () => { state.layers.night = !state.layers.night; renderToggles(); dirty = true; })
    );
  }

  /* ---------- Actions ---------- */
  let pending = false;
  function scheduleUpdate() { if (pending) return; pending = true; requestAnimationFrame(() => { pending = false; compute(); renderRanking(); renderDossier(); renderOverlay(); dirty = true; }); }
  function select(id, doFly) {
    state.selected = id;
    const s = state.sites.find((x) => x.id === id);
    renderRanking(); renderDossier(); dirty = true;
    if (doFly && s) flyTo(s.lon, s.lat);
  }
  function setTarget(id) {
    state.targetId = id;
    compute(); renderTargets(); renderOverlay(); drawInset();
    const best = shown()[0];
    if (best) select(best.site.id, true);
  }
  function setBody(body) {
    if (body === state.body) return;
    state.body = body;
    renderBodyToggle(); renderGaps();
    setTarget(state.targets.find((t) => t.body === body).id);
  }
  function applyPreset(id) {
    state.preset = id; state.weights = M.presetWeights(id);
    renderPresets(); renderWeights(); scheduleUpdate();
  }
  function setFocus(id) {
    state.focus = id;
    renderWeights(); renderOverlay(); renderRanking(); dirty = true;
  }

  /* ---------- Method dialog & data loading ---------- */
  const TEMPLATE = {
    sites: [{
      id: "my-site", name: "My candidate site", place: "Region, Country", lat: 0, lon: 0, elev: 0, status: "candidate",
      blurb: "One-sentence description.", use: "What you would test here.",
      x: Object.fromEntries(M.NUM.map((id) => [id, null])),
      min: M.MINERALS.map(() => 0), lf: "crater plain", sc: "basaltic regolith",
    }],
  };
  function buildMethod() {
    const rows = M.PARAMS.map((p) => `<tr><td>${p.name}</td><td>${p.scale}</td><td>${p.src.earth}</td><td>${p.src.moon}</td><td>${p.src.mars}</td></tr>`).join("");
    const links = [
      ["NASA Earthdata Search", "https://search.earthdata.nasa.gov/"], ["NASA Worldview", "https://worldview.earthdata.nasa.gov/"],
      ["NASA Planetary Data System", "https://pds.nasa.gov/"], ["LRO data at PDS Geosciences", "https://pds-geosciences.wustl.edu/missions/lro/"],
      ["LRO Diviner data", "https://pds-geosciences.wustl.edu/missions/lro/diviner.htm"], ["CSA RADARSAT Constellation Mission", "https://donnees-data.asc-csa.gc.ca/en/dataset/rcm"],
      ["CSA RADARSAT-1 archive", "https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1"], ["CSA SAR tutorial (Python + QGIS)", "https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial"],
      ["Copernicus Data Space Ecosystem", "https://dataspace.copernicus.eu/"], ["ESA Open Science Catalog", "https://opensciencedata.esa.int/"], ["JAXA G-Portal", "https://gportal.jaxa.jp/gpr/index/index"],
    ].map(([n, u]) => `<li><a href="${u}" target="_blank" rel="noopener">${n}</a></li>`).join("");
    $("#method-body").innerHTML = `
      <section><h2>How a site is scored</h2>
        <p>Every parameter is placed on a 0–1 scale with a physical meaning that works on all three worlds, so a site and a target can be compared directly. Each parameter gives a similarity between 0 and 1:</p>
        <div class="formula">numeric: s = exp(−((x<sub>site</sub> − x<sub>target</sub>) ÷ 0.3)²)<br>landforms, materials: share of the target's classes present at the site<br>mineralogy: 1 − Bray–Curtis dissimilarity<br>spectra: s = 1 − θ ÷ 0.35 rad (spectral angle)<br>match = Σ wᵢsᵢ ÷ Σ wᵢ over parameters with data</div>
        <p>Parameters with no data drop out of a site's score, and the dossier reports how much of the weight was covered. Gravity, vacuum and radiation are kept out of the score because no Earth surface site can approach them.</p></section>
      <section><h2>About the seed data</h2>
        <p>The 27 Earth sites and 11 targets ship with indicative values estimated from published studies and the global datasets listed below. They are meant to exercise the interface, not to be cited. Replace them with values computed from rasters in your pipeline, then load the result as JSON.</p></section>
      <section><h2>Parameters and data sources</h2><div class="tbl-wrap"><table><thead><tr><th>Parameter</th><th>0–1 scale</th><th>Earth</th><th>Moon</th><th>Mars</th></tr></thead><tbody>${rows}</tbody></table></div></section>
      <section><h2>Load your own sites</h2>
        <p>Use <b>Load site data</b> with a JSON file of the form below. <code>x</code> takes values keyed by parameter id (or use <code>v</code>, an array in the same order). <code>min</code> holds abundances in this order: ${M.MINERALS.join(", ")}. Add <code>targets</code> in the same shape with a <code>body</code> of "moon" or "mars" to replace the targets.</p>
        <pre id="tpl"></pre><div><button class="btn" id="copy-tpl">Copy JSON template</button></div></section>
      <section><h2>Data portals</h2><ul>${links}</ul><p>Base map: Natural Earth (public domain) via world-atlas.</p></section>`;
    $("#tpl").textContent = JSON.stringify(TEMPLATE, null, 2);
    $("#copy-tpl").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(JSON.stringify(TEMPLATE, null, 2)); toast("Template copied"); }
      catch { const r = document.createRange(); r.selectNodeContents($("#tpl")); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); toast("Copy blocked here. The template is selected; press Ctrl+C or ⌘C."); }
    });
  }
  function toast(msg) { const t = h("div", { class: "toast", role: "status" }, msg); document.body.append(t); setTimeout(() => t.remove(), 3600); }
  function normalize(e, i, isTarget) {
    if (typeof e.lat !== "number" || typeof e.lon !== "number" || !e.name) throw new Error(`Entry ${i + 1} needs name, lat and lon`);
    const v = Array.isArray(e.v) ? e.v : M.NUM.map((id) => (e.x && typeof e.x[id] === "number" ? e.x[id] : null));
    return M.expand({
      id: e.id || `${isTarget ? "t" : "s"}-${i}`, name: e.name, place: e.place || "", lat: e.lat, lon: e.lon, elev: +e.elev || 0,
      status: STATUS[e.status] ? e.status : "candidate", mode: e.mode, blurb: e.blurb || "", use: e.use || "No test plan given.",
      kind: e.kind || "Target", note: e.note || "", body: e.body === "mars" ? "mars" : "moon",
      v: M.NUM.map((_, k) => (typeof v[k] === "number" ? Math.max(0, Math.min(1, v[k])) : null)),
      min: Array.isArray(e.min) && e.min.length === M.MINERALS.length ? e.min.map((x) => +x || 0) : M.MINERALS.map(() => 0),
      lf: e.lf || null, sc: e.sc || null,
    });
  }
  $("#file-in").addEventListener("change", async (ev) => {
    const f = ev.target.files[0]; ev.target.value = "";
    if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      const sites = (Array.isArray(data) ? data : data.sites || []).map((e, i) => normalize(e, i, false));
      if (!sites.length) throw new Error("No sites found. Put them in a \"sites\" array.");
      state.sites = sites;
      if (Array.isArray(data.targets) && data.targets.length) { state.targets = data.targets.map((e, i) => normalize(e, i, true)); state.body = state.targets[0].body; state.targetId = state.targets[0].id; renderBodyToggle(); renderGaps(); }
      setTarget(state.targetId);
      toast(`Loaded ${sites.length} sites from ${f.name}`);
    } catch (err) { toast(`Couldn't load ${f.name}: ${err.message}`); }
  });

  /* ---------- Boot ---------- */
  document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => setBody(b.dataset.body)));
  $("#reset-w").addEventListener("click", () => applyPreset("balanced"));
  $("#btn-method").addEventListener("click", () => { if (!$("#method-body").childElementCount) buildMethod(); $("#method").showModal(); });
  $("#method-close").addEventListener("click", () => $("#method").close());
  renderBodyToggle(); renderPresets(); renderWeights(); renderGaps(); renderToggles();
  compute(); renderTargets(); renderOverlay(); drawInset();
  const first = shown()[0];
  state.selected = first.site.id;
  renderRanking(); renderDossier();
  rot = [-first.site.lon + 35, Math.max(-60, Math.min(60, -first.site.lat)), 0];
  requestAnimationFrame(tick);
  new ResizeObserver(() => drawInset()).observe(inset);
})();
