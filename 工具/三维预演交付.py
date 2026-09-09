"""Package existing Blender frame sequences, inspect videos and prepare current handoff.

Uses standard Python only. Image generation and video account execution are separate.
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'资产/三维预演'
FFMPEG=Path('D:/software/jianying/JianyingPro/11.3.0.14362/ffmpeg.exe')


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def ff(args):
    p=subprocess.run([str(FFMPEG),'-hide_banner',*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(p.stderr[-2500:])
    return p.stdout,p.stderr


def video_info(path):
    out,err=ff(['-v','error','-i',str(path),'-map','0:v:0','-progress','pipe:1','-nostats','-f','null','-'])
    frames=[int(v) for v in re.findall(r'^frame=(\d+)',out,re.M)]
    micros=[int(v) for v in re.findall(r'^out_time_us=(\d+)',out,re.M)]
    return {'decoded_frames':frames[-1] if frames else None,
            'decoded_duration_seconds':micros[-1]/1e6 if micros else None,
            'decode_errors':err.strip()}


def exr_channels(path):
    # Read standard EXR header attributes (not pixel data). Multipart first part header.
    data=path.read_bytes()
    if data[:4]!=b'v/1\x01':raise ValueError('Not an EXR file')
    pos=8; channels=[];multipart=bool(int.from_bytes(data[4:8],'little') & 0x1000)
    def cstr(i):
        end=data.index(b'\0',i);return data[i:end].decode('utf-8'),end+1
    while True:
        while data[pos]:
            name,pos=cstr(pos);kind,pos=cstr(pos)
            size=int.from_bytes(data[pos:pos+4],'little');pos+=4
            payload=data[pos:pos+size];pos+=size
            if kind=='chlist':
                at=0
                while at<len(payload) and payload[at]:
                    end=payload.index(b'\0',at)
                    channels.append(payload[at:end].decode('utf-8'))
                    at=end+1+16
        pos+=1
        if not multipart or not data[pos]:break
    return channels


def pack():
    manifest=load(OUT/'镜头登记.json');source=load(ROOT/'索引/数据/发行前三集.json')
    src={s['id']:s for e in source['episodes'] for s in e['shots']}
    rows=[];movie_dir=OUT/'视频';movie_dir.mkdir(exist_ok=True)
    for shot in manifest['shots']:
        sid=shot['id'];n=shot['local_frame_end_inclusive']
        expected=[OUT/'帧'/sid/f'frame_{i:04d}.png' for i in range(1,n+1)]
        if not all(p.is_file() for p in expected):raise RuntimeError('Missing render frames: '+sid)
        target=movie_dir/f'{sid}.mp4'
        ff(['-y','-loglevel','error','-framerate','24','-start_number','1','-i',
            str(OUT/'帧'/sid/'frame_%04d.png'),'-frames:v',str(n),'-c:v','h264_nvenc',
            '-b:v','5M','-pix_fmt','yuv420p','-movflags','+faststart',str(target)])
        info=video_info(target)
        if info['decoded_frames']!=n or info['decode_errors']:raise RuntimeError(f'Invalid video {sid}: {info}')
        row={'id':sid,'role':'Blender material and blocking previs, not final AI video',
             'file':target.relative_to(ROOT).as_posix(),'sha256':sha(target),'fps':[24,1],
             'width':960,'height':540,'duration_seconds':n/24,**info}
        rows.append(row)
        # An exact submission worksheet, not a submitted generation or invented receipt.
        prompt=(f"基于本镜三维预演，保留原视频相机、构图、透视、时长和所有建筑边缘。镜号{sid}。"
                f"运镜：{src[sid]['camera']}。动作依据：{src[sid]['action']}。"
                '背景为高门世家古宅或既有寒季林道；依场景区分，不把林道改成宅院。'
                '将代理体替换为已验收角色后才能生成正式人物镜头；当前未绑定身份参考。'
                '门窗、柱列、柜案、车马数量和所属状态不得变化。C60脸与手保持不可见。')
        dump(OUT/'生成输入'/sid/'视频交接.json',{
            'source_shot_id':sid,'source_scene_id':src[sid]['scene_id'],
            'source_video':target.relative_to(ROOT).as_posix(),'source_video_sha256':sha(target),
            'camera_track':f'资产/三维预演/相机/{sid}.json','duration_seconds':n/24,
            'source_fps':[24,1],'aspect_ratio':'16:9','prompt_working':prompt,
            'provider':None,'model':None,'task_id':None,'returned_video':None,
            'status':'awaiting_video_account_and_character_binding',
            'unknown_capabilities':['video-conditioned geometry fidelity','frame rate','depth input','identity binding'],
            'do_not_submit_without':['available_authenticated_video_model','reviewed_model_input_mapping'],
            'fallback':'retain original rendered background; no account purchase or autonomous paid upgrade'})
    listing=movie_dir/'concat.txt'
    listing.write_text(''.join("file '"+r['id']+".mp4'\n" for r in rows),encoding='utf-8')
    combined=movie_dir/'五镜技术预演合集.mp4'
    ff(['-y','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(combined)])
    combined_info=video_info(combined)
    if combined_info['decoded_frames']!=manifest['total_frames']:raise RuntimeError('Combined frame count mismatch')
    # Reusable current concat recipe is retained; never a historical copy.
    all_shots=[]
    for e in source['episodes']:
        for s in e['shots']:
            all_shots.append({'id':s['id'],'source_scene_id':s['scene_id'],
                'source_frame_window':[s['start_frame'],s['end_frame']],
                'role':'original release parent unchanged',
                'previs_status':'rendered' if s['id'] in [r['id'] for r in rows] else 'not_previsualized',
                'final_media_status':s['media_status'],'camera_intent':s['camera']})
    dump(OUT/'全71镜衔接表.json',{'source_sha256':sha(ROOT/'索引/数据/发行前三集.json'),'shots':all_shots})
    result={'scope':'5 existing parent shots; 43 seconds; remaining 66 shots not previsualized',
            'videos':rows,'combined':{'file':combined.relative_to(ROOT).as_posix(),
            'sha256':sha(combined),**combined_info},'ai_video_status':'not_generated',
            'source_production_task_count':178,'final_assets_selected':False}
    dump(OUT/'交付检查.json',result)
    sid='GJ-R02-SH019';n=240
    bg_dir=OUT/'背景帧'/sid
    if all((bg_dir/f'frame_{i:04d}.png').is_file() for i in range(1,n+1)):
        bg_video=OUT/'生成输入'/sid/'background.mp4'
        ff(['-y','-loglevel','error','-framerate','24','-start_number','1','-i',str(bg_dir/'frame_%04d.png'),
            '-frames:v','240','-c:v','h264_nvenc','-b:v','5M','-pix_fmt','yuv420p','-movflags','+faststart',str(bg_video)])
        bg_info=video_info(bg_video)
        if bg_info['decoded_frames']!=240:raise RuntimeError('Background frame count mismatch')
        dump(OUT/'生成输入'/'空景视频小样.json',{
            'shot_id':sid,'input_video':bg_video.relative_to(ROOT).as_posix(),
            'input_sha256':sha(bg_video),'role':'first video preservation benchmark, no character binding required',
            'duration_seconds':10,'fps':[24,1],**bg_info,
            'prompt':'将这段原创三维空景预演中的木材、石材、墙面与金属表面处理为高端古装剧真实质感。只改表面材质细节，完整保留原视频的相机旋转、构图、透视、时长、所有墙体门窗和家具轮廓。夜景保持既有窗外冷光与案灯局部暖光。禁止移动案窗门或柜体，禁止新增梁柱、门窗、人物、家具和光源；铜镜是普通镜子。不要添加对白、文字、配乐或转场。',
            'provider':None,'model':None,'task_id':None,'returned_video':None,
            'status':'ready_local_input_awaiting_authenticated_video_model',
            'acceptance':['static landmarks follow rendered path','no added or removed geometry','24fps time mapping reviewed',
                          'no framewise shape breathing','review every occlusion change'],
            'round_limit_proposal':2,'purchase_authorized':False})
    gallery(rows)
    print('PACK_OK',len(rows),'videos',manifest['total_frames'],'frames')


def gallery(rows):
    cards=[]
    for row in rows:
        sid=row['id']
        cards.append(f'<article><h3>{sid}<span>{row["duration_seconds"]:g}秒 · 24fps</span></h3>'
            f'<video controls preload="metadata" poster="关键帧/{sid}/start.png" src="视频/{sid}.mp4"></video>'
            f'<p><a href="镜头/{sid}.blend">Blender镜头</a> · <a href="相机/{sid}.json">相机轨道</a> · '
            f'<a href="生成输入/{sid}/视频交接.json">生成交接</a></p></article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>经世 · 空间与镜头预演</title><style>
*{box-sizing:border-box}body{margin:0;background:#101b1c;color:#e7e5da;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:1380px;margin:auto;padding:48px 36px}header{border-bottom:1px solid #3c4c47;padding-bottom:25px;margin-bottom:30px}
small{letter-spacing:3px;color:#c6a878}h1{font-size:40px;font-weight:550;margin:10px 0}h2{margin-top:40px;font-weight:500}
p{color:#bcc8c2}a{color:#d5b984}section{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
article{background:#182829;padding:18px;border:1px solid #344744}h3{margin:0 0 12px;font-size:18px;font-weight:500}
h3 span{float:right;font-size:14px;color:#a6b7b0}img,video{width:100%;display:block;background:#0a1213}figure{margin:0}figcaption{font-size:14px;color:#b1c2b9;padding:10px 0}
.note{border-left:3px solid #c6a878;padding:8px 18px;background:#1e2d2a}.wide{max-height:680px;object-fit:contain}
@media(max-width:760px){main{padding:24px 16px}section{grid-template-columns:1fr}h1{font-size:28px}h3 span{float:none;display:block}}
</style><main><header><small>JINGSHI / SPATIAL PREVIS</small><h1>同一座宅院，同一条镜头路径</h1>
<p>米制三维母场 · 原发行父镜号 · 可编辑相机 · 24fps / 16:9</p></header>
<div class="note">这是空间、光照与代理走位预演。人物为无身份代理体；美术候选未选版；AI视频尚未生成。五段共43秒是技术样镜集合，非连续剧情，也不代表71镜已经完成。</div>
<h2>先看空间</h2><section>'''
    for name,caption in [('顾府总装','S02—S06共用宅区与街段'),('顾府俯视剖面','剖面只供量尺核对；不是剧情机位'),('林道总装','37米工作路宽；四驾与四坐骑分开'),('长京关系体块','四区关系示意，不能按此重算城市行程')]:
        page+=f'<figure><img src="预览/{name}.png" alt="{name}"><figcaption>{caption}</figcaption></figure>'
    page+='</section><h2>五个已有镜头</h2><section>'+''.join(cards)+'</section>'
    page+='''<h2>待送入AI的10秒空景</h2><video controls preload="metadata" src="生成输入/GJ-R02-SH019/background.mp4"></video>
<p>移除人物代理，保留书房完整摇镜。当前为Blender渲染，AI返回视频尚未生成。</p>
<h2>灰模到美术：一次结构保持试验</h2><section>
<figure><img src="生成输入/GJ-R02-SH016/background_start.png" alt="原始三维空景"><figcaption>原始三维空景 / 空间依据</figcaption></figure>
<figure><img src="生成输入/S04-美术候选.png" alt="生成美术候选"><figcaption>内置图像生成候选 / 材质与雕工参考，几何未获通过</figcaption></figure>
</section><p>图像候选增加了梁柱装饰和窗格细节，需核几何偏差；不能替代原相机或认定整段视频会保留空间。</p>
<p><a href="README.md">交付说明与尚未完成项</a> · <a href="经世空间母场.blend">共用母场</a> · <a href="交付检查.json">文件与视频检查</a> · <a href="空间检查.json">空间检查范围</a></p>
</main></html>'''
    (OUT/'预演查看.html').write_text(page,encoding='utf-8')


def check():
    m=load(OUT/'交付检查.json');s=load(OUT/'空间检查.json')
    assert s['passed'],s
    for row in m['videos']:
        p=ROOT/row['file'];assert p.is_file() and sha(p)==row['sha256']
        assert row['decoded_frames']==round(row['duration_seconds']*24)
    combined=m['combined']
    assert sha(ROOT/combined['file'])==combined['sha256']
    assert combined['decoded_frames']==1032 and not combined['decode_errors']
    background=load(OUT/'生成输入'/'空景视频小样.json')
    assert sha(ROOT/background['input_video'])==background['input_sha256']
    assert background['decoded_frames']==240 and not background['decode_errors']
    assert len(load(OUT/'全71镜衔接表.json')['shots'])==71
    data=[]
    for row in m['videos']:
        p=OUT/'生成输入'/row['id']/'background_data.exr'
        channels=exr_channels(p)
        for needed in ['Depth','Normal','CryptoObject']:
            if not any(needed in c for c in channels):raise RuntimeError('Missing EXR pass: '+needed)
        data.append({'shot':row['id'],'file':p.relative_to(ROOT).as_posix(),'channels':channels,'bytes':p.stat().st_size})
    dump(OUT/'数据通道检查.json',{'files':data,'scope':'All EXR part headers include Depth, Normal and CryptoObject; numeric pixel semantics not independently decoded'})
    print('CHECK_OK: videos, spatial assertions, 71-parent mapping, EXR headers')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['pack','check']);a=p.parse_args()
    pack() if a.command=='pack' else check()
