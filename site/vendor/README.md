# Third-party files for the page

This folder holds code and images that we did not make. The page loads them from here, so it needs no outside host.

| File | What it is | Licence |
|---|---|---|
| `globe.gl.min.js` | globe.gl version 2.46.2, the library that draws the 3D globes | MIT (`globe.gl.LICENSE.txt`) |
| `globe.gl.LICENSE.txt` | The licence of globe.gl | - |
| `three.LICENSE.txt` | The licence of three.js, which globe.gl bundles | - |
| `textures/earth.jpg` | Surface image of the Earth, 4096 x 2048 | See below |
| `textures/moon.jpg` | Surface image of the Moon, 4096 x 2048 | Public domain |
| `textures/mars.jpg` | Surface image of Mars, 4096 x 2048 | Public domain |
| `textures/textures.json` | Size, centre longitude, source, credit and licence of each image | - |

## globe.gl 2.46.2

- Project: https://github.com/vasturiano/globe.gl
- File taken from: https://cdn.jsdelivr.net/npm/globe.gl@2.46.2/dist/globe.gl.min.js
- Licence: MIT. The full text is in `globe.gl.LICENSE.txt`.

The file bundles three.js revision 185. three.js is also MIT. Its licence was taken from the project's own repository at tag r185 (https://github.com/mrdoob/three.js/blob/r185/LICENSE). The text is in `three.LICENSE.txt`.

The bundle also keeps two other notices inside the file. One is for h3-js (Uber Technologies, Apache License 2.0). The other is for the Helvetiker typeface (MAGENTA Ltd, MgOpen licence). Do not remove the comments that hold them.

## The three images

Each image is a plain latitude and longitude grid (equirectangular). North is at the top. The image covers 90 N to 90 S and all 360 degrees of longitude. The centre of each image is longitude 0, so the left edge is 180 W. All three were fetched on 15 November 2026 from the providers' own sites. `textures/textures.json` gives the exact addresses and how each file was made.

### Earth: `textures/earth.jpg`

- What it shows: Blue Marble: Next Generation, July 2004, with shading for topography and bathymetry. Natural colour, no clouds.
- Provider: NASA Earth Observatory.
- Page: https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-topography-bathymetry/
- Credit: **NASA Earth Observatory**
- Licence: the provider's pages state no licence. They ask for the credit above. NASA's media usage page did not answer our client (HTTP 429), so we did not read it.

### Moon: `textures/moon.jpg`

- What it shows: the CGI Moon Kit colour map with the poles filled (2019 version). Colour from the Lunar Reconnaissance Orbiter Camera. North of 70 N and south of 70 S the map is a grey albedo map from the laser altimeter. Our four lunar regions are in that grey band.
- Provider: NASA's Scientific Visualization Studio.
- Page: https://svs.gsfc.nasa.gov/4720/
- Credit: **NASA's Scientific Visualization Studio**
- Licence: public domain. The studio's help page (https://svs.gsfc.nasa.gov/help/) says: "All of our content is in the public domain (unless otherwise noted)".

### Mars: `textures/mars.jpg`

- What it shows: the Mars Viking Colorized Global Mosaic (MDIM 2.1). These are Viking Orbiter images. NASA Ames coloured the mosaic. The colour looks natural, but it is not a true-colour photograph.
- Provider: USGS Astrogeology Science Center, from NASA Viking Orbiter data.
- Page: https://astrogeology.usgs.gov/search/map/mars_viking_colorized_global_mosaic_232m
- Credit: **Mars Viking Colorized Global Mosaic (MDIM 2.1): USGS Astrogeology Science Center and NASA Ames; Viking Orbiter images, NASA.** This is our wording; the page gives no credit line.
- Licence: public domain. The product page says "Access Constraints: Public domain" and "Use Constraints: None".

NASA is credited by name only. Do not add a NASA logo or insignia to the page.
