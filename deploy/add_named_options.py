# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Put back experiment conditions that the board lost, each with a name and a category.

    python3 deploy/add_named_options.py <folder of the page>

The board (ask.js) shows only options that have a name for a visitor. Two data files, extra.json and
mars_extra.json, hold fields with file names only, and the board left all of them out. Most are names,
codes or copies. Some are real conditions of an experiment: this script gives those a name, a unit and
a category, and the board then shows them. It also gives each Mars category a main option.
To run the script again changes nothing.
"""
import sys
from pathlib import Path

MARK = "// Named options: added by deploy/add_named_options.py."

TABLE = MARK + r"""
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
"""

POWER_ROWS = """    ['named:solar_panel_yield','Solar panel yield, yearly mean','Power','small','solar'],
    ['named:months_without_sun','Months without Sun','Power','small','sun'],
    ['named:wind_50m','Wind speed at 50 m, yearly mean','Power','small','wind'],
    ['named:wind_power','Wind power at 50 m','Power','small','turbine'],
    ['named:geothermal_plant_km','Distance to a geothermal power plant','Power','small','spring'],
"""
MOON_ANCHOR = "    ['factor:geothermal_class','Geothermal power','Power','small','spring'],\n"
MARS_ANCHOR = "    ['hemisphere','Hemisphere','Region','small','compass'],\n  ],\n};"
MARS_ROWS = """    ['month','Month','Time of year','small','calendar'],
    ['airfield','Distance to an airfield','Access','medium','plane'],
    ['factor:help_within_reach','Help within reach','Access','small','people'],
    ['factor:solar_class','Solar power','Power','small','solar'],
    ['factor:wind_class','Wind power','Power','small','turbine'],
    ['factor:geothermal_class','Geothermal power','Power','small','spring'],
""" + POWER_ROWS
TABLE_ANCHOR = "const TILE_DESIGN = "
GROUPS_OLD = "['Activity', 'Light', 'Time of year', 'Likeness to the site', 'Ground',"
GROUPS_NEW = "['Activity', 'Light', 'Likeness to the site', 'Time of year', 'Ground',"
LOOP_ANCHOR = "    for(const path of Object.keys(fields||{}))omittedFields.push(`${name}:${path}`);\n"
BLOCK = r"""  // Named options: read the two files again and add each field of NAMED_OPTIONS that the data has.
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
"""


def once(text: str, anchor: str) -> None:
    if text.count(anchor) != 1:
        raise SystemExit(f"add_named_options: STOP. ask.js has {text.count(anchor)} x this anchor, not 1: {anchor[:70]!r}")


def main() -> None:
    path = Path(sys.argv[1]) / "ask.js"
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        print("add_named_options: the options are there already")
        return
    for anchor in (MOON_ANCHOR, MARS_ANCHOR, TABLE_ANCHOR, GROUPS_OLD, LOOP_ANCHOR):
        once(text, anchor)
    text = text.replace(GROUPS_OLD, GROUPS_NEW)
    text = text.replace(MARS_ANCHOR, MARS_ROWS + MARS_ANCHOR)          # the Mars list first: it gains a second geothermal row
    first = text.index(MOON_ANCHOR)                                     # the first one is in the Moon list
    text = text[:first] + MOON_ANCHOR + POWER_ROWS + text[first + len(MOON_ANCHOR):]
    text = text.replace(TABLE_ANCHOR, TABLE + TABLE_ANCHOR)
    text = text.replace(LOOP_ANCHOR, LOOP_ANCHOR + BLOCK)
    path.write_text(text, encoding="utf-8")
    print("add_named_options: added 15 named options, 5 of them main options of Power, and main options for each Mars category")


if __name__ == "__main__":
    main()
