"""Build current, editable spatial assets and render existing-shot previs in Blender.

Blender: --background --factory-startup --python 工具/Blender场景预演.py -- build
Blender: --background --factory-startup --python 工具/Blender场景预演.py -- stills
Blender: --background --factory-startup --python 工具/Blender场景预演.py -- render SHOT
No historical copies; only original procedural geometry, no user image uploads.
"""
import argparse
import hashlib
import json
import math
import random
import time
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '资产' / '三维预演'
MASTER = OUT / '经世空间母场.blend'
SOURCE = ROOT / '索引' / '数据' / '发行前三集.json'
SHOTS = ['GJ-R02-SH016', 'GJ-R02-SH017', 'GJ-R02-SH019',
         'GJ-R01-SH002', 'GJ-R01-SH021']
MAT = {}
COL = None
ANCHORS = {}
# Facing +Y: left is -X; role-specific corner locations remain shared by horses and riders.
ESCORT_CORNERS = [('C16','H01',8.0,3.0),('C17','H02',14.4,3.0),('C20','H05',8.0,.3),('C23','H08',14.4,.3)]
DRAFT_ROW = [(9.1,6.3),(10.5,6.3),(11.9,6.3),(13.3,6.3)]
PACKAGE_WIDTH = 5.0
ROAD_WIDTH = 8*PACKAGE_WIDTH + 7*.3


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def setup(scene, engine='BLENDER_EEVEE', width=960, samples=16):
    bpy.context.preferences.filepaths.save_version = 0
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.render.engine = engine
    scene.render.resolution_x, scene.render.resolution_y = width, width * 9 // 16
    scene.render.resolution_percentage = 100
    scene.render.fps, scene.render.fps_base = 24, 1
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = samples
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.studiolight_rotate_z = 0.3
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.show_specular_highlight = True
    scene.display.shading.background_type = 'WORLD'
    scene.world = bpy.data.worlds.new(scene.name + '_World')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.48, 0.58, 0.72, 1)
    bg.inputs['Strength'].default_value = .45
    scene.world.color = (.09, .12, .16)


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def move_col(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    COL.objects.link(o)
    return o


def material(name, color, roughness=.65, metallic=0, noise=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    if noise:
        tex = m.node_tree.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 5
        tex.inputs['Detail'].default_value = 3
        bump = m.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .12
        bump.inputs['Distance'].default_value = .025
        m.node_tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    MAT[name] = m
    return m


def palette():
    MAT.clear()
    for n, c, r, met in [
        ('Wood', (.105,.054,.034),.4,0), ('Gold',(.43,.27,.085),.28,.7),
        ('Stone',(.38,.43,.43),.72,0), ('Plaster',(.73,.75,.68),.83,0),
        ('Roof',(.045,.095,.11),.58,0), ('Jade',(.17,.34,.31),.3,.1),
        ('Linen',(.7,.73,.65),.9,0), ('Earth',(.17,.13,.09),.85,0),
        ('Bamboo',(.06,.15,.10),.55,0), ('Leaf',(.035,.11,.075),.9,0),
        ('Copper',(.38,.19,.065),.24,.85), ('Paper',(.78,.76,.60),.8,0),
        ('GuProxy',(.5,.64,.59),.8,0), ('GuardProxy',(.12,.22,.31),.8,0),
        ('EnemyProxy',(.25,.16,.13),.8,0), ('GreySleeve',(.29,.32,.33),.8,0),
        ('Horse',(.15,.085,.048),.8,0), ('Water',(.07,.19,.21),.23,.2),
        ('Accent',(.65,.32,.13),.6,0)]:
        material(n,c,r,met,n in ('Wood','Stone','Earth','Plaster'))


def assign(o, name):
    o.data.materials.append(MAT[name])
    o['material_family'] = name
    return o


def cube(name, p, size, mat='Wood', bevel=0):
    verts=[(x*size[0]/2,y*size[1]/2,z*size[2]/2) for x,y,z in
           [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
    o=bpy.data.objects.new(name,mesh);COL.objects.link(o);o.location=p
    assign(o, mat)
    if bevel:
        mod = o.modifiers.new('Craft_edges', 'BEVEL')
        mod.width, mod.segments = bevel, 2
        o.modifiers.new('Weighted_normals', 'WEIGHTED_NORMAL')
    return o


def cyl(name, p, radius, depth, mat='Wood', vertices=12):
    n=vertices
    vv=[(radius*math.cos(2*math.pi*i/n),radius*math.sin(2*math.pi*i/n),z) for z in (-depth/2,depth/2) for i in range(n)]
    ff=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    ff += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vv,[],ff)
    o=bpy.data.objects.new(name,mesh);COL.objects.link(o);o.location=p
    assign(o, mat)
    return o


def ball(name, p, scale, mat='Wood', subdivisions=1):
    n=10 if subdivisions==1 else 16
    rings=6 if subdivisions==1 else 10
    vv=[]
    for j in range(rings+1):
        theta=math.pi*j/rings
        for i in range(n):
            phi=2*math.pi*i/n
            vv.append((math.sin(theta)*math.cos(phi)*scale[0],math.sin(theta)*math.sin(phi)*scale[1],math.cos(theta)*scale[2]))
    ff=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rings) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vv,[],ff)
    o=bpy.data.objects.new(name,mesh);COL.objects.link(o);o.location=p
    assign(o, mat)
    return o


def beam(name, a, b, radius=.08, mat='Wood'):
    a, b = Vector(a), Vector(b)
    o = cyl(name, (a+b)/2, radius, (b-a).length, mat)
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return o


def anchor(name, p):
    o = bpy.data.objects.new(name, None)
    COL.objects.link(o)
    o.location = p
    o.empty_display_type, o.empty_display_size = 'SPHERE', .13
    ANCHORS[name] = list(p)
    return o


def text3d(name, body, p, size=.65, mat='Wood', flat=True):
    data = bpy.data.curves.new(name, 'FONT')
    data.body, data.size, data.align_x = body, size, 'CENTER'
    o = bpy.data.objects.new(name,data)
    COL.objects.link(o)
    o.location = p
    if not flat:
        o.rotation_euler.x = math.pi/2
    assign(o,mat)
    return o


def roof(name, x,y,z,w,d, rise=2.0, detail=True):
    # Curved four-slope roof with modest lifted eaves; original fictional geometry.
    verts = []
    rings = [(w/2+.8,d/2+.9,z+.25),(w/2*.83,d/2*.70,z+.65),
             (w/2*.55,.16,z+rise)]
    for rx,ry,zz in rings:
        verts += [(x-rx,y-ry,zz),(x+rx,y-ry,zz),(x+rx,y+ry,zz),(x-rx,y+ry,zz)]
    faces = []
    for j in range(2):
        for i in range(4):
            faces.append((j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i))
    faces.append((8,9,10,11))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    o = bpy.data.objects.new(name,mesh)
    COL.objects.link(o)
    assign(o,'Roof')
    o['roof'] = True
    beam(name+'_Ridge',(x-w*.29,y,z+rise+.08),(x+w*.29,y,z+rise+.08),.12,'Roof')
    if detail:
        for xx in [x-w/2+i*.36 for i in range(int(w/.36)+1)]:
            for sign in (-1,1):
                beam(name+'_Tile',(xx,y+sign*(d/2+.9),z+.29),
                     (x+(xx-x)*.65,y+sign*.16,z+rise+.03),.045,'Roof')
        for sign in (-1,1):
            beam(name+'_Eave',(x-w/2-.8,y+sign*(d/2+.9),z+.15),
                 (x+w/2+.8,y+sign*(d/2+.9),z+.15),.12,'Wood')
    return o


def lattice(name,x,y,z,w,h):
    cube(name+'_Sill',(x,y,z-h/2),(w+.16,.26,.14))
    cube(name+'_Top',(x,y,z+h/2),(w+.16,.24,.14))
    for xx in (x-w/2,x+w/2):
        cube(name+'_Side',(xx,y,z),(.13,.24,h))
    for i in range(1, int(w/.22)):
        xx=x-w/2+i*.22
        cube(name+'_V',(xx,y,z),(.035,.07,h))
    for i in range(1,int(h/.25)):
        cube(name+'_H',(x,y,z-h/2+i*.25),(w,.07,.035))


def table(name,x,y,z=.30,w=2.5,d=1.15, movable=False):
    top = cube(name,(x,y,z+.87),(w,d,.17),'Wood',.045)
    top['movable'] = movable
    cube(name+'_Apron',(x,y,z+.64),(w-.12,d-.1,.30),'Wood',.025)
    for xx in (-w/2+.18,w/2-.18):
        for yy in (-d/2+.17,d/2-.17):
            cube(name+'_Leg',(x+xx,y+yy,z+.38),(.19,.19,.76),'Wood',.025)
    for xx in (-w*.3,0,w*.3):
        o=cube(name+'_Inlay',(x+xx,y-d/2-.01,z+.64),(.25,.018,.11),'Gold',.018)
        o.rotation_euler.y=.25
    return top


def bed(name,x,y,w=1.5,d=2.3):
    o=cube(name,(x,y,.77),(w,d,.24),'Wood',.035)
    o['bed'] = True
    cube(name+'_Bedding',(x,y,.96),(w-.08,d-.1,.13),'Linen',.06)
    cube(name+'_Pillow',(x,y+d*.30,1.08),(w*.65,.42,.14),'Linen',.07)
    for xx in (-w/2,w/2):
        for yy in (-d/2,d/2):
            cube(name+'_Post',(x+xx,y+yy,1.5),(.12,.12,2.4))
    cube(name+'_Cornice',(x,y,2.7),(w+.18,d+.15,.18),'Wood',.025)
    cube(name+'_GoldBand',(x,y-d/2-.1,2.67),(w,.025,.08),'Gold')


def pavilion(name,x,y,w,d,height=4.2,front_open=True,detail=True):
    cube(name+'_Plinth',(x,y,.14),(w+.8,d+.7,.28),'Stone',.05)
    for xx in (-w/2,w/2):
        cube(name+'_Wall',(x+xx,y,1.9),(.25,d,3.2),'Plaster')
    cube(name+'_Back',(x,y+d/2,1.9),(w,.25,3.2),'Plaster')
    if not front_open:
        cube(name+'_Front',(x,y-d/2,1.9),(w,.25,3.2),'Plaster')
    for yy in (-d/2,d/2):
        for i in range(5):
            xx=x-w/2+i*w/4
            cyl(name+'_StoneBase',(xx,y+yy,.42),.32,.28,'Stone')
            cyl(name+'_Column',(xx,y+yy,2.35),.22,3.7)
            cube(name+'_Capital',(xx,y+yy,4.08),(.76,.5,.18),'Wood')
            cube(name+'_Bracket',(xx,y+yy,4.28),(1.05,.65,.16),'Wood')
        cube(name+'_Beam',(x,y+yy,3.94),(w+.6,.35,.34),'Wood')
        cube(name+'_GoldLine',(x,y+yy-.19,3.90),(w+.4,.016,.038),'Gold')
    roof(name+'_Roof',x,y,height,w,d,detail=detail)


def light(name,p,energy,color=(1,1,1),size=4,target=None,kind='AREA'):
    data=bpy.data.lights.new(name,kind)
    data.energy, data.color=energy,color
    if kind=='AREA': data.shape,data.size='DISK',size
    if kind=='SUN': data.angle=.12
    o=bpy.data.objects.new(name,data)
    COL.objects.link(o)
    o.location=p
    if target is not None:
        o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def lantern(name,x,y,z):
    cube(name+'_Base',(x,y,z-.15),(.24,.24,.08),'Wood')
    cube(name+'_Shade',(x,y,z),(.17,.17,.25),'Paper',.02)
    cube(name+'_Cap',(x,y,z+.16),(.26,.26,.08),'Wood')
    return light(name+'_Source',(x,y,z),28,(1,.57,.27),kind='POINT')


def build_manor():
    global COL
    COL=collection('MANOR_S02_S03_S04_S05_S06')
    cube('S03_Ground',(0,16,-.15),(54,60,.25),'Earth')
    cube('S03_Courtyard',(0,10,.02),(27,20,.10),'Stone')
    for y in range(1,20,2):
        cube('S03_Paving_Joint',(0,y,.077),(26,.025,.01),'Wood')
    for x in (-5,0,5):
        cube('S03_Paving_Joint',(x,10,.077),(.025,20,.01),'Wood')
    for x in (-14,14):
        cube('S03_FrontWall',(x,0,1.65),(22,.45,3.3),'Plaster')
    for x in (-25,25):
        # West service entrance gap is an actual gap at y=8.
        segments=[(2,4),(21,20)] if x<0 else [(17,34)]
        for y,d in segments:
            cube('S03_Boundary',(x,y,1.65),(.4,d,3.3),'Plaster')
    cube('S06_RearWall',(0,38,1.65),(50,.4,3.3),'Plaster')
    pavilion('S03_Gate',0,0,6,3,height=4.6,detail=True)
    # Door leaves stay at jambs, leave 2.8m usable opening; gate back has actual opening.
    bpy.data.objects.remove(bpy.data.objects['S03_Gate_Back'],do_unlink=True)
    for o in list(COL.objects):
        if o.name.startswith(('S03_Gate_Column','S03_Gate_StoneBase')) and abs(o.location.x)<.1:
            bpy.data.objects.remove(o,do_unlink=True)
    for x in (-2.35,2.35):
        cube('S03_GateSide',(x,1.5,1.9),(1.1,.30,3.2),'Wood')
    for x in (-1.5,1.5):
        cube('S03_GateLeaf',(x,-.2,1.9),(.16,2.6,3.1),'Wood',.03)
    pavilion('S03_Hall',0,23,16,8,height=4.5)
    bpy.data.objects.remove(bpy.data.objects['S03_Hall_Back'],do_unlink=True)
    for x in (-4.75,4.75):
        cube('S03_Hall_RearWall',(x,27,1.9),(6.5,.25,3.2),'Plaster')
    cube('S03_Hall_RearLintel',(0,27,3.4),(3,.25,.3),'Wood')
    table('S03_Table_Fixed',0,25,.3,3.8,1.5)
    table('S03_Table_Moveable',6.4,19.7,.3,1.1,.65,True)
    for x in (-3.2,3.2):
        cube('S03_Seat',(x,24,.83),(.8,.8,.18),'Wood',.03)
        cube('S03_SeatBack',(x,24.35,1.4),(.8,.15,1.05),'Wood',.03)
    # Shared deep covered corridor; its posts avoid the study entrance and window.
    cube('S03_CorridorFloor',(0,18,.15),(41,2.6,.3),'Stone')
    for x in (-20,-16,-8,-4,0,4,8,17,20):
        cyl('S03_CorridorPost',(x,16.8,2.1),.19,3.8)
    cube('S03_CorridorBeam',(0,16.8,3.9),(41,.3,.35),'Wood')
    roof('S03_CorridorRoof',0,18,4.0,41,2.5,rise=.7,detail=False)
    pavilion('S04_Study',14,23.5,12,9,height=4.5)
    for o in list(COL.objects):
        if o.name.startswith(('S04_Study_Column','S04_Study_StoneBase')) and o.location.y<20 and 10<o.location.x<15:
            bpy.data.objects.remove(o,do_unlink=True)
    # Solid front wall assembled around door/window openings.
    for x,w in [(9.0,2),(12.1,.8),(17.8,4.4)]:
        cube('S04_FrontWall',(x,19,1.9),(w,.26,3.2),'Plaster')
    cube('S04_AboveDoor',(10.8,19,3.23),(1.8,.26,.55),'Plaster')
    cube('S04_UnderWindow',(14.2,19,.78),(2.6,.26,1.0),'Plaster')
    cube('S04_AboveWindow',(14.2,19,3.52),(2.6,.26,.48),'Plaster')
    lattice('S04_Window_Court',14.2,19,2.2,2.6,1.65)
    door=cube('S04_Door',(10.8,19.12,1.65),(1.55,.16,2.7),'Wood',.025)
    cube('S04_InnerLatch',(10.8,19.235,1.55),(1.2,.09,.07),'Wood')
    for x in (10.2,11.4):
        cube('S04_DoorInlay',(x,19.215,1.7),(.025,.015,2.3),'Gold')
    table('S04_Desk',12.1,21.65,.3,2.5,1.12)
    cube('S04_WindowCabinet',(14.2,19.64,.73),(2.2,.8,.85),'Wood',.035)
    for x in (13.65,14.75):
        cube('S04_CabinetFront',(x,20.05,.76),(.98,.055,.65),'Wood',.025)
        ball('S04_CabinetHandle',(x,20.10,.8),(.06,.03,.04),'Copper',2)
    cyl('S04_Cup',(12.6,21.5,1.31),.075,.16,'Jade',20)
    cube('S04_Book',(11.7,21.8,1.30),(.38,.55,.07),'Paper')
    mirror=cyl('S04_CopperMirror',(11.6,21.43,1.60),.23,.025,'Copper',32)
    mirror.rotation_euler.x=math.pi/2
    beam('S04_MirrorStand',(11.6,21.45,1.2),(11.6,21.45,1.55),.025,'Copper')
    lantern('S04_DeskLamp',12.9,21.8,1.47)
    for x in (10,13,16,18.5):
        cube('S04_Bookcase',(x,27.5,1.8),(2,.45,3),'Wood',.025)
        for z in (.55,1.25,1.95,2.65):
            cube('S04_Shelf',(x,27.13,z),(1.8,.4,.09),'Wood')
            for b in range(7):
                cube('S04_BookSpine',(x-.72+b*.22,27.09,z+.20),(.15,.28,.32),'Paper' if b%3 else 'Jade')
    for x in (16.5,19):
        lattice('S04_Screen',x,24.6,1.85,1.6,2.8)
    table('S04_ReadingTable',17.7,26.2,.3,1.65,.9)
    cube('S04_Daybed',(18.8,22.9,.77),(1.35,2.5,.35),'Wood',.045)
    cube('S04_DaybedCushion',(18.8,22.9,1.0),(1.2,2.3,.13),'Linen',.035)
    anchor('S04_DoorAnchor',(10.8,19.12,1.55))
    anchor('S04_WindowAnchor',(14.2,19,2.2))
    anchor('S04_DeskAnchor',(12.1,21.65,1.255))
    anchor('S04_CabinetAnchor',(14.2,20.04,1.155))
    anchor('S04_WaitingOutside',(10.8,17.7,.30))
    # West bedroom, separate from study.
    pavilion('S05_Bedroom',-14,23.5,12,9,height=4.5)
    bed('S05_MainBed',-15,25,2.0,2.6)
    table('S05_Bedside',-12.7,25,.3,1.2,.8)
    # Five formal guest beds in 2/2/1 working distribution; open common approach east.
    pavilion('S03W_GuestRooms',-18,10,8,15,height=3.9)
    for y in (7.6,12.6):
        cube('S03W_Partition',(-18,y,1.85),(7.6,.2,3.1),'Plaster')
    for i,(x,y) in enumerate([(-20,4.8),(-16,4.8),(-20,10),(-16,10),(-20,15)]):
        bed('S03W_Bed_'+str(i+1),x,y)
    # Actual side doors in guest east wall, sectioned from the existing solid wall.
    east=[o for o in COL.objects if o.name.startswith('S03W_GuestRooms_Wall') and o.location.x>-18]
    for o in east: bpy.data.objects.remove(o,do_unlink=True)
    for y,d in [(3.2,1.4),(7.4,2.6),(12.4,2.6),(17.1,.8)]:
        cube('S03W_EastWall',(-14,y,1.85),(.25,d,3.1),'Plaster')
    cube('S06_ShortCorridor',(0,29,.15),(3.0,5,.3),'Stone')
    cube('S06_Courtyard',(0,33,.05),(27,9,.1),'Stone')
    cyl('S06_Well',(-6,33,.55),.75,1,'Stone',24)
    cyl('S06_WellDark',(-6,33,1.055),.57,.015,'Water',24)
    table('S06_WashStand',-3.5,33,0,1.4,.65)
    cyl('S06_Basin',(-3.5,33,1.0),.25,.15,'Jade',20)
    pavilion('S06K_Store',17,33,8,7,height=3.9,front_open=False)
    cube('S06K_Door',(17,29.37,1.7),(2.0,.15,2.8),'Wood',.035)
    anchor('S06K_Threshold',(17,29.35,.3))
    # Side-edge planting, never on central path.
    rng=random.Random(41)
    for x in (-10.8,10.8):
        for y in (5,10,14):
            cube('S03_Planter',(x,y,.20),(2.2,2.4,.3),'Earth')
            for j in range(3):
                ball('S03_SideRock',(x+rng.uniform(-.6,.6),y+rng.uniform(-.5,.5),.6),(.4,.45,.75),'Stone',1)
            beam('S03_WinterTree',(x,y,.25),(x+.2,y,3.1),.10)
            for j in range(4):
                a=(x+.2,y,2.1+j*.2); b=(x+rng.uniform(-1,1),y+rng.uniform(-1,1),3.0+rng.random()*.6)
                beam('S03_WinterBranch',a,b,.035)
                ball('S03_WinterBlossom',b,(.20,.15,.18),'Linen',1)
    # Street modules and exact near-door geography, same coordinate system.
    cube('S02_Street',(0,-7.7,-.02),(100,12,.12),'Stone')
    cube('S02_WestLane',(-28,10,-.01),(5,48,.1),'Stone')
    for i in range(10):
        x=-43+i*9
        pavilion('S02_Shop_'+str(i),x,-18,7.5,6,detail=False)
    for i in (-1,1):
        for j in range(3):
            pavilion('S02_SideShop',i*(32+j*9),-.8,7,5,detail=False)
    table('S02_SoupStall',-8,-3.5,0,2.4,.9)
    cyl('S02_SoupPot',(-8,-3.5,1.1),.35,.35,'Copper',24)
    for x in (-9.4,-6.6):
        beam('S02_StallPost',(x,-3.5,0),(x,-3.5,2.7),.06)
    cube('S02_StallAwning',(-8,-3.5,2.65),(3.3,2,.12),'Linen')
    anchor('S02_SoupAnchor',(-8,-3.5,0))
    anchor('S02_ConstableAnchor',(7,-2.5,0))
    anchor('S02_WestLaneMouth',(-28,-7,0))
    anchor('S03_MainGateOrigin',(0,0,0))
    anchor('S03_HorseHolding',(-11,5,0))
    light('MANOR_Sun',(-25,-35,40),2.5,(1,.96,.88),target=(0,15,0),kind='SUN')
    light('S04_WindowSky',(14,16.8,3.2),800,(.72,.84,1),5,target=(14,23,1.5))
    return COL


def horse(name,x,y,mat='Horse'):
    root=bpy.data.objects.new(name,None); COL.objects.link(root)
    root['proxy_type']='horse'; root['asset_id']='P01' if 'Hitch' in name else 'P19'
    objects=[]
    objects.append(ball(name+'_Body',(x,y,1.25),(.38,.90,.55),mat,2))
    objects.append(beam(name+'_Neck',(x,y+.55,1.4),(x,y+.92,2.0),.23,mat))
    objects.append(ball(name+'_Head',(x,y+1.12,1.95),(.22,.4,.24),mat,2))
    for xx in (-.26,.26):
        for yy in (-.57,.6):
            objects.append(beam(name+'_Leg',(x+xx,y+yy,.05),(x+xx,y+yy,1.25),.065,mat))
    if 'Hitch' not in name:
        objects.append(cube(name+'_Saddle',(x,y,1.80),(.60,.6,.15),'Wood',.04))
    for o in objects: o.parent=root
    return root


def build_forest():
    global COL
    COL=collection('FOREST_S01')
    cube('S01_ForestGround',(0,15,-.34),(90,140,.25),'Earth')
    cube('S01_Road',(0,12,-.17),(ROAD_WIDTH,95,.30),'Earth')
    for x in (-ROAD_WIDTH/2-.8,ROAD_WIDTH/2+.8):
        cube('S01_Shoulder',(x,12,-.04),(1.6,95,.12),'Earth')
        cube('S01_Ditch',(x+(1 if x>0 else -1),12,-.10),(.3,95,.05),'Water')
    for x in (10.7,12.3):
        cube('S01_WheelRut',(x,4,.005),(.16,65,.016),'Wood')
    rng=random.Random(189)
    for side in (-1,1):
        for i in range(68):
            x=side*rng.uniform(ROAD_WIDTH/2+.2,33); y=rng.uniform(-27,45)
            h=rng.uniform(5,10)
            if side==1 and 7<y<14 and x<20: continue
            cyl('S01_Bamboo',(x,y,h/2),rng.uniform(.065,.12),h,'Bamboo',8)
            for z in (h*.35,h*.55,h*.75):
                cyl('S01_BambooNode',(x,y,z),.13,.065,'Bamboo',8)
            ball('S01_Leaves',(x,y,h*.8),(rng.uniform(.6,1.1),1.1,1.7),'Leaf',1)
        for i in range(20):
            x=side*rng.uniform(ROAD_WIDTH/2+1.5,36);y=rng.uniform(-30,50);h=rng.uniform(8,13)
            beam('S01_Tree',(x,y,0),(x+.5,y,h),rng.uniform(.3,.5))
            ball('S01_Canopy',(x,y,h),(3,3,2.5),'Leaf',1)
    # Hero obstruction tree and second bamboo layer: conceal face/hands, not a teleport.
    cyl('S01_C60_HeroTree',(22.0,8.4,4),.62,8,'Wood',18)
    cyl('S01_C60_BambooA',(21.25,8.05,3),.15,6,'Bamboo',10)
    cyl('S01_C60_BambooB',(21.6,7.65,3),.13,6,'Bamboo',10)
    # Carriage local X east, forward +Y; right door at +X.
    cube('P01_Chassis',(11.2,2,.90),(2.25,3.9,.24),'Wood',.035)
    cube('P01_CabinFloor',(11.2,1.7,1.15),(2.25,3.05,.18),'Wood')
    cube('P01_CabinLeft',(10.04,1.7,2.0),(.18,3.1,1.9),'Wood')
    cube('P01_CabinFront',(11.2,3.25,2.0),(2.4,.18,1.9),'Wood')
    cube('P01_CabinBack',(11.2,.15,2.0),(2.4,.18,1.9),'Wood')
    cube('P01_RightWallBack',(12.36,.55,2.0),(.18,.75,1.9),'Wood')
    cube('P01_RightWallFront',(12.36,2.9,2.0),(.18,.65,1.9),'Wood')
    door=cube('P01_RightDoor',(12.38,1.8,2.0),(.18,1.55,1.9),'Wood',.02)
    door['door_state']='closed_at_SH002'
    roof('P01_SolidRoof',11.2,1.7,2.93,2.1,3.0,rise=.48,detail=False)
    cube('P01_DriverSeat',(11.2,3.8,1.3),(1.8,.65,.2),'Wood')
    for z,x,w in [(.30,13.25,.65),(.60,12.9,.6),(.88,12.6,.45)]:
        cube('P01_RightStep',(x,1.6,z),(w,1.25,.15),'Wood')
    for x in (9.9,12.5):
        for y in (.5,3.0):
            wheel=cyl('P01_Wheel',(x,y,.73),.69,.15,'Wood',24)
            wheel.rotation_euler.y=math.pi/2
            hub=cyl('P01_WheelHub',(x,y,.73),.13,.23,'Copper',12)
            hub.rotation_euler.y=math.pi/2
    beam('P01_CentralPole',(11.2,3.5,.9),(11.2,7.4,.9),.055)
    for i,(x,y) in enumerate(DRAFT_ROW):
        horse('P01_HitchHorse_'+str(i+1),x,y)
    for i,(cid,hid,x,y) in enumerate(ESCORT_CORNERS):
        h=horse('P19_RidingHorse_'+str(i+1),x,y)
        h['horse_id']=hid;h['rider_id']=cid
    cube('P01_RearLuggageRack',(11.2,-.65,1.05),(1.8,.8,.16),'Wood')
    cube('P01_P02_Bag',(10.8,-.65,1.4),(.4,.35,.55),'GuardProxy')
    cube('P01_C23_Bag',(11.45,-.65,1.4),(.48,.32,.55),'GuardProxy')
    for i in range(8):
        o=anchor('S01_EightLaneEnvelope_'+str(i+1),(-ROAD_WIDTH/2+PACKAGE_WIDTH/2+i*(PACKAGE_WIDTH+.3),25,0))
        o.empty_display_type='CUBE';o.scale=(PACKAGE_WIDTH/2,5.5,1.5)
        o['full_width_m']=PACKAGE_WIDTH; o['spacing_m']=.3
    anchor('S01_RoadWidth',(0,25,0))
    anchor('S01_RightDoorAnchor',(12.5,1.8,1.1))
    anchor('S01_C60FaceAnchor',(22.15,9.1,1.7))
    anchor('S01_ExitForward',(11.2,32,0))
    # Bridge remains an offscreen layout anchor beyond the bend, never visible geometry here.
    anchor('S01_BridgeBeyondBend',(30,70,0))
    cube('S01_WheelBlock',(12.4,3.25,.23),(.22,1.6,.42),'Wood')
    lantern('P01_CarriageLamp',10.1,3.35,1.75)
    light('S01_MoonSky',(0,-10,30),.8,(.49,.64,1),target=(12,4,0),kind='SUN')
    light('S01_FrontCanopyGap',(10,20,9),650,(.5,.69,1),8,target=(12,1,0))
    return COL


def build_city():
    global COL
    COL=collection('CITY_RELATION_BLOCKS')
    cube('CITY_Plane',(0,0,-1),(1200,1000,2),'Earth')
    cube('CITY_MainNS',(0,0,.05),(26,900,.12),'Stone')
    cube('CITY_MainEW',(0,0,.06),(1100,24,.12),'Stone')
    rng=random.Random(771)
    districts=[('NORTH_OFFICES',0,290,'Stone'),('EAST_WAREHOUSES',330,0,'Jade'),
               ('SOUTH_GU',0,-290,'Accent'),('WEST_XIE',-330,0,'Wood')]
    for name,cx,cy,mat in districts:
        for i in range(32):
            x=cx+rng.uniform(-110,110);y=cy+rng.uniform(-85,85)
            if abs(x)<22 or abs(y)<18: continue
            w=rng.uniform(12,28);d=rng.uniform(16,35);h=rng.uniform(8,15)
            cube(name,(x,y,h/2),(w,d,h),mat)
            roof(name+'_Roof',x,y,h,w,d,rise=4,detail=False)
        text3d(name+'_Label',name,(cx,cy-120,.4),13,'Linen')
    cube('CITY_EastWaterRelation',(490,0,-.01),(32,650,.1),'Water')
    text3d('CITY_North','N',(0,460,.4),20,'Linen')
    text3d('CITY_Gu','GU / S02-S06',(0,-200,.4),13,'Linen')
    text3d('CITY_Guizang','GUIZANG COURTYARD',(-330,-210,.4),11,'Linen')
    anchor('CITY_GuAnchor',(0,-290,0))
    anchor('CITY_GuizangAnchor',(-330,-210,0))
    light('CITY_Sun',(0,-100,400),3,(1,.97,.92),target=(0,0,0),kind='SUN')
    return COL


def build_modern():
    global COL
    COL=collection('MODERN_S07_LOCAL')
    cube('S07_StableGround',(0,1,-.1),(5,5,.2),'Stone')
    rng=random.Random(73)
    for i in range(12):
        ball('S07_Rock',(rng.uniform(-2,2),2.3,rng.uniform(.4,3.5)),(.7,.6,.9),'Stone',1)
    anchor('S07_SafeFoot',(0,0,0))
    beam('S07_RopeReference',(1.3,.3,.1),(1.4,1,1.4),.025,'Accent')
    light('S07_Sun',(0,-10,10),2,(1,1,1),target=(0,2,0),kind='SUN')
    return COL


def camera(name,p,target,lens=35,ortho=None):
    data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);COL.objects.link(o)
    o.location=p;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    data.lens= lens;data.sensor_width=36;data.sensor_fit='HORIZONTAL'
    data.clip_start=.06;data.clip_end=3000
    if ortho is not None: data.type='ORTHO';data.ortho_scale=ortho
    bpy.context.scene.camera=o
    return o


def new_scene(name):
    s=bpy.data.scenes.new(name)
    bpy.context.window.scene=s
    setup(s)
    return s


def build_master():
    global COL
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    palette()
    s=bpy.context.scene;s.name='MANOR_DAY';setup(s)
    build_manor();camera('CAM_Manor_Overview',(55,-55,55),(0,15,1),40)
    new_scene('FOREST_DAY_SURVEY');build_forest()
    camera('CAM_Forest_Overview',(-32,-29,28),(10,5,1),35)
    new_scene('CITY_RELATION_ONLY');build_city()
    camera('CAM_City_Relations',(690,-920,1000),(0,0,0),43)
    new_scene('MODERN_LOCAL');build_modern()
    camera('CAM_Modern_Local',(4,-5,3),(0,1,1),42)
    bpy.context.window.scene=bpy.data.scenes['MANOR_DAY']
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    dump(OUT/'空间锚点.json',dict(maturity='working_spatial_model_not_final_design',
        units='meter',axes={'x':'east','y':'north','z':'up'},
        city_map='diagrammatic_only_not_real_travel_distance',
        city_to_manor={'relation':'Gu_anchor','translation':[0,-290,0],
                       'scale':1,'rotation_deg':0,'note':'城市图为示意尺度，不据此重算行程'},
        anchors=ANCHORS,
        road={'width_m':37,'package_width_m':4.3,'gap_m':.3,
              'minimum_eight_packages_m':8*PACKAGE_WIDTH+7*.3,'status':'proxy_dimensions_pending_art_review'},
        library_sha256=hashlib.sha256(MASTER.read_bytes()).hexdigest()))


def keyed(o,frame,p=None,rot=None):
    if p is not None: o.location=p;o.keyframe_insert(data_path='location',frame=frame)
    if rot is not None: o.rotation_euler=rot;o.keyframe_insert(data_path='rotation_euler',frame=frame)


def puppet(name,p,mat='GuProxy'):
    # Articulated proxy, not a face or a final character asset.
    root=bpy.data.objects.new(name,None);COL.objects.link(root)
    root.location=p;root['proxy_type']='adult_blocking_only'
    parts={}
    parts['torso']=ball(name+'_Torso',(0,0,1.13),(.24,.16,.35),mat,2)
    parts['head']=ball(name+'_Head',(0,0,1.68),(.12,.11,.15),mat,2)
    parts['pelvis']=ball(name+'_Pelvis',(0,0,.84),(.21,.14,.19),mat,1)
    for side,x in [('L',-.18),('R',.18)]:
        parts[side+'thigh']=beam(name+'_'+side+'Thigh',(x,0,.46),(x,0,.86),.075,mat)
        parts[side+'leg']=beam(name+'_'+side+'Leg',(x,0,.08),(x,0,.46),.065,mat)
        parts[side+'foot']=cube(name+'_'+side+'Foot',(x,-.06,.05),(.17,.30,.1),mat,.025)
        parts[side+'upper']=beam(name+'_'+side+'Upper',(x*1.5,0,1.36),(x*1.7,-.04,1.02),.065,mat)
        parts[side+'fore']=beam(name+'_'+side+'Fore',(x*1.7,-.04,1.02),(x*1.6,-.1,.75),.055,mat)
    for o in parts.values():o.parent=root
    return root,parts


def limb_pose(o,a,b,frame,radius):
    a,b=Vector(a),Vector(b)
    o.location=(a+b)/2
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    # Original cylinders have applied dimensions; use reference length for pose scaling.
    if 'base_length' not in o:o['base_length']=max(v.co.z for v in o.data.vertices)-min(v.co.z for v in o.data.vertices)
    o.scale.z=(b-a).length/o['base_length']
    for prop in ('location','rotation_euler','scale'):o.keyframe_insert(data_path=prop,frame=frame)


def pose(parts,frame,crouch=0,reach=0):
    for k in ('torso','head','pelvis'):
        base={'torso':1.13,'head':1.68,'pelvis':.84}[k]
        keyed(parts[k],frame,p=(0,0,base-crouch))
    for side,x in [('L',-.18),('R',.18)]:
        knee=(x,-crouch*.65,.46-crouch*.30)
        limb_pose(parts[side+'thigh'],knee,(x,0,.86-crouch),frame,.075)
        limb_pose(parts[side+'leg'],(x,0,.08),knee,frame,.065)
        shoulder=(x*1.5,0,1.36-crouch)
        elbow=(x*1.7,-.08-reach*.20,1.02-crouch+reach*.25)
        hand=(x*1.6,-.1-reach*.45,.75-crouch+reach*.46)
        if side=='L': # left shoulder guarded, never identical full arm reach
            elbow=(x*1.5,-.04,1.09-crouch);hand=(-.08,-.16,1.17-crouch)
        limb_pose(parts[side+'upper'],shoulder,elbow,frame,.065)
        limb_pose(parts[side+'fore'],elbow,hand,frame,.055)


def shot_source():
    data=json.loads(SOURCE.read_text(encoding='utf-8'))
    return {s['id']:s for e in data['episodes'] for s in e['shots']}


def configure_shot(shot_id):
    global COL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.name=shot_id;setup(s)
    palette()
    group='MANOR_S02_S03_S04_S05_S06' if 'R02' in shot_id else 'FOREST_S01'
    with bpy.data.libraries.load(str(MASTER),link=True) as (src,dst):
        dst.collections=[group]
    s.collection.children.link(dst.collections[0])
    COL=collection('SHOT_'+shot_id)
    info=shot_source()[shot_id]
    n=info['end_frame']-info['start_frame']
    s.frame_start,s.frame_end=1,n
    s['source_start_frame']=info['start_frame'];s['source_end_frame_exclusive']=info['end_frame']
    s['source_parent_id']=shot_id;s['media_role']='previs_not_final_performance'
    if 'R02' in shot_id:
        # Night source state: linked daytime sources disabled at shot View Layer only.
        for o in s.objects:
            if o.type=='LIGHT' and o.name in ('MANOR_Sun','S04_WindowSky'):
                # Linked objects are immutable; exclude their collection is unavailable.
                # Their contribution is removed through a shot-local linked-collection override below.
                pass
        # Background lighting is set in the master to physical daylight; a local night copy
        # is built through data-local linked objects without changing any geometry/transform.
        local=dst.collections[0].copy();s.collection.children.unlink(dst.collections[0]);s.collection.children.link(local)
        for obj in list(local.objects):
            if obj.type=='LIGHT':
                local.objects.unlink(obj)
                if obj.name=='S04_DeskLamp_Source':
                    own=obj.copy();own.data=obj.data.copy();COL.objects.link(own)
        s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.16
        light('S04_NightWindowSky',(14,17.6,3.4),420,(.52,.68,1),4,target=(13,22,1.4))
        # This source is same courtyard sky entering actual window, not an interior invisible lamp.
        if shot_id.endswith('016'):
            cam=camera('CAM_'+shot_id,(17.7,24.1,2.3),(12.8,20.2,1.35),29)
            actor,parts=puppet('C02_Blocking',(13.2,21.1,.3))
            for f,p in [(1,(13.2,21.1,.3)),(55,(13.2,21.1,.3)),(155,(14.2,20.56,.3)),(n,(14.2,20.56,.3))]:
                keyed(actor,f,p=p);pose(parts,f,0,.55 if f>100 else 0)
        elif shot_id.endswith('017'):
            cam=camera('CAM_'+shot_id,(16.9,23.9,1.95),(14.0,20.25,1.2),38)
            actor,parts=puppet('C02_Blocking',(14.2,20.56,.3))
            for f,c,r in [(1,0,.55),(65,.06,.9),(105,.13,.8),(165,.48,.1),(n,.48,.1)]:
                keyed(actor,f,p=(14.2,20.56+c*.3,.3));pose(parts,f,c,r)
        else:
            cam=camera('CAM_'+shot_id,(17.7,24.1,2.3),(14.2,20.4,1.15),32)
            actor,parts=puppet('C02_Blocking',(14.2,20.7,.3))
            for f,c,p in [(1,.48,(14.2,20.7,.3)),(65,.48,(14.2,20.7,.3)),
                           (145,0,(13.6,21.15,.3)),(n,0,(12.85,20.7,.3))]:
                keyed(actor,f,p=p,rot=(0,0,-.9 if f>=145 else 0));pose(parts,f,c,.2)
            for f,target in [(1,(14.2,20.4,1.15)),(75,(14.2,20.4,1.15)),
                              (195,(10.9,19.3,1.5)),(n,(10.9,19.3,1.5))]:
                keyed(cam,f,rot=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler())
        anchor('ACTOR_START',tuple(actor.location))
        cam.data.dof.use_dof=False
    else:
        s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.19
        if shot_id.endswith('002'):
            cam=camera('CAM_'+shot_id,(-5,-20,5.2),(12,0,1.4),28)
            for f,p in [(1,(-5,-20,5.2)),(112,(-3.5,-20,5.2)),(n,(-3.5,-20,5.2))]:
                keyed(cam,f,p=p,rot=(Vector((12,0,1.4))-Vector(p)).to_track_quat('-Z','Y').to_euler())
            # Same six companions; C01 is inside the solid cabin, riders mounted.
            _,parts=puppet('C01_InCabin',(11.2,1.65,1.2),'GuProxy');pose(parts,1,.4,0)
            _,parts=puppet('C03_Driver',(11.2,3.8,.9),'GuardProxy');pose(parts,1,.4,.3)
            for i,(cid,hid,x,y) in enumerate(ESCORT_CORNERS):
                rider,parts=puppet('C_Rider_'+str(i+1),(x,y,1.35),'GuardProxy')
                rider['character_id']=cid; rider['horse_id']=hid
                pose(parts,1,.4,0)
                for side,sign in [('L',-1),('R',1)]:
                    knee=(sign*.50,-.15,.2);foot=(sign*.55,-.2,-.3)
                    limb_pose(parts[side+'thigh'],knee,(sign*.18,0,.44),1,.075)
                    limb_pose(parts[side+'leg'],foot,knee,1,.065)
                    keyed(parts[side+'foot'],1,p=(sign*.55,-.2,-.34))
        else:
            cam=camera('CAM_'+shot_id,(14.9,3.0,1.7),(21.8,8.7,1.5),52)
            actor,parts=puppet('C06_Blocking',(17.7,6.0,0),'EnemyProxy')
            actor.rotation_euler.z=-.6
            # Only sleeve is modeled in this shot; face/hands have no mesh to leak.
            sleeve=cube('C60_VisibleGreySleeve',(21.5,8.65,1.1),(.22,.47,.45),'GreySleeve',.06)
            for f,p in [(1,(21.5,8.65,1.1)),(80,(21.5,8.65,1.1)),(126,(21.95,8.85,1.1)),(n,(21.95,8.85,1.1))]:
                keyed(sleeve,f,p=p)
            focus=bpy.data.objects.new('FocusTarget',None);COL.objects.link(focus)
            for f,p in [(1,(17.7,6,1.4)),(45,(17.7,6,1.4)),(105,(21.8,8.6,1.1)),(n,(21.8,8.6,1.1))]:
                keyed(focus,f,p=p)
            cam.data.dof.use_dof=True;cam.data.dof.focus_object=focus;cam.data.dof.aperture_fstop=4.0
    # Freeze start state before saving.
    s.frame_set(1)
    s.render.filepath=str(OUT/'帧'/shot_id/'frame_')
    path=OUT/'镜头'/f'{shot_id}.blend';path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path),relative_remap=True)
    return export_camera(s,info,path)


def export_camera(scene,source,path):
    cam=scene.camera
    landmarks=['S04_DoorAnchor','S04_WindowAnchor','S04_DeskAnchor','S04_CabinetAnchor'] if 'R02' in scene.name else ['S01_RightDoorAnchor','S01_C60FaceAnchor','S01_ExitForward']
    rows=[];camera_clear=True
    for frame in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(frame)
        m=cam.matrix_world; proj={}
        for name in landmarks:
            obj=scene.objects.get(name)
            if obj:
                p=world_to_camera_view(scene,cam,obj.matrix_world.translation)
                proj[name]=[round(float(v),6) for v in p]
        # Conservative camera clearance to nearby evaluated solid surfaces in six directions.
        dg=bpy.context.evaluated_depsgraph_get()
        for axis in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            hit,loc,normal,index,obj,mat=scene.ray_cast(dg,m.translation,Vector(axis),distance=.07)
            if hit:camera_clear=False
        rows.append({'local_frame':frame,'source_frame':source['start_frame']+frame-1,
                     'position_m':[round(v,6) for v in m.translation],
                     'quaternion_wxyz':[round(v,6) for v in m.to_quaternion()],
                     'lens_mm':cam.data.lens,'focus_distance_m':
                     (cam.data.dof.focus_object.matrix_world.translation-m.translation).length if cam.data.dof.focus_object else cam.data.dof.focus_distance,
                     'fstop':cam.data.dof.aperture_fstop,'dof_enabled':cam.data.dof.use_dof,
                     'landmarks_uv_depth':proj})
    scene.frame_set(1)
    output=dict(id=scene.name,source_scene_id=source['scene_id'],source_start=source['start_frame'],
                source_end_exclusive=source['end_frame'],local_frame_start=1,
                local_frame_end_inclusive=scene.frame_end,fps=[24,1],aspect_ratio='16:9',
                sensor_width_mm=cam.data.sensor_width,sensor_fit=cam.data.sensor_fit,
                clip_m=[cam.data.clip_start,cam.data.clip_end],projection=cam.data.type,
                camera_axis='local -Z forward, +Y up',coordinate_system='meters; X east,Y north,Z up',
                camera_surface_clearance_7cm=camera_clear,
                test_scope='six-direction camera rays, not actor collision or action approval',
                source=source,blend_file=path.relative_to(ROOT).as_posix(),
                status='built_previs_not_final_character_or_scene_master',frames=rows)
    dump(OUT/'相机'/f'{scene.name}.json',output)
    return {k:v for k,v in output.items() if k not in ('frames','source')}


def render_still_retry():
    # Windows may transiently lock an overwritten preview while it is indexed.
    for attempt in range(3):
        try:
            bpy.ops.render.render(write_still=True)
            return
        except RuntimeError as exc:
            if 'cannot save' not in str(exc) or attempt == 2:
                raise
            time.sleep(.5)


def render_stills():
    global COL
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    MAT.clear()
    MAT.update({m.name: m for m in bpy.data.materials})
    views=[('MANOR_DAY','顾府总装'),('FOREST_DAY_SURVEY','林道总装'),('CITY_RELATION_ONLY','长京关系体块'),('MODERN_LOCAL','S07局部')]
    for name,label in views:
        s=bpy.data.scenes[name];bpy.context.window.scene=s
        s.render.engine='BLENDER_WORKBENCH'
        s.render.resolution_x,s.render.resolution_y=1440,810
        s.render.filepath=str(OUT/'预览'/f'{label}.png')
        render_still_retry()
    s=bpy.data.scenes['MANOR_DAY'];bpy.context.window.scene=s
    COL=collection('SURVEY_ONLY')
    for o in s.objects:
        if 'Roof' in o.name:o.hide_render=True
    camera('CAM_CutawayPlan',(0,16,80),(0,16,0),ortho=105)
    for label,x,y in [('S03',0,9),('S03-W',-18,10),('S04',14,23),('S05',-14,23),('S06',0,33),('S06-K',17,33),('S02',0,-7)]:
        text3d('PLAN_'+label,label,(x,y,5),1.15,'Accent')
    s.render.filepath=str(OUT/'预览'/'顾府俯视剖面.png')
    render_still_retry()
    for sid in SHOTS:
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'镜头'/f'{sid}.blend'))
        s=bpy.context.scene
        for phase,f in [('start',1),('middle',(s.frame_end+1)//2),('end',s.frame_end)]:
            s.frame_set(f);s.render.engine='BLENDER_EEVEE'
            s.eevee.taa_render_samples=64
            s.render.resolution_x,s.render.resolution_y=960,540
            s.render.filepath=str(OUT/'关键帧'/sid/f'{phase}.png')
            render_still_retry()


def render_inputs(shot=None):
    if shot is not None and shot not in SHOTS:
        raise ValueError('Unknown shot: '+shot)
    for sid in ([shot] if shot else SHOTS):
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'镜头'/f'{sid}.blend'))
        s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=64
        for o in s.objects:
            if o.name.startswith(('C02_','C01_','C03_','C_Rider_','C06_','C60_')):
                o.hide_render=True
        for phase,f in [('start',1),('middle',(s.frame_end+1)//2),('end',s.frame_end)]:
            s.frame_set(f);s.render.image_settings.file_format='PNG'
            s.render.filepath=str(OUT/'生成输入'/sid/f'background_{phase}.png')
            render_still_retry()
        s.frame_set(1)
        vl=s.view_layers[0];vl.use_pass_z=True;vl.use_pass_normal=True
        vl.use_pass_cryptomatte_object=True
        s.render.image_settings.media_type='MULTI_LAYER_IMAGE'
        s.render.image_settings.file_format='OPEN_EXR_MULTILAYER'
        s.render.image_settings.color_depth='32'
        s.render.filepath=str(OUT/'生成输入'/sid/'background_data.exr')
        render_still_retry()


def render_shot(sid,engine='BLENDER_WORKBENCH',background=False):
    path=OUT/'镜头'/f'{sid}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    s=bpy.context.scene
    s.render.engine=engine
    s.render.resolution_x,s.render.resolution_y=960,540
    if background:
        for o in s.objects:
            if o.name.startswith(('C02_','C01_','C03_','C_Rider_','C06_','C60_')):o.hide_render=True
    s.render.filepath=str(OUT/('背景帧' if background else '帧')/sid/'frame_')
    Path(s.render.filepath).parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.render.render(animation=True)


def audit():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    manor=bpy.data.scenes['MANOR_DAY'];forest=bpy.data.scenes['FOREST_DAY_SURVEY']
    bpy.context.window.scene=forest;bpy.context.view_layer.update()
    xs=[(o.matrix_world@Vector(c)).x for o in forest.objects if o.name.startswith('P01_') and o.type=='MESH' for c in o.bound_box]
    measured_package_width=max(xs)-min(xs)
    checks={
        'guest_beds_exactly_five':sum(bool(o.get('bed')) for o in manor.objects if o.name.startswith('S03W_'))==5,
        'bedroom_bed_separate':sum(bool(o.get('bed')) for o in manor.objects if o.name.startswith('S05_'))==1,
        'draft_row_abreast':len({round(o.matrix_world.translation.y,3) for o in forest.objects if o.name.startswith('P01_HitchHorse_') and o.name.endswith('_Body')})==1,
        'four_hitch_horses':sum(o.get('proxy_type')=='horse' for o in forest.objects if o.name.startswith('P01_'))==4,
        'four_riding_horses':sum(o.get('proxy_type')=='horse' for o in forest.objects if o.name.startswith('P19_'))==4,
        'escort_horses_at_role_corners':all((forest.objects['P19_RidingHorse_'+str(i+1)+'_Body'].matrix_world.translation-Vector((x,y,1.25))).length < 1e-4 for i,(_,_,x,y) in enumerate(ESCORT_CORNERS)),
        'escort_horse_role_bindings':all(forest.objects['P19_RidingHorse_'+str(i+1)].get('horse_id')==hid and forest.objects['P19_RidingHorse_'+str(i+1)].get('rider_id')==cid for i,(cid,hid,_,_) in enumerate(ESCORT_CORNERS)),
        'luggage_behind_cabin':all(forest.objects[n].location.y < forest.objects['P01_CabinBack'].location.y for n in ['P01_RearLuggageRack','P01_P02_Bag','P01_C23_Bag']),
        'draft_horses_without_riding_saddles':not any(o.name.startswith('P01_HitchHorse_') and '_Saddle' in o.name for o in forest.objects),
        'road_accommodates_eight_packages':forest.objects['S01_Road'].dimensions.x + 1e-5 >= 8*PACKAGE_WIDTH+7*.3,
        'package_proxy_contains_actual_carriage':PACKAGE_WIDTH>=measured_package_width,
        'street_and_manor_share_scene':all(n in manor.objects for n in ['S02_Street','S03_GateLeaf','S04_Desk','S06K_Door']),
        'no_central_pond_geometry':not any('Pond' in o.name for o in manor.objects),
        'study_window_faces_courtyard':abs(manor.objects['S04_WindowAnchor'].location.y-19)<.001,
        'rear_store_east_of_yard':manor.objects['S06K_Door'].location.x>0,
        'no_hero_face_mesh_in_forest':not any(o.name.startswith(('C60_Face','S01_C60Face')) and o.type=='MESH' for o in forest.objects),
        'no_central_gate_column':not any(o.name.startswith('S03_Gate_Column') and abs(o.location.x)<.1 for o in manor.objects),
    }
    counts={s.name:sum(o.type=='MESH' for o in s.objects) for s in bpy.data.scenes}
    master_sha=hashlib.sha256(MASTER.read_bytes()).hexdigest()
    manifest=json.loads((OUT/'镜头登记.json').read_text(encoding='utf-8'))
    source=shot_source();rows=[]
    for sid in SHOTS:
        path=OUT/'镜头'/f'{sid}.blend'
        bpy.ops.wm.open_mainfile(filepath=str(path))
        s=bpy.context.scene
        rows.append(export_camera(s,source[sid],path))
        checks[sid+'_camera_clearance']=rows[-1]['camera_surface_clearance_7cm']
        checks[sid+'_library_exists']=all(Path(bpy.path.abspath(lib.filepath)).is_file() for lib in bpy.data.libraries)
        checks[sid+'_source_frame_count']=s.frame_end==source[sid]['end_frame']-source[sid]['start_frame']
    manifest['shots']=rows;manifest['master_sha256']=master_sha
    dump(OUT/'镜头登记.json',manifest)
    dump(OUT/'空间检查.json',{'checks':checks,'passed':all(checks.values()),'mesh_counts':counts,
         'measured_carriage_full_width_m':measured_package_width,
         'coverage':'Structural counts, local camera clearance rays and file/timebase bindings only.',
         'not_verified':['final character anatomy','foot-contact animation','fight choreography','acoustics',
                         'finished art fidelity','AI video temporal preservation','all 71 shots']})
    if not all(checks.values()):raise RuntimeError('Spatial audit failed: '+str([k for k,v in checks.items() if not v]))
    print('SPATIAL_AUDIT',len(checks),'passed')


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','stills','inputs','audit','render','background'])
    parser.add_argument('shot',nargs='?');parser.add_argument('--engine',default='BLENDER_WORKBENCH')
    a=parser.parse_args(args)
    if a.command=='build':
        build_master()
        rows=[configure_shot(sid) for sid in SHOTS]
        dump(OUT/'镜头登记.json',{'format':'jingshi-blender-previs','blender_version':bpy.app.version_string,
             'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'shots':rows,
             'total_frames':sum(r['local_frame_end_inclusive'] for r in rows),
             'ai_generation_status':'not_submitted_account_access_required'})
    elif a.command=='stills':render_stills()
    elif a.command=='inputs':render_inputs(a.shot)
    elif a.command=='audit':audit()
    elif a.command=='background':render_shot(a.shot,a.engine,True)
    elif a.shot=='all':
        for sid in SHOTS:render_shot(sid,a.engine)
    else:render_shot(a.shot,a.engine)


if __name__=='__main__':main()
