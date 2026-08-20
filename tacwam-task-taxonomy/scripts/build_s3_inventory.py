#!/usr/bin/env python3
"""Build a public, aggregate-only snapshot of TacWAM recordings in S3.

The output intentionally contains no object keys, recording UUIDs, credentials, or
raw sensor data. A recording is counted as complete only when all modalities used
by the TacWAM six-stream workflow are present and non-empty.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import boto3


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUCKET = "noitom-us-west-2"
DEFAULT_PREFIX_RE = r"^itw\d{2}-\d{2}$"
MIN_OBJECT_BYTES = 100
REQUIRED_FILES = (
    "rgb_head.csv",
    "rgb_head.mp4",
    "depth_head.mkv",
    "wrist_left.mp4",
    "wrist_right.mp4",
    "left_hand_data.npz",
    "right_hand_data.npz",
    "task_info.json",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).lower()
    value = re.sub(r"（难度[:：].*?）|\(难度[:：].*?\)", "", value)
    return "".join(ch for ch in value if ch.isalnum())


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def rounded(value: float) -> float:
    return round(float(value), 3)


def list_top_level_prefixes(s3, bucket: str) -> list[str]:
    prefixes: list[str] = []
    kwargs = {"Bucket": bucket, "Delimiter": "/"}
    while True:
        page = s3.list_objects_v2(**kwargs)
        prefixes.extend(item["Prefix"].rstrip("/") for item in page.get("CommonPrefixes", []))
        if not page.get("IsTruncated"):
            return sorted(set(prefixes))
        kwargs["ContinuationToken"] = page["NextContinuationToken"]


def inventory_prefix(s3, bucket: str, prefix: str) -> dict[str, dict[str, int]]:
    """Return recording-directory -> relative object path -> byte size."""
    recordings: dict[str, dict[str, int]] = defaultdict(dict)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
        for item in page.get("Contents", []):
            key = item["Key"]
            if "/" not in key:
                continue
            relative = key[len(prefix) + 1 :]
            parent = str(PurePosixPath(relative).parent)
            if parent == ".":
                continue
            recordings[parent][PurePosixPath(relative).name] = int(item["Size"])
    return dict(recordings)


def is_complete(files: dict[str, int]) -> bool:
    return all(files.get(name, 0) > MIN_OBJECT_BYTES for name in REQUIRED_FILES)


def fetch_task_infos(s3, bucket: str, jobs: list[tuple[str, str]], workers: int):
    def fetch(item: tuple[str, str]):
        prefix, recording_dir = item
        key = f"{prefix}/{recording_dir}/task_info.json"
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        return item, json.loads(body)

    results: dict[tuple[str, str], dict] = {}
    errors: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in jobs}
        for future in as_completed(futures):
            item = futures[future]
            try:
                _, info = future.result()
                results[item] = info
            except Exception:
                errors.append(item)
    return results, errors


def catalog_matcher(catalog: list[dict], aliases: dict[str, str]):
    by_id = {row["record_id"]: row for row in catalog}
    exact: dict[str, list[dict]] = defaultdict(list)
    normalized: dict[str, list[dict]] = defaultdict(list)
    for row in catalog:
        for value in (row["task_title"], row["raw_title"]):
            exact[value].append(row)
        for value in (row["task_title"], row["raw_title"], row["normalized_key"]):
            normalized[normalize_title(value)].append(row)

    def unique_taxonomy(rows: list[dict]):
        pairs = {(row["l1_scene_en"], row["l2_skill_en"]) for row in rows}
        return rows[0] if rows and len(pairs) == 1 else None

    def match(title: str):
        alias_id = aliases.get(title)
        if alias_id:
            if alias_id not in by_id:
                raise ValueError(f"alias for {title!r} references unknown record_id {alias_id!r}")
            return by_id[alias_id], "manual alias"
        row = unique_taxonomy(exact.get(title, []))
        if row:
            return row, "exact title"
        row = unique_taxonomy(normalized.get(normalize_title(title), []))
        if row:
            return row, "normalized title"
        return None, "unmapped"

    return match


def infer_l1(source_scene: str, title: str) -> str:
    value = f"{source_scene} {title}"
    rules = (
        ("Medical / First Aid", ("医疗", "急救", "绷带", "纱布", "创可贴", "药膏")),
        ("Packing / Shipping", ("快递", "打包", "纸箱", "气泡膜", "包装胶带", "包裹")),
        ("Bedroom", ("卧室", "衣物", "衣服", "枕套", "被子", "衣架")),
        ("Office", ("办公室", "办公", "文件", "文档", "记号笔", "白板", "订书", "打孔")),
        ("Workbench", ("工具台", "电子模块", "USB", "螺钉", "螺母", "扳手", "锤子", "装配")),
        ("Kitchen", ("厨房", "茶歇", "备菜", "果蔬", "黄瓜", "土豆", "饮水", "零食", "食品")),
        ("General / Active Tactile", ("柔性物与触觉判断", "轻重样品", "软硬", "回弹", "触觉")),
        ("Laboratory", ("实验室", "试管", "烧杯", "培养皿", "移液", "滴管", "离心管", "试剂瓶")),
    )
    for label, keywords in rules:
        if any(keyword in value for keyword in keywords):
            return label
    return "General / Teleop Alignment"


def infer_l2(title: str) -> str:
    """Assign a reproducible primary skill to uncatalogued S3 title variants."""
    rules = (
        ("Pipette / Dispense / Inject", ("移液枪", "滴管", "注射器", "滴加", "定量加液", "吸液")),
        ("Mix / Stir / Agitate", ("搅拌", "混匀", "摇匀", "摇混", "滚动混", "倒置混")),
        ("Rinse / Wipe / Drain", ("清洁", "清理", "擦", "冲洗", "旋洗", "刷过", "刷净", "刷清", "排液", "废液", "碎屑", "水迹", "湿痕")),
        ("Open / Close / Seal", ("开盖", "瓶盖", "罐盖", "盒盖", "旋开", "旋紧", "拧开", "拧紧", "打开", "闭合", "封口", "密封", "抽屉", "拉链", "按扣")),
        ("Insert / Remove / Align", ("插入", "拔出", "插好", "试插", "插拔", "插放", "插孔", "架孔", "上架", "归架", "放入试管架", "灯泡", "音频插头", "DC圆口", "USB")),
        ("Solids / Weighing / Filtration", ("称量", "粉末", "颗粒", "药匙", "滤纸", "过滤", "粗盐", "大米", "红豆")),
        ("Measure / Label / Document", ("记号笔", "描", "画线", "标签", "标记", "纸张", "书页", "卡片", "文件套", "信息卡")),
        ("Flexible Materials / Wrap / Fold", ("折叠", "对折", "包裹", "包扎", "气泡膜", "胶带", "餐巾", "薄饼", "饺子皮")),
        ("Active Tactile / Press / Classify", ("分类", "轻重", "软硬", "按压", "手感", "回弹", "喷一次", "喷瓶", "按钮", "按键", "开关", "魔方")),
        ("Pour / Container Transfer", ("倒水", "倾倒", "倒入", "倒出", "转移液体", "倒半杯", "续水", "补水")),
        ("Tool Use / Assembly / Fixing", ("扳手", "锤子", "螺钉", "螺母", "工具", "削", "切", "剪", "夹取", "食品夹", "镊子", "钳子", "锅铲", "筷子", "固定", "装配", "紧固")),
    )
    for label, keywords in rules:
        if any(keyword in title for keyword in keywords):
            return label
    return "Pick / Move / Place"


def aggregate_recordings(records: list[dict], catalog: list[dict], aliases: dict[str, str]):
    match = catalog_matcher(catalog, aliases)
    task_groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        task_groups[record["task_name"]].append(record)

    tasks: list[dict] = []
    for task_name, rows in task_groups.items():
        durations = [row["duration_s"] for row in rows if row["duration_s"] is not None]
        mapped, method = match(task_name)
        source_scenes = sorted({row["task_scene"] for row in rows if row["task_scene"]})
        if mapped:
            l1_scene = mapped["l1_scene_en"]
            l2_skill = mapped["l2_skill_en"]
        else:
            l1_scene = infer_l1(" ".join(source_scenes), task_name)
            l2_skill = infer_l2(task_name)
            method = "S3 scene + title rule"
        prefix_counts = Counter(row["prefix"] for row in rows)
        tasks.append(
            {
                "task_name": task_name,
                "task_title_en": mapped["task_title_en"] if mapped else task_name,
                "catalog_record_id": mapped["record_id"] if mapped else None,
                "l1_scene": l1_scene,
                "l2_skill": l2_skill,
                "mapping_method": method,
                "source_scenes": source_scenes,
                "recordings": len(rows),
                "recordings_with_duration": len(durations),
                "total_duration_s": rounded(sum(durations)),
                "median_duration_s": rounded(statistics.median(durations)) if durations else None,
                "p90_duration_s": rounded(percentile(durations, 0.9)) if durations else None,
                "min_duration_s": rounded(min(durations)) if durations else None,
                "max_duration_s": rounded(max(durations)) if durations else None,
                "prefixes": dict(sorted(prefix_counts.items())),
            }
        )
    return sorted(tasks, key=lambda row: (-row["total_duration_s"], row["task_name"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default=os.environ.get("TACWAM_S3_BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--prefix-regex", default=DEFAULT_PREFIX_RE)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/s3_recordings_summary.json",
    )
    args = parser.parse_args()

    catalog = load_json(ROOT / "data/task_catalog.json")
    aliases = load_json(ROOT / "data/s3_task_aliases.json")
    s3 = boto3.client("s3")
    pattern = re.compile(args.prefix_regex)
    prefixes = [p for p in list_top_level_prefixes(s3, args.bucket) if pattern.fullmatch(p)]
    if not prefixes:
        raise SystemExit(f"no S3 prefixes matched {args.prefix_regex!r}")

    inventories: dict[str, dict[str, dict[str, int]]] = {}
    jobs: list[tuple[str, str]] = []
    incomplete_by_prefix: Counter[str] = Counter()
    for prefix in prefixes:
        inventory = inventory_prefix(s3, args.bucket, prefix)
        inventories[prefix] = inventory
        for recording_dir, files in inventory.items():
            if "task_info.json" not in files:
                continue
            jobs.append((prefix, recording_dir))
            if not is_complete(files):
                incomplete_by_prefix[prefix] += 1

    infos, fetch_errors = fetch_task_infos(s3, args.bucket, jobs, args.workers)
    records: list[dict] = []
    invalid_duration = 0
    for (prefix, recording_dir), info in infos.items():
        if not is_complete(inventories[prefix][recording_dir]):
            continue
        task_name = str(info.get("name") or "").strip()
        if not task_name:
            continue
        try:
            duration = float(info["duration"])
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            duration = None
            invalid_duration += 1
        records.append(
            {
                "prefix": prefix,
                "task_name": task_name,
                "task_scene": str(info.get("task_scene") or "").strip(),
                "duration_s": duration,
            }
        )

    tasks = aggregate_recordings(records, catalog, aliases)
    per_prefix = []
    for prefix in prefixes:
        prefix_records = [row for row in records if row["prefix"] == prefix]
        durations = [row["duration_s"] for row in prefix_records if row["duration_s"] is not None]
        per_prefix.append(
            {
                "prefix": prefix,
                "recordings": len(prefix_records),
                "incomplete_excluded": incomplete_by_prefix[prefix],
                "unique_tasks": len({row["task_name"] for row in prefix_records}),
                "total_duration_s": rounded(sum(durations)),
                "median_duration_s": rounded(statistics.median(durations)) if durations else None,
            }
        )

    mapped_tasks = [task for task in tasks if task["l1_scene"] != "Unmapped"]
    unmapped_tasks = [task for task in tasks if task["l1_scene"] == "Unmapped"]
    rule_tasks = [task for task in tasks if task["mapping_method"] == "S3 scene + title rule"]
    catalog_tasks = [task for task in tasks if task["mapping_method"] != "S3 scene + title rule"]
    snapshot = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "prefix_regex": args.prefix_regex,
            "prefixes": prefixes,
            "recording_definition": "task_info.json plus all required TacWAM sensor streams over 100 bytes",
            "duration_source": "task_info.json duration (validated separately against rgb_head.csv timestamp span)",
        },
        "summary": {
            "recordings": len(records),
            "unique_task_names": len(tasks),
            "mapped_task_names": len(mapped_tasks),
            "unmapped_task_names": len(unmapped_tasks),
            "catalog_linked_task_names": len(catalog_tasks),
            "rule_classified_task_names": len(rule_tasks),
            "mapped_recordings": sum(task["recordings"] for task in mapped_tasks),
            "unmapped_recordings": sum(task["recordings"] for task in unmapped_tasks),
            "rule_classified_recordings": sum(task["recordings"] for task in rule_tasks),
            "total_duration_s": rounded(sum(task["total_duration_s"] for task in tasks)),
            "recordings_without_duration": invalid_duration,
            "metadata_fetch_errors": len(fetch_errors),
            "incomplete_excluded": sum(incomplete_by_prefix.values()),
        },
        "prefixes": per_prefix,
        "tasks": tasks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.output}: {len(records)} complete recordings, {len(tasks)} task names, "
        f"{snapshot['summary']['total_duration_s'] / 3600:.2f} hours, "
        f"{len(unmapped_tasks)} unmapped task names."
    )


if __name__ == "__main__":
    main()
