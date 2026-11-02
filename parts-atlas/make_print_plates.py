"""Arrange the individual STLs, save PrusaSlicer projects, and slice MK4S plates.

Run after design.py has exported the individual parts. No printer is contacted.
Set PRUSASLICER to override the local PrusaSlicer executable.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'print-plates'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
ET.register_namespace('',NS)
PROFILES={'printer_model':'MK4S','printer_variant':'HF0.4',
    'nozzle_diameter':'0.4','nozzle_high_flow':'1',
    'bed_shape':'0x0,250x0,250x210,0x210','max_print_height':'220',
    'layer_height':'0.2','filament_type':'PLA','binary_gcode':'1',
    'complete_objects':'0'}


def slicer_path():
    choices=[os.environ.get('PRUSASLICER'),shutil.which('prusa-slicer'),
        shutil.which('PrusaSlicer'),
        '/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer',
        '/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer']
    for choice in choices:
        if choice and Path(choice).is_file():return str(choice)
    raise RuntimeError('Individual STLs are ready. Install PrusaSlicer or set PRUSASLICER to generate the plates.')


def settings(text):
    result={}
    for line in text.splitlines():
        line=line.removeprefix(';').strip()
        if '=' in line:
            key,value=line.split('=',1)
            result[key.strip()]=value.strip()
    return result


def check_settings(values):
    for key,expected in PROFILES.items():
        assert values.get(key)==expected,(key,values.get(key),expected)
    assert values['printer_settings_id']=='Original Prusa MK4S HF0.4 nozzle'
    assert values['filament_settings_id'].strip('"')=='Generic PLA @MK4S HF0.4'
    for key in ('print_host','printhost_apikey','physical_printer_settings_id'):
        assert not values.get(key),f'Unexpected machine-specific setting: {key}'


def plans():
    # Coordinates are in the MK4S's 250 x 210 mm XY system. All bottoms at Z=0.
    return [
        {'name':'00-fit-sample','repeat':1,'sample':True,
         'objects':[('fit-rail',41,83,0),('fit-slider',43.2,109,0)]},
        {'name':'01-case-print-4x','repeat':4,'sample':False,
         'objects':[('case',41,47,0)]},
        {'name':'02-kit-abc-print-3x','repeat':3,'sample':False,
         'objects':[('lid',8.7,23.2,90),('bin-double',131.5,19.2,0),
            ('bin-small',128.9,78.4,0),('bin-small',188.1,78.4,0),
            ('bin-small',128.9,137.6,0),('bin-small',188.1,137.6,0)]},
        {'name':'03-kit-d-print-1x','repeat':1,'sample':False,
         'objects':[('lid',8.7,23.2,90),('bin-double',131.5,19.2,0),
            ('bin-double',131.5,78.4,0),('bin-small',128.9,137.6,0),
            ('bin-small',188.1,137.6,0)]},
    ]


def positioned_mesh(name,x,y,angle):
    mesh=trimesh.load(ROOT/(name+'.stl'))
    assert mesh.is_watertight and mesh.is_winding_consistent,name
    if angle:mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(angle),(0,0,1)))
    mesh.apply_translation(-mesh.bounds[0])
    mesh.apply_translation((x,y,0))
    return mesh


def verify_layout(meshes):
    bounds=[mesh.bounds for mesh in meshes]
    for low,high in bounds:
        assert low[0]>=6 and low[1]>=6 and high[0]<=244 and high[1]<=204
        assert abs(low[2])<1e-6 and high[2]<=220
    min_gap=float('inf')
    for i,(lo,hi) in enumerate(bounds):
        for lo2,hi2 in bounds[i+1:]:
            gap=np.maximum(np.maximum(lo2[:2]-hi[:2],lo[:2]-hi2[:2]),0)
            distance=float(np.linalg.norm(gap))
            assert distance>=5.99,('Plate spacing',distance)
            min_gap=min(min_gap,distance)
    return None if min_gap==float('inf') else round(min_gap,3)


def write_input_3mf(path,objects,meshes):
    model=ET.Element(f'{{{NS}}}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    ET.SubElement(model,f'{{{NS}}}metadata',{'name':'Title'}).text=path.stem
    resources=ET.SubElement(model,f'{{{NS}}}resources')
    build=ET.SubElement(model,f'{{{NS}}}build')
    for index,(obj,mesh) in enumerate(zip(objects,meshes),1):
        element=ET.SubElement(resources,f'{{{NS}}}object',{'id':str(index),'type':'model','name':f'{obj[0]}-{index}'})
        geometry=ET.SubElement(element,f'{{{NS}}}mesh')
        verts=ET.SubElement(geometry,f'{{{NS}}}vertices')
        for v in mesh.vertices:
            ET.SubElement(verts,f'{{{NS}}}vertex',dict(zip(('x','y','z'),(f'{n:.9f}' for n in v))))
        faces=ET.SubElement(geometry,f'{{{NS}}}triangles')
        for face in mesh.faces:
            ET.SubElement(faces,f'{{{NS}}}triangle',dict(zip(('v1','v2','v3'),map(str,face))))
        ET.SubElement(build,f'{{{NS}}}item',{'objectid':str(index)})
    content='''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',content)
        z.writestr('_rels/.rels',rels)
        z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))


def meshes_from_project(path):
    with zipfile.ZipFile(path) as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        config=settings(z.read('Metadata/Slic3r_PE.config').decode())
    check_settings(config)
    ns={'m':NS};objects={}
    for obj in model.findall('m:resources/m:object',ns):
        vertices=obj.findall('m:mesh/m:vertices/m:vertex',ns)
        faces=obj.findall('m:mesh/m:triangles/m:triangle',ns)
        assert vertices and faces,'Expected independently editable mesh objects'
        objects[obj.attrib['id']]=trimesh.Trimesh(
            vertices=[[float(v.attrib[k]) for k in ('x','y','z')] for v in vertices],
            faces=[[int(f.attrib[k]) for k in ('v1','v2','v3')] for f in faces],process=True)
    meshes=[]
    for item in model.findall('m:build/m:item',ns):
        mesh=objects[item.attrib['objectid']].copy()
        if 'transform' in item.attrib:
            values=np.array(list(map(float,item.attrib['transform'].split()))).reshape(4,3)
            transform=np.eye(4);transform[:3,:]=values.T
            mesh.apply_transform(transform)
        meshes.append(mesh)
    return meshes,config


def run(command,log):
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    log.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f'PrusaSlicer failed ({result.returncode}):\n{result.stdout[-6000:]}')
    if re.search(r'(?:^|\n)(?:ERROR|FATAL)',result.stdout,re.I):
        raise RuntimeError(result.stdout)
    return result.stdout


def plate_diagram(entries):
    colors={'case':'#505b66','lid':'#eea242','bin-small':'#65a6c4',
            'bin-double':'#65a6c4','fit-rail':'#505b66','fit-slider':'#eea242'}
    lines=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 600">',
        '<rect width="620" height="600" fill="#fafafa"/>',
        '<g font-family="sans-serif" fill="#222">',
        '<text x="20" y="22" font-size="16">Parts Atlas · MK4S plates · 250 × 210 mm</text>']
    for i,entry in enumerate(entries):
        ox=25+(i%2)*305;oy=65+(i//2)*275
        lines.append(f'<text x="{ox}" y="{oy-14}" font-size="12">{entry["name"]}</text>')
        lines.append(f'<rect x="{ox}" y="{oy}" width="250" height="210" fill="white" stroke="#777"/>')
        for j,(name,x,y,angle) in enumerate(entry['objects'],1):
            mesh=positioned_mesh(name,x,y,angle);w,d,_=mesh.extents
            sy=oy+210-y-d
            lines.append(f'<rect x="{ox+x:.2f}" y="{sy:.2f}" width="{w:.2f}" height="{d:.2f}" rx="2" fill="{colors[name]}"/>')
            lines.append(f'<text x="{ox+x+w/2:.2f}" y="{sy+d/2+4:.2f}" fill="white" text-anchor="middle" font-size="12">{j}</text>')
        text='Fit sample — print once' if entry['sample'] else f'Full set — print this plate {entry["repeat"]} time(s)'
        lines.append(f'<text x="{ox}" y="{oy+230}" font-size="12">{text}</text>')
    lines.extend(['</g>','</svg>'])
    return '\n'.join(lines)+'\n'


def main():
    slicer=slicer_path()
    check_settings(settings((ROOT/'mk4s-pla.ini').read_text()))
    report={'printer':'Original Prusa MK4S','nozzle':'0.4 mm high-flow',
        'bed_mm':[250,210],'material_profile':'Generic PLA @MK4S HF0.4',
        'layer_height_mm':.2,'sequential_printing':False,'plates':[]}
    totals=Counter()
    with tempfile.TemporaryDirectory(prefix='parts-atlas-plates-') as temporary:
        work=Path(temporary)
        canonical=work/'mk4s-canonical.ini'
        run([slicer,'--load',str(ROOT/'mk4s-pla.ini'),'--save',str(canonical)],work/'config.log')
        check_settings(settings(canonical.read_text()))
        embedded='\n'.join(line if line.startswith(';') else '; '+line
                           for line in canonical.read_text().splitlines())+'\n'
        for entry in plans():
            name=entry['name'];raw=work/(name+'-input.3mf')
            arranged=work/(name+'.3mf');gcode=work/(name+'.bgcode')
            expected=[positioned_mesh(*obj) for obj in entry['objects']]
            gap=verify_layout(expected)
            write_input_3mf(raw,entry['objects'],expected)
            run([slicer,'--load',str(ROOT/'mk4s-pla.ini'),'--dont-arrange',
                '--export-3mf','--output',str(arranged),str(raw)],work/(name+'-project.log'))
            # The CLI's geometry export omits print settings. Add the complete
            # canonical config in PrusaSlicer's native 3MF project format.
            with zipfile.ZipFile(arranged,'a',zipfile.ZIP_DEFLATED) as z:
                z.writestr('Metadata/Slic3r_PE.config',embedded)
            actual,config=meshes_from_project(arranged)
            assert len(actual)==len(expected),(name,'Object count changed')
            for planned,loaded in zip(expected,actual):
                assert np.allclose(planned.bounds,loaded.bounds,atol=.002),(name,'Placement changed',planned.bounds,loaded.bounds)
                assert loaded.is_watertight and loaded.is_winding_consistent
            verify_layout(actual)
            log=run([slicer,'--dont-arrange','--export-gcode','--output',str(gcode),str(arranged)],work/(name+'-slice.log'))
            assert gcode.exists() and gcode.stat().st_size>1000
            assert gcode.read_bytes()[:4]==b'GCDE','Expected binary G-code'
            counts=Counter(o[0] for o in entry['objects'])
            if not entry['sample']:
                totals.update({k:q*entry['repeat'] for k,q in counts.items()})
            report['plates'].append({'name':name,'print_count':entry['repeat'],
                'sample_only':entry['sample'],'object_count':len(actual),
                'parts_per_plate':dict(counts),'minimum_part_gap_mm':gap,
                'minimum_bed_edge_margin_mm':round(min(min(m.bounds[0][0],m.bounds[0][1],250-m.bounds[1][0],210-m.bounds[1][1]) for m in actual),3),
                'placement_round_trip_passed':True,'slicing_succeeded':True,
                'project_sha256':hashlib.sha256(arranged.read_bytes()).hexdigest(),
                'bgcode_sha256':hashlib.sha256(gcode.read_bytes()).hexdigest(),
                'positions':[{'part':o[0],'x_mm':o[1],'y_mm':o[2],'rotation_deg':o[3]} for o in entry['objects']],
                'slicer_log_summary':log.replace(str(work),'<temporary>').splitlines()[-12:]})
            print('Ready:',name,dict(counts),flush=True)
        bom=json.loads((ROOT/'dimensions.json').read_text())['bill_of_materials']
        assert dict(totals)==bom,('Print counts do not match individual-STL bill of materials',totals,bom)
        report['full_set_quantities']=dict(totals)
        report['full_set_print_runs']=sum(e['repeat'] for e in plans() if not e['sample'])
        OUT.mkdir(exist_ok=True)
        for entry in plans():
            for suffix in ('.3mf','.bgcode'):
                shutil.copy2(work/(entry['name']+suffix),OUT/(entry['name']+suffix))
        (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        (OUT/'plate-layouts.svg').write_text(plate_diagram(plans()))
    print('Validated full set:',dict(totals),flush=True)


if __name__=='__main__':main()
