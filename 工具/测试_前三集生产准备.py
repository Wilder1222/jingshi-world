"""制作清单的结构回归；不冒充视觉质量或台词计时测试。"""
import copy
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('production', ROOT / '工具/前三集生产准备.py')
production = importlib.util.module_from_spec(spec)
spec.loader.exec_module(production)


class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = production.build_data()

    def test_counts_and_nonmedia_status(self):
        tasks = self.data['tasks']
        self.assertEqual(len(tasks), 178)
        self.assertEqual(sum(t['method'] == 'MJ' for t in tasks), 162)
        self.assertTrue(all(t['actual_file'] is None for t in tasks))
        self.assertEqual(len(self.data['scene_ids']), 16)

    def test_script_budgets_and_cast(self):
        episodes = json.loads((ROOT / '索引/数据/episodes.json').read_text(encoding='utf-8'))[:3]
        self.assertEqual([len(e['scenes']) for e in episodes], [6, 5, 5])
        self.assertEqual([e['duration_estimate_seconds'] for e in episodes], [375, 180, 285])
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
        self.assertIn('却没有赢下交锋', scene)
        for old in ('反击擦破黄祁', '罗顺接住他', '两名刺客', '右上臂'):
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
        self.assertLess(script.index('打开右侧车门'), script.index('黄祁来得太快'))
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
            self.assertEqual('P21' in scene['prop_ids'], i < 3)

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
        for phrase in ('韩才腾手用刀', '原顾此时还由许扶着', '从许手里接回原顾', '五副轻皮内甲陆续取下', '之后都是卸甲便衣'):
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
        for phrase in ('八辆马车并行','没有横越整幅官道','六个人、八匹马'):
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
                    ('左肩衣料再添一道擦破','林侧一声极短的金铁轻鸣')]:
            self.assertLess(scene.index(a),scene.index(b))
        self.assertIn('不能重新以满状态接战',scene)
        self.assertIn('两拨。先十个，后五个',script)
        script3=(ROOT/'剧集/01-归京/GJ-EP03-门外的人.md').read_text(encoding='utf-8')
        self.assertIn('两拨人要杀我',script3)


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


if __name__ == '__main__':
    unittest.main()
