"""将全剧大纲同步到篇章目录和剧集登记，不改独立单集台本或场次资产。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    source = (ROOT / "剧集/全剧大纲.md").read_text(encoding="utf-8-sig")
    version_match = re.search(r"^# .*?(v\d+\.\d+)", source, re.M)
    story_version = version_match[1] if version_match else "现行版本"
    registry = ROOT / "索引/数据/episodes.json"
    items = json.loads(registry.read_text(encoding="utf-8-sig"))
    by_id = {item["id"]: item for item in items}
    gj = source.split("## 三、第一篇《归京》", 1)[1].split("## 四、第二篇", 1)[0]
    rows = []
    for line in gj.splitlines():
        match = re.match(r"^\| (\d{2}) (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if match:
            number, title, date, action, result = match.groups()
            rows.append((int(number), title, date, action, result))
    if [r[0] for r in rows] != list(range(1, 37)):
        raise ValueError("归京表必须有连续36个工作集；源格式或集数已变更，请先复核")
    outputs = {}
    intro = "# 《归京》剧集目录\n\n编号前缀：**GJ-EP**。36个工作单元，前3单元已有完整台本，其余33单元为大纲。前三发行集映射GJ-R01＝原1-1、GJ-R02＝原1-2—1-6、GJ-R03＝原2-1—2-5；180／195／180秒。原门口单元GJ-EP03为后续待拆，不按旧号发第3集。此目录从[全剧大纲](../全剧大纲.md)同步，当前感情线按v0.6；前三发行集约3分钟，后续发行总数与拆分未锁。\n\n[返回剧集目录](../README.md) · [前三集制作约定](../前三集制作约定.md)\n\n## 逐集索引\n\n| 编号／入口 | 标题 | 状态 | 日期／时段 |\n|---|---|---|---|\n"
    body = "\n## 第04至36集分集大纲摘录\n\n以下为大纲原有行动与关系后果，非完整对白台本；统一修改入口为全剧大纲。\n"
    for number, title, date, action, result in rows:
        key = f"GJ-EP{number:02}"
        item = by_id[key]
        item["name"], item["summary"] = title, action
        target = Path(item["path"]).name if number <= 3 else "#" + key.lower()
        intro += f"| [{key}]({target}) | {title} | {item['status']} | {date} |\n"
        if number > 3:
            body += f'\n<a id="{key.lower()}"></a>\n\n## {key}｜{title}\n\n状态：**分集大纲**。旧别名：EP{number:02}、归京{number:02}。日期／时段：{date}。\n\n**当前行动、阻力与结果：**{action}\n\n**关系变化与后果：**{result}\n'
    outputs[ROOT / "剧集/01-归京/README.md"] = intro + body
    specs = [("照夜", "ZY", "02-照夜", "## 四、第二篇", "## 五、第三篇"), ("白河", "BH", "03-白河", "## 五、第三篇", "## 六、第四篇"), ("众名", "ZM", "04-众名", "## 六、第四篇", "## 七、终局")]
    for name, prefix, directory, start, end in specs:
        section = source.split(start, 1)[1].split(end, 1)[0]
        matches = list(re.finditer(r"^### 单元(\d{2})｜(.+?)（(.+?)）\s*$", section, re.M))
        if [int(m[1]) for m in matches] != list(range(1, 13)):
            raise ValueError(f"{name}必须有连续12个剧情单元；请核对源格式")
        intro = f"# 《{name}》剧情单元目录\n\n编号前缀：**{prefix}-U**。现有12个剧情单元，可继续拆集，**不等于12个已锁定发行集**。以下从全剧大纲同步，当前感情线按v0.6，未扩写成完整台本。\n\n[返回剧集目录](../README.md) · [全剧大纲](../全剧大纲.md)\n\n## 单元索引\n\n| 编号 | 单元标题 | 状态 | 时间与地点 |\n|---|---|---|---|\n"
        body = "\n## 已有单元大纲摘录\n\n以下保留大纲单元原文，按编号与人物可检索；修改全剧大纲后可重新同步。\n"
        for i, match in enumerate(matches):
            number, title, time = match.groups()
            text = section[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(section)].strip()
            key = f"{prefix}-U{number}"
            by_id[key]["name"] = title
            by_id[key]["summary"] = text
            intro += f"| [{key}](#{key.lower()}) | {title} | 剧情单元大纲 | {time} |\n"
            body += f'\n<a id="{key.lower()}"></a>\n\n## {key}｜{title}\n\n状态：**剧情单元大纲**。旧别名：{name}{number}、{name}单元{number}。时间与地点：{time}。\n\n{text}\n'
        outputs[ROOT / "剧集" / directory / "README.md"] = intro + body
    if len(items) != 72:
        raise ValueError("登记条目数量已变化，请复核同步范围")
    for path, content in outputs.items():
        write(path, content.replace("当前感情线按v0.6", f"当前剧情按{story_version}"))
    write(registry, json.dumps(items, ensure_ascii=False, indent=2) + "\n")
    print("Synced: 4 arc indexes and 72 records; detailed scripts and scene metadata retained.")


if __name__ == "__main__":
    main()
