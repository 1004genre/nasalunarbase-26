/* Analog Atlas — parameter model, targets, seed sites and scoring.
   Every value is on a 0–1 scale whose physical meaning is defined per parameter,
   so Earth, Moon and Mars can be placed on the same axis.
   SEED VALUES ARE INDICATIVE ESTIMATES from published literature and global datasets;
   replace them with your pipeline output (see "Load your data"). */
const MODEL = (() => {
  const r0 = (x) => Math.round(x);
  const r1 = (x) => Math.round(x * 10) / 10;
  const sig = (x, n = 2) => { if (x === 0) return "0"; const p = Math.pow(10, n - 1 - Math.floor(Math.log10(Math.abs(x)))); return String(Math.round(x * p) / p); };

  const GROUPS = [
    { id: "sky", name: "Sky & light" },
    { id: "climate", name: "Atmosphere & climate" },
    { id: "terrain", name: "Terrain" },
    { id: "comp", name: "Composition" },
    { id: "sub", name: "Subsurface & volatiles" },
    { id: "ops", name: "Hazards & operations" },
  ];

  // kind: num (absolute 0–1 scale), tags (landform/material classes), vec (mineral abundances), spec (modelled spectra)
  const PARAMS = [
    { id: "light", g: "sky", name: "Light conditions", kind: "num",
      scale: "0 = ordinary day/night cycle, 1 = grazing sun, long shadows or permanent darkness",
      raw: (v) => v >= 0.97 ? "permanent dark or grazing sun" : v >= 0.75 ? "low sun / long shadows" : v >= 0.4 ? "strong seasonal swing" : "normal day–night",
      src: { earth: "NASA POWER solar geometry; CERES SYN1deg", moon: "LRO LOLA illumination maps", mars: "MOLA topography + Mars Climate Database" } },
    { id: "uv", g: "sky", name: "UV exposure", kind: "num",
      scale: "peak UV index ÷ 40; 1 = unshielded solar UV",
      raw: (v) => v >= 0.99 ? "unshielded (no atmosphere)" : `peak UVI ≈ ${r0(v * 40)}`,
      src: { earth: "Aura OMI OMUVBd erythemal UV; Sentinel-5P TROPOMI", moon: "modelled (no atmosphere)", mars: "Curiosity REMS UV sensor; MCD (no ozone shield)" } },
    { id: "solar", g: "sky", name: "Surface sunlight", kind: "num",
      scale: "time-averaged power on a sun-tracking panel ÷ 1361 W/m²",
      raw: (v) => `≈ ${r0(v * 1361)} W/m² (tracking, averaged)`,
      src: { earth: "CERES SYN1deg; NASA POWER ALLSKY_SFC_SW_DWN / DNI", moon: "LOLA illumination fraction × solar constant", mars: "MCS / THEMIS dust opacity + MCD" } },
    { id: "clear", g: "sky", name: "Cloud-free days", kind: "num",
      scale: "fraction of days clear enough for optical sensors",
      raw: (v) => `≈ ${r0(v * 100)}% of days clear`,
      src: { earth: "MODIS MOD35/MYD35 cloud mask; MOD08_M3", moon: "always clear", mars: "MRO MARCI; MCS water-ice opacity" } },

    { id: "dust", g: "climate", name: "Dust conditions", kind: "num",
      scale: "fine abrasive particles available to coat and abrade hardware (airborne or lofted)",
      raw: (v) => v >= 0.7 ? "severe" : v >= 0.45 ? "frequent" : v >= 0.2 ? "moderate" : "low",
      src: { earth: "MERRA-2 dust AOD (M2TMNXAER); MODIS MAIAC / Deep Blue AOD", moon: "LADEE LDEX; Apollo dust detectors", mars: "TES / THEMIS / MCS dust opacity" } },
    { id: "wind", g: "climate", name: "Wind & sand movement", kind: "num",
      scale: "saltation activity and sand-flux potential; 0 = no wind",
      raw: (v) => v <= 0.02 ? "no wind" : v >= 0.75 ? "very active saltation" : v >= 0.45 ? "active" : "occasional",
      src: { earth: "MERRA-2 / ERA5 10 m winds; Sentinel-2 dune tracking", moon: "none (no atmosphere)", mars: "HiRISE dune migration; MCD winds" } },
    { id: "persist", g: "climate", name: "Weather persistence", kind: "num",
      scale: "how long conditions stay within a stable, repeatable range; 1 = no weather",
      raw: (v) => v >= 0.97 ? "no weather" : v >= 0.75 ? "very stable" : v >= 0.5 ? "mostly stable" : "changeable",
      src: { earth: "MERRA-2 daily variance; GPM IMERG", moon: "n/a (no weather)", mars: "MCS / MCD interannual repeatability" } },
    { id: "aridity", g: "climate", name: "Aridity", kind: "num",
      scale: "1 = hyperarid (aridity index < 0.05) or no liquid water",
      raw: (v) => v >= 0.995 ? "no liquid water" : v >= 0.9 ? "hyperarid (AI < 0.05)" : v >= 0.75 ? "arid (AI 0.05–0.2)" : v >= 0.55 ? "semi-arid" : v >= 0.4 ? "dry sub-humid" : "humid",
      src: { earth: "Global Aridity Index v3; NASA POWER precipitation & PET; GLDAS", moon: "none", mars: "none today" } },
    { id: "rain", g: "climate", name: "Rainfall history", kind: "num",
      scale: "how strongly liquid water has shaped the surface (recent rainfall + geologic record)",
      raw: (v) => v <= 0.02 ? "never" : v >= 0.7 ? "strongly water-shaped" : v >= 0.4 ? "episodic floods / paleolakes" : "rare",
      src: { earth: "GPM IMERG; TRMM 3B43; HydroSHEDS drainage", moon: "none", mars: "valley-network maps (Hynek 2010); CTX mosaic" } },
    { id: "tswing", g: "climate", name: "Daily temperature swing", kind: "num",
      scale: "√(diurnal surface ΔT ÷ 300 K)",
      raw: (v) => `ΔT ≈ ${r0(300 * v * v)} K`,
      src: { earth: "MODIS MOD11A1/MYD11A1 day–night LST; ECOSTRESS", moon: "LRO Diviner", mars: "THEMIS / TES; Curiosity REMS ground temperature" } },

    { id: "slope", g: "terrain", name: "Slope", kind: "num",
      scale: "typical slope at ~30 m baseline ÷ 30°",
      raw: (v) => `≈ ${r1(v * 30)}°`,
      src: { earth: "Copernicus DEM GLO-30; NASADEM", moon: "LOLA DEM; LROC NAC DTMs", mars: "MOLA; HRSC / CTX DTMs" } },
    { id: "rough", g: "terrain", name: "Roughness (multi-scale)", kind: "num",
      scale: "combined cm-to-100 m roughness (radar, laser, DEM)",
      raw: (v) => v >= 0.75 ? "very rough" : v >= 0.5 ? "rough" : v >= 0.25 ? "moderate" : "smooth",
      src: { earth: "ICESat-2 ATL06/ATL08; Sentinel-1 / RCM / RADARSAT-1 backscatter", moon: "LOLA roughness; LRO Mini-RF CPR", mars: "MOLA pulse width; SHARAD" } },
    { id: "rocks", g: "terrain", name: "Rock abundance", kind: "num",
      scale: "rock cover fraction ÷ 30%",
      raw: (v) => `≈ ${r0(v * 30)}% rock cover`,
      src: { earth: "high-res imagery + ASTER emissivity", moon: "Diviner rock abundance", mars: "THEMIS / TES rock abundance; HiRISE boulder counts" } },
    { id: "albedo", g: "terrain", name: "Albedo", kind: "num",
      scale: "bolometric albedo ÷ 0.6",
      raw: (v) => `albedo ≈ ${sig(v * 0.6)}`,
      src: { earth: "MODIS MCD43A3", moon: "LROC WAC normalized reflectance; Diviner albedo", mars: "TES albedo" } },
    { id: "landforms", g: "terrain", name: "Landforms", kind: "tags", tagKey: "lf",
      scale: "share of the target's landform types present at the site",
      src: { earth: "Geomorpho90m; Sentinel-2; Landsat", moon: "LROC WAC/NAC; Robbins crater database", mars: "CTX / HiRISE; Robbins crater database" } },
    { id: "caves", g: "terrain", name: "Pits, caves & lava-tube skylights", kind: "num",
      scale: "0 = none, 0.5 = caves nearby, 1 = confirmed tubes or skylights at site",
      raw: (v) => v >= 0.9 ? "confirmed at site" : v >= 0.5 ? "present" : v >= 0.15 ? "minor" : "none",
      src: { earth: "national cave registers; high-res skylight search", moon: "LROC pit catalogue (Wagner & Robinson)", mars: "Mars Global Cave Candidate Catalog (MGC³)" } },
    { id: "activity", g: "terrain", name: "Surface activity rate", kind: "num",
      scale: "rate of visible change (dune migration, slope streaks, new craters)",
      raw: (v) => v >= 0.75 ? "changes yearly or faster" : v >= 0.4 ? "decadal change" : v >= 0.15 ? "slow" : "nearly static",
      src: { earth: "Sentinel-2 / Landsat change detection; Sentinel-1 / RCM coherence", moon: "LROC NAC temporal pairs", mars: "HiRISE repeat imaging" } },

    { id: "surface", g: "comp", name: "Surface characteristics", kind: "tags", tagKey: "sc",
      scale: "share of the target's material classes (volcanic, basaltic, ice-rich…) present",
      src: { earth: "USGS / OneGeology maps; ASTER GED", moon: "Unified Geologic Map of the Moon (USGS)", mars: "Global Geologic Map of Mars (USGS)" } },
    { id: "mineralogy", g: "comp", name: "Mineralogy", kind: "vec",
      scale: "1 − Bray–Curtis dissimilarity of mineral abundances",
      src: { earth: "EMIT L2B mineral identification; ASTER", moon: "Chandrayaan-1 M³", mars: "MRO CRISM; Mars Express OMEGA" } },
    { id: "spectral", g: "comp", name: "Spectral match", kind: "spec",
      scale: "spectral-angle similarity, 0.4–2.5 µm",
      src: { earth: "EMIT L2A reflectance; AVIRIS-NG", moon: "M³ reflectance", mars: "CRISM MTRDR" } },
    { id: "silica", g: "comp", name: "Silicate composition", kind: "num",
      scale: "(SiO₂ wt% − 35) ÷ 40",
      raw: (v) => `SiO₂ ≈ ${r0(35 + 40 * v)} wt%`,
      src: { earth: "ASTER TIR silica index; ASTER GED emissivity", moon: "Diviner Christiansen feature", mars: "TES; THEMIS" } },
    { id: "ti", g: "comp", name: "Thermal inertia", kind: "num",
      scale: "log scale, 20 → 2500 J m⁻² K⁻¹ s⁻½",
      raw: (v) => `TI ≈ ${sig(20 * Math.pow(125, v))} SI`,
      src: { earth: "apparent TI from MODIS / ASTER diurnal LST + albedo", moon: "Diviner H-parameter", mars: "THEMIS / TES thermal inertia" } },
    { id: "isru", g: "comp", name: "Resource-use materials", kind: "num",
      scale: "quality of construction / ISRU test feedstock (basalt, ilmenite, regolith-like fines, ice)",
      raw: (v) => v >= 0.8 ? "excellent feedstock" : v >= 0.6 ? "good" : v >= 0.4 ? "partial" : "poor",
      src: { earth: "USGS mineral resources; EMIT", moon: "LROC WAC TiO₂ (ilmenite); Lunar Prospector GRS", mars: "CRISM hydrated minerals; SWIM ice" } },

    { id: "subsurface", g: "sub", name: "Subsurface conditions", kind: "num",
      scale: "0 = no ground ice, 1 = continuous ice-cemented ground / permafrost",
      raw: (v) => v >= 0.85 ? "continuous ice-cemented" : v >= 0.5 ? "discontinuous" : v >= 0.1 ? "sporadic" : "none",
      src: { earth: "ESA CCI Permafrost; SMAP freeze/thaw", moon: "Diviner ice-stability depth (Paige 2010); Mini-RF", mars: "SHARAD; SWIM ice consistency" } },
    { id: "icedepth", g: "sub", name: "Depth to stable ice", kind: "num",
      scale: "log scale: 1 = ice at 1 cm, 0 = none within 1 km",
      raw: (v) => { if (v <= 0.02) return "none within ~1 km"; const d = 0.01 * Math.pow(10, 5 * (1 - v)); return d < 1 ? `≈ ${r0(d * 100)} cm` : `≈ ${sig(d)} m`; },
      src: { earth: "ESA CCI active-layer thickness; ICESat-2", moon: "Diviner ice-stability maps", mars: "SWIM; ice-exposing craters (Dundas)" } },
    { id: "hydrogen", g: "sub", name: "Near-surface hydrogen / water", kind: "num",
      scale: "log water-equivalent hydrogen: 0.01 wt% → 100 wt%",
      raw: (v) => `≈ ${sig(0.01 * Math.pow(10, 4 * v))} wt% WEH`,
      src: { earth: "SMAP L4 + EMIT hydrated minerals (proxy)", moon: "LRO LEND; Lunar Prospector NS", mars: "Mars Odyssey GRS/NS; TGO FREND" } },
    { id: "soilm", g: "sub", name: "Soil moisture (dryness)", kind: "num",
      scale: "1 − volumetric soil moisture ÷ 0.4; 1 = bone dry",
      raw: (v) => `θ ≈ ${sig(Math.max(0.001, 0.4 * (1 - v)))} m³/m³`,
      src: { earth: "SMAP L3/L4; ESA CCI Soil Moisture", moon: "none", mars: "adsorbed films only (REMS humidity)" } },

    { id: "seismic", g: "ops", name: "Seismic activity", kind: "num",
      scale: "0 = stable craton, 1 = plate-boundary activity",
      raw: (v) => v >= 0.7 ? "very active" : v >= 0.4 ? "active" : v >= 0.2 ? "moderate" : "quiet",
      src: { earth: "USGS ComCat; GEM seismic hazard", moon: "Apollo Passive Seismic Experiment", mars: "InSight SEIS" } },
    { id: "volcanism", g: "ops", name: "Active volcanism", kind: "num",
      scale: "0 = extinct, 1 = erupting / persistent degassing",
      raw: (v) => v >= 0.75 ? "active now" : v >= 0.3 ? "Holocene / dormant" : v >= 0.1 ? "young but quiet" : "extinct",
      src: { earth: "Smithsonian GVP; MODIS MODVOLC; TROPOMI SO₂", moon: "none", mars: "crater-count ages (Cerberus Fossae)" } },
    { id: "human", g: "ops", name: "Human footprint", kind: "num",
      scale: "0 = pristine, 1 = heavily modified",
      raw: (v) => v <= 0.01 ? "untouched" : v >= 0.6 ? "heavy" : v >= 0.3 ? "moderate" : "light",
      src: { earth: "VIIRS Black Marble VNP46A4; SEDAC Human Footprint; GHSL", moon: "landers only", mars: "rovers only" } },
    { id: "remote", g: "ops", name: "Remoteness / logistics", kind: "num", invertible: true,
      scale: "log travel time to a city of 50k+: 0 h → 200 h",
      raw: (v) => v >= 0.99 ? "off-world" : `≈ ${sig(Math.pow(201, v) - 1)} h to a city`,
      src: { earth: "Accessibility to Cities 2015 (Weiss et al.); OpenStreetMap", moon: "≈ 3 days transit", mars: "≈ 7 months transit" } },
    { id: "navdiff", g: "ops", name: "Visual navigation difficulty", kind: "num",
      scale: "0 = feature-rich, 1 = featureless, shadowed or dark",
      raw: (v) => v >= 0.8 ? "very hard" : v >= 0.55 ? "hard" : v >= 0.35 ? "moderate" : "easy",
      src: { earth: "Sentinel-2 texture entropy + sun geometry", moon: "LROC NAC shadow fraction; LOLA", mars: "HiRISE; CTX" } },
  ];
  const NUM = PARAMS.filter((p) => p.kind === "num").map((p) => p.id);
  const MINERALS = ["Plagioclase", "Pyroxene", "Olivine", "Glass", "Fe–Ti oxides", "Phyllosilicates", "Sulfates", "Carbonates", "Salts", "Ice", "Quartz"];
  const LANDFORMS = { crater: "impact crater", "lava-flow": "lava flows", "lava-tube": "lava tubes", volcano: "volcanic edifice", pit: "pits / skylights", dunes: "dunes", yardangs: "yardangs", patterned: "patterned ground", glacial: "glacial / ice", fluvial: "fluvial / deltaic", evaporite: "evaporite flats", layered: "layered deposits", massif: "massif / ridge", plain: "plains", "cold-trap": "cold traps", hydrothermal: "hydrothermal", subsurface: "subsurface void" };
  const MATERIALS = { volcanic: "volcanic", basaltic: "basaltic", anorthositic: "anorthositic", regolith: "regolith-like fines", ice: "ice-rich", evaporite: "evaporite", impact: "impact-processed", sedimentary: "sedimentary", altered: "water-altered" };

  // Gaps Earth cannot reproduce
  const GAPS = {
    moon: { gravity: "1.62 m/s² (0.17 g)", pressure: "≈ 3 × 10⁻¹² mbar (exosphere)", radiation: "≈ 1.37 mSv/day (Chang'e-4 LND)" },
    mars: { gravity: "3.71 m/s² (0.38 g)", pressure: "≈ 6 mbar mean", radiation: "≈ 0.67 mSv/day (Curiosity RAD)" },
    earth: { gravity: "9.81 m/s²", radiation: "≈ 0.007 mSv/day natural background" },
  };

  // Value order follows NUM:
  // light uv solar clear dust wind persist aridity rain tswing | slope rough rocks albedo caves activity | silica ti isru | subsurface icedepth hydrogen soilm | seismic volcanism human remote navdiff
  // Mineral order follows MINERALS.
  const T = (o) => o;
  const TARGETS = [
    T({ id: "m-gerlache", body: "moon", name: "de Gerlache Rim 2", kind: "Artemis III candidate region", lat: -88.7, lon: -69, note: "Sunlit crater rim beside permanently shadowed cold traps.",
      v: [0.95, 1, 0.85, 1, 0.6, 0, 1, 1, 0, 0.55, 0.25, 0.6, 0.05, 0.3, 0.05, 0.05, 0.25, 0.19, 0.85, 0.5, 0.63, 0.37, 1, 0.1, 0, 0, 1, 0.9],
      min: [0.7, 0.12, 0.03, 0.12, 0.01, 0, 0, 0, 0, 0.02, 0], lf: "crater massif plain", sc: "anorthositic regolith impact" }),
    T({ id: "m-mouton", body: "moon", name: "Mons Mouton", kind: "Artemis III candidate region", lat: -84.8, lon: 29.2, note: "Flat-topped massif near the south pole; IM-2 landed on its plateau in 2025.",
      v: [0.92, 1, 0.8, 1, 0.6, 0, 1, 1, 0, 0.58, 0.17, 0.5, 0.05, 0.3, 0.05, 0.05, 0.25, 0.19, 0.75, 0.4, 0.55, 0.35, 1, 0.1, 0, 0, 1, 0.85],
      min: [0.68, 0.13, 0.04, 0.13, 0.01, 0, 0, 0, 0, 0.01, 0], lf: "massif crater plain", sc: "anorthositic regolith impact" }),
    T({ id: "m-shackleton", body: "moon", name: "Shackleton floor", kind: "Permanently shadowed cold trap", lat: -89.67, lon: 129.78, note: "Never-lit crater floor near 40 K where water ice can persist.",
      v: [1, 0.05, 0, 1, 0.5, 0, 1, 1, 0, 0.15, 0.2, 0.45, 0.03, 0.33, 0, 0.02, 0.25, 0.19, 1, 0.9, 0.86, 0.6, 1, 0.1, 0, 0, 1, 1],
      min: [0.55, 0.12, 0.03, 0.12, 0, 0, 0, 0, 0, 0.18, 0], lf: "crater cold-trap plain", sc: "regolith ice impact anorthositic" }),
    T({ id: "m-marius", body: "moon", name: "Marius Hills skylight", kind: "Lava-tube skylight", lat: 14.09, lon: -56.77, note: "Pit opening into a probable lava tube in a volcanic dome field; shelter from radiation and thermal extremes.",
      v: [0.85, 0.3, 0.1, 1, 0.4, 0, 1, 1, 0, 0.2, 0.1, 0.5, 0.08, 0.2, 1, 0.05, 0.2, 0.22, 0.85, 0.05, 0, 0.08, 1, 0.12, 0, 0, 1, 0.75],
      min: [0.25, 0.45, 0.1, 0.15, 0.05, 0, 0, 0, 0, 0, 0], lf: "pit lava-tube lava-flow volcano plain subsurface", sc: "volcanic basaltic regolith" }),
    T({ id: "m-tranq", body: "moon", name: "Mare Tranquillitatis pit", kind: "Lava-tube skylight", lat: 8.335, lon: 33.222, note: "Radar shows a cave conduit beneath; shaded floor holds near 17 °C (Horvath et al. 2022).",
      v: [0.85, 0.3, 0.1, 1, 0.4, 0, 1, 1, 0, 0.2, 0.07, 0.45, 0.08, 0.18, 1, 0.05, 0.18, 0.25, 0.95, 0.05, 0, 0.08, 1, 0.12, 0, 0, 1, 0.75],
      min: [0.22, 0.42, 0.05, 0.21, 0.1, 0, 0, 0, 0, 0, 0], lf: "pit lava-tube lava-flow plain subsurface", sc: "volcanic basaltic regolith" }),

    T({ id: "r-jezero", body: "mars", name: "Jezero Crater delta", kind: "Perseverance site", lat: 18.44, lon: 77.45, note: "Ancient lake delta with olivine, carbonates and clays; the Mars Sample Return cache region.",
      v: [0.2, 0.9, 0.15, 0.9, 0.75, 0.35, 0.85, 1, 0.85, 0.52, 0.17, 0.5, 0.33, 0.28, 0.05, 0.25, 0.32, 0.59, 0.65, 0.05, 0.05, 0.65, 0.99, 0.15, 0.02, 0, 1, 0.45],
      min: [0.25, 0.25, 0.2, 0.08, 0.05, 0.07, 0.02, 0.08, 0, 0, 0], lf: "crater fluvial layered", sc: "sedimentary basaltic altered impact" }),
    T({ id: "r-gale", body: "mars", name: "Gale Crater, Mount Sharp", kind: "Curiosity site", lat: -4.59, lon: 137.44, note: "Kilometres of layered lake and wind deposits; clays below, sulfates above, active Bagnold dunes.",
      v: [0.15, 0.9, 0.15, 0.92, 0.75, 0.45, 0.85, 1, 0.75, 0.55, 0.25, 0.55, 0.25, 0.37, 0.05, 0.4, 0.35, 0.59, 0.7, 0.05, 0.03, 0.62, 0.99, 0.15, 0.02, 0, 1, 0.45],
      min: [0.3, 0.2, 0.05, 0.2, 0.05, 0.12, 0.08, 0, 0, 0, 0], lf: "crater layered dunes fluvial", sc: "sedimentary basaltic altered" }),
    T({ id: "r-meridiani", body: "mars", name: "Meridiani Planum", kind: "Opportunity site", lat: -1.95, lon: -5.53, note: "Flat sulfate-rich sandstones with hematite spherules from acidic groundwater.",
      v: [0.12, 0.9, 0.16, 0.92, 0.75, 0.4, 0.85, 1, 0.55, 0.55, 0.03, 0.2, 0.05, 0.22, 0.05, 0.3, 0.3, 0.48, 0.6, 0.1, 0.08, 0.67, 0.99, 0.15, 0.02, 0, 1, 0.65],
      min: [0.2, 0.2, 0.05, 0.1, 0.1, 0.03, 0.3, 0, 0.02, 0, 0], lf: "plain layered evaporite dunes crater", sc: "sedimentary evaporite basaltic altered" }),
    T({ id: "r-arcadia", body: "mars", name: "Arcadia Planitia (Erebus Montes)", kind: "Human landing candidate (shallow ice)", lat: 39.5, lon: -172, note: "Mid-latitude plains where SWIM maps ice within metres of the surface.",
      v: [0.35, 0.85, 0.12, 0.8, 0.7, 0.3, 0.75, 1, 0.25, 0.45, 0.05, 0.25, 0.08, 0.33, 0.1, 0.15, 0.33, 0.52, 0.95, 0.9, 0.6, 0.85, 0.98, 0.15, 0.05, 0, 1, 0.6],
      min: [0.3, 0.3, 0.08, 0.12, 0.05, 0, 0.03, 0, 0, 0.12, 0], lf: "plain patterned glacial crater", sc: "ice regolith basaltic" }),
    T({ id: "r-arsia", body: "mars", name: "Arsia Mons skylights", kind: "Cave candidate", lat: -5.6, lon: -118.5, note: "Pits on the flank of a Tharsis shield volcano; candidate shelters from radiation.",
      v: [0.8, 0.5, 0.1, 0.7, 0.85, 0.35, 0.8, 1, 0.05, 0.3, 0.17, 0.6, 0.15, 0.47, 1, 0.2, 0.3, 0.29, 0.6, 0.15, 0.05, 0.69, 0.99, 0.2, 0.08, 0, 1, 0.7],
      min: [0.35, 0.35, 0.1, 0.12, 0.05, 0, 0.03, 0, 0, 0, 0], lf: "volcano lava-flow lava-tube pit subsurface", sc: "volcanic basaltic regolith" }),
    T({ id: "r-utopia", body: "mars", name: "Utopia Planitia (Zhurong)", kind: "Zhurong site", lat: 25.07, lon: 109.93, note: "Northern lowland plains with possible buried ice and ancient shoreline deposits.",
      v: [0.25, 0.88, 0.14, 0.85, 0.75, 0.35, 0.8, 1, 0.35, 0.48, 0.03, 0.3, 0.15, 0.33, 0.1, 0.2, 0.32, 0.56, 0.75, 0.4, 0.4, 0.73, 0.99, 0.2, 0.08, 0, 1, 0.55],
      min: [0.3, 0.25, 0.1, 0.15, 0.05, 0.03, 0.05, 0.02, 0.02, 0.03, 0], lf: "plain patterned crater glacial", sc: "basaltic regolith ice sedimentary" }),
  ];

  const S = (o) => o;
  const SITES = [
    S({ id: "yungay", name: "Yungay, Atacama Desert", place: "Chile", lat: -24.10, lon: -70.02, elev: 1000, status: "established",
      blurb: "Hyperarid core of the Atacama. Soils hold nitrates and perchlorates and almost no microbial life.",
      use: "Life-detection drills, perchlorate handling, long-range rover autonomy.",
      v: [0.15, 0.4, 0.29, 0.97, 0.3, 0.35, 0.9, 1, 0.3, 0.37, 0.1, 0.3, 0.15, 0.5, 0.05, 0.15, 0.55, 0.81, 0.5, 0, 0, 0.45, 0.99, 0.85, 0.3, 0.15, 0.17, 0.4],
      min: [0.25, 0.04, 0, 0.06, 0.04, 0.04, 0.2, 0, 0.15, 0, 0.22], lf: "evaporite fluvial plain", sc: "evaporite sedimentary regolith" }),
    S({ id: "licancabur", name: "Licancabur summit lake", place: "Chile–Bolivia", lat: -22.83, lon: -67.88, elev: 5916, status: "studied",
      blurb: "Volcano with one of the highest lakes on Earth, under intense UV and roughly half sea-level air pressure.",
      use: "UV-hardened optics, high-altitude crew operations, UV-stressed extremophiles.",
      v: [0.15, 0.6, 0.3, 0.85, 0.25, 0.6, 0.55, 0.85, 0.45, 0.34, 0.6, 0.75, 0.6, 0.33, 0.1, 0.35, 0.62, 0.85, 0.45, 0.35, 0.4, 0.62, 0.9, 0.7, 0.4, 0.12, 0.24, 0.45],
      min: [0.35, 0.15, 0.02, 0.2, 0.05, 0.03, 0.05, 0, 0.03, 0, 0.12], lf: "volcano crater evaporite", sc: "volcanic regolith" }),
    S({ id: "haughton", name: "Haughton Crater, Devon Island", place: "Nunavut, Canada", lat: 75.37, lon: -89.67, elev: 200, status: "established",
      blurb: "23 km impact crater in a polar desert, home of the Haughton-Mars Project since 1997.",
      use: "Crewed traverse rehearsal, impact-hydrothermal geology, polar logistics.",
      v: [0.82, 0.1, 0.07, 0.4, 0.15, 0.3, 0.35, 0.8, 0.55, 0.16, 0.17, 0.5, 0.5, 0.33, 0.05, 0.35, 0.05, 0.89, 0.55, 0.9, 0.66, 0.83, 0.55, 0.1, 0, 0.05, 0.75, 0.4],
      min: [0.05, 0, 0, 0.1, 0, 0.1, 0.1, 0.55, 0, 0, 0.1], lf: "crater patterned fluvial", sc: "impact sedimentary altered" }),
    S({ id: "beacon", name: "Beacon Valley, McMurdo Dry Valleys", place: "Antarctica", lat: -77.83, lon: 160.67, elev: 1300, status: "established",
      blurb: "Hyperarid cold desert where glacier ice, possibly millions of years old, lies buried under thin till and polygons.",
      use: "Ice-prospecting drills and radar, cold-regolith excavation, polygon terrain mobility.",
      v: [0.85, 0.2, 0.1, 0.6, 0.15, 0.55, 0.5, 0.98, 0.15, 0.2, 0.27, 0.55, 0.45, 0.3, 0, 0.25, 0.6, 0.9, 0.85, 0.95, 0.7, 0.87, 0.97, 0.05, 0.02, 0.05, 0.95, 0.45],
      min: [0.2, 0.2, 0, 0.02, 0.03, 0, 0, 0, 0.05, 0.2, 0.3], lf: "glacial patterned layered", sc: "ice sedimentary basaltic" }),
    S({ id: "domea", name: "Dome A (Dome Argus)", place: "East Antarctic Plateau", lat: -80.37, lon: 77.35, elev: 4093, status: "candidate",
      blurb: "Highest ice dome on the Antarctic plateau: near-record cold, calm air, months of polar night and a grazing sun.",
      use: "Lunar polar-night power and thermal tests, cryogenic hardware, low-sun navigation, isolation studies.",
      v: [0.9, 0.22, 0.12, 0.75, 0.02, 0.15, 0.65, 0.97, 0.02, 0.18, 0, 0.05, 0, 1, 0, 0.15, null, 0.56, 0.6, 1, 1, 1, 0.99, 0.02, 0, 0.02, 1, 0.95],
      min: [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], lf: "glacial plain", sc: "ice" }),
    S({ id: "badwater", name: "Badwater Basin, Death Valley", place: "California, USA", lat: 36.25, lon: -116.82, elev: -86, status: "established",
      blurb: "Salt pan 86 m below sea level with evaporite polygons, alluvial fans and extreme summer heat.",
      use: "Evaporite mineral detection, thermal stress on rovers, playa trafficability.",
      v: [0.2, 0.28, 0.23, 0.85, 0.5, 0.35, 0.7, 0.93, 0.65, 0.34, 0.02, 0.35, 0.02, 0.83, 0.05, 0.45, 0.35, 0.89, 0.5, 0, 0, 0.67, 0.75, 0.55, 0.15, 0.3, 0.24, 0.55],
      min: [0.05, 0, 0, 0, 0, 0.1, 0.1, 0.1, 0.55, 0, 0.1], lf: "evaporite fluvial layered", sc: "evaporite sedimentary" }),
    S({ id: "lut", name: "Lut Desert kaluts", place: "Kerman, Iran", lat: 30.50, lon: 58.00, elev: 300, status: "candidate",
      blurb: "Wind-carved yardangs tens of metres tall. MODIS recorded 70.7 °C land-surface temperature in the Lut in 2005.",
      use: "Yardang analog for Mars' Medusae Fossae, aeolian erosion rates, extreme-heat thermal testing.",
      v: [0.2, 0.3, 0.24, 0.85, 0.75, 0.9, 0.7, 0.96, 0.45, 0.41, 0.1, 0.7, 0.15, 0.5, 0.1, 0.6, 0.6, 0.81, 0.45, 0, 0, 0.5, 0.97, 0.5, 0.1, 0.06, 0.25, 0.5],
      min: [0.15, 0, 0, 0, 0.05, 0.2, 0.1, 0.1, 0.1, 0, 0.3], lf: "yardangs dunes evaporite", sc: "sedimentary evaporite regolith" }),
    S({ id: "dalangtan", name: "Dalangtan playa, Qaidam Basin", place: "Qinghai, China", lat: 38.55, lon: 91.75, elev: 2800, status: "candidate",
      blurb: "High, hyperarid salt playa with sulfates, chlorides and yardangs. Studied as a Mars analog mostly by Chinese teams.",
      use: "Sulfate and chloride spectroscopy, salt-crust trafficability, yardang mapping.",
      v: [0.2, 0.33, 0.22, 0.8, 0.75, 0.85, 0.65, 0.93, 0.65, 0.37, 0.05, 0.45, 0.05, 0.58, 0.1, 0.5, 0.15, 0.81, 0.6, 0.05, 0, 0.62, 0.95, 0.5, 0.02, 0.2, 0.41, 0.6],
      min: [0.05, 0, 0, 0, 0, 0.15, 0.25, 0.1, 0.3, 0, 0.15], lf: "yardangs evaporite layered", sc: "evaporite sedimentary" }),
    S({ id: "kamil", name: "Kamil Crater", place: "East Uweinat, Egypt", lat: 22.018, lon: 26.088, elev: 600, status: "candidate",
      blurb: "45 m crater found on satellite imagery in 2008. An iron meteorite made it a few thousand years ago and its bright ray ejecta survive intact.",
      use: "Small fresh-crater morphology, ejecta-ray mapping, hazard detection for landers.",
      v: [0.12, 0.3, 0.25, 0.97, 0.6, 0.55, 0.88, 0.99, 0.25, 0.37, 0.1, 0.45, 0.35, 0.58, 0, 0.3, 1, 0.7, 0.5, 0, 0, 0.42, 0.99, 0.1, 0, 0.03, 0.73, 0.55],
      min: [0.05, 0, 0, 0.05, 0.05, 0.05, 0, 0, 0, 0, 0.8], lf: "crater plain", sc: "impact sedimentary regolith" }),
    S({ id: "emikoussi", name: "Emi Koussi, Tibesti", place: "Chad", lat: 19.79, lon: 18.55, elev: 3415, status: "candidate",
      blurb: "Shield volcano in the central Sahara with nested calderas holding pale lakebed deposits from wetter times.",
      use: "Remote-sensing study of a desert shield volcano, caldera geology, dust-laden operations.",
      v: [0.12, 0.38, 0.25, 0.9, 0.7, 0.7, 0.75, 0.9, 0.4, 0.36, 0.35, 0.65, 0.5, 0.42, 0.15, 0.3, 0.62, 0.85, 0.55, 0, 0, 0.5, 0.95, 0.15, 0.2, 0.05, 0.8, 0.4],
      min: [0.35, 0.15, 0.05, 0.15, 0.05, 0.05, 0, 0.05, 0, 0, 0.15], lf: "volcano crater lava-flow", sc: "volcanic regolith" }),
    S({ id: "khaybar", name: "Umm Jirsan, Harrat Khaybar", place: "Saudi Arabia", lat: 25.58, lon: 39.83, elev: 1400, status: "candidate",
      blurb: "Arabia's longest known lava tube, about 1.5 km, in a vast arid basalt field of shields and cinder cones.",
      use: "Lava-tube mapping with lidar and radar, cave habitat studies, basalt construction tests.",
      v: [0.15, 0.33, 0.24, 0.85, 0.6, 0.5, 0.7, 0.88, 0.3, 0.38, 0.1, 0.8, 0.85, 0.17, 1, 0.2, 0.28, 0.93, 0.85, 0, 0, 0.54, 0.93, 0.35, 0.35, 0.2, 0.26, 0.45],
      min: [0.35, 0.3, 0.15, 0.1, 0.07, 0, 0, 0.03, 0, 0, 0], lf: "lava-flow lava-tube volcano pit", sc: "volcanic basaltic regolith" }),
    S({ id: "payun", name: "Payún Matrú, La Payunia", place: "Mendoza, Argentina", lat: -36.42, lon: -69.20, elev: 2500, status: "candidate",
      blurb: "One of Earth's densest volcanic fields, with 800+ cones, very long pahoehoe flows and lava tubes in semi-arid Patagonia.",
      use: "Long-flow emplacement studies (Tharsis analog), tube detection, rover traverses on lava.",
      v: [0.2, 0.3, 0.2, 0.65, 0.4, 0.6, 0.45, 0.75, 0.35, 0.32, 0.13, 0.75, 0.8, 0.2, 0.75, 0.25, 0.38, 0.89, 0.8, 0, 0, 0.62, 0.85, 0.35, 0.3, 0.12, 0.37, 0.45],
      min: [0.38, 0.27, 0.12, 0.15, 0.06, 0, 0, 0, 0, 0, 0.02], lf: "lava-flow volcano lava-tube crater", sc: "volcanic basaltic" }),
    S({ id: "craters", name: "Craters of the Moon", place: "Idaho, USA", lat: 43.42, lon: -113.52, elev: 1800, status: "established",
      blurb: "Basalt flows about 2,000 years old with lava tubes, some holding perennial ice. A NASA FINESSE field site.",
      use: "EVA science operations, cave-ice sampling, basalt field mobility.",
      v: [0.25, 0.23, 0.17, 0.5, 0.25, 0.35, 0.35, 0.6, 0.35, 0.32, 0.1, 0.8, 0.85, 0.17, 0.95, 0.15, 0.3, 0.9, 0.8, 0.05, 0.4, 0.69, 0.75, 0.35, 0.25, 0.3, 0.17, 0.4],
      min: [0.35, 0.28, 0.12, 0.15, 0.08, 0, 0, 0, 0, 0.02, 0], lf: "lava-flow lava-tube volcano pit cold-trap", sc: "volcanic basaltic" }),
    S({ id: "lanzarote", name: "La Corona lava tube, Lanzarote", place: "Canary Islands, Spain", lat: 29.16, lon: -13.44, elev: 50, status: "established",
      blurb: "Lava tube several kilometres long that runs out under the sea, opened by collapse skylights (jameos). ESA trains astronauts here.",
      use: "Cave navigation, skylight descent, geology training (ESA PANGAEA).",
      v: [0.15, 0.25, 0.18, 0.55, 0.4, 0.55, 0.6, 0.8, 0.3, 0.22, 0.1, 0.75, 0.7, 0.2, 1, 0.25, 0.25, 0.74, 0.85, 0, 0, 0.65, 0.85, 0.25, 0.4, 0.55, 0.08, 0.35],
      min: [0.3, 0.3, 0.18, 0.15, 0.05, 0, 0, 0.02, 0, 0, 0], lf: "lava-flow lava-tube volcano pit", sc: "volcanic basaltic regolith" }),
    S({ id: "holuhraun", name: "Holuhraun lava field", place: "Iceland", lat: 64.87, lon: -16.83, elev: 750, status: "studied",
      blurb: "Fresh basalt from the 2014–15 eruption, Iceland's largest in over 200 years, next to glacial outwash plains and active dust sources.",
      use: "Fresh-basalt weathering, sand transport on lava, flow-margin mapping.",
      v: [0.45, 0.1, 0.06, 0.2, 0.55, 0.65, 0.15, 0.5, 0.75, 0.22, 0.04, 0.85, 0.9, 0.13, 0.2, 0.55, 0.35, 0.85, 0.8, 0.25, 0.15, 0.75, 0.65, 0.65, 0.8, 0.08, 0.37, 0.5],
      min: [0.35, 0.3, 0.1, 0.18, 0.05, 0, 0.02, 0, 0, 0, 0], lf: "lava-flow fluvial dunes glacial", sc: "volcanic basaltic regolith sedimentary" }),
    S({ id: "undara", name: "Undara lava tubes", place: "Queensland, Australia", lat: -18.25, lon: 144.60, elev: 750, status: "candidate",
      blurb: "Large tube system from an eruption about 190,000 years ago that sent lava some 160 km.",
      use: "Large-diameter tube surveys, skylight-collapse mechanics, cave microclimate logging.",
      v: [0.12, 0.33, 0.19, 0.6, 0.2, 0.15, 0.5, 0.4, 0.55, 0.29, 0.06, 0.55, 0.4, 0.25, 1, 0.2, 0.3, 0.87, 0.7, 0, 0, 0.79, 0.55, 0.1, 0.05, 0.25, 0.3, 0.3],
      min: [0.3, 0.25, 0.12, 0.05, 0.08, 0.18, 0, 0, 0, 0, 0.02], lf: "lava-flow lava-tube pit volcano", sc: "volcanic basaltic" }),
    S({ id: "pilbara", name: "Dresser Formation, Pilbara", place: "Western Australia", lat: -21.15, lon: 119.42, elev: 400, status: "studied",
      blurb: "3.48-billion-year-old hot-spring deposits and stromatolites, among Earth's oldest signs of life.",
      use: "Biosignature detection in ancient rock, a reference for Jezero samples.",
      v: [0.12, 0.33, 0.23, 0.8, 0.45, 0.35, 0.65, 0.78, 0.75, 0.32, 0.17, 0.6, 0.6, 0.25, 0.05, 0.2, 0.75, 0.92, 0.5, 0, 0, 0.62, 0.85, 0.15, 0, 0.35, 0.55, 0.3],
      min: [0.1, 0.1, 0, 0, 0.1, 0.15, 0.05, 0.1, 0, 0, 0.4], lf: "layered hydrothermal", sc: "sedimentary altered basaltic" }),
    S({ id: "riotinto", name: "Río Tinto", place: "Andalusia, Spain", lat: 37.72, lon: -6.55, elev: 400, status: "established",
      blurb: "Acidic, iron- and sulfate-rich river (pH about 2) that deposits jarosite and hematite, as Opportunity found at Meridiani.",
      use: "Acid-sulfate mineralogy, subsurface drilling for life (MARTE), Fe-oxide spectroscopy.",
      v: [0.2, 0.23, 0.17, 0.6, 0.2, 0.15, 0.4, 0.4, 0.85, 0.26, 0.33, 0.55, 0.45, 0.25, 0.3, 0.5, 0.5, 0.89, 0.6, 0, 0, 0.79, 0.5, 0.3, 0, 0.7, 0.13, 0.3],
      min: [0.05, 0, 0, 0, 0.3, 0.15, 0.3, 0, 0.05, 0, 0.15], lf: "fluvial layered hydrothermal", sc: "altered sedimentary" }),
    S({ id: "dallol", name: "Dallol, Danakil Depression", place: "Afar, Ethiopia", lat: 14.24, lon: 40.30, elev: -45, status: "studied",
      blurb: "Hydrothermal salt field below sea level with hyperacid, hypersaline pools that test the limits of habitability.",
      use: "Habitability limits, brine and salt spectroscopy, instrument survival in corrosive heat.",
      v: [0.12, 0.33, 0.2, 0.75, 0.45, 0.4, 0.7, 0.93, 0.7, 0.29, 0.07, 0.6, 0.25, 0.67, 0.15, 0.95, 0, 0.9, 0.4, 0, 0, 0.75, 0.6, 0.8, 0.85, 0.2, 0.41, 0.45],
      min: [0, 0, 0, 0, 0.1, 0.05, 0.25, 0.05, 0.5, 0, 0.05], lf: "hydrothermal evaporite volcano", sc: "evaporite altered volcanic" }),
    S({ id: "kobuk", name: "Great Kobuk Sand Dunes", place: "Alaska, USA", lat: 67.08, lon: -159.02, elev: 60, status: "candidate",
      blurb: "Active Arctic dune field above the Arctic Circle, with permafrost and long winter darkness.",
      use: "Cold-climate dune migration, frozen-sand mechanics, polar Mars dune analog.",
      v: [0.7, 0.08, 0.06, 0.3, 0.3, 0.65, 0.25, 0.55, 0.6, 0.22, 0.3, 0.35, 0, 0.42, 0, 0.8, 1, 0.67, 0.3, 0.6, 0.5, 0.75, 0.6, 0.25, 0, 0.03, 0.65, 0.75],
      min: [0.12, 0.03, 0, 0, 0.03, 0.05, 0, 0, 0, 0.02, 0.75], lf: "dunes patterned fluvial", sc: "sedimentary regolith ice" }),
    S({ id: "bockfjord", name: "Sverrefjell, Bockfjord", place: "Svalbard, Norway", lat: 79.43, lon: 13.33, elev: 300, status: "established",
      blurb: "Volcanic centre whose carbonate globules closely resemble those in Martian meteorite ALH84001. AMASE expedition site.",
      use: "Carbonate biosignature work, sample-caching rehearsal, polar fieldwork.",
      v: [0.82, 0.06, 0.06, 0.25, 0.1, 0.4, 0.2, 0.75, 0.65, 0.16, 0.5, 0.65, 0.55, 0.25, 0.05, 0.35, 0.25, 0.93, 0.55, 0.95, 0.6, 0.83, 0.6, 0.2, 0.05, 0.05, 0.6, 0.35],
      min: [0.3, 0.25, 0.15, 0.08, 0.05, 0, 0, 0.12, 0, 0.05, 0], lf: "volcano hydrothermal glacial patterned", sc: "volcanic basaltic ice altered" }),
    S({ id: "erebus", name: "Erebus fumarolic ice caves", place: "Ross Island, Antarctica", lat: -77.52, lon: 167.15, elev: 3400, status: "studied", mode: "subsurface",
      blurb: "Ice caves melted by volcanic gas near the summit of Earth's southernmost active volcano: dark, cold and nutrient-poor.",
      use: "Cold-trap sampling, dark-cave robotics, life in ice-rock interfaces.",
      v: [0.95, 0.03, 0.02, null, 0.05, 0.1, 0.85, 0.85, 0.05, 0.08, 0.3, 0.6, 0.3, 0.6, 0.85, 0.7, 0.5, 0.79, 0.5, 0.9, 0.95, 0.94, 0.6, 0.4, 0.95, 0.05, 0.95, 0.85],
      min: [0.25, 0.05, 0, 0.15, 0.05, 0, 0.03, 0, 0, 0.45, 0.02], lf: "volcano glacial cold-trap hydrothermal subsurface", sc: "volcanic ice altered" }),
    S({ id: "stillwater", name: "Stillwater Complex", place: "Montana, USA", lat: 45.38, lon: -109.88, elev: 2000, status: "candidate",
      blurb: "Layered intrusion whose anorthosite was used to make NASA's lunar highlands regolith simulant (NU-LHT).",
      use: "Highland-rock spectroscopy, simulant feedstock, anorthosite ISRU tests.",
      v: [0.25, 0.23, 0.15, 0.45, 0.1, 0.2, 0.3, 0.35, 0.6, 0.26, 0.65, 0.7, 0.7, 0.3, 0.3, 0.3, 0.35, 0.95, 0.95, 0.05, 0, 0.75, 0.45, 0.3, 0, 0.5, 0.17, 0.25],
      min: [0.8, 0.15, 0.03, 0, 0.02, 0, 0, 0, 0, 0, 0], lf: "massif layered", sc: "anorthositic" }),
    S({ id: "qiangtang", name: "Qiangtang Plateau", place: "Tibet, China", lat: 34.5, lon: 86.0, elev: 5000, status: "candidate",
      blurb: "Cold desert around 5,000 m with permafrost, salt lakes, intense UV and about half sea-level air pressure.",
      use: "Permafrost and UV together, low-pressure crew physiology, saline-lake spectroscopy.",
      v: [0.2, 0.45, 0.24, 0.6, 0.45, 0.6, 0.4, 0.75, 0.55, 0.34, 0.13, 0.35, 0.2, 0.42, 0.05, 0.45, 0.6, 0.83, 0.55, 0.75, 0.54, 0.79, 0.65, 0.6, 0.1, 0.04, 0.6, 0.55],
      min: [0.2, 0, 0, 0, 0, 0.15, 0.05, 0.15, 0.05, 0.05, 0.35], lf: "patterned evaporite glacial plain", sc: "sedimentary ice evaporite" }),
    S({ id: "boulby", name: "Boulby Underground Laboratory", place: "North Yorkshire, UK", lat: 54.55, lon: -0.82, elev: -1100, status: "established", mode: "subsurface",
      blurb: "1.1 km down a working potash and salt mine in Permian evaporites. Hosts the MINAR rover and instrument trials.",
      use: "Subsurface rover operations, evaporite life detection, low-background instruments.",
      v: [1, 0, 0, null, 0.3, 0, 1, 0.85, 0.7, 0.04, 0, 0.3, 0.3, null, 1, 0.05, 0.05, 0.95, 0.35, 0, 0, 0.6, 0.95, 0.05, 0, 0.8, 0.08, 0.85],
      min: [0, 0, 0, 0, 0, 0.05, 0.3, 0.05, 0.6, 0, 0], lf: "subsurface layered evaporite", sc: "evaporite sedimentary" }),
    S({ id: "wabar", name: "Wabar craters, Rub' al Khali", place: "Saudi Arabia", lat: 21.50, lon: 50.47, elev: 200, status: "candidate",
      blurb: "Iron-meteorite craters in the Empty Quarter dunes, with impact glass and black glass beads, slowly being buried by sand.",
      use: "Crater burial by dunes, impact-glass detection, navigation in featureless sand seas.",
      v: [0.12, 0.33, 0.22, 0.92, 0.75, 0.85, 0.8, 0.99, 0.2, 0.37, 0.17, 0.35, 0.05, 0.67, 0, 0.85, 1, 0.69, 0.35, 0, 0, 0.42, 0.98, 0.05, 0, 0.02, 0.65, 0.8],
      min: [0.03, 0, 0, 0.08, 0.04, 0, 0, 0, 0, 0, 0.85], lf: "crater dunes", sc: "impact sedimentary regolith" }),
    S({ id: "lonar", name: "Lonar Crater", place: "Maharashtra, India", lat: 19.98, lon: 76.51, elev: 480, status: "candidate",
      blurb: "1.8 km crater in Deccan basalt: one of very few well-preserved impacts into basalt, the commonest crater target on the Moon and Mars.",
      use: "Shock effects in basalt, ejecta in mare-like rock, crater-rim mobility.",
      v: [0.12, 0.3, 0.17, 0.5, 0.25, 0.2, 0.3, 0.3, 0.8, 0.22, 0.17, 0.5, 0.35, 0.25, 0.05, 0.3, 0.35, 0.89, 0.7, 0, 0, 0.85, 0.45, 0.15, 0, 0.45, 0.21, 0.25],
      min: [0.35, 0.3, 0.05, 0.1, 0.05, 0.12, 0, 0.03, 0, 0, 0], lf: "crater lava-flow", sc: "impact basaltic volcanic" }),
  ];

  /* ---------- Spectral model (illustrative stand-in for EMIT / M³ / CRISM spectra) ---------- */
  const WL = []; for (let w = 0.4; w <= 2.5001; w += 0.02) WL.push(Math.round(w * 100) / 100);
  const band = (l, c, d, w) => 1 - d * Math.exp(-0.5 * ((l - c) / w) ** 2);
  const EM = [
    (l) => (0.55 + 0.03 * (l - 0.4)) * band(l, 1.25, 0.08, 0.15),
    (l) => (0.28 + 0.06 * (l - 0.4)) * band(l, 0.93, 0.35, 0.09) * band(l, 1.95, 0.3, 0.22),
    (l) => (0.4 + 0.04 * (l - 0.4)) * band(l, 0.85, 0.15, 0.07) * band(l, 1.05, 0.45, 0.1) * band(l, 1.25, 0.25, 0.09),
    (l) => (0.12 + 0.06 * (l - 0.4)) * band(l, 1.05, 0.15, 0.2) * band(l, 1.95, 0.12, 0.25),
    (l) => (0.08 + 0.18 / (1 + Math.exp(-(l - 0.6) / 0.03))) * band(l, 0.88, 0.25, 0.06),
    (l) => (0.45 + 0.05 * (l - 0.4)) * band(l, 0.4, 0.3, 0.15) * band(l, 1.41, 0.15, 0.025) * band(l, 1.91, 0.25, 0.035) * band(l, 2.29, 0.15, 0.03) * band(l, 2.39, 0.08, 0.03),
    (l) => 0.65 * band(l, 0.43, 0.15, 0.03) * band(l, 1.44, 0.25, 0.03) * band(l, 1.75, 0.1, 0.03) * band(l, 1.94, 0.35, 0.04) * band(l, 2.21, 0.1, 0.03) * band(l, 2.27, 0.08, 0.03),
    (l) => (0.6 + 0.04 * (l - 0.4)) * band(l, 1.9, 0.06, 0.04) * band(l, 2.33, 0.25, 0.04) * band(l, 2.5, 0.2, 0.05),
    (l) => 0.78 * band(l, 1.45, 0.04, 0.03) * band(l, 1.95, 0.06, 0.04),
    (l) => (0.92 - 0.02 * (l - 0.4)) * band(l, 1.03, 0.15, 0.05) * band(l, 1.25, 0.25, 0.06) * band(l, 1.5, 0.7, 0.1) * band(l, 2.0, 0.85, 0.12) * band(l, 2.5, 0.5, 0.2),
    (l) => (0.5 + 0.15 * (1 - Math.exp(-(l - 0.4) / 0.3))) * band(l, 1.4, 0.04, 0.03) * band(l, 1.9, 0.05, 0.04),
  ];
  const marsDust = (l) => (0.05 + 0.33 / (1 + Math.exp(-(l - 0.62) / 0.05))) * band(l, 1.92, 0.04, 0.05);
  function spectrum(min, body) {
    const tot = min.reduce((a, b) => a + b, 0) || 1;
    let R = WL.map((l) => min.reduce((s, a, i) => s + (a / tot) * EM[i](l), 0));
    if (body === "moon") { const C = R.reduce((a, b) => a + b, 0) / R.length; R = R.map((r, i) => (0.5 * r + 0.5 * C) * (0.55 + 0.22 * (WL[i] - 0.4))); }
    if (body === "mars") R = R.map((r, i) => 0.65 * r + 0.35 * marsDust(WL[i]));
    return R;
  }
  const dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);
  const cos = (a, b) => { const d = Math.sqrt(dot(a, a) * dot(b, b)); return d ? dot(a, b) / d : 0; };
  const sum = (a) => (a || []).reduce((s, x) => s + (x || 0), 0);
  const bray = (a, b) => { const sa = sum(a), sb = sum(b); let d = 0; a.forEach((x, i) => (d += Math.abs(x / sa - b[i] / sb))); return 1 - d / 2; };

  /* ---------- Scoring ---------- */
  const SIGMA = 0.3;
  const numSim = (a, b) => Math.exp(-(((a - b) / SIGMA) ** 2));
  const tagSim = (site, target) => { const T = target.split(" "), S = new Set(site.split(" ")); return T.filter((t) => S.has(t)).length / T.length; };

  function expand(e) {
    const o = { ...e, x: {} };
    NUM.forEach((id, i) => { o.x[id] = e.v[i] == null ? null : e.v[i]; });
    return o;
  }

  // per-parameter similarity in [0,1] or null when data is missing
  function paramSims(site, target, opts = {}) {
    const out = {};
    for (const p of PARAMS) {
      if (p.kind === "num") {
        const a = site.x[p.id], b = target.x[p.id];
        if (a == null || b == null) { out[p.id] = null; continue; }
        out[p.id] = p.invertible && opts.preferAccess ? 1 - a : numSim(a, b);
      } else if (p.kind === "tags") {
        out[p.id] = site[p.tagKey] && target[p.tagKey] ? tagSim(site[p.tagKey], target[p.tagKey]) : null;
      } else if (!sum(site.min) || !sum(target.min)) {
        out[p.id] = null;
      } else if (p.kind === "vec") {
        out[p.id] = bray(site.min, target.min);
      } else if (p.kind === "spec") {
        const th = Math.acos(Math.min(1, cos(spectrum(site.min, "earth"), spectrum(target.min, target.body))));
        out[p.id] = Math.max(0, 1 - th / 0.35);
      }
    }
    return out;
  }

  function score(site, target, weights, opts) {
    const sims = paramSims(site, target, opts);
    let num = 0, den = 0, all = 0;
    for (const p of PARAMS) {
      const w = weights[p.id] ?? 1; all += w;
      if (sims[p.id] == null || w === 0) continue;
      num += w * sims[p.id]; den += w;
    }
    return { score: den ? num / den : 0, coverage: all ? den / all : 0, sims };
  }

  const PRESETS = [
    { id: "balanced", name: "Balanced", base: 1, w: {} },
    { id: "ops", name: "Base operations", base: 0.5, w: { light: 3, solar: 3, slope: 3, rough: 2.5, rocks: 2.5, navdiff: 2.5, dust: 2, tswing: 2, clear: 1.5, albedo: 1.5, ti: 1.5, persist: 1.5, remote: 1 } },
    { id: "geology", name: "Geology & sampling", base: 0.5, w: { landforms: 3, surface: 3, mineralogy: 3, spectral: 2.5, silica: 2, ti: 1.5, rocks: 1.5, albedo: 1.5, rain: 1.5, activity: 1, caves: 1 } },
    { id: "water", name: "Water & ISRU", base: 0.5, w: { subsurface: 3, icedepth: 3, hydrogen: 3, isru: 3, soilm: 2, aridity: 1.5, tswing: 1.5, mineralogy: 1 } },
    { id: "caves", name: "Caves & shelter", base: 0.5, w: { caves: 3, landforms: 2, light: 2, persist: 2, tswing: 2, surface: 1.5, isru: 1.5, seismic: 1.5, navdiff: 1.5 } },
    { id: "optics", name: "Instruments & optics", base: 0.5, w: { clear: 3, uv: 2.5, dust: 2.5, spectral: 2.5, albedo: 2, navdiff: 2, solar: 1.5, persist: 1.5, tswing: 1 } },
  ];
  const presetWeights = (id) => { const p = PRESETS.find((x) => x.id === id) || PRESETS[0]; const w = {}; PARAMS.forEach((q) => (w[q.id] = p.w[q.id] ?? p.base)); return w; };

  return { GROUPS, PARAMS, NUM, MINERALS, LANDFORMS, MATERIALS, GAPS, TARGETS: TARGETS.map(expand), SITES: SITES.map(expand), PRESETS, presetWeights, score, paramSims, spectrum, WL, expand };
})();
if (typeof module !== "undefined") module.exports = MODEL;
