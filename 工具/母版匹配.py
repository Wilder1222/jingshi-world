"""从现行媒体登记生成编号总览及任务缺口；不把匹配当作选版。"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


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


def render_missing(data):
    tasks = [t for t in data['tasks'] if t['release_scope'] == 'current_first_three']
    selected = [t for t in tasks if t['media_status'] == 'selected']
    candidates = [t for t in tasks if t['media_status'] == 'generated_candidate']
    text = '# 前三集实际资产缺口\n\n'
    text += f'由生产任务和实际媒体登记生成：前三集{len(tasks)}项，已选{len(selected)}项，已生成待复核{len(candidates)}项，未生成／未完成{len(tasks)-len(selected)-len(candidates)}项。后续专用任务不混入此数。\n\n'
    text += '[母版自动适配编号](../../媒体/母版自动适配编号.md) · [逐镜分镜](前三集节奏与分镜.md) · [剧情动作关系](../../../剧集/前三集重写与生产交接-v1.9.md)\n\n'
    text += '通过次序：身份与衣装 → 侧背与剧情状态；空间拓扑 → 空景与光态；道具底形 → 字版与流转；最后做人景、动作、声音和逐镜占时。五镜技术预演与书房美术候选另见三维预演登记，不能抵扣未验收任务。\n\n'
    text += '| 未完成任务 | 名称 | 发行集 | 当前状态 | 尚缺前置 | 验收要求 |\n|---|---|---|---|---|---|\n'
    for t in tasks:
        if t['media_status'] == 'selected':
            continue
        status = '已生成候选，待复核' if t['media_status'] == 'generated_candidate' else '未生成／未完成'
        text += f"| {t['id']} | {t['name']} | {'、'.join(t['release_episode_ids'])} | {status} | {'、'.join(t['unresolved_dependencies']) or '无未选前置；按验收要求执行'} | {t['acceptance']} |\n"
    return text
