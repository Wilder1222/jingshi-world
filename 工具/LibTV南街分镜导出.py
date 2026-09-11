"""派生本地LibTV南街两行草案；不上传、不触发模型，不填造URL。"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "资产/生产准备/前三集-v1.9"
OUTPUT = PACK / "LibTV南街分镜草案.json"
CAST = {"GJ-R02-SH001": ["C01", "C03"], "GJ-R02-SH002": ["C08", "C09", "C10", "C01", "C03"]}

def build():
    paths = ["索引/数据/发行前三集.json", "索引/数据/characters.json", "索引/数据/episodes.json",
             "资产/媒体/镜头/镜头媒体登记.json", "资产/生产准备/前三集-v1.9/南街镜头执行卡.md",
             "剧集/01-归京/GJ-EP01-归京.md", "剧集/01-归京/GJ-EP02-先过今夜.md", "工具/对白节奏核对.py",
             "工具/LibTV南街分镜导出.py"]
    read = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8-sig"))
    release = read(paths[0])
    chars = {c["id"]: c for c in read(paths[1])}
    media = read(paths[3])["shots"]
    card = (ROOT / paths[4]).read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("dialogue", ROOT / "工具/对白节奏核对.py")
    dialogue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dialogue)
    resolved = dialogue.resolve_dialogue(release)
    rows, mapping = [], []
    for ep in release["episodes"]:
        for shot in ep["shots"]:
            sid = shot["id"]
            if sid not in CAST:
                continue
            section = card.split("## " + sid + "｜", 1)[1].split("\n## ", 1)[0]
            start = re.search(r"^起始图：(.*)$", section, re.M)
            if not start:
                raise ValueError("执行卡缺起始图：" + sid)
            people = []
            for cid in CAST[sid]:
                c = chars[cid]
                design = c.get("visual_design", {})
                description = "；".join(design.get(k, "") for k in ("骨相与仪态", "服装与色彩"))
                people.append({"characterName": c["name"], "characterDescription": description,
                               "characterImageUrl": ""})
            rows.append({
                "durationSeconds": (shot["end_frame"] - shot["start_frame"]) / 24,
                "plotDescription": sid + "｜" + shot["beat"] + "。" + shot["action"],
                "characters": people,
                "videoReference": {"referenceFrameImage": ""},
                "shotSize": "中景" if sid.endswith("001") else "中近景",
                "characterAction": shot["action"], "emotion": shot["performance"],
                "sceneTags": "S02，南街汤摊邻近街面，雨夜",
                "lightingAndAtmosphere": "以当前S02已选场景及本镜起始图统一灯源和雨夜状态，待人景绑定复核。",
                "audioEffects": shot["sound"],
                "dialogue": "\n".join(r["speaker"] + "：" + r["text"] for r in resolved[sid]),
                "imageGenerationPrompt": start.group(1),
                "videoMotionPrompt": "人物动作：" + shot["action"] + "\n摄影机：" + shot["camera"] +
                    "\n接续：" + shot["blocking_continuity"] + "\n切点：" + shot["cut_cue"]
            })
            refs = []
            for item in media:
                if item["shot_id"] != sid:
                    continue
                file = ROOT / item["path"]
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
                if digest != item["sha256"]:
                    raise ValueError("候选登记哈希不匹配：" + sid)
                paths.append(item["path"])
                refs.append({"path": item["path"], "status": item["status"], "sha256": digest})
            mapping.append({"sourceShotId": sid, "localRowIndex": len(rows)-1, "characterIds": CAST[sid],
                "platformRowId": None, "platformHiddenUuid": None, "platformNodeId": None,
                "referenceCandidates": refs,
                "pending": ["角色参考URL尚未上传绑定", "起始画面及动作接触待验收", "模型与实际生成参数尚未配置"]})
    if len(rows) != 2 or sum(r["durationSeconds"] for r in rows) != 15:
        raise ValueError("南街两镜范围已变，需复核导出适配")
    return {"status": "local_draft_not_ready_to_run", "rows": rows, "handoff": {
        "note": "仅rows映射分镜节点属性；handoff为本地核验数据。空URL不是已绑定素材。执行卡和源台本仍为权威。",
        "mapping": mapping, "sourceHashes": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(set(paths))}}}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "check"])
    args = parser.parse_args()
    data = build()
    if args.command == "build":
        OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif json.loads(OUTPUT.read_text(encoding="utf-8")) != data:
        raise SystemExit("草案与当前源不一致，请重新build")
    print("南街2行／15秒；源、对白和候选哈希一致；未上传、未绑定URL、未生成。")

if __name__ == "__main__":
    main()
