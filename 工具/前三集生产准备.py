"""从作者维护的任务源生成 MJ 探索交接包；不调用生成服务、不宣布选版。"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / '资产/生产准备/前三集-v1.9'
VETS = ['C03', *[f'C{i:02}' for i in range(16, 24)]]
CORE = {'C01', 'C03', 'C04', 'C06', 'C12', 'C14', 'C16'}
ASSASSINS = {'C06', 'C07', 'C57', 'C58', 'C59'}
FIRST_CAST = {f'C{i:02}' for i in range(1, 24)} | {'C57', 'C58', 'C59', 'C60'}
FACE_CAST = FIRST_CAST - {'C02', 'C05', 'C60'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def link(path):
    return os.path.relpath(ROOT / path, PACK).replace('\\', '/')


def validate(data):
    tasks = data['tasks']
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError('重复任务编号')
    by_id = {t['id']: t for t in tasks}
    first = sorted(t['first_batch'] for t in tasks if t['first_batch'])
    if first != list(range(1, 13)):
        raise ValueError('首批须为连续12项')
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
        if t['actual_file'] is not None or t['media_status'] != 'not_generated':
            raise ValueError('任务计划不能冒充实际媒体')
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
        raise ValueError('必须24张独立身份脸，C01/C02同脸、C05仅声、C60遮脸')
    mystery = [t for t in tasks if t['method'] == 'MJ' and 'C60' in t['asset_ids']]
    if len(mystery) != 1 or mystery[0]['id'] != 'MB-C60-SILHOUETTE':
        raise ValueError('C60仅允许遮脸轮廓任务，不能自动制作身份脸')
    coverage = {a for t in tasks if t['method'] == 'MJ' for a in t['asset_ids']}
    if not set(data['visible_asset_ids']) <= coverage:
        raise ValueError('可见资产未覆盖：' + str(set(data['visible_asset_ids']) - coverage))


def build_data():
    cfg = read(PACK / '视觉任务源.json')
    extra = read(PACK / '补充任务源.json')
    eps = read(ROOT / '索引/数据/episodes.json')[:3]
    registry = {}
    for name in ('characters', 'locations', 'props'):
        for item in read(ROOT / f'索引/数据/{name}.json'):
            registry[item['id']] = item
    scenes = [s for e in eps for s in e['scenes']]
    char = {c['id']: c for c in cfg['characters']}
    gear = {g['id']: g for g in extra['veteran_gear']}
    tasks = []

    def add(key, title, category, assets, body='', ratio='4:3', deps=(), first=0,
            checks='', scene_ids=None, phase='B', method='MJ'):
        used = scene_ids or [s['id'] for s in scenes if set(assets) &
                                set(s['character_ids'] + (s['voice_only_ids'] if method != 'MJ' else []) + s['location_ids'] + s['prop_ids'])]
        paths = sorted({registry[a]['path'] for a in assets if a in registry} |
                       {e['path'] for e in eps if any(s['id'] in used for s in e['scenes'])} |
                       {'剧集/前三集重写与生产交接-v1.9.md', '资产/美术风格与造型总则.md'})
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

    def actor(c, view, costume=None):
        return (f"Single fictional Chinese man, age {c['age']}, {c['identity_en']}. "
                f"{c['hair_en']}. {costume or c['costume_en']}. {view}. "
                'Plain warm-gray studio background, one subject, one frame. ' + cfg['style_en'])

    for c in cfg['characters']:
        cid = c['id']
        aids = [cid, *c['shares']]
        add(f'MB-{cid}-FACE', c['name'] + '｜正脸身份', '身份', aids,
            actor(c, 'Front-facing head-and-shoulders portrait, neutral relaxed expression, unobstructed face, soft even face light'),
            '3:4', first=c['first_batch'], checks=c['checks'], phase=c['tier'])
        add(f'MB-{cid}-FULL', c['name'] + '｜全身干衣', '衣装', aids,
            actor(c, 'Front-facing full-length standing costume study, both hands relaxed and visible, feet included'),
            '2:3', deps=[f'MB-{cid}-FACE'], checks=c['checks'] + '；衣型、体量和脸沿已选母版；干衣无新伤', phase=c['tier'])
        if cid in CORE:
            for suffix, label, angle in [('PROFILE', '侧脸', 'clean left profile head-and-shoulders portrait'),
                                          ('THREEQUARTER', '四分之三脸', 'three-quarter head-and-shoulders portrait')]:
                add(f'MB-{cid}-{suffix}', c['name'] + '｜' + label, '身份视角', aids,
                    actor(c, angle + ', neutral relaxed expression'), '3:4', [f'MB-{cid}-FACE'],
                    checks=c['checks'] + '；只改视角，耳鼻下颌与选脸同源', phase=c['tier'])
    for e in cfg['environments']:
        add('MB-ENV-' + e['key'], e['name'], '空间', e['asset_ids'], e['body_en'], e['ratio'],
            first=e['first_batch'], checks=e['checks'])
    for p in cfg['props']:
        add(f"MB-{p['id']}-BASE", p['name'], '道具', [p['id']], p['body_en'], p['ratio'],
            first=p['first_batch'], checks=p['checks'])
    for s in extra['states']:
        add('MB-' + s['key'], s['name'], '衣伤表演状态', s['asset_ids'],
            actor(char[s['owner']], 'Head-and-shoulders performance study' if s['key'] in ('C02-FEAR', 'C02-FOCUS') else 'Single full-length standing costume continuity study', s['costume_en']),
            '3:4' if s['key'] in ('C02-FEAR', 'C02-FOCUS') else '2:3', [s['parent']],
            checks=s['checks'], scene_ids=s['scenes'])
    for cid in VETS:
        c = char[cid]
        g = gear[cid]
        costume = c['costume_en'] + ', ' + g['armor_en']
        used = [s['id'] for s in scenes[:3] if cid in s['character_ids']]
        add(f'MB-{cid}-ARMOR', c['name'] + '｜归途轻甲与佩兵', '轻甲衣装', [cid, 'P20', 'P21'],
            actor(c, 'Full-length neutral standing costume study, equipment at rest, no combat pose', costume + ', ' + g['standing_en']),
            '2:3', [f'MB-{cid}-FULL', 'MB-P20-BASE', 'POST-KIT'],
            checks=c['checks'] + '；' + g['checks'] + '；只加P20轻甲及本人P21，不改脸、衣色或境界；1-3卸甲，1-4以后用常服FULL', scene_ids=used)
        add(f'MB-{cid}-RAIN', c['name'] + '｜归途湿甲', '衣伤状态', [cid, 'P20', 'P21'],
            actor(c, 'Full-length standing costume continuity study', costume + ', ' + g['standing_en'] + ', rain-darkened matte leather, rain-soaked cloth, restrained road mud at hems'),
            '2:3', [f'MB-{cid}-ARMOR'], checks=c['checks'] + '；只改湿度与下摆泥痕，不新增本人伤口；甲不透光，1-3卸下，之后常服', scene_ids=used)
    for e in extra['extras']:
        add('MB-' + e['key'], e['name'], '补充近景件', e['asset_ids'], e['body_en'], e['ratio'],
            [e['parent']] if e['parent'] else [], checks=e['checks'], phase=e['phase'])
    for m in extra.get('mounts', []):
        c = char[m['rider']]
        add('MB-' + m['rider'] + '-MOUNTED', c['name'] + '｜单人骑乘绑定', '骑乘绑定',
            [m['rider'], 'P19', 'P20', 'P21'],
            f"One fictional Chinese man, age {c['age']}, {c['identity_en']}, {c['hair_en']}, wearing {c['costume_en']}, {gear[m['rider']]['armor_en']}, seated naturally on one ordinary adult riding horse, {m['horse_en']}. {gear[m['rider']]['mounted_en']}. Plain period travel saddle and modest side luggage, full rider and horse visible in a three-quarter side view, all four hooves supported on level ground, quiet neutral pose, diffuse daylight, plain background, one rider and one horse only. " + cfg['style_en'],
            '4:3', [f"MB-{m['rider']}-ARMOR", 'POST-HORSES'],
            checks=f"骑手与已选轻甲母版同脸同衣甲；坐骑必须是已核对{m['horse_id']}，人马体量、鞍接触与行李位置一致；长兵盾弓按本人鞍侧归属，不画马上交锋；只验证骑乘外观，不宣称真实骑术或安全。",
            scene_ids=['GJ-EP01-SC01'])
    for key, label, change, used in [
        ('S02', '清晨街口', 'Replace night lighting with cool early-morning daylight; preserve the selected street geometry and stall placement.', ['GJ-EP02-SC03', 'GJ-EP03-SC02', 'GJ-EP03-SC04']),
        ('S03-COURT', '雨后夜院', 'Replace daylight with restrained warm practical lamps and cool wet-night ambient light; preserve every door and passage.', ['GJ-EP01-SC03', 'GJ-EP01-SC04']),
        ('S03-HALL', '夜间前厅', 'Replace daylight with warm practical lamp light and cool night fill; preserve the fixed large table and door geometry.', ['GJ-EP01-SC03']),
        ('S03-W', '夜间西厢', 'Replace daylight with warm practical lamps and cool night fill; preserve sleeping and luggage zones.', ['GJ-EP01-SC03', 'GJ-EP02-SC02']),
        ('S05', '清晨卧房', 'Replace night lighting with gentle cool morning window light; preserve bed, doors and furniture.', ['GJ-EP02-SC05'])]:
        e = next(e for e in cfg['environments'] if e['key'] == key)
        add('MB-LIGHT-' + key, label, '空间光态', e['asset_ids'],
            'Edit the selected empty set master. ' + change + ' High-end Chinese costume drama set, readable shadows, empty room or street, one frame.',
            '16:9', ['MB-ENV-' + key], checks='与父母版同一拓扑及机位；只改昼夜光态，不新增建筑', scene_ids=used)
    add('MB-TEST-C01-BLOOM', '顾砚高光扩散单变量对照（选做）', '风格测试', ['C01', 'C02'],
        'Edit the selected portrait. Preserve identity, pose, clothing, background, framing and color balance. Add only a restrained soft highlight bloom around the existing light-facing edge, keeping eyes and skin texture crisp.',
        '3:4', ['MB-C01-FACE'], checks='只比较高光扩散有／无；不以磨皮、改脸替代柔光，其他参数与母版相同', phase='OPTIONAL')
    manual_deps = {
        'PLAN-COURT': [], 'TEXT-DOCS': [f'MB-P{i:02}-BASE' for i in (3, 4, 6, 7, 8, 17)],
        'P09-BROKEN': ['MB-P09-BASE'], 'P06-STATE': ['POST-TEXT-DOCS'],
        'P16-NINE': ['MB-P16-BASE'], 'ENSEMBLE': [f'MB-{c}-ARMOR' for c in VETS],
        'KIT': ['MB-P20-BASE', *['MB-WEAPON-' + key for key in ('BLADE', 'SPEAR', 'BOW', 'LONG-BLADE', 'SHORT-SPEAR', 'SHIELD')]],
        'FX-COPPER': ['POST-P16-NINE', 'MB-P20-BASE', 'MB-ENV-S01'],
        'INTEGRATION': ['MB-C01-DRY', 'MB-C03-FULL', 'MB-C04-FULL', 'MB-C16-FULL', 'MB-ENV-S04', 'MB-ENV-S03-COURT'],
        'AUDIO': [], 'ACTION': ['POST-PLAN-COURT', 'POST-PLAN-FOREST'],
        'PLAN-FOREST': [], 'HORSES': ['MB-P19-BASE'], 'BACKGROUND': ['POST-PLAN-COURT']}
    for e in extra['manual_tasks']:
        add('POST-' + e['key'], e['name'], '非MJ交接', e['asset_ids'],
            deps=manual_deps[e['key']], checks=e['deliverable'] + ' 验收：' + e['acceptance'], method='POST')
    # 光态与群体图的形状依赖不是选漂亮图之后再反改平面图。
    for t in tasks:
        if 'S01' in t['asset_ids'] and t['method'] == 'MJ':
            t['depends_on'].append('POST-PLAN-FOREST')
            t['status'] = 'awaiting_parent_selection'
        if t['category'] == '空间' and any(a.startswith(('S03', 'S04', 'S05', 'S06')) for a in t['asset_ids']):
            t['depends_on'].append('POST-PLAN-COURT')
            t['status'] = 'awaiting_parent_selection'
    visible = sorted({a for s in scenes for a in s['character_ids'] + s['location_ids'] + s['prop_ids']})
    paths = {p for t in tasks for p in t['source_paths']} | {
        '索引/数据/episodes.json', '资产/生产准备/前三集-v1.9/视觉任务源.json',
        '资产/生产准备/前三集-v1.9/补充任务源.json', '工具/前三集生产准备.py'}
    data = dict(format='jingshi-production-working-draft', canonical=False, revision='v1.9',
                baseline_commit=cfg['baseline_commit'], media_status='not_generated',
                model=cfg['model'], manual_preflight_required=True,
                scene_ids=[s['id'] for s in scenes], visible_asset_ids=visible,
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)}, tasks=tasks)
    validate(data)
    return data


def render(data):
    tasks = data['tasks']
    mj = [t for t in tasks if t['method'] == 'MJ']
    ordered = sorted(mj, key=lambda t: (not bool(t['first_batch']), t['first_batch'] or 999, t['id']))
    counts = f'{len(tasks)}项交接任务：{len(mj)}项MJ探索、{len(tasks)-len(mj)}项非MJ任务；{len(FACE_CAST)}张独立身份脸、1个遮脸轮廓、16场，全部尚未生成或选版。'
    overview = '# 前三集资产任务清单 v1.9\n\n' + counts + '\n\n[使用说明](README.md) · [英文提示词](MJ提示词.md) · [文书与后制](文书后制与非MJ任务.md)\n\n优先级A/B/C是探索批次，不是成片可删等级。所有角色仍须覆盖；首批序号1—12只确定审美方向。带依赖任务须先验收前置，不能按表格行序盲跑。\n\n| 任务 | 名称／类别 | 批次／首批序 | 资产 | 场次 | 前置 | 验收 |\n|---|---|---|---|---|---|---|\n'
    prompts = '# MJ母版探索提示词 v1.9\n\n以下是执行前待检查的文字投影，不是已经批准的母版。模型V8.2；使用前按[README](README.md)检查账户设置。派生项正文须配合已选父母版输入，不能仅靠文字重抽。不得把父任务编号当作图片链接。\n\n首批12项置前；其余按ID排列便于检索，实际按依赖执行。每框仅一张图。\n'
    for t in tasks:
        target = 'MJ提示词.md#' + t['id'].lower() if t['method'] == 'MJ' else '文书后制与非MJ任务.md'
        overview += f"| [{t['id']}]({target}) | {t['name']}／{t['category']} | {t['phase']}／{t['first_batch'] or '—'} | {', '.join(t['asset_ids'])} | {', '.join(t['scene_ids'])} | {', '.join(t['depends_on']) or '执行前检查'} | {t['acceptance']} |\n"
    for t in ordered:
        prompts += f"\n<a id=\"{t['id'].lower()}\"></a>\n\n## {t['id']}｜{t['name']}\n\n"
        prompts += f"首批：{t['first_batch'] or '扩展'}；前置：{', '.join(t['depends_on']) or '无图像前置，先检查设置'}。\n\n"
        prompts += '来源：' + ' · '.join(f'[{Path(p).stem}](<{link(p)}>)' for p in t['source_paths']) + '\n\n'
        prompts += f"```text\n{t['projection']}\n```\n\n验收：{t['acceptance']}。\n\n状态：尚未生成；拟存文件名 `{t['planned_filename']}`，实际文件为空。\n"
    out = {'生产任务.json': json.dumps(data, ensure_ascii=False, indent=2) + '\n',
           '资产任务清单.md': overview, 'MJ提示词.md': prompts}
    buf = io.StringIO(newline='')
    writer = csv.writer(buf)
    writer.writerow(['任务ID', '名称', '工序', '批次', '首批序', '资产ID', '场次', '前置任务', '验收条件', '英文提示词', '状态', '拟定文件名'])
    for t in tasks:
        writer.writerow([t['id'], t['name'], t['method'], t['phase'], t['first_batch'] or '',
                         ';'.join(t['asset_ids']), ';'.join(t['scene_ids']), ';'.join(t['depends_on']),
                         t['acceptance'], t['projection'], t['status'], t['planned_filename']])
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
    print(f"{args.command}: {len(data['tasks'])} tasks, {len(FACE_CAST)} faces, 1 concealed figure, 16 scenes; media not generated.")


if __name__ == '__main__':
    main()
