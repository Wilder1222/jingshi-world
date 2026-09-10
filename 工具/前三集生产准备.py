"""从作者维护的任务源生成 MJ 探索交接包；不调用生成服务、不宣布选版。"""
import argparse
import sys
import csv
import hashlib
import io
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from 母版匹配 import load_generated, render_mapping, render_missing

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / '资产/生产准备/前三集-v1.9'
VETS = ['C03', 'C16', 'C17', 'C20', 'C23']
CORE = {'C01', 'C03', 'C04', 'C06', 'C12', 'C14', 'C16'}
ASSASSINS = {'C06', 'C07', 'C57', 'C58', 'C59'}
FIRST_CAST = ({f'C{i:02}' for i in range(1, 24)} | {'C57', 'C58', 'C59', 'C60'}) - {'C18', 'C19', 'C21', 'C22'}
FACE_CAST = FIRST_CAST - {'C02', 'C05', 'C60'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def link(path):
    return os.path.relpath(ROOT / path, PACK).replace('\\', '/')


def load_masters():
    """读取已选身份／建筑视觉母版；视觉选用不等于空间验收。"""
    masters = read(ROOT / '资产/媒体/母版登记.json')['masters']
    characters = {c['id']: c for c in read(ROOT / '索引/数据/characters.json')}
    locations = {s['id']: s for s in read(ROOT / '索引/数据/locations.json')}
    seen, assets, task_ids = set(), set(), set()
    instance_masters = {p['id']: p.get('master_id') for p in read(PACK / '补充任务源.json')['first_wave']}
    assigned_instances = set()
    for master in masters:
        key = master['id']
        if key in seen or master['status'] != 'selected' or master['scope'] not in ('portrait_identity', 'architecture_visual', 'ordinary_assassin_group'):
            raise ValueError('母版编号重复或选用范围错误')
        seen.add(key)
        path = (ROOT / master['path']).resolve()
        if not path.is_relative_to((ROOT / '资产/媒体').resolve()) or not path.is_file():
            raise ValueError('母版文件缺失或越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != master['sha256']:
            raise ValueError('母版文件校验不符')
        if master.get('source_kind') == 'user_attachment_edited':
            original = (ROOT / master['original_path']).resolve()
            if not original.is_relative_to((ROOT / '参考').resolve()) or not original.is_file():
                raise ValueError('修图缺原始用户参考或路径越界')
            if hashlib.sha256(original.read_bytes()).hexdigest() != master['original_sha256']:
                raise ValueError('修图原始参考校验不符')
            if master['sha256'] == master['original_sha256']:
                raise ValueError('修图产物不能冒充未修改原图')
            generation = master.get('generation', {})
            if generation.get('tool') != 'image_gen.imagegen' or not generation.get('prompts') or not all(generation['prompts']):
                raise ValueError('修图缺生成工具或提示词记录')
            if master.get('style_review', {}).get('status') != 'passed_visual_review':
                raise ValueError('修图母版尚未完成视觉复核')
        if not master['asset_ids'] or not master['selection_basis']:
            raise ValueError('母版缺角色或选用依据')
        if master['scope'] == 'ordinary_assassin_group':
            instance = master.get('instance_id')
            if master['asset_ids'] != ['S01'] or master.get('group_key') != 'S01-W1':
                raise ValueError('普通刺客组不能冒充具名角色或已分配实例')
            if instance not in instance_masters or instance_masters[instance] != key or instance in assigned_instances:
                raise ValueError('普通刺客实例重复或与源映射不符')
            assigned_instances.add(instance)
            if not master.get('instance_assignment', {}).get('basis'):
                raise ValueError('普通刺客自动分配缺依据')
            if master['task_ids'] or master['reference_task_ids'] != ['POST-WAVES', 'MB-' + instance] or not master.get('unverified'):
                raise ValueError('普通刺客组仅可供波次核对，不完成全身实例任务')
            if master.get('framing') not in ('full_body', 'feet_cropped'):
                raise ValueError('普通刺客须记录完整裁幅')
            continue
        if master['scope'] == 'architecture_visual':
            if master['task_ids'] or master.get('spatial_status') != 'not_verified':
                raise ValueError('建筑视觉母版不能冒充空间或光态任务验收')
            for sid in master['asset_ids']:
                if sid not in locations or key not in locations[sid].get('architecture_master_ids', []):
                    raise ValueError('建筑母版与场景登记不一致')
            if not master.get('visual_slot') or not master.get('unverified'):
                raise ValueError('建筑母版缺用途或未核验范围')
            continue
        for cid in master['asset_ids']:
            if cid in assets or cid not in characters:
                raise ValueError('肖像角色重复或不存在')
            assets.add(cid)
            if characters[cid].get('portrait_master_id') != key or characters[cid]['visual_key'] != master['visual_key']:
                raise ValueError('角色与肖像母版绑定不一致')
        for task_id in master['task_ids']:
            if task_id in task_ids:
                raise ValueError('任务绑定多个肖像母版')
            task_ids.add(task_id)
    shared = [m for m in masters if set(m['asset_ids']) & {'C01', 'C02'}]
    if shared and (len(shared) != 1 or set(shared[0]['asset_ids']) != {'C01', 'C02'}):
        raise ValueError('C01/C02必须共用同一母版')
    return masters


def bind_masters(tasks, masters):
    by_id = {t['id']: t for t in tasks}
    selected = {}
    for master in masters:
        for tid in master['task_ids']:
            if tid not in by_id or tid != 'MB-' + master['asset_ids'][0] + '-FACE':
                raise ValueError('肖像只能完成对应身份脸任务')
            selected[tid] = master
    def ancestors(tid, seen=None, images_only=False):
        seen = set() if seen is None else seen
        for dep in by_id[tid]['depends_on']:
            if images_only and by_id[dep]['method'] != 'MJ':
                continue
            if dep not in seen:
                seen.add(dep)
                ancestors(dep, seen, images_only)
        return seen
    for m in masters:
        if m['scope'] == 'architecture_visual':
            for tid in m['reference_task_ids']:
                if tid not in by_id or (by_id[tid]['category'] not in ('空间', '空间光态') and tid != 'POST-PLAN-COURT'):
                    raise ValueError('建筑引用任务不存在或不属于空间工序')
                if not set(m['asset_ids']) & set(by_id[tid]['asset_ids']):
                    raise ValueError('建筑引用跨越登记场景范围')
    for t in tasks:
        master = selected.get(t['id'])
        t['selected_master_id'] = master['id'] if master else None
        if master:
            t.update(status='selected_external_master', media_status='selected', actual_file=master['path'])
        t['input_references'] = [dict(master_id=m['id'], path=m['path'], sha256=m['sha256'], purpose='portrait_identity')
                                 for tid, m in sorted(selected.items()) if tid in ancestors(t['id'])]
        lineage = {t['id']} | ancestors(t['id'], images_only=True)
        t['input_references'] += [dict(master_id=m['id'], path=m['path'], sha256=m['sha256'],
                                      purpose='architecture_visual', visual_slot=m['visual_slot'],
                                      constraints=m['derivation_rule'])
                                  for m in masters if m['scope'] == 'architecture_visual'
                                  and set(m['reference_task_ids']) & lineage]
        t['input_references'] += [dict(master_id=m['id'], path=m['path'], sha256=m['sha256'],
                                          purpose='ordinary_assassin_group', constraints=m['derivation_rule'])
                                      for m in masters if m['scope'] == 'ordinary_assassin_group' and t['id'] in m['reference_task_ids']]
        t['unresolved_dependencies'] = [dep for dep in t['depends_on'] if dep not in selected]
        if t['depends_on'] and not t['unresolved_dependencies'] and not master:
            t['status'] = 'ready_for_exploration'
        if t['input_references']:
            t['reference_slot'] = 'Use each registered image only for its stated purpose; unresolved clothing/space parents remain required.'


def load_pending_masters():
    registry = read(ROOT / '资产/媒体/母版登记.json')
    candidates = registry.get('pending_masters', [])
    seen = {m['id'] for m in registry['masters']}
    for m in candidates:
        if m['id'] in seen or m['status'] != 'pending_identity_confirmation' or m['scope'] != 'masked_portrait_reference':
            raise ValueError('蒙面候选编号或状态不合法')
        seen.add(m['id'])
        if m['task_ids'] or m['reference_task_ids'] or not m['candidate_asset_ids'] or not set(m['candidate_asset_ids']) <= ASSASSINS:
            raise ValueError('蒙面候选不能确认身份、分配第一波实例或自动执行任务')
        if not m.get('matching_basis') or not m.get('unverified'):
            raise ValueError('蒙面候选缺匹配依据或核对范围')
        path = (ROOT / m['path']).resolve()
        if not path.is_relative_to((ROOT / '资产/媒体/待核对').resolve()) or not path.is_file():
            raise ValueError('蒙面候选文件缺失或路径越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != m['sha256']:
            raise ValueError('蒙面候选文件校验不符')
    return candidates


def load_matched_references():
    registry = read(ROOT / '资产/媒体/母版登记.json')
    refs = registry.get('matched_references', [])
    valid = {c['id'] for c in read(ROOT / '索引/数据/characters.json')} | {'P19'} | {s['id'] for s in read(ROOT / '索引/数据/locations.json')}
    seen = {m['id'] for m in registry['masters'] + registry.get('pending_masters', [])}
    for m in refs:
        if m['id'] in seen or m['scope'] != 'matched_asset_reference':
            raise ValueError('匹配参考编号重复或范围错误')
        seen.add(m['id'])
        if not m['asset_ids'] or not set(m['asset_ids']) <= valid:
            raise ValueError('匹配参考资产不存在')
        if m['confidence'] not in ('high', 'medium', 'low') or m['status'] != ('matched_reference' if m['confidence'] == 'high' else 'candidate_reference'):
            raise ValueError('匹配参考置信度与状态不一致')
        if m['task_ids'] or m['reference_task_ids'] or not m['matching_basis'] or not m['unverified']:
            raise ValueError('匹配参考不能自动选版或缺少核对依据')
        path = (ROOT / m['path']).resolve()
        if not path.is_relative_to((ROOT / '资产/媒体/资产匹配').resolve()) or not path.is_file():
            raise ValueError('匹配参考缺失或越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != m['sha256']:
            raise ValueError('匹配参考校验不符')
        if m.get('source_kind') == 'user_attachment_edited':
            original = (ROOT / m['original_path']).resolve()
            if not original.is_relative_to((ROOT / '参考/用户媒体').resolve()) or not original.is_file():
                raise ValueError('匹配修图原始参考缺失或越界')
            if hashlib.sha256(original.read_bytes()).hexdigest() != m['original_sha256'] or m['original_sha256'] == m['sha256']:
                raise ValueError('匹配修图原始参考校验不符')
            if m.get('generation', {}).get('tool') != 'image_gen.imagegen' or not m['generation'].get('prompts') or m.get('style_review', {}).get('status') != 'passed_visual_review':
                raise ValueError('匹配修图缺执行记录或视觉复核')

    return refs


def validate(data):
    if data['selected_masters'] != load_masters():
        raise ValueError('生产母版与选用源登记不一致')
    if data['pending_master_candidates'] != load_pending_masters():
        raise ValueError('蒙面候选与源登记不一致')
    if data['matched_asset_references'] != load_matched_references():
        raise ValueError('匹配参考与源登记不一致')
    if data['generated_assets'] != read(ROOT / '资产/媒体/母版登记.json').get('generated_assets', []):
        raise ValueError('生成候选与源登记不一致')
    tasks = data['tasks']
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError('重复任务编号')
    by_id = {t['id']: t for t in tasks}
    release = data['release_plan']
    if release['fps'] != {'numerator': 24, 'denominator': 1} or release['duration_verified']:
        raise ValueError('发行时基须为待验证24fps草案')
    deliveries = release['episodes']
    if [e['id'] for e in deliveries] != ['GJ-R01', 'GJ-R02', 'GJ-R03'] or [e['duration_seconds'] for e in deliveries] != [180, 195, 180]:
        raise ValueError('前三发行集须180／195／180秒')
    expected_scenes = [[f'GJ-EP01-SC01'], [f'GJ-EP01-SC{i:02}' for i in range(2, 7)], [f'GJ-EP02-SC{i:02}' for i in range(1, 6)]]
    shot_ids = set()
    for delivery, expected in zip(deliveries, expected_scenes):
        if delivery['scene_ids'] != expected:
            raise ValueError('发行场次映射失配或后续门口戏提前')
        if any(data['scene_release_map'].get(sid) != delivery['id'] for sid in expected):
            raise ValueError('场次源的发行映射失配')
        if list(dict.fromkeys(s['scene_id'] for s in delivery['shots'])) != expected or [expected.index(s['scene_id']) for s in delivery['shots'] if s['scene_id'] in expected] != sorted(expected.index(s['scene_id']) for s in delivery['shots'] if s['scene_id'] in expected):
            raise ValueError('分镜场次顺序倒置')
        cursor = 0
        totals = {key: 0 for key in expected}
        previous = []
        for shot in delivery['shots']:
            if shot['id'] in shot_ids or shot['scene_id'] not in totals:
                raise ValueError('分镜编号或场次失配')
            shot_ids.add(shot['id'])
            if not all(type(shot[k]) is int for k in ('start_frame', 'end_frame')) or shot['start_frame'] != cursor or shot['end_frame'] <= cursor:
                raise ValueError('分镜帧窗重叠、空隙或非整数')
            if shot['depends_on'] != previous or shot['media_status'] != 'not_generated':
                raise ValueError('分镜相邻依赖或媒体状态不实')
            if not all(shot.get(k) for k in ('beat', 'camera', 'action', 'sound', 'end_state')):
                raise ValueError('分镜缺因果、运镜或声音')
            if not all(shot.get(k) for k in ('performance', 'blocking_continuity', 'cut_cue')):
                raise ValueError('前三集逐镜表演、接续或切点缺失')
            totals[shot['scene_id']] += shot['end_frame'] - cursor
            cursor = shot['end_frame']
            previous = [shot['id']]
        if cursor != delivery['duration_seconds'] * 24 or any(total != data['scene_budgets'][sid] * 24 for sid, total in totals.items()):
            raise ValueError('分镜与场次／发行时长不一致')
    if 'POST-RHYTHM3' not in by_id:
        raise ValueError('缺前三发行集节奏验收')
    for task in tasks:
        expected = [e['id'] for e in deliveries if set(task['scene_ids']) & set(e['scene_ids'])]
        if task['release_episode_ids'] != expected:
            raise ValueError('任务发行关联失配')
        if task['release_scope'] != ('current_first_three' if expected else 'followup_reserve'):
            raise ValueError('后续任务未隔离')
    expected_instances = [f'S01-W1-{i:02}' for i in range(1,11)]
    if [p['id'] for p in data.get('first_wave_instances',[])] != expected_instances:
        raise ValueError('第一波必须十个独立遮面实例')
    waves = data.get('assault_waves',[])
    if len(waves) != 2 or [w['count'] for w in waves] != [10,5] or waves[0].get('instance_ids') != expected_instances or set(waves[1].get('character_ids',[])) != ASSASSINS:
        raise ValueError('两波刺客须10＋5且第二波沿现有五人')
    wave_tasks=[t for t in tasks if t['category']=='第一波遮面实例']
    if len(wave_tasks)!=10 or {t['id'] for t in wave_tasks}!={'MB-'+i for i in expected_instances}:
        raise ValueError('第一波十个实例任务缺失或复用')
    if 'POST-WAVES' not in by_id:
        raise ValueError('缺两波人数交接核对')
    first = sorted(t['first_batch'] for t in tasks if t['first_batch'])
    if first != list(range(1, 21)):
        raise ValueError('首批须为连续20项服装母版')
    expected_first = [f'MB-{cid}-{suffix}' for cid in ('C01','C03','C16','C04','C06')
                      for suffix in ('FULL','FULL-3Q','FULL-BACK','COSTUME-DETAIL')]
    if [t['id'] for t in sorted((t for t in tasks if t['first_batch']), key=lambda t:t['first_batch'])] != expected_first:
        raise ValueError('首批五人服装视角失配，不是五卒合照或肖像批次')
    mystery = [t for t in tasks if t['method'] == 'MJ' and 'C60' in t['asset_ids']]
    if len(mystery) != 1 or mystery[0]['id'] != 'MB-C60-SILHOUETTE':
        raise ValueError('C60仅允许遮脸轮廓任务，不能自动制作身份脸')
    seen, active = set(), set()

    def visit(key):
        if key not in by_id:
            raise ValueError('缺前置任务：' + key)
        if key in active:
            raise ValueError('循环依赖：' + key)
        if key in seen:
            return
        active.add(key)
        for dep in by_id[key]['depends_on']:
            visit(dep)
        active.remove(key)
        seen.add(key)

    for t in tasks:
        visit(t['id'])
        master = next((m for m in data['selected_masters'] if t['id'] in m['task_ids']), None)
        candidate = next((m for m in data['generated_assets'] if t['id'] == m['task_id']), None)
        if (t['actual_file'], t['media_status'], t['selected_master_id']) != (
                master['path'] if master else candidate['path'] if candidate else None,
                'selected' if master else candidate['status'] if candidate else 'not_generated', master['id'] if master else candidate['id'] if candidate and candidate['status'] == 'selected' else None):
            raise ValueError('任务媒体必须对应已登记母版；不能冒充实际媒体')
        if not t['scene_ids'] or not set(t['scene_ids']) <= set(data['scene_ids']):
            raise ValueError('场次失配：' + t['id'])
        if not t['acceptance'] or not t['source_paths']:
            raise ValueError('缺验收或来源：' + t['id'])
        if t['method'] == 'MJ':
            if set(t['asset_ids']) & {'C05', 'P05', 'P13'}:
                raise ValueError('越界可视资产：' + t['id'])
            if not t['prompt_en'] or any(x in t['projection'] for x in ('--oref', '--cref', '--q ', '--hd', '::')):
                raise ValueError('提示词或模型参数不合规')
    faces = {t['asset_ids'][0] for t in tasks if t['id'].endswith('-FACE')}
    if faces != FACE_CAST:
        raise ValueError('必须20张独立身份脸，C01/C02同脸、C05仅声、C60遮脸')
    coverage = {a for t in tasks if t['method'] == 'MJ' for a in t['asset_ids']}
    if not set(data['visible_asset_ids']) <= coverage:
        raise ValueError('可见资产未覆盖：' + str(set(data['visible_asset_ids']) - coverage))


def validate_visual_source(cfg):
    fields = ('studio_background_en', 'portrait_light_en', 'grooming_en',
              'identity_en', 'hair_en', 'costume_en', 'body_proportion_en', 'checks')
    ids = [c['id'] for c in cfg['characters']]
    if len(ids) != len(set(ids)):
        raise ValueError('重复人物视觉源编号')
    for c in cfg['characters']:
        if not all(isinstance(c.get(k), str) and c[k].strip() for k in fields):
            raise ValueError(c['id'] + '：缺人物摄影或衣装字段')
    if not cfg.get('portrait_direction', {}).get('source_path'):
        raise ValueError('缺人物服装系统来源')


def build_data():
    cfg = read(PACK / '视觉任务源.json')
    validate_visual_source(cfg)
    architecture = cfg['architecture_direction']
    extra = read(PACK / '补充任务源.json')
    release = read(ROOT / '索引/数据/发行前三集.json')
    eps = read(ROOT / '索引/数据/episodes.json')[:3]
    registry = {}
    for name in ('characters', 'locations', 'props'):
        for item in read(ROOT / f'索引/数据/{name}.json'):
            registry[item['id']] = item
    scenes = [s for e in eps for s in e['scenes']]
    char = {c['id']: c for c in cfg['characters']}
    priority = cfg['costume_priority']
    first_wave = extra['first_wave']
    gear = {g['id']: g for g in extra['veteran_gear']}
    tasks = []

    def add(key, title, category, assets, body='', ratio='4:3', deps=(), first=0,
            checks='', scene_ids=None, phase='B', method='MJ'):
        if method == 'MJ' and category in ('空间', '空间光态') and set(assets) & set(architecture['scope_asset_ids']):
            body += ' ' + architecture['family_en']
            checks += ' ' + architecture['checks']
        used = scene_ids or [s['id'] for s in scenes if set(assets) &
                                set(s['character_ids'] + (s['voice_only_ids'] if method != 'MJ' else []) + s['location_ids'] + s['prop_ids'])]
        paths = sorted({registry[a]['path'] for a in assets if a in registry} |
                       {e['path'] for e in eps if any(s['id'] in used for s in e['scenes'])} |
                       {'剧集/前三集重写与生产交接-v1.9.md', '资产/美术风格与造型总则.md', '参考/第一集视觉讨论-采用边界.md'})
        if any(a.startswith('C') for a in assets):
            paths.append(cfg['portrait_direction']['source_path'])
        # S03-W/S06-K 为现有场景子区，源登记不一定独列。
        for a in assets:
            if a not in registry and a.split('-')[0] in registry:
                paths.append(registry[a.split('-')[0]]['path'])
        tail = f'--ar {ratio} --v 8.2 --raw --s 75 --c 0'
        tasks.append(dict(id=key, name=title, category=category, method=method,
                          phase='A' if first else phase, first_batch=first,
                          asset_ids=assets, scene_ids=used, source_paths=sorted(set(paths)),
                          depends_on=list(deps), acceptance=checks, prompt_en=body,
                          provider_tail=tail if method == 'MJ' else '',
                          projection=f'{body} {tail}' if method == 'MJ' else '',
                          manual_preflight_required=True,
                          status='awaiting_parent_selection' if deps else 'ready_for_exploration' if method == 'MJ' else 'planned',
                          media_status='not_generated', actual_file=None,
                          planned_filename=f'{key}__v01__candidate.png' if method == 'MJ' else f'{key}__v01__working',
                          input_references=[], reference_slot='executor: selected parent master, rights checked' if deps else 'none'))

    def actor(c, view, costume=None, background=None, framing='person'):
        subject = f"Single fictional Chinese man, age {c['age']}, {c['identity_en']}. {c['hair_en']}. "
        grooming = c['grooming_en'] + '. '
        if framing == 'back':
            subject = f"Rear view of the same selected costumed person. {c['hair_en']}. "
            grooming = ''
        elif framing == 'detail':
            subject = 'Detail crop of the same selected costume. '
            grooming = ''
        proportions = c['body_proportion_en'] + ' ' if 'full-length' in view.lower() or framing == 'back' else ''
        return (subject + f"{costume or c['costume_en']}. {view}. "
                + grooming + proportions + f"{background or c['studio_background_en']}. {c['portrait_light_en']}. "
                'One subject, one frame. ' + cfg['style_en'])

    for c in cfg['characters']:
        cid = c['id']
        aids = [cid, *c['shares']]
        add(f'MB-{cid}-FACE', c['name'] + '｜正脸身份', '身份', aids,
            actor(c, 'Front-facing head-and-shoulders identity portrait, full topknot included with headroom, neutral relaxed expression, unobstructed face, natural catchlights'),
            '3:4', first=c['first_batch'], checks=c['checks'], phase=c['tier'])
        add(f'MB-{cid}-FULL', c['name'] + '｜全身干衣', '衣装', aids,
            actor(c, 'Front-facing full-length standing costume study, both hands relaxed and visible, feet included'),
            '2:3', deps=[f'MB-{cid}-FACE'], first=priority.index(cid)*4+1 if cid in priority else 0,
            checks=c['checks'] + '；衣型、体量和脸沿已选母版；干衣无新伤；双手自然垂于身侧可见、不背手', phase=c['tier'])
        if cid in priority:
            for offset, suffix, label, view, ratio in [
                (2, 'FULL-3Q', '四分之三全身', 'Three-quarter full-length standing view, relaxed arms at the sides, both hands and feet visible, layered lapels and waist sash thickness readable', '2:3'),
                (3, 'FULL-BACK', '背面全身', 'Straight rear full-length standing view, head facing away, both arms relaxed at the sides, feet visible, rear hair binding and the back seam and split hem clearly readable', '2:3'),
                (4, 'COSTUME-DETAIL', '领襟腰封织物细节', 'Single continuous close crop from the lower neck to the waist, visible collar edging, woven tonal pattern and sash hardware at realistic scale, no collage or diagram', '4:3')]:
                add(f'MB-{cid}-{suffix}', c['name'] + '｜' + label, '服装结构', aids,
                    actor(c, view, framing='back' if suffix == 'FULL-BACK' else 'detail' if suffix == 'COSTUME-DETAIL' else 'person'), ratio, [f'MB-{cid}-FULL'], first=priority.index(cid)*4+offset,
                    checks=c['checks'] + '；同一套已选FULL只改视角或裁幅，不换暗纹、腰封、背部发式；非战斗、不临时加兵器或内甲')
        if cid in CORE:
            for suffix, label, angle in [('PROFILE', '侧脸', 'clean left profile head-and-shoulders portrait'),
                                          ('THREEQUARTER', '四分之三脸', 'three-quarter head-and-shoulders portrait')]:
                add(f'MB-{cid}-{suffix}', c['name'] + '｜' + label, '身份视角', aids,
                    actor(c, angle + ', full topknot included with headroom, neutral relaxed expression'), '3:4', [f'MB-{cid}-FACE'],
                    checks=c['checks'] + '；只改视角，耳鼻下颌与选脸同源', phase=c['tier'])
    for e in cfg['environments']:
        add('MB-ENV-' + e['key'], e['name'], '空间', e['asset_ids'], e['body_en'], e['ratio'],
            first=e['first_batch'], checks=e['checks'])
    for p in cfg['props']:
        add(f"MB-{p['id']}-BASE", p['name'], '道具', [p['id']], p['body_en'], p['ratio'],
            first=p['first_batch'], checks=p['checks'])
    for s in extra['states']:
        add('MB-' + s['key'], s['name'], '衣伤表演状态', s['asset_ids'],
            actor(char[s['owner']], 'Head-and-shoulders performance study' if s['key'] in ('C02-FEAR', 'C02-FOCUS') else 'Single full-length standing costume continuity study', s['costume_en'], s.get('studio_background_en')),
            '3:4' if s['key'] in ('C02-FEAR', 'C02-FOCUS') else '2:3', [s['parent']],
            checks=s['checks'], scene_ids=s['scenes'])
    for cid in VETS:
        c = char[cid]
        g = gear[cid]
        costume = c['costume_en'] + ', ' + g['armor_en']
        used = [s['id'] for s in scenes[:3] if cid in s['character_ids']]
        add(f'MB-{cid}-ARMOR', c['name'] + '｜外劲装内轻甲与佩兵', '轻甲衣装', [cid, 'P20', 'P21'],
            actor(c, 'Full-length neutral standing costume study, equipment at rest, no combat pose', costume + ', ' + g['standing_en']),
            '2:3', [f'MB-{cid}-FULL', 'MB-P20-BASE', 'POST-KIT'],
            checks=c['checks'] + '；' + g['checks'] + '；只在外劲装里面加P20轻皮内甲及本人P21，不改脸、衣色或境界；1-3卸甲，1-4以后用常服FULL', scene_ids=used)
        add(f'MB-{cid}-RAIN', c['name'] + '｜雨湿劲装内甲', '衣伤状态', [cid, 'P20', 'P21'],
            actor(c, 'Full-length standing costume continuity study', costume + ', ' + g['standing_en'] + ', rain-soaked opaque richly woven outer jacket with subtle wet tonal patterns and localized under-armor contour, restrained road mud at hems'),
            '2:3', [f'MB-{cid}-ARMOR'], checks=c['checks'] + '；只改湿度与下摆泥痕，不新增本人伤口；甲不透光，1-3卸下，之后同色精工无甲劲装', scene_ids=used)
    for e in extra['extras']:
        add('MB-' + e['key'], e['name'], '补充近景件', e['asset_ids'], e['body_en'], e['ratio'],
            [e['parent']] if e['parent'] else [], checks=e['checks'], phase=e['phase'])
    for person in first_wave:
        add('MB-' + person['id'], person['name'], '第一波遮面实例', ['S01'],
            'One fictional adult masked assailant, ' + person['body_en'] + ', wearing ' + person['costume_en'] +
            '. Fine tightly woven opaque period travel cloth with restrained dark tonal texture, hood and lower-face wrap concealing identifying facial detail. Full-length neutral standing pose, hands relaxed at the sides, feet visible, ordinary sheathed blade at waist, no combat pose, no insignia. Slightly rain-damp clothing, neutral gray background, diffuse light, one subject and one frame. ' + cfg['style_en'],
            '2:3', checks='仅'+person['id']+'第一波成年遮面实例；按独立体量与服装识别，不生成正脸、不复用第二波或五卒；十人交接退林后不再参战，无新增伤口。',
            scene_ids=person['scene_ids'])
        tasks[-1]['instance_ids'] = [person['id']]
    for m in extra.get('mounts', []):
        c = char[m['rider']]
        add('MB-' + m['rider'] + '-MOUNTED', c['name'] + '｜单人骑乘绑定', '骑乘绑定',
            [m['rider'], 'P19', 'P20', 'P21'],
            f"One fictional Chinese man, age {c['age']}, {c['identity_en']}, {c['hair_en']}, wearing {c['costume_en']}, {gear[m['rider']]['armor_en']}, seated naturally on one ordinary adult riding horse, {m['horse_en']}. {gear[m['rider']]['mounted_en']}. Plain period travel saddle and modest side luggage, full rider and horse visible in a three-quarter side view, all four hooves supported on level ground, quiet neutral pose, diffuse daylight, plain background, one rider and one horse only. " + cfg['style_en'],
            '4:3', [f"MB-{m['rider']}-ARMOR", 'POST-HORSES'],
            checks=f"骑手与已选轻甲母版同脸同衣甲；坐骑必须是已核对{m['horse_id']}，人马体量、鞍接触与行李位置一致；长兵盾弓按本人鞍侧归属，不画马上交锋；只验证骑乘外观，不宣称真实骑术或安全。",
            scene_ids=['GJ-EP01-SC01'])
    for key, label, change, used in [
        ('S02', '雨停初晴街口', 'Bright clear winter morning after rain, natural neutral-white daylight and skylight, damp paving retained, no amber or yellow cast, lamps unlit; preserve the selected street geometry and practical stall placement.', ['GJ-EP02-SC03', 'GJ-EP03-SC02', 'GJ-EP03-SC04']),
        ('S03-COURT', '雨后夜院', 'Replace daylight with restrained warm practical lamps and cool wet-night ambient light; preserve every door and passage.', ['GJ-EP01-SC03', 'GJ-EP01-SC04']),
        ('S03-HALL', '夜间前厅', 'Replace daylight with warm practical lamp light and cool night fill; preserve the fixed large table and door geometry.', ['GJ-EP01-SC03']),
        ('S03-W', '夜间西厢', 'Replace daylight with warm practical lamps and cool night fill; preserve sleeping and luggage zones.', ['GJ-EP01-SC03', 'GJ-EP02-SC02']),
        ('S05', '初晴明亮卧房', architecture['morning_en'] + ' Light enters through existing lattice windows, reflected from pale plaster; preserve the substantial carved bed, doors, furniture and bedside care space.', ['GJ-EP02-SC05'])]:
        e = next(e for e in cfg['environments'] if e['key'] == key)
        add('MB-LIGHT-' + key, label, '空间光态', e['asset_ids'],
            'Edit the selected empty set master. ' + change + ' High-end Chinese costume drama set, readable shadows, empty room or street, one frame.',
            '16:9', ['MB-ENV-' + key], checks='与父母版同一拓扑及机位；只改昼夜光态，不新增建筑', scene_ids=used)
    for key, parent, label, body, used in [
        ('S04-DAY', 'S04', '高门大书房明媚日光材质校验', architecture['daylight_en'] + ' Preserve the massive carved desk, freestanding cabinets and heavy screens, ordinary mirror, low window cabinet, inner door bolt and compact uncluttered action area; incense unlit.', ['GJ-EP01-SC04','GJ-EP01-SC05','GJ-EP01-SC06']),
        ('S01-DAY', 'S01', '宽阔官道日间尺度校验', 'The same extraordinarily broad official road and right-side passing bay between dense bamboo and woodland trees in clear neutral daylight, readable compacted-earth roadbed and drainage edges, no people, horses or vehicles. Preserve the bend, unseen bridge, unbroken route and near-verge local action area.', ['GJ-EP01-SC01']),
        ('S03-COURT-OVERCAST', 'S03-COURT', '外院雨停初晴明媚晨光', architecture['morning_en'] + ' Preserve the tall solid gates, heavy colonnades, winter plum garden margins and clear central route; no people or animals. White plaster remains neutral, carved wood stays readable beneath deep eaves.', ['GJ-EP02-SC05','GJ-EP03-SC01','GJ-EP03-SC02','GJ-EP03-SC03','GJ-EP03-SC04','GJ-EP03-SC05']),
        ('S03-HALL-OVERCAST', 'S03-HALL', '前厅雨停初晴明媚晨光', architecture['morning_en'] + ' Daylight enters from the south courtyard, reflected by pale plaster and stone. Preserve the fixed massive carved table deep inside, large grouped display objects and the smaller portable table by the door; no blown-out white surfaces.', ['GJ-EP02-SC05','GJ-EP03-SC01','GJ-EP03-SC05'])]:
        e = next(e for e in cfg['environments'] if e['key'] == parent)
        add('MB-LIGHT-' + key, label, '空间光态', e['asset_ids'], body, '16:9', ['MB-ENV-' + parent],
            checks='同一空间、同机位只改光态；S04日景仅材质校验，夜戏不改白天；现行晨戏为雨停初晴、湿石仍在，白墙青石保色。OVERCAST沿用兼容编号，不代表当前阴天。金饰不是全局暖滤镜', scene_ids=used)
    add('MB-TEST-C01-BLOOM', '顾砚高光扩散单变量对照（选做）', '风格测试', ['C01', 'C02'],
        'Edit the selected portrait. Preserve identity, pose, clothing, background, framing and color balance. Test only barely visible local optical highlight spill at the existing light-facing edge, keeping eyes and skin texture crisp. No golden halo, dreamy glow, soft-focus face or warm color cast.',
        '3:4', ['MB-C01-FACE'], checks='只比较极弱局部高光扩散有／无；身份基线无新增扩散，不以磨皮、改脸替代柔光，其他参数与母版相同；禁止金色光晕与梦幻泛光，不作任何生产项必需前置', phase='OPTIONAL')
    manual_deps = {
        'PLAN-COURT': [], 'TEXT-DOCS': [f'MB-P{i:02}-BASE' for i in (3, 4, 6, 7, 8, 17)],
        'P09-BROKEN': ['MB-P09-BASE'], 'P06-STATE': ['POST-TEXT-DOCS'],
        'P16-NINE': ['MB-P16-BASE'], 'ENSEMBLE': [f'MB-{c}-ARMOR' for c in VETS],
        'KIT': ['MB-P20-BASE', *['MB-WEAPON-' + key for key in ('BLADE', 'BOW', 'SHIELD')]],
        'FX-COPPER': ['POST-P16-NINE', 'MB-P20-BASE', 'MB-ENV-S01'],
        'INTEGRATION': ['MB-C01-DRY', 'MB-C03-FULL', 'MB-C04-FULL', 'MB-C16-FULL', 'MB-ENV-S04', 'MB-ENV-S03-COURT'],
        'AUDIO': [], 'ACTION': ['POST-PLAN-COURT', 'POST-PLAN-FOREST'],
        'PLAN-FOREST': [], 'HORSES': ['MB-P19-BASE'], 'BACKGROUND': ['POST-PLAN-COURT'],
        'WAVES': [*['MB-'+p['id'] for p in first_wave], 'MB-C06-RAIN-PRE', 'MB-C07-RAIN',
                  'MB-C57-RAIN', 'MB-C58-RAIN', 'MB-C59-RAIN', 'POST-PLAN-FOREST'],
        'RHYTHM3': ['POST-AUDIO', 'POST-ACTION', 'POST-WAVES']}
    for e in extra['manual_tasks']:
        add('POST-' + e['key'], e['name'], '非MJ交接', e['asset_ids'],
            deps=manual_deps[e['key']], checks=e['deliverable'] + ' 验收：' + e['acceptance'], method='POST', scene_ids=e.get('scene_ids'))
    # 光态与群体图的形状依赖不是选漂亮图之后再反改平面图。
    for t in tasks:
        t['release_episode_ids'] = [e['id'] for e in release['episodes'] if set(t['scene_ids']) & set(e['scene_ids'])]
        t['release_scope'] = 'current_first_three' if t['release_episode_ids'] else 'followup_reserve'
        if 'S01' in t['asset_ids'] and t['method'] == 'MJ':
            t['depends_on'].append('POST-PLAN-FOREST')
            t['status'] = 'awaiting_parent_selection'
        if t['category'] == '空间' and any(a.startswith(('S03', 'S04', 'S05', 'S06')) for a in t['asset_ids']):
            t['depends_on'].append('POST-PLAN-COURT')
            t['status'] = 'awaiting_parent_selection'
    visible = sorted({a for s in scenes for a in s['character_ids'] + s['location_ids'] + s['prop_ids']})
    masters = load_masters()
    pending = load_pending_masters()
    matched = load_matched_references()
    bind_masters(tasks, masters)
    generated = load_generated(tasks)
    support_paths = {s['path'] for m in generated for s in m.get('supporting_assets', [])}
    paths = {p for t in tasks for p in t['source_paths']} | {
        '索引/数据/episodes.json', '索引/数据/发行前三集.json', '资产/生产准备/前三集-v1.9/视觉任务源.json',
        '资产/生产准备/前三集-v1.9/补充任务源.json', '工具/前三集生产准备.py',
        '资产/媒体/母版登记.json', '工具/母版匹配.py', '索引/数据/characters.json', '索引/数据/locations.json'} | {m['path'] for m in masters} | {m['original_path'] for m in masters if m.get('original_path')} | {m['path'] for m in pending} | {m['path'] for m in matched} | {m['path'] for m in generated}
    data = dict(format='jingshi-production-working-draft', canonical=False, revision='v1.9',
                baseline_commit=cfg['baseline_commit'], media_status='partially_selected', selected_masters=masters, pending_master_candidates=pending, matched_asset_references=matched, generated_assets=generated,
                model=cfg['model'], manual_preflight_required=True,
                scene_ids=[s['id'] for s in scenes], visible_asset_ids=visible,
                release_plan=release, scene_budgets={s['id']: s['duration_estimate_seconds'] for s in scenes},
                scene_release_map={s['id']: s.get('release_episode_id') for s in scenes},
                first_wave_instances=first_wave, assault_waves=eps[0]['scenes'][0]['assault_waves'],
                retired_tasks=extra.get('retired_tasks', []),
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths | support_paths)}, tasks=tasks)
    validate(data)
    return data


def render_release(release):
    text = '# 前三发行集：节奏、运镜与逐镜交接\n\n'
    text += '创作执行：[用典与侧面烘托](../../../剧集/剧情结构与推进.md#allusion-and-atmosphere)。用典适量、核对出处并符合人物见识与世界内流传依据；季节、天气、环境、场景、人物、穿着、事件与声场等均可推进剧情、表达情绪，变化须有前后状态与因果，落入可见动作、声音入口及镜末变化。沿用车灯晃动、退廊留灯、尝粥后叩门等既有节拍，不强塞诗句或增加重复空景，保持父镜号与时长预算。\n\n'
    text += '继续选材与执行：[短剧情节方法](../../../剧集/剧情结构与推进.md#short-drama-enrichment) · [AIGC镜头执行卡与五组推演](../../../剧集/前三集重写与生产交接-v1.9.md#aigc-story-to-shot)。先定观看目的与入镜状态，再分写人物、摄影机、环境和声音的变化，落到可接续的结果与切点；一个父镜可按需要拆分生成，子镜取用时长仍归原预算。起始图、动作过程、首尾接续与关键接触分别核验，文字计划不代表动态通过。\n\n'
    text += release['planning_unit'] + '\n\n'
    text += '本页由[发行分镜源](../../../索引/数据/发行前三集.json)生成；剧情与动作系统见[制作交接](../../../剧集/前三集重写与生产交接-v1.9.md)。原场次编号不变。24/1 fps仅为剪辑工作假设，16:9，帧窗左闭右开；71镜均为文字计划，未试读、未生成、未进行动作安全验收。片名与尾签画内叠加且已经计时，不另加片头片尾或上一集回顾。\n\n'
    text += '相邻切镜优先接动作完成或视线落点；跨场省略明确保留前后状态。林道以车旁同侧轴线为基准，书房以案—窗—门局部三角为基准；具体焦段是视角意向，机位尺寸与最终格式待母版和预演复核。\n'
    def stamp(frame):
        seconds, ff = divmod(frame, 24)
        mm, ss = divmod(seconds, 60)
        return f'{mm:02}:{ss:02}:{ff:02}'
    for ep in release['episodes']:
        text += f"\n## {ep['id']}《{ep['name']}》｜{ep['duration_seconds']}秒\n\n"
        turns = '；'.join(item.rstrip('。；') for item in ep['reversals']) + '。'
        text += f"主问题：{ep['story_question']}\n\n开头钩子：{ep['opening_hook']}\n\n反转：{turns}\n\n结尾钩子：{ep['ending_hook']}\n\n"
        text += '| 镜号／场次 | 时间码／帧窗 | 叙事节拍 | 运镜与构图 | 可见动作 | 声音／对白入口 | 镜末变化 |\n|---|---|---|---|---|---|---|\n'
        for shot in ep['shots']:
            window = f"{stamp(shot['start_frame'])}–{stamp(shot['end_frame'])} / [{shot['start_frame']},{shot['end_frame']})"
            text += f"| {shot['id']}／{shot['scene_id']} | {window} | {shot['beat']} | {shot['camera']} | {shot['action']} | {shot['sound']} | {shot['end_state']} |\n"
        detailed = [s for s in ep['shots'] if s.get('performance')]
        if detailed:
            text += '\n### 逐镜表演与接续执行\n\n以下为导演工作稿；切点是动作触发条件，未替代试读计时，父镜号和预算保持。\n\n| 镜号 | 表演与关系变化 | 调度／道具接续 | 切镜触发 |\n|---|---|---|---|\n'
            for s in detailed:
                text += f"| {s['id']} | {s['performance']} | {s['blocking_continuity']} | {s['cut_cue']} |\n"
    text += '\n## 验收与减法顺序\n\n先用当前对白和静帧／占位板验证占时，再录可替换的临时声音；不宣称已经有录音。每镜检查空间、接触结果、视线、衣伤、道具归属、声音先后。超时优先压空景、重复反应和走路过渡；不删十人退出、韩许换手、黄撤令、原顾清醒回家、今顾选择开门、旧票用途差异。若仍超出约3分钟，提出新的分集边界供复核，不能默默加速成片。\n'
    return text


def render(data):
    tasks = data['tasks']
    mj = [t for t in tasks if t['method'] == 'MJ']
    ordered = sorted(mj, key=lambda t: (not bool(t['first_batch']), t['first_batch'] or 999, t['id']))
    selected_count = sum(t['media_status'] == 'selected' for t in tasks)
    counts = f'{len(tasks)}项交接任务：{len(mj)}项MJ探索、{len(tasks)-len(mj)}项非MJ任务；{len(FACE_CAST)}张独立身份脸、C60一个遮脸轮廓、另有第一波十个遮面群演实例、16场。已有{selected_count}项已绑定身份母版，其余{len(tasks)-selected_count}项未完成；全库母版登记见[媒体库](../../媒体/README.md)。'
    current = [t for t in tasks if t['release_scope'] == 'current_first_three']
    counts += f" 这是前三发行集与后续门口预备的合计；当前前三集关联{len(current)}项，后续专用{len(tasks)-len(current)}项。前三发行集11场、180／195／180秒，详[逐镜节奏](前三集节奏与分镜.md)。"
    if data['matched_asset_references']:
        counts += f" 另有{len(data['matched_asset_references'])}张混合资产匹配参考已登记，置信度与冲突见[媒体登记](../../媒体/README.md)，不计已选任务。"
    if data['pending_master_candidates']:
        counts += f" 另有{len(data['pending_master_candidates'])}张蒙面半身参考待核对身份，未绑定FACE、全身或第一波实例；详[媒体登记](../../媒体/README.md)。"
    overview = '# 前三集资产任务清单 v1.9\n\n' + counts + '\n\n[使用说明](README.md) · [英文提示词](MJ提示词.md) · [文书与后制](文书后制与非MJ任务.md)\n\n优先级A/B/C是探索批次，不是成片可删等级。首批1—20为顾砚、韩青、杜长庚、顾伯、黄祁各四项服装母版，不是护送队名单；已有身份选图可先登记复用，未提供不算通过。带依赖任务须先验收前置，不能按行序盲跑。\n\n| 任务 | 名称／类别 | 批次／首批序 | 资产 | 场次 | 前置 | 验收 |\n|---|---|---|---|---|---|---|\n'
    prompts = '# MJ母版探索提示词 v1.9\n\n以下是执行前待检查的文字投影，不是已经批准的母版。模型V8.2；使用前按[README](README.md)检查账户设置，基线关闭Personalization并清除遗留引用。派生项正文须配合已选父母版输入，不能仅靠文字重抽。不得把父任务编号当作图片链接。\n\n首批20项服装图置前；其余按ID排列便于检索，实际按依赖执行。每框仅一张图。既有THREEQUARTER仍为侧脸，不与新增FULL-3Q混同。\n'
    for t in tasks:
        target = 'MJ提示词.md#' + t['id'].lower() if t['method'] == 'MJ' else '文书后制与非MJ任务.md'
        scope = ', '.join(t['release_episode_ids']) or '后续专用预备'
        overview += f"| [{t['id']}]({target}) | {t['name']}／{t['category']} | {t['phase']}／{t['first_batch'] or '—'} | {', '.join(t['asset_ids'])} | {scope}：{', '.join(t['scene_ids'])} | {', '.join(t['depends_on']) or '执行前检查'} | {t['acceptance']} |\n"
    for t in ordered:
        prompts += f"\n<a id=\"{t['id'].lower()}\"></a>\n\n## {t['id']}｜{t['name']}\n\n"
        prompts += f"首批：{t['first_batch'] or '扩展'}；前置：{', '.join(t['depends_on']) or '无图像前置，先检查设置'}。\n\n"
        prompts += '发行用途：' + (', '.join(t['release_episode_ids']) or '后续专用预备，不进入前三发行集') + '。场次关联不自动授权露脸或台词。\n\n'
        prompts += '来源：' + ' · '.join(f'[{Path(p).stem}](<{link(p)}>)' for p in t['source_paths']) + '\n\n'
        prompts += f"```text\n{t['projection']}\n```\n\n验收：{t['acceptance']}。\n\n"
        if t['media_status'] == 'selected':
            prompts += f"状态：已绑定[本任务母版](<{link(t['actual_file'])}>)，复用本图；指定、自动适配或逐图验收依据见媒体登记，以上文字无需重新海选。\n"
        elif t['media_status'] == 'generated_candidate':
            prompts += f"状态：已用内置imagegen生成[实际候选](<{link(t['actual_file'])}>)，尚待衣装复核；并非MJ执行结果，实际工具和提示词见媒体登记。\n"
        else:
            prompts += f"状态：尚未生成；拟存文件名 `{t['planned_filename']}`，实际文件为空。\n"
        if t['input_references']:
            prompts += '\n母版图像引用：' + ' · '.join(f"[{r['master_id']}](<{link(r['path'])}>)（{r['purpose']}）" for r in t['input_references']) + '。按各引用用途锁身份或建筑造型；仍须满足服装与空间前置。\n'
        for r in t['input_references']:
            if r['purpose'] in ('architecture_visual', 'ordinary_assassin_group'):
                prompts += '\n引用边界：' + r['constraints'] + '\n'
        if t['unresolved_dependencies']:
            prompts += '\n尚缺前置：' + '、'.join(t['unresolved_dependencies']) + '。\n'
    overview += '\n## 停用编号\n\n' + '\n'.join(f"- {r['id']}：{r['reason']}" for r in data['retired_tasks']) + '\n'
    out = {'生产任务.json': json.dumps(data, ensure_ascii=False, indent=2) + '\n',
           '资产任务清单.md': overview, 'MJ提示词.md': prompts,
           '../../媒体/母版自动适配编号.md': render_mapping(data),
           '前三集实际资产缺口.md': render_missing(data),
           '前三集节奏与分镜.md': render_release(data['release_plan'])}
    buf = io.StringIO(newline='')
    writer = csv.writer(buf)
    writer.writerow(['任务ID', '名称', '工序', '批次', '首批序', '资产ID', '场次', '前置任务', '验收条件', '英文提示词', '状态', '拟定文件名', '发行集', '制作范围', '实际文件', '母版图像引用', '尚缺前置'])
    for t in tasks:
        writer.writerow([t['id'], t['name'], t['method'], t['phase'], t['first_batch'] or '',
                         ';'.join(t['asset_ids']), ';'.join(t['scene_ids']), ';'.join(t['depends_on']),
                         t['acceptance'], t['projection'], t['status'], t['planned_filename'], ';'.join(t['release_episode_ids']), t['release_scope'],
                         t['actual_file'] or '', ';'.join(r['path'] for r in t['input_references']), ';'.join(t['unresolved_dependencies'])])
    out['资产任务清单.csv'] = '\ufeff' + buf.getvalue()
    buf = io.StringIO(newline='')
    writer = csv.writer(buf)
    writer.writerow(['任务ID', '候选文件路径', '实际MJ任务ID', '执行日期', '模型与实际参数', '完整提示词', '实际Seed', '输入引用与用途', '引用权利检查', '选择结果', '选择人', '不通过原因', '父母版版本', '输出尺寸'])
    for t in mj:
        writer.writerow([t['id'], *[''] * 13])
    out['选版记录模板.csv'] = '\ufeff' + buf.getvalue()
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'check'))
    args = parser.parse_args()
    data = build_data()
    outputs = render(data)
    stale = []
    for name, value in outputs.items():
        path = PACK / name
        if args.command == 'build':
            path.write_bytes(value.encode('utf-8'))
        elif not path.exists() or path.read_bytes() != value.encode('utf-8'):
            stale.append(name)
    if stale:
        raise SystemExit('生产派生件过期：' + ', '.join(stale))
    print(f"{args.command}: {len(data['tasks'])} tasks, {len(FACE_CAST)} faces, 1 concealed figure, 16 scenes; {len(data['selected_masters'])} registered masters, {sum(t['media_status']=='selected' for t in data['tasks'])} selected task; remaining task outputs pending.")


if __name__ == '__main__':
    main()
