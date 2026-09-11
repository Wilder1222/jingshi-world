"""从现行媒体登记生成编号总览及任务缺口；不把匹配当作选版。"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def validate_media_provenance(root, registry):
    """生成当时的原图与当前身份锚点分开核对，不把换版当成重新生成。"""
    paths = set()
    current = {m['path']: m['sha256'] for m in registry['masters']}
    for row in registry['masters'] + registry.get('matched_references', []) + registry.get('generated_assets', []):
        generation = row.get('generation', {})
        refs = generation.get('execution_style_references', []) + generation.get('auxiliary_input_references', [])
        refs += [dict(path=p, sha256=h) for p, h in generation.get('style_reference_sha256', {}).items()]
        if row.get('current_style_anchor'):
            anchor = row['current_style_anchor']
            if current.get(anchor['path']) != anchor['sha256']:
                raise ValueError('当前视觉锚点已失效')
            refs.append(anchor)
        for ref in refs:
            target = (root / ref['path']).resolve()
            allowed = any(target.is_relative_to((root / base).resolve()) for base in ('资产/媒体', '参考/用户媒体'))
            if not allowed or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != ref['sha256']:
                raise ValueError('图像实际生成来源失配：' + ref['path'])
            paths.add(ref['path'])
    return paths


def load_generated(tasks):
    registry = json.loads((ROOT / '资产/媒体/母版登记.json').read_text(encoding='utf-8'))
    rows = registry.get('generated_assets', [])
    by_id = {t['id']: t for t in tasks}
    seen = set()
    support_ids = set()
    for row in rows:
        path = (ROOT / row['path']).resolve()
        if row['task_id'] in seen or row['task_id'] not in by_id:
            raise ValueError('生成候选任务重复或不存在')
        seen.add(row['task_id'])
        for item in row.get('supporting_assets', []):
            validate_support(item, row, support_ids, row.get('supporting_assets', []))
        if not path.is_relative_to((ROOT / '资产/媒体').resolve()) or not path.is_file():
            raise ValueError('生成候选文件缺失或越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('生成候选哈希不符')
        if row['status'] not in ('generated_candidate', 'selected') or not row['generation']['prompt'] or not row['review']['remaining']:
            raise ValueError('生成候选缺执行记录或复核边界')
        if row['status'] == 'selected' and (row['review']['status'] != 'passed_task_review' or not row.get('selected_by') or not row['review'].get('scope')):
            raise ValueError('生成选版缺任务验收范围或执行者')
        masters = {m['id']: m for m in registry['masters'] + rows if m.get('status') == 'selected'}
        for ref in row['generation']['input_references']:
            if ref.get('purpose') == 'registered_style_reference':
                source = next((m for m in registry.get('matched_references', []) if m['id'] == ref['master_id']), None)
                if not source or ref['path'] != source['path'] or ref['sha256'] != source['sha256']:
                    raise ValueError('生成输入风格参考失配')
                continue
            if ref['master_id'] not in masters or ref['sha256'] != masters[ref['master_id']]['sha256']:
                raise ValueError('生成候选输入母版失配')
        task = by_id[row['task_id']]
        if task['media_status'] == 'selected' or set(task['asset_ids']) != set(row['asset_ids']):
            raise ValueError('生成候选不能覆盖选版或跨资产绑定')
        accepted = row['status'] == 'selected'
        task.update(media_status=row['status'], status='selected_generated_asset' if accepted else 'awaiting_candidate_review', actual_file=row['path'], selected_master_id=row['id'] if accepted else None)
    accepted = {r['task_id']: r for r in rows if r['status'] == 'selected'}
    selected_ids = {t['id'] for t in tasks if t['media_status'] == 'selected'}
    for task in tasks:
        task['unresolved_dependencies'] = [d for d in task['depends_on'] if d not in selected_ids]
        lineage, todo = set(), list(task['depends_on'])
        while todo:
            dep = todo.pop()
            if dep not in by_id:
                raise ValueError('生成派生缺前置任务')
            if dep not in lineage:
                lineage.add(dep)
                todo.extend(by_id[dep]['depends_on'])
        for tid in sorted(lineage & accepted.keys()):
            m = accepted[tid]
            task['input_references'].append(dict(master_id=m['id'], path=m['path'], sha256=m['sha256'], purpose='selected_generated_asset', constraints=m['review']['scope']))
        if not task['unresolved_dependencies'] and task['media_status'] == 'not_generated':
            task['status'] = 'ready_for_exploration'
        if task['media_status'] == 'selected' and task['unresolved_dependencies']:
            raise ValueError('未通过前置不能验收派生任务')
    return rows


def validate_support(item, parent, seen, siblings=()):
    path = (ROOT / item['path']).resolve()
    if item['id'] in seen:
        raise ValueError('个体派生编号重复')
    seen.add(item['id'])
    if not path.is_relative_to((ROOT / '资产/媒体').resolve()) or not path.is_file():
        raise ValueError('个体派生文件缺失或越界')
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('个体派生哈希不符')
    sources = {parent['id']: parent}
    sources.update({s['id']: s for s in siblings if s['id'] != item['id'] and s['review']['status'] == 'passed_candidate_visual_review'})
    refs = item['generation']['input_references']
    if parent['status'] != 'selected' or not refs or any(r['master_id'] not in sources or r != dict(master_id=r['master_id'], path=sources[r['master_id']]['path'], sha256=sources[r['master_id']]['sha256']) for r in refs):
        raise ValueError('个体派生输入母版失配')
    if item['status'] != 'visual_candidate' or not item['generation']['prompt'] or not item['review']['remaining']:
        raise ValueError('个体派生缺提示词或复核边界')


def render_mapping(data):
    rows = []
    for m in data['selected_masters'] + data['pending_master_candidates'] + data['matched_asset_references']:
        ids = m.get('asset_ids', m.get('candidate_asset_ids', []))
        binding = m.get('candidate_subarea') or '／'.join(ids)
        basis = m.get('matching_basis') or m.get('selection_basis') or m.get('visual_notes') or m.get('matching_notes') or '按现行候选登记'
        if isinstance(basis, list):
            basis = '；'.join(basis)
        rows.append((m, binding, basis))
    text = '# 用户母版自动适配编号总表\n\n'
    text += f'当前登记的{len(rows)}张用户媒体／现行修图均可反查稳定资产编号；同类候选保留各自媒体键，不新增C／S／P号。自动适配的是制作归属，不是对未知身份的事实确认，也不等于全视角、空间或动作验收。\n\n'
    text += '来源：[母版登记](母版登记.json)。后续宁清晏／殷照夜仍保留，未强加前三集出场。普通组五张已按体量与衣型分配到不同稳定实例，其余五人独立设计；分配不证明身高尺度、雨态与动作通过。\n\n'
    text += '| 媒体编号／文件 | 自动适配资产／子区 | 用途与依据 | 尚缺核验 |\n|---|---|---|---|\n'
    for m, binding, basis in rows:
        relative = Path(m['path']).relative_to('资产/媒体').as_posix()
        missing = '；'.join(m.get('unverified', [])) or '见原登记'
        if m.get('scope') == 'ordinary_assassin_group':
            binding = 'S01／' + m['instance_id']
            basis = m['instance_assignment']['basis']
        text += f"| [{m['id']}]({relative}) | {binding} | {basis} | {missing} |\n"
    text += '\n## 实际生成的派生资产\n\n'
    for m in data['generated_assets']:
        relative = Path(m['path']).relative_to('资产/媒体').as_posix()
        state = '已选用本任务' if m['status'] == 'selected' else '候选'
        text += f"- [{m['task_id']}]({relative})：{'／'.join(m['asset_ids'])}；{state}。{m['review']['summary']} 后续范围：{'；'.join(m['review']['remaining'])}。\n"
        for item in m.get('supporting_assets', []):
            link = Path(item['path']).relative_to('资产/媒体').as_posix()
            text += f"  - [{item['id']}]({link}) 个体派生候选：{item['review']['summary']} 待核：{'；'.join(item['review']['remaining'])}；不另抵扣任务。\n"
    return text


def render_required_coverage(data):
    """逐项列出必要包要求，包括尚无媒体登记的空槽；不从近似视角推断完成。"""
    tasks = {t['id']: t for t in data['tasks']}
    packages = {p['id']: p for p in data.get('necessary_asset_packages', [])}

    def cell(key, package=False):
        row = (packages if package else tasks).get(key)
        if not row:
            return '缺：未登记交付'
        path = row.get('path') if package else row.get('actual_file')
        if not path:
            return '缺：未登记交付'
        status = row.get('status') if package else row.get('media_status')
        label = '已选静态' if status == 'selected' else '候选待验'
        link = '../../媒体/' + Path(path).relative_to('资产/媒体').as_posix()
        return f'[{label}]({link})'

    text = '\n## 主要人物与重点场景必要项覆盖\n\n'
    text += '按[必要资产设计](必要资产与分镜设计.md)逐项核对以下主要人物和六个重点场景，不因没有登记行就略过缺口。已选静态只说明单项验收；侧脸不抵严格侧面全身，四分之三不抵正侧背，日景不抵同空间夜景。此表不替代其他具名配角、遮面群体与逐镜状态的要求。\n\n'
    text += '| 人物 | 身份肖像 | 基础正面全身 | 严格侧面全身 | 基础背面全身 | 表情九宫格 | 轻仙侠换装边界 |\n|---|---|---|---|---|---|---|\n'
    people = [('C01', '顾砚／陈渡同身体'), ('C03', '韩青'), ('C04', '顾伯'),
              ('C16', '杜长庚'), ('C17', '石照川'), ('C20', '崔望野'),
              ('C23', '许照邻'), ('C06', '黄祁')]
    for cid, name in people:
        expression = cell(cid + '-EXPRESSION-GRID', True)
        if cid == 'C01':
            expression = '原顾：' + expression + '；今顾：' + cell('C02-EXPRESSION-GRID', True)
        wardrobe = ('男主现行母版对应；室内干衣另按镜头绑定' if cid == 'C01' else
                    '正：' + cell(cid + '-XIANXIA', True) + '；侧：' + cell(cid + '-XIANXIA-SIDE', True) +
                    '；背：' + cell(cid + '-XIANXIA-BACK', True) + '；整套一致性另验，不与基础视图拼包')
        values = [cid + ' ' + name, cell('MB-' + cid + '-FACE'), cell('MB-' + cid + '-FULL'),
                  cell(cid + '-FULL-SIDE', True), cell('MB-' + cid + '-FULL-BACK'), expression, wardrobe]
        text += '| ' + ' | '.join(values) + ' |\n'
    text += '\n| 场景／子区 | 主视角 | 同空间反打 | 同空间侧向 | 未完成的整体核验 |\n|---|---|---|---|---|\n'
    scenes = [('S01', '林道', 'S01-REVERSE', 'S01-SIDE', '完整车马包络、八马六人及两波站位'),
              ('S02', '南街汤摊', 'S02-REVERSE', 'S02-SIDE', '同机位去人和人物姿态不抵反打／侧向；街面扶行与四骑通道'),
              ('S03-COURT', '顾府外院', 'S03-COURT-REVERSE', 'S03-COURT-SIDE', '正门、西厢外四马、五床与通行邻接'),
              ('S03-HALL', '前厅', 'S03-HALL-REVERSE', 'S03-HALL-SIDE', '大案、小案、照护位及东西开口对应；首夜光态'),
              ('S04', '书房', 'S04-REVERSE', 'S04-SIDE', '案窗门、柜、镜杯灯和碎杯落区对应'),
              ('S05', '卧房', 'S05-REVERSE', 'S05-SIDE', '床门关系、左肩照护与起身落脚；日夜光态')]
    for sid, name, reverse, side, pending in scenes:
        text += '| ' + ' | '.join([sid + ' ' + name, cell('MB-ENV-' + sid), cell(reverse, True),
                                  cell(side, True), pending]) + ' |\n'
    text += '\n空槽表示尚无绑定到该必要项的有效交付；不推断磁盘上任意相似图片已经满足要求。新媒体须按用途登记后再更新覆盖，建筑参考和单机位表演末态不能自动填入其他空间视角。\n'
    return text


def render_missing(data):
    tasks = [t for t in data['tasks'] if t['release_scope'] == 'current_first_three']
    selected = [t for t in tasks if t['media_status'] == 'selected']
    candidates = [t for t in tasks if t['media_status'] == 'generated_candidate']
    text = '# 前三集实际资产缺口\n\n先看[视频平台制作分工](视频平台制作分工.md)。以下是完整任务登记，未完成数不等于必须生成的独立图片数；按镜头补核心参考，其余按需或用提示词执行，实际验收仍保留。\n\n'
    text += f'由生产任务和实际媒体登记生成：前三集{len(tasks)}项，已选{len(selected)}项，已生成待复核{len(candidates)}项，未生成／未完成{len(tasks)-len(selected)-len(candidates)}项。后续专用任务不混入此数。\n\n'
    text += '[母版自动适配编号](../../媒体/母版自动适配编号.md) · [逐镜分镜](前三集节奏与分镜.md) · [剧情动作关系](../../../剧集/前三集重写与生产交接-v1.9.md)\n\n'
    text += '## 按制作路线核对缺口\n\n'
    text += '| 路线 | 已选任务 | 候选任务 | 未完成任务 | 执行含义 |\n|---|---|---|---|---|\n'
    routes = [('core', '核心参考'), ('shot', '逐镜派生'), ('prompt', '提示词实现'), ('execution', '执行与验证')]
    actual_routes = {t['production_route'] for t in tasks}
    routes += [(r, r) for r in sorted(actual_routes - {r for r, _ in routes})]
    for route, label in routes:
        subset = [t for t in tasks if t['production_route'] == route]
        if not subset:
            continue
        done = sum(t['media_status'] == 'selected' for t in subset)
        review = sum(t['media_status'] == 'generated_candidate' for t in subset)
        text += f'| {label} | {done} | {review} | {len(subset)-done-review} | 按登记验收；路线不代表已生成或自动通过 |\n'
    text += '\n优先补尚缺的核心参考；逐镜派生随实际镜头执行，提示词与后期项仍需结果核验。不得按未完成行数机械生成同等数量的独立图片。\n\n'
    core_missing = [t for t in tasks if t['production_route'] == 'core' and t['media_status'] != 'selected']
    text += '### 尚未通过的核心参考\n\n'
    for t in core_missing:
        text += f"- {t['id']}：{t['name']}；{'、'.join(t['release_episode_ids'])}；{'已有候选，先复核' if t['media_status'] == 'generated_candidate' else '尚缺有效交付'}。\n"
    if not core_missing:
        text += '旧任务范围内核心参考已选；仍须核对下列必要包及逐镜输入。\n'
    text += render_required_coverage(data)
    packages = data.get('necessary_asset_packages', [])
    accepted = sum(p['status'] == 'selected' for p in packages)
    text += f'\n## 新增必要包与分镜候选\n\n必要包登记共{len(packages)}项，其中已选{accepted}项、候选{len(packages)-accepted}项。此数独立于旧任务，不相加为完成率；已选只覆盖各项静态验收范围，不等于整个人物包或镜头通过。\n\n'
    text += '| 实际文件 | 类型 | 状态 | 验收范围 | 尚缺核对 |\n|---|---|---|---|---|\n'
    for p in packages:
        link = '../../媒体/' + Path(p['path']).relative_to('资产/媒体').as_posix()
        scope = p['review'].get('scope', '待核')
        pending = '；'.join(p['review'].get('remaining', [])) or '后续镜头与动态另验'
        text += f"| [{p['id']}]({link}) | {p['kind']} | {'已选静态范围' if p['status'] == 'selected' else '候选'} | {scope} | {pending} |\n"
    text += '\n未登记项目仍可能是缺口，不能因本表没有一行就视为完成。人物三视图和表情、场景主视角／反打／侧向的要求见[必要资产与分镜设计](必要资产与分镜设计.md)；镜头候选不能代替未完成的动态接触、对白、声音及逐镜占时验证。\n\n## 旧任务逐项验收缺口\n\n'
    text += '通过次序：身份与衣装 → 侧背与剧情状态；空间拓扑 → 空景与光态；道具底形 → 字版与流转；最后做人景、动作、声音和逐镜占时。五镜技术预演与书房美术候选另见三维预演登记，不能抵扣未验收任务。\n\n'
    text += '| 未完成任务 | 名称 | 发行集 | 当前状态 | 尚缺前置 | 验收要求 |\n|---|---|---|---|---|---|\n'
    for t in tasks:
        if t['media_status'] == 'selected':
            continue
        status = '已生成候选，待复核' if t['media_status'] == 'generated_candidate' else '未生成／未完成'
        text += f"| {t['id']} | {t['name']} | {'、'.join(t['release_episode_ids'])} | {status} | {'、'.join(t['unresolved_dependencies']) or '无未选前置；按验收要求执行'} | {t['acceptance']} |\n"
    return text
