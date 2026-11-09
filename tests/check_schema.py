#!/usr/bin/env python3
"""check_schema.py — every column eic2ai writes is documented on the website's CSV Schema page.

Usage:
  tests/check_schema.py                     reads tests/columns.txt (the committed `eic2ai --list-columns` output)
  tests/check_schema.py --eic2ai BIN        reads `BIN --list-columns`
  tests/check_schema.py --headers FILE      reads a saved `--list-columns` output
  --schema FILE                             the schema (default: website/ai-epic-background/csv-schema.yaml)

The schema file is the hand-edited source of https://sroai.github.io/ai-epic-background/csv-schema, in the
`website` submodule. For every output file eic2ai writes (a role, or role_suffix for extra outputs) this
checks that the schema lists the same columns in the same order, each with a description; that `keys`,
`links` and `prefixes` name real columns and files; and that `layout` places every file exactly once.
PyYAML is the one dependency (`pip install pyyaml`; the eic_xl image has it).
Exit code 1 on any mismatch, with what to add, remove or move.
"""
import argparse
import pathlib
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent


def read_headers(text):
    """`role: a,b,c` lines → {role: [a, b, c]}."""
    headers = {}
    for line in text.splitlines():
        if ": " in line:
            role, header = line.split(": ", 1)
            headers[role] = header.split(",")
    return headers


def compare_columns(name, written, documented):
    """Problems of one output file: missing, extra, out-of-order or undescribed columns."""
    problems = []
    missing = [column for column in written if column not in documented]
    extra = [column for column in documented if column not in written]
    for column in missing:
        before = written[written.index(column) - 1] if written.index(column) > 0 else None
        where = f"after {before}" if before else "first"
        problems.append(f"{name}: add column {column} ({where})")
    for column in extra:
        problems.append(f"{name}: remove column {column} (eic2ai does not write it)")
    common_written = [column for column in written if column in documented]
    common_documented = [column for column in documented if column in written]
    if common_written != common_documented:
        first = next(i for i, (a, b) in enumerate(zip(common_written, common_documented)) if a != b)
        problems.append(f"{name}: column order differs from eic2ai's from {common_documented[first]} on; "
                        f"eic2ai writes {', '.join(common_written[first:first + 4])}, …")
    for column, description in documented.items():
        if column in written and not str(description or "").strip():
            problems.append(f"{name}: column {column} has no description")
    return problems


def check_references(files, layout, layout_titles):
    """Problems in keys, links, prefixes, layout and lane_titles."""
    problems = []
    for name, entry in files.items():
        columns = entry.get("columns") or {}
        for key in entry.get("keys") or []:
            if key not in columns:
                problems.append(f"{name}: keys lists {key}, which is not a column")
        for column, target in (entry.get("links") or {}).items():
            if column not in columns:
                problems.append(f"{name}: links lists {column}, which is not a column")
            target_file, _, target_column = str(target).partition(".")
            if target_file not in files or target_column not in (files[target_file].get("columns") or {}):
                problems.append(f"{name}: link {column} → {target} names no documented file.column")
        for prefix in entry.get("prefixes") or {}:
            if not any(column.startswith(prefix + "_") for column in columns):
                problems.append(f"{name}: prefix {prefix} starts no column")
        for field in ("row", "needs"):
            if not str(entry.get(field) or "").strip():
                problems.append(f"{name}: {field} is empty")
    placed = [name for lane in (layout or {}).values() for name in lane]
    for name in files:
        if placed.count(name) != 1:
            problems.append(f"layout: {name} is placed {placed.count(name)} times (needs exactly once)")
    for name in placed:
        if name not in files:
            problems.append(f"layout: {name} is not a documented file")
    for lane in (layout_titles or {}):
        if lane not in (layout or {}):
            problems.append(f"lane_titles: {lane} is not a lane of layout")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eic2ai")
    parser.add_argument("--headers", default=str(REPO / "tests" / "columns.txt"))
    parser.add_argument("--schema", default=str(REPO / "website" / "ai-epic-background" / "csv-schema.yaml"))
    args = parser.parse_args()

    if args.eic2ai:
        text = subprocess.run([args.eic2ai, "--list-columns"], capture_output=True, text=True, check=True).stdout
        source = f"{args.eic2ai} --list-columns"
    else:
        text = open(args.headers).read()
        source = args.headers
    headers = read_headers(text)
    schema_path = pathlib.Path(args.schema)
    if not schema_path.exists():
        sys.exit(f"{schema_path} not found; run `git submodule update --init website`")
    schema = yaml.safe_load(schema_path.read_text())
    files = schema.get("files") or {}

    problems = []
    for name, written in headers.items():
        if name not in files:
            problems.append(f"{name}: file missing from the schema ({len(written)} columns)")
            continue
        problems += compare_columns(name, written, files[name].get("columns") or {})
    for name in files:
        if name not in headers:
            problems.append(f"{name}: in the schema, but eic2ai writes no such file")
    problems += check_references(files, schema.get("layout"), schema.get("lane_titles"))

    n_columns = sum(len(columns) for columns in headers.values())
    if problems:
        print(f"{schema_path} does not match {source}:")
        for problem in problems:
            print("  " + problem)
        print(f"{len(problems)} problem(s). Edit the schema file in the website submodule (AGENTS.md).")
        sys.exit(1)
    print(f"schema OK: {len(headers)} files, {n_columns} columns match {source}")


if __name__ == "__main__":
    main()
