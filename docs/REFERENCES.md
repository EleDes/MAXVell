# Tools and public references

The ordinary decoder, IR tools and reconstruction drafts run with Python alone.
Quartus and a simulator are optional tools for collecting new observations and
checking fitted or emitted designs. External manuals, installers, device packages
and simulation libraries are linked here; none are redistributed in this repository.
See [model provenance](PROVENANCE.md) for the included technical models.

## Get the tools

| Tool | Direct official entry point | What to install or check |
| --- | --- | --- |
| Python | [Downloads](https://www.python.org/downloads/) · [Windows](https://www.python.org/downloads/windows/) | Use a maintained Python release; 3.14 is a tested branch. The compatibility floor is 3.10, which reached end of life in October 2026. No third-party Python runtime packages are required. |
| Git | [Installation](https://git-scm.com/install/) | For cloning and contributions. It is unnecessary when running an unpacked source archive. |
| Quartus Prime Lite 25.1 | [Windows](https://www.altera.com/downloads/fpga-development-tools/quartus-prime-lite-edition-design-software-version-25-1-windows) · [Linux](https://www.altera.com/downloads/fpga-development-tools/quartus-prime-lite-edition-design-software-version-25-1-linux) | Install Quartus **and MAX II/MAX V device support**, not only the programmer. The checked Windows build is `25.1std.0 Build 1129`; its device package is `max-25.1std.0.1129.qdz`. |
| Quartus II Web 13.1, historical reproduction | [Windows](https://www.altera.com/downloads/fpga-development-tools/quartus-ii-web-edition-design-software-version-13-1-windows) · [Linux](https://www.altera.com/downloads/fpga-development-tools/quartus-ii-web-edition-design-software-version-13-1-linux) | The retained routing/ECO observations use **13.1.4 Build 182**, not the base 13.1.0 installer. Install matching MAX support and Update 4 when reproducing that version. |
| Questa Altera FPGA / Starter | The **Individual Files** section of the Lite 25.1 download pages above · [Simulator guidance](https://www.altera.com/design/guidance/software/modelsim) · [Licensing](https://www.altera.com/support/support-resources/licensing/support-center) | Optional for the [emitted-HDL check](CHECKS.md#independent-emitted-hdl-example). The installer is `QuestaSetup-25.1std.0.1129-windows.exe`; the simulator engine is 2025.2. Starter still requires its zero-cost license file. Use your installed vendor simulation atoms. |

The Altera pages list the installers and checksums; their download actions require
a MyAltera sign-in. Follow those supported download pages rather than assuming an
anonymous binary URL. Linux links are provided for access; the retained checks
were performed on Windows.

For Quartus experiments, make `quartus_sh`, `quartus_cdb`, `quartus_sta` and
`quartus_asm` available from the same installation. Its Tcl packages are bundled
with Quartus; a separate Tcl installation does not supply the Chip Planner APIs.
Check the actual tool version and exact target before comparing results. Start
with [usage](USAGE.md), the [control example](QUARTUS_CONTROL.md) and
[experiment design](EXPERIMENTS.md).

## POF container and MAX V hardware

| Reference | Useful scope |
| --- | --- |
| [Data I/O 3980/3900/2900 User Manual: POF Format, Code 14](https://download.dataio.com/ftp/main/2939u_book1.pdf#page=163), printed pp. 5-9–5-11 | Historical packet description, tag vocabulary and terminator rules. This is a programmer manual describing older Altera MAX devices, not a complete MAX V binary specification. A [separate archived copy of the three-page section](https://web.archive.org/web/20110715093822id_/http://www.pldtool.com/pdf/fmt_pof.pdf) is also available. See our [implementation and its limits](POF_FORMAT.md). |
| [MAX V documentation index](https://docs.altera.com/r/docs/783862/current/max-v-featured-documentation-quick-links-guide/max-v-featured-documentation-quick-links) | Entry point for the handbook, UFM, electrical characteristics, power-up behavior and device resources. |
| [MAX V architecture, handbook chapter 2](https://docs.altera.com/v/u/docs/654763/max-v-architecture-max-v-device-handbook-section-i-chapter-2) | LE/LAB structure, LUT/register modes, I/O elements and global resources. Architecture terminology does not by itself establish a POF bit mapping. |
| [User Flash Memory, chapter 7, May 2014; MAX V handbook (Mouser mirror)](https://www.mouser.com/datasheet/2/612/max5_handbook-1098935.pdf#page=105) | UFM organization, interface and operating modes. Physical UFM behavior and this repository's content-order mapping or bounded recipes are separate claims. |
| [JTAG and in-system programmability, chapter 6 (PDF)](https://docs.altera.com/api/khub/documents/~HgjyYhcd4SGDTwYdfyEmg/content) | Configuration, ISP, security and JTAG operations; these are distinct from POF parsing and recovered logic. |
| [JTAG boundary-scan testing, chapter 8 (PDF)](https://docs.altera.com/api/khub/documents/GG9mTmJDtoJFMATpM2GKwA/content) · [BSDL files](https://www.altera.com/design/devices/resources/models/bsdl) | Device/package scan descriptions and observation limits. BSDL describes boundary scan, not internal LUT/routing storage. |
| [MAX V pin connection guidelines, PCG-01012 (PDF)](https://docs.altera.com/api/khub/documents/rQuQuELn14Enh~I28qmpHQ/content) · [Device pinouts](https://www.altera.com/design/devices/resources/pinouts) | Check the exact package, supply banks, dedicated pins and permitted pin roles before a fit or hardware experiment. |

## Quartus controls and scripting

- [Quartus Standard synthesis options](https://docs.altera.com/r/docs/683283/18.1/design-compilation-user-guide-quartus-prime-standard-edition/quartus-prime-synthesis-options?contentId=rvzN3Z6Z6OBvNpRbrfW4jw),
  including separate keep/preserve/dont_merge/noprune controls.
- [Standard Signal Probe and ECO guidance](https://docs.altera.com/r/docs/683283/18.1/design-compilation-user-guide-quartus-prime-standard-edition/signal-probe-pins-and-engineering-change-orders?contentId=EHmCF_RYVo9nTvTV37FQRA).
- [Altera Tcl scripting support](https://www.altera.com/design/guidance/software/sof-qts-scripting).
  Use the installed executable's help for its actual command syntax, packages and
  device restrictions. The [retained RCF/ECO observations](QUARTUS_CONTROL.md#routing-and-saved-eco-experiments)
  explain a MAX V result that is narrower than general API support.
- [Quartus programming-file types](https://docs.altera.com/r/docs/683039/25.3.1/quartus-prime-pro-edition-user-guide/secondary-programming-files-convert-programming-files).
  This newer **Pro** guide is file-type context; it does not establish MAX V
  support or a preservation recipe for Lite/Standard.

## Related projects

- [Project Chibi](https://github.com/ArcaneNibble/project-chibi), external MAX V
  bitstream research.
- [emtenet/max-v-fuse-map](https://github.com/emtenet/max-v-fuse-map), experimental
  MAX V fuse mapping through Quartus input/output observations, with fuse and
  interconnect databases and Rust tooling
  ([ISC license](https://github.com/emtenet/max-v-fuse-map/blob/main/LICENCE)).
- [Bitstream spreadsheet DSL](https://github.com/ArcaneNibble/bitstream-spreadsheet-dsl).
- [nextpnr](https://github.com/YosysHQ/nextpnr), related place-and-route research.

These projects are references, not runtime dependencies. Their source/data files
are not copied here, and their findings do not validate this repository's models
without a checked binding and independent comparison.

## Repository licenses

- [0BSD](https://opensource.org/license/0bsd) for the software.
- [CC0-1.0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en)
  for own data, diagrams and documentation; see [LICENSES](../LICENSES.md).

Those grants apply to this repository's material. Linked third-party tools and
documents retain their own terms.
