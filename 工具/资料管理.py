"""从登记表更新双向索引，或检索当前创作资料。仅使用 Python 标准库。"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "索引" / "数据"
FILES = ("characters.json", "locations.json", "props.json", "episodes.json")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_bytes() == text.encode("utf-8"):
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def relative(path, parent):
    return os.path.relpath(path, parent).replace("\\", "/")


def link(item, parent, label=None):
    anchor = item.get("anchor", "")
    if not anchor and item.get("kind") and Path(item["path"]).name == "README.md":
        anchor = item["id"].lower()
    suffix = "#" + anchor if anchor else ""
    return f"[{label or item['id'] + ' ' + item['name']}](<{relative(ROOT / item['path'], parent)}{suffix}>)"


def cell(value):
    return str(value or "—").replace("|", "／").replace("\n", " ")


def table(headers, rows):
    return "| " + " | ".join(headers) + " |\n|" + "|".join(["---"] * len(headers)) + "|\n" + "".join("| " + " | ".join(cell(v) for v in row) + " |\n" for row in rows)


def load():
    groups = [json.loads(read(DATA / name)) for name in FILES]
    if not all(isinstance(group, list) for group in groups):
        raise ValueError("四份源登记表必须为 JSON 数组")
    assets = groups[0] + groups[1] + groups[2]
    episodes = groups[3]
    by_id = {item["id"]: item for item in assets + episodes}
    if len(by_id) != len(assets + episodes):
        raise ValueError("登记表存在重复编号")
    subareas = {}
    for item in groups[1]:
        for sub in item.get("subareas", []):
            if sub["id"] in subareas or sub["id"] in by_id:
                raise ValueError(f"子区编号重复或与资产/剧集冲突：{sub['id']}")
            subareas[sub["id"]] = item["id"]
    scenes = []
    for ep in episodes:
        for scene in ep.get("scenes", []):
            scenes.append(dict(scene, episode_id=ep["id"], episode_path=ep["path"]))
    return assets, episodes, by_id, subareas, scenes


def validate(assets, episodes, by_id, subareas, scenes):
    errors = []
    for item in assets + episodes:
        path = (ROOT / item["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            errors.append(f"{item['id']} 文档不存在或越出工作区：{item['path']}")
        for src in item.get("source_paths", []):
            if not (ROOT / src).is_file():
                errors.append(f"{item['id']} 来源不存在：{src}")
    seen = set()
    for scene in scenes:
        if scene["id"] in seen:
            errors.append(f"场次重复：{scene['id']}")
        seen.add(scene["id"])
        for field, category in (("character_ids", "角色"), ("voice_only_ids", "角色"), ("location_ids", "场景"), ("prop_ids", "道具")):
            values = scene.get(field, [])
            if len(values) != len(set(values)):
                errors.append(f"{scene['id']} {field} 内编号重复")
            for value in values:
                key = subareas.get(value, value)
                if key not in by_id or by_id[key].get("category") != category:
                    errors.append(f"{scene['id']} 引用无效{category}：{value}")
                elif by_id[key].get("status") == "停用":
                    errors.append(f"{scene['id']} 错用停用资产：{value}")
        overlap = set(scene.get("character_ids", [])) & set(scene.get("voice_only_ids", []))
        if overlap:
            errors.append(f"{scene['id']} 同一角色同时登记可见和仅画外声：{overlap}")
        ep_text = read(ROOT / scene["episode_path"])
        if not re.search(r"^###\s+" + re.escape(scene["alias"]) + r"\s", ep_text, re.M):
            errors.append(f"{scene['id']} 在台本中找不到原场号 {scene['alias']}")
    if errors:
        raise ValueError("\n".join(errors))


def usage_for(asset, scenes, subareas):
    rows = []
    for scene in scenes:
        roles = []
        if asset["id"] in scene.get("character_ids", []):
            roles.append("出镜")
        if asset["id"] in scene.get("voice_only_ids", []):
            roles.append("仅画外声")
        if asset["id"] in scene.get("prop_ids", []):
            roles.append("台本呈现")
        locations = scene.get("location_ids", [])
        used_locations = [key for key in locations if subareas.get(key, key) == asset["id"]]
        if used_locations:
            roles.append("场景 " + "、".join(used_locations))
        if roles:
            rows.append((scene, "／".join(roles)))
    return rows


def block(path, key, content):
    start, end = f"<!-- AUTO:{key}:START -->", f"<!-- AUTO:{key}:END -->"
    source = read(path)
    new = f"{start}\n{content.rstrip()}\n{end}"
    pattern = re.escape(start) + r"[\s\S]*?" + re.escape(end)
    if start in source:
        if end not in source:
            raise ValueError(f"自动区缺少结束标记：{path}")
        source = re.sub(pattern, lambda _: new, source)
    else:
        source = source.rstrip() + "\n\n" + new + "\n"
    write(path, source)


def csv_export(path, headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stream.getvalue(), encoding="utf-8-sig", newline="")


def build(assets, episodes, by_id, subareas, scenes):
    index = ROOT / "索引"
    usage = {item["id"]: usage_for(item, scenes, subareas) for item in assets}
    records = []
    asset_rows, asset_csv = [], []
    for item in assets:
        uses = usage[item["id"]]
        eps = list(dict.fromkeys(s["episode_id"] for s, _ in uses))
        row = [link(item, index), item["category"], "、".join(item.get("aliases", [])), "、".join(item.get("tags", [])), item["status"], "、".join(eps)]
        asset_rows.append(row)
        asset_csv.append([item["id"], item["name"], item["category"], "；".join(item.get("aliases", [])), "；".join(item.get("tags", [])), item["status"], "；".join(eps), item["path"]])
        records.append(dict(item, registered_episodes=eps, scene_ids=[s["id"] for s, _ in uses]))
        path = ROOT / item["path"]
        text = "## 剧集反查\n\n由场次登记自动汇总；只登记已有详细台本，后篇大纲安排另见本卡正文。\n\n"
        if uses:
            text += table(["剧集", "场次", "呈现方式"], [[link(by_id[s["episode_id"]], path.parent), link(dict(by_id[s["episode_id"]], anchor=s["id"].lower()), path.parent, s["id"] + "（" + s["alias"] + "）"), mode] for s, mode in uses])
        else:
            text += "现有详细工作单元无明确呈现登记。大纲人物、隐去物件和停用资产不据此判为已出镜。\n"
        block(path, "USAGE", text)
    write(index / "资产总表.md", "# 资产总表\n\n[返回入口](../README.md) · [按场次查资产](场次资产表.md) · [剧集总表](剧集总表.md)\n\n本表自动生成。可用 Ctrl+F 搜编号、姓名、别名或标签。文字设定与大纲登记都不表示已有图片、配音或视频。未具名背景人物不强行分配角色编号。P05停用保留，不参与当前剧集。\n\n" + table(["编号与资产卡", "类别", "别名", "标签", "状态", "已有台本呈现"], asset_rows))
    ep_rows, ep_csv = [], []
    for ep in episodes:
        linked = link(ep, index)
        ep_rows.append([linked, ep["arc"], "工作集" if ep["kind"] == "episode" else "剧情单元", ep["status"], ep.get("summary", "")])
        ep_csv.append([ep["id"], ep["name"], ep["arc"], ep["kind"], ep["status"], ep["path"], ep.get("summary", "")])
        records.append(dict(ep, category="剧集" if ep["kind"] == "episode" else "剧情单元"))
        if not ep.get("scenes"):
            continue
        path = ROOT / ep["path"]
        scene_index = "## 场次检索\n\n下表与末尾资产清单由同一份场次登记生成。仅明确出镜者计入；未具名背景、隐去物件和声效的边界见[场次资产表](../../索引/场次资产表.md)。原场号作为别名保留；GJ-EP为创作单元号，发行映射见前三集制作交接；对白以本页当前修订稿为准。\n\n"
        scene_index += table(["场次编号", "旧场号", "发行集", "场景", "出镜角色", "仅画外声", "编号道具"], [[f'<a id="{s["id"].lower()}"></a>{s["id"]}', s["alias"], s.get("release_episode_id", "后续待拆"), "、".join(s.get("location_ids", [])), "、".join(s.get("character_ids", [])), "、".join(s.get("voice_only_ids", [])), "、".join(s.get("prop_ids", []))] for s in ep["scenes"]])
        if "<!-- AUTO:SCENES:START -->" not in read(path):
            source = read(path)
            source, changed = re.subn(r"## 场次检索\n[\s\S]*?(?=## 台本原文)", "<!-- AUTO:SCENES:START -->\n<!-- AUTO:SCENES:END -->\n\n", source, count=1)
            if changed != 1:
                raise ValueError(f"找不到单集场次索引区域：{ep['id']}")
            write(path, source)
        block(path, "SCENES", scene_index)
        rows = []
        for category in ("角色", "场景", "道具"):
            for item in assets:
                if item["category"] != category:
                    continue
                matches = [(s, mode) for s, mode in usage[item["id"]] if s["episode_id"] == ep["id"]]
                if matches:
                    rows.append([category, link(item, path.parent), "；".join(s["alias"] + " " + mode for s, mode in matches)])
        block(path, "ASSETS", "## 本集资产调用清单\n\n由场次登记自动汇总。仅声音、隐去物件与可见角色分别处理；衣伤和物件交接须同时查[连续性](../../资产/连续性.md)。\n\n" + table(["类别", "资产卡", "场次与呈现"], rows))
    write(index / "剧集总表.md", "# 剧集总表\n\n[返回剧集目录](../剧集/README.md) · [资产总表](资产总表.md)\n\n归京36个工作单元，前3单元为详细剧本；前三发行集为GJ-R01—03（180／195／180秒），原门口单元留后续待拆；后三篇各12个剧情单元，尚未拆为发行剧集，总集数未锁定。\n\n" + table(["编号与入口", "篇章", "粒度", "完成状态", "事件摘要"], ep_rows))
    scene_rows, scene_csv = [], []
    subarea_names = {sub["id"]: sub["name"] for item in assets for sub in item.get("subareas", [])}
    for s in scenes:
        def names(field):
            return "、".join(key + " " + (subarea_names[key] if key in subarea_names else by_id[key]["name"]) for key in s.get(field, []))
        row = [s["id"] + "（" + s["alias"] + "）", link(by_id[s["episode_id"]], index), s["name"], names("location_ids"), names("character_ids"), names("voice_only_ids"), names("prop_ids"), s.get("notes", "")]
        scene_rows.append(row)
        scene_csv.append([s["id"], s["alias"], s["episode_id"], s["name"], names("location_ids"), names("character_ids"), names("voice_only_ids"), names("prop_ids"), s.get("notes", "")])
    write(index / "场次资产表.md", "# 场次资产表\n\n[资产总表](资产总表.md) · [剧集总表](剧集总表.md) · [连续性](../资产/连续性.md)\n\n3个工作单元16场已有台本，其中前三发行集11场、后续门口预备5场。场号保留原别名；场景子区归所属主资产。未具名背景、仅声音、作者隐去物件以备注区分，不能据‘留在府中’推成‘本场出镜’。本表列现有编号资产，零散布景小物仍见场景卡和原文。\n\n" + table(["场次", "剧集", "名称", "场景", "出镜角色", "仅画外声", "编号道具", "备注"], scene_rows))
    write(DATA / "检索索引.json", json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    csv_export(index / "导出" / "资产总表.csv", ["编号", "名称", "类别", "别名", "标签", "状态", "已有台本呈现", "文档路径"], asset_csv)
    csv_export(index / "导出" / "剧集总表.csv", ["编号", "名称", "篇章", "粒度", "状态", "文档路径", "摘要"], ep_csv)
    csv_export(index / "导出" / "场次资产表.csv", ["场次编号", "原场号", "剧集编号", "场次名称", "场景", "出镜角色", "仅画外声", "编号道具", "备注"], scene_csv)
    return records


def check_links():
    failures, count = [], 0
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        count += 1
        for match in re.finditer(r"\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)", read(path)):
            raw = match.group(1).strip().strip("<>")
            if re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I) or raw.startswith("#"):
                continue
            target = unquote(raw.split("#", 1)[0])
            if target and not (path.parent / target).exists():
                failures.append(f"{relative(path, ROOT)} -> {raw}")
    if failures:
        raise ValueError("失效文件链接：\n" + "\n".join(failures))
    return count


def search(args, assets, episodes, subareas, scenes):
    hits = []
    exact = set()
    if args.query and not args.fulltext:
        for item in assets + episodes:
            keys = [item["id"], item["name"], *item.get("aliases", []), *[s["id"] for s in item.get("subareas", [])]]
            if args.query.casefold() in [key.casefold() for key in keys]:
                exact.add(item["id"])
    for item in assets + episodes:
        if exact and item["id"] not in exact:
            continue
        category = item.get("category", "剧集" if item.get("kind") == "episode" else "剧情单元")
        if args.type and args.type != category:
            continue
        if item.get("status") == "停用" and not args.include_inactive:
            continue
        uses = usage_for(item, scenes, subareas) if category not in ("剧集", "剧情单元") else []
        eps = list(dict.fromkeys(s["episode_id"] for s, _ in uses))
        if args.episode and args.episode not in eps and item["id"] != args.episode:
            continue
        content = json.dumps(item, ensure_ascii=False)
        if args.fulltext:
            content += re.sub(r"<!-- AUTO:[\s\S]*?<!-- AUTO:[^>]+:END -->", "", read(ROOT / item["path"]))
        if args.query.casefold() not in content.casefold():
            continue
        hits.append(f"{item['id']} | {item['name']} | {category} | {item['status']}\n  {item['path']}" + ("\n  已有台本：" + "、".join(eps) if eps else ""))
    print("\n".join(hits) if hits else "无匹配。可尝试别名、--fulltext，或用 --include-inactive 检索停用资产。")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="更新索引、CSV和卡片反查")
    sub.add_parser("check", help="检查编号、路径、场次及Markdown文件链接")
    find = sub.add_parser("search", help="检索当前登记资料，默认不含停用资产")
    find.add_argument("query", nargs="?", default="")
    find.add_argument("--type", choices=["角色", "场景", "道具", "剧集", "剧情单元"])
    find.add_argument("--episode")
    find.add_argument("--fulltext", action="store_true")
    find.add_argument("--include-inactive", action="store_true")
    args = parser.parse_args()
    loaded = load()
    validate(*loaded)
    assets, episodes, by_id, subareas, scenes = loaded
    if args.command == "search":
        search(args, assets, episodes, subareas, scenes)
    elif args.command == "build":
        build(*loaded)
        print(f"已更新：{len(assets)}项资产、{len(episodes)}个工作集/剧情单元、{len(scenes)}场及双向索引。")
    else:
        count = check_links()
        print(f"检查通过：{len(assets)}项资产、{len(episodes)}个工作集/剧情单元、{len(scenes)}场；{count}份Markdown无失效文件链接。")


if __name__ == "__main__":
    main()
