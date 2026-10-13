# Verification scope

The public tools were checked on Windows with Python 3.10.11 and 3.14.3. Both
passed the tests and synthetic LUT/feedback demonstrations. The runtime
uses only the standard library. Use a maintained Python release for normal work;
the isolated 3.10 interpreter was used to check the declared compatibility floor.

## Reproducible checks

```sh
python -m unittest discover -s tests -q
python -m maxvell validate
python tools/check_publication.py
python -m maxvell demo-functional --out work/checked_feedback
```

The 66 public tests cover packet bounds, critical tag duplication, CRC, section
geometry, explicit die/package binding, privacy-pattern detection, LUT/USER_CODE
bit order and polarity, UFM bijection/word order, ambiguous routes, functional
feedback, control/event restrictions, exact-target pin binding, read-only database
queries, model export, partial-project guards and both synthetic
demonstrations. Negative cases reject arithmetic feedback, simultaneous
independent events, inconsistent async state and invalid project models.

Data validation checks SQLite integrity/foreign keys, exact public schemas and
populations, all included model hashes/lengths, metadata exclusions and decoded
model-text privacy. All **185 unique models** pass their all-zero/all-one decoder
checks. These patterns exercise storage/schema behavior; they are not functional
proofs for every configuration represented by a model.

## Functional comparisons

Fresh POF decoding of 81 own synthetic configurations produced the same
LUT/register/pin graphs and HDL as their current reference models. A further
42 retained inputs produced matching canonical behavior graphs; the 33
previously compiled cases among them have no unresolved interfaces in the
newly decoded graph. The public runtime requires no reference test files.

All nine UFM recipe classes were accepted and rendered against matching own
inputs. Their decoded words match the recipe content order. Two additional
files with invalid nonzero CRC were rejected before classification/emission.

The included feedback POF demonstration exercises the included model path:
two closed nonconstant output paths, two closed registers and no open
interfaces. The separate small state example checks the event sequence
`1, 1, 0, 0, 1`. These are software checks under the documented model assumptions.

## Independent emitted-HDL example

`tools/check_hdl.py` generates a testbench for the included own feedback model.
The emitted Verilog passed compilation/elaboration and 15 events against the
installed MAX V primitive model using Questa 2025.2 and the Quartus II 13.1
`maxv_atoms.v` model. The sequence covers feedback toggling, Enable hold,
asynchronous Load with changing data, Clear-over-Load and Clear release.
An explicit reset establishes the test's initial state. This checks the emitted
example independently of the Python evaluator; it is not a fitted POF comparison.

To reproduce with your own licensed simulator and installed model file:

```sh
python tools/check_hdl.py --simulator-dir path/to/simulator/bin --maxv-atoms path/to/sim_lib/maxv_atoms.v --out work/hdl_check
```

The output directory must be empty. Phase logs, generated HDL/testbench, stimulus
and `hdl_check.json` stay there. Vendor model source is read from the supplied
installation and is not copied into the repository. No simulator is needed for
the ordinary decoder/tests/demonstrations.

The 81 emitted comparison-case projects also passed Verilog compilation and
elaboration together against the same primitive model. This checks syntax,
module/port binding and parameter compatibility; the composite elaboration
probe applies no behavioral stimulus. The final example and 81-case runs reported
no compiler/elaboration warnings; unused primitive ports are explicitly left open.

## Own Quartus control example

The [control starter](QUARTUS_CONTROL.md) was freshly fitted in Quartus Prime
Lite 25.1std.0 Build 1129 for 5M1270ZT144C5: baseline, a combined preservation
profile, and a fresh source-only project with three observed LC locks. All three
full compiles completed with zero errors and five warnings each. Final pin rows
matched all five requested pins; the locked refit retained all three requested
register locations. Post-fit Tcl inspection passed without warnings.

The warning set was: intentionally unread `orphan` (10036), single-processor
notices (12473, three occurrences) and a LogicLock subscription notice (292013).
No region was requested and no ignored/unknown control assignment was observed.
The initial unpinned example additionally warned about missing pin assignments
and default unused-pin behavior; the final generator fixes these for the checked
target. An initial `get_node_loc -file` call failed; the shipped inspector uses
the installed API's supported no-argument form and passed inspection.

Synthesis/fitted LE counts were 3/2 for the baseline and 4/3 for both controlled
fits. The third register survives; `keep` does not give the XOR a separate final
LC. Both visible registers already survive the baseline, so individual merging
control effects are not established.

Fresh decoding of the controlled POF passed CRC, exact target and section
geometry checks. Functional IR closes one register/output path on pin 6; pin 5
retains `LC_X1_Y10_N9:REGOUT`, reason `nonconstant data needs cone composition`.
This is a measured partial reconstruction, not a whole-design comparison.
No ECO edit, alternate-target fit, routing lock, A-B-A stability campaign,
exhaustive formal comparison or hardware test was performed for this example.

## Candidate inventory checks

The [candidate inventory](CANDIDATES.md) was checked against the shipped catalog,
exported model contracts and grouped scope records. The additional ALOAD stage
decoded all 1,252 candidate bits from the own controlled POF while retaining
`canonical_ir_allowed=false`. Analysis of the synthetic feedback POF retained
its diagnostic source/route limits. The two focused candidate-analysis and
route-ambiguity tests passed. These checks establish availability and preserved
boundaries; they do not independently validate the candidates' physical meaning.
That inventory-only check changed no model data or functional admission.

The scoped models include exact-site ALOAD support, conditional 5M570/5M2210
LUT minterms and exact-pin electrical options. Positive/negative tests check
constant-LUT exclusions, positive-only ALOAD,
bijective minterm relabels, conflicting/partial I/O settings, site signatures,
existing-pin binding and fresh POF-to-QSF consumption. Fresh synthetic POF
regressions also check that a conflict on an excluded pin cannot block a selected
closed output, and permanently released pads receive input options only. A
conflict on an included qualified pin still blocks bound emission before any
files are written. No productive equality grant was added.
All 1,252 decoded ALOAD candidate values also match independent reads of the
actual POF packet on a nonuniform synthetic payload. The retained inventory's
packet offsets include a 96-bit prefix; the decoder and storage union normalize
them to CFM offsets. This corrected address-domain error reduces the 5M1270
storage union by 225 previously miscounted offsets; it does not reduce the
included candidate population or functional consumer scope.

Fresh decoding of the 81 retained own comparison inputs still matches their
LUT/register/pin graphs and emitted HDL. The 5M570 support view matches the
original scoped decoder for all 570 cells on four byte-pattern inputs; the ALOAD
observation rule matches its original packet-prefix interpretation on four
patterns and 1,252 sites. These compare implementations under the same retained
models, not their physical hypotheses independently.

All 570 and 2,210 retained-topology cell modules were also compiled, elaborated
and simulated with four synthetic payload patterns (rotating one-hot,
asymmetric, complement and per-cell hash). All 16 binary inputs per cell/pattern
matched direct interpretation of the shipped offset/minterm tables: 177,920
output comparisons across eight simulations, with no warnings or errors. A
separate basis-bit check passed 44,480 mask comparisons. The expectation does
not call the scoped decoder, but shares its model data. These checks establish
decoder/export consistency under the retained relabels; they do not establish
historical model correctness, input topology or source connectivity.

The UFM support classifier passed all 128 source/sink combinations against the
retained decoder. Four retained input-fingerprint cases match all eleven
patterns, and thirty retained semantic-source cases match their profile
endpoints. Public tests include fresh POF decoding with a nonzero section
prefix, unmatched codewords and counterexamples; fingerprint/profile matches
create no bindings or edges and do not verify the historical exact-input scope.

Route-group tests cover both equal-bit states and disagreement. The 5M240
qualification/context consumers match the unchanged reference functions on
twenty own payloads: 19,200 selector-instance comparisons and 4,960 context-mask
comparisons. All 240 controlled views and eight alternative site views remain
unselected; tests reject class, offset-domain and functional-scope widening.
These are decoder/interpretation comparisons. The historical proof harnesses
and input-specific grants were not rerun or transferred.

A further spot check decoded one retained large-LUT case each on 5M40ZE64C5,
5M80ZE64C5, 5M570ZT144C5 and 5M2210ZF324C5. The first three close one output
path without interfaces. The 5M2210 case reads 2,208 reachable LUTs but leaves
one output interface; the scoped view separately exposes all 2,210 retained cell
truth functions. Exporting those isolated modules does not close the collector
or establish the original package-output function. The full original input
therefore must not be described as reconstructed by that export.

## Retained routing and ECO observations

The [routing/ECO guide](QUARTUS_CONTROL.md#routing-and-saved-eco-experiments)
summarizes an own six-LC/nine-pin study on 5M1270ZT144C5 with Quartus II 13.1.4
Build 182 Web and Prime 25.1std.0 Build 1129 Lite. Retained receipts record 18
positive route cases, 12 successful compilations rejected for invalid/stale
constraints, 28 post-fit netlist comparisons (1,792 untimed functional checks)
and eight final saved-ECO cases. These are distinct from the register-control
starter and from the reconstructed public drafts.

During documentation review, eleven selected result/export/replay files matched
their retained SHA-256 and byte-count manifest. The original route/ECO fixture
and its full receipts are not shipped as a public regression suite. The compiler,
ECO operations and simulations were not rerun for this update. This is retained
experimental evidence for the named fixture, not a fresh reproduction, timing
sign-off, hardware check or general routing-support qualification.

## Limits

No fresh Quartus fit or hardware test has been run for the reconstructed public
drafts. The own control-example fits above are separate from those drafts.
The vendor-model simulation covers the example above, not the full configuration
catalog or all state-control classes. Prior compile results do not certify a newly emitted project.
Timing, startup, simultaneous independent events and whole-input equivalence
remain outside the fresh checks. Identifying-text scans use heuristic patterns
and can miss strings they do not recognize. Non-Windows execution was not tested.

An isolated wheel installation passed the LUT and feedback demonstrations,
output-cone selection, physical pin emission, sequential example and UFM
content/MIF export. The package's 1,363 catalog rows, all five additional research
stages and package/license contents were checked without importing another
project. All 79 runtime/checkout-bootstrap Python files also parse with the
Python 3.10 grammar; all 66 tests passed on Python 3.10.11 and 3.14.3.

All runtime models are included; no other repository is required. For a
fresh-clone check, run the commands above with empty demonstration output
directories.

A fresh local clone passed the tests, feedback demonstration and the
repository content/link scan. The public file set is about 39.0 MB before Git
compression, including the 38.5 MB database, excluding generated user outputs.
