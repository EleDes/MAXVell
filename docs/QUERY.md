# Database query interface

The query interface reads the included SQLite database; it does not import data
or change mappings. Runtime decoders use the same `maxvell.models` access layer.

## Schema and bounded SQL

```sh
python -m maxvell query schema
python -m maxvell query sql "SELECT kind,COUNT(*) AS targets FROM model_catalog GROUP BY kind ORDER BY kind"
python -m maxvell query sql "SELECT target,kind,cfm_bits FROM model_catalog WHERE target=?" --params '["5M1270ZT144C5"]'
python -m maxvell query sql "SELECT region,field_class,COUNT(*) AS fields FROM mapping_results GROUP BY region,field_class"
```

Examples use a POSIX shell or PowerShell 7 with normal native argument passing.
`--params` takes a JSON array; strings, finite numbers and null are supported.
Integer parameters must fit SQLite's signed 64-bit range. SQL
parameters bind values, not table or column names. Give duplicate result columns
distinct aliases using `AS`.

Results contain `columns`, `rows`, `row_count`, `limit` and `truncated`. The default
limit is 50 rows; `--limit` accepts 1 to 1,000. A result that exceeds the limit
sets `truncated: true`. Console results are bounded to 16 KiB. Use `--out` for a
JSON result up to 1 MiB; console output then contains only a short summary:

```sh
python -m maxvell query sql "SELECT target,kind,cfm_bits FROM model_catalog ORDER BY target,kind" --limit 1000 --out work/catalog.json
```

SQL can read `metadata`, `devices`, `mapping_results` and `model_catalog`.
Writes, attached databases, pragmas, extension loading and raw compressed-blob
access are rejected. Only ordinary scalar/aggregate functions used for
inspection are allowed. Expensive queries stop after approximately two million
SQLite virtual-machine instructions; refine a join or select fewer rows when
that happens. A row limit alone does not make an expensive aggregate cheap.

## Export a verified technical model

```sh
python -m maxvell query model --target 5M1270ZT144C5 --kind global_clock --out work/global_clock_model.json
python -m maxvell query model --target 5M40ZE64C5 --kind lut --out work/lut_model.json
python -m maxvell query model --target "*" --kind ufm_content --out work/ufm_content_model.json
```

Model export checks the uncompressed content's SHA-256 and byte length, restores
the exact target where a shared layout uses `@TARGET@`, and writes the full public
JSON model. Large models are written only to a file. Functional encoding tables
retain their `__pairs__` and `__tuple__` JSON records; the functional consumer
restores their native keys. `models --target PART` lists available kinds.

Model presence and storage bindings do not establish functional equality.
[Data/schema](DATA.md) · [Interpretation and consumers](STATUS.md) · [Usage](USAGE.md)
