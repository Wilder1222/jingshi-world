"""把发行分镜源中的当前二维关系方案导出为可切换的走位图，不建模。"""
import json


def validate_blocking(release):
    ep = release['episodes'][0]
    plan = ep.get('blocking_plan', {})
    if plan.get('status') != 'draft_unverified' or plan.get('scale') != 'schematic_not_metric':
        raise ValueError('二维走位须标为待核的非比例工作图')
    shots = {s['id']: s for s in ep['shots']}
    vets = set(ep['combat_contract']['formation_members'])
    foes = set(ep['combat_contract']['blocked_opponents']) | {'C06'}
    first = {f'S01-W1-{n:02}' for n in range(1, 11)}
    panels = plan.get('panels', [])
    if [p['key'] for p in panels] != ['paired', 'cleared', 'pressed', 'formation', 'rescue', 'support']:
        raise ValueError('二维走位缺关键阶段')
    previous = -1
    for p in panels:
        selected = [shots[sid] for sid in p['shot_ids'] if sid in shots]
        if len(selected) != len(p['shot_ids']) or not selected or selected[0]['start_frame'] < previous:
            raise ValueError('二维走位引用镜头失配或倒序')
        previous = selected[-1]['end_frame']
        ids = [a['id'] for a in p['actors']]
        expected = vets | {'C01'}
        expected |= first if p['key'] == 'paired' else (set() if p['key'] in ('cleared', 'support') else foes)
        if p['key'] == 'rescue':
            expected.add('C60')
            point = p.get('intercept_point', [])
            if len(point) != 2 or any(type(v) not in (int, float) or not 0 <= v <= bound for v, bound in zip(point, [1200, 720])):
                raise ValueError('二维走位缺有效截刃分化点')
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise ValueError('二维走位人数、波次或身份失配')
        if p['first_wave_offstage'] != (0 if p['key'] == 'paired' else 10) or p['second_wave_offstage'] != (5 if p['key'] == 'support' else 0):
            raise ValueError('二维走位退场人数失配')
        if p['formation'] != (p['key'] in ('formation', 'rescue')):
            raise ValueError('二维走位提前结阵或未收阵')
        for a in p['actors']:
            if not all(type(a[k]) in (int, float) and 0 <= a[k] <= bound for k, bound in [('x', 1200), ('y', 720)]):
                raise ValueError('二维走位坐标越界')
        if any(len(pair) != 2 or not set(pair) <= set(ids) for pair in p['links']):
            raise ValueError('二维走位连线引用失配')
        if p['formation']:
            x, y, w, h = plan['formation_bounds']
            inside = {a['id'] for a in p['actors'] if x <= a['x'] <= x + w and y <= a['y'] <= y + h}
            if inside != vets:
                raise ValueError('二维走位必须五卒在阵、顾黄在阵外')
    return plan


def render_blocking(release):
    plan = validate_blocking(release)
    shots = {s['id']: {k: s[k] for k in ('id', 'start_frame', 'end_frame', 'action', 'camera')}
             for s in release['episodes'][0]['shots']}
    payload = json.dumps(dict(plan=plan, shots=shots), ensure_ascii=False).replace('<', '\\u003c')
    return TEMPLATE.replace('/*BLOCKING_DATA*/', payload)


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>林道惊杀 · 二维走位</title><style>
*{box-sizing:border-box}body{margin:0;background:#10191d;color:#e8ece8;font:16px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1280px;margin:auto;padding:30px 24px}header{display:flex;gap:24px;justify-content:space-between;align-items:end}h1{font-size:30px;line-height:1.2;margin:5px 0 14px}p{margin:8px 0;color:#adbdbe}.eyebrow{font-size:12px;letter-spacing:.12em;color:#8bbdb5}a{color:#90d5c7}.notice{max-width:440px;font-size:13px}nav{display:flex;gap:8px;margin:24px 0 14px;flex-wrap:wrap}button{font:inherit;color:#b6c7c8;background:#18282d;border:1px solid #355058;border-radius:7px;padding:10px 14px;cursor:pointer}button[aria-pressed=true]{background:#abd2c3;color:#132421;border-color:#abd2c3}button:focus-visible,input:focus-visible{outline:3px solid #f0c571;outline-offset:3px}.bar{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;font-size:13px;color:#afc4c7;margin-bottom:10px}.canvas{border:1px solid #35484d;border-radius:10px;overflow:hidden;background:#19292d}svg{display:block;width:100%;height:auto}svg text{font-family:system-ui,"Microsoft YaHei",sans-serif}.bottom{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:18px}.bottom h2{font-size:17px;margin:0 0 6px}.bottom p{font-size:14px}.legend{display:flex;gap:20px;font-size:13px;flex-wrap:wrap;margin-top:10px}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}details{border-top:1px solid #33494d;padding-top:12px;margin-top:18px}summary{cursor:pointer;color:#c2d1d0}details p{font-size:13px}footer{font-size:12px;color:#91a9ad;margin-top:22px}@media(max-width:700px){main{padding:20px 12px}header{display:block}.bottom{grid-template-columns:1fr;gap:12px}h1{font-size:25px}button{font-size:13px;padding:9px}}
</style></head><body><main><header><div><div class="eyebrow">《经世》／第一集／场内关系工作图</div><h1>林道惊杀 · 六个战斗状态</h1></div><p class="notice">二维示意，无米制比例。图面上方是前行方向，右侧是近林；机位仅作同侧覆盖建议，真实遮挡与身体接触仍待验证。</p></header>
<nav id="phases" aria-label="战斗阶段"></nav><div class="bar"><span id="window"></span><label><input id="camera" type="checkbox"> 显示同侧机位建议</label><span id="counts" aria-live="polite"></span></div>
<div class="canvas"><svg id="map" viewBox="0 0 1200 720" role="img" aria-labelledby="map-title map-desc"><title id="map-title"></title><desc id="map-desc"></desc><g id="drawing"></g></svg></div>
<div class="legend"><span><i style="background:#e4bf75"></i>原顾</span><span><i style="background:#9dcfbf"></i>五卒</span><span><i style="background:#de9992"></i>刺客</span><span><i style="background:#c5bfde"></i>黄祁</span><span>灰虚线＝交锋；金虚线＝顾的视线；浅实线＝剑形来向</span></div>
<div class="bottom"><section><h2 id="heading"></h2><p id="focus"></p></section><section><h2>镜头与画外接续</h2><p id="continuity"></p></section></div>
<details><summary>查看对应的现行分镜</summary><div id="source"></div></details>
<footer><a href="前三集节奏与分镜.md">完整分镜与对白</a> · <a href="../../../索引/数据/发行前三集.json">唯一分镜源</a> · <a href="../../../剧集/01-归京/GJ-EP01-归京.md">第一集台本</a><br>六个状态是原父镜窗口内的示意，不是连续动画，不追加片长，不代表完成建模、生成或动作验收。</footer></main>
<script>
const data=/*BLOCKING_DATA*/;
const labels={C01:'原顾',C03:'韩青',C16:'杜长庚',C17:'石照川',C20:'崔望野',C23:'许照邻',C06:'黄祁',C07:'罗顺',C57:'灰领',C58:'褐袖',C59:'窄额带',C60:'树后灰袖'};
const vets=new Set(['C03','C16','C17','C20','C23']);
const el=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const txt=(x,y,s,color='#93aaad',size=14,anchor='start')=>`<text x="${x}" y="${y}" fill="${color}" font-size="${size}" text-anchor="${anchor}">${esc(s)}</text>`;
let selected=0;
function base(){let v=`<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10" fill="#809da1"/></marker></defs><path d="M 1040 0 V720" stroke="#415852" stroke-dasharray="6 7"/><rect x="1041" width="159" height="720" fill="#13251f"/>`;
 v+=txt(1120,43,'近林遮挡','#84a497',16,'middle')+txt(80,670,'官道向左侧延展；此图只画车旁局部，不以阵宽代替路宽');
 v+=`<path d="M105 150V60" stroke="#7c999f" stroke-width="2" marker-end="url(#arrow)"/>`+txt(127,87,'E 前方林口')+txt(127,111,'桥不在战斗画面内',undefined,12);
 for(let y=95;y<690;y+=95)v+=`<path d="M1130 ${y-30}v70m-24-44 24 18 27-32" stroke="#264438" stroke-width="6" fill="none"/>`;
 v+=`<rect x="270" y="220" width="130" height="195" rx="15" fill="#293941" stroke="#9aa5a4" stroke-width="2"/><path d="M405 271v40" stroke="#f0c570" stroke-width="5"/><rect x="405" y="303" width="22" height="35" fill="#576361"/>`+txt(335,295,'P01','#d0d7d4',19,'middle')+txt(335,322,'封闭车厢','#b8c8c6',14,'middle')+txt(426,267,'D 右门',undefined,13);
 for(let i=0;i<4;i++)v+=`<rect x="${224+i*49}" y="149" width="30" height="46" rx="12" fill="#6f7467"/>`;
 v+=txt(325,134,'四匹牵引马','#b3beb4',13,'middle');
 for(let i=0;i<4;i++)v+=`<rect x="${145+(i%2)*52}" y="${520+Math.floor(i/2)*69}" width="32" height="45" rx="12" fill="#526a67"/>`;
 v+=txt(152,505,'H 四骑避让区',undefined,13)+txt(150,649,'P02已放在干实处；战后再收至H08',undefined,12);
 v+=`<path d="M1064 151v58" stroke="#4b6557" stroke-width="14"/>`+txt(1060,136,'M 高树','#abc1b3',13,'middle');
 v+=txt(1100,350,'F', '#abc1b3',18,'middle')+txt(1100,374,'同侧林隙','#abc1b3',13,'middle');
 return v;}
function draw(){const p=data.plan.panels[selected],actors=Object.fromEntries(p.actors.map(a=>[a.id,a]));let v=base();
 if(p.formation){let [x,y,w,h]=data.plan.formation_bounds;v+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="70" fill="#7ebfbe" fill-opacity=".065"/><path d="M780 352Q882 487 780 622" fill="none" stroke="#8cd5c8" stroke-width="6"/>`+txt(690,645,'五卒阵位 · 护罩拦四','#9ed5cb',14,'middle');}
 v+=`<ellipse cx="530" cy="282" rx="133" ry="65" fill="none" stroke="#596963" stroke-dasharray="3 8"/>`+txt(550,204,'G 门前侧实地','#b4bcb0',13,'middle');
 for(const [a,b] of p.links){let q=actors[a],r=actors[b];v+=`<path d="M${q.x} ${q.y}L${r.x} ${r.y}" stroke="#bbaba1" stroke-opacity=".6" stroke-dasharray="5 7"/>`;}
 if(p.key==='rescue'){const [ix,iy]=p.intercept_point,origin=actors.C60,gu=actors.C01;
 v+=`<path d="M${gu.x} ${gu.y}L${origin.x} ${origin.y}" fill="none" stroke="#b5a889" stroke-width="2" stroke-dasharray="3 7"/>`;
 for(const [n,id] of ['C06','C58','C07','C57','C59'].entries()){let a=actors[id];v+=`<path d="M${ix} ${iy}Q${n===0?630:880} ${n===0?250:230} ${a.x} ${a.y-18}" fill="none" stroke="#e0dfc7" stroke-width="3"/>`+txt(a.x-27,a.y-22,String(n+1),'#f0e9c6',12,'middle');}
 v+=`<circle cx="${ix}" cy="${iy}" r="8" fill="#ece4bf" stroke="#25393c" stroke-width="2"/>`+txt(ix-10,iy-27,'截刃／分化点','#ece4bf',13,'middle')+txt(865,105,'近处分化 · 灰袖仍在远处','#dfdfcb',14,'middle')+txt(865,129,'虚线为视线；实线为来向示意','#afa98b',12,'middle');}
 for(const a of p.actors){let color=a.id==='C01'?'#e4bf75':vets.has(a.id)?'#9dcfbf':a.id==='C06'?'#c5bfde':a.id==='C60'?'#b7bfbe':'#de9992';let name=labels[a.id]||a.id.replace('S01-','');let short=a.id.startsWith('S01-')?a.id.slice(-2):a.id;
 v+=`<g data-actor="${a.id}"><circle cx="${a.x}" cy="${a.y}" r="18" fill="${color}"/><text x="${a.x}" y="${a.y+4}" fill="#14252a" font-size="11" text-anchor="middle">${short}</text>`+txt(a.x,a.y+38,name,color,13,'middle')+'</g>';}
 if(p.key==='rescue')v+=`<path d="M1064 151v58" stroke="#4b6557" stroke-width="14"/>`;
 if(el('camera').checked)v+=`<g id="camera-guide"><path d="M370 626L540 466" fill="none" stroke="#91acb4" stroke-width="2" marker-end="url(#arrow)"/><path d="M350 610h36v26h-36z" fill="#67878b"/></g>`+txt(385,688,'同侧机位意向；不跨顾黄交锋轴线翻面', '#b8c8cb',13);
 el('drawing').innerHTML=v;el('map-title').textContent=p.title;el('map-desc').textContent=p.focus;el('heading').textContent=p.title;el('focus').textContent=p.focus;
 const ss=p.shot_ids.map(id=>data.shots[id]);el('window').textContent=`${ss[0].start_frame/24}—${ss.at(-1).end_frame/24} 秒 · ${p.shot_ids.join(' / ')}`;
 const enemies=p.actors.filter(a=>!vets.has(a.id)&&!['C01','C60'].includes(a.id)).length;el('counts').textContent=`我方 6 人 · 当前来敌 ${enemies} 人${p.key==='rescue'?' · 救者 1 人':''}`;
 el('continuity').textContent=(['paired','cleared'].includes(p.key)?'第二波尚未入场。':'')+`第一波退场 ${p.first_wave_offstage}/10；第二波退场 ${p.second_wave_offstage}/5。四驾与四骑分计；所有人物点位均为局部相对关系，不是量尺坐标。`;
 el('source').innerHTML=ss.map(s=>`<p><strong>${s.id}</strong> · ${esc(s.action)}<br>机位：${esc(s.camera)}</p>`).join('');
 [...el('phases').children].forEach((b,i)=>b.setAttribute('aria-pressed',i===selected));}
 data.plan.panels.forEach((p,i)=>{let b=document.createElement('button');b.type='button';b.textContent=`${i+1} ${p.title}`;b.onclick=()=>{selected=i;draw()};el('phases').appendChild(b)});el('camera').onchange=draw;draw();
</script></body></html>'''
