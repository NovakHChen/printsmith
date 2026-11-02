"""Parts Atlas v1. Millimeters. Generate closed STL meshes and preview data.

Requires numpy, manifold3d and trimesh. Run: python design.py
Printer reference: ../PRINTER.md
This is a prototype; validate the rail coupon before printing four cases.
"""
from pathlib import Path
import json
import numpy as np
import manifold3d as m
import trimesh

OUT = Path(__file__).resolve().parent
PITCH = 54.0
W, D, H = 168.0, 116.0, 48.4
FLOOR, CUP_H, CUP_WALL = 2.4, 40.0, 1.8
LID_Z, LID_T = 42.8, 2.4


def block(w, d, h, x=0, y=0, z=0):
    return m.Manifold.cube((w, d, h)).translate((x, y, z))


def rr(w, d, r):
    return m.CrossSection.square((w - 2*r, d - 2*r), center=True).offset(
        r, circular_segments=32)


def rounded(w, d, h, r, x=0, y=0, z=0):
    return rr(w, d, r).extrude(h).translate((x+w/2, y+d/2, z))


def yz_prism(points, width, x=0):
    # Local (u,v,w) becomes world (x+w,u,v).
    section = m.CrossSection([points])
    return section.extrude(width).transform([[0,0,1,x],[1,0,0,0],[0,1,0,0]])


def make_case():
    case = rounded(W,D,H,5)
    case -= rounded(W-6,D-6,40.21,3,3,3,FLOOR)
    # Rails: 0.4 mm sideways clearance per edge; 0.2 below / 0.4 above.
    # A single XZ tool avoids coincident seams between the channel and its
    # 45-degree roof. The cut overlaps the lower cavity by 0.01 mm.
    profile=[(1.8,42.6),(W-1.8,42.6),(W-1.8,45.6),(W-3,46.8),
             (W-3,50),(3,50),(3,46.8),(1.8,45.6)]
    tool=m.CrossSection([profile]).extrude(D-2).transform(
        [[1,0,0,0],[0,0,1,-1],[0,1,0,0]])
    case -= tool
    # Open the front above the entry ledge, leaving the back as a hard stop.
    case -= block(W+2,4.2,H-42.59+1,-1,-1,42.59)
    # Recessed tape label and shallow grip grooves on the front.
    label = rounded(68,12,0.65,2).rotate((90,0,0)).translate((50,.6,24))
    case -= label
    for x in (13,20,27,138,145,152):
        case -= block(2,.6,16,x,-.05,12)
    return case


def make_cup(cells=1):
    w,d = cells*PITCH-.8, PITCH-.8
    cup = rounded(w,d,CUP_H,3.6)
    iw,id_ = w-2*CUP_WALL, d-2*CUP_WALL
    # A 3 mm internal chamfer helps scoop small parts out of the bottom.
    lower = rr(iw-6,id_-6,2).extrude(3,scale_top=(iw/(iw-6),id_/(id_-6)))
    lower = lower.translate((w/2,d/2,1.8))
    upper = rounded(iw,id_,CUP_H,2*iw/(iw-6),CUP_WALL,CUP_WALL,4.79)
    cup -= lower + upper
    # Full-height rim with an inward label / grip ledge; 45-degree underside.
    back = d-CUP_WALL
    tab = yz_prism([(back+1,34),(back+1,40),(back-5,40)],22,w/2-11)
    cup += tab
    return cup


def make_lid():
    lid = rounded(163.6,112.2,LID_T,1,2.2,.4)
    # Three short ribs give purchase without encroaching on either rail.
    for y in (7,10,13):
        lid += rounded(30,1.4,1.2,.6,69,y,LID_T-.01)
    # Recess for a paper / tape label. Decorative inset contour lines.
    lid -= rounded(56,15,.6,2,56,24,LID_T-.4)
    for w,d in ((120,54),(104,38),(88,22)):
        ring = rr(w,d,9)-rr(w-1.2,d-1.2,8.4)
        lid -= ring.extrude(.4).translate((84,77,LID_T-.3))
    return lid


def to_trimesh(solid):
    mesh=solid.to_mesh()
    result=trimesh.Trimesh(vertices=np.array(mesh.vert_properties)[:,:3],
                         faces=np.array(mesh.tri_verts),process=True)
    # Remove zero-area seams collapsed by STL's float32 precision.
    result.update_faces(result.nondegenerate_faces(height=1e-5))
    result.update_faces(result.unique_faces())
    result.remove_unreferenced_vertices()
    return result


def layouts():
    common=[(0,0,2),(2,0,1),(0,1,1),(1,1,1),(2,1,1)]
    return [common,common,common,[(0,0,2),(2,0,1),(0,1,2),(2,1,1)]]


def build():
    parts={'case':make_case(),'lid':make_lid(),'bin-small':make_cup(1),
           'bin-double':make_cup(2)}
    parts['fit-rail']= (parts['case'] ^ block(W,18,H,0,38,0)).translate((0,-38,0))
    parts['fit-slider']= (parts['lid'] ^ block(W,18,10,0,38,-1)).translate((0,-38,0))
    report={}
    preview={}
    for name, solid in parts.items():
        mesh=to_trimesh(solid)
        assert solid.status()==m.Error.NoError,(name,solid.status())
        assert mesh.is_watertight and mesh.is_winding_consistent,name
        assert len(solid.decompose())==1,name
        assert mesh.volume>0,name
        extent=mesh.extents
        assert extent[0]<=250 and extent[1]<=210 and extent[2]<=220,name
        mesh.export(OUT/(name+'.stl'))
        reloaded=trimesh.load(OUT/(name+'.stl'))
        assert reloaded.is_watertight and reloaded.is_winding_consistent,name
        report[name]={'watertight':True,'connected_solids':1,
            'dimensions_mm':np.round(extent,3).tolist(),
            'volume_cm3':round(mesh.volume/1000,3),'triangles':len(mesh.faces),
            'fits_MK4S_250x210x220':True}
        if name in ('case','lid','bin-small','bin-double'):
            preview[name]={'v':np.round(mesh.vertices,3).tolist(),'f':mesh.faces.tolist()}
    closed_lid=parts['lid'].translate((0,0,LID_Z))
    assert (closed_lid ^ parts['case']).volume()<1e-5,'Lid/case collision'
    for slide in (0,-10,-40,-80,-120):
        assert (closed_lid.translate((0,slide,0)) ^ parts['case']).volume()<1e-5
    cup_instances=[]
    for col,row,cells in layouts()[3]:
        cup=parts['bin-double' if cells==2 else 'bin-small'].translate(
            (3.4+col*PITCH,4.4+row*PITCH,FLOOR))
        assert (cup ^ parts['case']).volume()<1e-5
        assert (cup ^ closed_lid).volume()<1e-5
        for other in cup_instances:
            assert (cup ^ other).volume()<1e-5
        cup_instances.append(cup)
    # Check the remaining three-bin row as well as the common layout.
    for layout in layouts()[:1]:
        row=[]
        for col,y,cells in layout:
            cup=parts['bin-double' if cells==2 else 'bin-small'].translate(
                (3.4+col*PITCH,4.4+y*PITCH,FLOOR))
            assert (cup ^ parts['case']).volume()<1e-5
            assert (cup ^ closed_lid).volume()<1e-5
            for other in row: assert (cup ^ other).volume()<1e-5
            row.append(cup)
    bom={'case':4,'lid':4,'bin-small':14,'bin-double':5}
    total=sum(report[n]['volume_cm3']*q for n,q in bom.items())
    report.update({'bill_of_materials':bom,'units':'mm',
        'all_nominal_fit_and_slide_collision_checks_passed':True,
        'nominal_bin_to_lid_gap_mm':.4,
        'layout':layouts(),'material_volume_cm3':round(total,1),
        'fully_solid_PLA_mass_g_at_1_24':round(total*1.24),
        'physical_fit_tested':False,'closure':'Sliding lid; external elastic/strap required for transport',
        'printer_config_source':'../PRINTER.md'})
    (OUT/'dimensions.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'preview-meshes.json').write_text(json.dumps(preview,separators=(',',':')))
    print(json.dumps(report,indent=2))


if __name__=='__main__': build()
