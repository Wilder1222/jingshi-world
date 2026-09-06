"""一次性目录整理。逐个移动文件，保留旧新路径映射；不会删除文件。"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "索引" / "数据" / "目录迁移.json"
TARGETS = {
    "07": "研究/热门作品研究与创作启示.md",
    "10": "设定/世界观与终局.md",
    "14": "设定/归藏山与师门.md",
    "15": "设定/群像与周边关系.md",
    "16": "剧集/全剧大纲.md",
    "17": "设定/九卒与归旌阵.md",
    "18": "设定/九卒长线与日常.md",
}


def local(path):
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"目标越出工作区：{path}")
    return resolved


def write(path, value):
    local(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if MAPPING.exists():
        print("迁移记录已存在；不重复移动。后续请用资料管理.py。")
        return
    rows = []
    for path in sorted((ROOT / "docs").rglob("*.md")):
        key = path.name[:2]
        if path.parent.name == "research":
            dest = "研究/" + path.name
        elif key in TARGETS:
            dest = TARGETS[key]
        else:
            version = "v0.1" if int(key) <= 6 else "v0.2" if int(key) <= 9 else "v0.3" if int(key) <= 13 else "v0.5"
            dest = f"档案/版本快照/{version}/{path.name}"
        rows.append({"old_path": path.relative_to(ROOT).as_posix(), "new_path": dest, "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for path in sorted((ROOT / "reference").glob("*.md")):
        rows.append({"old_path": path.relative_to(ROOT).as_posix(), "new_path": "参考/" + path.name, "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if not rows:
        raise ValueError("未找到待整理原稿")
    for row in rows:
        src, dest = local(ROOT / row["old_path"]), local(ROOT / row["new_path"])
        if not src.is_file() or dest.exists():
            raise ValueError(f"源文件缺失或目标已存在：{row}")
    if not args.apply:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    # 所有路径在移动前一次性核验；每次仅移动一个明确文件，不递归移动目录。
    for row in rows:
        src, dest = local(ROOT / row["old_path"]), local(ROOT / row["new_path"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
    mapping = {row["old_path"]: row["new_path"] for row in rows}
    inverse = {row["new_path"]: row["old_path"] for row in rows}
    count = 0
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        old_base = (ROOT / inverse.get(rel, rel)).parent
        content = path.read_text(encoding="utf-8-sig")

        def replace(match):
            nonlocal count
            raw = match.group(2).strip().strip("<>")
            if re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I) or raw.startswith("#"):
                return match.group(0)
            target, sep, anchor = raw.partition("#")
            source = (old_base / unquote(target)).resolve()
            if not source.is_relative_to(ROOT):
                return match.group(0)
            source_rel = source.relative_to(ROOT).as_posix()
            final = ROOT / mapping.get(source_rel, source_rel)
            new_target = os.path.relpath(final, path.parent).replace("\\", "/") + (sep + anchor if sep else "")
            if new_target == raw:
                return match.group(0)
            count += 1
            return match.group(1) + "(<" + new_target + ">)"

        content = re.sub(r"(\[[^\]\n]*\])\((<[^>]+>|[^)\n]+)\)", replace, content)
        write(path, content)
    for file in (ROOT / "索引" / "数据").glob("*.json"):
        value = json.loads(file.read_text(encoding="utf-8-sig"))

        def update(obj):
            if isinstance(obj, str):
                return mapping.get(obj, obj)
            if isinstance(obj, list):
                return [update(v) for v in obj]
            if isinstance(obj, dict):
                return {key: update(v) for key, v in obj.items()}
            return obj

        write(file, json.dumps(update(value), ensure_ascii=False, indent=2) + "\n")
    for row in rows:
        row["migrated_sha256"] = hashlib.sha256((ROOT / row["new_path"]).read_bytes()).hexdigest()
    write(MAPPING, json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    header = "# 目录迁移记录\n\n2026-09-06。原资料逐文件迁移，正文及引用保留，内部链接随位置更新；未删除任何原稿。原始与迁移后的SHA-256记录在[JSON映射](数据/目录迁移.json)。前三集及23人、7场景同时拆分到现行剧集和资产卡；v0.5合订本留作拆分来源。\n\n| 原路径 | 新位置 |\n|---|---|\n"
    for row in rows:
        target = os.path.relpath(ROOT / row["new_path"], ROOT / "索引").replace("\\", "/")
        header += f"| `{row['old_path']}` | [{row['new_path']}](<{target}>) |\n"
    write(ROOT / "索引" / "目录迁移.md", header)
    print(f"已迁移{len(rows)}份原稿，更新{count}处内部链接。")


if __name__ == "__main__":
    main()
