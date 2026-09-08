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
        self.assertEqual(len(tasks), 167)
        self.assertEqual(sum(t['method'] == 'MJ' for t in tasks), 153)
        self.assertTrue(all(t['actual_file'] is None for t in tasks))
        self.assertEqual(len(self.data['scene_ids']), 16)

    def test_script_budgets_and_cast(self):
        episodes = json.loads((ROOT / '索引/数据/episodes.json').read_text(encoding='utf-8'))[:3]
        self.assertEqual([len(e['scenes']) for e in episodes], [6, 5, 5])
        self.assertEqual([e['duration_estimate_seconds'] for e in episodes], [330, 270, 285])
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
        self.assertIn('one small enclosed travel lantern', tasks['MB-P01-BASE']['prompt_en'])
        self.assertEqual(forest['first_batch'], 8)
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
        for old in ('黄祁被九阵所伤', '黄祁伤后去向', '罗顺救走黄', '求医住宿'):
            self.assertNotIn(old, outline)
        self.assertIn('守一协缉者', outline)
        self.assertIn('宗师是对守一', (ROOT / '设定/修炼体系与武学谱系.md').read_text(encoding='utf-8'))

    def test_latest_only_policy(self):
        self.assertFalse((ROOT / '档案').exists())
        self.assertFalse((ROOT / '索引/数据/目录迁移.json').exists())
        self.assertFalse((ROOT / '资产/风格探索/2026-09-07/MJ提示词库.json').exists())
        self.assertTrue((ROOT / 'CHANGELOG.md').is_file())
        self.assertTrue((ROOT / 'AGENTS.md').is_file())

    def test_eight_riders_one_driver_and_horse_continuity(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        mounted = [t for t in self.data['tasks'] if t['category']=='骑乘绑定']
        self.assertEqual({t['asset_ids'][0] for t in mounted}, {f'C{i:02}' for i in range(16,24)})
        self.assertEqual(len(mounted), 8)
        self.assertNotIn('MB-C03-MOUNTED', tasks)
        self.assertEqual(tasks['POST-HORSES']['depends_on'], ['MB-P19-BASE'])
        self.assertEqual(tasks['MB-P19-BASE']['scene_ids'], ['GJ-EP01-SC01','GJ-EP01-SC02','GJ-EP01-SC03'])
        for t in mounted:
            self.assertIn('POST-HORSES', t['depends_on'])
            self.assertIn('MB-'+t['asset_ids'][0]+'-ARMOR', t['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        opening=script.split('### 1-1',1)[1].split('### 1-2',1)[0]
        for phrase in ('各骑一匹马','接连下马','九人在地面合阵','清点八匹都在','两匹牵引马留在'):
            self.assertIn(phrase,opening)
        self.assertNotIn('八名同袍沿车两侧的实地步行',opening)
        self.assertIn('从鞍侧取下顾砚的私人行囊交韩',script)

    def test_two_draft_horses_are_separate_from_eight_mounts(self):
        tasks = {t['id']: t for t in self.data['tasks']}
        cart = tasks['MB-P01-BASE']
        team = tasks['MB-P01-HORSE']
        self.assertIn('one central draw pole', cart['prompt_en'])
        self.assertIn('two-horse team', cart['prompt_en'])
        self.assertIn('no horses', cart['prompt_en'])
        self.assertIn('Exactly two ordinary adult brown draft horses', team['prompt_en'])
        self.assertIn('side by side', team['prompt_en'])
        self.assertEqual(team['asset_ids'], ['P01'])
        self.assertEqual(team['depends_on'], ['MB-P01-BASE'])
        self.assertEqual(team['scene_ids'], ['GJ-EP01-SC01'])
        self.assertIn('One ordinary adult bay riding horse', tasks['MB-P19-BASE']['prompt_en'])
        self.assertEqual(len([t for t in self.data['tasks'] if t['category']=='骑乘绑定']), 8)
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        self.assertIn('两匹棕马并排拉车', script)
        self.assertIn('小车与两匹牵引马留在', script)
        card=(ROOT/'资产/道具/P01-敞棚小车.md').read_text(encoding='utf-8')
        self.assertIn('P01两匹牵引马＋P19八匹坐骑＝全队十匹马', card)
        for t in self.data['tasks']:
            for old in ('一匹牵引马', '单匹牵引马', '单匹拉车马', '全队共九马', '车、九匹马'):
                self.assertNotIn(old, t['acceptance'])

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
        for key, cid in [('LONG-BLADE','C18'), ('SPEAR','C19'), ('BOW','C20'), ('SHORT-SPEAR','C21')]:
            self.assertIn(cid, tasks['MB-WEAPON-'+key]['asset_ids'])
            self.assertIn('P21', tasks['MB-WEAPON-'+key]['asset_ids'])
        self.assertEqual(set(tasks['MB-WEAPON-SHIELD']['asset_ids']), {'C17','C22','P21'})
        self.assertNotIn('P21', tasks['MB-WEAPON-ASSASSIN']['asset_ids'])
        self.assertIn('closed', tasks['MB-WEAPON-BOW']['prompt_en'])
        self.assertIn('POST-KIT', tasks['MB-C20-ARMOR']['depends_on'])
        script=(ROOT/'剧集/01-归京/GJ-EP01-归京.md').read_text(encoding='utf-8')
        for phrase in ('韩才腾手用刀', '原顾此时还由段扶着', '从段手里接回原顾', '九副轻皮甲陆续解下', '之后都是卸甲便衣'):
            self.assertIn(phrase, script)
        self.assertIn('不穿透皮甲', tasks['POST-FX-COPPER']['acceptance'])


if __name__ == '__main__':
    unittest.main()
