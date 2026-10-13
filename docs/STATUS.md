# Decoder, IR and reconstruction scope

Snapshot date: **2026-10-12**. “Decoded” means included storage bindings and field
interpretation. “Functional IR” means expressions constructed within the named
model class. “Project” means an explicit partial HDL/Quartus draft. These levels
do not imply whole-design, startup or timing equality.

Partially validated candidates and retained negative results are included.
[Candidate inventory](CANDIDATES.md) lists their model/IR access, established
scope and missing validation, separately from the functional consumers below.

## Function families

| Family | Decoder | IR | Reconstruction / export | Main boundary |
| --- | --- | --- | --- | --- |
| POF container | All packet bounds, CFM/UFM sizes, optional CRC | Structural summary | No full POF roundtrip | Several header/tag payloads opaque |
| LUT storage | Exact native ordinal/offset/XOR bindings | Typed storage masks | Native functional LUT cones | Truth order and input transform are separate |
| Logical-minterm LUT view | Two exact targets | 16-bit logical truth table | `emit-lut` isolated cell modules | 5M40ZE64C5 / 5M80ZE64C5; wiring stays open |
| Retained-topology LUT view | 570 / 2,210 cells on 5M570ZT144C5 / 5M2210ZF324C5 | Physical and conditional semantic masks | `emit-lut --view retained-topology` isolated partial modules | Retained controlled topology assumed; new-input topology and source wiring unverified |
| LUT input selectors | Two-stage storage and native source candidates | Named-port candidates / graph inputs | Influential resolved inputs consumed | Ambiguous or unsupported sources become cuts |
| 5M240 selector qualification | 960 instances; 53/72 classes qualified, 19 unresolved | Retained controlled / train-holdout basis | Diagnostic view only | Class qualification does not prove source identity or route completeness |
| 5M240 context LUT views | 240 controlled + eight alternative site codebooks | Conditional masks, all unselected | Diagnostic view only | 58 conflicting minterm bindings across six sites; no universal site transform |
| LE / LAB controls | Fields, extensions, sentinels, exclusions | Storage and bounded control expressions | Ordinary register controls | Carry and unqualified cascade/control modes excluded |
| Routing: LAB, H4/V4, remaining muxes | Stored predicates | Zero / unique / multiple / unknown candidates | Unique candidate paths within model class | Candidate selection alone is no universal route proof |
| Source-only conditions | Stored assembly exclusions | Diagnostic predicates | No independent logical-net grant | Not turned into destination selection requirements |
| IO / CFF / package joins | Storage, inversion, DATA/OE selectors, mode candidates | Pin DATA/OE expressions | Push-pull/open-drain and normal/direct paths | Sampled pad values and drive values remain separate |
| Clock / Clear / Load / Enable | Native selector and polarity fields | Bounded primary-clock control sources | Qualified register cones and `maxv_lcell` drafts | Unknown clock terminals and event models remain cuts |
| Boolean / state-sourced controls | Ordinary LUT sources and native output roles | Bounded expressions | One-layer, one-state-source async controls on opposite edges | Settled binary single-input events only |
| Internal register feedback | Same-LC feedback mode | REGOUT → raw LUT-C XOR 1 | Ordinary feedback state cones | Ordinary DATAC may independently feed async data |
| Readback / bidirectional IO | Input-pad and output-drive paths | Independent sampled-pad expressions | Conditional pin graph | No inferred external board feedback |
| USER_CODE | Complete 32-bit field | Scalar, value and hex | QSF assignment in functional project | No logic-function significance inferred |
| Device / JTAG / UFM options | Included device-wide configuration fields | Typed values and diagnostic classifications | Only consumed settings such as USER_CODE and matched UFM recipes | Other options are not automatically translated into QSF |
| Exact-pin electrical options | `io_options` on eight exact targets | Field values, paired current-strength bits and site signature | Qualified Bus Hold / weak pull-up / slow slew / 8 mA QSF on five targets | Existing matching pin/port required; conflicts and unqualified sites do not receive assignments |
| UFM content | Complete 8,192-bit content layout | 512 × 16-bit words | JSON and MIF | Content alone gives no control-port wiring |
| UFM CFM recipes | Nine bounded recipes on seven exact targets | Serial-raw / parallel interface description | `ufm --project` primitive drafts | Exact CFM recipe and packet geometry must match |
| UFM source/four-sink support | Seven CFM bits on 5M1270ZT144C5 | Support-only dataout[0] to DATAA edge at four retained sinks | No functional project consumer | Other codewords unmatched; no complete route/event proof |
| UFM input/source candidates | Eleven fingerprints / five three-bit source profiles on 5M1270ZT144C5 | Diagnostic pattern matches | No bindings, logical nets or emission | Original exact-input qualification does not transfer to new POFs |
| Additional ALOAD candidates | 1,252 active-high candidate bits on 5M1270ZT144C5 | Diagnostic candidate values | None from this surface | Canonical functional IR explicitly disallowed |
| Duplicate route-group candidate | Two active-low CFM bits for C4_X15_Y8_N0 on 5M1270ZT144C5 | Candidate presence/absence, disagreement blocked | None from this surface | Eight historical inputs; atomic ownership and new-input scope unproved |
| Exact-site ALOAD support | The same 1,252 offsets joined to retained LC/LUT bindings | Positive support nodes/edges for nonconstant LUT sites | No functional connection or emitter grant | Unknown source/events; zero or a constant LUT does not prove absence |
| Outside retained coordinate partition | Stored fields on 48 variants | Diagnostic fields | None from this surface | No placement or legality inference |

## Device families

| Device family | Exact variants | CFM bits | Included interpretation | Reconstruction |
| --- | ---: | ---: | --- | --- |
| 5M40Z | 8 | 53,248 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M80Z | 16 | 53,248 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M160Z | 16 | 53,248 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M240Z | 16 | 53,248 / 110,592 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M570Z | 16 | 110,592 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M1270Z | 12 | 208,896 / 348,160 | Native fields + functional context | Bounded LUT/state/pin drafts |
| 5M2210Z | 8 | 348,160 | Native fields + functional context | Bounded LUT/state/pin drafts |

All 92 catalog variants have the native storage, functional-context and global
clock models. Exact package/grade names still matter. CFM geometry can differ
within a density family. The catalog is authoritative: use `models --target PART`.
The presence of a model does not make every control combination reconstructible.

UFM recipe targets: `5M40ZE64C5`, `5M80ZE64C5`, `5M160ZE64C5`, `5M570ZT144C5`,
`5M2210ZF324C5` (serial raw); `5M240ZT100C5` and `5M1270ZT144C5`
(parallel read-only/read-write). Recipes admit their matched CFM classes, not
every UFM design on those devices.

## Representative storage unions

| Exact target | CFM bits | Model-addressed bits | Remaining bits | Addressed fraction |
| --- | ---: | ---: | ---: | ---: |
| `5M40ZE64C5` | 53,248 | 33,981 | 19,267 | 63.816% |
| `5M80ZE64C5` | 53,248 | 33,981 | 19,267 | 63.816% |
| `5M160ZE64C5` | 53,248 | 33,981 | 19,267 | 63.816% |
| `5M240ZM100C5` | 53,248 | 33,981 | 19,267 | 63.816% |
| `5M570ZT100C5` | 110,592 | 77,425 | 33,167 | 70.010% |
| `5M1270ZT144C5` | 208,896 | 163,144 | 45,752 | 78.098% |
| `5M2210ZF324C5` | 348,160 | 277,017 | 71,143 | 79.566% |

UFM contributes a separate 8,192 content bits when present. Counts include
diagnostic/candidate fields and overlap only once. They are not the amount of
functionally closed logic. Native storage coordinates can outnumber nominal
usable LCs; nominal capacity and legal placement are not derived from this table.

## Open reconstruction work

A retained 5M2210 large-LUT example leaves an output interface in the general
functional graph despite its decoded LUTs. `lut_topology` and the explicit
retained-topology emitter expose the cell functions; they do not infer the
collector or original package-output connection. The two paths have different
validation boundaries.

- Unqualified clock-terminal roles, derived-clock event models and register
  combinations still leave explicit interfaces.
- Carry/arithmetic modes, unsupported cascades and broader state-control
  compositions need additional semantic consumers.
- Complete route-alternative legality, effective pin behavior and package-aware
  fitted equality are broader than current candidate composition.
- UFM control inference outside the nine recipes and integration with surrounding
  logic remain partial.
- Several POF tag/prefix fields and residual CFM bits remain opaque.
- Whole-input equivalence, simultaneous independent events, startup state and
  analog/timing behavior are not established by this release.

The own [Quartus control example](QUARTUS_CONTROL.md#observed-result-and-remaining-boundaries)
provides a fresh concrete case: both visible registers survive the fit, but the
current reconstruction closes only pin 6; pin 5 requires further nonconstant
data-cone composition. [Experiment guidance](EXPERIMENTS.md) describes how to
design a discriminator and qualify a new consumer without guessing that boundary.

[Usage](USAGE.md) · [Functional model details](RECONSTRUCTION.md) · [Verification](CHECKS.md)
