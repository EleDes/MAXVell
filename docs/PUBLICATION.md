# Repository contents

The repository includes the decoder, typed storage and functional IR tools,
partial HDL/Quartus project emitters, read-only database queries, UFM exports,
technical models, synthetic examples, tests and documentation.
The own [Quartus starter](QUARTUS_CONTROL.md) generates isolated test projects
and reads their fitted node locations; [experiment guidance](EXPERIMENTS.md)
describes how to establish and limit new reconstruction claims.
All 27 model families, including [scoped candidates](CANDIDATES.md), are usable
from the checkout. [Usage](USAGE.md) covers their entry points and limitations.

The public path retains packet/storage decoding, candidate analysis, bounded
functional composition, evaluation and project emission. Exact-input compile
certificates are not transferred into a general public equality grant. New
projects must be compared on their own inputs. A complete regeneration procedure
for every model is not included; the existing consumers require no acquisition
or historical test files. [Development guide](../CONTRIBUTING.md).
The [scope tables](STATUS.md) distinguish storage decoding, functional
interpretation and project generation for each supported family.

The compact database contains every runtime model used by these tools.
Model acquisition is described in [PROVENANCE](PROVENANCE.md); schemas,
populations and model formats are in [DATA](DATA.md).

Vendor tools, manuals, raw architecture reports, device-data files and vendor
HDL implementations are external resources. They are not included in this
repository; [REFERENCES](REFERENCES.md) links to the related tools and documents.
The optional [HDL check](CHECKS.md#independent-emitted-hdl-example) reads the
primitive model from a locally supplied installation.

Input-specific generated files belong under `work/`, which Git ignores.
The synthetic examples contain no original third-party input designs or
creator/comment records. [License details](../LICENSES.md).
