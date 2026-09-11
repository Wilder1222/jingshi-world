"""从现行台本解析逐镜对白引用；字数密度只供试读排查，不等于实测语速。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_dialogue(release, root=ROOT):
    required = {sid for ep in release['episodes'] for sid in ep['scene_ids']}
    scenes = {}
    for episode in json.loads((root / '索引/数据/episodes.json').read_text(encoding='utf-8-sig')):
        selected = [s for s in episode.get('scenes', []) if s['id'] in required]
        if not selected:
            continue
        script = (root / episode['path']).read_text(encoding='utf-8-sig')
        for scene in selected:
            heading = re.search(r'^### ' + re.escape(scene['alias']) + r'\s[^\n]*', script, re.M)
            if not heading:
                raise ValueError('对白源场次标题缺失：' + scene['id'])
            section = re.split(r'^### |<!-- DRAFT-EP\d+-END -->', script[heading.end():], maxsplit=1, flags=re.M)[0]
            turns = []
            for match in re.finditer(r'^\*\*([^\n]*?)：\*\*([^\n]+)', section, re.M):
                speaker, line = match.groups()
                if speaker == '跨集省略的接续状态':
                    continue
                parts = re.findall(r'[^。！？!?]+[。！？!?]?', line.strip())
                turns.append(dict(speaker=speaker, parts=parts, source=episode['path'],
                                  source_line=script.count('\n', 0, heading.end() + match.start()) + 1))
            scenes[scene['id']] = turns
    if set(scenes) != required:
        raise ValueError('对白源场次未完整解析')
    used = {sid: [] for sid in required}
    result = {}
    for episode in release['episodes']:
        for shot in episode['shots']:
            refs = shot.get('dialogue_refs')
            if not isinstance(refs, list):
                raise ValueError('逐镜对白引用缺失：' + shot['id'])
            sid = shot['scene_id']
            rows = []
            for ref in refs:
                number = ref.get('turn')
                if type(number) is not int or not 1 <= number <= len(scenes[sid]):
                    raise ValueError('对白轮次引用越界：' + shot['id'])
                turn = scenes[sid][number - 1]
                indices = ref.get('sentences', list(range(1, len(turn['parts']) + 1)))
                if (not isinstance(indices, list) or not indices or any(type(i) is not int or
                        not 1 <= i <= len(turn['parts']) for i in indices)):
                    raise ValueError('对白句段引用越界：' + shot['id'])
                used[sid].extend((number, i) for i in indices)
                quote = ''.join(turn['parts'][i - 1] for i in indices)
                rows.append(dict(speaker=turn['speaker'], text=quote, source=turn['source'],
                                 source_line=turn['source_line'],
                                 characters=len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', quote))))
            result[shot['id']] = rows
    for sid, turns in scenes.items():
        expected = [(n, i) for n, turn in enumerate(turns, 1) for i in range(1, len(turn['parts']) + 1)]
        if used[sid] != expected:
            raise ValueError('对白漏句、重复或倒序：' + sid)
    return result


def render_dialogue(episode, resolved):
    text = '\n### 台本对白与试读入口\n\n'
    text += '对白由现行台本读取，分镜源只保存轮次／句段引用。下面的字数不含标点；字数÷镜长仅为整个镜头的字数密度，未扣除换气、反应和动作，不能视为演员语速或已通过时长验收。对白跨切镜可分句承接，不能重复配音；没有台本句子的声栏不授权自行增加解释对白。\n\n'
    text += '| 镜号 | 镜长 | 说话者与台本原句 | 字数／秒 |\n|---|---|---|---|\n'
    for shot in episode['shots']:
        rows = resolved[shot['id']]
        if not rows:
            continue
        seconds = (shot['end_frame'] - shot['start_frame']) / 24
        count = sum(row['characters'] for row in rows)
        lines = '<br>'.join(f"{row['speaker']}：{row['text']}".replace('|', '\\|') for row in rows)
        text += f"| {shot['id']} | {seconds:g}秒 | {lines} | {count}字／{count / seconds:.2f} |\n"
    return text
