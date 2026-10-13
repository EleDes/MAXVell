# Where the models come from

MAXVell combines its own implementation and controlled test designs with
technical information obtained from the Altera Quartus II 13.1 toolchain.
The included models use compiler output, device queries, serialization
experiments and direct parsing of installed device-data files.

| Material | Acquisition and processing |
| --- | --- |
| POF storage mappings and polarity | Own controlled test designs and compiler/serialization experiments; configuration addresses are joined to observed storage positions |
| Field templates and selector encodings | Compiler-generated architecture reports, including diagnostic output; parsed into typed fields and numeric IO/LC tables |
| Resources, routing and functional predicates | Device/Chip Planner queries and diagnostic output, including own helpers calling internal library interfaces; records are normalized and joined to configuration mappings |
| Exact-device LC/LAB membership | Device queries and structural reads of installed device-data files, with coordinate/count checks; used to restrict exact-device model scope |
| LUT semantics, USER_CODE and UFM content/recipes | Own bit-pattern, content-order and compiler experiments; emitted UFM project templates use vendor primitive interfaces |
| ALOAD site support, retained-topology minterms and exact-pin I/O options | Own retained compiler/fit experiments; compact technical site, offset and relabel records, with their original scope limits |
| UFM source/sink codewords, input fingerprints and semantic-source profiles | Own controlled compiler/fit experiments; retained numerical patterns and interpretations. Input-specific qualification remains separate from public diagnostic pattern matching. |
| Duplicate route group, selector qualifications and layout-conditioned LUT codebooks | Own controlled, held-out and layout/port experiments; compact numerical interpretations with unresolved ownership, source and context-selection limits retained. |
| Python tools, examples, documentation and diagrams | Own implementation, test designs and presentation of the results |

Diagnostic output and internal library interfaces were used during model
construction; these are separate from ordinary documented Quartus commands.
Direct device-file parsing also contributes to exact-device membership and
scope. The models therefore do not come exclusively from compiler experiments
or from documented public queries.

The snapshot retains numerical encodings, resource coordinates and configuration
predicates derived from that tool/device information, together with the project's
own storage joins and interpretations. Records are grouped by exact target and
model kind, with identical model contents shared by checksum. See the
[data formats](DATA.md) and [functional scope](STATUS.md).

All runtime models are included. The published tools read this snapshot directly;
they do not regenerate it from an installed Quartus toolchain. Quartus and a
simulator are used separately when compiling or simulating emitted designs.

[MAX V architecture](https://docs.altera.com/v/u/docs/654763/max-v-architecture-max-v-device-handbook-section-i-chapter-2)
and [public references](REFERENCES.md) provide the product context.
[Licenses](../LICENSES.md) and [repository contents](PUBLICATION.md) describe
the included material and external resources.
