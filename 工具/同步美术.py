"""从角色和场景卡同步当前美术文字到检索源表；不改变剧情与出镜登记。"""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "资产/美术风格与造型总则.md"
FIELDS = ("视觉气质", "骨相与仪态", "服装与色彩", "连续性")


def section(text, heading):
    match = re.search(r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |<!-- AUTO:|\Z)", text, re.M | re.S)
    if not match:
        raise ValueError(f"缺少章节：{heading}")
    return match.group(1).strip()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    character_path = ROOT / "索引/数据/characters.json"
    location_path = ROOT / "索引/数据/locations.json"
    characters = json.loads(character_path.read_text(encoding="utf-8"))
    locations = json.loads(location_path.read_text(encoding="utf-8"))
    card_updates = []
    for item in characters:
        path = ROOT / item["path"]
        text = path.read_text(encoding="utf-8")
        block = section(text, "造型设计 v0.8")
        pairs = re.findall(r"^- \*\*([^：]+)：\*\*(.+)$", block, re.M)
        design = {key: value.strip() for key, value in pairs}
        if len(pairs) != len(FIELDS) or set(design) != set(FIELDS):
            raise ValueError(f"{item['id']}：造型字段须为四项且不重复")
        appearance = re.search(r"^- \*\*形象说明：\*\*(.+)$", text, re.M)
        if not appearance:
            raise ValueError(f"{item['id']}：缺少形象说明")
        item["visual_design"] = {"version": "v0.8", **design}
        item["appearance_note"] = appearance.group(1).strip()
        added_tags = ["美术v0.8", "独立造型"]
        if item["id"] not in ("C05", "C56"):
            added_tags.append("高端古装")
        item["tags"] = list(dict.fromkeys([*item["tags"], *added_tags]))
        item["source_paths"] = list(dict.fromkeys([*item["source_paths"], SOURCE]))
        updated, count = re.subn(r"^- \*\*分类／标签：\*\*.*$", lambda _: "- **分类／标签：**" + "、".join(item["tags"]), text, flags=re.M)
        if count != 1:
            raise ValueError(f"{item['id']}：分类标签行数量异常")
        card_updates.append((path, updated))
    for item in locations:
        text = (ROOT / item["path"]).read_text(encoding="utf-8")
        item["art_direction"] = section(text, "美术执行 v0.8").split("\n\n", 1)[0]
        item["source_paths"] = list(dict.fromkeys([*item["source_paths"], SOURCE]))
    # 全部读取与字段检查成功后才写入，避免缺卡时只同步部分角色。
    for path, text in card_updates:
        path.write_text(text, encoding="utf-8")
    for path, data in ((character_path, characters), (location_path, locations)):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"美术已同步：{len(characters)}张角色卡、{len(locations)}张场景卡；出镜与身份登记保持。")


if __name__ == "__main__":
    main()
