# Printsmith

Personal 3D printing projects for an Original Prusa MK4S with a 0.4 mm high-flow nozzle, primarily using PLA.

Each project lives in its own folder at the repository root. Project folders contain editable CAD source, STL exports, a preview, and design/printing notes. STEP solids are included where available. Previous revisions live in a project's `archive/` folder.

## Projects

| Project | Description | Current revision |
| --- | --- | --- |
| [Device Dock](device-dock/README.md) | Three-slot vertical holder for a MacBook, cased iPad, and cased Kindle | v2 — 19 / 12 / 19 mm |
| [Parts Atlas](parts-atlas/README.md) | Four independent cases with 19 removable bins and sliding lids | v1 prototype — physical fit untested |

See [PRINTER.md](PRINTER.md) for the printer setup. New and revised designs must include individual STL exports plus prearranged PrusaSlicer `.3mf` plates covering the required quantities. Include sliced `.bgcode` files when PrusaSlicer is available. Use the MK4S and its 250 × 210 mm bed until the owner changes the setup; see [AGENTS.md](AGENTS.md).

## CAD environment

Use Python 3.12 and a local virtual environment. The root requirements below are for Device Dock; Parts Atlas has its own requirements and regeneration commands in its project README.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python device-dock/design.py
python device-dock/render_preview.py
```

Model dimensions use millimeters. Keep source, STEP, STL, and preview files together, and regenerate exports after changing a design. `.3mf` slicer projects may be kept alongside the corresponding revision. Machine G-code is ignored by default because it depends on the selected printer, material, and slicing settings. Parts Atlas explicitly tracks its current `.bgcode` plates alongside the `.3mf` projects and the configuration used to slice them. The original Device Dock print's binary G-code is retained explicitly in its v1 archive for provenance.
