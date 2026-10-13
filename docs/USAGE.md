# Tool usage

Python 3.10+; runtime dependencies are the standard library. In a checkout, use
`python -m maxvell`. After `python -m pip install .`, use `maxvell` instead.
Commands print bounded summaries; detailed IR goes to `--out`.
Use a maintained Python release; see [tool downloads](REFERENCES.md#get-the-tools)
for Python, Git and the optional Quartus/Questa installations.

## Start with the demonstrations

```sh
python -m maxvell demo --out work/lut_demo
python -m maxvell demo-functional --out work/feedback_demo
python -m maxvell simulate examples/feedback_model.json examples/feedback_stimulus.json --out work/feedback_steps.json
```

The LUT demo checks a synthetic logical truth mask. The functional demo builds a
synthetic POF, decodes two register-feedback cones and emits a partial project.
The separate small model example toggles state on rising edges; the five expected
states are `1, 1, 0, 0, 1`. These are software examples, not hardware measurements.
Demo/project output directories must be empty. `work/` is ignored by Git.

## Inspect and decode

```sh
python -m maxvell status
python -m maxvell --version
python -m maxvell models --target 5M1270ZT144C5
python -m maxvell query schema
python -m maxvell inspect design.pof
python -m maxvell decode design.pof --out work/storage_ir.json
python -m maxvell decode design.pof --stages lut,usercode,io_fields --out work/selected_fields.json
python -m maxvell analyze design.pof --out work/candidate_ir.json
```

`inspect` lists packet offsets/sizes, target binding, CFM/UFM sizes and CRC status.
Creator/comments and input paths are omitted. Duplicate critical packets,
truncation, size mismatches and invalid nonzero CRC are rejected. CFM field
decoding requires included exact target geometry.

`analyze` writes diagnostic candidate IR; it does not prove complete routing or
create emitter-ready logical nets. See the [candidate inventory and validation
boundaries](CANDIDATES.md) for the shipped research surfaces and scope flags.

If the header contains only a die name such as `5M1270Z`, supply the exact part:

```sh
python -m maxvell reconstruct design.pof --target 5M1270ZT144C5 --out work/functional_ir.json
```

This chooses decoding/package geometry. It does not verify that package identity
or grant functional equivalence. A conflicting exact header is rejected.

## Recover functional cones and emit a draft

```sh
python -m maxvell reconstruct design.pof --out work/functional_ir.json --project work/recovered
python -m maxvell emit-project work/functional_ir.json --out work/recovered_again
python -m maxvell reconstruct design.pof --output-pin 35 --out work/selected_ir.json --project work/selected_project
```

Use the decoded `pins[].pin` identity (for example `35`) for `--output-pin`; repeat it to select multiple
closed driven cones. Read `assessment` and `boundaries` before treating a result
as a closed function. A project contains `recovered.v`, QPF/QSF, the model and a
checksummed manifest. Unknown cuts become explicit input ports. USER_CODE is
carried into QSF when decoded. By default, no physical pin assignments are added.
Quartus is not invoked by these commands; manifests report compilation as unrun.

To apply the exact target's included package-pin join:

```sh
python -m maxvell emit-project work/functional_ir.json --out work/pin_bound_project --bind-pins
```

Each native IO/pin pair must match the included bonded-pad table. Conceptual pin
names and mismatches are rejected before files are created. `--bind-pins` also
works with `reconstruct --project`; it requires project output. This copies pin
constraints into a draft; it does not establish fitted equality. LC placement,
startup state and timing assumptions remain unspecified.
All project draft paths set one internal compiler worker and reserve unused pins
as inputs tri-stated. These defaults do not replace actual pin, voltage, clock
or timing constraints, nor do they freeze placement or routing.

The separate LUT-only path uses a logical-minterm storage IR:

```sh
python -m maxvell emit-lut work/storage_ir.json --cell LC_X2_Y1_N0 --out work/lut_project
```

It requires the target's `lut_semantics` stage and leaves physical input wiring
open. Supported targets and function classes are listed in [STATUS](STATUS.md).

## Scoped support views and I/O options

These stages are included by default when the exact target has their models:

```sh
python -m maxvell decode own-1270.pof --stages aload_candidates,aload_sites --out work/aload_support.json
python -m maxvell decode own-570.pof --stages lut,lut_topology --out work/topology_luts.json
python -m maxvell decode own-input.pof --stages io_options --out work/io_options.json
```

`aload_sites` is specific to 5M1270ZT144C5. It joins retained LC sites, active-high
bits and nonconstant raw LUT occupancy, creating positive **support** nodes/edges.
Source identity and asynchronous behavior remain unresolved. A zero bit or an
omitted constant-LUT site must not be interpreted as absence of a load path.
This support artifact is not an input to `emit-project`.

`lut_topology` covers 5M570ZT144C5 (570 cells / 9,120 minterms) and
5M2210ZF324C5 (2,210 cells / 35,360 minterms). The semantic view assumes the
retained controlled topology; the decoder does not establish a new input's
topology or sources. It does not replace a checked functional graph or the
ordinary `lut_semantics` contract.

To emit the conditional truth view as isolated modules with unresolved inputs:

```sh
python -m maxvell decode own-2210.pof --stages lut_topology --out work/retained_luts.json
python -m maxvell emit-lut work/retained_luts.json --view retained-topology --out work/retained_lut_project
```

`--cell LC_X..._Y..._N...` selects one available site. The default truth view
remains the checked small-device logical-minterm view. Neither isolated-cell
emitter infers input nets, collector logic, package output paths or placement.
Only one cell is the project top; additional modules are separate interfaces.
The functions are usable while their environment remains explicitly open.

| Exact part | Pin | I/O decoding | Qualified QSF in a pin-bound draft |
| --- | --- | --- | --- |
| 5M40ZE64C5 | 64 | Yes | No |
| 5M80ZE64C5 | 64 | Yes | Yes |
| 5M160ZE64C5 | 64 | Yes | No |
| 5M240ZT100C4 / 5M240ZT100C5 | 2 | Yes | Yes |
| 5M570ZT144C5 | 1 | Yes | No |
| 5M1270ZT144C5 | 32 | Output-site signature required | Yes, existing decoded output required |
| 5M2210ZF324C5 | B8 | Yes | Yes |

For applicable sites, `reconstruct` retains the I/O-option result in functional
IR. With `--project ... --bind-pins`, the emitter can restore qualified Bus Hold,
weak pull-up, slow slew and 8 mA assignments to the existing `p_PIN` port.
Current-strength group bits must agree; Bus Hold and weak pull-up must not be
active together. A blocked qualified option set on an included pin stops bound
emission before writing files. Unsupported sites stay diagnostic. Output options
are not applied to permanently released pads (constant-low OE or open-drain
constant-high data); input options can still apply. A removed pin receives no
assignment and its option conflicts do not block a selected output cone.
The manifest records `io_option_assignments_applied`.

This does not recover the complete I/O standard, bank voltage, board loads or
timing constraints. Review those before fitting or programming. No new fit or
hardware comparison is implied by an exported assignment.
[Candidate limits](CANDIDATES.md) · [Controlled fitting](QUARTUS_CONTROL.md).

## Additional route and context candidates

```sh
python -m maxvell decode own-1270.pof --stages route_group_candidates --out work/route_group.json
python -m maxvell decode own-240.pof --stages selector_qualification,lut_context_candidates --out work/layout_candidates.json
```

These require 5M1270ZT144C5 and 5M240ZT100C5, respectively. The route group is
a duplicated active-low candidate; inconsistent bits block its interpretation.
The 5M240 selector view labels retained qualified classes and the 19 unresolved
classes without supplying source nets. Its LUT-context view exposes 240
controlled and eight alternative site codebooks, always unselected on a new
input. Conflicting site codebooks cannot be merged into a universal transform.
These research views are not inputs to either project emitter; see
[the complete scope table](CANDIDATES.md).

## UFM content and recipes

On 5M1270ZT144C5, separate research stages expose retained UFM routing support
and diagnostic input/source patterns:

```sh
python -m maxvell decode own-1270.pof --stages ufm_source_sink_support,ufm_candidates --out work/ufm_support.json
python -m maxvell query model --target 5M1270ZT144C5 --kind ufm_candidates --out work/ufm_patterns.json
```

`ufm_source_sink_support` can report a support-only `dataout[0]` to `dataa` edge
for four retained sink LCs. `ufm_candidates` exposes eleven input fingerprints
and five semantic-source profiles as pattern matches. These do not reconstruct
the UFM instance or surrounding logic and cannot be passed to `emit-project`.
The exact historical input guards are not replaced by matching codewords;
see [their validation boundaries](CANDIDATES.md).

```sh
python -m maxvell ufm design.pof --out work/ufm_words.json --mif work/ufm_init.mif
python -m maxvell ufm design.pof --out work/ufm_words.json --project work/ufm_project
```

Content export requires an 8,192-bit UFM section. Project generation additionally
requires a matched included CFM recipe. Unmatched designs report their recipe
status and block project emission. Serial and parallel interfaces are distinct;
the recipe result states which interface was recognized.

A file containing UFM without CFM still permits word/MIF export and reports
`no_cfm_section`. `decode`, `analyze` and `reconstruct` consume CFM; use `ufm`
for independent UFM content extraction.

The five serial recipes include their exact test-interface pin maps and accept
`--project ... --bind-pins`. Parallel recipes have no included physical map and
reject that option. A recipe's test-interface assignment does not identify the
board wiring of an arbitrary design.

## Storage accounting and checks

```sh
python -m maxvell coverage --target 5M1270ZT144C5 --out work/coverage.json --svg work/coverage.svg
python -m maxvell validate
python -m unittest discover -s tests -q
python tools/check_publication.py
```

Coverage JSON includes per-family counts and unassigned ranges. Families overlap;
the total is a set union. It measures included storage addressing, never
functional completion. `validate` checks included data, schemas, checksums and
decoder patterns. The repository check covers the publishable file set and
Markdown links. [Verification scope](CHECKS.md).

The [database query interface](QUERY.md) supports bounded read-only SQL and full
technical-model export without an input POF.

## Simulating an explicit functional IR

Provide `initial_state` keyed by modeled register identities, `initial_inputs`
keyed by sampled input pins and `input_steps` with complete subsequent input
dictionaries. `boundary_values` supplies fixed values for open interfaces.
Change at most one independent input per event. All values must be binary
integers; booleans and missing/extra domains are rejected where checked.

```sh
python -m maxvell simulate work/functional_ir.json stimulus.json --out work/steps.json
```

An inconsistent active async initial state or unsupported event fails explicitly.
Evaluation of caller-supplied state/cuts does not establish original-input equality.
