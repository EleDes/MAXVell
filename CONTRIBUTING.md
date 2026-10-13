# Developing MAXVell

The checkout contains the runtime code, technical models and synthetic tests.
Decoder, IR and emitter changes can be developed without another repository or
an installed Quartus toolchain. New device observations and independent HDL/fit
checks need the contributor's own tools and test designs.
The [tool and manual links](docs/REFERENCES.md) include matching Quartus device
support, historical builds and the optional simulator.

Start with [scope](docs/STATUS.md), [IR contracts](docs/ARCHITECTURE.md) and
[model provenance](docs/PROVENANCE.md). Storage interpretation, functional
interpretation and fitted equivalence are separate results.

The [Quartus starter example](docs/QUARTUS_CONTROL.md) shows preservation,
post-fit inspection and checked LC placement. [Experiment design](docs/EXPERIMENTS.md)
covers discriminators, formal scope, independent oracles, contradictions and
current development traps. Use these before interpreting new POF differences.

## Start from a working example

Use Python 3.10+ and run from the checkout root:

```sh
python -m unittest discover -s tests -q
python -m maxvell demo-functional --out work/dev-feedback
python -m maxvell query model --target 5M40ZE64C5 --kind usercode --out work/dev-usercode.json
```

The demo provides a synthetic POF, fresh functional IR and an emitted project.
Its current result has two closed registers, two closed nonconstant output paths
and no open interfaces. The model export supplies a small storage-binding example.
Keep output directories separate; demo/project directories must be empty.

## Where to change the implementation

| Area | Entry points | Related checks |
| --- | --- | --- |
| POF parsing and storage decoding | [decode.py](src/maxvell/decode.py), [_core/pof.py](src/maxvell/_core/pof.py), the corresponding `_core/native_*_storage.py` | Packet bounds, target/geometry, bit order and polarity in [test_tools.py](tests/test_tools.py) |
| Routing and field candidates | [analysis.py](src/maxvell/analysis.py), native routing/predicate helpers | Ambiguous/unknown candidates and route matching in `test_tools.py` |
| Functional IR and control composition | [functional.py](src/maxvell/functional.py), native partial-cone and state-control helpers | Admission, feedback, event and boundary cases in [test_functional.py](tests/test_functional.py) |
| HDL and project generation | [project.py](src/maxvell/project.py), [_core/state_control_project.py](src/maxvell/_core/state_control_project.py) | Invalid models, pin bindings and emitted drafts in `test_functional.py`; optional [HDL check](docs/CHECKS.md#independent-emitted-hdl-example) |
| Sequential evaluation | [simulation.py](src/maxvell/simulation.py), state-control event/expression helpers | Initial state, Clear/Load/Enable, edges and unsupported simultaneous events |
| UFM | [ufm.py](src/maxvell/ufm.py), UFM model/recipe records | Content order, section-only export and recipe restrictions in `test_tools.py` |
| Exact-scope support and I/O options | [scoped.py](src/maxvell/scoped.py) | Positive-only ALOAD, conditional minterm relabels, electrical conflicts and exact-pin emission in [test_scoped.py](tests/test_scoped.py) |
| UFM support and exact-input research patterns | [ufm_support.py](src/maxvell/ufm_support.py) | Source/sink codewords, input fingerprints, profile matches and no binding promotion in [test_ufm_support.py](tests/test_ufm_support.py) |
| Route groups, selector qualification and LUT contexts | [research.py](src/maxvell/research.py) | Duplicate-bit disagreement, one-hot classes, unselected codebooks and scope checks in [test_research.py](tests/test_research.py) |
| Model access and validation | [models.py](src/maxvell/models.py), [validation.py](src/maxvell/validation.py), [query.py](src/maxvell/query.py) | Snapshot/schema/hash checks and [test_query.py](tests/test_query.py) |

Wire a new public command or option through [cli.py](src/maxvell/cli.py).
The `_core` modules are included implementation code; their retained `maxvrec.*`
schema names do not imply an external runtime dependency.

## Extend one functional path

1. Choose one exact target and one behavior from the open work in
   [STATUS](docs/STATUS.md). State the behavior to recover and its current boundary.
2. Add a small positive test and a case that must remain rejected or unresolved.
   The synthetic POF builder in `tests/test_tools.py` and the feedback fixtures
   provide starting points without original third-party design files.
3. Decode the required fields before interpreting their meaning. Keep payload
   offsets, native coordinates, logical input order and physical pin identities
   distinct. Reuse the existing model/context loader and admission checks.
4. Follow the change through its consumer: storage decoder, functional expression,
   class/event validation, emitted HDL and evaluation as applicable. A new field
   binding alone is a storage result; it does not establish a reconstructed function.
5. Preserve named unknown interfaces. Add supported behavior explicitly rather
   than weakening class checks or filling unresolved connections with assumptions.
6. Report the exact target/mode tested, closed output paths, modeled registers,
   remaining interfaces and checks actually performed. Update the affected scope
   table and usage instructions; keep untested modes outside the claim.

For code changes, run the relevant tests and the existing unit suite. For emitted
HDL changes, use the optional HDL check or a matching own simulation case. A
simulation result does not replace a fit or hardware comparison.

## New observations and model changes

Use small designs that isolate one function, with explicit input/stimulus and
expected behavior. Start new compiler experiments with ordinary documented
Quartus workflows on your own installation. Record the actual tool version,
exact device, settings, observation method and result, including contradictory
observations. Fitting can move or reroute unrelated logic; a POF bit difference
alone does not identify a function or its polarity.

The shipped SQLite database is an immutable runtime snapshot. The CLI exports
models but has no import/write command. There is no published procedure that
rebuilds every included model family from Quartus. New data requires a reproducible
model-building step as part of that contribution; no hidden acquisition pipeline
is required to develop the existing Python consumers.

Export the nearest model with `query model` and inspect its JSON contracts before
changing the snapshot. For storage-decoder prototypes, `decode.decode_model`
takes an explicit target, kind, provider, catalog record and CFM payload.
Functional reconstruction additionally uses the full IO/LC/routing/control
context from the included catalog; changing one exported JSON file does not
replace that context automatically.

For a model-changing contribution:

- Include a small own reproduction script/design, expected results and factual
  acquisition notes. Keep raw local reports and input-specific outputs under `work/`.
- Describe offsets, XOR/polarity, coordinates and semantic transforms separately;
  state which targets/modes are established and which remain candidates.
- Rebuild the affected record using the [data/schema contracts](docs/DATA.md):
  SHA-256 and length cover the uncompressed JSON, which is stored as zlib data;
  catalog target, kind, geometry and decoder entry point must agree.
- Update `src/maxvell/data/snapshot.json`, validation population expectations and affected
  tests only to reflect the new actual contents. Preserve schema, checksum,
  exact-target and decoder-pattern checks; do not duplicate records to meet counts.
- Run `python -m maxvell validate` after a data change, then exercise the affected
  decoder, functional consumer and emitter with a relevant configuration.

## Material to submit

Contribute your own implementation/tests under 0BSD and your own data/docs under
CC0-1.0, as described in [LICENSES](LICENSES.md). State the actual origin and
method for new model records; a source label is not a substitute for that account.
Use external links for vendor software, vendor HDL, device databases, manuals
and third-party material. Keep credentials, personal identifiers, local paths,
original third-party POFs and bulk vendor dumps out of contributions.

A useful change description states the problem, resulting behavior, affected
targets/modes, reproduction/checks and remaining limits.
