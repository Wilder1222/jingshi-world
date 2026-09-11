"""Local spatial/motion study of R01-SH021/022; not final character/VFX footage.

blender --background --python 工具/分剑动作预演.py -- build
blender --background --python 工具/分剑动作预演.py -- render
python 工具/分剑动作预演.py pack
Uses the existing forest master without rebuilding or modifying it.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '资产/三维预演/动作研究'
SOURCE = ROOT / '索引/数据/发行前三集.json'
MASTER = ROOT / '资产/三维预演/经世空间母场.blend'
BLEND = OUT / '分剑化形.blend'
FFMPEG = Path('D:/software/jianying/JianyingPro/11.3.0.14362/ffmpeg.exe')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    return [s for s in data['episodes'][0]['shots'] if s['id'] in ('GJ-R01-SH021', 'GJ-R01-SH022')]


def build():
    import bpy
    from mathutils import Vector
    spec = importlib.util.spec_from_file_location('spatial', ROOT / '工具/Blender场景预演.py')
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    parents = source()
    children = [s for p in parents for s in p['subshots']]
    first = parents[0]['start_frame']
    total = parents[-1]['end_frame'] - first
    if total != 360 or [c['end_frame']-c['start_frame'] for c in children] != [72,96,72,48,72]:
        raise ValueError('Study must be retimed to the changed authored subshot windows')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'S01_SPLIT_SWORD_MOTION_STUDY'
    base.setup(scene, engine='BLENDER_WORKBENCH', width=960, samples=8)
    base.palette()
    base.material('StudySword', (.38, .9, 1), .2)
    base.material('StudyShield', (.12, .58, .52), .4)
    base.material('StudyAura', (1, .66, .25), .4)
    with bpy.data.libraries.load(str(MASTER), link=True) as (_, dst):
        dst.collections = ['FOREST_S01']
    # Local object copies allow battle horse/bag states; source master remains immutable.
    col = bpy.data.collections.new('FOREST_STUDY_COPY')
    scene.collection.children.link(col)
    copies = {}
    for obj in dst.collections[0].objects:
        own = obj.copy()
        own.name = obj.name + '_STUDY'
        col.objects.link(own)
        copies[obj.name] = own
    for name, own in copies.items():
        if own.parent:
            own.parent = copies[own.parent.name]
    base.COL = base.collection('STUDY_ACTION')
    for i, dest in enumerate([(8,-1),(8,-4),(10,-4),(12,-4)], 1):
        body = copies[f'P19_RidingHorse_{i}_Body']
        copies[f'P19_RidingHorse_{i}'].location = (dest[0]-body.location.x,dest[1]-body.location.y,0)
    copies['P01_P02_Bag'].location = (14.1,1.6,.3)

    def curve(name, points, material, radius=.025):
        data = bpy.data.curves.new(name, 'CURVE')
        data.dimensions = '3D'
        data.bevel_depth = radius
        data.bevel_resolution = 1
        line = data.splines.new('POLY')
        line.points.add(len(points)-1)
        for point, xyz in zip(line.points, points):
            point.co = (*xyz, 1)
        obj = bpy.data.objects.new(name, data)
        base.COL.objects.link(obj)
        base.assign(obj, material)
        return obj

    def smooth(value):
        value=max(0.0,min(1.0,value))
        return value*value*(3-2*value)

    def leg(parts, side, ankle, hip, frame):
        # Two rigid limb lengths; bend the knee forward while each planted foot stays in world space.
        ankle,hip=Vector(ankle),Vector(hip)
        delta=ankle-hip; distance=delta.length
        if not .02<distance<.85:
            raise ValueError(f'Unreachable proxy leg at frame {frame}: {distance}')
        axis=delta.normalized()
        along=(.42**2-.43**2+distance**2)/(2*distance)
        bend=Vector((0,-1,0));bend=(bend-axis*bend.dot(axis)).normalized()
        knee=hip+axis*along+bend*math.sqrt(max(0,.42**2-along**2))
        base.limb_pose(parts[side+'thigh'],hip,knee,frame,.075)
        base.limb_pose(parts[side+'leg'],knee,ankle,frame,.065)
        base.keyed(parts[side+'foot'],frame,p=(ankle.x,ankle.y-.06,ankle.z-.03))

    defenders = {'C01':(14.7,2.7,0),'C23':(15.22,2.65,0),'C03':(14.3,3.7,0),
                 'C16':(15.6,4.3,0),'C17':(16.3,2.6,0),'C20':(14.5,1.2,0)}
    rigs={}
    for cid, pos in defenders.items():
        root, parts = base.puppet(cid+'_Study', pos, 'GuProxy' if cid=='C01' else 'GuardProxy')
        root['character_id'] = cid;rigs[cid]=(root,parts)
        crouch=.62 if cid=='C01' else .34 if cid=='C23' else .15
        base.pose(parts,1,crouch,0)
        if cid in ('C01','C23'):
            for side,x in [('L',-.18),('R',.18)]:
                leg(parts,side,(x,0,.08),(x,0,.86-crouch),1)
    # The supporter has two actual proxy contact points on Gu's uninjured right arm.
    gu_root,gu_parts=rigs['C01'];xu_root,xu_parts=rigs['C23']
    gu_elbow=Vector((15.02,2.63,.60));gu_wrist=Vector((15.20,2.52,.65))
    base.limb_pose(gu_parts['Rupper'],(.27,0,.74),gu_elbow-gu_root.location,1,.065)
    base.limb_pose(gu_parts['Rfore'],gu_elbow-gu_root.location,gu_wrist-gu_root.location,1,.055)
    support=[]
    for side,target,elbow in [('L',gu_elbow,(14.92,2.67,.78)),('R',gu_wrist,(15.5,2.48,.8))]:
        x=-.27 if side=='L' else .27
        local=target-xu_root.location
        base.limb_pose(xu_parts[side+'upper'],(x,0,1.02),Vector(elbow)-xu_root.location,1,.065)
        base.limb_pose(xu_parts[side+'fore'],Vector(elbow)-xu_root.location,local,1,.055)
        hand=base.ball('C23_'+side+'_SupportHand',tuple(local),(.06,.06,.06),'GuardProxy',1);hand.parent=xu_root
        marker=bpy.data.objects.new('C01_'+side+'_SupportTarget',None);base.COL.objects.link(marker)
        marker.parent=gu_root;marker.location=target-gu_root.location
        support.append((hand,marker))
    # Each sword has one stable opponent/contact pairing, ordered across the fan.
    enemies = {'C58':(19.3,.5,0),'C06':(18.0,3.0,0),'C59':(20.0,2.8,0),
               'C07':(19.1,4.5,0),'C57':(20.2,5.5,0)}
    event_rows=[];contact_points=[];enemy_rigs={};attack_arcs=[]
    for i, (cid, pos) in enumerate(enemies.items()):
        root, parts = base.puppet(cid+'_Study',pos,'EnemyProxy')
        root['character_id'] = cid
        away=Vector((pos[0]-15.1,pos[1]-2.7,0)).normalized()
        angle=math.atan2(-away.x,away.y)
        root.rotation_euler.z=angle
        from mathutils import Matrix
        rot=Matrix.Rotation(angle,3,'Z')
        contact=96+i*4; step_start=contact+6
        hit=Vector(pos)+rot@Vector((.32,-1.4,1.25));contact_points.append(hit)
        blade=base.beam(cid+'_HeldBlade',(.32,-.48,1.1),(.32,-1.2,1.25),.035,'Copper');blade.parent=root
        schedule=[('L',step_start,step_start+16,0,.7),
                  ('R',step_start+16,step_start+36,0,1.2),
                  ('L',step_start+36,step_start+48,.7,1.2)]
        for f in range(1,361):
            positions={'L':0.0,'R':0.0};lifts={'L':0.0,'R':0.0}
            for side,begin,end,y0,y1 in schedule:
                if f>=begin:
                    q=smooth((f-begin)/(end-begin))
                    positions[side]=y0+(y1-y0)*q
                    lifts[side]=.12*math.sin(math.pi*q) if f<end else 0
            travel=(positions['L']+positions['R'])/2
            base.keyed(root,f,p=tuple(Vector(pos)+away*travel),rot=(0,0,angle))
            crouch=.10+.06*max(lifts.values())/.12
            base.pose(parts,f,crouch,0)
            for side,x in [('L',-.18),('R',.18)]:
                leg(parts,side,(x,positions[side]-travel,.08+lifts[side]),(x,0,.86-crouch),f)
            # Contact deflects the blade before either foot leaves its planted position.
            deflect=smooth((f-contact)/6)
            grip=Vector((.32,-.48,1.1-crouch*.2))
            elbow=Vector((.36,-.23,1.0-crouch*.2))
            tip=Vector((.32+.50*deflect,-1.2+.55*deflect,1.25+.25*deflect-crouch*.2))
            base.limb_pose(parts['Rupper'],(.27,0,1.36-crouch),elbow,f,.065)
            base.limb_pose(parts['Rfore'],elbow,grip,f,.055)
            base.limb_pose(blade,grip,tip,f,.035)
        arc=curve(cid+'_IncomingQi',[tuple(rot@Vector(v)+Vector(pos)-hit)
                    for v in [(.32,-1.2,1.25),(.32,-1.4,1.25),(.27,-1.85,1.1)]],
                    'StudyAura' if cid=='C06' else 'Copper',.025 if cid=='C06' else .014)
        arc.location=hit
        for f,factor in [(1,0),(72,0),(73,1),(contact,1),(contact+5,0),(360,0)]:
            arc.data.bevel_factor_end=factor;arc.data.keyframe_insert(data_path='bevel_factor_end',frame=f)
        for j in range(2):
            fragment=curve(cid+'_QiFragment_'+str(j),[(0,0,0),(.06,0,.1)],'StudyAura',.015)
            for f,loc,scale in [(1,hit,0),(contact,hit,0),(contact+1,hit,1),
                                (contact+5,hit+Vector((.15*(-1 if j else 1),0,.18)),1),
                                (contact+6,hit+Vector((.2*(-1 if j else 1),0,.24)),0),(360,hit,0)]:
                base.keyed(fragment,f,p=tuple(loc));fragment.scale=(scale,)*3;fragment.keyframe_insert(data_path='scale',frame=f)
        event_rows.append({'character_id':cid,'sword_shape':i+1,'contact_frame':contact,
                           'qi_clear_frame':contact+5,'first_step_frame':step_start,
                           'settled_frame':step_start+48,'foot_schedule':schedule})
        enemy_rigs[cid]=(root,parts,schedule)
        attack_arcs.append(arc)
    sleeve=base.cube('C60_StudySleeve',(21.5,8.65,1.1),(.22,.47,.45),'GreySleeve',.04)
    sleeve['character_id']='C60'
    for f,loc in [(1,(21.5,8.65,1.1)),(288,(21.5,8.65,1.1)),(360,(21.8,8.75,1.1))]:
        base.keyed(sleeve,f,p=loc)
    # Wire arcs test occupied protective space, not finished transparent shield material.
    arcs=[]
    for i in range(5):
        a=i*math.pi/5
        points=[(15.1+1.65*math.cos(t)*math.cos(a),2.7+1.65*math.cos(t)*math.sin(a),.1+2.0*math.sin(t))
                for t in [j*math.pi/24 for j in range(25)]]
        arc=curve('GUijing_Arc_'+str(i+1),points,'StudyShield',.018)
        center=Vector((15.1,2.7,.1))
        for point in arc.data.splines[0].points:
            point.co.xyz -= center
        arc.location=center
        for f,scale in [(1,1),(241,1),(288,.83),(360,.83)]:
            arc.scale=(scale,scale,1);arc.keyframe_insert(data_path='scale',frame=f)
        arcs.append(arc)
    swords=[]
    for i in range(5):
        # A hollow sword-shaped outline avoids pretending these are five physical props.
        o=curve('C60_SwordShape_'+str(i+1),[(0,0,-.95),(-.12,0,-.62),(-.12,0,.55),(-.25,0,.58),
                (-.25,0,.68),(-.07,0,.7),(-.07,0,.95),(.07,0,.95),(.07,0,.7),(.25,0,.68),
                (.25,0,.58),(.12,0,.55),(.12,0,-.62),(0,0,-.95)],'StudySword',.035)
        start=Vector((20.6,7.3,3.5))
        formed=Vector((19.5,1.2+i*1.5,3.2+math.sin(i*math.pi/4)*1.2))
        # Spread endpoints in depth as well as screen position; never collapse into one bundle.
        target=contact_points[i]+Vector((0,0,.95))
        contact=event_rows[i]['contact_frame']
        reveal=1 if i==2 else 22+i*8
        close_rank={0:0,4:0,1:1,3:1,2:2}[i]
        for f,loc,scale in [(1,start,1 if i==2 else 0),(reveal,start,1 if i==2 else 0),
                            (65,formed,1),(73,formed,1),(contact,target,1),(240,target,1),
                            (245+close_rank*14,target,1),(258+close_rank*14,target,0),(360,target,0)]:
            facing=Vector((12.7,1.16,1.06))-loc
            base.keyed(o,f,p=tuple(loc),rot=(0,0,math.atan2(facing.x,-facing.y)))
            o.scale=(scale,)*3;o.keyframe_insert(data_path='scale',frame=f)
        swords.append(o)
    aura=curve('C06_ProtectiveAura',[(.5*math.cos(t),0,.55*math.sin(t)) for t in [i*math.tau/32 for i in range(33)]],'StudyAura',.02)
    aura.location=tuple(enemy_rigs['C06'][0].location+Vector((0,0,1.15)))
    for f,scale in [(1,0),(169,0),(191,1),(288,1),(308,0),(360,0)]:
        aura.scale=(scale,)*3;aura.keyframe_insert(data_path='scale',frame=f)
    # Hard camera cuts follow authored child windows; no drifting camera between cuts.
    cams=[base.camera('POV_C01',(14.9,2.83,1.06),(19.5,4.2,3.6),23),
          base.camera('OBJECTIVE_RETREAT',(12.8,-5.4,4.6),(17.8,3.8,1.9),26),
          base.camera('HUANG_REACTION',(18.5,1.2,1.65),tuple(enemy_rigs['C06'][0].location+Vector((0,0,1.35))),50)]
    for child,cam in zip(children,[cams[0],cams[1],cams[2],cams[1],cams[2]]):
        marker=scene.timeline_markers.new(child['id'],frame=child['start_frame']-first+1)
        marker.camera=cam
    scene.camera=cams[0]
    scene.frame_start=1;scene.frame_end=total
    scene['source_scope']=';'.join(p['id'] for p in parents)
    scene['study_limit']='proxy contact and planted-foot geometry; not final choreography, photometry or character performance'
    scene.display.shading.light='STUDIO'
    scene.display.shading.background_type='WORLD'
    scene.world.color=(.025,.04,.065)
    scene.render.filepath=str(OUT/'帧/frame_')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'帧').mkdir(exist_ok=True)
    # Audit evaluated scene geometry, not only the animation plan.
    max_planted_drift=0.0;max_support_gap=0.0;max_contact_gap=0.0
    previous_feet={};first_lifts={}
    for frame in range(1,total+1):
        scene.frame_set(frame)
        for hand,marker in support:
            max_support_gap=max(max_support_gap,(hand.matrix_world.translation-marker.matrix_world.translation).length)
        for row,sword,arc in zip(event_rows,swords,attack_arcs):
            if frame==row['contact_frame']:
                tip=sword.matrix_world@Vector((0,0,-.95))
                hit=arc.matrix_world@Vector(arc.data.splines[0].points[1].co[:3])
                max_contact_gap=max(max_contact_gap,(tip-hit).length)
        for cid,(root,parts,schedule) in enemy_rigs.items():
            for side in ('L','R'):
                xyz=parts[side+'foot'].matrix_world.translation.copy()
                key=(cid,side)
                swinging=any(s==side and begin<frame<=end for s,begin,end,_,_ in schedule)
                if xyz.z>.052 and cid not in first_lifts:first_lifts[cid]=frame
                if key in previous_feet and not swinging:
                    max_planted_drift=max(max_planted_drift,(xyz-previous_feet[key]).length)
                previous_feet[key]=xyz
    for row in event_rows:
        row['observed_first_lift_frame']=first_lifts[row['character_id']]
        if row['observed_first_lift_frame']<=row['qi_clear_frame']:
            raise ValueError('Foot moved before incoming qi cleared')
    if max_contact_gap>.001 or max_support_gap>.001 or max_planted_drift>.001:
        raise ValueError(f'Proxy geometry failed: contact={max_contact_gap}, support={max_support_gap}, stance={max_planted_drift}')
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),relative_remap=True)
    sampled=[]
    for frame in [1,65,73,120,168,200,241,288,320,360]:
        scene.frame_set(frame)
        scene.render.filepath=str(OUT/f'帧核对-{frame:03}.png')
        bpy.ops.render.render(write_still=True)
        from bpy_extras.object_utils import world_to_camera_view
        active=[o for o in swords if o.scale.length>.01]
        projected=[]
        for o in active:
            points=[world_to_camera_view(scene,scene.camera,o.matrix_world@Vector(p[:3]))
                    for p in [p.co for p in o.data.splines[0].points]]
            projected.append({'id':o.name,'bounds':[min(p.x for p in points),min(p.y for p in points),
                                                   max(p.x for p in points),max(p.y for p in points)],
                              'all_in_front':all(p.z>0 for p in points)})
        sampled.append({'frame':frame,'active_sword_shapes':len(active),'projected_shapes':projected,
                        'camera':scene.camera.name})
    dump(OUT/'分剑动作登记.json',{'format':'jingshi-motion-study','role':'independent technical study, not final shot replacement',
         'source_sha256':sha(SOURCE),'source_parents':parents,'master_sha256':sha(MASTER),
         'builder_sha256':sha(Path(__file__)),'blend_sha256':sha(BLEND),'frames':total,'fps':24,'width':960,'height':540,
         'characters':list(defenders)+list(enemies)+['C60'],'sampled_shape_counts':sampled,
         'action_events':event_rows,'geometry_audit':{'evaluated_frames':total,
            'max_sword_qi_contact_gap_m':max_contact_gap,'max_proxy_support_gap_m':max_support_gap,
            'max_planted_foot_drift_m':max_planted_drift,
            'scope':'proxy endpoints and planted feet only; excludes clothing, fingers, balance, collisions and final performance'},
         'limitations':['proxy stepping is not anatomically approved choreography','proxy support points do not validate fingers or clothing contact','wire arcs are not final shield material',
                        'no rain simulation or interactive light validation','no dialogue or final soundtrack','C60 sleeve only, no face or hands'],
         'review_status':'awaiting_visual_review','video':None})


def render():
    import bpy
    reg=json.loads((OUT/'分剑动作登记.json').read_text(encoding='utf-8'))
    if reg['source_parents'] != source() or reg['builder_sha256'] != sha(Path(__file__)):
        raise ValueError('Source or builder changed; rebuild before rendering')
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene=bpy.context.scene
    scene.render.filepath=str(OUT/'帧/frame_')
    bpy.ops.render.render(animation=True)
    dump(OUT/'渲染登记.json',{'blend_sha256':sha(BLEND),'builder_sha256':sha(Path(__file__)),
         'frame_sha256':[sha(OUT/'帧'/f'frame_{i:04}.png') for i in range(1,reg['frames']+1)]})


def pack():
    import re
    regpath=OUT/'分剑动作登记.json'
    reg=json.loads(regpath.read_text(encoding='utf-8'))
    if reg['source_parents'] != source():
        raise ValueError('Authored parent/subshot content changed; rebuild before packaging')
    receipt=json.loads((OUT/'渲染登记.json').read_text(encoding='utf-8'))
    if receipt['blend_sha256'] != sha(BLEND) or receipt['builder_sha256'] != sha(Path(__file__)):
        raise ValueError('Render receipt does not match current scene or builder')
    for n in range(1,reg['frames']+1):
        if not (OUT/'帧'/f'frame_{n:04}.png').is_file():raise ValueError(f'Missing frame {n}')
        if receipt['frame_sha256'][n-1] != sha(OUT/'帧'/f'frame_{n:04}.png'):
            raise ValueError(f'Render frame changed: {n}')
    path=OUT/'分剑化形-动作研究.mp4'
    subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-y','-framerate','24','-i',str(OUT/'帧/frame_%04d.png'),
                    '-frames:v',str(reg['frames']),'-c:v','h264_nvenc','-b:v','5M','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
    result=subprocess.run([str(FFMPEG),'-hide_banner','-v','error','-i',str(path),'-progress','pipe:1','-nostats','-f','null','-'],
                          check=True,capture_output=True,text=True)
    frames=[int(n) for n in re.findall(r'^frame=(\d+)',result.stdout,re.M)]
    if not frames or frames[-1]!=reg['frames'] or result.stderr.strip():raise ValueError('Decode validation failed')
    reg['video']={'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'decoded_frames':frames[-1],
                  'duration_seconds':frames[-1]/24,'audio':'none'}
    dump(regpath,reg)
    write_view(reg)
    print('PACK_OK',frames[-1],'frames',frames[-1]/24,'seconds')


def write_view(reg):
    from html import escape
    children=[c for p in reg['source_parents'] for c in p['subshots']]
    first=reg['source_parents'][0]['start_frame']
    rows=''.join(f'<button data-start="{(c["start_frame"]-first)/24}" data-end="{(c["end_frame"]-first)/24}">'
                 f'<b>{escape(c["id"])}</b><span>{(c["start_frame"]-first)/24:g}–{(c["end_frame"]-first)/24:g} 秒 · '
                 f'{escape(c["purpose"])}</span></button>' for c in children)
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>分剑化形 · 动作研究</title><style>
*{box-sizing:border-box}body{margin:0;background:#10181c;color:#e3eded;font:16px/1.6 system-ui,sans-serif}
main{max-width:1240px;margin:auto;padding:36px 24px}h1{margin:6px 0;font-size:32px}p{color:#b4c9cb;max-width:900px}
.tag{color:#80ddd3;font-size:13px;letter-spacing:.12em}.layout{display:grid;grid-template-columns:minmax(0,3fr) minmax(240px,1fr);gap:20px}
video{width:100%;background:#050808;border-radius:12px}button{display:block;width:100%;text-align:left;color:inherit;background:#1b292e;border:1px solid #35484c;padding:12px;margin-bottom:8px;border-radius:8px;cursor:pointer}
button[aria-current=true]{border-color:#80ddd3;background:#234441}button span{display:block;font-size:13px;color:#bfd0d1}button:focus-visible,a:focus-visible{outline:3px solid #f2c77e}
.note{border-left:3px solid #e1b773;padding:10px 18px;background:#20292b;margin:22px 0}a{color:#80ddd3}.frames{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.frames img{width:100%;border-radius:8px}figure{margin:0}figcaption{font-size:13px;color:#b4c9cb}#clock{font-variant-numeric:tabular-nums}footer{margin-top:24px;color:#9db1b4;font-size:13px}@media(max-width:800px){.layout{grid-template-columns:1fr}.frames{grid-template-columns:1fr}main{padding:20px}}
</style><main><div class="tag">《经世》／林道惊杀／本地三维预演</div><h1>一剑分五，退敌收势</h1>
<p>15 秒 · 360 帧 · 24 fps · 960×540。对应 SH021—SH022 的五个子镜，研究分剑数量、退敌空间和切镜次序。点击右侧条目跳转；视频无声音。</p>
<div class="layout"><section><video id="film" controls preload="metadata" poster="帧核对-065.png" src="分剑化形-动作研究.mp4"></video><div id="clock" aria-live="off">预演 0.00 秒 ／ 第一集 __SOURCE_START__ 秒</div></section><nav aria-label="子镜跳转">__ROWS__</nav></div>
<div class="note"><strong>这是动作研究片，尚未通过正式镜头验收。</strong><br>青色轮廓＝剑气占位；绿色弧线＝护罩范围；橙色环＝黄祁气膜占位。本轮已加入剑气接触、刃气散开、分步退开与右臂两个扶持点；支撑脚按世界位置锁定。它们仍是代理几何，不能代替真实重心、手指衣料接触与动作表演验收。线框凝形、雨叶、交互光、表情与“撤”的声音仍待制作。</div>
<div class="frames"><figure><img src="帧核对-065.png" alt="低视点下的五道剑形"><figcaption>第 65 帧：低视点与五剑间距</figcaption></figure><figure><img src="帧核对-168.png" alt="客观镜头中的护送队与退开刺客"><figcaption>第 168 帧：客观机位确认敌我位置</figcaption></figure><figure><img src="帧核对-288.png" alt="剑形消隐后护送者仍聚在原顾附近"><figcaption>第 288 帧：剑形消失，护送者仍在</figcaption></figure></div>
<footer><a href="分剑化形-动作研究.mp4">打开视频</a> · <a href="分剑化形.blend">可编辑三维源</a> · <a href="分剑动作登记.json">来源与技术登记</a> · <a href="../README.md">三维预演说明</a><br>未使用外部服务或人物媒体；本片不将发行分镜的未生成状态改为完成。</footer></main>
<script>const v=document.querySelector('#film'),bs=[...document.querySelectorAll('button[data-start]')];bs.forEach(b=>b.onclick=()=>{v.currentTime=Number(b.dataset.start);v.pause()});v.ontimeupdate=()=>{document.querySelector('#clock').textContent=`预演 ${v.currentTime.toFixed(2)} 秒 ／ 第一集 ${(__SOURCE_START__+v.currentTime).toFixed(2)} 秒`;bs.forEach(b=>b.setAttribute('aria-current',v.currentTime>=Number(b.dataset.start)&&v.currentTime<Number(b.dataset.end)?'true':'false'))};</script></html>'''
    (OUT/'查看.html').write_text(html.replace('__ROWS__',rows).replace('__SOURCE_START__',str(first/24)),encoding='utf-8')


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['build','render','pack'])
    command=parser.parse_args(args).command
    {'build':build,'render':render,'pack':pack}[command]()
