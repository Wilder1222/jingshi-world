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
        self.assertEqual(len(tasks), 131)
        self.assertEqual(sum(t['method'] == 'MJ' for t in tasks), 120)
        self.assertTrue(all(t['actual_file'] is None for t in tasks))
        self.assertEqual(len(self.data['scene_ids']), 16)

    def test_script_budgets_and_cast(self):
        episodes = json.loads((ROOT / '索引/数据/episodes.json').read_text(encoding='utf-8'))[:3]
        self.assertEqual([len(e['scenes']) for e in episodes], [6, 5, 5])
        self.assertEqual([e['duration_estimate_seconds'] for e in episodes], [300, 270, 285])
        for e in episodes:
            text = (ROOT / e['path']).read_text(encoding='utf-8')
            budgets = [int(x) for x in re.findall(r'^### .*?节奏预算(\d+)秒', text, re.M)]
            self.assertEqual(budgets, [s['duration_estimate_seconds'] for s in e['scenes']])
            self.assertFalse(e['duration_verified'])
            for scene in e['scenes']:
                self.assertTrue(scene['notes'].startswith(f"v1.9节奏预算{scene['duration_estimate_seconds']}秒"))
                self.assertNotIn('v0.7', scene['notes'])
        chars = {c for e in episodes for s in e['scenes'] for c in s['character_ids'] + s['voice_only_ids']}
        self.assertEqual(chars, {f'C{i:02}' for i in range(1, 24)})
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

    def test_latest_only_policy(self):
        self.assertFalse((ROOT / '档案').exists())
        self.assertFalse((ROOT / '索引/数据/目录迁移.json').exists())
        self.assertFalse((ROOT / '资产/风格探索/2026-09-07/MJ提示词库.json').exists())
        self.assertTrue((ROOT / 'CHANGELOG.md').is_file())
        self.assertTrue((ROOT / 'AGENTS.md').is_file())


if __name__ == '__main__':
    unittest.main()
