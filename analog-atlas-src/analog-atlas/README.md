# Analog Atlas front end

- `index.html`: the built, self-contained page. Open it in a browser.
- `src/model.js`: parameters, Moon/Mars targets, seed Earth sites and the scoring function. Edit this, or load JSON from your pipeline in the UI.
- `src/app.js`: the globe (d3-geo on canvas), panels and interactions.
- `src/style.css`, `src/index.template.html`: layout and styling.
- `basemap.json`: land, desert and glacier outlines (Natural Earth, public domain).

Rebuild after editing: `node build.js src basemap.json index.html`

Seed values are indicative estimates. Replace them with values computed from rasters
(e.g. MODIS LST, MERRA-2, SMAP, EMIT, Copernicus DEM on Earth; LRO Diviner/LOLA, CRISM/THEMIS/MOLA on the Moon and Mars).
