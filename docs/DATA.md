# Included data and model formats

`src/maxvell/data/results.sqlite` contains technical results only and is opened
read-only. The database is 38.5 MB (decimal).
[schema.sql](../src/maxvell/data/schema.sql) defines the public columns;
[snapshot.json](../src/maxvell/data/snapshot.json) records release counts.

| Table | Rows | Contents |
| --- | ---: | --- |
| `metadata` | 4 | Public format, date, coordinates and functional scope |
| `devices` | 7 | Family/CFM/UFM geometry |
| `mapping_results` | 3,149 | Field/address results and technical scope metadata |
| `model_catalog` | 1,363 | Exact-target/model-family entries |
| `model_blobs` | 185 | Deduplicated compressed technical models |

## Model families

| Kind | Catalog entries |
| --- | ---: |
| `aload_candidates` | 1 |
| `aload_sites` | 1 |
| `cff_io` | 92 |
| `device_fields` | 92 |
| `functional` | 92 |
| `global_clock` | 92 |
| `h4_v4` | 92 |
| `input_selectors` | 92 |
| `io_fields` | 92 |
| `io_options` | 8 |
| `lc_bundle` | 92 |
| `le_lab_controls` | 92 |
| `lut` | 92 |
| `lut_semantics` | 2 |
| `lut_topology` | 2 |
| `lut_context_candidates` | 1 |
| `outside_legal` | 48 |
| `remaining_mux` | 92 |
| `route_mux` | 92 |
| `route_group_candidates` | 1 |
| `selector_qualification` | 1 |
| `source_exclusions` | 92 |
| `ufm_content` | 1 |
| `ufm_candidates` | 1 |
| `ufm_recipe` | 7 |
| `ufm_source_sink_support` | 1 |
| `usercode` | 92 |

Most families have 92 exact targets. `lut_semantics` has two, `outside_legal`
has 48 and `ufm_recipe` has seven. `ufm_content` uses the shared `*` content layout;
exact target and section checks still precede its application. Functional/global
clock models include encoding tables and configuration predicates. ALOAD
candidates remain explicitly noncanonical. See [STATUS](STATUS.md) for consumers
and semantic restrictions; a catalog entry is not a universal function grant.
`aload_sites` adds exact-site positive support edges to the raw bit inventory.
`lut_topology` records conditional 5M570/5M2210 minterm relabels. `io_options` records
enumerated exact-pin options, signatures, grouped bits and QSF limits. These
models have no dependency on retained input files or another repository.
The [candidate inventory](CANDIDATES.md) explains provisional predicates,
support-only records and retained refuted transforms, with their explicit limits.
The [provenance table](PROVENANCE.md) describes the records obtained from
compiler experiments, tool queries, diagnostic output and device-data parsing.

## Reading the database

```sh
python -m maxvell query schema
python -m maxvell query sql "SELECT kind,COUNT(*) AS targets FROM model_catalog GROUP BY kind ORDER BY kind"
python -m maxvell query model --target 5M1270ZT144C5 --kind global_clock --out work/global_clock_model.json
```

Use the [query interface](QUERY.md) for bounded read-only SQL, field inspection
and checksum-verified full model export. It documents parameters, row/byte limits
and allowed query operations.

`mapping_results` is a small reviewed field collection, not the denominator for
coverage. The larger model families overlap; use `coverage` for a set union.

| Mapping columns | Interpretation |
| --- | --- |
| `target`, `cfm_class` | Exact part and configuration-storage class |
| `region`, `bit_offset` | Section/payload address; `packet_0x0011_payload` uses CFM payload LSB0 offsets, excluding the 12-byte section prefix |
| `field_class`, `block_kind`, `resource_kind` | Field and native resource categories |
| `block_coord`, `signal_name` | Retained native identities; not automatically logical nets or physical placements |
| `polarity` | Retained polarity description; use model terms/XOR values for actual decoding |
| `truth_scope`, `usage_class`, `transform_status` | Technical characterization of retained results; labels alone do not authorize functional composition or establish new equivalence |

`devices` groups storage geometry. `model_catalog.cfm_bits` records model payload
geometry; for the shared `ufm_content` row it holds the 8,192 UFM content bits.
Nominal logic capacity and functionally reconstructed state are separate from
these storage populations.

`model_catalog` joins `model_blobs` by `content_sha256`. Each `zlib_json` value is
compressed UTF-8 JSON; its hash and `json_bytes` cover uncompressed public content.
The loader verifies both. `@TARGET@` restores the exact catalog target where
otherwise identical layouts are shared. Functional encoding tables use
`__pairs__`/`__tuple__` records to retain non-string keys without lossy conversion.
`maxvell.functional.unpack` restores these native table keys.

UFM recipe fingerprints constrain CFM/configuration geometry for the included
own test classes; UFM content is separately decoded. They are not whole-input
identity lists. The synthetic feedback fixture contains compact configuration
bytes for the demo and no creator/comment records; its USER_CODE is zero.


## Scoped model layouts

All scoped offsets address the CFM section payload in LSB0 order, excluding its
12-byte prefix. They do not mix file offsets or packet-payload offsets.
The older `aload_candidates` v1 model is an explicit exception: its
`candidate_bits[].payload_offset` is packet-relative and includes that prefix.
The decoder subtracts 96 bits and emits `maxvell.aload_candidate_ir.v2` with
CFM-relative `payload_offset`, retained `packet_payload_offset` and
`offset_domain=cfm_section_payload_lsb0`. Storage accounting uses the normalized
CFM offsets too. Apply this conversion only to that model format.

| Kind | Technical layout |
| --- | --- |
| `aload_sites` | `sites[]`: retained `quartus_lc`, active-high `payload_offset`, and 16 `lut_offsets` used only to test nonconstant raw occupancy. Positive support leaves source identity/events unresolved. |
| `lut_topology` | `cells[quartus_lc]`: triples `[payload_offset, physical_minterm, retained_semantic_minterm]`, with `cell_count` and exact retained `scope`. Each cell has a complete bijective relabel of 0..15; input topology and connectivity are separate. |
| `io_options` | `fields[]`: `kind`, `offset`, `active_raw`; `signature[]`: `[offset, required_raw]`; fixed assignment names/values, exact pin, grouped-bit and output/scope restrictions. |
| `ufm_source_sink_support` | Two source bits and five sink bits; codewords distinguish `dataout`/`disconnected` and four retained sink LCs. A match creates only a support edge for `dataout[0]` to `dataa`. |
| `ufm_candidates` | Eleven `input_bindings` contain 2,837 non-overlapping offset/codeword positions (2,809 from eight added bindings plus 28 from three earlier bindings). Five `source_profiles` each contain a three-bit codebook for disconnected / dataout / data_valid / nbusy / osc. Public decoding reports pattern matches only, with no binding or edge creation. |
| `route_group_candidates` | Two normalized CFM `offsets` and an active-low duplicate-group interpretation for `C4_X15_Y8_N0`. Equal bits yield candidate presence/absence; disagreement blocks that interpretation. Atomic ownership and current-input scope are unproved. |
| `selector_qualification` | Four two-stage code tables, 960 `fields` with nine `[offset,xor]` terms each, and disjoint controlled/pairable/unresolved class lists. Decoding adds the retained qualification basis to active selector classes; it does not identify the source net. |
| `lut_context_candidates` | 240 `cells` with 16 native offsets, controlled minterm relabels, four-port assignments and segment index; eight `exact_sites` supply separate alternative codebooks. Both views remain `available_not_selected` on new inputs. |

`query model` exports these layouts without another toolchain. Preserve target,
geometry, polarity, denominators and declared scope when extending them. An
altered model needs its own reproducible observation and consumer checks.

## Schema names and IR

Public envelopes use `maxvell.*`. Core `maxvrec.*` names identify retained typed
schemas and require no external runtime. Terms and native coordinates are
technical identities; their presence does not establish legal placement or
logical connectivity. Storage-normalized masks, raw functional masks and
logical-minterm masks have different contracts. [Architecture](ARCHITECTURE.md).

The CLI reads/exports this snapshot; it has no model import or database writer.
See [new observations and model changes](../CONTRIBUTING.md#new-observations-and-model-changes)
for the contribution requirements and current regeneration boundary.
