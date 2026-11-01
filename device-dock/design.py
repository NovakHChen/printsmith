"""Device Dock v2 — dimensions in mm. Requires cadquery==2.8.0.

Run: python design.py
STEP is an editable solid; this script retains the design parameters.
"""
from pathlib import Path
import json
import cadquery as cq

OUT = Path(__file__).resolve().parent
BASE_X, BASE_Y, BASE_Z = 104.0, 120.0, 8.0
WALL = 6.0
GAPS = [19.0, 12.0, 19.0]  # MacBook / iPad with case / Kindle with case
HEIGHTS = [64.0, 64.0, 46.0, 34.0]  # above slot floor
LENGTHS = [100.0, 100.0, 92.0, 84.0]
DEVICE_NAMES = ["MacBook Pro 14", "iPad Pro 11 with case", "Kindle Paperwhite with case"]
ASSUMED_DEVICE_THICKNESSES = [15.5, None, None]
FIT_BASIS = ["Original 19 mm laptop opening retained",
             "Owner reports the original 12 mm Kindle opening fits the cased iPad",
             "Owner reports the original 19 mm MacBook opening fits the cased Kindle"]


def rounded_plate(x, y, h, radius, z=0):
    return (cq.Workplane("XY").box(x, y, h, centered=(True, True, False))
            .edges("|Z").fillet(radius).translate((0, 0, z)))


def make_holder():
    assert len(GAPS) == 3 and all(gap > 0 for gap in GAPS)
    assert len(HEIGHTS) == len(LENGTHS) == 4
    # Keep the wider v2 fins clear of the decorative side grooves.
    assert sum(GAPS) + 4*WALL <= 76, "Wall span exceeds groove clearance"
    # Two terraces: broad lower footprint and inset upper deck.
    lower = rounded_plate(BASE_X, BASE_Y, 4.0, 14.0)
    lower = lower.faces(">Z").edges().chamfer(0.7)
    lower = lower.faces("<Z").edges().chamfer(0.4)
    upper = rounded_plate(BASE_X-8, BASE_Y-8, 4.5, 11.0, 3.5)
    upper = upper.faces(">Z").edges().chamfer(0.8)
    body = lower.union(upper)

    # Paired inset pill grooves echo the rounded outline of the base.
    for side in (-1, 1):
        for x, length in [(44.5, 80.0), (40.0, 58.0)]:
            groove = (cq.Workplane("XY").workplane(offset=BASE_Z-1.1)
                      .center(side*x, 0).slot2D(length, 2.0, angle=90)
                      .extrude(1.3))
            body = body.cut(groove)

    span = sum(GAPS) + 4*WALL
    left = -span/2
    slot_data = []
    # Fillet each fin before fusing. Vertical corners and crowns form soft
    # entries; full-width parallel faces remain below the rounded crowns.
    for i, (height, length) in enumerate(zip(HEIGHTS, LENGTHS)):
        center = left + WALL/2
        fin = rounded_plate(WALL, length, height+0.5, 2.5, BASE_Z-0.5)
        fin = fin.faces(">Z").edges().fillet(1.5)
        body = body.union(fin.translate((center, 0, 0)))
        left += WALL
        if i < 3:
            slot_data.append({
                "device": DEVICE_NAMES[i],
                "x_min": left, "x_max": left+GAPS[i],
                "gap_mm": GAPS[i], "center_x": left+GAPS[i]/2,
                "assumed_device_thickness_mm": ASSUMED_DEVICE_THICKNESSES[i],
                "raw_total_clearance_mm": (round(GAPS[i]-ASSUMED_DEVICE_THICKNESSES[i], 3)
                                           if ASSUMED_DEVICE_THICKNESSES[i] is not None else None),
                "fit_basis": FIT_BASIS[i],
                "minimum_wall_height_mm": min(HEIGHTS[i:i+2]),
            })
            left += GAPS[i]
    return body.clean(), slot_data


def validate(body, slots, step_path):
    shape = body.val()
    assert shape.isValid(), "Invalid source solid"
    assert len(shape.Solids()) == 1, "Holder must be one connected solid"
    bb = shape.BoundingBox()
    assert max(abs(a-b) for a,b in zip(
        [bb.xlen, bb.ylen, bb.zlen], [BASE_X, BASE_Y, BASE_Z+max(HEIGHTS)])) < 1e-5
    for slot in slots:
        # Verify full nominal gap, clear above the floor in the contact zone.
        gauge = (cq.Workplane("XY")
                 .box(slot["gap_mm"]-0.02, 60, 20, centered=(True, True, False))
                 .translate((slot["center_x"], 0, BASE_Z+0.01)))
        assert body.intersect(gauge).val().Volume() < 1e-6, slot["device"]
    loaded = cq.importers.importStep(str(step_path))
    assert loaded.val().isValid() and len(loaded.val().Solids()) == 1
    assert abs(loaded.val().Volume()-shape.Volume())/shape.Volume() < 1e-7
    return {"solid_valid": True, "solid_count": 1, "STEP_round_trip_passed": True,
            "nominal_slot_gauges_passed": True,
            "bounding_box_mm": [bb.xlen, bb.ylen, bb.zlen],
            "solid_volume_cm3": shape.Volume()/1000,
            "note": "Geometric checks only; physical fit and loaded stability require a prototype."}


if __name__ == "__main__":
    holder, slots = make_holder()
    cq.exporters.export(holder, str(OUT/"device_dock_v2.step"))
    # Check exact CAD bounds before a tessellation cache is attached by STL export.
    report = validate(holder, slots, OUT/"device_dock_v2.step")
    cq.exporters.export(holder, str(OUT/"device_dock_v2.stl"),
                        tolerance=0.05, angularTolerance=0.1)
    # A short section of the actual holder tests all three gaps inexpensively.
    coupon = holder.intersect(cq.Workplane("XY").box(
        110, 22, 26, centered=(True, True, False)))
    assert coupon.val().isValid() and len(coupon.val().Solids()) == 1
    cq.exporters.export(coupon, str(OUT/"fit_coupon_v2.stl"),
                        tolerance=0.05, angularTolerance=0.1)
    (OUT/"dimensions.json").write_text(json.dumps({
        "revision": 2, "units": "mm", "base": [BASE_X, BASE_Y, BASE_Z],
        "wall_thickness": WALL, "wall_heights_above_floor": HEIGHTS,
        "wall_lengths": LENGTHS, "slots": slots, "validation": report}, indent=2)+"\n")
    print(json.dumps(report, indent=2))
