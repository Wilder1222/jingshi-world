"""核验并导出《经世》人物事件图谱。只读原始设定，不修改正式登记。"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "索引" / "数据"
INPUTS = [DATA / "图谱人物.json", DATA / "图谱事件.json"]
TEMPLATE = ROOT / "工具" / "图谱浏览器模板.html"
OUTPUTS = {
    "json": DATA / "人物事件图谱.json",
    "html": ROOT / "索引" / "人物事件图谱.html",
    "md": ROOT / "索引" / "人物事件图谱明细.md",
}
ARCS = ["归京", "照夜", "白河", "众名", "渡世", "天倾", "经世"]
TASK_SOURCES = [ROOT / "剧集" / name for name in (
    "主线成长与任务总图.md", "情感任务与坚定选择.md", "支线与配角任务.md", "配角情感线与关系回收.md"
)]
FIELDS = {
    "characters": "id name group status want fear bottom_line resources blind_spot behavior_rule sources",
    "relations": "id from to label direction basis trigger boundary stage status sources",
    "events": "id name arc order stage status participants goal trigger obstacle choice cost result next_pressure task_ids knowledge sources",
    "causal_edges": "id from to label kind status sources",
    "plotlines": "id name question event_ids payoff sources",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_data() -> dict:
    result: dict = {"notes": []}
    for path in INPUTS:
        part = json.loads(read(path))
        for key, value in part.items():
            if key == "notes":
                result["notes"].extend(value)
            elif key in result:
                raise ValueError(f"重复数据组：{key}")
            else:
                result[key] = value
    return result


def validate(data: dict) -> None:
    errors = []
    seen = set()
    sources = set()
    for group, fields in FIELDS.items():
        if not isinstance(data.get(group), list) or not data[group]:
            errors.append(f"{group} 必须是非空数组")
            continue
        for item in data[group]:
            if not isinstance(item, dict):
                errors.append(f"{group} 中有非对象记录")
                continue
            key = item.get("id", "无编号")
            if key in seen:
                errors.append(f"重复编号：{key}")
            seen.add(key)
            for field in fields.split():
                value = item.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors.append(f"{key} 缺少字段：{field}")
            refs = item.get("sources", [])
            if not isinstance(refs, list) or not refs:
                errors.append(f"{key} 必须有来源数组")
            else:
                for ref in refs:
                    if not isinstance(ref, str):
                        errors.append(f"{key} 来源须为相对路径字符串")
                        continue
                    path = (ROOT / ref).resolve()
                    if not path.is_relative_to(ROOT) or not path.is_file():
                        errors.append(f"{key} 来源不存在或越出工作区：{ref}")
                    sources.add(ref)
    if errors:
        raise ValueError("\n".join(errors))

    registered = {x["id"]: x for x in json.loads(read(DATA / "characters.json"))}
    chars = {x["id"]: x for x in data["characters"]}
    events = {x["id"]: x for x in data["events"]}
    if chars.keys() != registered.keys():
        errors.append(f"人物覆盖不同于现有登记：遗漏{sorted(registered.keys() - chars.keys())}，多出{sorted(chars.keys() - registered.keys())}")
    for char in chars.values():
        if char["id"] in registered and char["name"] != registered[char["id"]]["name"]:
            errors.append(f"{char['id']} 名称与登记不同：{char['name']}")
        if not isinstance(char["resources"], list):
            errors.append(f"{char['id']} resources 必须是数组")
        if char["status"] not in {"设定提取", "发展稿提取"}:
            errors.append(f"{char['id']} 人物提取状态无效")
    for edge in data["relations"]:
        if edge["from"] not in chars or edge["to"] not in chars:
            errors.append(f"{edge['id']} 人物关系悬空")
        if edge["from"] == edge["to"]:
            errors.append(f"{edge['id']} 人物关系不能自连")
        if edge["direction"] not in {"双向", "单向"}:
            errors.append(f"{edge['id']} 方向无效")
    tasks = set()
    for path in TASK_SOURCES:
        tasks.update(re.findall(r"^###\s+(Q-[MESR]\d{2})\b", read(path), re.M))
    if not tasks:
        errors.append("无法读取现有Q任务标题")
    orders = set()
    for event in events.values():
        eid = event["id"]
        if event["arc"] not in ARCS:
            errors.append(f"{eid} 篇章无效")
        if not isinstance(event["order"], (int, float)) or isinstance(event["order"], bool):
            errors.append(f"{eid} order 必须是数值")
        elif event["order"] in orders:
            errors.append(f"{eid} 事件排序重复")
        orders.add(event["order"])
        if event["status"] not in {"台本提取", "发展稿提取"}:
            errors.append(f"{eid} 事件提取状态无效")
        for field, allowed in (("participants", chars), ("task_ids", tasks)):
            values = event[field]
            if not isinstance(values, list):
                errors.append(f"{eid} {field} 必须是数组")
                continue
            if len(values) != len(set(values)):
                errors.append(f"{eid} {field} 内重复")
            for value in values:
                if value not in allowed:
                    errors.append(f"{eid} 引用未知{field}：{value}")
        if not isinstance(event["knowledge"], list):
            errors.append(f"{eid} knowledge 必须是数组")
            continue
        for row in event["knowledge"]:
            if any(not isinstance(row.get(field), str) or not row[field].strip() for field in ("who", "before", "after", "channel")):
                errors.append(f"{eid} 知情记录字段不完整")
            if row.get("who") not in chars:
                errors.append(f"{eid} 知情者没有人物编号：{row.get('who')}")
    for edge in data["causal_edges"]:
        before, after = events.get(edge["from"]), events.get(edge["to"])
        if not before or not after:
            errors.append(f"{edge['id']} 因果关系悬空")
        elif before["order"] >= after["order"]:
            errors.append(f"{edge['id']} 因果必须指向后发生的事件；回看信息应指向获知时刻")
        if edge["kind"] not in {"触发", "提供条件", "揭示", "迫使选择"}:
            errors.append(f"{edge['id']} 因果类型无效")
    # 严格递增的边序也证明事件图无环；人物关系允许互相作用。
    for line in data["plotlines"]:
        ids = line["event_ids"]
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
            errors.append(f"{line['id']} 情节线事件必须非空且不重复")
            continue
        if any(key not in events for key in ids):
            errors.append(f"{line['id']} 情节线事件悬空")
        elif ids != sorted(ids, key=lambda key: events[key]["order"]):
            errors.append(f"{line['id']} 情节线须按事件顺序列出")
    arc_sequence = [ARCS.index(e["arc"]) for e in sorted(events.values(), key=lambda e: e["order"]) if e["arc"] in ARCS]
    if arc_sequence != sorted(arc_sequence):
        errors.append("事件顺序与七篇顺序不符")
    if set(e["arc"] for e in events.values()) != set(ARCS):
        errors.append("事件尚未覆盖七篇")
    if errors:
        raise ValueError("\n".join(errors))


def source_paths(data: dict) -> list[Path]:
    refs = set()
    for group in FIELDS:
        for item in data[group]:
            refs.update(item["sources"])
    refs.add("索引/数据/characters.json")
    return sorted({ROOT / ref for ref in refs} | set(TASK_SOURCES) | set(INPUTS) | {TEMPLATE}, key=str)


def assemble(data: dict) -> dict:
    return {
        "meta": {
            "title": "《经世》人物、事件与情节图谱",
            "version": "1.0",
            "updated": "2026-09-08",
            "description": "作者全剧视图；以现行发展稿及v1.7穿越保密边界提取。陈渡是作者标签，剧中仍称顾砚；未列出的知情不能自动补齐。",
            "authority": "设定/穿越隐秘与现代知识运用.md 明确替代旧公开身份节点；世界、人物硬锁与前三集台本保留各自范围。",
            "source_hashes": {relative(path): digest(path) for path in source_paths(data)},
            "snapshot_note": "哈希仅记录生成时文件内容，用于提醒资料变化，不证明提取逐句正确或已经审定。",
        },
        **data,
    }


def cell(value) -> str:
    return str(value).replace("|", "／").replace("\n", " ")


def table(headers, rows) -> str:
    return "| " + " | ".join(headers) + " |\n|" + "|".join("---" for _ in headers) + "|\n" + "".join("| " + " | ".join(cell(x) for x in row) + " |\n" for row in rows)


def refs(item) -> str:
    return "、".join(f"[{Path(path).stem}](<../{path}>)" for path in item["sources"])


def markdown(data: dict) -> str:
    chars = {x["id"]: x for x in data["characters"]}
    events = {x["id"]: x for x in data["events"]}

    def name(key):
        item = chars.get(key) or events.get(key)
        return f"[{key} {item['name']}](#{key.lower()})"

    lines = [
        "# 《经世》人物事件图谱明细\n",
        "由 `python 工具/图谱管理.py build` 生成；维护两份图谱输入数据，不在此手改。\n",
        "[交互查看](人物事件图谱.html) · [推演方法与示例](../剧集/人物事件与情节关系图谱.md)\n",
        f"{len(chars)}个人物、{len(data['relations'])}条人物关系、{len(events)}个核心事件、{len(data['causal_edges'])}条因果关系、{len(data['plotlines'])}条情节线。\n",
        "作者全剧视图，包含未来发展稿。陈渡／今顾是作者标签，剧内仍称顾砚。人物关系不是逐场历史快照；知识以事件条目及保密专题为准，未记录不等于已知。\n",
        "## 提取说明\n",
    ]
    lines.extend(f"- {note}\n" for note in data.get("notes", []))
    lines += ["\n## 人物目录\n", table(["编号", "人物", "分组", "提取状态"], ((x["id"], name(x["id"]), x["group"], x["status"]) for x in chars.values()))]
    for char in chars.values():
        key = char["id"]
        lines += [f'\n<a id="{key.lower()}"></a>\n\n### {key} {char["name"]}\n',
                  table(["维度", "内容"], [("想要", char["want"]), ("害怕", char["fear"]), ("底线", char["bottom_line"]), ("资源", "；".join(char["resources"])), ("盲点", char["blind_spot"]), ("行为推演规则", char["behavior_rule"])]),
                  f"\n来源（{char['status']}）：{refs(char)}。\n"]
        edges = [e for e in data["relations"] if key in (e["from"], e["to"])]
        if edges:
            lines += ["\n人物关系：\n", table(["关系", "对象与方向", "依据", "可能改变关系的条件", "边界", "阶段／状态／来源"], (
                (e["id"] + " " + e["label"], name(e["from"]) + (" ↔ " if e["direction"] == "双向" else " → ") + name(e["to"]), e["basis"], e["trigger"], e["boundary"], e["stage"] + "／" + e["status"] + "／" + refs(e)) for e in edges))]
        involved = [name(e["id"]) for e in events.values() if key in e["participants"]]
        lines.append("\n本图关联事件：" + ("、".join(involved) or "尚未选入核心事件；不表示此人没有其他生活或剧情。") + "\n")
    lines += ["\n## 事件目录\n", table(["事件", "篇章／位置", "状态", "任务标签"], ((name(e["id"]), e["arc"] + "／" + e["stage"], e["status"], "、".join(e["task_ids"])) for e in events.values()))]
    for event in events.values():
        key = event["id"]
        lines += [f'\n<a id="{key.lower()}"></a>\n\n### {key} {event["name"]}\n',
                  f"{event['arc']}／{event['stage']} · {event['status']} · 任务：{'、'.join(event['task_ids']) or '未挂任务标签'}\n",
                  "涉及身份（跨场／回忆不等于同时在场）：" + "、".join(name(pid) for pid in event["participants"]) + "\n",
                  table(["因果环节", "内容"], [(title, event[field]) for title, field in [("目标", "goal"), ("触发", "trigger"), ("阻力", "obstacle"), ("选择", "choice"), ("代价", "cost"), ("结果", "result"), ("后续压力", "next_pressure")]]),
                  "\n知情变化（仅列本次核心信息）：\n",
                  table(["人物", "此前", "此后", "获知渠道"], ((name(k["who"]), k["before"], k["after"], k["channel"]) for k in event["knowledge"])),
                  "\n前因与后继：\n",
                  table(["方向", "相连事件", "为什么产生影响", "类型／状态／来源"], (("前因" if edge["to"] == key else "后继", name(edge["from"] if edge["to"] == key else edge["to"]), edge["label"], edge["kind"] + "／" + edge["status"] + "／" + refs(edge)) for edge in data["causal_edges"] if key in (edge["from"], edge["to"]))),
                  f"\n来源：{refs(event)}。\n"]
    lines += ["\n## 情节线\n"]
    for line in data["plotlines"]:
        lines += [f"\n### {line['id']} {line['name']}\n", f"核心问题：{line['question']}\n", "事件路径：" + " → ".join(name(key) for key in line["event_ids"]) + "\n", f"兑现：{line['payoff']}\n", f"来源：{refs(line)}。\n"]
    return "\n".join(lines).rstrip() + "\n"


def rendered(data: dict) -> dict[Path, str]:
    template = read(TEMPLATE)
    if template.count("__GRAPH_DATA__") != 1:
        raise ValueError("HTML模板须且仅须包含一个 __GRAPH_DATA__ 占位符")
    # 避免JSON内的文本提前闭合script元素。
    embedded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return {
        OUTPUTS["json"]: json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        OUTPUTS["html"]: template.replace("__GRAPH_DATA__", embedded),
        OUTPUTS["md"]: markdown(data),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "check"])
    args = parser.parse_args()
    try:
        data = load_data()
        validate(data)
        outputs = rendered(assemble(data))
        if args.command == "build":
            for path, text in outputs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
            print("已生成图谱JSON、HTML与Markdown；原始设定及正式登记未改写。")
        else:
            stale = [relative(path) for path, text in outputs.items() if not path.is_file() or read(path) != text]
            if stale:
                raise ValueError("图谱生成内容与当前输入／来源快照不同，请先核对变化的原文并修正提取数据，再运行build：\n" + "\n".join(stale))
            print("图谱检查通过：人物登记、来源、Q任务、引用、顺序、因果无环及导出一致。语义与知情仍须人工复核。")
        print("／".join(f"{len(data[group])}{label}" for group, label in [("characters", "人物"), ("relations", "人物关系"), ("events", "事件"), ("causal_edges", "因果关系"), ("plotlines", "情节线")]))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"图谱检查失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
