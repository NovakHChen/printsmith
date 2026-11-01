"""Render the exported STL, plus illustrative device envelopes, using a software renderer."""
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/ripple-mpl")
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json

ROOT = Path(__file__).resolve().parent
BG = (0.955, 0.949, 0.925)
reader = vtk.vtkSTLReader()
reader.SetFileName(str(ROOT/"ripple_dock_v1.stl"))
reader.Update()


def render(loaded=False):
    poly = reader.GetOutput()
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    tris = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1,3)
    meshes = [(pts[tris], (0.13,0.43,0.44))]
    if loaded:
        import cadquery as cq
        for x,t,w,h,color in [
            (-16.5,15.5,312.6,221.2,(0.44,0.48,0.51)),
            (3.5,5.9,178.5,247.6,(0.64,0.74,0.79)),
            (20,9.2,117,169,(0.80,0.71,0.54))]:
            obj = (cq.Workplane("XY").box(t,w,h,centered=(True,True,False))
                   .edges().fillet(min(2,t/3)).translate((x,0,8.8)))
            vertices, triangles = obj.val().tessellate(0.25)
            points = np.array([[v.x,v.y,v.z] for v in vertices])
            meshes.append((points[np.array(triangles)],color))
    width,height = (760,800) if loaded else (1080,800)
    # Orthographic software rasterizer with a per-pixel depth buffer. This
    # avoids OpenGL and painter-order artifacts between long parallel fins.
    tri = np.concatenate([mesh[0] for mesh in meshes])
    colors = []
    light = np.array([0.2,-0.5,1.0]); light /= np.linalg.norm(light)
    for faces,color in meshes:
        normal = np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
        normal /= np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
        intensity = 0.56+0.44*np.clip(normal@light,0,1)
        colors.append(np.clip(np.array(color)[None,:]*intensity[:,None]*255,0,255))
    colors = np.concatenate(colors).astype(np.uint8)
    eye = np.array([1.0,-1.35,0.95 if not loaded else 0.60])
    eye /= np.linalg.norm(eye)
    right = np.cross([0,0,1],eye); right /= np.linalg.norm(right)
    up = np.cross(eye,right)
    projected = np.stack([tri@right, -(tri@up), tri@eye],axis=-1)
    lo = projected[:,:,:2].min(axis=(0,1)); hi = projected[:,:,:2].max(axis=(0,1))
    supersample = 1.5
    w,h = int(width*supersample),int(height*supersample)
    scale = min((w-130*supersample)/(hi[0]-lo[0]),
                (h-150*supersample)/(hi[1]-lo[1]))
    projected[:,:,:2] = (projected[:,:,:2]-(lo+hi)/2)*scale+np.array([w/2,h/2])
    pixels = np.empty((h,w,3),dtype=np.uint8)
    pixels[:] = np.array(BG)*255
    depth = np.full((h,w),-np.inf)
    for t,color in zip(projected,colors):
        x0,x1 = max(0,int(np.floor(t[:,0].min()))),min(w-1,int(np.ceil(t[:,0].max())))
        y0,y1 = max(0,int(np.floor(t[:,1].min()))),min(h-1,int(np.ceil(t[:,1].max())))
        if x1<x0 or y1<y0: continue
        denom = (t[1,1]-t[2,1])*(t[0,0]-t[2,0])+(t[2,0]-t[1,0])*(t[0,1]-t[2,1])
        if abs(denom)<1e-9: continue
        xx,yy = np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        aa = ((t[1,1]-t[2,1])*(xx-t[2,0])+(t[2,0]-t[1,0])*(yy-t[2,1]))/denom
        bb = ((t[2,1]-t[0,1])*(xx-t[2,0])+(t[0,0]-t[2,0])*(yy-t[2,1]))/denom
        cc = 1-aa-bb
        zz = aa*t[0,2]+bb*t[1,2]+cc*t[2,2]
        old = depth[y0:y1+1,x0:x1+1]
        mask = (aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8)&(zz>old)
        old[mask] = zz[mask]
        pixels[y0:y1+1,x0:x1+1][mask] = color
    return Image.fromarray(pixels).resize((width,height),Image.Resampling.LANCZOS)


def font(size):
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        if Path(path).exists(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()


empty, loaded = render(), render(True)
canvas = Image.new("RGB", (1840,1160), tuple(int(v*255) for v in BG))
canvas.paste(empty,(0,135))
canvas.paste(loaded,(1080,135))
draw = ImageDraw.Draw(canvas)
ink,muted = "#183c3d", "#5c6d6a"
draw.text((62,35), "RIPPLE / 03", font=font(48), fill=ink)
draw.text((65,96), "Three-device vertical dock  /  Draft 01  /  PLA", font=font(22), fill=muted)
draw.text((65,153), "THE HOLDER", font=font(18), fill=muted)
draw.text((1130,153), "DEVICE SCALE STUDY", font=font(18), fill=muted)
draw.line((65,945,1775,945),fill="#bbc6bf",width=2)
draw.text((65,970), "120 x 104 mm base",font=font(28),fill=ink)
draw.text((65,1012), "72 mm maximum height",font=font(21),fill=muted)
draw.text((65,1047), "Stepped plinth / rounded fins / inset ripple grooves",font=font(20),fill=muted)
for x,title,value in [(690,"MACBOOK PRO 14","19 mm slot"),(1060,"IPAD PRO 11","9 mm slot"),(1420,"KINDLE PAPERWHITE","12 mm slot")]:
    draw.text((x,974),title,font=font(18),fill=muted)
    draw.text((x,1009),value,font=font(28),fill=ink)
draw.text((65,1110), "Fixed widths for bare devices. Device envelopes are illustrative; verify generation and actual thickness before a full print.",font=font(20),fill=muted)
canvas.save(ROOT/"preview.png")

# Closed manifold check on the actual exported STL.
edges = vtk.vtkFeatureEdges()
edges.SetInputConnection(reader.GetOutputPort())
edges.BoundaryEdgesOn()
edges.NonManifoldEdgesOn()
edges.FeatureEdgesOff()
edges.ManifoldEdgesOff()
edges.Update()
count = edges.GetOutput().GetNumberOfCells()
assert count == 0, f"Mesh has {count} boundary/nonmanifold edges"
data = json.loads((ROOT/"dimensions.json").read_text())
data["validation"]["STL_boundary_and_nonmanifold_edge_count"] = count
(ROOT/"dimensions.json").write_text(json.dumps(data,indent=2)+"\n")
print("Saved preview.png; STL is closed and manifold.")
