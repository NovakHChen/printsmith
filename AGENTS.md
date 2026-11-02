# 3D printing project workflow

The user currently requires both individual parts and prepared print plates:

- Generate a separate STL for each distinct printable part type before arranging plates.
- Also deliver prearranged PrusaSlicer `.3mf` projects covering all required parts and quantities, so the user can open a complete plate without importing and placing individual STLs.
- When PrusaSlicer is available, include sliced `.bgcode` for each plate alongside the `.3mf` projects. Keep the individual STLs as maintained deliverables.
- Until the user changes the printer, use the Original Prusa MK4S, its 250 × 210 mm bed and 220 mm maximum height, and the installed 0.4 mm high-flow nozzle. PLA is the current default material.
- State the actual filament profile used. Check the embedded printer model and high-flow nozzle settings; an old Device Dock slicer project uses an MK4 profile and is not the current MK4S setup.
- Preserve placement, keep parts independently editable, validate bed margins and part separation, and provide clear print counts for repeated plates. Plate quantities must match the individual-part bill of materials.
- Keep the plate generation source, printer configuration, and layout manifest with the project. Regeneration should export the individual STLs first and then rebuild the plate projects and sliced files.
- Apply this to new or revised work. Preserve archived revisions.
