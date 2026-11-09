# eic2ai — rules for changes

Read `README.md` first: what eic2ai does, the reading order of the sources, how to build it.
`CLAUDE.md` is a link to this file.

## A schema change ships with the website page

Every column eic2ai writes is documented on the CSV Schema page,
<https://sroai.github.io/ai-epic-background/csv-schema>. The page is generated from
`website/ai-epic-background/csv-schema.yaml`; `website/` is the submodule
[sroai/sroai.github.io](https://github.com/sroai/sroai.github.io).

**Any change of the CSV schema MUST be accompanied by the updated website page.** A schema change is a column
added, removed, renamed or moved; a new role or extra output; or a column whose meaning changes under the same
name (for example `clu_index` going from the association index to the cluster index). The checks below catch
the first three; only the description you write catches the last one.

1. Change the writer (`src/writer_*.hpp`).
2. Build in a container (README, Build) and write the new headers to the committed snapshot:
   `build/eic2ai --list-columns > tests/columns.txt`.
3. Edit `website/ai-epic-background/csv-schema.yaml`: one line per column, `name: description [unit]`, in the
   order eic2ai writes them. Add the column to `links` when it holds a row number of another file, to `keys`
   when it identifies a row; place a new file in `layout`.
4. Run the checks (PyYAML is the one dependency):
   `python3 tests/check_schema.py` and `python3 tests/check_columns.py --headers tests/columns.txt`.
5. Look at the page when boxes or links changed: `cd website && npm ci && npm run dev`, then open
   `/ai-epic-background/csv-schema`. `npm run build` must pass.
6. Commit the YAML in `website/` and push it to sroai/sroai.github.io `main` (the push deploys the site).
   Then commit in eic2ai the writer change, `tests/columns.txt` and the new `website` submodule pointer together.

CI (`.github/workflows/csv-schema.yml`) checks the YAML and the column vocabulary against `tests/columns.txt`,
and builds eic2ai in `eic_xl` to check that `--list-columns` still prints `tests/columns.txt`. A commit that
changes columns without the page fails.

## Other rules

- Build and run only inside an EIC container (`eic_xl`, `eic-full`, `eic-claude`); the host has no podio.
  `tests/build_in_image.sh <image> <build-dir>` builds in any local image.
- Existing columns keep their bytes: `tests/parity.py` compares against the `csv_convert` macro outputs.
  A value changes only when it is shown wrong; new information goes into new columns.
- Column names follow the vocabulary in `column_renames.py` (`tests/check_columns.py` enforces it).
- Test on the 100-event reference sets; a multi-hour run needs the user's go-ahead.
