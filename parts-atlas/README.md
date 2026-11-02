# Parts Atlas — v1 prototype

A smaller reinterpretation of a 19-bin parts organizer: four independent cases,
14 square lift-out bins, five double-width bins, and four opaque sliding lids.
Print complete parts in contrasting filament colors; no multi-material unit is
required. Cases do not mechanically connect to one another.

![Parts Atlas](preview.png)

Each case measures **168 × 116 × 48.4 mm**. A 2 × 2 arrangement occupies
336 × 232 mm. Rounded bin interiors have a bottom scoop chamfer and inward
label/grip ledges. Lids have finger ribs, a label recess, and inset contour lines.

## Prepared print plates

Open a `.3mf` in PrusaSlicer as a project to load the complete arrangement and
printer settings. The matching `.bgcode` is already sliced. Every object remains
independently editable, and the individual STL files are retained below.

| Plate | Project | Sliced file | Print count |
| --- | --- | --- | --- |
| Fit sample: rail + slider | [00-fit-sample.3mf](print-plates/00-fit-sample.3mf) | [BGCODE](print-plates/00-fit-sample.bgcode) | Once first |
| One case | [01-case-print-4x.3mf](print-plates/01-case-print-4x.3mf) | [BGCODE](print-plates/01-case-print-4x.bgcode) | 4 |
| Kits A–C: one lid, four small bins, one double bin | [02-kit-abc-print-3x.3mf](print-plates/02-kit-abc-print-3x.3mf) | [BGCODE](print-plates/02-kit-abc-print-3x.bgcode) | 3, one color per kit |
| Kit D: one lid, two small bins, two double bins | [03-kit-d-print-1x.3mf](print-plates/03-kit-d-print-1x.3mf) | [BGCODE](print-plates/03-kit-d-print-1x.bgcode) | 1 |

The full set takes **8 plate runs**, plus the initial fit sample. Use the same
case plate four times; repeat the A–C plate once for each kit. Suggested colors
can be changed by loading a different spool between runs; no multi-material
printing is required. [Plate layout diagram](print-plates/plate-layouts.svg).

Files target the **Original Prusa MK4S, 0.4 mm high-flow nozzle, 250 × 210 mm bed**,
using the official **Generic PLA @MK4S HF0.4** preset: 230 °C first layer,
225 °C thereafter, 60 °C bed. Print overrides are 0.20 mm layers, 3 perimeters,
5 top/bottom layers, and 15% gyroid infill, with supports, brims and sequential
printing disabled. Use the `.3mf` and select the actual spool's filament preset
if its settings differ, then reslice. There is no need to arrange the parts.

## Individual print files

| STL | Full-set quantity | Purpose |
| --- | --- | --- |
| [case.stl](case.stl) | 4 | Case with sliding-lid tracks |
| [lid.stl](lid.stl) | 4 | Opaque sliding lid |
| [bin-small.stl](bin-small.stl) | 14 | 53.2 × 53.2 × 40 mm bin |
| [bin-double.stl](bin-double.stl) | 5 | 107.2 × 53.2 × 40 mm bin |
| [fit-rail.stl](fit-rail.stl) | 1 sample | Full-width, 18 mm long rail section |
| [fit-slider.stl](fit-slider.stl) | 1 sample | Matching slider sample |

Cases A–C each hold one double bin and four small bins. Case D holds two
double bins and two small bins. See [PRINTING.txt](PRINTING.txt) for layouts,
orientations, proposed slicer settings, and the sample-fit procedure.

## Prototype status

Designed around [our Original Prusa MK4S setup](../PRINTER.md), using PLA and
the installed 0.4 mm high-flow nozzle. Every individual part fits its nominal
build volume. Print the rail and slider samples first, then one complete case.
The design is intended to print without supports; inspect the sliced preview.

This revision has passed digital geometry checks but has not been physically
printed or tested. The lid has **no positive latch**: use a snug external elastic
band or reusable strap before carrying a closed case. The 0.4 mm nominal gap
above the bins is unsealed, so very fine contents can migrate between bins.

## Source and validation

[design.py](design.py) generates the individual STL files, [dimensions.json](dimensions.json),
and [preview-meshes.json](preview-meshes.json), then runs
[make_print_plates.py](make_print_plates.py) to produce the prepared `.3mf` and
`.bgcode` files. [mk4s-pla.ini](mk4s-pla.ini) records the complete slicing settings;
[the plate manifest](print-plates/manifest.json) records placements, quantities,
file hashes and validation results. This revision uses Manifold and
Trimesh and does not include STEP solids. Use its project-specific environment:

```sh
python3.12 -m venv parts-atlas/.venv
parts-atlas/.venv/bin/python -m pip install -r parts-atlas/requirements.txt
parts-atlas/.venv/bin/python parts-atlas/design.py
```

PrusaSlicer must be installed for the plate generation step. Set `PRUSASLICER`
to its executable path if it is not found automatically. To rebuild the plates
from existing individual STL exports, run `python parts-atlas/make_print_plates.py`.

Generation checks closed, consistently oriented meshes, one solid per source
part, STL reimport, build-volume limits, nominal bin clearances, and lid/case
clearance at five sampled slide positions. These checks do not establish print
tolerances, full swept-motion clearance, friction, spill resistance or durability.
Plate generation also checks exact object counts, STL-to-project placement,
at least 6 mm between parts, bed margins, the embedded MK4S/high-flow nozzle
configuration, binary G-code output, and successful slicing of every plate.
The prepared print counts produce exactly 4 cases, 4 lids, 14 small bins and
5 double bins, plus a separate sample. The PNG is a design preview.

Reference: [Amazon Basics 19-compartment organizer](https://www.amazon.com/dp/B08RZMKC9K).
