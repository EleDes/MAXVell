# Included research candidates and validation boundaries

The package includes diagnostic and partially validated interpretations alongside
the models used for bounded functional reconstruction. They are available for
independent investigation; they are not silently promoted to established
connectivity or emitted behavior.

Storage binding, a matching configuration predicate, a functional interpretation
and an exact-input equivalence comparison are different results. In particular,
a single matching candidate is unique **within the represented alternatives**;
it does not establish that those alternatives are complete or physically legal.

## Candidate surfaces in the shipped package

Counts below refer to catalog targets or retained records, not successful
functional experiments. The catalog holds 92 exact device variants.

| Surface and access | Included result | Validation boundary / missing step |
| --- | --- | --- |
| Additional ALOAD bits: `aload_candidates`, `decode --stages aload_candidates` | **1,252** offsets labeled active-high on **5M1270ZT144C5**; raw bit values can be decoded | No canonical functional IR from this surface: `canonical_ir_allowed=false`. Source identity, polarity in the actual circuit, event behavior and connection to a particular register are not established by that bit list. The active-high label is the candidate description, not an independent event proof. |
| Routing muxes: `route_mux`, `h4_v4`, `remaining_mux`; `analyze` | Storage predicates on **92** targets; destination/assembled match sets and native paths | `route_mux` explicitly retains `complete_legal_alternatives_proved=false` and `functional_routes_proved=false`. Zero, unique, multiple or unresolved matches do not alone prove the selected logical connection. A functional consumer needs qualified endpoints, relevant alternatives and composition. |
| Exact-site positive ALOAD support: `aload_sites` | **1,252** retained LC/bit joins with each site's 16 LUT offsets. Nonconstant raw LUT + set active-high bit produces a support edge to ALOAD. | `canonical_support_ir_allowed=true` only for structural positive support; `canonical_functional_ir_allowed=false`. Source identity and events unproved. Zero is unresolved; constant-LUT sites are omitted, not disproved. |
| Retained-topology minterm views: `lut_topology` | **570** / **2,210** LC relabels on **5M570ZT144C5** / **5M2210ZF324C5** | Conditional on the retained controlled topology. `input_topology_verified=false`, source connectivity unproved and no logical nets created. Target/size do not verify a new input's topology. |
| Exact-pin electrical options: `io_options` | Eight exact target/site decoders; five targets permit qualified QSF in pin-bound drafts | Scope, paired bits, electrical conflicts, existing physical pin and output requirements checked. No complete I/O-standard, voltage, timing or board reconstruction. [Target table and usage](USAGE.md#scoped-support-views-and-io-options). |
| UFM source/four-sink support: `ufm_source_sink_support` | On **5M1270ZT144C5**, two source bits distinguish dataout/disconnected; five sink bits select one of four retained LCs. Matching dataout creates a support edge to `dataa`; disconnected creates none. | `canonical_support_ir_allowed=true`, functional/emission flags false. Retained source validation covered four dataout cases, four disconnected cases and a negative corpus; no complete routing, timing or UFM behavior is proved. Other source/sink codewords are unmatched. |
| UFM input fingerprints and semantic source profiles: `ufm_candidates` | **11** input patterns with **2,837** positions (nine address inputs, nread, oscena); **five** source profiles distinguish disconnected/dataout/data_valid/nbusy/osc | Original input bindings were limited to four exact inputs; source profiles to thirty retained inputs. The public view has no historical input-identity grant: `exact_input_scope_verified=false`, canonical flags false, no bindings/edges. A pattern match alone does not establish a pin connection, generic selector or coordinate transfer. |
| Duplicated route-group candidate: `route_group_candidates` | **5M1270ZT144C5**, `C4_X15_Y8_N0`: CFM bits **195184 / 196208**, active-low duplicate group. Equal bits report candidate presence/absence; disagreement blocks it. | Historical evidence: six discovery and two held-out inputs. `input_scope_verified=false` for a new input; atomic bit ownership, source identity and productive interpretation remain unproved. No route edge or emitter grant. |
| Selector-class qualification: `selector_qualification` | **5M240ZT100C5**: **960** selector instances / **8,640** terms; **17** controlled + **36** train/holdout classes = **53 / 72** qualified classes, **19** unresolved | Qualification describes the retained storage class, not the logical source. Illegal one-hot patterns are rejected as selector states. Source binding, full route alternatives and functional/emission grants remain absent. Other parts/sites are not inferred. |
| Context-dependent LUT codebooks: `lut_context_candidates` | **5M240ZT100C5**: **240** controlled-layout views (**3,840** minterm bindings) and **eight** separate site views (**128** bindings) | Every public view stays `available_not_selected`; no new input topology is verified. The retained contexts disagree on **58** bindings at **six** sites, so a single site-wide transform is explicitly forbidden. No automatic context choice, wiring or emitter grant. |
| Source-only exclusions: `source_exclusions`; `analyze` | Source-condition terms on **92** targets, kept distinct from destination predicates | `mandatory_route_terms_proved=false`, `selected_routes_proved=false`. An assembly exclusion is not automatically a mandatory condition for selecting a destination. Establish that distinction before using it as a routing rule. |
| LUT input selectors: `input_selectors`; `decode` / `analyze` | Native selector fields on **92** targets, including stored stages and exclusions | `selected_source_proved=false` at this storage surface. Native input indices are not automatically named DATAA–DATAD or logical minterms. A resolved functional input requires the separately checked port/order transform and source path. |
| Native source-output roles: `analyze` → `source_roles` | Field-derived COMBOUT/REGOUT role descriptions at supported endpoints | `state_semantics_proved=false`. A role alone does not establish register data, clock, control priority or output-cone closure. Missing role fields or unsupported classes cannot be assumed to resolve. |
| ALOAD presence and control-source composition: `analyze` → `controls`; functional IR qualification details | A local/LAB predicate may return `candidate_resolved`; other combinations remain unresolved. Separate consumers can compose some qualified controls. | The presence predictor retains `source_identity_proved=false` and `event_behavior_proved=false`; the control-source predictor also retains `source_polarity_proved=false`. Finding a source or presence condition is not its complete asynchronous behavior. Use only the functional consumer's admitted class/event scope. |
| Fields outside the retained coordinate partition: `outside_legal`, `decode --stages outside_legal` | Diagnostic storage fields on **48** targets; excluded fields and coupled bits retained | `functional_influence="unresolved"`, `usable_logic_claimed=false`, `no_effect_proved=false`. Neither usable physical logic nor lack of functional influence is established. The retained partition and schema name are not a universal placement-legality proof. |
| Scope-limited field records: `query sql` → `mapping_results` | Exact-target source identity, partial route predicates and local transforms, with `truth_scope`, `usage_class`, `transform_status` | Some records are support-only or location/context-specific. Their labels do not extend them to another site, device, control class or whole-design equality. Read all three scope columns together. |
| Refuted local LUT projections: `mapping_results` | **16** rows on **5M1270ZT144C5**, marked `local_projection_refuted` and `superseded_by_decoder_offset_domain_transform` | These are retained negative results, not unresolved alternatives or recommended mappings. Do not use them as an active offset/minterm transform. The table separately retains **8** `local_projection_active` rows, still limited by their exact target and transform scope. |

For example, the support-only records include four global-clock source-identity
rows and four topology-conditioned LE configuration rows on 5M1270ZT144C5.
They do not by themselves qualify a complete register or route. Likewise,
carried `proven`/`validated` labels describe their retained scope; the public
package does not attach a new universal equivalence grant to those labels.

The raw ALOAD inventory, exact-site positive support and local/LAB ALOAD presence
predictor are **different surfaces**. Restrictions on the inventory do not remove the
already qualified ALOAD behavior of the bounded functional consumer. See
[scope tables](STATUS.md) and [functional boundaries](RECONSTRUCTION.md).

## Read the candidates without changing the database

From the checkout root, export the full technical models to ignored local files:

```sh
python -m maxvell query model --target 5M1270ZT144C5 --kind aload_candidates --out work/aload_candidates.json
python -m maxvell query model --target 5M1270ZF324A5 --kind outside_legal --out work/outside_partition.json
python -m maxvell query model --target 5M40ZE64C5 --kind route_mux --out work/route_candidates.json
python -m maxvell query model --target 5M40ZE64C5 --kind source_exclusions --out work/source_exclusions.json
```

These exact target/kind combinations are present in the catalog. The
`outside_legal` family is **not** available for every part: for example,
5M1270ZT144C5 has no such model. Check `models --target PART` or query the
catalog before selecting a stage. Model export verifies byte length and SHA-256,
not the candidate's functional meaning.

To inspect scope labels, including retained negative results:

```sh
python -m maxvell query sql "SELECT usage_class,COUNT(*) AS fields FROM mapping_results GROUP BY usage_class ORDER BY usage_class"
python -m maxvell query sql "SELECT target,field_class,truth_scope,usage_class,transform_status,COUNT(*) AS fields FROM mapping_results WHERE usage_class IN ('local_projection_active','local_projection_refuted','decoder_ir_support_only_exact_device_source_identity','decoder_ir_support_only_partial_route_predicate') GROUP BY target,field_class,truth_scope,usage_class,transform_status"
```

For an own POF with matching exact target and CFM geometry:

```sh
python -m maxvell decode own-input.pof --stages aload_candidates --out work/aload_values.json
python -m maxvell decode own-input.pof --stages ufm_source_sink_support,ufm_candidates --out work/ufm_candidates.json
python -m maxvell analyze own-input.pof --out work/candidate_ir.json
python -m maxvell reconstruct own-input.pof --out work/functional_ir.json
```

The ALOAD- and UFM-candidate commands need 5M1270ZT144C5. The analysis and reconstruction
commands apply their own exact-target checks. Keep the diagnostic candidate IR
and the functional IR separate; the former is not an emitter input.
The ALOAD candidate model retains packet-relative offsets including the 12-byte
section prefix. Decoded v2 IR exposes CFM-relative offsets and also keeps the
original packet offsets; see [the address conversion](DATA.md#scoped-model-layouts).

For the route group and 5M240 qualification/codebooks:

```sh
python -m maxvell decode own-1270.pof --stages route_group_candidates --out work/route_group.json
python -m maxvell decode own-240.pof --stages selector_qualification,lut_context_candidates --out work/qualified_contexts.json
python -m maxvell query model --target 5M240ZT100C5 --kind lut_context_candidates --out work/context_codebooks.json
```

Use **5M1270ZT144C5** and **5M240ZT100C5**, respectively. Alternative context masks
are useful for designing a discriminator, but must not be substituted for an
established input-port transform merely because a mask looks plausible.

## Interpreting machine-readable limits

- `destination_state` / `assembled_state`: `zero` means no represented matching
  source, `unique` one, `multiple` more than one, `unresolved` missing terms.
  Inspect the unknown sets and represented candidate class as well as the count.
- `candidate_resolved` describes the particular predicate decision. It does not
  override separate false flags for source identity, polarity or event behavior.
- `named_port_order_proved=false` and `logical_nets_created=0` in diagnostic
  analysis explicitly limit that artifact; functional composition has separate
  transforms and admission checks.
- `productive_emission_allowed=false` is also the public research-release policy
  for bounded functional outputs. It is **not**, by itself, a ranking of all
  included data as equally unvalidated. Use each surface's actual contract.
- `validate` checks integrity, schemas, geometry, model checksums and decoder
  patterns. Passing it does not discharge the functional limits in the table.

Unsupported functional dependencies remain named boundaries. The freshly fitted
[control example](QUARTUS_CONTROL.md#observed-result-and-remaining-boundaries)
currently leaves `LC_X1_Y10_N9:REGOUT` open because nonconstant data needs cone
composition. That is a concrete unresolved consumer, not evidence that every
register on that device is unsupported.

To advance a candidate, state its exact claim, enumerate competing explanations,
add a discriminating own experiment and an independent oracle, and check the
affected decoder → functional consumer → emitter chain. Preserve negative cases
and refuse promotion while a relevant contradiction or ambiguity remains.
[Experiment and proof guidance](EXPERIMENTS.md) · [Contribution workflow](../CONTRIBUTING.md).

This overview covers the candidate surfaces available in the shipped models and
tools. It does not enumerate every possible interpretation of opaque POF fields.
