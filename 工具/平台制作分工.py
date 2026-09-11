"""按用户的视频平台工作流区分母版与逐镜执行，不改媒体验收状态。"""
import json
from collections import Counter

LABELS = {'core': '核心母版', 'shot': '镜头按需', 'prompt': '提示词优先', 'execution': '后期与执行', 'reserve': '后续预备'}


def bind_routes(tasks, source):
    rows = json.loads(source.read_text(encoding='utf-8'))['tasks']
    ids = [r['task_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != {t['id'] for t in tasks}:
        raise ValueError('平台制作分工必须逐项覆盖现行任务，禁止重复或漏项')
    mapping = {r['task_id']: r for r in rows}
    for t in tasks:
        r = mapping[t['id']]
        if r['route'] not in LABELS or not r['reason'].strip():
            raise ValueError('制作路线或理由无效：' + t['id'])
        if (r['route'] == 'reserve') != (t['release_scope'] == 'followup_reserve'):
            raise ValueError('制作范围不一致：' + t['id'])
        t['production_route'] = r['route']
        t['production_reason'] = r['reason']


def render_routes(data):
    tasks = data['tasks']
    text = '# 视频平台制作分工\n\n当前必要范围见[必要资产与分镜设计](必要资产与分镜设计.md)：人物三视图、主要角色表情九宫格及场景多视角均须准备。下表只统计旧任务条目，未覆盖全部必要资产包，不能用其核心完成比例判定就绪。\n\n'
    text += '采用核心母版＋逐镜按需生成。适用于准备向LibTV、小云雀等平台交接的素材组织；本表不假定具体平台支持多图、首尾帧或声音控制，实际提交前按所选模型能力适配。\n\n'
    text += '先选要制作的镜头，只补该镜头缺少的核心参考与构图，再生成视频。不要等待全表完成；不要把每条提示词拆成独立资产。已有媒体保留复用，任务编号、实际完成状态和原验收条件不变。\n\n'
    text += '| 分工 | 前三集任务数 | 已选素材 | 候选素材 | 尚无已选素材 |\n|---|---:|---:|---:|---:|\n'
    current = [t for t in tasks if t['release_scope'] == 'current_first_three']
    for route in ('core', 'shot', 'prompt', 'execution'):
        group = [t for t in current if t['production_route'] == route]
        counts = Counter(t['media_status'] for t in group)
        text += f"| {LABELS[route]} | {len(group)} | {counts['selected']} | {counts['generated_candidate']} | {len(group)-counts['selected']} |\n"
    text += '\n“尚无已选素材”包含候选，并非必须另生成的图片数。核心母版按镜头需要准备，已有图可复用；提示词优先任务的未生成状态不阻止镜头制作，但生成结果仍需验收。\n\n'
    text += '人物锁本人脸与服装；雨湿、惊讶、转头、普通杯碗、沾粉手先写入镜头。反复切镜的伤侧、面巾或湿衣，以该场已通过的起始图继续派生。文书文字后制；碎杯需同源；马车四角护送、扶持接触与五道分剑需构图或动作参考，不能靠一句提示词跳过验证。\n\n'
    text += '执行顺序：核心人物与关键场景 → 对应镜头构图／起始图 → 单镜动作和运镜 → 接续、声音与剪辑验收。复杂镜头保留首尾状态、人数、道具归属和切点；平台不支持所需控制时拆镜实现。\n'
    for route, label in LABELS.items():
        text += f'\n## {label}\n\n| 任务 | 名称 | 当前媒体状态 | 执行依据 |\n|---|---|---|---|\n'
        for t in tasks:
            if t['production_route'] == route:
                text += f"| {t['id']} | {t['name']} | {t['media_status']} | {t['production_reason']} |\n"
    return text
