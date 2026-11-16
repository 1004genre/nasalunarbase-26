// Added by deploy/use_server_models.py: true if this copy of the page runs on the visitor's own computer.
const ETF_LOCAL=/^(?:localhost|127\.0\.0\.1|\[::1\])$/.test(globalThis.location?.hostname||'localhost');
// Words become criteria. Only the readers and arithmetic below select places.
const GROUPS = ['Activity', 'Light', 'Likeness to the site', 'Time of year', 'Ground', 'Climate', 'Access', 'Land and permits', 'People and hazards', 'Power', 'Region'];
// These main options, their order and their sizes are a design decision of the team.
// Each row is: canonical id, name, category, size, icon. Other named fields are More options.
const MAIN_OPTIONS = {
  moon: [
    ['activity:rover','Rover operations in long shadows','Activity','large','rover'],
    ['activity:camera','Camera and navigation tests','Activity','large','camera'],
    ['activity:crew','Crew work on foot','Activity','large','boot'],
    ['activity:lamp','Lamp comparison with the real Sun','Activity','medium','lamp'],
    ['h30','Low-Sun hours in the best 30 days','Light','large','sun'],
    ['hours','Low-Sun hours in the selected time','Light','medium','sun'],
    ['month','Month','Time of year','large','calendar'],
    ['season','Half-year','Time of year','small','calendar'],
    ['factor:p90_slope','Slope that 90 percent of the ground stays under','Ground','large','slope'],
    ['slope_likeness','Slopes like the lunar region','Ground','medium','slope'],
    ['bare','Bare ground','Ground','medium','rock'],
    ['factor:rock_class','Rock type','Ground','medium','rock'],
    ['factor:volcanic','Volcanic rock','Ground','small','volcano'],
    ['factor:median_slope','Median slope','Ground','small','slope'],
    ['factor:rough_90','Roughness at 90 m','Ground','small','rock'],
    ['factor:permafrost_zone','Permafrost zone','Ground','small','snow'],
    ['snow','Snow-free odds in the selected time','Climate','medium','snow'],
    ['temperature','Air temperature in the selected time','Climate','medium','thermometer'],
    ['cloud','Cloud in the selected time','Climate','medium','cloud'],
    ['factor:clear_days_year','Clear-sky days in a year','Climate','small','sun'],
    ['factor:wind_year','Wind, yearly mean','Climate','small','wind'],
    ['factor:uv_index_year','UV index, yearly mean','Climate','small','sun'],
    ['factor:aod_year','Haze, yearly mean','Climate','small','cloud'],
    ['airfield','Distance to an airfield','Access','large','plane'],
    ['factor:road_km','Distance to a road','Access','small','road'],
    ['factor:help_within_reach','Help within reach','Access','small','people'],
    ['factor:land_class','Land status','Land and permits','medium','shield'],
    ['protected','Inside a protected area','Land and permits','small','shield'],
    ['factor:human_class','Human influence','People and hazards','medium','people'],
    ['factor:tremor_verdict','Small tremors','People and hazards','small','wave'],
    ['factor:volcanic_class','Volcanic influence','People and hazards','small','volcano'],
    ['factor:solar_class','Solar power','Power','small','solar'],
    ['factor:wind_class','Wind power','Power','small','turbine'],
    ['factor:geothermal_class','Geothermal power','Power','small','spring'],
    ['named:solar_panel_yield','Solar panel yield, yearly mean','Power','small','solar'],
    ['named:months_without_sun','Months without Sun','Power','small','sun'],
    ['named:wind_50m','Wind speed at 50 m, yearly mean','Power','small','wind'],
    ['named:wind_power','Wind power at 50 m','Power','small','turbine'],
    ['named:geothermal_plant_km','Distance to a geothermal power plant','Power','small','spring'],
    ['region','Region','Region','small','pin'],
    ['hemisphere','Hemisphere','Region','small','compass'],
    ['lat','Latitude','Region','small','compass'],
  ],
  mars: [
    ['mars:full','All factors together','Likeness to the site','large','compass'],
    ['mars:landscape','Landscape','Likeness to the site','large','rock'],
    ['mars:environment','Environment','Likeness to the site','large','thermometer'],
    ['slope_likeness','Terrain','Likeness to the site','medium','slope'],
    ['mars:dry','Dryness','Likeness to the site','medium','rock'],
    ['mars:cold','Cold','Likeness to the site','medium','snow'],
    ['bare','Bare ground','Likeness to the site','medium','rock'],
    ['mars:sun','Sun','Likeness to the site','medium','sun'],
    ['factor:rock_class','Rock type','Ground','medium','rock'],
    ['factor:volcanic','Volcanic rock','Ground','small','volcano'],
    ['factor:median_slope','Slope','Ground','small','slope'],
    ['temperature','Yearly mean air temperature','Climate','medium','thermometer'],
    ['mars:precip_mm_year','Rain and snow in a year','Climate','small','cloud'],
    ['mars:pressure_kpa','Surface pressure','Climate','small','cloud'],
    ['factor:uv_index_year','UV index','Climate','small','sun'],
    ['factor:clear_days_year','Clear-sky days','Climate','small','sun'],
    ['factor:aod_year','Haze','Climate','small','cloud'],
    ['factor:land_class','Land status','Land and permits','small','shield'],
    ['factor:human_class','Human influence','People and hazards','small','people'],
    ['region','Region','Region','small','pin'],
    ['month','Month','Time of year','small','calendar'],
    ['airfield','Distance to an airfield','Access','medium','plane'],
    ['factor:help_within_reach','Help within reach','Access','small','people'],
    ['factor:solar_class','Solar power','Power','small','solar'],
    ['factor:wind_class','Wind power','Power','small','turbine'],
    ['factor:geothermal_class','Geothermal power','Power','small','spring'],
    ['named:solar_panel_yield','Solar panel yield, yearly mean','Power','small','solar'],
    ['named:months_without_sun','Months without Sun','Power','small','sun'],
    ['named:wind_50m','Wind speed at 50 m, yearly mean','Power','small','wind'],
    ['named:wind_power','Wind power at 50 m','Power','small','turbine'],
    ['named:geothermal_plant_km','Distance to a geothermal power plant','Power','small','spring'],
    ['hemisphere','Hemisphere','Region','small','compass'],
  ],
};
// Named options: added by deploy/add_named_options.py.
// Each row: key, name, category, unit, digits, kind, field for a lunar region, field for a Mars site,
// how to read a list (count or first), the wanted direction, what it is not.
const NAMED_COUNT = v => Array.isArray(v) ? v.length : v, NAMED_FIRST = v => Array.isArray(v) ? (Number.isFinite(v[0]) ? v[0] : null) : v;
const NAMED_OPTIONS = [
  ['solar_panel_yield','Solar panel yield, yearly mean','Power','kWh per kW in a day',2,'model','power.solar.panel_kwh_per_kw_day_year','mars_power.solar.panel_kwh_per_kw_day_year',null,'more','An estimate for a fixed panel from satellite sunlight in a box of approximately 1 degree. It is not a measurement at the place.'],
  ['months_without_sun','Months without Sun','Power','months',0,'model','power.solar.months_without_sun','mars_power.solar.months_without_sun',NAMED_COUNT,'less','The number of months with no sunlight in the monthly figures of the same box. It counts months, not days.'],
  ['wind_50m','Wind speed at 50 m, yearly mean','Power','m/s',2,'model','power.wind.ws50m_ms_year','mars_power.wind.ws50m_ms_year',null,'more','A model figure for a grid point. It is not a measurement at the place.'],
  ['wind_power','Wind power at 50 m','Power','W per m²',0,'model','power.wind.power_w_m2','mars_power.wind.power_w_m2',null,'more','A model estimate for a grid point. It is not a measurement at the place.'],
  ['geothermal_plant_km','Distance to a geothermal power plant','Power','km',0,'measured','power.geothermal.plant.km','mars_power.geothermal.plant.km',null,'less','A straight-line distance to the nearest plant in a public list of power plants. A plant in the list does not show that ground heat is usable at the place.'],
  ['geothermal_mw_150','Geothermal power plants within 150 km','Power','MW',0,'measured','power.geothermal.plant_mw_within_150_km','mars_power.geothermal.plant_mw_within_150_km',null,'more','The sum of the plants in a public list of power plants. It does not show that ground heat is usable at the place.'],
  ['wind_class_1_7','Wind power class, 1 to 7','Power','',0,'model','power.wind.class_1_to_7','mars_power.wind.class_1_to_7',null,'more','A class from the model wind at a grid point. It is not a measurement at the place.'],
  ['low_sun_power','Power of low sunlight on a panel that faces the Sun','Power','W per m²',0,'rough estimate','power.low_sun.<region>.w_m2',null,NAMED_FIRST,'more','A textbook estimate for clear air with the Sun at the ceiling of the lunar region. Light from the sky is not in it.'],
  ['people_25km','People in listed settlements within 25 km','People and hazards','people',0,'measured','steady.human.population_within_25km','mars_steady_effects.human.population_within_25km',null,'less','From a list of settlements. A camp or a station that is not in the list is not counted.'],
  ['settlements_25km','Listed settlements within 25 km','People and hazards','',0,'measured','steady.human.settlements_within_25km','mars_steady_effects.human.settlements_within_25km',null,'less','From a list of settlements. A camp or a station that is not in the list is not counted.'],
  ['volcano_1990_km','Nearest volcano with an eruption since 1990: distance','People and hazards','km',0,'measured','steady.volcanic.nearest_erupted_since_1990.km','mars_steady_effects.volcanic.nearest_erupted_since_1990.km',null,null,'A straight-line distance from a public list of volcanoes. A distance does not show the effect at the place.'],
  ['not_earthquake_share','Share of small events that are not earthquakes','People and hazards','share',2,'measured','tremors.share_not_earthquake_100km','mars_tremors.share_not_earthquake_100km',null,null,'From the event types of the earthquake catalogue, within 100 km. The catalogue does not see each small event.'],
  ['settlement_1000_km','Nearest settlement of 1,000 people or more: distance','Access','km',0,'measured','steady.human.nearest_settlement_1000_or_more.km','mars_steady_effects.human.nearest_settlement_1000_or_more.km',null,'less','A straight-line distance. It tells nothing about roads, boats, permits or cost.'],
  ['glacier_ice_share','Glacier ice, share of the area','Ground','share',2,'','steady.small_tremors.glacier_ice_share','mars_steady_effects.small_tremors.glacier_ice_share',null,null,'The share of the area that the map shows as glacier ice. It is not a survey of the ice.'],
  ['clearness','Clearness of the sky, yearly mean','Climate','index 0 to 1',2,'model',null,'mars_environment.clearness_index_year',null,'more','The share of the sunlight above the air that reaches the ground, from satellite data in a coarse box.'],
];
const TILE_DESIGN = Object.fromEntries(MAIN_OPTIONS.moon.map(([id,,,size,icon])=>[id,[size,icon]]));
// Numeric directions are a design decision of the team.
const WANTED_DEFAULTS = { hours:'more',h30:'more',snow:'more',bare:'more',slope:'less',slope_likeness:'more',roughness:'less',cloud:'less',clear_days:'more',wind:'less',airfield:'less',road:'less',human_footprint:'less',small_tremors:'less',sunlight:'more',power:'more' };
const ICON_PATHS = {
 sun:'M2 17h20M6 14a6 6 0 0 1 12 0M12 2v3M3 7l2 2M19 9l2-2',calendar:'M4 5h16v16H4zM8 2v6M16 2v6M4 10h16M8 14h2M14 14h2M8 18h2',
 rover:'M4 14h15l2-6H7zM8 8V4h6M11 4V2M7 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4M18 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4',camera:'M3 7h5l2-3h4l2 3h5v14H3zM12 10a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
 boot:'M6 3h7v10l7 3v5H4v-7h2zM4 18h16',lamp:'M9 3h6l-1 9h-4zM9 12h6l3 8H6zM2 10l3 2M22 10l-3 2',slope:'M2 20h20L18 5zM7 17l3-1M12 13l3-1',rock:'M3 16 7 5l9-2 6 11-7 7H6zM7 5l5 8 10 1M12 13l3 8',
 snow:'M12 2v20M3 7l18 10M3 17 21 7M8 4l4 3 4-3M8 20l4-3 4 3',thermometer:'M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0M12 8v10M17 5h3M17 9h2',cloud:'M6 18a5 5 0 1 1 1-10 6 6 0 0 1 11 2 4 4 0 1 1 0 8z',
 wind:'M2 8h14a3 3 0 1 0-3-3M2 12h18a3 3 0 1 1-3 3M2 16h7',plane:'M3 13l8-3V3l2-1 2 1v7l7 3v2l-7-1v5l3 2H8l3-2v-5l-8 1z',road:'M8 2 3 22M16 2l5 20M12 3v3M12 10v3M12 17v4',
 shield:'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6zM8 12l3 3 5-6',people:'M9 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6M3 21v-6a6 6 0 0 1 12 0v6M17 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 5v2',
 wave:'M2 13h4l3-8 4 15 3-10 2 3h4',volcano:'M2 21 9 8h6l7 13zM8 13l4 2 4-2M10 5 8 2M14 5l2-3',solar:'M5 9h14l3 10H2zM12 9v13M4 14h16M9 22h6M12 2v4M4 4l2 2M20 4l-2 2',
 turbine:'M12 9v13M12 9 10 2h3zM12 9l8 2-2 3zM12 9l-7 7-2-3z',spring:'M2 20h20M5 16c-4-5 4-5 0-10M12 16c-4-5 4-5 0-10M19 16c-4-5 4-5 0-10',compass:'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20M8 16l2-6 6-2-2 6z',pin:'M12 22S4 13 4 9a8 8 0 1 1 16 0c0 4-8 13-8 13M12 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6'
};
const TYPES = {u8:['getUint8',1],u16:['getUint16',2],u32:['getUint32',4],i8:['getInt8',1],i16:['getInt16',2],f32:['getFloat32',4],uint8:['getUint8',1],uint16:['getUint16',2],int8:['getInt8',1],int16:['getInt16',2],float32:['getFloat32',4],uint32:['getUint32',4],int32:['getInt32',4],float64:['getFloat64',8]};
const finite = x => typeof x === 'number' && Number.isFinite(x);
const norm = x => String(x ?? '').toLowerCase().replace(/[−–](?=\d)/g,'-').replace(/[‐‑–—_]|-(?!\d)/g,' ').replace(/\s+/g,' ').trim();
const el = (tag, cls = '', text) => { const n = document.createElement(tag); n.className = cls; if (text != null) n.textContent = text; return n; };
const button = (text, fn, cls = '') => { const b=el('button',`ak-button ${cls}`,text); b.type='button'; b.addEventListener('click',fn); return b; };
const unique = a => [...new Set(a)];
const mean = a => a.length&&a.every(finite)?a.reduce((s,x)=>s+x,0)/a.length:null;
const pretty = x => String(x).replace(/[._@]/g,' ').replace(/\b\w/g, c=>c.toUpperCase());
const COMMON = {
  volcanic: ['volcanic ground','volcanic rock','lava'], basic_volcanic:['basalt'],
  human_class:['remote','nobody','undisturbed','quiet place','really quiet'], permafrost_zone:['frozen ground','permafrost'],
  airfield:['near an airfield','near an airport','reachable'], median_slope:['gentle slopes','gentle ground','flat ground'],
  tremor_verdict:['no small tremors','no tremors'], pop_100km:['no people'],
  topsoil_water:['dry'], temperature:['cold'], light:['long shadows','low sun','winter light'],
  rover:['rover'],camera:['camera'],crew:['crew','on foot'],lamp:['lamp','headlamp'],
};
// Topics that the Atlas has no data for. Each row: words (a plural "s" also matches), the sentence that the page shows,
// the nearest option or null. unsupportedPart reads the same words: no AI step sets an option from them.
const NO_DATA = [
  [['hotel','lodging','accommodation','hostel'],'The Atlas has no data on hotels.','named:settlement_1000_km'],
  [['flight price','ticket','cost','price','budget','cheap','expensive'],'The Atlas has no data on costs.',null],
  [['flight'],'The Atlas has no data on flights.','airfield'],
  [['wifi','wi fi','internet','phone signal','mobile network'],'The Atlas has no data on internet or phone networks.',null],
  [['restaurant','food','shop','supermarket'],'The Atlas has no data on food or shops.',null],
  [['hospital','doctor','medical'],'The Atlas has no data on hospitals.','factor:help_within_reach'],
  [['crime','war','safe country','security'],'The Atlas has no data on security.',null],
  [['drill','drilling'],'The Atlas has no data on where you can drill.',null],
  [['permit','permission'],'The Atlas has data on the land status, but not on permits.','factor:land_class'],
  [['seismometer'],'The Atlas has no data on seismometers.','factor:tremor_verdict'],
  [['colour','color'],'The Atlas has no data on colours.',null],
  [['favourite','favorite'],'The Atlas has no data on personal preferences.',null],
].map(([words,...rest])=>[new RegExp(`(?<![a-z0-9])(?:${words.join('|')})s?(?![a-z0-9])`),...rest]);
// Words that set the importance or only join words. A phrase of only these words gets no feedback line.
const FILLER_WORDS = /^(?:must|necessary|need|needs|important|prefer|preferably|ideally|if|possible|little|want|wants|we|our|us|you|me|very|please|also|should|can|that|this|there|are|from|by|as|but|so|some|any|have|has|no|not|without|than|least|most|more|less|within|under|over|below|above|around|about|close|nearby|approximately|max|maximum|min|minimum|something|anything|everything|thing|things|stuff|kind|sort|minus|plus|degree|degrees|percent|colder|warmer|hotter|cooler|higher|lower|bigger|smaller|good|best|nice|ideal|suitable|area|areas|site|sites|places|location|experiment|experiments)$/;

export async function mount(root, api) {
  const cleanups=[], aborters=new Set(), missing=[];
  let alive=true, generation=0, lastSaved='', current=null, rows=[], aiModels=[], aiOn=false;
  root.classList.add('ak-module');
  root.replaceChildren(el('p','ak-status','Read the data: please wait.'));
  const read=async(name,bin=false)=>{try{return await (bin?api.loadBin(name):api.loadJSON(name));}catch{missing.push(name);return null;}};
  const names=['factors.json','extra.json','tools.json','planner.json','rehearsal_rules.json','sites.json','mars.json','mars_extra.json','sources.json','meta.json','extras.json','yearplan.json','airfields.json','cells.json'];
  const loaded=await Promise.all(names.map(n=>read(n)));
  const [factors,extra,tools,planner,rules,sites,mars,mextra,sources,meta,extras,yearplan,airfields,cells]=loaded;
  if(!factors || !sites || !meta) {root.replaceChildren(el('p','ak-status','The search data is unavailable.'));return {destroy(){root.replaceChildren();}};}
  const areas=Array.from({length:api.areaCount},(_,i)=>api.area(i));
  let idHash=null;
  if(globalThis.crypto?.subtle){const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(areas.map(a=>a.id).join('\n')));idHash=Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');}
  const matches=(count,hash)=>count===api.areaCount&&(!hash||idHash===hash);
  async function viewFile(file,bytes,valid=true){if(!valid||!file){if(file)missing.push(`${file}: area order differs`);return null;}const b=await read(file,true);if(!b || (bytes!=null&&b.byteLength!==bytes)){if(b)missing.push(`${file}: size differs`);return null;}return new DataView(b);}
  const [fv,mfv,av,rv,mv,tv,sv,cv,yv]=await Promise.all([
    viewFile(factors.layout.file,factors.layout.bytes,matches(factors.layout.count)),
    viewFile(factors.mars_layout?.file,factors.mars_layout?.bytes,factors.mars_layout?.count===mars?.squares?.count),
    viewFile('access.bin',tools?.files?.['access.bin']?.bytes,matches(tools?.areas?.count,tools?.areas?.ids_sha256)),
    viewFile('rehearsal.bin',planner?.files?.['rehearsal.bin']?.bytes,matches(planner?.areas?.count,planner?.areas?.ids_sha256)),
    viewFile(mars?.squares?.file,mars?.squares?.bytes??mars?.squares?.byte_length),
    viewFile('temperature.bin',extras?.files?.['temperature.bin']?.bytes,matches(extras?.areas?.count,extras?.areas?.ids_sha256)),
    viewFile('snowodds.bin',api.areaCount*api.periods.length),
    viewFile('cloud.bin',api.areaCount*new Set(api.periods.map(p=>p.month)).size),
    viewFile(cells?.yearly?.file,cells?.yearly?.shape?.reduce((a,b)=>a*b,2),cells?.ids?.every((id,i)=>id===areas[i]?.id)&&cells?.n===api.areaCount),
  ]);
  const raw=(view,f,i,j=0)=>{const t=TYPES[f?.type];if(!view||!t)return null;const pos=f.offset+(i*(f.width||1)+j)*t[1];if(pos<0||pos+t[1]>view.byteLength)return null;const v=view[t[0]](pos,true);return !finite(v)||v===f.unknown?null:v;};
  const decode=(view,f,i,tables)=>{const v=raw(view,f,i);if(v==null)return null;if(f.beyond && v===f.beyond.stored)return null;const codes=f.codes||f.values||(Array.isArray(f.lookup)?f.lookup:null);if(codes)return codes[v]??null;if(f.ref){const x=tables?.[f.ref]?.[v];return x?.name??x??null;}if(f.mask)return f.mask.filter((_,j)=>v&(1<<j));return v/(f.scale||1);};
  const marsViews=new Map([[mars?.squares?.file,mv]]),marsLoads=new Map();
  const marsSiteFiles=id=>unique(Object.entries(mars?.squares?.columns||{}).filter(([name])=>name.startsWith(`sites.${id}.`)).map(([,field])=>field.file||mars.squares.file));
  const marsSiteReady=id=>marsSiteFiles(id).every(file=>marsViews.has(file));
  async function ensureMarsSite(id){
    for(const file of marsSiteFiles(id)){
      if(marsViews.has(file))continue;
      if(!marsLoads.has(file)){
        const entry=Object.values(mars.squares.site_files||{}).find(item=>item.file===file);
        marsLoads.set(file,viewFile(file,entry?.bytes).then(view=>{marsViews.set(file,view);return view;}));
      }
      await marsLoads.get(file);
      // A control can be open before its site's file arrives. Do not retain its unknown values.
      for(const [key] of columns)if(key.startsWith('mars:')&&key.includes(`:${id}`))columns.delete(key);
      for(const [key] of evaluations)if(key.startsWith('mars:')&&key.includes(`:${id}`))evaluations.delete(key);
    }
  }
  const mc=(id,i)=>{const field=mars?.squares?.columns?.[id];return decode(marsViews.get(field?.file||mars?.squares?.file),field,i);};
  const marsAreas=(mars?.squares?.ids||[]).map((id,i)=>({id,lat:mc('lat',i),lon:mc('lon',i),region:mars.squares.regions[mc('region',i)]??null,bare:mc('bare',i)}));
  const months=unique(api.periods.map(p=>p.month)).sort((a,b)=>a-b).map(m=>({value:m,label:new Intl.DateTimeFormat('en',{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2000,m-1)))}));
  const targetMap=new Map(api.targets.map(t=>[t.id,t.name]));
  const marsMap=new Map((mars?.sites||[]).map(t=>[t.id,t.name]));
  const definitions=[], byId=new Map();
  function add(d){d.comparisons=d.values?['is']:['at least','at most'];d.modes||=['moon','mars'];if(!d.read)d.read=()=>null;definitions.push(d);byId.set(d.id,d);return d;}
  function group(row){if(row==='land_status')return 'Land and permits';if(['cloud','uv','sunlight','clear_days','haze','snow'].includes(row))return 'Climate';const g=factors.matrix.find(r=>r.id===row)?.group;return row==='power'?'Power':/ground|below/.test(g)?'Ground':/climate/.test(g)?'Climate':/hazard|people/.test(g)?'People and hazards':/light/.test(g)?'Light':'Ground';}
  const omittedFields=[];
  const factorIds=unique([...factors.layout.fields,...(factors.mars_layout?.fields||[])].map(f=>f.id.split('@')[0]));
  const administrativeFields=new Set(['shadow_basis','rock_box']);
  function fieldFor(mode,id,target){return (mode==='mars'?factors.mars_layout?.fields:factors.layout.fields)?.find(f=>f.id===id||f.id===`${id}@${target}`);}
  function fieldLabel(f,row){
    if(f.label==='Distance to it'){
      const reference=factors.layout.fields.find(x=>x.id===f.id.replace(/_km$/,'_ref'));
      if(reference?.label)return `${reference.label}: distance`;
    }
    return /^(Distance to it|Largest of them|Nearest of them)$/.test(f.label)?`${row?.name||'Earthquakes'}: ${f.label.toLowerCase()}`:f.label;
  }
  for(const id of factorIds){
    const a=factors.layout.fields.find(f=>f.id.split('@')[0]===id), b=factors.mars_layout?.fields.find(f=>f.id.split('@')[0]===id), f=a||b, row=factors.matrix.find(r=>r.id===f.row);
    if(f.ref||!f.label||administrativeFields.has(id)){omittedFields.push(`factors:${id}`);continue;}
    const values=unique([...(a?.codes||a?.mask||[]),...(b?.codes||b?.mask||[])]);
    const d=add({id:`factor:${id}`,field:id,factor:f.row,modes:[...(a?['moon']:[]),...(b?['mars']:[])],targetSpecific:Boolean(f.target),monthly:/_(?:m)?(?:0[1-9]|1[0-2])$/.test(id),label:fieldLabel(f,row),group:/airfield|remoteness/.test(f.row)||/road/.test(id)?'Access':group(f.row),unit:values.length?'':f.unit,digits:f.digits??2,values:values.length?values:undefined,kind:f.kind,note:[row?.what_it_is,row?.what_it_is_not].filter(Boolean).join(' '),metadata:c=>fieldFor(c.mode,id,c.target),read:(i,c)=>decode(c.mode==='mars'?mfv:fv,fieldFor(c.mode,id,c.target),i,factors.tables)});
    if(f.beyond)d.note+=` ${f.beyond.words} is a bound, not an exact distance. The search treats that bound as unknown.`;
  }
  // These files repeat matrix factors and expose unlabeled implementation fields.
  // Keep only the matrix's named meanings; a file key is never a visitor's label.
  for(const [name,fields] of [['extra',extra?.fields],['mars-extra',mextra?.squares?.columns]])
    for(const path of Object.keys(fields||{}))omittedFields.push(`${name}:${path}`);
  // Named options: read the two files again and add each field of NAMED_OPTIONS that the data has.
  const [namedMoonView,namedMarsView]=await Promise.all([
    viewFile(extra?.binary,extra?.binary_bytes,matches(extra?.area_count,extra?.ids_sha256)),
    viewFile(mextra?.squares?.file,mextra?.squares?.byte_length,mextra?.squares?.count===mars?.squares?.count),
  ]);
  for(const [key,label,groupName,unit,digits,kind,moonPath,marsPath,pick,wanted,note] of NAMED_OPTIONS){
    const marsField=marsPath?mextra?.squares?.columns?.[marsPath]:null;
    const moonField=c=>moonPath?extra?.fields?.[moonPath.replace('<region>',c.target)]:null;
    const modes=[...(moonPath&&namedMoonView?['moon']:[]),...(marsField&&namedMarsView?['mars']:[])];
    if(!modes.length)continue;
    if(wanted)WANTED_DEFAULTS[`named:${key}`]=wanted;
    add({id:`named:${key}`,label,group:groupName,unit,digits,kind,modes,note,targetSpecific:Boolean(moonPath?.includes('<region>')),
      read:(i,c)=>{const v=c.mode==='mars'?decode(namedMarsView,marsField,i):decode(namedMoonView,moonField(c),i);return pick?pick(v):v;}});
  }
  add({id:'destination',label:'Destination',group:'Destination',values:[...targetMap.keys(),...marsMap.keys()],labels:Object.fromEntries([...targetMap,...marsMap]),read:(i,c)=>c.target});
  const regions=unique([...areas.map(a=>a.region),...marsAreas.map(a=>a.region)].filter(Boolean)).sort();
  add({id:'region',label:'Region',group:'Region',values:regions,read:(i,c)=>(c.mode==='moon'?areas:marsAreas)[i].region});
  add({id:'hemisphere',label:'Hemisphere',group:'Region',values:unique(areas.map(a=>a.hemisphere)),read:(i,c)=>c.mode==='moon'?areas[i].hemisphere:(marsAreas[i].lat<0?'S':'N')});
  for(const key of ['lat','lon'])add({id:key,label:key==='lat'?'Latitude':'Longitude',group:'Region',unit:'degrees',read:(i,c)=>(c.mode==='moon'?areas:marsAreas)[i][key]});
  add({id:'bare',label:'Bare ground',group:'Ground',unit:'share of land',read:(i,c)=>(c.mode==='moon'?areas:marsAreas)[i].bare});
  add({id:'hours',modes:['moon'],factor:'sun_low_hours',label:'Low-Sun hours in the selected time',group:'Light',unit:'hours',read:(i,c)=>c.mode==='moon'?timeHours(i,c):null});
  const blocks=planner?.files?.['rehearsal.bin']?.layout?.blocks||[];
  const hblock=blocks.find(b=>b.name==='h30'), vblock=blocks.find(b=>b.name==='verdicts');
  function rehearsal(i,target,activity){if(!rv||!vblock)return null;const t=planner.targets.indexOf(target),a=vblock.activities.indexOf(activity);if(t<0||a<0)return null;const v=rv.getUint8(vblock.offset_bytes+(i*planner.targets.length+t)*vblock.activities.length+a);return Object.entries(vblock.codes).find(([k,x])=>x===v&&k!=='cannot tell')?.[0]??null;}
  add({id:'h30',modes:['moon'],factor:'sun_low_hours',label:'Low-Sun hours in the best three ten-day periods in a row, across the year',group:'Light',unit:rules?.inputs?.find(x=>x.key==='H30')?.unit||'hours',note:hblock?.what,read:(i,c)=>{if(c.mode!=='moon'||!rv||!hblock)return null;const t=planner.targets.indexOf(c.target);if(t<0)return null;const v=rv.getUint16(hblock.offset_bytes+(i*planner.targets.length+t)*2,true);return v===hblock.unknown?null:v/10;}});
  for(const a of rules?.activities||[])add({id:`activity:${a.id}`,modes:['moon'],label:a.activity,group:'Activity',values:(rules.verdicts||[]).filter(x=>x.word!=='cannot tell').map(x=>x.word),kind:a.kind||rules.kind,note:`${rules.label}. ${a.pass_rule} ${a.near_rule}`,read:(i,c)=>c.mode==='moon'?rehearsal(i,c.target,a.id):null});
  const accessLayout=tools?.files?.['access.bin']?.layout;
  function access(i){if(!av||!accessLayout)return null;const base=i*accessLayout.columns.length;const col=areas[i].hemisphere==='S'?'any':'scheduled';const get=name=>{const v=av.getUint16((base+accessLayout.columns.indexOf(name))*2,true);return v===accessLayout.unknown?null:v;};return {km:get(`${col}_km`),name:airfields?.airfields?.[get(`${col}_index`)]?.name??null};}
  add({id:'airfield',label:'Distance to an airfield',group:'Access',unit:'km',digits:0,note:airfields?.what_it_is_not,read:(i,c)=>c.mode==='moon'?access(i)?.km??null:byId.get('factor:airfield_km')?.read(i,c)});
  const tempLayout=extras?.files?.['temperature.bin']?.layout;
  add({id:'temperature',label:'Mean air temperature in the selected time',group:'Climate',unit:'degrees C',digits:1,read:(i,c)=>{if(c.mode==='mars')return mc('t2m_year_c',i);if(!tv||!tempLayout)return null;const ms=selectedMonths(c,i);return mean(ms.map(m=>{const x=tv.getInt8(i*months.length+m-1);return x===tempLayout.unknown?null:x;}));}});
  add({id:'snow',modes:['moon'],label:'Mean snow-free odds in the selected time',group:'Climate',unit:'percent',read:(i,c)=>{if(c.mode!=='moon'||!sv)return null;return mean(selectedPeriods(c,i).map(p=>{const x=sv.getUint8(i*api.periods.length+p.index);return x===meta.encoding.unknown?null:x;}));}});
  add({id:'cloud',modes:['moon'],label:'Mean cloud in the selected time',group:'Climate',unit:'percent',read:(i,c)=>{if(c.mode!=='moon'||!cv)return null;return mean(selectedMonths(c,i).map(m=>{const x=cv.getUint8(i*months.length+m-1);return x===meta.encoding.unknown?null:x;}));}});
  add({id:'month',siteScore:'best_months_count',label:'Month',group:'Time of year',values:months.map(m=>m.value),labels:Object.fromEntries(months.map(m=>[m.value,m.label])),read:(i,c)=>c.mode==='moon'?unique(api.periods.filter(p=>periodValues(i,c.target)[p.index]>0).map(p=>p.month)):marsMonths(i,c.target)});
  const seasonNames=Object.keys(meta.seasons).filter(k=>k.endsWith('_bins_north')).map(k=>k.replace('_bins_north',''));
  add({id:'season',modes:['moon'],label:'Half-year with low Sun',group:'Time of year',values:seasonNames,labels:Object.fromEntries(seasonNames.map(s=>[s,`${pretty(s)} half-year (${meta.seasons[`${s}_text`]})`])),read:(i,c)=>c.mode==='moon'?seasonNames.filter(s=>meta.seasons[`${s}_bins_north`].some(p=>periodValues(i,c.target)[p]>0)):null});
  for(const [id,label,unit] of [['precip_mm_year','Rain and snow in a year','mm'],['pressure_kpa','Surface pressure','kPa']])if(mars?.squares?.columns?.[id])add({id:`mars:${id}`,modes:['mars'],label,group:'Climate',unit,digits:1,read:(i,c)=>c.mode==='mars'?mc(id,i):null});
  const terrainIndex=cells?.yearly?.fields?.indexOf('terrain')??-1;
  const noTerrainModel=ctx=>ctx.mode==='moon'&&meta.targets.find(t=>t.id===ctx.target)?.has_model===false;
  add({id:'slope_likeness',factor:'slope_likeness',label:'Slopes like the lunar region',group:'Ground',unit:factors.matrix.find(r=>r.id==='slope_likeness')?.unit||'',siteScore:'terrain',read:(i,c)=>{
    if(c.mode==='mars')return mc(`sites.${c.target}.terrain`,i);
    if(noTerrainModel(c)||!yv||terrainIndex<0)return null;
    const t=meta.targets.findIndex(t=>t.id===c.target),shape=cells.yearly.shape;if(t<0||t>=shape[1])return null;
    const value=yv.getUint16(((i*shape[1]+t)*shape[2]+terrainIndex)*2,true);
    return value===cells.yearly.unknown?null:value/cells.yearly.scale.terrain;
  }});
  const protectedField=byId.get('factor:land_protected');
  if(protectedField){protectedField.hidden=true;add({id:'protected',factor:'land_status',label:'Inside a protected area',group:'Land and permits',values:['no','yes'],modes:protectedField.modes,kind:protectedField.kind,note:'The maps describe the centre. This does not establish a permit for research.',metadata:protectedField.metadata,read:(i,c)=>{const value=protectedField.read(i,c);return typeof value!=='string'||/^(unknown|cannot tell)/i.test(value)?null:value==='none in the maps we checked'?'no':'yes';}});}
  for(const [key,label] of [['full','All factors together'],['landscape','Landscape'],['environment','Environment'],['dry','Dryness'],['cold','Cold'],['sun','Sun']])
    if(mars?.sites?.some(site=>mars.squares.columns?.[`sites.${site.id}.${key}`]))add({id:`mars:${key}`,modes:['mars'],siteScore:key,label,group:'Likeness to the site',unit:`score ${mars.meta.score_scale.join(' to ')}`,note:mars.meta.formulas[key],read:(i,c)=>c.mode==='mars'?mc(`sites.${c.target}.${key}`,i):null});
  const kindTag=kind=>/estimate/i.test(kind||'')?'rough estimate':/measur/i.test(kind||'')?'measured':/coarse/i.test(kind||'')?'coarse map':/model/i.test(kind||'')?'model':'';
  for(const d of definitions){
    d.factor ||= factors.matrix.some(r=>r.id===d.id)?d.id:d.id;
    const row=factors.matrix.find(r=>r.id===d.factor);
    d.main=false;d.kind=kindTag(d.kind||row?.kind);
    d.note ||= row?.what_it_is_not || (d.group==='Region'?'A location does not establish access or permission.':'These figures do not measure conditions for a particular visit.');
  }
  const mainOptions=Object.fromEntries(Object.entries(MAIN_OPTIONS).map(([mode,items])=>[mode,new Map(items.map(([id,label,group,size,icon],order)=>[id,{label,group,size,icon,order}]))]));
  function projectDefinition(d,ctx){
    if(!d)return null;const main=mainOptions[ctx.mode]?.get(d.id),field=d.metadata?.(ctx),rawValues=d.id==='protected'?d.values:d.id==='region'?unique((ctx.mode==='moon'?areas:marsAreas).map(a=>a.region).filter(Boolean)).sort():d.id==='hemisphere'?unique((ctx.mode==='moon'?areas:marsAreas).map(a=>a.hemisphere||(a.lat<0?'S':'N'))):field?.codes||field?.mask;
    const values=(rawValues||d.values)?.filter(v=>!/^(unknown(?:[: ]|$)|cannot tell$|mixed or cannot tell)/i.test(String(v)));
    const note=d.id==='slope_likeness'&&noTerrainModel(ctx)?'Unknown: NASA has no 5 m terrain model of this region.':d.note;
    return {...d,...main,main:Boolean(main),order:main?.order??Infinity,size:main?.size||'small',kind:kindTag(field?.kind||d.kind),values:values?.length?values:undefined,note};
  }
  const knownOptionValues=new Map();
  const knownValue=v=>v!=null&&!(typeof v==='number'&&!finite(v))&&!(typeof v==='string'&&/^(unknown(?:[: ]|$)|cannot tell$|mixed or cannot tell)/i.test(v))&&(!Array.isArray(v)||v.length>0);
  function definitionAvailable(d,ctx){
    if(!d||d.hidden||d.id==='destination'||!d.modes.includes(ctx.mode))return false;
    if(ctx.mode==='mars'&&d.id==='factor:airfield_km')return false; // The canonical airfield option reads this same column.
    if(d.id==='slope_likeness'&&noTerrainModel(ctx))return terrainIndex>=0;
    if(d.metadata&&!d.metadata(ctx))return false;
    if(ctx.mode==='mars'&&d.siteScore){
      if(!mars?.squares?.columns?.[`sites.${ctx.target}.${d.siteScore}`])return false;
      if(!marsSiteReady(ctx.target))return true;
    }
    const key=`${ctx.mode}:${ctx.target}:${d.id}`;
    if(!knownOptionValues.has(key))knownOptionValues.set(key,(ctx.mode==='moon'?areas:marsAreas).some((_,i)=>knownValue(d.read(i,{...ctx,months:[],seasons:[]}))));
    return knownOptionValues.get(key);
  }
  function availableDefinitions(ctx){return definitions.filter(d=>definitionAvailable(d,ctx)).map(d=>projectDefinition(d,ctx)).sort((a,b)=>GROUPS.indexOf(a.group)-GROUPS.indexOf(b.group)||a.order-b.order||a.label.localeCompare(b.label));}
  const definitionLabel=(d,ctx)=>projectDefinition(d,ctx)?.label||'';
  const definitionGroup=(d,ctx)=>projectDefinition(d,ctx)?.group||'';
  const criterionAliases={'mars:t2m_year_c':'temperature','mars:terrain':'slope_likeness','mars:bare':'bare','factor:land_protected':'protected'};
  for(const [prefix,paths] of [['extra',{ 'power.solar.class':'solar_class','power.wind.class':'wind_class','power.geothermal.class':'geothermal_class','power.wind.ws10m_ms_year':'wind_year','steady.human.class':'human_class','steady.volcanic.class':'volcanic_class','tremors.verdict':'tremor_verdict'}],['mars-extra',{'mars_power.solar.class':'solar_class','mars_power.wind.class':'wind_class','mars_power.geothermal.class':'geothermal_class','mars_power.wind.ws10m_ms_year':'wind_year','mars_power_extra.wind_10m_ms_year':'wind_year','mars_environment.uv_index_year':'uv_index_year','mars_environment.clear_days_year':'clear_days_year','mars_environment.aod_550_year':'aod_year','mars_steady_effects.human.class':'human_class','mars_steady_effects.volcanic.class':'volcanic_class','mars_tremors.verdict':'tremor_verdict'}]])
    for(const [path,id] of Object.entries(paths))criterionAliases[`${prefix}:${path}`]=`factor:${id}`;
  function canonicalCriterion(c,ctx,preserveImportance=false){
    if(!c||typeof c.id!=='string')return null;const id=ctx.mode==='mars'&&c.id==='factor:airfield_km'?'airfield':criterionAliases[c.id]||c.id.split('@')[0],d=byId.get(id);
    if(!d||id!=='destination'&&!definitionAvailable(d,ctx))return null;
    let value=c.value;
    if(c.id==='factor:land_protected')value=(Array.isArray(value)?value:[value]).filter(knownValue).map(v=>v==='none in the maps we checked'?'no':'yes');
    const projected=projectDefinition(d,ctx);
    if(projected.values){const values=Array.isArray(value)?value:[value],allowed=values.filter(v=>projected.values.includes(v));if(!allowed.length){if(!preserveImportance||!values.length||!values.every(v=>d.values?.includes(v)))return null;return normalizeCriterion({...c,id,value:Array.isArray(value)?[projected.values[0]]:projected.values[0],pageDefault:true,baseDefault:true});}value=Array.isArray(value)?unique(allowed):allowed[0];}
    const next={...c,id,value};delete next.baseDefault;return normalizeCriterion(next);
  }
  const periodCache=new Map();
  function periodValues(i,t){if(!periodCache.has(t))periodCache.set(t,new Array(api.areaCount));const cache=periodCache.get(t);return cache[i]||(cache[i]=api.periodHours(i,t,3));}
  const dateSelections=new WeakMap();
  function selectedPeriods(c,i){const south=areas[i]?.hemisphere==='S';let cache=dateSelections.get(c);if(!cache){cache={};dateSelections.set(c,cache);}if(cache[south])return cache[south];let ps=api.periods;if(c.months.length)ps=ps.filter(p=>c.months.includes(p.month));if(c.seasons.length)ps=ps.filter(p=>c.seasons.some(s=>meta.seasons[`${s}_bins_north`]?.includes(p.index)));if(south)ps=ps.filter(p=>meta.seasons.rock_season_bins_south.includes(p.index));cache[south]=ps;return ps;}
  function selectedMonths(c,i){return c.mode==='moon'?unique(selectedPeriods(c,i).map(p=>p.month)):c.months.length?c.months:months.map(m=>m.value);}
  function timeHours(i,c){if(!c.months.length&&!c.seasons.length)return api.hours(i,c.target,3,'year');const vs=selectedPeriods(c,i).map(p=>periodValues(i,c.target)[p.index]);return !vs.length?0:vs.some(x=>!finite(x))?null:vs.reduce((s,x)=>s+x,0);}
  function marsMonths(i,t){const count=mc(`sites.${t}.best_months_count`,i);return count==null?null:Array.from({length:count},(_,j)=>mc(`sites.${t}.best_month_${j}`,i)).filter(finite);}
  function context(criteria,override){const state=api.getState(),dest=criteria.find(c=>c.id==='destination')?.value;const target=override||(Array.isArray(dest)?dest[0]:dest)||(state.dest==='mars'?state.msite||mars.sites[0]?.id:state.target||api.targets[0].id);return {target,mode:marsMap.has(target)?'mars':'moon',months:criteria.filter(c=>c.id==='month'&&(c.importance==null?c.necessity==='necessary':c.importance>0)).flatMap(c=>c.value),seasons:criteria.filter(c=>c.id==='season'&&(c.importance==null?c.necessity==='necessary':c.importance>0)).flatMap(c=>c.value)};}
  const displayValue=(d,v)=>v==null?'unknown':Array.isArray(v)?v.length?v.map(x=>displayValue(d,x)).join(' or '):'none':d.labels?.[v]??(typeof v==='number'?`${api.fmtNumber(v,Number.isInteger(v)?0:d.digits??2)}${d.unit?` ${d.unit}`:''}`:String(v));
  const importance=c=>Number.isInteger(c.importance)?c.importance:c.necessity==='necessary'?10:5;
  const direction=d=>WANTED_DEFAULTS[d.id]||WANTED_DEFAULTS[d.factor]||(/wind|rough|slope|road|airfield|pop_|tremor.*count/.test(d.id)?'less':undefined);
  function normalizeCriterion(c){
    const d=byId.get(c.id);if(!d)return c;const weight=importance(c);
    let wanted=c.wanted||(d.values?'is':['at least','at most','near','more','less'].includes(c.comparison)?c.comparison:direction(d)||'near');
    if(weight===10&&!d.values&&!['at least','at most'].includes(wanted))wanted=wanted==='more'?'at least':wanted==='less'?'at most':c.comparison==='at most'?'at most':'at least';
    if(weight<10&&['at least','at most'].includes(wanted))wanted=wanted==='at least'?'more':'less';
    return {...c,importance:weight,wanted,comparison:d.values?'is':wanted,necessity:weight===10?'necessary':'preferred'};
  }
  function criterionText(raw,ctx=context(current?.criteria||[])){const c=normalizeCriterion(raw),d=projectDefinition(byId.get(c.id),ctx),wanted=c.wanted==='more'?'more is better':c.wanted==='less'?'less is better':c.wanted==='near'?`near ${displayValue(d,c.value)}`:`${c.wanted==='is'?'':`${c.wanted} `}${displayValue(d,c.value)}`;return `${d.label}: ${wanted}${c.pageDefault?' (the page set this value)':''}`;}
  function validCriterion(c){const d=byId.get(c?.id);if(!d)return false;const weight=importance(c);if(!Number.isInteger(weight)||weight<0||weight>10)return false;const wanted=c.wanted||c.comparison;if(!['is','at least','at most','more','less','near'].includes(wanted))return false;const vs=Array.isArray(c.value)?c.value:[c.value];if(c.id==='destination'&&vs.length!==1)return false;return d.values?vs.length>0&&vs.every(v=>d.values.includes(v)):!Array.isArray(c.value)&&(finite(c.value)||weight<10&&['near','more','less'].includes(wanted));}
  // Values and empirical ranks are shared by controls, the search and the destination table.
  const columns=new Map(),evaluations=new Map();
  const dynamicIds=new Set(['hours','h30','month','season','temperature','snow','cloud','slope_likeness']);
  function drain(iterator){let step;do{step=iterator.next();}while(!step.done);return step.value;}
  function column(d,ctx){return drain(columnParts(d,ctx));}
  function* columnParts(d,ctx){
    const dynamic=dynamicIds.has(d.id)||d.targetSpecific||d.id.startsWith('activity:')||d.id.startsWith('mars:');
    const time=['hours','temperature','snow','cloud'].includes(d.id)?`:${ctx.months}:${ctx.seasons}`:'';
    const key=`${ctx.mode}:${d.id}${dynamic?`:${ctx.target}`:''}${time}`;
    if(columns.has(key))return columns.get(key);
    const pool=ctx.mode==='moon'?areas:marsAreas;
    const values=new Array(pool.length),ordered=[];
    for(let i=0;i<pool.length;i++){
      if(i%64===0)yield;
      let v=d.read(i,ctx);v=v==null||typeof v==='number'&&!finite(v)||typeof v==='string'&&/^(unknown(?:[: ]|$)|cannot tell$|mixed or cannot tell)/i.test(v)?null:v;
      values[i]=v;if(!d.values&&finite(v))ordered.push({v,i});
    }
    // Merge in bounded pieces too: a large native sort would block the controls.
    let work=ordered,scratch=new Array(ordered.length),ticks=0;
    for(let width=1;width<work.length;width*=2){
      for(let start=0;start<work.length;start+=width*2){
        const middle=Math.min(start+width,work.length),end=Math.min(start+width*2,work.length);let left=start,right=middle;
        for(let k=start;k<end;k++){if(++ticks%128===0)yield;scratch[k]=right>=end||(left<middle&&work[left].v<=work[right].v)?work[left++]:work[right++];}
      }
      [work,scratch]=[scratch,work];
    }
    const sorted=new Array(work.length),ranks=new Float32Array(pool.length).fill(NaN);
    for(let k=0;k<work.length;){let end=k+1;while(end<work.length&&work[end].v===work[k].v){end++;if(++ticks%128===0)yield;}
      const rank=work.length>1?(k+end-1)/2/(work.length-1):0;
      for(let j=k;j<end;j++){if(++ticks%128===0)yield;sorted[j]=work[j].v;ranks[work[j].i]=rank;}k=end;
    }
    const rankLow=work.length?ranks[work[0].i]:0,rankHigh=work.length?ranks[work.at(-1).i]:1;
    for(let i=0;i<ranks.length;i++){if(i%128===0)yield;if(finite(ranks[i]))ranks[i]=rankHigh>rankLow?(ranks[i]-rankLow)/(rankHigh-rankLow):1;}
    const out={key,values,sorted,ranks,rankLow,rankHigh,knownCount:values.filter(v=>v!=null).length,min:sorted[0],max:sorted.at(-1)};columns.set(key,out);return out;
  }
  function targetRank(sorted,value){
    if(!sorted.length)return NaN;let lo=0,hi=sorted.length;while(lo<hi){const mid=(lo+hi)>>>1;if(sorted[mid]<value)lo=mid+1;else hi=mid;}const first=lo;hi=sorted.length;while(lo<hi){const mid=(lo+hi)>>>1;if(sorted[mid]<=value)lo=mid+1;else hi=mid;}
    if(first<lo)return sorted.length>1?(first+lo-1)/2/(sorted.length-1):0;
    return Math.max(0,Math.min(1,(first-0.5)/Math.max(1,sorted.length-1)));
  }
  function evaluate(c,ctx){return drain(evaluationParts(c,ctx));}
  function* evaluationParts(raw,ctx){
    const c=normalizeCriterion(raw),d=byId.get(c.id),col=yield* columnParts(d,ctx),key=`${col.key}:${c.importance}:${c.wanted}:${JSON.stringify(c.value)}`;
    if(evaluations.has(key))return evaluations.get(key);
    const want=Array.isArray(c.value)?c.value:[c.value],rawRank=d.values?null:targetRank(col.sorted,c.value);
    const wantedRank=col.rankHigh>col.rankLow?Math.max(0,Math.min(1,(rawRank-col.rankLow)/(col.rankHigh-col.rankLow))):c.value===col.min?1:0;
    const yes=new Int8Array(col.values.length),near=new Float32Array(col.values.length);let count=0,unknown=0,timeIndices;
    if(ctx.mode==='moon'&&['month','season'].includes(c.id))timeIndices=api.periods.filter(p=>c.id==='month'?want.includes(p.month):want.some(s=>meta.seasons[`${s}_bins_north`]?.includes(p.index))).map(p=>p.index);
    for(let i=0;i<yes.length;i++){
      if(i%64===0)yield;const v=col.values[i];let pass=null,score=0;
      if(v!=null){if(d.values){pass=(Array.isArray(v)?v:[v]).some(x=>want.includes(x));score=pass?1:0;}
        else if(c.importance===10){pass=c.wanted==='at least'?v>=c.value:v<=c.value;score=pass?1:0;}
        else if(c.wanted==='more'||c.wanted==='less'){score=c.wanted==='more'?col.ranks[i]:1-col.ranks[i];if(col.min===col.max)score=1;pass=score>=1-1e-7;}
        else if(finite(c.value)){score=v===c.value?1:Math.max(0,1-Math.abs(col.ranks[i]-wantedRank));pass=v===c.value;}
      }
      if(timeIndices){const pv=periodValues(i,ctx.target);pass=timeIndices.some(p=>finite(pv[p])&&pv[p]>0)?true:timeIndices.some(p=>!finite(pv[p]))?null:false;score=pass?1:0;}
      yes[i]=pass==null?-1:pass?1:0;near[i]=score;
      if(pass==null)unknown++;else if(pass||['more','less'].includes(c.wanted))count++;
    }
    const out={yes,near,col,count,unknown};evaluations.set(key,out);return out;
  }
  function check(i,c,ctx){const e=evaluate(c,ctx);return {yes:e.yes[i]<0?null:Boolean(e.yes[i]),value:e.yes[i]<0?null:e.col.values[i],near:e.near[i]};}
  function interpret(request){
    const text=norm(request), spans=[], criteria=[], notes=[], wordUses=[], noteUses=[];
    const base=context([]),mode=base.mode;
    const find=phrase=>{const p=norm(phrase);if(!p)return [];const escaped=p.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return [...text.matchAll(new RegExp(`(?<![a-z0-9])${escaped}(?![a-z0-9])`,'g'))];};
    const use=m=>spans.push([m.index,m.index+m[0].length]);
    const addC=(id,value,comparison='is',necessity='necessary',matches=[],note)=>{const d=byId.get(id);if(id!=='destination'&&!definitionAvailable(d,context(criteria)))return;const projected=projectDefinition(d,context(criteria));if(projected?.values){const values=(Array.isArray(value)?value:[value]).filter(v=>projected.values.includes(v));if(!values.length)return;value=Array.isArray(value)?values:values[0];}const c={id,comparison,value,necessity};if(note&&/limit comes|Gentle slopes|lowest quarter|Long shadows|page set this value/.test(note))c.pageDefault=true;if(validCriterion(c)){criteria.push(c);matches.forEach(use);if(matches.length)wordUses.push({id,words:unique(matches.map(m=>m[0]))});if(note){notes.push(note);noteUses.push({id,text:note});}}};
    const wordMatches=words=>words.flatMap(find);
    let target=null;
    for(const t of mode==='moon'?api.targets:[]){const ms=wordMatches([t.name,t.id]);if(ms.length){target=t.id;ms.forEach(use);}}
    for(const t of mode==='mars'?mars?.sites||[]:[]){const ms=wordMatches([t.name,t.id,t.name.split(',')[0],t.id.replaceAll('-',' ')]);if(ms.length){target=t.id;ms.forEach(use);}}
    const marsWord=find('Mars');
    if(marsWord.length&&mode==='mars')marsWord.forEach(use);
    target ||= base.target;
    if(target)addC('destination',target);
    const candidates=availableDefinitions(context(criteria));
    const modeRegions=unique((mode==='moon'?areas:marsAreas).map(a=>a.region));
    const regionMatches=modeRegions.filter(r=>mode!=='moon'||norm(r)!=='antarctica').map(r=>[r,find(r)]).filter(x=>x[1].length);
    if(regionMatches.length)addC('region',regionMatches.map(x=>x[0]),'is','necessary',regionMatches.flatMap(x=>x[1]));
    const antarctic=find('Antarctica');
    if(antarctic.length&&mode==='moon')addC('hemisphere',areas.find(a=>a.hemisphere==='S')?.hemisphere,'is','necessary',antarctic);
    const ms=months.map(m=>[m,wordMatches([m.label,m.label.slice(0,3)])]).filter(x=>x[1].length);
    if(ms.length)addC('month',ms.map(x=>x[0].value),'is','necessary',ms.flatMap(x=>x[1]));
    for(const s of seasonNames){const matches=find(s);if(matches.length&&mode==='moon')addC('season',s,'is','necessary',matches,`${pretty(s)} means the stored half-year: ${meta.seasons[`${s}_text`]}.`);}
    for(const a of rules?.activities||[]){const matches=wordMatches([a.activity,...(COMMON[a.id]||[])]);if(matches.length&&mode==='moon')addC(`activity:${a.id}`,rules.verdicts.find(v=>v.word==='pass')?.word,'is','preferred',matches,'Activity verdicts are preferences from our own rule, not a standard of an agency. They use the best periods in the year.');}
    const synonyms=[['volcanic','factor:volcanic',v=>v==='yes'],['basic_volcanic','factor:basic_volcanic',v=>v==='yes'],['human_class','factor:human_class',v=>/undisturbed/.test(v)],['permafrost_zone','factor:permafrost_zone',v=>v==='continuous'],['tremor_verdict','factor:tremor_verdict',v=>v==='none recorded'],['topsoil_water','factor:topsoil_water',v=>v==='dry']];
    for(const [key,id,pick] of synonyms){if(key==='topsoil_water'&&mode==='mars')continue;const matches=wordMatches(COMMON[key]);const value=byId.get(id)?.values?.find(pick);if(matches.length&&value!=null)addC(id,value,'is','necessary',matches);}
    const noPeople=wordMatches(COMMON.pop_100km);if(noPeople.length)addC('factor:pop_100km',0,'at most','necessary',noPeople,'The people count covers listed settlements. It does not prove that no person is there.');
    if(wordMatches(COMMON.tremor_verdict).length)notes.push('No small tremors means none recorded. It does not prove that the ground is still.');
    const near=wordMatches(COMMON.airfield);
    const reach=rules?.activities?.find(a=>a.id==='crew')?.pass?.find(p=>p.input==='D')?.value??yearplan?.reach_km;
    if(near.length&&finite(reach))addC('airfield',reach,'at most','necessary',near,'The airfield distance limit comes from the crew rule. It is a straight-line distance.');
    const gentle=wordMatches(COMMON.median_slope), slopeLimit=rules?.activities?.find(a=>a.id==='rover')?.pass?.find(p=>p.input==='P90')?.value;
    if(gentle.length&&finite(slopeLimit))addC('factor:p90_slope',slopeLimit,'at most','necessary',gentle,'Gentle slopes use the limit in the rover rule.');
    const cold=wordMatches(COMMON.temperature);
    if(cold.length){const id='temperature';const ctx=context(criteria),d=byId.get(id),vals=(mode==='mars'?marsAreas:areas).map((_,i)=>d.read(i,ctx)).filter(finite).sort((a,b)=>a-b);if(vals.length)addC(id,vals[Math.floor((vals.length-1)/4)],'at most','preferred',cold,'Cold means the lowest quarter of the known temperatures. You can change this preference.');}
    if(mode==='mars'&&find('dry').length){const id='mars:precip_mm_year';addC(id,mars.meta.dry_reference_mm,'at most','preferred',find('dry'),'Dry uses the reference precipitation in the Mars data.');}
    const publicLand=find('public land');
    if(publicLand.length){const d=byId.get('factor:land_class');const values=d?.values?.filter(v=>/^public land/.test(v));if(values?.length)addC(d.id,values,'is','necessary',publicLand);}
    if(/(?:no|not need|without|do not need) (?:a )?permit/.test(text))notes.push('Public land does not mean permission for research. The data cannot confirm that a permit is unnecessary.');
    for(const [phrase,id,comparison] of [['sunny','factor:sun_kwh_year','at least'],['not too windy','factor:wind_year','at most']]){
      const hits=find(phrase),d=byId.get(id);if(!hits.length||!d)continue;const vals=column(d,context(criteria)).sorted;
      if(vals.length)addC(id,vals[Math.floor((vals.length-1)*(comparison==='at least'?3/4:1/4))],comparison,'preferred',hits,'The page set this value from a quarter of the known figures.');
    }
    if(!criteria.some(c=>c.id==='factor:wind_year')){const hits=wordMatches(['wind','windy']);if(hits.length&&byId.has('factor:wind_year')){const d=byId.get('factor:wind_year'),col=column(d,context(criteria));if(col.sorted.length)addC(d.id,col.sorted[Math.floor((col.sorted.length-1)/2)],'at most','preferred',hits,'The page set this value from the middle of the known figures.');}}
    if(/seismometer/.test(text))notes.push('The activity data has no seismometer verdict. Recorded tremors and people are separate criteria.');
    // Numbers attach to the closest named field in the same clause. No numeric default is invented.
    const numericAliases={airfield:['airfield','airport'],hours:['low sun','hours','light'],h30:['best 30 days','best three ten day periods'],temperature:['temperature','cold'],snow:['snow-free odds','snow free odds'], 'factor:p90_slope':['slope','slopes'], 'factor:wind_year':['wind'], 'factor:rough_90':['roughness']};
    const numberRE=/(?:(at least|at most|below|under|above|over|less than|more than|no more than)\s+)?(-?\d+(?:\.\d+)?)\s*(km|kilometres?|hours?|h\b|degrees?(?:\s*c)?|°c?|percent|%|m\/s|mm|m\b)?/g;
    for(const match of text.matchAll(numberRE)){
      if(/\s*(?:a|per|each)\s+day\b/.test(text.slice(match.index+match[0].length,match.index+match[0].length+15))) {notes.push('The data has ten-day totals. Thus, the page cannot check the hours on each day.');continue;}
      if(spans.some(([s,e])=>match.index>=s&&match.index<e))continue;
      const start=Math.max(text.lastIndexOf(',',match.index),text.lastIndexOf(';',match.index))+1,endCandidates=[text.indexOf(',',match.index),text.indexOf(';',match.index)].filter(x=>x>=0),end=endCandidates.length?Math.min(...endCandidates):text.length;
      const clause=text.slice(start,end);let choices=[];
      for(const d of candidates.filter(d=>!d.values)){
        const aliases=[d.label,d.field?.replaceAll('_',' '),...(numericAliases[d.id]||[])].filter(Boolean);
        for(const alias of aliases){for(const hit of find(alias)){if(hit.index>=start&&hit.index<end)choices.push({d,hit,distance:Math.abs(hit.index-match.index)});}}
      }
      const unit=match[3]||'';
      if(/hours?|^h$/.test(unit)&&!/best/.test(clause))choices=choices.filter(x=>x.d.id==='hours');
      if(/km|kilometre/.test(unit))choices=choices.filter(x=>x.d.unit==='km');
      if(/degree|°/.test(unit))choices=choices.filter(x=>/degree/.test(x.d.unit));
      choices.sort((a,b)=>a.distance-b.distance);let choice=choices[0];if(!choice&&mode==='moon'&&/hours?|^h$/.test(unit)&&candidates.some(d=>d.id==='hours'))choice={d:byId.get('hours'),hit:match};
      if(!choice)continue;
      const comparison=/\bnear(?: a)?(?: value)?\s+-?\d/.test(clause)?'near':/at most|below|under|less|no more/.test(match[1]||'')?'at most':/at least|above|over|more/.test(match[1]||'')?'at least':choice.d.group==='Access'||/slope|temperature/.test(choice.d.id)?'at most':'at least';
      const old=criteria.findIndex(c=>c.id===choice.d.id);if(old>=0)criteria.splice(old,1);
      addC(choice.d.id,Number(match[2]),comparison,'necessary',[match,choice.hit]);
    }
    if(mode==='moon'&&wordMatches(COMMON.light).length&&!criteria.some(c=>['hours','h30'].includes(c.id))&&!/\d+\s*(?:hours?|h)\s*(?:a|per|each)\s+day/.test(text)){
      const threshold=rules?.activities?.find(a=>a.id==='rover')?.pass?.find(p=>p.input==='H30')?.value;
      if(finite(threshold))addC('h30',threshold,'at least','preferred',wordMatches(COMMON.light),'Long shadows use the rover rule for low-Sun hours.');
    }
    // A named numeric option can use its documented rule or the data's middle value.
    for(const d of candidates.filter(d=>d.main&&!d.values)){
      if(['hours','h30'].includes(d.id)&&/\d+(?:\.\d+)?\s*(?:hours?|h)\s*(?:a|per|each)\s+day/.test(text))continue;
      if(criteria.some(c=>c.id===d.id||(d.factor&&byId.get(c.id)?.factor===d.factor)))continue;
      const hits=wordMatches(unique([d.label,shortLabel(d),d.field?.replaceAll('_',' '),...(numericAliases[d.id]||[])].filter(Boolean))).filter(hit=>!spans.some(([start,end])=>hit.index<end&&hit.index+hit[0].length>start)
        &&!(d.id==='mars:sun'&&wordMatches(COMMON.light).some(light=>hit.index<light.index+light[0].length&&hit.index+hit[0].length>light.index)));
      if(!hits.length)continue;const limit=dataLimit(d,context(criteria));if(finite(limit.value))addC(d.id,limit.value,limit.wanted,'preferred',hits,'The page set this value from its rule or from the middle of the known figures.');
    }
    // Data labels and class words extend the interpreter when new fields arrive.
    for(const d of candidates){if(criteria.some(c=>c.id===d.id)||!d.values||['region','destination','month','season','hemisphere'].includes(d.id)||d.id.startsWith('activity:'))continue;
      const labels=wordMatches([d.label,d.field?.replaceAll('_',' ')].filter(Boolean));if(!labels.length)continue;
      const hits=d.values.filter(v=>typeof v==='string').map(v=>[v,find(v)]).filter(x=>x[1].length);
      if(hits.length)addC(d.id,hits.map(x=>x[0]),'is','necessary',[...labels,...hits.flatMap(x=>x[1])]);
    }
    // Retain every unmatched word, including linking words, so omissions are visible.
    const unused=[];let pending='';for(const token of text.matchAll(/\S+/g)){const used=spans.some(([s,e])=>token.index<e&&token.index+token[0].length>s);if(used){if(pending)unused.push(pending.trim());pending='';}else pending+=`${token[0]} `;}if(pending)unused.push(pending.trim());
    return {version:1,request,criteria,unused,notes:unique(notes),wordUses,noteUses,interpreter:'The page interpreter'};
  }
  const radiusText=mars?.meta?.fields?.bare_km2||'';
  const earthRadius=Number(radiusText.match(/radius\s+([\d,.]+)\s*km/)?.[1]?.replaceAll(',',''));
  // The spherical radius is stored in the Mars area definition; no geographic constant is duplicated here.
  function distance(a,b){if(!earthRadius||![a.lat,a.lon,b.lat,b.lon].every(finite))return null;const r=Math.PI/180,dlat=(b.lat-a.lat)*r,dlon=(b.lon-a.lon)*r;const h=Math.sin(dlat/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin(dlon/2)**2;return 2*earthRadius*Math.asin(Math.sqrt(Math.min(1,h)));}
  function nameOf(i,mode='moon'){const a=(mode==='moon'?areas:marsAreas)[i];return a.named||a.region||(mode==='moon'?'Area':'Square');}
  function search(criteria,override,compact=false){
    const ctx=context(criteria,override),pool=ctx.mode==='moon'?areas:marsAreas,active=criteria.filter(c=>c.id!=='destination'&&importance(c)>0).map(normalizeCriterion);
    const prepared=active.map(c=>({c,e:evaluate(c,ctx),weight:importance(c)})),necessary=prepared.filter(x=>importance(x.c)===10);
    const weight=prepared.reduce((n,x)=>n+x.weight,0),hours=column(byId.get('hours'),ctx).values;
    let unknown=0,passed=0,best=null;const all=[];
    for(let i=0;i<pool.length;i++){
      let pass=true,hasUnknown=false;for(const {e} of necessary){if(e.yes[i]!==1)pass=false;if(e.yes[i]<0)hasUnknown=true;}
      if(hasUnknown)unknown++;if(!pass)continue;passed++;
      let sum=0,knownWeight=0;for(const x of prepared)if(x.e.yes[i]>=0){sum+=x.e.near[i]*x.weight;knownWeight+=x.weight;}
      const share=knownWeight?sum/knownWeight:null,score=ctx.mode==='mars'?mc(`sites.${ctx.target}.full`,i):hours[i];
      if(share!=null&&(best==null||share>best))best=share;
      if(!compact)all.push({i,hours:hours[i],score,share});
    }
    all.sort((a,b)=>(b.share??-1)-(a.share??-1)||(b.score??-Infinity)-(a.score??-Infinity)||a.i-b.i);
    const selected=[];for(const r of all){if(selected.every(s=>{const km=distance(pool[r.i],pool[s.i]);return km==null||km>=sites.same_site_km;})){selected.push(r);if(selected.length===10)break;}}
    const worst=necessary.map(x=>[x.c,pool.length-x.e.count]).sort((a,b)=>b[1]-a[1])[0];
    return {ctx,rows:selected,all,unknown,passed,total:pool.length,best,worst,active};
  }
  function bestPeriods(i,c){if(c.mode==='mars'){const ms=marsMonths(i,c.target);return ms==null?'Best months: unknown':ms.length?`Best months: ${ms.map(m=>months.find(x=>x.value===m)?.label??'unknown').join(', ')}`:'The data has no best month';}
    const ps=selectedPeriods(c,i).map(p=>({...p,h:periodValues(i,c.target)[p.index]})).filter(p=>finite(p.h)&&p.h>0).sort((a,b)=>b.h-a.h).slice(0,3);
    if(!selectedPeriods(c,i).some(p=>finite(periodValues(i,c.target)[p.index])))return 'Best ten-day periods: unknown';
    return ps.length?`Best ten-day periods: ${ps.map(p=>`${p.label}: ${api.fmtHours(p.h)}`).join('; ')}`:'Best ten-day periods: none with known hours above zero';
  }
  function openResult(i,c){if(c.mode==='moon')api.openPlace(areas[i].id);else api.setState({dest:'mars',msite:c.target,msquare:marsAreas[i].id,go:'mars-square'});}
  const head=el('header','ak-head');
  const form=el('form','ak-form'),label=el('label','','Tell the AI what your experiment needs. It sets the options above.'),textarea=el('textarea','ak-request');textarea.id='ak-request';textarea.rows=2;textarea.placeholder='Tell the AI what your experiment needs. It sets the options above.';label.htmlFor=textarea.id;
  const findButton=el('button','ak-button ak-primary','Send');findButton.type='submit';form.append(label,textarea,findButton);
  const examples=el('div','ak-examples');const exampleTexts=['A rover camera test in long shadows in August, near an airfield, on volcanic ground',`Crew work on foot in winter light like ${api.targets.find(t=>t.id===api.getState().target)?.name||api.targets[0].name}, in Iceland or Svalbard`,'A quiet place with no people and no small tremors for a seismometer test, low Sun for 6 hours a day'];
  for(const text of exampleTexts)examples.append(button(text,()=>{textarea.value=text;textarea.focus();},'ak-example'));
  // Replace the old block from `const aiBox` through `aiInterpret` with this block.
  // The page's rules own values, directions and importance. Models supply option IDs only.
  const aiBox=el('div','ak-ai'),aiNote=el('p','ak-note',(ETF_LOCAL?'The AI models run on your computer. They only change your words into options. The places and all figures come from the data.':'The AI models run on the server of this page. Your words go to that server and to no other service. The models only change your words into options. The places and all figures come from the data.'));
  const aiWrap=el('label','ak-ai-switch'),aiToggle=el('input'),aiState=el('p','ak-note'),aiReadyLine=el('p','ak-note ak-ai-ready');
  aiToggle.type='checkbox';aiWrap.append(aiToggle,document.createTextNode((ETF_LOCAL?' Use an AI model on this computer':' Use an AI model')));
  const chatLabel=el('label','ak-ai-model','Chat model'),chatSelect=el('select');chatSelect.setAttribute('aria-label','Chat model');chatSelect.disabled=true;chatLabel.append(chatSelect);
  const aiCancel=button('Stop',()=>cancelAIInterpretation());aiCancel.hidden=true;
  aiReadyLine.setAttribute('role','status');aiState.setAttribute('role','status');
  aiBox.append(aiWrap,chatLabel,aiReadyLine,aiState,aiCancel,aiNote);
  const VECTOR_LIMIT=0.58,VECTOR_MARGIN=0.04;
  let embeddingModel=null,chatModel=null,modelReady=null,modelDiscovery=null,labelReady=null,aiCancelled=false,modelEpoch=0,activeInterpretation=null;
  const vectorCache=new Map();
  const elapsed=start=>`${((performance.now()-start)/1000).toFixed(3)} s`;
  function cancelAIInterpretation(announce=true){
    aiCancelled=true;
    if(activeInterpretation){activeInterpretation.cancelled=true;for(const controller of activeInterpretation.controllers)controller.abort();}
    aiCancel.hidden=true;
    if(announce&&alive)aiState.textContent='Stopped. The options already set stay on the board.';
  }
  async function localRequest(path,body,timeout=20000,scope=null){
    if(!aiOn||!alive||scope?.cancelled)throw new DOMException((ETF_LOCAL?'The local models are off.':'The AI models are off.'),'AbortError');
    const controller=new AbortController();aborters.add(controller);scope?.controllers.add(controller);const timer=setTimeout(()=>controller.abort(),timeout);
    try{const response=await fetch(`${ETF_LOCAL?'http://localhost:11434':'/ollama'}${path}`,{method:body?'POST':'GET',redirect:'error',signal:controller.signal,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});if(!response.ok)throw new Error((ETF_LOCAL?'The local model server refused this request.':'The model server refused this request.'));return await response.json();}
    finally{clearTimeout(timer);aborters.delete(controller);scope?.controllers.delete(controller);}
  }
  function unitVector(vector){if(!Array.isArray(vector)||!vector.length||!vector.every(finite))throw new Error('Invalid vector');const length=Math.hypot(...vector);if(!length)throw new Error('Empty vector');return Float32Array.from(vector,x=>x/length);}
  const cosine=(a,b)=>{if(a.length!==b.length)return -1;let sum=0;for(let i=0;i<a.length;i++)sum+=a[i]*b[i];return sum;};
  function factorKey(d){return d.id;}
  function commonWords(d){const key=d.field||d.id.replace(/^activity:/,'');return unique([...(COMMON[key]||[]),...(COMMON[d.id]||[]),...(d.id==='hours'||d.id==='h30'?COMMON.light||[]:[])]);}
  function vectorCatalog(ctx){
    const definitions=availableDefinitions(ctx),labels=definitions.map(d=>`${d.group}: ${d.label}${commonWords(d).length?` (${commonWords(d).join(', ')})`:''}`);
    return {definitions,labels,key:`${ctx.mode}\n${labels.join('\n')}`};
  }
  async function storedVectors(key,value){
    if(!globalThis.indexedDB)return null;
    return new Promise(resolve=>{
      const request=indexedDB.open('earth-twin-criteria',1);let done=false;
      const finish=value=>{if(!done){done=true;resolve(value);}};
      request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains('vectors'))request.result.createObjectStore('vectors');};
      request.onerror=()=>finish(null);request.onblocked=()=>finish(null);
      request.onsuccess=()=>{const db=request.result;try{const transaction=db.transaction('vectors',value?'readwrite':'readonly'),store=transaction.objectStore('vectors'),operation=value?store.put(value,key):store.get(key);operation.onsuccess=()=>finish(value||operation.result||null);operation.onerror=()=>finish(null);transaction.oncomplete=()=>db.close();transaction.onabort=()=>{db.close();finish(null);};}catch{db.close();finish(null);}};
    });
  }
  async function embedTexts(texts,model=embeddingModel,scope=null){
    const key=text=>`${model}\n${text}`,vectors=new Map(),pending=unique(texts).filter(text=>!vectorCache.has(key(text)));
    if(pending.length){const answer=await localRequest('/api/embed',{model,input:pending,keep_alive:'30m'},20000,scope);if(answer.embeddings?.length!==pending.length)throw new Error('The embedding model returned a different number of vectors.');answer.embeddings.forEach((v,i)=>vectorCache.set(key(pending[i]),unitVector(v)));}
    for(const text of texts)vectors.set(text,vectorCache.get(key(text)));return vectors;
  }
  async function loadLabels(model=embeddingModel,ctx=context(current?.criteria||[])){
    const catalog=vectorCatalog(ctx),vectorLabels=catalog.labels,key=`${model}\n${catalog.key}`,cached=await storedVectors(key);
    if(Array.isArray(cached)&&cached.length===vectorLabels.length&&cached.every(v=>Array.isArray(v)&&v.length&&v.every(finite)))return {...catalog,vectors:cached.map(unitVector)};
    const vectors=[];
    for(let i=0;i<vectorLabels.length;i+=48){const answer=await localRequest('/api/embed',{model,input:vectorLabels.slice(i,i+48),keep_alive:'30m'});if(answer.embeddings?.length!==Math.min(48,vectorLabels.length-i))throw new Error('Invalid label vectors');vectors.push(...answer.embeddings.map(unitVector));}
    await storedVectors(key,vectors.map(v=>Array.from(v)));return {...catalog,vectors};
  }
  function prepareModels(refresh=true){
    const epoch=++modelEpoch,start=performance.now();aiReadyLine.textContent='Load the AI models.';
    modelDiscovery=(async()=>{
      if(refresh){
        const result=await localRequest('/api/tags',undefined,2000),models=(result.models||[]).filter(m=>typeof m.name==='string');
        if(!alive||!aiOn||epoch!==modelEpoch)return false;
        // Preserve server order. The first chat model is the initial choice.
        aiModels=models.map(m=>m.name);const nextEmbedding=aiModels.find(name=>/embed/i.test(name))||null;
        if(nextEmbedding!==embeddingModel){vectorCache.clear();labelReady=null;}embeddingModel=nextEmbedding;
        const chats=aiModels.filter(name=>!/embed/i.test(name));if(!chats.includes(chatModel))chatModel=chats[0]||null;
        chatSelect.replaceChildren();for(const name of chats){const option=el('option','',name);option.value=name;chatSelect.append(option);}chatSelect.value=chatModel||'';chatSelect.disabled=!chats.length;
      }
      return alive&&aiOn&&epoch===modelEpoch;
    })();
    modelReady=(async()=>{
      try{
        if(!await modelDiscovery)return;
        const embed=embeddingModel,chat=chatModel;
        // These two short requests start together, even when label vectors are cached.
        const embeddingWarm=embed?localRequest('/api/embed',{model:embed,input:['experiment options'],keep_alive:'30m'},60000):Promise.resolve(null);
        const chatWarm=chat?localRequest('/api/chat',{model:chat,stream:false,keep_alive:'30m',options:{num_ctx:2048,num_predict:10,temperature:0},format:{type:'array',minItems:1,maxItems:1,items:{enum:['none']}},messages:[{role:'system',content:'Give ids only.'},{role:'user',content:'["none"]'}]},60000):Promise.resolve(null);
        if(!labelReady&&embed){const job=embeddingWarm.then(()=>loadLabels(embed));labelReady=job;job.catch(()=>{if(labelReady===job)labelReady=null;});}
        const results=await Promise.allSettled([embeddingWarm,chatWarm]);
        if(!alive||!aiOn||epoch!==modelEpoch)return;
        aiReadyLine.textContent=embed&&chat&&results.every(result=>result.status==='fulfilled')?'The AI models are ready':'Some AI models are unavailable. The page rules still set options.';
        aiReadyLine.title=`First load: ${elapsed(start)}.`;
      }catch{if(alive&&aiOn&&epoch===modelEpoch)aiReadyLine.textContent=(ETF_LOCAL?'No local model replied. The page rules still set options.':'No AI model replied. The page rules still set options.');}
    })();
    return modelReady;
  }
  aiToggle.addEventListener('change',()=>{
    aiOn=aiToggle.checked;cancelAIInterpretation(false);
    if(aiOn){aiCancelled=false;prepareModels();}
    else{modelEpoch++;for(const controller of aborters)controller.abort();modelDiscovery=null;modelReady=null;labelReady=null;chatSelect.disabled=true;aiReadyLine.textContent=(ETF_LOCAL?'The local models are off.':'The AI models are off.');aiState.textContent='';}
  });
  chatSelect.addEventListener('change',()=>{
    if(!aiModels.includes(chatSelect.value)||/embed/i.test(chatSelect.value))return;
    cancelAIInterpretation(false);chatModel=chatSelect.value;if(aiOn)prepareModels(false);
  });
  function requestParts(request){
    const clauses=requestClauses(request),parts=[...clauses];
    for(const clause of clauses){const words=clause.match(/[a-z0-9°%/]+(?:[-.][a-z0-9]+)*/g)||[];
      for(let start=0;start<words.length;start++)for(let length=1;length<=4&&start+length<=words.length;length++)parts.push(words.slice(start,start+length).join(' '));
    }
    return unique(parts);
  }
  function contentWords(text){return norm(text).match(/[a-z0-9]+/g)?.filter(w=>!['a','an','the','and','or','with','for','of','to','in','on','at','near','somewhere','place','test','like','really','where','i','my','is','it','be'].includes(w))||[];}
  function requestClauses(request){return norm(request).split(/[,;:.!?]|\b(?:and|with|near|in)\b|\bon\b(?!\s+foot\b)/).map(part=>part.trim()).filter(Boolean);}
  function unsupportedBasePart(part,ctx){
    if(ctx?.mode!=='mars')return false;
    // Rehearsal verdicts and low-Sun hours belong to the lunar-area data.
    const phrases=[...COMMON.light,...(rules?.activities||[]).flatMap(activity=>[activity.activity,...(COMMON[activity.id]||[])])];
    return phrases.some(phrase=>{const escaped=norm(phrase).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return escaped&&new RegExp(`(?<![a-z0-9])${escaped}s?(?![a-z0-9])`).test(norm(part));});
  }
  // The words of NO_DATA include each word of the older list (hotel, flights, favourite, colour, permit, wifi, restaurant, cheap, budget, drill, seismometer).
  function noDataTopic(part,ctx){const text=norm(part);return NO_DATA.find(([words])=>words.test(text))?.slice(1)||(unsupportedBasePart(part,ctx)?['The Atlas has activity and low-Sun data only for lunar regions.',null]:/\d+(?:\.\d+)?\s*(?:hours?|h)\s*(?:a|per|each)\s+day/.test(text)?['The Atlas has no figures for one day.','hours']:null);}
  function unsupportedPart(part,ctx){return Boolean(noDataTopic(part,ctx));}
  function lexicalCandidates(part,ctx){
    const words=contentWords(part);
    return availableDefinitions(ctx).map(d=>{const labelWords=new Set(contentWords(`${d.label} ${commonWords(d).join(' ')}`));return {d,score:words.length?words.filter(w=>labelWords.has(w)).length/words.length:0};}).sort((a,b)=>b.score-a.score).slice(0,10);
  }
  function valueFromWords(d,part,draft){
    if(unsupportedPart(part,context(draft.criteria))||!definitionAvailable(d,context(draft.criteria))||!column(d,context(draft.criteria)).values.some(value=>value!=null))return null;
    const text=norm(part);if(/\b(?:no|not|without)\b/.test(text)&&!/(?:no people|no (?:small )?tremors|not too windy|no more than)/.test(text))return null;
    const numbers=[...text.matchAll(/-?\d+(?:\.\d+)?/g)].map(m=>Number(m[0]));
    if(!d.values&&numbers.length===1){const comparison=/\b(?:at most|under|below|less than|no more than)\b/.test(text)?'at most':/\b(?:at least|over|above|more than)\b/.test(text)?'at least':null;if(comparison)return {id:d.id,comparison,value:numbers[0],necessity:'preferred'};}
    if(d.values){
      const matches=d.values.filter(v=>typeof v==='string'&&norm(v).length>2&&text.includes(norm(v)));
      if(matches.length)return {id:d.id,comparison:'is',value:matches.length===1?matches[0]:matches,necessity:'preferred'};
    }
    const alias=commonWords(d)[0];
    if(alias){const translated=interpret(alias).criteria.find(c=>c.id===d.id);if(translated)return {...translated,necessity:'preferred',pageDefault:true};}
    // A vague request can use only a default already set by the page rules.
    const exact=interpret(part).criteria.find(c=>c.id===d.id);if(exact)return {...exact,necessity:'preferred'};
    return {...defaultCriterion(d,context(draft.criteria),5),pageDefault:true};
  }
  function usePart(draft,part,c,source){
    if(draft.criteria.some(old=>old.id===c.id))return false;
    draft.criteria.push(c);draft.wordUses.push({id:c.id,words:[part],source});
    draft.unused=draft.unused.flatMap(unused=>{const text=norm(unused),index=text.indexOf(norm(part));return index<0?[unused]:[text.slice(0,index).trim(),text.slice(index+norm(part).length).trim()].filter(Boolean);});
    draft.notes.push(`${source}: ${criterionText(c)}.${c.pageDefault?' The page set this value.':''}`);return true;
  }
  async function aiInterpret(request,{publishDraft=()=>{},isCurrent=()=>true,rankings=new Map()}={}){
    cancelAIInterpretation(false);aiCancelled=false;
    const scope={cancelled:false,controllers:new Set()},ruleStart=performance.now(),draft=interpret(request),timings=[];
    activeInterpretation=scope;draft.wordUses||=[];draft.notes||=[];
    for(const use of draft.wordUses)use.source||='Page interpreter';
    const live=()=>alive&&!scope.cancelled&&activeInterpretation===scope&&isCurrent();
    const modelsLive=()=>live()&&aiOn;
    const snapshot=()=>{
      const copy=structuredClone(draft);copy.notes=unique([...copy.notes,...timings]);copy.interpreter=timings.join(' · ');
      return decorateDraft(copy,request);
    };
    const publish=(stage,start)=>{if(live())publishDraft(snapshot(),stage,(performance.now()-start)/1000);};
    timings.push(`Page interpreter: ${elapsed(ruleStart)}`);publish('rules',ruleStart);
    // Yield after publishing so the board can paint before any model/data work.
    await new Promise(resolve=>setTimeout(resolve,0));
    if(!modelsLive())return snapshot();
    aiCancel.hidden=false;aiState.textContent='The vector model checks the words that are not used.';
    let deadline;
    try{
      if(!modelDiscovery)prepareModels();
      await modelDiscovery;
      if(!modelsLive())return snapshot();
      const draftContext=context(draft.criteria);if(draftContext.mode==='mars')await ensureMarsSite(draftContext.target);
      if(!modelsLive())return snapshot();
      // Loading a cold model is handled by prewarm. Limit inference after preparation.
      const embed=embeddingModel,labelsPromise=labelReady;
      const unsupportedClauses=requestClauses(request).filter(part=>unsupportedPart(part,draftContext));
      // A fragment of an unsupported clause is not a new request for another factor.
      const allowedPart=part=>contentWords(part).length&&!unsupportedPart(part,draftContext)&&!unsupportedClauses.some(clause=>clause.includes(norm(part)));
      const parts=unique(draft.unused.flatMap(requestParts)).filter(allowedPart);let vectors=null;
      if(embed&&parts.length){
        const vectorStart=performance.now();
        try{
          const catalog=vectorCatalog(draftContext),job=labelsPromise||loadLabels(embed,draftContext);if(!labelsPromise){labelReady=job;job.catch(()=>{if(labelReady===job)labelReady=null;});}
          let loadedLabels=await job;if(!modelsLive())return snapshot();
          if(loadedLabels.key!==catalog.key)loadedLabels=await loadLabels(embed,draftContext);
          if(!modelsLive())return snapshot();
          const labels=loadedLabels.vectors,vectorDefinitions=loadedLabels.definitions;
          vectors=await embedTexts(parts,embed,scope);if(!modelsLive())return snapshot();
          for(const part of parts){const vector=vectors.get(part),ranked=vectorDefinitions.map((d,i)=>({d,score:cosine(vector,labels[i])})).sort((a,b)=>b.score-a.score),nearest=ranked.slice(0,10);nearest.otherScore=ranked.find(match=>factorKey(match.d)!==factorKey(ranked[0].d))?.score??-1;rankings.set(part,nearest);}
          const unusedText=()=>draft.unused.map(norm).join(' ');
          for(const part of [...parts].sort((a,b)=>b.length-a.length)){
            if(!unusedText().includes(norm(part))||!allowedPart(part))continue;
            const nearest=rankings.get(part),best=nearest[0];if(!best||best.score<VECTOR_LIMIT||best.score-nearest.otherScore<VECTOR_MARGIN)continue;
            const equivalent=nearest.filter(match=>factorKey(match.d)===factorKey(best.d)&&match.score>=VECTOR_LIMIT).sort((a,b)=>Number(Boolean(b.d.main))-Number(Boolean(a.d.main))||b.score-a.score);
            for(const match of equivalent){const criterion=valueFromWords(match.d,part,draft);if(criterion&&validCriterion(criterion)){usePart(draft,part,criterion,'Vector matching');break;}}
          }
          timings.push(`Vector matching (${embed}): ${elapsed(vectorStart)}`);publish('vectors',vectorStart);
        }catch(error){timings.push(`Vector matching: ${elapsed(vectorStart)}; ${error.name==='AbortError'?'stopped':'unavailable'}`);}
      }else timings.push(embed?'Vector matching: no unused words need it':'Vector matching: no embedding model');
      if(!modelsLive())return snapshot();
      // The fast steps have already set tiles. Only unused fragments go to chat.
      const remaining=unique(draft.unused.flatMap(requestClauses)).filter(allowedPart);
      if(!remaining.length||!chatModel)return snapshot();
      aiState.textContent='The chat model checks the words that are not used.';
      const chatStart=performance.now(),chat=chatModel;
      deadline=setTimeout(()=>{scope.cancelled=true;for(const controller of scope.controllers)controller.abort();if(activeInterpretation===scope&&alive){aiState.textContent='The chat model stopped. The options already set stay on the board.';aiCancel.hidden=true;}},20000);
      for(let offset=0;offset<remaining.length;offset+=3){
        if(!modelsLive())break;
        const batch=remaining.slice(offset,offset+3).map(part=>({part,nearest:rankings.get(norm(part))||lexicalCandidates(part,draftContext)}));
        const permitted=new Map();
        // At most six option meanings and three fragments keep the request short.
        for(let rank=0;rank<10&&permitted.size<6;rank++)for(const item of batch){
          const match=item.nearest[rank];if(!match||permitted.size>=6||!allowedPart(item.part))continue;
          if((vectors&&match.score<VECTOR_LIMIT)||(!vectors&&match.score<=0))continue;
          const criterion=valueFromWords(match.d,item.part,draft);
          if(criterion&&validCriterion(criterion))permitted.set(match.d.id,match.d);
        }
        if(!permitted.size)continue;
        const ids=['none',...permitted.keys()],schema={type:'array',minItems:batch.length,maxItems:batch.length,items:{enum:ids}};
        const catalog={parts:batch.map(item=>item.part),options:[...permitted.values()].map(d=>({id:d.id,meaning:`${d.label}${commonWords(d).length?`; ${commonWords(d).join(', ')}`:''}`}))};
        try{
          const answer=await localRequest('/api/chat',{model:chat,stream:false,keep_alive:'30m',options:{num_ctx:2048,num_predict:60,temperature:0},format:schema,messages:[{role:'system',content:'Give ids only. Return one JSON array, one option id or "none" for each part, in order. Select only from the supplied options. A shortlist is not proof of a match. Use "none" for questions, greetings, unrelated words, hotels, flights, colours, drilling or permission. Do not infer seismic noise from quiet alone or volcanic hazards from volcanic rock. Never answer, explain, ask a question, give advice, name a place or give a figure.'},{role:'user',content:JSON.stringify(catalog)}]},20000,scope);
          if(!modelsLive())break;
          const answerIds=JSON.parse(answer.message?.content||'null');
          if(!Array.isArray(answerIds)||answerIds.length!==batch.length||!answerIds.every(id=>typeof id==='string'&&ids.includes(id)))throw new Error('Invalid model answer');
          let changed=false;
          answerIds.forEach((id,index)=>{
            if(id==='none')return;
            const item=batch[index],candidate=item.nearest.find(match=>match.d.id===id);if(!candidate||!permitted.has(id)||!allowedPart(item.part))return;
            if((vectors&&candidate.score<VECTOR_LIMIT)||(!vectors&&candidate.score<=0))return;
            // The page derives every value; the model cannot supply one.
            const criterion=valueFromWords(candidate.d,item.part,draft);
            if(criterion&&validCriterion(criterion))changed=usePart(draft,item.part,criterion,'Chat interpreter')||changed;
          });
          if(changed){timings.push(`Chat interpreter (${chat}): ${elapsed(chatStart)}`);publish('chat',chatStart);}
        }catch(error){if(!modelsLive())break;timings.push(`Chat interpreter: ${elapsed(chatStart)}; ${error.name==='AbortError'?'stopped':'invalid or unavailable'}`);}
      }
      return snapshot();
    }catch(error){if(live())timings.push(error.name==='AbortError'?'Local models stopped':'Local models unavailable');return snapshot();}
    finally{clearTimeout(deadline);if(activeInterpretation===scope){aiCancel.hidden=true;if(live())aiState.textContent=timings.join(' · ');}}
  }
  const breakdown=el('section','ak-breakdown'),results=el('section','ak-results'),status=el('p','ak-status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  // Feedback on a request sits under the result line. CSS hides it while it is empty.
  const feedback=el('div','ak-feedback');feedback.setAttribute('aria-live','polite');
  const builder=el('section','ak-builder ak-board'),builderCount=el('p','ak-count'),baseNotice=el('p','ak-base-notice'),categories=el('div','ak-categories');
  baseNotice.hidden=true;baseNotice.setAttribute('role','status');
  const wordsRoot=root.ownerDocument.getElementById('ask-words'),resultsRoot=root.ownerDocument.getElementById('ask-results');
  const words=el('div','ak-words ak-bubble');words.append(head,form,examples,aiBox);
  root.replaceChildren();if(wordsRoot){wordsRoot.classList.add('ak-module');wordsRoot.replaceChildren(words);}else root.append(words);
  root.append(builder);words.append(breakdown);if(resultsRoot){resultsRoot.classList.add('ak-module');resultsRoot.replaceChildren(status,results);}else root.append(status,results);
  const presets=el('div','ak-presets');
  const applyPreset=i=>{if(!alive||!exampleTexts[i])return false;generation++;cancelAIInterpretation(false);feedback.replaceChildren();const previous=current;current=decorateDraft(timedInterpret(exampleTexts[i]),exampleTexts[i]);current.criteria=curatedCriteria(current.criteria,context(current.criteria));textarea.value=current.request;bubbleUndo=null;bubbleUndoTiles=null;markChanges(previous.criteria,current.criteria);bubbleResult=`Preset: ${current.criteria.filter(c=>c.id!=='destination'&&importance(c)>0).map(c=>`${shortLabel(projectDefinition(byId.get(c.id),context(current.criteria)))}: ${importance(c)}`).join('; ')}.`;revealChangedOptions();render();save(true);return true;};
  for(const [i,label] of ['Rover camera test','Crew work in winter light','Seismometer test'].entries())presets.append(button(label,()=>applyPreset(i),'ak-preset'));
  const boardActions=el('div','ak-board-actions');
  boardActions.append(button('Open all',()=>{for(const view of categoryViews.values())setCategoryOpen(view,true,false);}),button('Close all',()=>{for(const view of categoryViews.values())setCategoryOpen(view,false,false);}),button('Clear all',()=>{generation++;cancelAIInterpretation(false);feedback.replaceChildren();bubbleUndo=null;bubbleUndoTiles=null;bubbleResult='';changedOptions.clear();pendingExtras.clear();baseNotice.hidden=true;current=emptyExperiment();textarea.value='';drawBuilder();render();save();}));
  builder.append(el('h3','','Make your experiment'),el('p','ak-note','Set how much each option counts, from 0 to 10. 10 means necessary.'),presets,builderCount,boardActions,baseNotice,categories);
  let lastSearch=null,openCategories=new Set(),builderUpdates=[],showAll=false,renderRequest=0,waitingSite=null,bubbleUndo=null,bubbleUndoTiles=null,bubbleUndoBoard=null,bubbleResult='',changedOptions=new Set(),pendingExtras=new Set(),changeTimer=0,tourSnapshotActive=false;
  const tileDrafts=new Map(),categoryViews=new Map();
  function curatedCriteria(criteria,ctx,preserveImportance=false){const seen=new Set();return criteria.map(c=>canonicalCriterion(c,ctx,preserveImportance)).filter(c=>c&&validCriterion(c)&&(c.id==='destination'||definitionAvailable(byId.get(c.id),ctx))&&!seen.has(c.id)&&seen.add(c.id));}
  function markChanges(before,after){changedOptions=new Set([...before,...after].filter(c=>c.id!=='destination'&&importance(c)>0&&JSON.stringify(before.find(x=>x.id===c.id))!==JSON.stringify(after.find(x=>x.id===c.id))).map(c=>c.id));clearTimeout(changeTimer);changeTimer=setTimeout(()=>{changedOptions.clear();for(const node of categories.querySelectorAll('.ak-changed'))node.classList.remove('ak-changed');},5000);}
  function emptyExperiment(){return {version:1,request:'',criteria:[],unused:[],notes:[],interpreter:'Controls on this page'};}
  function timedInterpret(request){const start=performance.now(),next=interpret(request);next.interpreter=`The page interpreter: ${((performance.now()-start)/1000).toFixed(3)} s`;return next;}
  function isOptionRequest(request){return !/^(?:hi|hello|hey|thanks|thank you|good morning|good evening)[!.,\s]*$/i.test(request.trim())&&!/\?/.test(request)&&! /^(?:please\s+)?(?:explain|tell me|give (?:me )?advice|advise|recommend)\b/i.test(request.trim())&&! /^(?:what|why|how|where|when|who|which|can|could|should|would|is|are|do|does|will)\b/i.test(request.trim());}
  function phraseImportance(text){text=norm(text).replace(/no permit (?:is )?necessary/g,'');return /\b(?:must|necessary|need)\b/.test(text)?10:/\bimportant\b/.test(text)?8:/\b(?:prefer|if possible|ideally)\b/.test(text)?4:/\ba little\b/.test(text)?2:6;}
  function decorateDraft(source,request){
    const draft=structuredClone(source),clauses=request.split(/[;!]|\.(?!\d)|(?<!\d)\.|,(?!\d)/).map(norm),uses=draft.wordUses||[];
    draft.criteria=draft.criteria.map(raw=>{
      if(raw.id==='destination')return normalizeCriterion({...raw,importance:10});
      const d=byId.get(raw.id),words=uses.filter(x=>x.id===raw.id).flatMap(x=>x.words||[]),clause=clauses.find(part=>words.some(word=>part.includes(norm(word))))||clauses.find(part=>part.includes(norm(d.label)))||norm(request);
      let c=normalizeCriterion({...raw,importance:phraseImportance(clause),wanted:raw.wanted||(d.values?'is':raw.pageDefault?direction(d)||'near':raw.comparison||direction(d)||'near')});
      if(!d.values&&(!finite(c.value)||c.importance===10&&raw.pageDefault)){const limit=dataLimit(d,context(draft.criteria));c={...c,value:limit.value,pageDefault:true};if(c.importance===10)c.wanted=c.comparison=limit.wanted;}
      return c;
    }).filter(validCriterion);return draft;
  }
  function applyDraft(draft,baseline,stage,seconds){
    draft.criteria=curatedCriteria(draft.criteria,context(draft.criteria));
    const incoming=draft.criteria.filter(c=>c.id!=='destination'&&importance(c)>0);
    // No option: the feedback block says so when the work is complete (after the last AI step).
    if(!incoming.length){bubbleResult='';drawBreakdown();return false;}
    const ids=new Set(draft.criteria.map(c=>c.id));current={...draft,criteria:[...baseline.criteria.filter(c=>!ids.has(c.id)),...draft.criteria]};
    markChanges(baseline.criteria,current.criteria);
    const names={rules:'The page interpreter',vectors:'Vector matching',chat:'The chat interpreter'};
    const groups=new Map();for(const c of incoming){const source=draft.wordUses?.find(use=>use.id===c.id)?.source||'Page interpreter';if(!groups.has(source))groups.set(source,[]);groups.get(source).push(`${shortLabel(projectDefinition(byId.get(c.id),context(current.criteria)))}: ${importance(c)}`);}
    bubbleResult=`${[...groups].map(([source,items])=>`${source}: ${items.join('; ')}.`).join(' ')} ${stage==='rules'?`${names[stage]}: ${seconds.toFixed(3)} s.`:draft.interpreter||`${names[stage]}: ${seconds.toFixed(3)} s.`}`;
    revealChangedOptions();render();save(true);return true;
  }
  function save(wordsChanged=false){
    if(!current)return;lastSaved=JSON.stringify(current);const patch={ask:JSON.parse(lastSaved)};
    if(wordsChanged){patch.tab2='make';const c=context(current.criteria);patch.dest=c.mode;patch[c.mode==='moon'?'target':'msite']=c.target;}
    api.setState(patch);
  }
  // A change on the board makes the lines of kind 4 (nothing passes) old: remove them.
  function edit(){generation++;cancelAIInterpretation?.(false);feedback.querySelector('.ak-feedback-group')?.remove();showAll=false;render();save();}
  function labelledControl(text,node){const l=el('label');l.append(el('span','',text),node);return l;}
  function defaultCriterion(d,ctx,weight=0){
    const col=column(d,ctx),wanted=d.values?'is':direction(d)||'near';
    const value=d.values?d.values.find(v=>! /^(unknown|cannot tell)/i.test(String(v)))??d.values[0]:null;
    return normalizeCriterion({id:d.id,importance:weight,wanted,value,comparison:wanted});
  }
  function dataLimit(d,ctx){
    const input={h30:'H30',airfield:'D',bare:'B',temperature:'T',snow:'S','factor:p90_slope':'P90'}[d.id];
    const rule=input?(rules?.activities||[]).flatMap(a=>a.pass||[]).find(p=>p.input===input):null;
    const col=column(d,ctx);return rule?{value:rule.value*(d.id==='snow'?100:1),wanted:rule.op.includes('>')?'at least':'at most'}:{value:col.sorted.length?col.sorted[Math.floor((col.sorted.length-1)/2)]:null,wanted:direction(d)==='less'?'at most':'at least'};
  }
  function design(d){
    if(d.size&&d.icon)return [d.size,d.icon];
    const entry=TILE_DESIGN[d.id]||TILE_DESIGN[d.factor];if(entry)return entry;
    const word=`${d.factor} ${d.id} ${d.group}`.toLowerCase();const icon=/airfield/.test(word)?'plane':/road/.test(word)?'road':/wind.*power|power.*wind/.test(word)?'turbine':/wind/.test(word)?'wind':/solar|sun/.test(word)?'solar':/geothermal/.test(word)?'spring':/volcan/.test(word)?'volcano':/tremor|seismic/.test(word)?'wave':/snow|frozen|permafrost/.test(word)?'snow':/rock|rough|ground/.test(word)?'rock':/temperature/.test(word)?'thermometer':/cloud|haze|climate/.test(word)?'cloud':/people|human/.test(word)?'people':/land|hazard|permit/.test(word)?'shield':/hemisphere|latitude|longitude/.test(word)?'compass':'pin';return ['small',icon];
  }
  function tileIcon(kind){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.classList.add('ak-tile-icon');const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',ICON_PATHS[kind]||ICON_PATHS.pin);path.setAttribute('fill','none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1.6');path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');svg.append(path);return svg;}
  function shortLabel(d){return d.shortLabel||d.label;}
  const categoryDesign={Activity:['large','rover'],Light:['large','sun'],'Time of year':['large','calendar'],'Likeness to the site':['large','compass'],Ground:['medium','rock'],Climate:['medium','cloud'],Access:['medium','plane'],'Land and permits':['medium','shield'],'People and hazards':['small','people'],Power:['small','solar'],Region:['small','pin']};
  function focusFirstOption(panel){const option=panel.querySelector('.ak-tile,.ak-option-row')||panel,controls=[...option.querySelectorAll('input,select'),...option.querySelectorAll('button,summary')],first=controls.find(node=>!node.disabled&&!node.closest('[hidden]')&&node.getClientRects().length);first?.focus({preventScroll:true});}
  function setCategoryOpen(view,open,focus=true){
    if(categoryViews.get(view.name)!==view)return;
    if(open){openCategories.add(view.name);view.build();}else openCategories.delete(view.name);
    view.card.setAttribute('aria-expanded',String(open));view.panel.hidden=!open;view.section.dataset.open=String(open);view.chevron.textContent=open?'−':'+';
    if(focus){if(open)focusFirstOption(view.panel);else view.card.focus({preventScroll:true});}
  }
  function drawBuilder(){
    const active=document.activeElement,focusedCategory=categories.contains(active)?active.closest('.ak-category')?.dataset.category:null,focusedCriterion=active?.closest('[data-criterion]')?.dataset.criterion,focusLabel=active?.getAttribute('aria-label');
    categories.replaceChildren();builderUpdates=[];tileDrafts.clear();categoryViews.clear();
    const ctx=context(current.criteria),available=availableDefinitions(ctx),groups=unique([...available.filter(d=>d.main),...available].map(d=>d.group));
    for(const name of openCategories)if(!groups.includes(name))openCategories.delete(name);
    for(const [index,groupName] of groups.entries()){
      const defs=available.filter(d=>d.group===groupName),section=el('section','ak-category'),card=button('',()=>setCategoryOpen(view,!openCategories.has(groupName)),'ak-category-card'),panel=el('section','ak-category-panel'),line=el('span','ak-category-line'),count=el('span','ak-category-count'),chevron=el('span','ak-category-chevron','+');
      const [size,icon]=ctx.mode==='mars'&&groupName==='Time of year'?['small','calendar']:categoryDesign[groupName]||['small','pin'],picture=tileIcon(icon);picture.classList.replace('ak-tile-icon','ak-category-icon');
      section.dataset.category=groupName;section.dataset.open='false';card.dataset.size=size;card.id=`ak-category-${index}`;panel.id=`ak-panel-${index}`;panel.hidden=true;
      card.setAttribute('aria-expanded','false');card.setAttribute('aria-controls',panel.id);panel.setAttribute('aria-labelledby',card.id);chevron.setAttribute('aria-hidden','true');
      card.append(picture,el('span','ak-category-name',groupName),line,count,chevron);section.append(card,panel);categories.append(section);
      const view={name:groupName,section,card,panel,chevron,defs,built:false,more:null,build(){
        if(view.built||categoryViews.get(groupName)!==view)return;view.built=true;
        const body=el('div','ak-category-body');panel.append(el('h4','ak-panel-title',groupName),body);
        for(const d of defs.filter(d=>d.main))body.append(criterionControl(d));
        const others=defs.filter(d=>!d.main);
        if(others.length){const more=el('details','ak-more');view.more=more;more.append(el('summary','',`More options (${others.length})`));let made=false;const populate=()=>{if(made||categoryViews.get(groupName)!==view)return;made=true;const list=el('div','ak-more-list');for(const d of others)list.append(criterionControl(d,true));more.append(list);};more.buildOptions=populate;more.addEventListener('toggle',()=>{if(more.open)populate();});panel.append(more);if(others.some(d=>pendingExtras.has(d.id))){populate();more.open=true;}}
      }};
      categoryViews.set(groupName,view);
      panel.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();setCategoryOpen(view,false);}});
      const update=()=>{const set=defs.map(d=>({d,c:current.criteria.find(c=>c.id===d.id)})).filter(({c})=>c&&importance(c)>0);line.textContent=set.length?set.map(({d,c})=>`${shortLabel(d)} ${importance(c)}`).join(' · '):'not set';line.title=line.textContent;count.textContent=set.length?`${set.length} set`:'';count.hidden=!set.length;card.classList.toggle('ak-changed',defs.some(d=>changedOptions.has(d.id)));};builderUpdates.push(update);update();
      if(openCategories.has(groupName))setCategoryOpen(view,true,false);
    }
    if(focusedCategory){const view=categoryViews.get(focusedCategory);if(view){const field=focusedCriterion?[...view.panel.querySelectorAll('[data-criterion]')].find(node=>node.dataset.criterion===focusedCriterion):null;const control=field&&[...field.querySelectorAll('[aria-label]')].find(node=>node.getAttribute('aria-label')===focusLabel);(control||view.card).focus({preventScroll:true});}}
  }
  function revealChangedOptions(){for(const id of changedOptions){if(!current.criteria.some(c=>c.id===id&&importance(c)>0))continue;const d=projectDefinition(byId.get(id),context(current.criteria));if(!d||d.main)continue;pendingExtras.add(id);const view=categoryViews.get(d.group);if(view?.built&&view.more){view.more.buildOptions();view.more.open=true;}}}
  function criterionControl(d,compact=false){
    const [size,icon]=design(d),box=el('div',compact?'ak-option-row':'ak-tile');box.dataset.criterion=d.id;box.dataset.size=size;
    const name=el('strong',compact?'ak-option-name':'ak-tile-name',shortLabel(d));name.title=d.label;if(!compact)box.append(tileIcon(icon));box.append(name);
    let draft=current.criteria.find(c=>c.id===d.id)||defaultCriterion(d,context(current.criteria));
    tileDrafts.set(d.id,{read:()=>structuredClone(draft),restore:value=>{draft=structuredClone(value);}});
    const importanceBox=el('div','ak-importance'),weightInput=el('input'),necessary=el('span','ak-necessary');weightInput.type='number';weightInput.min='0';weightInput.max='10';weightInput.step='1';weightInput.setAttribute('aria-label',`${d.label}: importance`);
    const wanted=el('div','ak-wanted'),alone=el('span','ak-alone'),metaLine=el('div','ak-tile-meta'),warning=el('span','ak-value-note');
    const kind=/estimate/.test(d.kind)?'rough estimate':/measur/.test(d.kind)?'measured':/coarse/.test(d.kind)?'coarse map':/model/.test(d.kind)?'model':'';metaLine.append(alone);if(kind)metaLine.append(el('span','ak-kind',kind));metaLine.append(warning);
    const commit=patch=>{let next=normalizeCriterion({...draft,...current.criteria.find(c=>c.id===d.id),...patch});
      if(Object.prototype.hasOwnProperty.call(patch,'value')){next.pageDefault=false;delete next.baseDefault;}
      if(next.importance===10&&!d.values){const limit=dataLimit(d,context(current.criteria));if(!finite(next.value)){next.value=limit.value;next.pageDefault=true;}if(!['at least','at most'].includes(next.wanted))next.wanted=limit.wanted;next.comparison=next.wanted;}
      current.criteria=current.criteria.filter(c=>c.id!==d.id);draft=next;if(next.importance>0&&validCriterion(next))current.criteria.push(next);edit();
    };
    const step=delta=>commit({importance:Math.max(0,Math.min(10,importance(draft)+delta))});
    importanceBox.append(button('↓',()=>step(-1),'ak-weight-down'),weightInput,button('↑',()=>step(1),'ak-weight-up'),necessary);
    for(const [node,label] of [[importanceBox.children[0],'Decrease'],[importanceBox.children[2],'Increase']])node.setAttribute('aria-label',`${label} ${d.label} importance`);
    weightInput.addEventListener('input',()=>{if(Number.isInteger(weightInput.valueAsNumber))commit({importance:Math.max(0,Math.min(10,weightInput.valueAsNumber))});});
    const knownClasses=d.values?.filter(v=>!/^(unknown|cannot tell|mixed or cannot tell)/i.test(String(v))),boolean=knownClasses?.length===2&&knownClasses.some(v=>v===true||norm(v)==='yes')&&knownClasses.some(v=>v===false||norm(v)==='no');
    let toggle,select,valueInput,choices=[];
    if(boolean){const label=el('label','ak-toggle');toggle=el('input');toggle.type='checkbox';toggle.setAttribute('aria-label',d.label);label.append(toggle,document.createTextNode('On'));wanted.append(label);toggle.addEventListener('change',()=>commit({importance:toggle.checked?5:0,value:d.values.find(v=>v===true||norm(v)==='yes')}));}
    else if(d.values){const chips=el('div','ak-chips');for(const value of d.values){const b=button(displayValue(d,value),()=>{const old=current.criteria.find(c=>c.id===d.id),values=old?(Array.isArray(old.value)?old.value:[old.value]):[],next=values.includes(value)?values.filter(v=>v!==value):[...values,value];commit({importance:next.length?(old?importance(old):5):0,value:next});},'ak-choice');choices.push([b,value]);chips.append(b);}wanted.append(chips);}
    else{select=el('select');select.setAttribute('aria-label',`${d.label}: wanted direction`);valueInput=el('input');valueInput.type='number';valueInput.step='any';valueInput.placeholder='Set a value';valueInput.setAttribute('aria-label',`${d.label}: wanted value`);select.addEventListener('change',()=>commit({wanted:select.value,importance:importance(draft)||5,pageDefault:false}));valueInput.addEventListener('input',()=>{if(finite(valueInput.valueAsNumber))commit({value:valueInput.valueAsNumber,importance:importance(draft)||5,pageDefault:false});});wanted.append(select,valueInput,el('span','ak-unit',d.unit||''));}
    const detail=el('details','ak-detail');detail.append(el('summary','','What it is not'),el('p','ak-note',`${d.label}. ${d.note}`));box.append(importanceBox,wanted,metaLine,detail);
    const update=()=>{const active=current.criteria.find(c=>c.id===d.id);draft=active?normalizeCriterion(active):{...draft,importance:0};const weight=importance(draft);box.dataset.active=String(weight>0);box.classList.toggle('ak-changed',changedOptions.has(d.id));weightInput.value=String(weight);necessary.textContent=weight===10?'necessary':'';
      if(toggle){toggle.checked=weight>0;importanceBox.hidden=weight===0;}
      if(select){const range=column(d,context(current.criteria));valueInput.min=finite(range.min)?String(range.min):'';valueInput.max=finite(range.max)?String(range.max):'';valueInput.title=finite(range.min)?`${api.fmtNumber(range.min,2)} to ${api.fmtNumber(range.max,2)} ${d.unit||''}`:'Range unknown';const labels=weight===10?[['at least','at least'],['at most','at most']]:[['more','more is better'],['less','less is better'],['near','near a value']];if(select.dataset.mode!==String(weight===10)){select.replaceChildren(...labels.map(([value,label])=>{const o=el('option','',label);o.value=value;return o;}));select.dataset.mode=String(weight===10);}select.value=draft.wanted;valueInput.hidden=weight!==10&&draft.wanted!=='near';if(document.activeElement!==valueInput)valueInput.value=finite(draft.value)?String(draft.value):'';}
      for(const [b,value] of choices)b.setAttribute('aria-pressed',String(weight>0&&(Array.isArray(draft.value)?draft.value:[draft.value]).includes(value)));
      const e=evaluate(draft,context(current.criteria)),unset=draft.wanted==='near'&&!finite(draft.value);alone.textContent=!e.col.knownCount?'unknown':`${api.fmtNumber(unset?e.col.knownCount:e.count)} ${context(current.criteria).mode==='moon'?'areas':'squares'}${unset||['more','less'].includes(draft.wanted)?' with figures':''}`;warning.textContent=weight>0&&!d.values&&unset?'Set a wanted value.':weight>0&&draft.pageDefault?'the page set this value':'';
    };builderUpdates.push(update);update();return box;
  }
  function drawBreakdown(){
    // The feedback block stays in the page: a live region that is put in again is not announced.
    for(const node of [...breakdown.childNodes])if(node!==feedback)node.remove();const line=el('p','ak-bubble-answer',bubbleResult);line.setAttribute('role','status');line.setAttribute('aria-live','polite');breakdown.prepend(line);if(feedback.parentNode!==breakdown)breakdown.append(feedback);
    if(bubbleResult&&bubbleResult!=='No option was set. Write what the experiment needs.'&&current.unused?.length){const unused=el('details','ak-unused');unused.append(el('summary','','Words that the page did not use'),el('p','',current.unused.join('; ')));breakdown.append(unused);}
    const actions=el('div','ak-actions');if(bubbleUndo)actions.append(button('Undo',()=>{generation++;cancelAIInterpretation(false);feedback.replaceChildren();current=structuredClone(bubbleUndo);for(const [id,control] of tileDrafts)control.restore(bubbleUndoTiles?.get(id)||defaultCriterion(byId.get(id),context(current.criteria)));pendingExtras=new Set(bubbleUndoBoard?.pendingExtras||[]);for(const [name,view] of categoryViews)if(view.more){view.more.open=bubbleUndoBoard?.more.get(name)||false;if(view.more.open)view.more.buildOptions();}bubbleUndo=null;bubbleUndoTiles=null;bubbleUndoBoard=null;bubbleResult='The board is back as it was before the request.';changedOptions.clear();textarea.value=current.request;render();save(true);}));
    actions.append(button('Copy this experiment as a link',async()=>{save();await copy(location.href);}),button('Copy the breakdown',()=>copy(plainText())));breakdown.append(actions);
  }
  async function copy(text){try{await navigator.clipboard.writeText(text);status.textContent='Copied.';}catch{const box=el('textarea','ak-request');box.value=text;box.readOnly=true;box.setAttribute('aria-label','Text to copy');status.replaceChildren(el('span','','Select and copy this text.'),box);box.focus();box.select();}}
  function mark(c,i,ctx){const v=check(i,c,ctx);return {...v,word:v.yes==null?'unknown':v.yes?'yes':v.near>0?'near':'no'};}
  function plainText(){if(!current||!lastSearch)return '';const out=[current.request,'',current.interpreter];for(const g of GROUPS){const cs=current.criteria.filter(c=>projectDefinition(byId.get(c.id),lastSearch.ctx).group===g);if(cs.length)out.push(g,...cs.map(c=>`${criterionText(c,lastSearch.ctx)} · importance ${importance(c)}`));}out.push('Words that the page did not use:',...current.unused,...current.notes,'',`${lastSearch.passed} places pass. ${lastSearch.unknown} places are out because a figure is unknown.`);
    if(lastSearch.ctx.mode==='mars')out.push(...marsCautions());for(const r of rows){out.push(nameOf(r.i,lastSearch.ctx.mode),`Match: ${r.share==null?'unknown':`${api.fmtNumber(r.share*100,1)}%`}`,lastSearch.ctx.mode==='moon'?api.fmtHours(r.hours):`Mars score: ${api.fmtNumber(r.score,4)}`,bestPeriods(r.i,lastSearch.ctx));for(const c of lastSearch.active){const v=mark(c,r.i,lastSearch.ctx);out.push(`${criterionText(c)}: ${v.word} · ${displayValue(byId.get(c.id),v.value)}`);}}out.push('','The match compares the figures of this page with your criteria. It does not measure the ground.',sources?.licence_line||'The licence line is unavailable.');return out.join('\n');}
  function marsCautions(){return [`First pass: squares of approximately ${mars.meta.square_km_about} km.`,mars.meta.climate_caution,mars.meta.score_caution,mars.meta.status_caution].filter(Boolean);}
  function destinationItems(){
    const lunar=(meta.targets||api.targets).slice().sort((a,b)=>(a.limit_deg??a.limitDeg??Infinity)-(b.limit_deg??b.limitDeg??Infinity)).map(t=>{
      const tags=Array.isArray(t.lists)?t.lists.filter(x=>typeof x==='string'):[];
      const listed2024=Array.isArray(t.lists)?tags.some(x=>/\b2024\b/.test(x)):String(t.list_summary||'').split(/(?<=[.!?])\s+/).some(x=>/\b2024\b/.test(x)&&! /\b(?:not|no longer|removed)\b/i.test(x));
      return {...t,mode:'moon',group:listed2024?'NASA 2024 list':'NASA 2022 list only',tags:[...tags,...(t.has_model===false?['no terrain model']:[])]};
    });
    const groups=['NASA landing sites','2021 shortlist for human landings','2015 exploration zones'];
    return [...lunar,...(mars?.sites||[]).map(t=>{const tags=Array.isArray(t.lists)?t.lists.filter(x=>typeof x==='string'):[];return {...t,mode:'mars',tags,group:groups.find((_,i)=>tags.some(x=>i===0?/NASA landing sites?/i.test(x):i===1?/2021/.test(x):/2015/.test(x)))||'Mars'};})];
  }
  function selectDestination(id){
    generation++;current.criteria=current.criteria.filter(c=>c.id!=='destination');current.criteria.unshift({id:'destination',comparison:'is',value:id,necessity:'necessary'});save(true);drawBuilder();render();
  }
  function destinationControl(){
    const box=el('div','ak-destination-control'),label=el('label','','Filter destinations'),filter=el('input'),list=el('div','ak-destination-list'),count=el('p','ak-note');
    box.dataset.criterion='destination';filter.type='search';filter.placeholder='Name or list';label.append(filter);count.setAttribute('role','status');box.append(label,count,list);
    const items=destinationItems(),groups=['NASA 2024 list','NASA 2022 list only','NASA landing sites','2021 shortlist for human landings','2015 exploration zones','Mars'];
    const draw=()=>{const query=norm(filter.value),shown=items.filter(t=>norm([t.name,t.id,t.region,...t.tags,t.list_summary,t.list_line].join(' ')).includes(query));list.replaceChildren();count.textContent=`${shown.length} of ${items.length} destinations`;
      for(const group of groups){const rows=shown.filter(t=>t.group===group);if(!rows.length)continue;list.append(el('h4','',`${group} (${rows.length})`));for(const t of rows){const b=button(t.name,()=>selectDestination(t.id),'ak-destination-row');b.dataset.destination=t.id;b.setAttribute('aria-pressed',String(context(current.criteria).target===t.id));if(t.tags.length)b.append(el('small','',t.tags.join(' · ')));list.append(b);}}
      if(!shown.length)list.append(el('p','ak-note','No destination has this name or list.'));
    };filter.addEventListener('input',draw);draw();return box;
  }
  function* destinationParts(criteria,target){
    const ctx=context(criteria,target),pool=ctx.mode==='moon'?areas:marsAreas,prepared=[];
    for(const c of criteria){const e=yield* evaluationParts(c,ctx);prepared.push({c,e,weight:importance(c)});yield;}
    if(ctx.mode==='mars'&&prepared.some(x=>x.e.col.values.every(v=>v==null)))return null;
    const necessary=prepared.filter(x=>importance(x.c)===10),weight=prepared.reduce((n,x)=>n+x.weight,0);let passed=0,best=null;
    for(let i=0;i<pool.length;i++){if(i%64===0)yield;if(necessary.some(x=>x.e.yes[i]!==1))continue;passed++;let sum=0,knownWeight=0;for(const x of prepared)if(x.e.yes[i]>=0){sum+=x.e.near[i]*x.weight;knownWeight+=x.weight;}const share=knownWeight?sum/knownWeight:null;if(share!=null&&(best==null||share>best))best=share;}
    return {ctx,passed,best};
  }
  function drawDestinations(){
    const fold=el('details','ak-destinations');fold.append(el('summary','','Which destination fits this experiment?'));const output=el('div');fold.append(output);
    const experiment=current,active=current.criteria.filter(c=>c.id!=='destination'&&importance(c)>0).map(c=>({...c})),signature=JSON.stringify(active);
    const marsSites=mars?.sites||[];let phase='',epoch=0,moonNext=0,marsNext=0,all=false,order='places',answers=[],progress='';
    const valid=()=>alive&&fold.isConnected&&current===experiment&&JSON.stringify(current.criteria.filter(c=>c.id!=='destination'&&importance(c)>0))===signature;
    const draw=()=>{
      const controls=el('div','ak-destination-order'),label=el('label','','Order by '),sort=el('select');sort.setAttribute('aria-label','Order destinations');
      for(const [value,text] of [['places','Number of places'],['match','Best match']]){const option=el('option','',text);option.value=value;sort.append(option);}sort.value=order;sort.addEventListener('change',()=>{order=sort.value;draw();});label.append(sort);controls.append(label);
      if(answers.length>8)controls.append(button(all?'Show best eight':`Show all ${answers.length}`,()=>{all=!all;draw();}));
      if(marsSites.length){
        const action=button(phase==='mars'?'Stop':marsNext>=marsSites.length?'Mars sites compared':marsNext?'Continue Mars comparison':'Compare Mars sites',()=>{
          if(phase==='mars'){epoch++;phase='';progress=`Stopped: ${marsNext} of ${marsSites.length} Mars sites compared.`;draw();}
          else run('mars');
        });action.disabled=phase==='moon'||marsNext>=marsSites.length;action.classList.add('ak-compare-mars');controls.append(action);
      }
      const note=el('p','ak-note',progress);note.setAttribute('role','status');note.setAttribute('aria-live','polite');note.classList.add('ak-destination-progress');
      const table=el('table','ak-table'),head=el('thead'),hr=el('tr');for(const text of ['Destination','Places','Best match',''])hr.append(el('th','',text));head.append(hr);table.append(head);const body=el('tbody');
      const sorted=answers.slice().sort((a,b)=>order==='match'?(b.best??-1)-(a.best??-1)||b.passed-a.passed:b.passed-a.passed||(b.best??-1)-(a.best??-1));
      for(const s of sorted.slice(0,all?sorted.length:8)){const tr=el('tr'),isMars=s.ctx.mode==='mars';tr.dataset.destination=s.t.id;tr.setAttribute('aria-current',String(context(current.criteria).target===s.t.id));tr.append(el('th','',`${s.t.name}${isMars?' · first pass':''}`),el('td','',`${api.fmtNumber(s.passed)} ${isMars?'squares':'areas'}`),el('td','',s.best==null?'unknown':`${api.fmtNumber(s.best*100,1)}%`));const td=el('td');td.append(button('Select',()=>selectDestination(s.t.id)));tr.append(td);body.append(tr);}table.append(body);output.replaceChildren(controls,note);
      if(answers.some(s=>s.ctx.mode==='mars'))output.append(el('p','ak-note',`First pass: Mars squares of approximately ${mars.meta.square_km_about} km.`));output.append(table);
      if(marsNext){for(const line of marsCautions())output.append(el('p','ak-note',line));if(answers.filter(s=>s.ctx.mode==='mars').length<marsNext)output.append(el('p','ak-note','Some criteria have no Mars figures. Those Mars sites are not in this table.'));}
      fold.dataset.destinationCount=String(answers.length);
    };
    const run=async mode=>{
      if(!fold.open||phase)return;phase=mode;const token=++epoch,start=performance.now(),destinations=mode==='moon'?api.targets:marsSites;
      let maxSlice=Number(fold.dataset.maxSliceMs)||0;
      const keep=()=>valid()&&token===epoch;
      try{for(let index=mode==='moon'?moonNext:marsNext;index<destinations.length;index++){
        const t=destinations[index];progress=`Working: ${index} of ${destinations.length} ${mode==='moon'?'lunar regions':'Mars sites'} compared.`;draw();
        if(mode==='mars')await ensureMarsSite(t.id);
        if(!keep())return;
        const iterator=destinationParts(active,t.id);let step;
        do{if(!keep())return;const slice=performance.now();do{step=iterator.next();}while(!step.done&&performance.now()-slice<12);maxSlice=Math.max(maxSlice,performance.now()-slice);if(!step.done)await new Promise(resolve=>setTimeout(resolve,0));}while(!step.done);
        if(step.value)answers.push({...step.value,t});if(mode==='moon')moonNext=index+1;else marsNext=index+1;
        await new Promise(resolve=>setTimeout(resolve,0));
      }if(!keep())return;progress=`${destinations.length} of ${destinations.length} ${mode==='moon'?'lunar regions':'Mars sites'} compared.`;
      fold.dataset.elapsedMs=String((Number(fold.dataset.elapsedMs)||0)+performance.now()-start);fold.dataset.maxSliceMs=String(maxSlice);
      }finally{if(token===epoch){phase='';if(mode==='mars'&&marsNext<marsSites.length&&!valid())progress=`Stopped: ${marsNext} of ${marsSites.length} Mars sites compared.`;if(valid())draw();}}
    };
    fold.addEventListener('toggle',()=>{if(!fold.open)return;draw();if(moonNext<api.targets.length)run('moon');});draw();return fold;
  }
  function publishMatches(s){const known=s?.all.filter(r=>finite(r.share))||[];api.setMatches?.(s?.active.length?{label:`${api.fmtNumber(s.passed)} ${s.ctx.mode==='moon'?'areas':'squares'} pass. Best match: ${s.best==null?'unknown':`${api.fmtNumber(s.best*100,1)}%`}.`,areas:known.map(r=>r.i),scores:known.map(r=>r.share),mode:s.ctx.mode}:null);}
  function render(){
    if(!alive||!current)return;
    const request=++renderRequest,ctx=context(current.criteria);
    if(ctx.mode==='mars'&&!marsSiteReady(ctx.target)){
      waitingSite=ctx.target;status.textContent='Working: read the figures for this Mars site.';
      ensureMarsSite(ctx.target).then(()=>{if(alive&&request===renderRequest){drawBuilder();render();}});return;
    }
    waitingSite=null;const start=performance.now();lastSearch=search(current.criteria);const s=lastSearch,noun=s.ctx.mode==='moon'?'areas':'squares';rows=s.rows;
    for(const host of [root,wordsRoot,resultsRoot].filter(Boolean))host.dataset.dest=s.ctx.mode;
    builderCount.textContent=`${api.fmtNumber(s.passed)} of ${api.fmtNumber(s.total)} ${noun} pass the necessary options`;
    status.textContent=`${api.fmtNumber(s.unknown)} ${noun} are out because a figure is unknown.`;
    for(const update of builderUpdates)update();drawBreakdown();results.replaceChildren(el('h3','','Places from the data'));
    publishMatches(s);
    if(!s.active.length){results.append(el('p','ak-note','Set a criterion to see the nearest places.'));root.dataset.updateMs=String(performance.now()-start);return;}
    if(s.ctx.mode==='mars'){const cautions=el('div','ak-cautions');for(const line of marsCautions())cautions.append(el('p','',line));results.append(cautions);}
    else results.append(el('p','ak-note',`${targetMap.get(s.ctx.target)} · step 3 · areas of ${meta.scoring.cell_km} km.`));
    results.append(el('p','ak-note',`The list has at most one place within ${sites.same_site_km} km. Importance sets the weight. Unknown preferences take no part in the mean. Equal matches use ${s.ctx.mode==='moon'?'low-Sun hours':'the stored Mars score'}.`));
    if(!rows.length){results.append(el('p','','No place passes these necessary criteria.'));if(s.worst){const [c,count]=s.worst;results.append(el('p','',`${criterionText(c)} removes the most ${noun}: ${api.fmtNumber(count)}.`),button('Set this option to importance 5',()=>{const original=current.criteria.find(item=>item.id===c.id);if(original)Object.assign(original,normalizeCriterion({...original,importance:5}));edit();}));}}
    for(const r of rows.slice(0,showAll?rows.length:5)){
      const card=el('article','ak-result');card.dataset.area=(s.ctx.mode==='moon'?areas:marsAreas)[r.i].id;card.dataset.match=String(r.share);
      const position=(s.ctx.mode==='moon'?areas:marsAreas)[r.i];card.append(button(nameOf(r.i,s.ctx.mode),()=>openResult(r.i,s.ctx),'ak-result-open'),el('span','ak-match',`${r.share==null?'unknown':`${api.fmtNumber(r.share*100,1)}%`} match`),el('p','ak-metrics',`${s.ctx.mode==='moon'?api.fmtHours(r.hours):`Mars score: ${api.fmtNumber(r.score,4)}`} · ${api.fmtNumber(position.lat,2)}°, ${api.fmtNumber(position.lon,2)}°`));
      const detail=el('details','ak-result-detail'),marks=el('ul','ak-marks');detail.append(el('summary','','All options and dates'),el('p','ak-note',bestPeriods(r.i,s.ctx)));
      const priorities=s.active.slice().sort((a,b)=>importance(b)-importance(a));for(const [index,c] of priorities.entries()){const d=projectDefinition(byId.get(c.id),s.ctx),v=mark(c,r.i,s.ctx),text=`${v.word==='yes'?'✓':v.word==='unknown'?'?':v.word==='near'?'≈':'×'} ${v.word} · ${d.label} (${importance(c)}): ${displayValue(d,v.value)}`;if(index<3)card.append(el('p',`ak-result-option ak-${v.word}`,text));marks.append(el('li',`ak-mark ak-${v.word}`,`${text} · Wanted: ${criterionText(c,s.ctx)}`));}detail.append(marks);card.append(detail);results.append(card);
    }
    if(rows.length>5)results.append(button(showAll?'Show five':'Show all',()=>{showAll=!showAll;render();}));
    results.append(el('p','ak-note','The match compares the figures of this page with your criteria. It does not measure the ground.'),drawDestinations());
    if(missing.length)results.append(el('p','ak-note',`Files unavailable: ${unique(missing).join(', ')}. Their figures stay unknown.`));
    root.dataset.updateMs=String(performance.now()-start);
  }
  // Feedback on a request. It says what the page did not use. It never answers, never names a place and never sets a value.
  // "Show this option" opens the category (and "More options"), scrolls to the option and puts the focus on its importance control.
  function showOption(id){const d=projectDefinition(byId.get(id),context(current.criteria)),view=categoryViews.get(d?.group);if(!view)return;setCategoryOpen(view,true,false);if(!d.main&&view.more){view.more.buildOptions();view.more.open=true;}const box=[...view.panel.querySelectorAll('[data-criterion]')].find(node=>node.dataset.criterion===id),control=box&&[...box.querySelectorAll('.ak-importance input,.ak-toggle input')].find(node=>!node.closest('[hidden]'));if(!control){view.card.focus();return;}box.scrollIntoView({block:'center'});control.focus({preventScroll:true});}
  function feedbackLine(text,d){const line=el('p','',text);if(d){const b=button('Show this option',()=>showOption(d.id),'ak-feedback-button');b.setAttribute('aria-label',`Show this option: ${shortLabel(d)}`);line.append(' ',b);}return line;}
  // Low Sun is lunar data only, so a Mars site gets an example with cold and dry.
  function sayNotRequest(){feedback.replaceChildren(...['This field sets options only. It does not answer questions.','Write what the place must have.',context(current.criteria).mode==='mars'?'Example: bare ground, an airfield within 100 km, and a cold, dry place.':'Example: bare ground, an airfield within 100 km, and low Sun in August.'].map(text=>el('p','',text)));}
  function sayNoOption(){const names=el('div','ak-feedback-categories');for(const name of categoryViews.keys()){const b=button(name,()=>{const view=categoryViews.get(name);if(!view)return;setCategoryOpen(view,true,false);view.card.focus();},'ak-feedback-button');b.setAttribute('aria-label',`Open the category ${name}`);names.append(b);}feedback.replaceChildren(el('p','','The page found no option in this text.'),el('p','','Write what the place must have: the ground, climate, access, people, power or time of year.'),el('p','','Open a category:'),names);}
  // The vector match of the phrase (or of its clauses) counts from a score of 0.45. With no vector result, the best word match counts.
  function nearestOption(phrase,ctx,rankings){const vector=[phrase,...requestClauses(phrase)].map(part=>rankings.get(norm(part))?.[0]).filter(Boolean).sort((a,b)=>b.score-a.score)[0],id=vector?(vector.score>=0.52?vector.d.id:null):lexicalCandidates(contentWords(phrase).filter(word=>!FILLER_WORDS.test(word)).join(' '),ctx).find(match=>match.score>0)?.d.id,d=byId.get(id);return definitionAvailable(d,ctx)?projectDefinition(d,ctx):null;}
  function sayUnused(rankings){
    // interpret joins neighbouring unused words across commas: split at clause marks, so that each topic gets its own line ("1,000" stays whole).
    const ctx=context(current.criteria),phrases=(current.unused||[]).flatMap(phrase=>phrase.split(/[;:!?]|[,.](?!\d)/)).map(phrase=>phrase.replace(/^[\s,;:.!]+|[\s,;:.!]+$/g,'')).filter(phrase=>contentWords(phrase).some(word=>!FILLER_WORDS.test(word)));
    // A leftover of a clause that already set an option gets no line: its nearest option is set, or it holds an importance word and matches nothing.
    const isSet=d=>Boolean(d)&&current.criteria.some(c=>c.id===d.id&&importance(c)>0),leftover=phrase=>/\b(?:must|necessary|need|needs)\b/.test(norm(phrase));
    const lines=phrases.map(phrase=>{const topic=noDataTopic(phrase,ctx),d=topic?(definitionAvailable(byId.get(topic[1]),ctx)?projectDefinition(byId.get(topic[1]),ctx):null):nearestOption(phrase,ctx,rankings);return {phrase,topic,d};}).filter(line=>line.topic?true:line.d?!isSet(line.d):!leftover(line.phrase)),more=lines.length-4;
    for(const {phrase,topic,d} of lines.slice(0,4)){feedback.append(feedbackLine(`Not used: "${phrase}". ${topic?`${topic[0]} `:''}${d?`The nearest option is "${shortLabel(d)}", in the category "${d.group}".`:topic?'':'The page has no option for this phrase.'}`.trim(),d));}
    if(more>0)feedback.append(el('p','',`The page did not use ${more} more ${more===1?'phrase':'phrases'}.`));
  }
  // Kind 4: after the result shows, find the necessary option that removes the most areas. The board does not change.
  async function sayNothingPasses(token){
    const experiment=current,wait=()=>new Promise(resolve=>setTimeout(resolve,0)),live=()=>alive&&token===generation&&current===experiment;
    await wait();const ctx=context(current.criteria);if(ctx.mode==='mars')await ensureMarsSite(ctx.target);if(!live())return;
    const noun=ctx.mode==='moon'?'area':'square',s=search(current.criteria,undefined,true),necessary=s.active.filter(c=>importance(c)===10);if(s.passed||!necessary.length)return;
    const group=el('div','ak-feedback-group');group.append(el('p','',`No ${noun} passes all the necessary options.`));
    if(necessary.length<=6){
      let best=null;for(const c of necessary){await wait();if(!live())return;const passed=search(current.criteria.map(x=>x.id===c.id?{...x,importance:9}:x),undefined,true).passed;if(passed>(best?.passed||0))best={c,passed};}
      if(best){const d=projectDefinition(byId.get(best.c.id),ctx);group.append(el('p','',`If the option "${shortLabel(d)}" is not necessary, ${api.fmtNumber(best.passed)} ${best.passed===1?`${noun} passes`:`${noun}s pass`}. This is the highest count for one option.`),feedbackLine('Give it an importance of 9 or less, or change its value.',d));}
      else group.append(el('p','',`Two or more necessary options together remove all ${noun}s. Give two or more of them an importance of 9 or less.`));
    }
    if(live())feedback.append(group);
  }
  form.addEventListener('submit',event=>{
    event.preventDefault();cancelAIInterpretation(false);let token=++generation;const request=textarea.value.trim();feedback.replaceChildren();
    if(!request||!isOptionRequest(request)){bubbleResult='';drawBreakdown();sayNotRequest();return;}
    const baseline=structuredClone(current);bubbleUndo=baseline;bubbleUndoTiles=new Map([...tileDrafts].map(([id,control])=>[id,control.read()]));bubbleUndoBoard={pendingExtras:new Set(pendingExtras),more:new Map([...categoryViews].map(([name,view])=>[name,Boolean(view.more?.open)]))};
    // A request that names another base changes the base in save(): that change belongs to this request, so the feedback follows it.
    let applied=false;const rankings=new Map();
    const publishDraft=(draft,stage,seconds)=>{if(alive&&token===generation){applied=applyDraft(draft,baseline,stage,seconds)||applied;token=generation;}};
    const finish=()=>{if(!alive||token!==generation)return;if(!applied){sayNoOption();return;}sayUnused(rankings);sayNothingPasses(token);};
    if(aiOn)aiInterpret(request,{isCurrent:()=>alive&&token===generation,publishDraft,rankings}).then(finish);
    else{const start=performance.now(),draft=decorateDraft(interpret(request),request);publishDraft(draft,'rules',(performance.now()-start)/1000);finish();}
  });
  const rankCache=new Map(),summaryCache=new Map();
  function similarityColumns(target){
    if(rankCache.has(target))return rankCache.get(target);
    const ctx={target,mode:'moon',months:[],seasons:[]}, cols=[];
    const ranked=values=>{
      const ordered=values.map((v,i)=>({v,i})).filter(x=>finite(x.v)).sort((a,b)=>a.v-b.v),ranks=new Float32Array(api.areaCount).fill(NaN);
      for(let k=0;k<ordered.length;){let end=k+1;while(end<ordered.length&&ordered[end].v===ordered[k].v)end++;const rank=ordered.length>1?(k+end-1)/2/(ordered.length-1):0;for(let j=k;j<end;j++)ranks[ordered[j].i]=rank;k=end;}
      return ranks;
    };
    const attach=(id,label,group,read,unit='',categorical=false)=>{
      const values=areas.map((_,i)=>read(i)),ranks=ranked(values);let dateRanks;
      if(id==='best-period'){
        const yearDays=api.periods.at(-1).lastDay-api.periods[0].firstDay+1;
        const phases=values.map(v=>finite(v)?(api.periods[v].firstDay-api.periods[0].firstDay)/yearDays*Math.PI*2:null);
        dateRanks=[Math.sin,Math.cos].map(fn=>ranked(phases.map(v=>finite(v)?fn(v):null)));
      }
      cols.push({id,label,group,values,ranks,unit,categorical,dateRanks});
    };
    attach('hours','Low-Sun hours','Light',i=>api.hours(i,target,3,'year'),'hours');
    attach('best-period','Best ten-day period','Light',i=>{const p=periodValues(i,target);let best=null;for(let k=0;k<p.length;k++)if(finite(p[k])&&p[k]>0&&(best==null||p[k]>p[best]))best=k;return best;},'');
    const ids=['factor:median_slope','factor:p90_slope','factor:rough_90','factor:rough_270','factor:rough_810','bare','factor:rock_class','factor:permafrost_zone','temperature','snow','cloud','factor:wind_year','airfield'];
    for(const id of ids){const d=byId.get(id);if(!d)continue;attach(id,d.label,id==='airfield'?'Access':['temperature','snow','cloud','factor:wind_year'].includes(id)?'Climate':'Ground',i=>d.read(i,ctx),d.unit||'',Boolean(d.values));}
    if(tv&&tempLayout)for(const [kind,method] of [['Coldest month',Math.min],['Warmest month',Math.max]])attach(kind,`${kind}: mean air temperature`,'Climate',i=>{const vals=months.map(m=>tv.getInt8(i*months.length+m.value-1)).filter(v=>v!==tempLayout.unknown);return vals.length?method(...vals):null;},'degrees C');
    rankCache.set(target,cols);return cols;
  }
  function compare(i,target,selected){
    const cols=similarityColumns(target).filter(c=>selected.includes(c.group));if(!cols.length)return {matches:[],columns:0};
    const minShared=Math.max(Math.min(3,cols.length),Math.ceil(cols.length/2)),all=[];
    for(let j=0;j<areas.length;j++){if(j===i)continue;const km=distance(areas[i],areas[j]);if(km==null||km<sites.same_site_km)continue;let sum=0,count=0;
      for(const col of cols){const a=col.values[i],b=col.values[j];if(a==null||b==null||(!col.categorical&&(!finite(a)||!finite(b))))continue;const d=col.categorical?(a===b?0:1):col.dateRanks?mean(col.dateRanks.map(r=>Math.abs(r[i]-r[j]))):Math.abs(col.ranks[i]-col.ranks[j]);sum+=d;count++;}
      if(count>=minShared)all.push({i:j,km,distance:sum/count,shared:count});
    }
    all.sort((a,b)=>a.distance-b.distance||a.i-b.i);const chosen=[];for(const row of all){if(chosen.every(r=>distance(areas[r.i],areas[row.i])>=sites.same_site_km)){chosen.push(row);if(chosen.length===10)break;}}
    for(const row of chosen){row.factors=cols.flatMap(col=>{const a=col.values[i],b=col.values[row.i];if(a==null||b==null||(!col.categorical&&(!finite(a)||!finite(b))))return [];const d=col.categorical?(a===b?0:1):col.dateRanks?mean(col.dateRanks.map(r=>Math.abs(r[i]-r[row.i]))):Math.abs(col.ranks[i]-col.ranks[row.i]);return [{col,a,b,d}];}).sort((a,b)=>a.d-b.d);}
    return {matches:chosen,columns:cols.length,minShared};
  }
  const cardOff=api.addCardSection('ask-similar','Places like this one',(i,target)=>{
    const section=el('div','ak-similar'),checks=el('div','ak-checks'),output=el('div');let selected=['Light','Ground','Climate'],ran=false;const listenerCleanups=[];
    for(const group of ['Light','Ground','Climate','Access']){const l=el('label'),input=el('input');input.type='checkbox';input.checked=selected.includes(group);input.addEventListener('change',()=>{selected=[...checks.querySelectorAll('input:checked')].map(x=>x.value);draw();});input.value=group;l.append(input,document.createTextNode(` ${group}`));checks.append(l);}
    section.append(checks,output,el('p','ak-note','This compares the figures on this page. It does not measure how alike the ground is.'));
    const draw=()=>{if(!alive)return;ran=true;const start=performance.now(),result=compare(i,target,selected);section.dataset.elapsedMs=String(performance.now()-start);output.replaceChildren(el('p','ak-note',`Numbers use ranks among all areas. Dates use ranks around the year. Class words must agree. At least ${result.minShared??0} of ${result.columns} factors must be known in both areas.`),el('p','ak-note','Nearness is one minus the mean difference in ranks, shown as a percent. The year joins December to January.'));
      if(!result.matches.length)output.append(el('p','','No place has sufficient shared figures.'));
      const show=(col,v)=>col.id==='best-period'?api.periods[v]?.label??'unknown':typeof v==='number'?`${api.fmtNumber(v,2)}${col.unit?` ${col.unit}`:''}`:v;
      for(const r of result.matches){const article=el('article','ak-result');article.dataset.area=areas[r.i].id;article.append(button(nameOf(r.i),()=>api.openPlace(areas[r.i].id),'ak-result-open'),el('p','ak-metrics',`Near figures: ${api.fmtNumber((1-r.distance)*100,1)}% · ${api.fmtNumber(r.km)} km away · ${r.shared} shared factors`));
        const factorsList=el('ul','ak-factors');const alike=r.factors.slice(0,3),different=r.factors.slice().reverse().filter(x=>!alike.includes(x)).slice(0,2);
        for(const [label,items] of [['Most alike',alike],['Most different',different]])for(const f of items)factorsList.append(el('li','',`${label} · ${f.col.label}: here ${show(f.col,f.a)}; there ${show(f.col,f.b)}`));article.append(factorsList);output.append(article);
      }
      const first=result.matches[0],line=first?`Most alike: ${nameOf(first.i)}, ${api.fmtNumber(first.km)} km away`:'No place has sufficient shared figures.';summaryCache.set(`${i}:${target}`,line);
      const summary=section.closest('details')?.querySelector(':scope > summary');if(summary){const existing=summary.querySelector('.ak-summary')||summary.querySelector('span:last-child');if(existing)existing.textContent=line;else summary.append(el('span','ak-summary',line));}
    };
    // Card render runs while the outer fold is closed. Wait for its first open event.
    const observer=new MutationObserver(()=>{const fold=section.closest('details');if(!fold)return;observer.disconnect();const toggle=()=>{if(fold.open&&!ran)draw();};fold.addEventListener('toggle',toggle);listenerCleanups.push(()=>fold.removeEventListener('toggle',toggle));if(fold.open)draw();});observer.observe(document.documentElement,{childList:true,subtree:true});cleanups.push(()=>{observer.disconnect();listenerCleanups.forEach(fn=>fn());});
    return section;
  },(i,target)=>summaryCache.get(`${i}:${target}`)||'Open this part to compare Light, Ground and Climate.');if(typeof cardOff==='function')cleanups.push(cardOff);
  function restore(value){if(typeof value==='string'){try{value=JSON.parse(value);}catch{return false;}}if(!value||!Array.isArray(value.criteria)||typeof value.request!=='string')return false;
    const ctx=context(value.criteria),converted=value.criteria.map(c=>canonicalCriterion(c,ctx)).filter(Boolean),invalid=converted.filter(c=>!validCriterion(c));current={version:1,request:value.request,criteria:curatedCriteria(converted.filter(validCriterion).map(normalizeCriterion),ctx),unused:[...(Array.isArray(value.unused)?value.unused.filter(x=>typeof x==='string'):[]),...invalid.map(c=>`Rejected criterion: ${JSON.stringify(c)}`)],notes:Array.isArray(value.notes)?value.notes.filter(x=>typeof x==='string'):[],interpreter:typeof value.interpreter==='string'?value.interpreter:'Saved criteria'};textarea.value=current.request;drawBuilder();render();const state=api.getState();if(current.criteria.some(c=>c.id==='destination')&&(state.dest!==ctx.mode||state[ctx.mode==='moon'?'target':'msite']!==ctx.target))save(true);return true;}
  let previousDestination=`${api.getState().dest}:${api.getState().target}:${api.getState().msite}`;
  cleanups.push(api.onState(state=>{
    // The tour hook restores the retained board and its matches in this turn.
    // Do not rebuild an intermediate board before that snapshot is put back.
    if(tourSnapshotActive&&document.body.classList.contains('tl-tour-restoring'))return;
    const signature=JSON.stringify(state.ask),destination=`${state.dest}:${state.target}:${state.msite}`,changed=destination!==previousDestination,modeChanged=state.dest!==previousDestination.split(':')[0];previousDestination=destination;
    if(signature!==lastSaved){lastSaved=signature;feedback.replaceChildren();if(!restore(state.ask)){current=emptyExperiment();textarea.value='';drawBuilder();render();}}
    else if(changed&&current){generation++;cancelAIInterpretation(false);feedback.replaceChildren();const before=current.criteria.filter(c=>c.id!=='destination'),ctx=context([]);current.criteria=curatedCriteria(before,ctx,true);const removed=before.filter(c=>importance(c)>0).length-current.criteria.filter(c=>importance(c)>0).length,defaulted=current.criteria.filter(c=>c.baseDefault).length;if(modeChanged){openCategories.clear();pendingExtras.clear();}baseNotice.textContent=`${removed} ${removed===1?'option was':'options were'} put away because this base has no figures for ${removed===1?'it':'them'}.${defaulted?` ${defaulted} shared ${defaulted===1?'option uses':'options use'} a wanted value from this base.`:''}`;baseNotice.hidden=!modeChanged&&!removed&&!defaulted;bubbleUndo=null;bubbleUndoTiles=null;bubbleUndoBoard=null;changedOptions.clear();drawBuilder();render();save();}
  }));
  // Read each static field once. Later changes reuse these values and their ranks.
  for(const mode of ['moon','mars']){const ctx={target:mode==='moon'?api.targets[0].id:mars?.sites[0]?.id,mode,months:[],seasons:[]};for(const d of definitions)if(!dynamicIds.has(d.id)&&!d.id.startsWith('activity:')&&!d.id.startsWith('mars:'))column(d,ctx);}
  const boardMedia=matchMedia('(max-width: 600px)'),resizeBoard=()=>{drawBuilder();};boardMedia.addEventListener('change',resizeBoard);cleanups.push(()=>boardMedia.removeEventListener('change',resizeBoard));
  lastSaved=JSON.stringify(api.getState().ask);if(!restore(api.getState().ask)){current=emptyExperiment();drawBuilder();render();}
  // Tours reuse the module's actions. The snapshot is local and opaque: retaining
  // these nodes also retains accordion drafts and the callbacks which own them.
  const tourActions={
    applyPreset(id){return id==='rover-camera'&&applyPreset(0);},
    openDestinations(){const fold=results.querySelector('.ak-destinations');if(!alive||!fold)return null;fold.open=true;return fold;},
    snapshot(){
      tourSnapshotActive=true;
      const saved={current,criteria:current.criteria.slice(),openCategories:new Set(openCategories),categoryViews:new Map(categoryViews),pendingExtras:new Set(pendingExtras),baseNotice:{text:baseNotice.textContent,hidden:baseNotice.hidden},showAll,lastSearch,rows,builderUpdates,waitingSite,bubbleUndo,bubbleUndoTiles,bubbleUndoBoard,tileDrafts:new Map(tileDrafts),bubbleResult,changedOptions:new Set(changedOptions),
        nodes:[categories,breakdown,feedback,results,status].map(host=>({host,children:[...host.childNodes]})),
        count:builderCount.textContent,draft:textarea.value,selection:[textarea.selectionStart,textarea.selectionEnd,textarea.selectionDirection],
        draftScroll:textarea.scrollTop,aiText:aiState.textContent};
      // Keep the saved controls untouched while a preset updates the tour board.
      drawBuilder();
      // An unfinished interpretation must not replace the tour's criteria later.
      generation++;for(const controller of aborters)controller.abort();findButton.disabled=false;aiCancel.hidden=true;
      return saved;
    },
    restore(saved){
      if(!alive||!saved)return;tourSnapshotActive=false;generation++;renderRequest++;
      current=saved.current;current.criteria=saved.criteria;openCategories=saved.openCategories;categoryViews.clear();for(const [name,view] of saved.categoryViews)categoryViews.set(name,view);pendingExtras=saved.pendingExtras;baseNotice.textContent=saved.baseNotice.text;baseNotice.hidden=saved.baseNotice.hidden;showAll=saved.showAll;bubbleUndo=saved.bubbleUndo;bubbleUndoTiles=saved.bubbleUndoTiles;bubbleUndoBoard=saved.bubbleUndoBoard;tileDrafts.clear();for(const [id,control] of saved.tileDrafts)tileDrafts.set(id,control);bubbleResult=saved.bubbleResult;changedOptions=saved.changedOptions||new Set();clearTimeout(changeTimer);if(changedOptions.size)changeTimer=setTimeout(()=>{changedOptions.clear();for(const node of categories.querySelectorAll('.ak-changed'))node.classList.remove('ak-changed');},5000);
      lastSearch=saved.lastSearch;rows=saved.rows;builderUpdates=saved.builderUpdates;
      for(const {host,children} of saved.nodes)host.replaceChildren(...children);
      for(const fold of results.querySelectorAll('.ak-destinations[open]'))fold.dispatchEvent(new Event('toggle'));
      builderCount.textContent=saved.count;textarea.value=saved.draft;textarea.setSelectionRange(...saved.selection);textarea.scrollTop=saved.draftScroll;
      aiState.textContent=saved.aiText;findButton.disabled=false;aiCancel.hidden=true;
      const state=api.getState();lastSaved=JSON.stringify(state.ask);previousDestination=`${state.dest}:${state.target}:${state.msite}`;
      if(saved.waitingSite){waitingSite=saved.waitingSite;drawBuilder();render();return;}waitingSite=null;
      publishMatches(lastSearch);
    },
  };
  root.tourActions=tourActions;
  return {destroy(){alive=false;generation++;clearTimeout(changeTimer);if(root.tourActions===tourActions)delete root.tourActions;for(const c of aborters)c.abort();for(const off of cleanups)if(typeof off==='function')off();api.setMatches?.(null);for(const host of [root,wordsRoot,resultsRoot].filter(Boolean)){host.replaceChildren();host.classList.remove('ak-module');}}};
}
