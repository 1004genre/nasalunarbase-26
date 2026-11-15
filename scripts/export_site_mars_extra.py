#!/usr/bin/env python3
"""Pack Mars card context from local derived files, using only the standard library."""

import json
import math
import struct
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / 'data' / 'derived'
DESTINATION = ROOT / 'site' / 'data'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from twinfinder import estimates  # noqa: E402  (standard library only: the sentence on lunar hydrogen)

# The limit of the two files together (mars_extra.json and mars_extra.bin). The first limit was 5,000,000 bytes.
# The Mars copy with 57 Mars sites gave 4,983,002 bytes. The joined build of 15 November 2026 adds the planet
# factors of the 16 lunar regions (manifest "planet_factors") and gives 5,041,570 bytes, thus the export stopped at
# the first limit. The limit is now 5,500,000 bytes, approximately 9 % above the joined build.
# The page loads mars_extra.json.gz first (scripts/compress_site_data.py).
SIZE_LIMIT_BYTES = 5_500_000

# These are source field names, not scientific values or classification rules.
FIELDS = {
    'mars_environment': '''
        sun_kwh_m2_day_year uv_index_year uv_index_brightest_hour_max
        clear_days_year clearness_index_year aod_550_year
        sun_clear_sky_kwh_m2_day_year
    ''',
    'mars_power': '''
        solar.class solar.sun_kwh_m2_day_year solar.panel_kwh_per_kw_day_year
        solar.panel_best_month solar.months_without_sun
        wind.class wind.class_1_to_7 wind.ws50m_ms_year wind.ws10m_ms_year
        wind.power_w_m2 wind.air_density_kg_m3
        geothermal.class geothermal.plant.name geothermal.plant.km
        geothermal.plant.mw geothermal.plants_within_150_km
        geothermal.plant_mw_within_150_km
        geothermal.volcano_since_1990.name geothermal.volcano_since_1990.km
        geothermal.volcano_since_1990.last_eruption_year
        geothermal.holocene_volcano.name geothermal.holocene_volcano.km
        geothermal.holocene_volcano.last_eruption_year
    ''',
    'mars_power_extra': '''
        t2m_range_c_year albedo_year soil_wetness_top_year
        soil_wetness_ice_flag wind_10m_ms_year
    ''',
    'mars_rock_frozen': '''
        rock.class_code rock.class rock.volcanic rock.basic_volcanic
        rock.loose_sediment rock.box rock.coarse
        permafrost.prob_mean permafrost.zone permafrost.note
    ''',
    'mars_ground': '''
        median_slope_deg p90_slope_deg relief_m relief_class slope_pixels why_null
    ''',
    'mars_hazards_people': '''
        quakes_m5_200km.count quakes_m5_200km.largest_mag
        quakes_m5_200km.nearest_km quakes_m5_200km.latest_date
        volcano.name volcano.km volcano.last_eruption_year
        people.nearest.name people.nearest.km people.nearest.population
        people.population_within_100km people.settlements_within_100km
        people.settlements_without_population_within_100km
    ''',
    'mars_steady_effects': '''
        volcanic.class volcanic.effects volcanic.decided_by
        volcanic.nearest_erupted_since_1990.name
        volcanic.nearest_erupted_since_1990.km
        volcanic.nearest_erupted_since_1990.years_erupting_since_1990
        volcanic.nearest_erupted_since_1990.last_eruption_year
        volcanic.nearest_holocene.name volcanic.nearest_holocene.km
        volcanic.young_volcanic_ground volcanic.young_volcanic_ground_why
        human.class human.effects human.why
        human.nearest_settlement.name human.nearest_settlement.km
        human.nearest_settlement.population
        human.nearest_settlement_1000_or_more.name
        human.nearest_settlement_1000_or_more.km
        human.nearest_settlement_1000_or_more.population
        human.population_within_25km human.settlements_within_25km
        human.settlements_without_population_within_25km
        human.nearest_main_road_or_railway.kind
        human.nearest_main_road_or_railway.km
        human.nearest_main_road_or_railway.none_within_km
        human.nearest_airfield.name human.nearest_airfield.km
        human.nearest_airfield_with_scheduled_flights.name
        human.nearest_airfield_with_scheduled_flights.km
        human.help_within_reach human.help_within_reach_why
        small_tremors.class small_tremors.source small_tremors.source_words
        small_tremors.catalogue_verdict small_tremors.catalogue_status
        small_tremors.our_estimate small_tremors.our_estimate_why
        small_tremors.m5_quakes_200km_since_1990 small_tremors.glacier_ice_share
    ''',
    'mars_tremors': '''
        small_per_year_50km small_per_year_100km years_with_events_100km
        median_magnitude_100km largest_small_magnitude_100km
        nearest_small_event_km share_not_earthquake_100km
        events_500km_for_floor detection_floor floor_check status verdict
        catalogued_anyway_100km.events catalogued_anyway_100km.years
        catalogued_anyway_100km.smallest_magnitude
    ''',
    'mars_estimates': '''
        rockiness.estimate rockiness.figures.bare rockiness.figures.p90_slope_deg
        rockiness.figures.loose_sediment
        heat_response.estimate heat_response.figures.index_per_c
        heat_response.figures.one_minus_albedo heat_response.figures.t2m_range_c
        mineral_family.estimate mineral_family.figures.rock_class_code
        mineral_family.figures.anorthosite_body
        topsoil_water.estimate topsoil_water.ground_ice
        topsoil_water.figures.soil_wetness topsoil_water.figures.ice_flag
        topsoil_water.figures.permafrost_prob_mean
        topsoil_water.figures.ground_ice_basis
        frozen_ground_depth.estimate frozen_ground_depth.metres
        frozen_ground_depth.figures.permafrost_zone frozen_ground_depth.figures.basis
        sand_dust.estimate sand_dust.figures.loose_sediment sand_dust.figures.bare
        sand_dust.figures.topsoil sand_dust.figures.wind_10m_ms sand_dust.figures.frozen
        ilmenite.estimate ilmenite.figures.rock_class_code
        ilmenite.figures.anorthosite_body
    ''',
}

# The month names and scientific values are read from the source files.
MONTHLY_PEAKS = {
    'sun_kwh_m2_day': ('sun_best_month', 'sun_best_month_kwh_m2_day'),
    'uv_index': ('uv_best_month', 'uv_best_month_index'),
    'uv_index_brightest_hour': ('uv_brightest_hour_month', 'uv_brightest_hour_max'),
}

INTEGER_TYPES = (
    ('uint8', 'B', 0, 255),
    ('int8', 'b', -128, 127),
    ('uint16', 'H', 0, 65535),
    ('int16', 'h', -32768, 32767),
    ('uint32', 'I', 0, 4294967295),
    ('int32', 'i', -2147483648, 2147483647),
)


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def read(path):
    with path.open(encoding='utf-8') as source:
        return json.load(source)


def field(record, path):
    for part in path.split('.'):
        if not isinstance(record, dict):
            return None
        record = record.get(part)
    return record


def finite_number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def integer_encoding(values):
    low, high = min(values, default=0), max(values, default=0)
    for name, code, minimum, maximum in INTEGER_TYPES:
        unknown = maximum if minimum == 0 else minimum
        if low >= minimum and high <= maximum and not low <= unknown <= high:
            return name, code, unknown
    return None


def pack_column(values, offset):
    """Keep source decimal precision; distinguish unknown from every known value."""
    known = [value for value in values if value is not None]
    if all(finite_number(value) for value in known):
        digits = max((max(0, -Decimal(str(value)).as_tuple().exponent) for value in known), default=0)
        scale = 10 ** digits
        scaled = [int(Decimal(str(value)) * scale) for value in known]
        encoding = integer_encoding(scaled)
        if encoding:
            name, code, unknown = encoding
            packed = [unknown if value is None else int(Decimal(str(value)) * scale) for value in values]
            descriptor = {'type': name, 'scale': scale, 'unknown': unknown, 'offset': offset}
        else:
            name, code, unknown = 'float64', 'd', -1.7976931348623157e308
            if unknown in known:
                raise ValueError('A source value collides with the reserved unknown value.')
            packed = [unknown if value is None else value for value in values]
            descriptor = {'type': name, 'scale': 1, 'unknown': unknown, 'offset': offset}
    else:
        lookup, index_by_value, packed = [], {}, []
        for value in values:
            if value is None:
                packed.append(None)
                continue
            key = compact(value)
            if key not in index_by_value:
                index_by_value[key] = len(lookup)
                lookup.append(value)
            packed.append(index_by_value[key])
        name, code, unknown = integer_encoding(range(len(lookup)))
        packed = [unknown if value is None else value for value in packed]
        descriptor = {'type': name, 'scale': 1, 'unknown': unknown, 'offset': offset, 'lookup': lookup}
    descriptor['bytes_per_value'] = struct.calcsize('<' + code)
    descriptor['unknown_count'] = len(values) - len(known)
    return descriptor, struct.pack('<' + str(len(packed)) + code, *packed)


def main():
    base = read(DESTINATION / 'mars.json')
    ids = base['squares']['ids']
    if len(ids) != base['squares']['count'] or len(set(ids)) != len(ids):
        raise ValueError('The base manifest has an inconsistent square order.')
    months = base['squares']['months']
    manifest = {
        'meta': {
            'what': 'Display context for the Mars first pass; these extra figures do not change any score.',
            'order': 'Every column follows squares.ids, copied in order from mars.json squares.ids.',
            'layout': [
                'Column-major data, little-endian, without a header or padding.',
                'For row i, read type at offset + i * bytes_per_value.',
                'The reserved unknown value means null and is never zero.',
                'For numeric columns, divide the stored integer by scale.',
                'For lookup columns, the stored integer indexes lookup; its JSON value is returned unchanged.',
                'Lookup entries may be names, booleans, lists, or small records.',
                'Field paths start with the input filename stem; dots describe nested object keys.',
                'Numeric values retain the precision held in the inputs; the page controls their displayed precision.',
            ],
            'monthly_peak_rule': [
                'Best month means the month with the highest known monthly value, not the safest UV exposure.',
                'Ties keep calendar order; all months unknown gives an unknown month and value.',
                'Month names come from mars.json squares.months.',
            ],
            'monthly_peak_fields': MONTHLY_PEAKS,
            'input_meta': 'The input_meta object copies every input meta block without changing any value.',
            'omitted': 'Monthly arrays and figures unused by the cards are omitted; their definitions remain in input_meta.',
        },
        'missing_inputs': [],
        'inputs': {},
        'input_meta': {},
        'squares': {'file': 'mars_extra.bin', 'count': len(ids), 'ids': ids, 'columns': {}},
    }
    binary = bytearray()
    for stem, fields in FIELDS.items():
        path = DERIVED / (stem + '.json')
        if not path.is_file():
            manifest['missing_inputs'].append(path.name)
            print('Missing input: ' + path.name + '; its columns are omitted.')
            continue
        source = read(path)
        manifest['input_meta'][stem] = source['meta']
        cells = source['cells']
        missing = sum(square_id not in cells for square_id in ids)
        manifest['inputs'][stem] = {'file': path.name, 'missing_squares': missing}
        columns = {name: [field(cells.get(square_id), name) for square_id in ids] for name in fields.split()}
        if stem == 'mars_environment':
            for source_name, (month_name, value_name) in MONTHLY_PEAKS.items():
                peak_months, peak_values = [], []
                for square_id in ids:
                    values = field(cells.get(square_id), source_name)
                    available = [(index, value) for index, value in enumerate(values or []) if finite_number(value)]
                    if available:
                        month_index, value = max(available, key=lambda pair: pair[1])
                        peak_months.append(months[month_index])
                        peak_values.append(value)
                    else:
                        peak_months.append(None)
                        peak_values.append(None)
                columns[month_name] = peak_months
                columns[value_name] = peak_values
        for name, values in columns.items():
            descriptor, packed = pack_column(values, len(binary))
            manifest['squares']['columns'][stem + '.' + name] = descriptor
            binary.extend(packed)
    planet_path = DERIVED / 'planet_factors.json'
    if planet_path.is_file():
        planet = read(planet_path)
        manifest['input_meta']['planet_factors'] = planet['meta']
        manifest['planet_factors'] = planet
        manifest['inputs']['planet_factors'] = {'file': planet_path.name}
        # The sentence on lunar hydrogen takes the count of lunar regions and the range from planet_factors.json,
        # also if mars_estimates.json is older than that file.
        stored = manifest['input_meta'].get('mars_estimates')
        if isinstance(stored, dict) and 'water_sentence' in stored:
            sentence = estimates.water_sentence(planet)
            if stored['water_sentence'] != sentence:
                stored['water_sentence'] = sentence
                manifest['meta']['input_meta'] = (
                    'The input_meta object copies every input meta block without changing any value, except '
                    'mars_estimates.water_sentence. This script makes that sentence again from planet_factors.json.')
    else:
        manifest['missing_inputs'].append(planet_path.name)
        print('Missing input: ' + planet_path.name + '; planet-only figures are omitted.')
    manifest['squares']['byte_length'] = len(binary)
    output = (compact(manifest) + '\n').encode('utf-8')
    total = len(output) + len(binary)
    if total >= SIZE_LIMIT_BYTES:
        raise ValueError(f'Extra data would exceed the limit of {SIZE_LIMIT_BYTES:,} bytes; no files were written.')
    (DESTINATION / 'mars_extra.bin').write_bytes(binary)
    (DESTINATION / 'mars_extra.json').write_bytes(output)
    print(f'Exported {len(ids):,} squares and {len(manifest["squares"]["columns"])} columns.')
    print(f'mars_extra.json: {len(output):,} bytes; mars_extra.bin: {len(binary):,} bytes; total: {total:,} bytes.')
    print('Missing inputs: ' + (', '.join(manifest['missing_inputs']) or 'none') + '.')


if __name__ == '__main__':
    main()
