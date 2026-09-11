"""校验必要资产包的真实文件，不把表演板计作视频完成。"""
import hashlib
import json


def load_packages(root):
    registry = '资产/媒体/必要资产包登记.json'
    data = json.loads((root / registry).read_text(encoding='utf-8'))
    paths = {registry, '工具/必要资产包.py', '资产/生产准备/前三集-v1.9/必要资产与分镜设计.md'}
    seen = set()
    for item in data['items']:
        if item['id'] in seen or item['status'] not in {'candidate', 'selected'}:
            raise ValueError('必要包编号重复或状态无效')
        seen.add(item['id'])
        if not item['generation']['prompt'] or not item['generation']['input_references']:
            raise ValueError('必要包缺少实际生成依据')
        if item['status'] == 'selected' and (not item.get('selected_by') or not item['review'].get('scope')):
            raise ValueError('必要包已选项缺验收范围')
        if item['kind'] == 'expression_grid' and len(item.get('panel_order', [])) != 9:
            raise ValueError('表情板必须登记九格顺序')
        for ref in [item] + item['generation']['input_references']:
            target = (root / ref['path']).resolve()
            if not target.is_relative_to((root / '资产/媒体').resolve()) or not target.is_file():
                raise ValueError('必要包媒体文件不存在或越界')
            if hashlib.sha256(target.read_bytes()).hexdigest() != ref['sha256']:
                raise ValueError('必要包媒体哈希失配：' + ref['path'])
            paths.add(ref['path'])
    return data['items'], paths
