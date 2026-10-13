# MAXVell

MAX V POF decoding and partial reconstruction, with the technical models included.
Read configuration fields, inspect routing and control candidates, recover LUT and
register cones, and generate explicit HDL / Quartus project drafts.

**Current scope:** 92 exact device variants, typed storage and functional IR,
ordinary register feedback, bounded clock/Clear/Load/Enable controls, pin DATA/OE
composition, qualified exact-pin I/O options, UFM content and target-specific UFM recipes. Unknown dependencies
remain named inputs. Full-design, startup and timing equivalence are open.
See the [function and device-family tables](docs/STATUS.md).

Python 3.10+; use a maintained release (3.14 is tested). Runtime dependencies
are the standard library. [Tool downloads and manuals](docs/REFERENCES.md).
From a checkout:

```sh
python -m maxvell demo-functional --out work/feedback
python -m maxvell inspect your-input.pof
python -m maxvell decode your-input.pof --out work/storage_ir.json
python -m maxvell reconstruct your-input.pof --out work/functional_ir.json --project work/recovered
```

Optional installation: `python -m pip install .` adds the `maxvell` command.

- [Tool usage and examples](docs/USAGE.md)
- [Development and contributions](CONTRIBUTING.md)
- [Quartus control, optimization pitfalls and own experiments](docs/QUARTUS_CONTROL.md)
- [Experiment design, proof scope and development practice](docs/EXPERIMENTS.md)
- [POF structure, tags and bit addressing](docs/POF_FORMAT.md)
- [What is decoded, represented in IR and reconstructed](docs/STATUS.md)
- [Included research candidates and validation boundaries](docs/CANDIDATES.md)
- [Functional reconstruction and its boundaries](docs/RECONSTRUCTION.md)
- [Architecture and IR contracts](docs/ARCHITECTURE.md)
- [Database, model formats and queries](docs/DATA.md)
- [Read-only database query and model export](docs/QUERY.md)
- [Verification](docs/CHECKS.md) · [Model provenance](docs/PROVENANCE.md) · [Public references](docs/REFERENCES.md)

Software: **0BSD**. Own data, diagrams and documentation: **CC0-1.0**.
[Licenses](LICENSES.md) · [Repository contents](docs/PUBLICATION.md).
