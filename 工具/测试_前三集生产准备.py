"""制作清单的结构回归；不冒充视觉质量或台词计时测试。"""
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('production', ROOT / '工具/前三集生产准备.py')
production = importlib.util.module_from_spec(spec)
spec.loader.exec_module(production)


class ProductionTests(unittest.TestCase):
    def test_required_coverage_does_not_infer_missing_views(self):
        data = copy.deepcopy(self.data)
        report = production.render_missing(data)
        coverage = report.split('## 主要人物与重点场景必要项覆盖')[1].split('## 新增必要包')[0]
        c04 = next(line for line in coverage.splitlines() if line.startswith('| C04 '))
        self.assertIn('缺：未登记交付', c04)
        self.assertIn('C04-表情九宫格.png', c04)
        self.assertNotIn('C04-侧脸.png', c04)
        s02 = next(line for line in coverage.splitlines() if line.startswith('| S02 '))
        self.assertEqual(s02.count('缺：未登记交付'), 2)
        self.assertNotIn('同机位空底.png', s02)
        c01 = next(line for line in coverage.splitlines() if line.startswith('| C01 '))
        self.assertIn('C01-表情九宫格.png', c01)
        self.assertIn('C02-表情九宫格.png', c01)
        data['necessary_asset_packages'] = [p for p in data['necessary_asset_packages'] if p['id'] != 'C01-FULL-SIDE']
        changed = production.render_missing(data)
        c01 = next(line for line in changed.splitlines() if line.startswith('| C01 '))
        self.assertIn('缺：未登记交付', c01)
        self.assertNotIn('四分之三', c01)

    def test_court_horse_labels_match_current_convoy(self):
        plan = json.loads((ROOT / '资产/空间校核/P01-空间基准.json').read_text(encoding='utf-8'))
        convoy = plan['convoy']
        horses = {convoy[k].split(' / ')[1] for k in ('front_left', 'front_right', 'rear_left', 'rear_right')}
        self.assertEqual(horses, {'H01', 'H02', 'H05', 'H08'})
        diagram = (ROOT / '资产/空间校核/顾府二维关系.svg').read_text(encoding='utf-8')
        self.assertEqual(set(re.findall(r'\bH\d{2}\b', diagram)), horses)
        self.assertIsNone(plan['travel_envelope']['four_abreast_draft_outer_width'])
        self.assertIn('资产/空间校核/P01-空间基准.json', self.data['source_sha256'])

    def test_missing_report_keeps_necessary_candidates_separate(self):
        data = copy.deepcopy(self.data)
        report = production.render_missing(data)
        self.assertIn('新增必要包与分镜候选', report)
        self.assertIn('尚未通过的核心参考', report)
        for item in data['necessary_asset_packages']:
            self.assertIn('[' + item['id'] + ']', report)
        task_states = [(t['id'], t['media_status']) for t in data['tasks']]
        data['necessary_asset_packages'] = []
        empty = production.render_missing(data)
        self.assertIn('必要包登记共0项', empty)
        self.assertEqual(task_states, [(t['id'], t['media_status']) for t in data['tasks']])
        self.assertEqual(report.split('由生产任务和实际媒体登记生成：')[1].split('\n')[0],
                         empty.split('由生产任务和实际媒体登记生成：')[1].split('\n')[0])

    def test_global_creation_rules_invalidate_production_fingerprint(self):
        original_read = Path.read_bytes
        for source_name in production.CREATION_RULE_SOURCES:
            with self.subTest(source=source_name):
                rule_path = ROOT / source_name
                rule_bytes = original_read(rule_path)
                self.assertEqual(self.data['source_sha256'][source_name], hashlib.sha256(rule_bytes).hexdigest())

                def changed_rule_bytes(path):
                    if path.resolve() == rule_path.resolve():
                        return rule_bytes + b'\n<!-- changed creation requirement -->\n'
                    return original_read(path)

                with patch.object(Path, 'read_bytes', changed_rule_bytes):
                    changed = production.build_data()
                self.assertNotEqual(changed['source_sha256'][source_name], self.data['source_sha256'][source_name])
                self.assertEqual(changed['release_plan'], self.data['release_plan'])
                self.assertEqual(changed['tasks'], self.data['tasks'])

    def test_return_convoy_corners_and_rear_luggage(self):
        shots = {s['id']: s for e in self.data['release_plan']['episodes'] for s in e['shots']}
        layout = shots['GJ-R01-SH002']['blocking_continuity']
        for detail in ('杜长庚左前', '石照川右前', '崔望野左后', '许照邻右后', '韩青在前驾座', '车厢后部行李架'):
            self.assertIn(detail, layout)
        self.assertIn('P02在车尾', shots['GJ-R01-SH003']['blocking_continuity'])
        self.assertIn('右后角接车尾取包', shots['GJ-R01-SH004']['blocking_continuity'])

    def test_individual_prop_support_integrity_and_task_boundary(self):
        from 母版匹配 import validate_support
        parent = next(m for m in self.data['generated_assets'] if m['task_id'] == 'MB-WEAPON-BLADE')
        self.assertEqual({s['id'] for s in parent['supporting_assets']}, {'P21-C03', 'P21-C16', 'P21-C17', 'P21-C20', 'P21-C23'})
        for item in parent['supporting_assets']:
            self.assertIn(item['path'], self.data['source_sha256'])
            validate_support(item, parent, set(), parent['supporting_assets'])
            bad = copy.deepcopy(item)
            bad['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, '哈希'):
                validate_support(bad, parent, set(), parent['supporting_assets'])
            bad = copy.deepcopy(item)
            bad['generation']['input_references'][0]['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, '输入母版'):
                validate_support(bad, parent, set(), parent['supporting_assets'])
            with self.assertRaisesRegex(ValueError, '编号重复'):
                validate_support(item, parent, {item['id']})
        kit = next(t for t in self.data['tasks'] if t['id'] == 'POST-KIT')
        self.assertNotEqual(kit['media_status'], 'selected')

    @classmethod
    def setUpClass(cls):
        cls.data = production.build_data()

    def test_auto_assigned_portraits_reuse_user_media(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for cid in ('C04', 'C16'):
            face = tasks[f'MB-{cid}-FACE']
            master = next(m for m in self.data['selected_masters'] if m['id'] == face['selected_master_id'])
            self.assertEqual(master['selected_by'], 'assistant_under_user_auto_numbering_request')
            self.assertEqual(face['actual_file'], master['path'])
            self.assertIn(master['id'], {r['master_id'] for r in tasks[f'MB-{cid}-FULL']['input_references']})

    def test_reviewed_generated_parent_unlocks_only_its_descendants(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for cid in ('C01', 'C04', 'C16'):
            self.assertEqual(tasks[f'MB-{cid}-FULL']['media_status'], 'selected')
            back = tasks[f'MB-{cid}-FULL-BACK']
            self.assertNotIn(f'MB-{cid}-FULL', back['unresolved_dependencies'])
            self.assertIn(f'generated-{cid}-FULL', {r['master_id'] for r in back['input_references']})
        self.assertIn('MB-S01-W1-01', tasks['POST-WAVES']['unresolved_dependencies'])

    def test_full_body_age_and_proportions_do_not_leak_into_sets(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for cid in ('C01','C04','C16'):
            for suffix in ('FULL','FULL-3Q','FULL-BACK'):
                self.assertIn('head-to-body', tasks[f'MB-{cid}-{suffix}']['prompt_en'])
        self.assertIn('do not automatically hunch', tasks['MB-C04-FULL']['prompt_en'])
        self.assertNotIn('head-to-body', tasks['MB-ENV-S04']['prompt_en'])

    def test_episode_three_performance_continuity_and_cut_cues(self):
        shots = self.data['release_plan']['episodes'][2]['shots']
        self.assertEqual(len(shots), 22)
        self.assertIn('右侧', shots[17]['blocking_continuity'])
        self.assertIn('门始终未开', shots[-1]['blocking_continuity'])
        bad = copy.deepcopy(self.data)
        del bad['release_plan']['episodes'][2]['shots'][0]['performance']
        with self.assertRaisesRegex(ValueError, '前三集逐镜'):
            production.validate(bad)

    def test_all_shots_have_executable_story_continuity_notes(self):
        shots = [s for e in self.data['release_plan']['episodes'] for s in e['shots']]
        self.assertEqual(len(shots), 71)
        for key in ('performance', 'blocking_continuity', 'cut_cue'):
            self.assertTrue(all(s[key] for s in shots))
        first = self.data['release_plan']['episodes'][0]['shots']
        self.assertIn('许扶顾右侧', first[6]['blocking_continuity'])
        self.assertIn('第二波只在末人离开后', first[11]['blocking_continuity'])
        second = self.data['release_plan']['episodes'][1]['shots']
        self.assertIn('不暗示意识更替', second[5]['blocking_continuity'])
        self.assertIn('只合门不落闩', second[-1]['blocking_continuity'])

    def test_combat_contract_rejects_wrong_sequence_and_duel_roles(self):
        mutations = [
            lambda e: e['shots'][7].update(combat_phase='formation_four_and_duel'),
            lambda e: e['shots'][15].update(combat_phase='elite_individual_pressure'),
            lambda e: e['shots'][11].pop('combat_phase'),
            lambda e: e['combat_contract'].update(blocked_opponents=['C06', 'C57', 'C58', 'C59']),
            lambda e: e['combat_contract'].update(formation_members=production.VETS + ['C01']),
            lambda e: e['combat_contract'].update(duel_participants=['C01', 'C07']),
            lambda e: e['combat_contract'].update(held_during_duel=True),
            lambda e: e['combat_contract'].update(hero_in_formation=True),
            lambda e: e['combat_contract'].update(first_wave_resolution='planned_handover'),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                data = copy.deepcopy(self.data)
                mutate(data['release_plan']['episodes'][0])
                with self.assertRaisesRegex(ValueError, '林战'):
                    production.validate(data)

    def test_first_wave_handovers_precede_full_team_combat(self):
        shots = self.data['release_plan']['episodes'][0]['shots']
        self.assertIn('二人此镜不参加', shots[4]['blocking_continuity'])
        self.assertIn('顾靠车自行站稳', shots[6]['action'])
        self.assertIn('许再拔刀入战', shots[6]['action'])
        self.assertIn('第一波十人', shots[10]['action'])
        self.assertIn('最后一人退净', shots[10]['action'])
        self.assertIn('五名高手', shots[11]['action'])
        self.assertIn('五卒仍捉对接敌', shots[12]['action'])
        self.assertIn('杜令合', shots[14]['action'])
        self.assertIn('原顾与黄祁留在阵旁独斗', shots[14]['action'])

    def test_matched_references_are_tracked_without_selecting_tasks(self):
        refs = self.data['matched_asset_references']
        self.assertEqual(len(refs), 18)
        self.assertEqual([m['asset_ids'][0] for m in refs[:6]], ['P19', 'S06', 'C06', 'C11', 'C07', 'C58'])
        keys = {m['id'] for m in refs}
        for m in refs:
            self.assertEqual(self.data['source_sha256'][m['path']], m['sha256'])
        for task in self.data['tasks']:
            self.assertNotIn(task['selected_master_id'], keys)
            self.assertFalse(keys & {m['master_id'] for m in task['input_references']})
        self.assertEqual(refs[4]['status'], 'candidate_reference')
        self.assertEqual(refs[1]['candidate_subarea'], 'S06-K')

    def test_user_style_edits_preserve_sources_and_scope(self):
        refs = {m['id']: m for m in self.data['matched_asset_references']}
        masters = {m['id']: m for m in self.data['selected_masters']}
        for row in [masters['portrait-C25'], refs['asset-match-C60-style-01'], refs['asset-match-S01-style-01']]:
            self.assertEqual(row['source_kind'], 'user_attachment_edited')
            self.assertNotEqual(row['sha256'], row['original_sha256'])
            self.assertEqual(hashlib.sha256((production.ROOT / row['original_path']).read_bytes()).hexdigest(), row['original_sha256'])
            self.assertEqual(row['generation']['style_reference_paths'], ['参考/用户媒体/C01-肖像原始参考.jpg'])
            self.assertEqual(row['current_style_anchor']['sha256'], masters['portrait-C01']['sha256'])
            for path, digest in row['generation']['style_reference_sha256'].items():
                self.assertEqual(hashlib.sha256((production.ROOT / path).read_bytes()).hexdigest(), digest)
                self.assertNotEqual(digest, masters['portrait-C01']['sha256'])
            self.assertTrue(row['generation']['prompts'])
            self.assertEqual(row['task_ids'], [])
        self.assertFalse(any('C25' in t['asset_ids'] for t in self.data['tasks']))

    def test_replaced_hero_keeps_execution_provenance_and_rejects_stale_anchor(self):
        registry = production.read(production.ROOT / '资产/媒体/母版登记.json')
        sources = production.validate_media_provenance(production.ROOT, registry)
        self.assertIn('参考/用户媒体/C01-肖像原始参考.jpg', sources)
        self.assertIn('资产/媒体/C01/C01-严格侧面全身.png', sources)
        row = next(r for r in registry['generated_assets'] if r['id'] == 'generated-C06-FACE')
        row['current_style_anchor']['sha256'] = row['generation']['execution_style_references'][0]['sha256']
        with self.assertRaisesRegex(ValueError, '当前视觉锚点已失效'):
            production.validate_media_provenance(production.ROOT, registry)

    def test_counts_and_nonmedia_status(self):
        tasks = self.data['tasks']
        self.assertEqual(len(tasks), 178)
        self.assertEqual(sum(t['method'] == 'MJ' for t in tasks), 162)
        selected = [t for t in tasks if t['media_status'] == 'selected']
        self.assertEqual({t['id'] for t in selected}, {'MB-ENV-S02', 'MB-C06-FULL', 'MB-C06-FACE', 'MB-P12-BASE', 'MB-P17-BASE', 'MB-P18-POUCH', 'MB-P18-BASE', 'MB-P09-BASE', 'MB-C16-FULL-BACK', 'MB-C04-FULL-BACK', 'MB-C03-FULL-BACK', 'MB-C01-FULL-BACK', 'MB-C16-THREEQUARTER', 'MB-C16-PROFILE', 'MB-C04-THREEQUARTER', 'MB-C04-PROFILE', 'MB-C03-THREEQUARTER', 'MB-C01-THREEQUARTER', 'MB-C03-PROFILE', 'MB-C01-PROFILE', 'MB-P06-BASE', 'MB-P07-BASE', 'MB-P03-BASE', 'MB-P04-BASE', 'MB-P10-BOWL', 'MB-P10-WATER', 'MB-P10-BASE', 'MB-P15-BASE', 'MB-C01-DRY', 'MB-P14-BASE', 'MB-P16-BASE', 'MB-C01-FACE', 'MB-C04-FACE', 'MB-C16-FACE', 'MB-C04-FULL', 'MB-C16-FULL', 'MB-C01-FULL', 'MB-C01-FULL-3Q', 'MB-C04-FULL-3Q', 'MB-C16-FULL-3Q', 'MB-C04-COSTUME-DETAIL', 'MB-C17-FACE', 'MB-C17-FULL', 'MB-C20-FACE', 'MB-C20-FULL', 'MB-C03-FACE', 'MB-C03-FULL', 'MB-C03-FULL-3Q', 'MB-C23-FACE', 'MB-C23-FULL', 'MB-P20-BASE', 'MB-WEAPON-BLADE', 'MB-WEAPON-BOW', 'MB-WEAPON-SHIELD', 'MB-P02-BASE', 'MB-BAG-C23', 'MB-P01-BASE', 'MB-P19-BASE'})
        self.assertEqual(selected[0]['media_status'], 'selected')
        candidates = {'POST-P09-BROKEN', 'MB-C60-SILHOUETTE', 'MB-P01-HORSE', 'MB-P01-CABIN', 'MB-C01-COSTUME-DETAIL', 'MB-C16-COSTUME-DETAIL', 'MB-S01-W1-01', 'MB-S01-W1-05'}
        candidates.update({'MB-ENV-S01', 'MB-ENV-S04', 'MB-ENV-S05', 'MB-ENV-S03-HALL', 'MB-ENV-S03-COURT'})
        self.assertEqual({t['id'] for t in tasks if t['media_status'] == 'generated_candidate'}, candidates)
        self.assertTrue(all(t['media_status'] == 'not_generated' for t in tasks if t not in selected and t['id'] not in candidates))
        self.assertEqual(len(self.data['scene_ids']), 16)

    def test_generated_candidate_is_real_but_does_not_unlock_children(self):
        by_id = {t['id']: t for t in self.data['tasks']}
        candidate = next(m for m in self.data['generated_assets'] if m['task_id'] == 'MB-S01-W1-01')
        self.assertEqual(self.data['source_sha256'][candidate['path']], candidate['sha256'])
        self.assertIsNone(by_id['MB-S01-W1-01']['selected_master_id'])
        self.assertIn('MB-S01-W1-01', by_id['POST-WAVES']['unresolved_dependencies'])
        bad = copy.deepcopy(self.data)
        bad['generated_assets'][0]['sha256'] = 'fake'
        with self.assertRaises(ValueError):
            production.validate(bad)

    def test_mapping_and_missing_report_cover_current_sources(self):
        rendered = production.render(self.data)
        report = rendered['../../媒体/母版自动适配编号.md']
        for row in self.data['selected_masters'] + self.data['pending_master_candidates'] + self.data['matched_asset_references']:
            self.assertIn(row['id'], report)
        missing = rendered['前三集实际资产缺口.md']
        for task in self.data['tasks']:
            if task['release_scope'] == 'current_first_three' and task['media_status'] != 'selected':
                self.assertIn('| ' + task['id'] + ' |', missing)

    def test_masked_candidates_do_not_count_as_selected_or_seven_identities(self):
        candidates = self.data['pending_master_candidates']
        self.assertEqual(len(candidates), 7)
        self.assertEqual([m['candidate_asset_ids'] for m in candidates], [['C57'], ['C57'], ['C58'], ['C58'], ['C59'], ['C06'], ['C07']])
        self.assertEqual(len(self.data['selected_masters']), 28)
        ids = {m['id'] for m in candidates}
        for t in self.data['tasks']:
            self.assertFalse(ids & {ref['master_id'] for ref in t['input_references']})
        self.assertEqual(len(self.data['first_wave_instances']), 10)

    def test_masked_candidate_hash_rejected(self):
        original_read = production.read
        def fake_read(path):
            data = original_read(path)
            if path.name == '母版登记.json':
                data['pending_masters'][0]['sha256'] = '0' * 64
            return data
        with patch.object(production, 'read', side_effect=fake_read):
            with self.assertRaisesRegex(ValueError, '校验'):
                production.load_pending_masters()

    def test_ordinary_group_references_bind_distinct_instances(self):
        group = [m for m in self.data['selected_masters'] if m['scope'] == 'ordinary_assassin_group']
        self.assertEqual(len(group), 5)
        self.assertEqual([m['framing'] for m in group], ['full_body', 'feet_cropped', 'feet_cropped', 'full_body', 'full_body'])
        ids = {m['id'] for m in group}
        for t in self.data['tasks']:
            refs = ids & {ref['master_id'] for ref in t['input_references']}
            self.assertEqual(refs, {m['id'] for m in group if t['id'] in m['reference_task_ids']})
        self.assertEqual([m['instance_id'] for m in group], ['S01-W1-04','S01-W1-05','S01-W1-01','S01-W1-08','S01-W1-09'])
        self.assertTrue(all(not m['task_ids'] for m in group))

    def test_ordinary_group_rejects_implicit_cast_or_task_binding(self):
        original_read = production.read
        for field, value in [('asset_ids', ['C57']), ('instance_id', 'S01-W1-01'), ('task_ids', ['MB-S01-W1-01']), ('reference_task_ids', ['MB-C57-RAIN'])]:
            def fake_read(path):
                data = original_read(path)
                if path.name == '母版登记.json':
                    next(m for m in data['masters'] if m['scope'] == 'ordinary_assassin_group')[field] = value
                return data
            with patch.object(production, 'read', side_effect=fake_read):
                with self.assertRaises(ValueError):
                    production.load_masters()

    def test_masked_candidate_cannot_autobind_or_become_selected(self):
        original_read = production.read
        for field, value in [('status', 'selected'), ('task_ids', ['MB-C57-FACE']), ('reference_task_ids', ['MB-C57-RAIN']), ('candidate_asset_ids', ['C60'])]:
            def fake_read(path):
                data = original_read(path)
                if path.name == '母版登记.json':
                    data['pending_masters'][0][field] = value
                return data
            with patch.object(production, 'read', side_effect=fake_read):
                with self.assertRaises(ValueError):
                    production.load_pending_masters()

    def test_dialogue_references_cover_script_once_and_reject_missing_or_repeated_lines(self):
        release = self.data['release_plan']
        resolved = production.resolve_dialogue(release)
        rescue = resolved['GJ-R02-SH022']
        self.assertEqual([row['speaker'] for row in rescue], ['今顾', '韩青', '今顾', '韩青'])
        self.assertEqual(sum(row['characters'] for row in rescue), 30)
        self.assertEqual(resolved['GJ-R03-SH012'][0]['text'], '开门的先问。')
        self.assertEqual(resolved['GJ-R03-SH013'][0]['text'], '夜里收得晚的，回头来。')
        self.assertNotIn('跨集省略的接续状态', {r['speaker'] for rows in resolved.values() for r in rows})
        for mutation in ('missing', 'duplicate', 'overflow', 'reorder'):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(release)
                refs = changed['episodes'][1]['shots'][21]['dialogue_refs']
                if mutation == 'missing':
                    refs.pop()
                elif mutation == 'duplicate':
                    refs.append(copy.deepcopy(refs[-1]))
                elif mutation == 'overflow':
                    refs[0]['turn'] = 999
                else:
                    refs.reverse()
                with self.assertRaisesRegex(ValueError, '对白'):
                    production.resolve_dialogue(changed)

    def test_dialogue_export_reads_current_script_without_copying_it_into_shot_source(self):
        import 对白节奏核对 as dialogue
        original = Path.read_text
        def revised(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path.name == 'GJ-EP01-归京.md':
                value = value.replace('认得他们？', '见过他们？')
            return value
        with patch.object(Path, 'read_text', revised):
            current = dialogue.resolve_dialogue(self.data['release_plan'])
        self.assertEqual(current['GJ-R02-SH022'][0]['text'], '见过他们？')
        rendered = dialogue.render_dialogue(self.data['release_plan']['episodes'][1], current)
        self.assertIn('见过他们？', rendered)
        self.assertNotIn('认得他们？', rendered)

    def test_2d_blocking_rejects_extra_enemy_and_hero_inside_formation(self):
        release = self.data['release_plan']
        plan = production.validate_blocking(release)
        self.assertEqual([len(p['actors']) for p in plan['panels']], [16, 6, 11, 11, 12, 6])
        for mutation in ('extra', 'inside', 'early_formation', 'wrong_exit', 'bad_shot', 'uncleared'):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(release)
                panels = {p['key']: p for p in changed['episodes'][0]['blocking_plan']['panels']}
                if mutation == 'extra':
                    panels['pressed']['actors'].append(dict(id='S01-W1-01', x=900, y=200))
                elif mutation == 'inside':
                    next(a for a in panels['formation']['actors'] if a['id'] == 'C01').update(x=660, y=400)
                elif mutation == 'early_formation':
                    panels['pressed']['formation'] = True
                elif mutation == 'wrong_exit':
                    panels['support']['second_wave_offstage'] = 4
                elif mutation == 'uncleared':
                    panels['cleared']['actors'].append(dict(id='C06', x=900, y=200))
                else:
                    panels['formation']['shot_ids'] = ['GJ-R03-SH001']
                with self.assertRaisesRegex(ValueError, '二维走位'):
                    production.validate_blocking(changed)

    def test_current_face_count_in_entry_points(self):
        for filename in ['README.md', '讨论状态.md', '索引/核验记录.md']:
            content = (ROOT / filename).read_text(encoding='utf-8')
            self.assertNotIn('113张', content)
            self.assertIn('18张', content)

    def test_portrait_sharing_and_later_cast_scope(self):
        masters = {m['id']: m for m in self.data['selected_masters']}
        self.assertEqual(masters['portrait-C01']['asset_ids'], ['C01', 'C02'])
        self.assertEqual(masters['portrait-C27']['task_ids'], [])
        self.assertEqual(masters['portrait-C28']['task_ids'], [])
        self.assertFalse(any(set(t['asset_ids']) & {'C27', 'C28'} for t in self.data['tasks']))

    def test_portrait_and_reviewed_clothing_have_separate_bindings(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        full = tasks['MB-C01-FULL']
        self.assertEqual(full['input_references'][0]['master_id'], 'portrait-C01')
        self.assertEqual(full['status'], 'selected_generated_asset')
        self.assertEqual(full['selected_master_id'], 'generated-C01-FULL')
        self.assertEqual(full['actual_file'], '资产/媒体/C01/C01-全身候选.png')
        back = tasks['MB-C01-FULL-BACK']
        self.assertNotIn('MB-C01-FULL', back['unresolved_dependencies'])
        self.assertEqual(back['status'], 'selected_generated_asset')

    def test_portrait_hash_and_path_rejected(self):
        original_read = production.read
        for field, value in [('sha256', '0' * 64), ('path', '../outside.jpg')]:
            def fake_read(path):
                data = original_read(path)
                if path.name == '母版登记.json':
                    data['masters'][0][field] = value
                return data
            with patch.object(production, 'read', side_effect=fake_read):
                with self.assertRaises(ValueError):
                    production.load_masters()

    def test_unregistered_portrait_selection_rejected(self):
        data = copy.deepcopy(self.data)
        data['selected_masters'][0]['task_ids'] = ['MB-C03-FACE']
        with self.assertRaises(ValueError):
            production.validate(data)

    def test_architecture_selected_without_spatial_completion(self):
        masters = [m for m in self.data['selected_masters'] if m['scope'] == 'architecture_visual']
        self.assertEqual(len(masters), 13)
        for m in masters:
            self.assertEqual(m['task_ids'], [])
            self.assertEqual(m['spatial_status'], 'not_verified')
        tasks = {t['id']: t for t in self.data['tasks']}
        study = tasks['MB-ENV-S04']
        self.assertEqual(study['media_status'], 'generated_candidate')
        self.assertIsNotNone(study['actual_file'])
        self.assertIsNone(study['selected_master_id'])
        self.assertIn('POST-PLAN-COURT', study['unresolved_dependencies'])
        bedroom = tasks['MB-ENV-S05']
        self.assertEqual(bedroom['media_status'], 'generated_candidate')
        self.assertIsNotNone(bedroom['actual_file'])
        self.assertIsNone(bedroom['selected_master_id'])
        self.assertIn('POST-PLAN-COURT', bedroom['unresolved_dependencies'])
        hall = tasks['MB-ENV-S03-HALL']
        self.assertEqual(hall['media_status'], 'generated_candidate')
        self.assertIsNotNone(hall['actual_file'])
        self.assertIsNone(hall['selected_master_id'])
        self.assertIn('POST-PLAN-COURT', hall['unresolved_dependencies'])
        for tid in ['MB-ENV-S03-CORRIDOR']:
            self.assertIsNone(tasks[tid]['actual_file'])
            self.assertIn('POST-PLAN-COURT', tasks[tid]['unresolved_dependencies'])
            self.assertEqual(tasks[tid]['status'], 'awaiting_parent_selection')

    def test_architecture_routing_and_secondary_room_isolation(self):
        refs = {t['id']: {r['master_id'] for r in t['input_references']} for t in self.data['tasks']}
        self.assertIn('architecture-S04-STUDY', refs['MB-ENV-S04'])
        self.assertIn('architecture-S04-STUDY', refs['MB-LIGHT-S04-DAY'])
        self.assertNotIn('architecture-S04-STUDY', refs['MB-ENV-S05'])
        self.assertIn('architecture-S03-OVERVIEW', refs['MB-ENV-S03-W'])
        self.assertFalse(any('architecture-S05-SECONDARY' in values for values in refs.values()))
        for tid in ['MB-ENV-S01', 'MB-ENV-S02', 'MB-ENV-S07', 'MB-C01-FULL']:
            self.assertFalse(any(key.startswith('architecture-') for key in refs[tid]))

    def test_garden_is_not_court_reverse_view(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        garden = next(m for m in self.data['selected_masters'] if m['id'] == 'architecture-S03-GARDEN')
        self.assertEqual(garden['reference_task_ids'], [])
        self.assertEqual(garden['identification']['exact_spatial_mapping'], 'pending')
        for tid in ['MB-ENV-S03-COURT', 'MB-LIGHT-S03-COURT', 'MB-LIGHT-S03-COURT-OVERCAST']:
            refs = {r['master_id'] for r in tasks[tid]['input_references']}
            self.assertIn('architecture-S03-COURT', refs)
            self.assertNotIn('architecture-S03-GARDEN', refs)
            if tid == 'MB-ENV-S03-COURT':
                self.assertIsNotNone(tasks[tid]['actual_file'])
                self.assertEqual(tasks[tid]['media_status'], 'generated_candidate')
                self.assertIsNone(tasks[tid]['selected_master_id'])
            else:
                self.assertIsNone(tasks[tid]['actual_file'])
            self.assertTrue(tasks[tid]['unresolved_dependencies'])

    def test_edited_architecture_keeps_original_and_separate_layout(self):
        edited = [m for m in self.data['selected_masters'] if m.get('source_kind') == 'user_attachment_edited' and m['scope'] == 'architecture_visual']
        self.assertEqual(len(edited), 5)
        self.assertEqual(len({m['original_path'] for m in edited}), 5)
        for m in edited:
            self.assertNotEqual(m['sha256'], m['original_sha256'])
            self.assertEqual(m['reference_task_ids'], ['POST-PLAN-COURT'])
            self.assertEqual(m['style_review']['status'], 'passed_visual_review')
        ids = {m['id'] for m in edited}
        for t in self.data['tasks']:
            if t['method'] == 'MJ':
                self.assertFalse(ids & {r['master_id'] for r in t['input_references']})

    def test_edited_original_hash_rejected(self):
        original_read = production.read
        def fake_read(path):
            data = original_read(path)
            if path.name == '母版登记.json':
                next(m for m in data['masters'] if m.get('source_kind') == 'user_attachment_edited')['original_sha256'] = '0' * 64
            return data
        with patch.object(production, 'read', side_effect=fake_read):
            with self.assertRaisesRegex(ValueError, '原始参考校验'):
                production.load_masters()

    def test_edited_missing_prompt_or_review_rejected(self):
        original_read = production.read
        for field in ['generation', 'style_review']:
            def fake_read(path):
                data = original_read(path)
                if path.name == '母版登记.json':
                    next(m for m in data['masters'] if m.get('source_kind') == 'user_attachment_edited')[field] = {}
                return data
            with patch.object(production, 'read', side_effect=fake_read):
                with self.assertRaises(ValueError):
                    production.load_masters()

    def test_architecture_cannot_complete_task_via_registry(self):
        original_read = production.read
        def fake_read(path):
            data = original_read(path)
            if path.name == '母版登记.json':
                next(m for m in data['masters'] if m['scope'] == 'architecture_visual')['task_ids'] = ['MB-ENV-S04']
            return data
        with patch.object(production, 'read', side_effect=fake_read):
            with self.assertRaises(ValueError):
                production.load_masters()

    def test_architecture_rejects_cross_scene_and_nonspatial_target(self):
        for tid in ['MB-ENV-S01', 'MB-C01-FULL', 'NO-SUCH-TASK']:
            masters = copy.deepcopy(self.data['selected_masters'])
            next(m for m in masters if m['id'] == 'architecture-S04-STUDY')['reference_task_ids'] = [tid]
            with self.assertRaises(ValueError):
                production.bind_masters(copy.deepcopy(self.data['tasks']), masters)

    def test_script_budgets_and_cast(self):
        episodes = json.loads((ROOT / '索引/数据/episodes.json').read_text(encoding='utf-8'))[:3]
        self.assertEqual([len(e['scenes']) for e in episodes], [6, 5, 5])
        self.assertEqual([e['duration_estimate_seconds'] for e in episodes], [375, 180, 180])
        for e in episodes:
            text = (ROOT / e['path']).read_text(encoding='utf-8')
            budgets = [int(x) for x in re.findall(r'^### .*?节奏预算(\d+)秒', text, re.M)]
            self.assertEqual(budgets, [s['duration_estimate_seconds'] for s in e['scenes']])
            self.assertFalse(e['duration_verified'])
            for scene in e['scenes']:
                self.assertTrue(scene['notes'].startswith(f"v1.9节奏预算{scene['duration_estimate_seconds']}秒"))
                self.assertNotIn('v0.7', scene['notes'])
        chars = {c for e in episodes for s in e['scenes'] for c in s['character_ids'] + s['voice_only_ids']}
        self.assertEqual(chars, production.FIRST_CAST)
        self.assertNotIn('C05', {c for e in episodes for s in e['scenes'] for c in s['character_ids']})

    def test_duplicate_rejected(self):
        data = copy.deepcopy(self.data)
        data['tasks'].append(data['tasks'][0])
        with self.assertRaisesRegex(ValueError, '重复'):
            production.validate(data)

    def test_missing_dependency_rejected(self):
        data = copy.deepcopy(self.data)
        data['tasks'][0]['depends_on'].append('MB-MISSING')
        with self.assertRaisesRegex(ValueError, '缺前置'):
            production.validate(data)

    def test_cycle_rejected(self):
        data = copy.deepcopy(self.data)
        data['tasks'][0]['depends_on'].append(data['tasks'][0]['id'])
        with self.assertRaisesRegex(ValueError, '循环'):
            production.validate(data)

    def test_fake_media_rejected(self):
        data = copy.deepcopy(self.data)
        data['tasks'][0]['actual_file'] = 'not-a-real-image.png'
        with self.assertRaisesRegex(ValueError, '媒体'):
            production.validate(data)

    def test_hidden_prop_rejected(self):
        data = copy.deepcopy(self.data)
        data['tasks'][0]['asset_ids'].append('P13')
        with self.assertRaisesRegex(ValueError, '越界'):
            production.validate(data)

    def test_forest_scene_and_continuity(self):
        locations = json.loads((ROOT / '索引/数据/locations.json').read_text(encoding='utf-8'))
        scene = next(s for s in locations if s['id'] == 'S01')
        self.assertEqual(scene['name'], '春泽桥前竹木密林道')
        self.assertTrue((ROOT / scene['path']).is_file())
        self.assertFalse((ROOT / '资产/场景/S01-春泽桥与入城接道.md').exists())
        script = (ROOT / '剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        scene_text = script.split('### 1-1', 1)[1].split('### 1-2', 1)[0]
        for word in ('竹林', '高树', '会车', '前方林口', '有罩', '左肩'):
            self.assertIn(word, scene_text)
        for word in ('小车留在桥头', '驶向石桥', '完整桥面'):
            self.assertNotIn(word, scene_text)
        script3 = (ROOT / '剧集/01-归京/GJ-EP03-门外的人.md').read_text(encoding='utf-8')
        self.assertNotIn('桥上', script3)

    def test_forest_prompt_light_separation(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        forest = tasks['MB-ENV-S01']
        for text in ('dense bamboo', 'woodland trees', 'passing bay', 'forest opening', 'no visible bridge deck', 'no lanterns'):
            self.assertIn(text, forest['prompt_en'])
        self.assertNotIn('an intact traversable deck', forest['prompt_en'])
        self.assertIn('one small enclosed travel lantern', tasks['MB-P01-BASE']['prompt_en'].lower())
        self.assertEqual(forest['first_batch'], 0)
        self.assertEqual(forest['scene_ids'], ['GJ-EP01-SC01'])

    def test_five_assassins_and_external_intervention(self):
        episodes = json.loads((ROOT / '索引/数据/episodes.json').read_text(encoding='utf-8'))
        first = episodes[0]['scenes'][0]
        self.assertEqual(set(first['character_ids']), set(production.VETS) | production.ASSASSINS | {'C01', 'C60'})
        self.assertEqual(len(production.ASSASSINS), 5)
        script = (ROOT / episodes[0]['path']).read_text(encoding='utf-8')
        scene = script.split('### 1-1', 1)[1].split('### 1-2', 1)[0]
        self.assertLess(scene.index('林侧一声'), scene.index('**黄祁：**撤。'))
        self.assertLess(scene.index('**黄祁：**撤。'), scene.index('移动的巡灯'))
        self.assertIn('五卒打退第一波，结阵拦住第二波四名高手', scene)
        self.assertIn('原顾独斗头领败下', scene)
        for old in ('反击擦破黄祁', '罗顺接住他', '右上臂'):
            self.assertNotIn(old, scene)

    def test_mystery_is_faceless_and_retreat_has_no_wound(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        self.assertNotIn('MB-C60-FACE', tasks)
        self.assertIn('face and bare hands fully occluded', tasks['MB-C60-SILHOUETTE']['prompt_en'])
        self.assertIn('POST-PLAN-FOREST', tasks['MB-C60-SILHOUETTE']['depends_on'])
        self.assertIn('without blood stains', tasks['MB-C06-RAIN-POST']['prompt_en'])
        self.assertNotIn('torn area', tasks['MB-C06-RAIN-POST']['prompt_en'])
        for cid in ('C57', 'C58', 'C59'):
            self.assertIn('MB-' + cid + '-RAIN', tasks)

    def test_mystery_face_task_rejected(self):
        data = copy.deepcopy(self.data)
        next(t for t in data['tasks'] if t['id']=='MB-C60-SILHOUETTE')['id'] = 'MB-C60-FULL'
        with self.assertRaisesRegex(ValueError, 'C60'):
            production.validate(data)

    def test_pursuit_no_longer_depends_on_assassin_injury(self):
        outline = (ROOT / '剧集/全剧大纲.md').read_text(encoding='utf-8')
        for old in ('黄祁被归旌阵所伤', '黄祁伤后去向', '罗顺救走黄', '求医住宿'):
            self.assertNotIn(old, outline)
        self.assertIn('守一协缉者', outline)
        self.assertIn('宗师是对守一', (ROOT / '设定/修炼体系与武学谱系.md').read_text(encoding='utf-8'))

    def test_latest_only_policy(self):
        self.assertFalse((ROOT / '档案').exists())
        self.assertFalse((ROOT / '索引/数据/目录迁移.json').exists())
        self.assertFalse((ROOT / '资产/风格探索/2026-09-07/MJ提示词库.json').exists())
        self.assertTrue((ROOT / 'CHANGELOG.md').is_file())
        self.assertTrue((ROOT / 'AGENTS.md').is_file())

    def test_four_riders_one_driver_and_horse_continuity(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        mounted = [t for t in self.data['tasks'] if t['category']=='骑乘绑定']
        self.assertEqual({t['asset_ids'][0] for t in mounted}, {'C16','C17','C20','C23'})
        self.assertEqual(len(mounted), 4)
        self.assertNotIn('MB-C03-MOUNTED', tasks)
        self.assertEqual(tasks['POST-HORSES']['depends_on'], ['MB-P19-BASE'])
        self.assertEqual(tasks['MB-P19-BASE']['scene_ids'], ['GJ-EP01-SC01','GJ-EP01-SC02','GJ-EP01-SC03'])
        for t in mounted:
            self.assertIn('POST-HORSES', t['depends_on'])
            self.assertIn('MB-'+t['asset_ids'][0]+'-ARMOR', t['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        opening=script.split('### 1-1',1)[1].split('### 1-2',1)[0]
        for phrase in ('各骑一匹马','接连下马','五人在地面合阵','清点四匹都在','四匹牵引马仍在'):
            self.assertIn(phrase,opening)
        self.assertNotIn('四名同袍沿车两侧的实地步行',opening)
        self.assertIn('从鞍侧取下顾砚的私人行囊交韩',script)

    def test_four_draft_horses_and_enclosed_carriage(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        cart, team = tasks['MB-P01-BASE'], tasks['MB-P01-HORSE']
        for phrase in ('enclosed', 'four-wheel', 'solid curved roof', 'right-side passenger door', 'external front driver bench', 'no horses'):
            self.assertIn(phrase, cart['prompt_en'])
        self.assertIn('Exactly four ordinary adult brown draft horses abreast', team['prompt_en'])
        self.assertEqual(team['asset_ids'], ['P01'])
        self.assertEqual(team['depends_on'], ['MB-P01-BASE'])
        self.assertEqual(team['scene_ids'], ['GJ-EP01-SC01'])
        self.assertEqual(len([t for t in self.data['tasks'] if t['category']=='骑乘绑定']), 4)
        for key in ('MB-P01-CABIN', 'MB-P01-RAIN-STOP'):
            self.assertIn('MB-P01-BASE', tasks[key]['depends_on'])
        self.assertIn('POST-PLAN-FOREST', tasks['MB-P01-RAIN-STOP']['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        self.assertLess(script.index('打开右侧车门'), script.index('黄祁不跟五卒缠斗'))
        for phrase in ('四匹棕马并列拉车', '六个人、八匹马', '车轮已损', '报出遇袭处和留场车马的位置'):
            self.assertIn(phrase, script)
        card=(ROOT/'资产/道具/P01-四驾封闭豪华马车.md').read_text(encoding='utf-8')
        self.assertIn('P01四匹牵引马＋P19四匹坐骑＝全队八匹马', card)

    def test_light_armor_is_derived_and_scene_scoped(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        used = ['GJ-EP01-SC01', 'GJ-EP01-SC02', 'GJ-EP01-SC03']
        for cid in production.VETS:
            armor = tasks[f'MB-{cid}-ARMOR']
            self.assertEqual(armor['scene_ids'], used)
            self.assertEqual(armor['depends_on'], [f'MB-{cid}-FULL', 'MB-P20-BASE', 'POST-KIT'])
            self.assertIn('light leather armor', armor['prompt_en'])
            self.assertNotIn('light leather armor', tasks[f'MB-{cid}-FULL']['prompt_en'])
            self.assertEqual(tasks[f'MB-{cid}-RAIN']['depends_on'], [f'MB-{cid}-ARMOR'])
        self.assertNotIn('MB-C01-ARMOR', tasks)
        for pid in ('P20', 'P21'):
            self.assertIn(pid, self.data['visible_asset_ids'])
        eps = json.loads((ROOT/'索引/数据/episodes.json').read_text(encoding='utf-8'))[:3]
        for i, scene in enumerate(s for e in eps for s in e['scenes']):
            self.assertEqual('P20' in scene['prop_ids'], i < 3)
            self.assertEqual('P21' in scene['prop_ids'], i < 3 or scene['id'] == 'GJ-EP02-SC04')

    def test_personal_weapons_and_handovers(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        extra = json.loads((production.PACK/'补充任务源.json').read_text(encoding='utf-8'))
        self.assertEqual({g['id'] for g in extra['veteran_gear']}, set(production.VETS))
        for key, cid in [('BOW','C20')]:
            self.assertIn(cid, tasks['MB-WEAPON-'+key]['asset_ids'])
            self.assertIn('P21', tasks['MB-WEAPON-'+key]['asset_ids'])
        self.assertEqual(set(tasks['MB-WEAPON-SHIELD']['asset_ids']), {'C17','P21'})
        self.assertNotIn('P21', tasks['MB-WEAPON-ASSASSIN']['asset_ids'])
        self.assertIn('closed', tasks['MB-WEAPON-BOW']['prompt_en'])
        self.assertIn('POST-KIT', tasks['MB-C20-ARMOR']['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        for phrase in ('韩才腾手用刀', '许看他确已站稳，才退回同伴身边拔刀', '从许手里接回原顾', '五副轻皮内甲陆续取下', '之后都是卸甲便衣'):
            self.assertIn(phrase, script)
        self.assertIn('不穿透皮甲', tasks['POST-FX-COPPER']['acceptance'])

    def test_five_escorts_and_retired_tasks(self):
        self.assertEqual(set(production.VETS), {'C03','C16','C17','C20','C23'})
        removed = {'C18','C19','C21','C22'}
        for task in self.data['tasks']:
            self.assertFalse(removed & set(task['asset_ids']))
        active = {t['id'] for t in self.data['tasks']}
        retired = {t['id'] for t in self.data['retired_tasks']}
        self.assertEqual(len(retired), 23)
        self.assertFalse(active & retired)
        self.assertEqual(len(production.FACE_CAST), 20)

    def test_independent_three_and_five_formations(self):
        text=(ROOT/'设定/五卒与归旌阵.md').read_text(encoding='utf-8')
        for phrase in ('三人一应', '五人归旌', '不需要其余两人在画外供力', '不是更大人数阵的破损版本', '杜与崔可替领'):
            self.assertIn(phrase, text)
        self.assertNotIn('六人“两转”', text)

    def test_luxurious_outerwear_opaque_underarmor(self):
        tasks={t['id']:t for t in self.data['tasks']}
        for cid in production.VETS:
            text=tasks[f'MB-{cid}-ARMOR']['prompt_en']
            for phrase in ('tonal embroidery', 'light leather armor worn under', 'fully opaque outer fabric', 'no exterior leather breastplate'):
                self.assertIn(phrase,text)
        self.assertIn('C17', tasks['POST-AUDIO']['asset_ids'])
        self.assertNotIn('C22', tasks['POST-AUDIO']['asset_ids'])

    def test_first_twenty_are_five_costume_sets(self):
        tasks={t['id']:t for t in self.data['tasks']}
        first=sorted((t for t in tasks.values() if t['first_batch']),key=lambda t:t['first_batch'])
        expected=[f'MB-{cid}-{suffix}' for cid in ('C01','C03','C16','C04','C06')
                  for suffix in ('FULL','FULL-3Q','FULL-BACK','COSTUME-DETAIL')]
        self.assertEqual([t['id'] for t in first],expected)
        for cid in ('C01','C03','C16','C04','C06'):
            self.assertEqual(tasks[f'MB-{cid}-FULL']['depends_on'],[f'MB-{cid}-FACE'])
            self.assertEqual(tasks[f'MB-{cid}-FULL-BACK']['depends_on'],[f'MB-{cid}-FULL'])
            self.assertIn('head-and-shoulders',tasks[f'MB-{cid}-THREEQUARTER']['prompt_en'])
            self.assertIn('full-length',tasks[f'MB-{cid}-FULL-3Q']['prompt_en'])
            self.assertIn('both hands',tasks[f'MB-{cid}-FULL']['prompt_en'])
        bad=copy.deepcopy(self.data)
        next(t for t in bad['tasks'] if t['first_batch']==1)['first_batch']=21
        with self.assertRaisesRegex(ValueError,'首批'):
            production.validate(bad)

    def test_grand_house_and_local_action_geometry(self):
        tasks={t['id']:t for t in self.data['tasks']}
        for key in ('S03-COURT','S03-HALL'):
            body=tasks['MB-ENV-'+key]['prompt_en']
            for phrase in ('gild', 'daylight', 'lamps unlit'):
                self.assertIn(phrase,body)
            for old in ('faded paint','rain basin','modest old'):
                self.assertNotIn(old,body)
        study=tasks['MB-ENV-S04']['prompt_en']
        for phrase in ('expansive','low cabinet directly beneath','compact clear action area','Bare stone','plain bronze mirror'):
            self.assertIn(phrase,study)
        self.assertIn('canopy beds',tasks['MB-ENV-S03-W']['prompt_en'])
        for key,parent in [('S04-DAY','S04'),('S03-COURT-OVERCAST','S03-COURT'),('S03-HALL-OVERCAST','S03-HALL')]:
            self.assertIn('MB-ENV-'+parent,tasks['MB-LIGHT-'+key]['depends_on'])
        self.assertIn('POST-PLAN-COURT',tasks['MB-ENV-S03-CORRIDOR']['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        for phrase in ('西厢五张床','正式架子床','紧邻的窗下矮柜'):
            self.assertIn(phrase,script)
        self.assertNotIn('漏雨旧盆',script)
        outline=(ROOT/'剧集/全剧大纲.md').read_text(encoding='utf-8')
        self.assertIn('整理正式床具和行囊',outline)
        self.assertIn('整理书架、调窗帘',outline)
        self.assertNotIn('约好补窗',outline)

    def test_wide_road_and_finite_household_resources(self):
        tasks={t['id']:t for t in self.data['tasks']}
        for phrase in ('at least eight complete','right-side passing bay','no visible bridge deck'):
            self.assertIn(phrase,tasks['MB-ENV-S01']['prompt_en'])
        self.assertIn('至少八辆',tasks['POST-PLAN-FOREST']['acceptance'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        for phrase in ('八辆马车并行','不横越整条宽官道','六个人、八匹马'):
            self.assertIn(phrase,script)
        world=(ROOT/'设定/世界观与终局.md').read_text(encoding='utf-8')
        for phrase in ('现银和人手始终有限','爵位、食邑和军权已经失去'):
            self.assertIn(phrase,world)
        cfg=json.loads((production.PACK/'视觉任务源.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg['settings']['personalization'],'off_for_baseline_executor_must_verify')

    def test_two_waves_ten_then_five(self):
        waves=self.data['assault_waves']
        self.assertEqual([w['count'] for w in waves],[10,5])
        self.assertEqual(len(set(waves[0]['instance_ids'])),10)
        self.assertEqual(set(waves[1]['character_ids']),production.ASSASSINS)
        tasks={t['id']:t for t in self.data['tasks']}
        for item in self.data['first_wave_instances']:
            task=tasks['MB-'+item['id']]
            self.assertEqual(task['scene_ids'],['GJ-EP01-SC01'])
            self.assertEqual(task['instance_ids'],[item['id']])
            self.assertEqual(task['asset_ids'],['S01'])
            self.assertIn('masked assailant',task['prompt_en'])
            self.assertIn(task['id'],tasks['POST-WAVES']['depends_on'])
        self.assertEqual(len(production.FACE_CAST),20)

    def test_invalid_wave_counts_rejected(self):
        data=copy.deepcopy(self.data)
        data['first_wave_instances'].pop()
        with self.assertRaisesRegex(ValueError,'第一波'):
            production.validate(data)
        data=copy.deepcopy(self.data)
        data['assault_waves'][1]['count']=10
        with self.assertRaisesRegex(ValueError,'两波'):
            production.validate(data)

    def test_wave_handover_wound_and_report_order(self):
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        scene=script.split('### 1-1',1)[1].split('### 1-2',1)[0]
        for a,b in [('十个不同体量的身影形成第一波','第一波十人依次退入侧后林隙'),
                    ('第一波十人依次退入侧后林隙','第二波恰好五人'),
                    ('第二波恰好五人','左肩衣料再添一道擦破'),
                    ('左肩衣料再添一道擦破','林侧一声清越剑鸣')]:
            self.assertLess(scene.index(a),scene.index(b))
        self.assertIn('不能重新以满状态接战',scene)
        self.assertIn('第一波已经退净，不返回战团',scene)
        self.assertIn('第二波恰好五人',scene)
        script3=(ROOT/'剧集/01-归京/GJ-EP03-门外的人.md').read_text(encoding='utf-8')
        self.assertIn('先去车行核。别跟林道那辆混。',script3)
        self.assertIn('没有使两起行动自动并案',script3)


    def test_xianxia_climax_and_recovery_preserve_causality(self):
        first, second, third = self.data['release_plan']['episodes']
        shots = {s['id']: s for e in (first, second, third) for s in e['shots']}
        self.assertLessEqual(shots['GJ-R01-SH001']['end_frame'], 5 * 24)
        self.assertIn('短芒', shots['GJ-R01-SH001']['action'])
        for sid, phrase in [('GJ-R01-SH015', '护罩'), ('GJ-R01-SH019', '护体真气'),
                            ('GJ-R01-SH021', '五道虚影'), ('GJ-R01-SH025', '合眼'),
                            ('GJ-R02-SH001', '睁眼能回应才扶起')]:
            self.assertIn(phrase, shots[sid]['action'])
        self.assertIn('客观全景', shots['GJ-R01-SH021']['action'])
        self.assertIn('无新血伤', shots['GJ-R01-SH022']['action'])
        self.assertIn('不拥有林中主观记忆', shots['GJ-R02-SH022']['blocking_continuity'])
        # Retimed scene totals must agree with the authored scene ledger, not only episode totals.
        totals = {}
        for e in (first, second, third):
            for shot in e['shots']:
                sid = shot['scene_id']
                totals[sid] = totals.get(sid, 0) + shot['end_frame'] - shot['start_frame']
        ledger = json.loads((ROOT/'索引/数据/episodes.json').read_text(encoding='utf-8'))
        for ep in ledger:
            for scene in ep.get('scenes', []):
                if scene['id'] in totals:
                    self.assertEqual(totals[scene['id']], scene['duration_estimate_seconds'] * 24)
        script = (ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        first_scene = script.split('### 1-1', 1)[1].split('<a id="rel02">', 1)[0]
        self.assertLess(first_scene.index('气膜先散'), first_scene.index('林侧一声清越剑鸣'))
        self.assertLess(first_scene.index('剑气化形'), first_scene.index('**黄祁：**撤。'))
        self.assertLess(first_scene.index('**黄祁：**撤。'), first_scene.index('彻底昏厥'))
        tasks = {t['id']: t for t in self.data['tasks']}
        self.assertIn('客观全景证明退敌', tasks['POST-FX-COPPER']['acceptance'])
        self.assertIn('伤疲昏厥不等于返府意识更替', tasks['POST-ACTION']['acceptance'])

    def test_release_split_preserves_stable_scene_ids(self):
        releases = self.data['release_plan']['episodes']
        self.assertEqual([e['duration_seconds'] for e in releases], [180, 195, 180])
        self.assertEqual(sum(e['duration_seconds'] for e in releases[:2]), 375)
        self.assertEqual([len(e['scene_ids']) for e in releases], [1, 5, 5])
        self.assertEqual([len(e['shots']) for e in releases], [25, 24, 22])
        self.assertTrue(all(not s.startswith('GJ-EP03') for e in releases for s in e['scene_ids']))
        self.assertIn('GJ-EP03-SC05', self.data['scene_ids'])

    def test_release_timeline_gaps_and_duplicate_ids_rejected(self):
        data = copy.deepcopy(self.data)
        data['release_plan']['episodes'][0]['shots'][1]['start_frame'] += 1
        with self.assertRaisesRegex(ValueError, '帧窗'):
            production.validate(data)
        data = copy.deepcopy(self.data)
        shots = data['release_plan']['episodes'][0]['shots']
        shots[1]['id'] = shots[0]['id']
        with self.assertRaisesRegex(ValueError, '分镜编号'):
            production.validate(data)

    def test_forest_subshots_cover_parent_windows_and_export(self):
        release = self.data['release_plan']
        parents = [s for e in release['episodes'] for s in e['shots'] if 'subshots' in s]
        self.assertEqual({s['id'] for s in parents},
                         {f'GJ-R01-SH{n:03}' for n in (8, 15, 17, 18, 19, 20, 21, 22)})
        self.assertEqual(sum(len(s['subshots']) for s in parents), 19)
        rendered = production.render_release(release)
        for parent in parents:
            children = parent['subshots']
            self.assertEqual(children[0]['start_frame'], parent['start_frame'])
            self.assertEqual(children[-1]['end_frame'], parent['end_frame'])
            self.assertEqual(sum(c['end_frame'] - c['start_frame'] for c in children),
                             parent['end_frame'] - parent['start_frame'])
            for child in children:
                self.assertIn(child['id'], rendered)
                for key in ('state_in', 'action', 'camera', 'environment', 'sound', 'state_out', 'cut_cue'):
                    self.assertIn(child[key], rendered)
        climax = next(s for s in parents if s['id'] == 'GJ-R01-SH021')
        self.assertEqual([c['viewpoint'] for c in climax['subshots']],
                         ['subjective', 'objective', 'objective'])
        self.assertEqual(climax['subshots'][0]['subjective_owner'], 'C01')
        self.assertIn('五名刺客均退开', climax['subshots'][1]['state_out'])

    def test_invalid_subshot_windows_ownership_and_media_rejected(self):
        mutations = {
            'gap': lambda p: p['subshots'][1].update(start_frame=p['subshots'][1]['start_frame'] + 1),
            'overlap': lambda p: p['subshots'][1].update(start_frame=p['subshots'][1]['start_frame'] - 1),
            'overflow': lambda p: p['subshots'][-1].update(end_frame=p['end_frame'] + 1),
            'unfilled': lambda p: p['subshots'][-1].update(end_frame=p['end_frame'] - 1),
            'fraction': lambda p: p['subshots'][0].update(start_frame=float(p['start_frame'])),
            'duplicate': lambda p: p['subshots'][1].update(id=p['subshots'][0]['id']),
            'foreign_parent': lambda p: p['subshots'][0].update(parent_id='GJ-R02-SH001'),
            'foreign_id': lambda p: p['subshots'][0].update(id='GJ-R02-SH001-A'),
            'missing_link': lambda p: p['subshots'][1].update(depends_on=[]),
            'claimed_media': lambda p: p['subshots'][0].update(media_status='generated'),
            'wrong_memory': lambda p: p['subshots'][0].update(subjective_owner='C02'),
            'empty_track': lambda p: p['subshots'][0].update(environment=''),
            'invalid_view': lambda p: p['subshots'][0].update(viewpoint='omniscient'),
            'empty_list': lambda p: p.update(subshots=[]),
        }
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                data = copy.deepcopy(self.data)
                parent = next(s for s in data['release_plan']['episodes'][0]['shots']
                              if s['id'] == 'GJ-R01-SH021')
                mutate(parent)
                with self.assertRaises(ValueError):
                    production.validate(data)

    def test_release_scope_and_scene_metadata_rejected(self):
        data = copy.deepcopy(self.data)
        data['scene_release_map']['GJ-EP01-SC02'] = 'GJ-R01'
        with self.assertRaisesRegex(ValueError, '映射失配'):
            production.validate(data)
        data = copy.deepcopy(self.data)
        data['release_plan']['episodes'][2]['scene_ids'].append('GJ-EP03-SC01')
        with self.assertRaisesRegex(ValueError, '映射失配'):
            production.validate(data)

    def test_followup_reserve_does_not_advance_faces(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for key in ('MB-C12-FACE', 'MB-C13-FACE', 'POST-P06-STATE'):
            self.assertEqual(tasks[key]['release_episode_ids'], [])
            self.assertEqual(tasks[key]['release_scope'], 'followup_reserve')
        current = [t for t in tasks.values() if t['release_scope'] == 'current_first_three']
        self.assertEqual(len(current), 166)
        self.assertEqual(sum(t['method'] == 'MJ' for t in current), 151)
        self.assertEqual(sum(t['id'].endswith('-FACE') for t in current), 18)
        self.assertIn('POST-WAVES', tasks['POST-RHYTHM3']['depends_on'])

    def test_release_third_hook_and_secret_preserved(self):
        script = (ROOT / '剧集/01-归京/GJ-EP02-先过今夜.md').read_text(encoding='utf-8')
        for phrase in ('发行第3集', '送你回来，不是关你回来', '灯能留么？我有点怕', '门仍未开', '王寿，门外画外声'):
            self.assertIn(phrase, script)
        self.assertNotIn('半步也算走过了', script)
        shots = self.data['release_plan']['episodes'][2]['shots']
        self.assertIn('禁止切门外正脸', shots[-2]['camera'])
        self.assertIn('核验', shots[-1]['end_state'])
        data = copy.deepcopy(self.data)
        data['release_plan']['episodes'][0]['shots'][0]['media_status'] = 'generated'
        with self.assertRaisesRegex(ValueError, '媒体状态'):
            production.validate(data)


    def test_ancestral_mansion_style_propagates_without_scope_leak(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for task in tasks.values():
            if task['category'] in ('空间', '空间光态') and set(task['asset_ids']) & {'S03', 'S04', 'S05', 'S06'}:
                for phrase in ('prestigious old Chinese lineage', 'massive timber columns', 'deep tiled eaves', 'No modern New Chinese villa'):
                    self.assertIn(phrase, task['prompt_en'])
        for key in ('MB-ENV-S01', 'MB-ENV-S02', 'MB-ENV-S07', 'MB-C01-FACE'):
            self.assertNotIn('prestigious old Chinese lineage', tasks[key]['prompt_en'])

    def test_bright_neutral_morning_keeps_legacy_light_ids(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for key in ('MB-LIGHT-S03-COURT-OVERCAST', 'MB-LIGHT-S03-HALL-OVERCAST', 'MB-LIGHT-S05', 'MB-ENV-S03-W', 'MB-ENV-S06-WELL'):
            text = tasks[key]['prompt_en']
            for phrase in ('Bright clear winter morning after rain', 'no amber or yellow cast', 'lamps unlit'):
                self.assertIn(phrase, text)
            self.assertNotIn('overcast', text.lower())
        for key in ('MB-ENV-S03-COURT', 'MB-ENV-S03-HALL', 'MB-LIGHT-S04-DAY'):
            self.assertIn('Bright natural neutral-white daylight', tasks[key]['prompt_en'])
        for key in ('MB-ENV-S04', 'MB-ENV-S05', 'MB-ENV-S06-K', 'MB-ENV-S03-CORRIDOR'):
            self.assertIn('night', tasks[key]['prompt_en'].lower())
            self.assertNotIn('Bright clear winter morning', tasks[key]['prompt_en'])

    def test_heavy_furniture_preserves_movable_and_reach_constraints(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        small = tasks['MB-S03-TABLE']['prompt_en']
        self.assertIn('movable by one adult', small)
        self.assertIn('thick tabletop edge', small)
        large = tasks['MB-S03-LARGE']['prompt_en']
        self.assertIn('fixed heavy', large)
        self.assertIn('stout structural legs', large)
        self.assertIn('low cabinet directly beneath', tasks['MB-ENV-S04']['prompt_en'])
        self.assertIn('compact clear action area', tasks['MB-ENV-S04']['prompt_en'])
        self.assertIn('five-bed plan', tasks['MB-ENV-S03-W']['prompt_en'])
        self.assertIn('familiar bed height', tasks['MB-ENV-S05']['prompt_en'])

    def test_architecture_revision_preserves_release_budgets(self):
        plan = self.data['release_plan']
        self.assertIn('非现代新中式', (ROOT / '资产/场景/S03-顾府门院前厅与西厢.md').read_text(encoding='utf-8').replace('禁止现代新中式', '非现代新中式'))
        self.assertEqual([e['duration_seconds'] for e in plan['episodes']], [180, 195, 180])
        self.assertEqual([len(e['shots']) for e in plan['episodes']], [25, 24, 22])
        self.assertEqual(plan['architecture_binding']['scope'], ['S03', 'S04', 'S05', 'S06'])
        script = (ROOT / '剧集/01-归京/GJ-EP02-先过今夜.md').read_text(encoding='utf-8')
        self.assertIn('雨停初晴', script)
        self.assertIn('白墙不泛暖黄', script)


    def test_portrait_source_missing_fields_and_duplicate_rejected(self):
        cfg = production.read(production.PACK / '视觉任务源.json')
        for key in ('studio_background_en', 'portrait_light_en', 'grooming_en', 'costume_en'):
            broken = copy.deepcopy(cfg)
            broken['characters'][0][key] = ' '
            with self.assertRaisesRegex(ValueError, '缺人物摄影或衣装字段'):
                production.validate_visual_source(broken)
        broken = copy.deepcopy(cfg)
        broken['characters'].append(broken['characters'][0])
        with self.assertRaisesRegex(ValueError, '重复人物'):
            production.validate_visual_source(broken)

    def test_studio_background_and_crop_propagation(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        cfg = production.read(production.PACK / '视觉任务源.json')
        self.assertGreaterEqual(len({c['studio_background_en'] for c in cfg['characters']}), 4)
        for c in cfg['characters']:
            for suffix in ('FACE', 'FULL'):
                body = tasks[f"MB-{c['id']}-{suffix}"]['prompt_en']
                self.assertIn(c['studio_background_en'], body)
                self.assertIn(c['portrait_light_en'], body)
                self.assertIn(c['grooming_en'], body)
            self.assertIn('full topknot included', tasks[f"MB-{c['id']}-FACE"]['prompt_en'])
        self.assertNotIn('natural catchlights', tasks['MB-C01-FULL-BACK']['prompt_en'])
        self.assertNotIn('full topknot included', tasks['MB-C01-COSTUME-DETAIL']['prompt_en'])
        self.assertNotIn('defined cheekbones', tasks['MB-C01-FULL-BACK']['prompt_en'])
        self.assertNotIn('natural skin', tasks['MB-C01-COSTUME-DETAIL']['prompt_en'].lower())
        self.assertNotIn('black hair', tasks['MB-C01-COSTUME-DETAIL']['prompt_en'])

    def test_face_without_wounds_preserves_shoulder_and_change(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for key in ('C01-FACE', 'C01-FULL', 'C01-RAIN-PRE', 'C01-RAIN-POST', 'C01-DRY', 'C02-FEAR', 'C02-FOCUS'):
            self.assertIn('uninjured face without scars, cuts or blood', tasks['MB-' + key]['prompt_en'])
        self.assertIn('fresh abrasion tear', tasks['MB-C01-RAIN-POST']['prompt_en'])
        self.assertIn('own left shoulder', tasks['MB-C01-RAIN-POST']['prompt_en'])
        for key in ('C01-DRY', 'C02-FEAR', 'C02-FOCUS'):
            body = tasks['MB-' + key]['prompt_en']
            self.assertIn('opaque fine cotton', body)
            self.assertIn('medium stone-green gray', body)
            self.assertNotIn('ink-teal and blackened ink travel martial robe', body)

    def test_material_layers_reach_rain_and_detail_tasks(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        for cid, phrase in {'C03': 'tea-white silk collar', 'C16': 'chestnut-brown silk-wool',
                            'C17': 'stone-gray cotton', 'C20': 'bamboo-green inner layer',
                            'C23': 'celadon-gray cotton'}.items():
            for suffix in ('FULL', 'ARMOR', 'RAIN'):
                self.assertIn(phrase, tasks[f'MB-{cid}-{suffix}']['prompt_en'])
        self.assertIn('cotton padding layer', tasks['MB-C04-COSTUME-DETAIL']['prompt_en'])
        self.assertIn('silk-twill', tasks['MB-P14-BASE']['prompt_en'])
        for suffix in ('FULL', 'COSTUME-DETAIL', 'RAIN-PRE', 'RAIN-POST'):
            prompt = tasks[f'MB-C01-{suffix}']['prompt_en']
            self.assertIn('mountain and cloud landscape weave', prompt)
            self.assertIn('two matching antique silver cloud chest clasps', prompt)
            self.assertNotIn('dark-gold flowing geometric', prompt)

    def test_portrait_language_does_not_pollute_empty_assets(self):
        for task in self.data['tasks']:
            if task['category'] in ('空间', '空间光态', '道具'):
                for phrase in ('Natural skin texture', 'soft face light', 'natural catchlights', 'studio backdrop'):
                    self.assertNotIn(phrase, task['prompt_en'])
        bloom = next(t for t in self.data['tasks'] if t['id'] == 'MB-TEST-C01-BLOOM')
        self.assertEqual(bloom['phase'], 'OPTIONAL')
        self.assertIn('No golden halo', bloom['prompt_en'])
        self.assertFalse(any(bloom['id'] in t['depends_on'] for t in self.data['tasks']))

    def test_wardrobe_sources_and_heroines_remain_future(self):
        registry = production.read(ROOT / '索引/数据/characters.json')
        for cid, age, color in [('C25', '二十', '暖杏'), ('C27', '二十二', '青瓷'), ('C28', '十九', '杏白')]:
            c = next(c for c in registry if c['id'] == cid)
            card = (ROOT / c['path']).read_text(encoding='utf-8')
            self.assertIn(age, card)
            self.assertIn(color, c['visual_design']['服装与色彩'])
            self.assertIn('资产/角色服装系统.md', c['source_paths'])
            self.assertFalse(any(cid in t['asset_ids'] for t in self.data['tasks']))
        self.assertIn('资产/角色服装系统.md', self.data['source_sha256'])
        self.assertEqual(len(self.data['release_plan']['episodes'][0]['shots']), 25)


if __name__ == '__main__':
    unittest.main()
