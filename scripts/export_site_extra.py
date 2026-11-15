#!/usr/bin/env python3
"""Pack the local power and steady-influence inputs for the static page.

Run with python3 scripts/export_site_extra.py. Uses the standard library only.
No source is fetched. Missing source files are listed in the output manifest.
"""

import hashlib
import json
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site" / "data"
SOURCES = {
    "power": "power_cells.json",
    "steady": "steady_effects_cells.json",
    "tremors": "tremors_cells.json",
}
FORMATS = {"u8": ("B", 1, 255), "u16": ("H", 2, 65535),
           "u32": ("I", 4, 4294967295), "f32": ("f", 4, "NaN")}
META_KEYS = {
    "power": ("what", "rough_estimate", "rules_in_words", "rules", "classes",
              "null_rule", "what_it_is", "what_it_is_not", "clear_sky_low_sun_table",
              "low_sun_sentence", "moon_and_mars", "notes_from_the_sanity_look",
              "sunlight_blocks_missing", "wind_50m_blocks_missing", "fields", "counts"),
    "steady": ("place_point", "what_this_is", "rule_of_thumb", "rules_in_plain_words",
               "rules", "rules_left_out_here", "fields", "null_rule", "distance",
               "roads_accuracy", "search"),
    "tremors": ("what", "years", "magnitude_range", "rule_of_thumb", "fields",
                "what_it_is_not", "edge_note", "grid_index"),
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def public_words(value):
    """Keep the supplied rules, with personal scientific-author names omitted."""
    if isinstance(value, dict):
        return {key: public_words(item) for key, item in value.items()}
    if isinstance(value, list):
        return [public_words(item) for item in value]
    if not isinstance(value, str):
        return value
    # The handoff forbids personal names. Dates, formulas and publications stay.
    value = re.sub(r"[A-Z][a-z]+ and [A-Z][a-z]+ \((\d{4})\)",
                   lambda match: "the cited " + match[1] + " study", value)
    value = re.sub(r"[A-Z][a-z]+ et al\. (\d{4})",
                   lambda match: "the cited " + match[1] + " study", value)
    return value


def leaf_paths(value, prefix, paths):
    if isinstance(value, dict):
        for key, item in value.items():
            leaf_paths(item, prefix + "." + key, paths)
    elif value is not None:
        paths.add(prefix)


def follow(value, path):
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def uint_type(largest):
    for name in ("u8", "u16", "u32"):
        if largest < FORMATS[name][2]:
            return name
    return "f32"


def numeric_type(values):
    known = [item for item in values if item is not None]
    if known and all(item >= 0 and float(item).is_integer() for item in known):
        return uint_type(max(known))
    return "f32"


def binary_values(values, kind):
    code, _, unknown = FORMATS[kind]
    blank = float("nan") if kind == "f32" else unknown
    clean = [blank if value is None else value for value in values]
    if kind != "f32":
        clean = [int(value) for value in clean]
    return struct.pack("<" + str(len(clean)) + code, *clean)


def main():
    cells = json.loads((OUTPUT / "cells.json").read_text())
    ids = cells["ids"]
    inputs, missing, paths = {}, [], set()
    for group, filename in SOURCES.items():
        source = ROOT / "data" / "derived" / filename
        if not source.is_file():
            missing.append(filename)
            continue
        inputs[group] = json.loads(source.read_text())
        for area in inputs[group]["cells"].values():
            leaf_paths(area, group, paths)

    columns = {}
    for path in sorted(paths):
        group, *keys = path.split(".")
        columns[path] = [follow(inputs[group]["cells"].get(area), keys) for area in ids]

    names = sorted({value for key, values in columns.items() if key.endswith(".name")
                    for value in values if isinstance(value, str)})
    name_ids = {name: index for index, name in enumerate(names)}
    # One shared lookup also replaces names embedded in explanatory strings.
    names_pattern = re.compile("|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))) if names else None

    def tokenize(value):
        if isinstance(value, list):
            return [tokenize(item) for item in value]
        if isinstance(value, str) and names_pattern:
            return names_pattern.sub(lambda match: "{@n:" + str(name_ids[match[0]]) + "}", value)
        return value

    data = {
        "version": 1,
        "area_count": len(ids),
        "area_order": "The exact order of ids in cells.json.",
        "ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
        "binary": "extra.bin",
        "binary_bytes": 0,
        "layout": {
            "byte_order": "little endian",
            "address": "offset + (area_index * width + item_index) * bytes_per_value",
            "columns": "Each field has one contiguous column, padded to its type alignment.",
            "types": {kind: {"bytes_per_value": spec[1], "unknown": spec[2]} for kind, spec in FORMATS.items()},
            "unknown": "Unknown integers use their type maximum. Unknown float32 values are NaN. Zero is always known.",
            "lookup": "A values array or named lookup maps stored indexes to values. Index zero is valid.",
            "names": "Entity names occur once in lookups.names. Text token {@n:index} refers to that name.",
            "arrays": "Width greater than one is an array. A lookup may also return an array; retain its empty or null members.",
            "precision": "Integers and lookup values are exact. Float32 columns keep source precision to normal float32 rounding.",
        },
        "fields": {},
        "lookups": {"names": names},
        "meta": {},
        "metadata_note": "Rules, caveats and comparison lines retain the source words except personal scientific-author names, omitted as required.",
        "missing_inputs": missing,
        "coverage": {},
    }
    for group, source in inputs.items():
        data["meta"][group] = public_words({key: source["meta"][key] for key in META_KEYS[group] if key in source["meta"]})
        if group == "power":
            rules = data["meta"][group].get("rules", {})
            formula_keys = [key for key, rule in rules.items()
                            if isinstance(rule, dict) and rule.get("unit") in
                            {"a, b (degrees), c", "base, exponent"}]
            for key in formula_keys:
                replacement = "air_mass" if rules[key]["unit"] == "a, b (degrees), c" else "direct_beam"
                rules[replacement] = rules.pop(key)
        data["coverage"][group] = {
            "areas_present": sum(area in source["cells"] for area in ids),
            "areas_missing": sum(area not in source["cells"] for area in ids),
        }

    packed = bytearray()
    for path, values in columns.items():
        known = [value for value in values if value is not None]
        descriptor = {"width": 1, "unknown_areas": len(values) - len(known)}
        if path.endswith(".name"):
            kind = uint_type(len(names) - 1)
            content = binary_values([name_ids.get(value) for value in values], kind)
            descriptor["lookup"] = "names"
        else:
            dictionary, dictionary_ids, indexes = [], {}, []
            for value in values:
                if value is None:
                    indexes.append(None)
                    continue
                key = compact(value)
                if key not in dictionary_ids:
                    dictionary_ids[key] = len(dictionary)
                    dictionary.append(tokenize(value))
                indexes.append(dictionary_ids[key])
            kind = uint_type(len(dictionary) - 1)
            content = binary_values(indexes, kind)
            descriptor["values"] = dictionary
            dictionary_bytes = len(content) + len(compact(dictionary).encode())
            direct = None
            if known and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in known):
                direct = (values, 1)
            elif known and all(isinstance(value, list) and len(value) == len(known[0])
                               and all(item is None or isinstance(item, (int, float)) for item in value) for value in known):
                width = len(known[0])
                if width:
                    direct = ([item for value in values for item in (value if value is not None else [None] * width)], width)
            if direct:
                direct_values, width = direct
                direct_kind = numeric_type(direct_values)
                direct_content = binary_values(direct_values, direct_kind)
                if len(direct_content) < dictionary_bytes:
                    kind, content = direct_kind, direct_content
                    descriptor.pop("values")
                    descriptor["width"] = width
        alignment = FORMATS[kind][1]
        packed.extend(b"\0" * (-len(packed) % alignment))
        descriptor.update(offset=len(packed), type=kind, unknown=FORMATS[kind][2])
        if path == "power.wind.ws50m_ms":
            words = inputs["power"]["meta"].get("what_it_is", {}).get("wind", "")
            height = re.search(r"Mean wind speed (\d+(?:\.\d+)?) m above", words)
            descriptor["height_m"] = float(height[1]) if height else None
        packed.extend(content)
        data["fields"][path] = descriptor

    data["binary_bytes"] = len(packed)
    metadata = (compact(data) + "\n").encode()
    # A compressed copy (<name>.gz, scripts/compress_site_data.py) replaces its plain file on the page; it is not
    # more data, thus the limit does not count it.
    companions = sum(path.stat().st_size for path in OUTPUT.glob("extra*")
                     if path.is_file() and path.name not in {"extra.json", "extra.bin"} and not path.name.endswith(".gz"))
    total = len(metadata) + len(packed) + companions
    if total >= 6_000_000:
        raise SystemExit(f"Extra data would exceed the limit: {total:,} bytes")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "extra.json").write_bytes(metadata)
    (OUTPUT / "extra.bin").write_bytes(packed)
    print(f"Exported {len(ids):,} areas, {len(data['fields'])} columns, {len(names)} shared names.")
    print(f"extra.json: {len(metadata):,} bytes; extra.bin: {len(packed):,} bytes.")
    print(f"All extra data: {total:,} bytes. Missing inputs: {', '.join(missing) or 'none'}.")


if __name__ == "__main__":
    main()
