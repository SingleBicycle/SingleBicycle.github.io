#!/usr/bin/env python3
"""Validate the catalog and rebuild the self-contained static site.

This is intentionally a narrow catalog build step. It does not classify tasks,
change taxonomy assignments, or perform vendor-return QA.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = (
    "record_id",
    "batch",
    "source_file",
    "page",
    "source_task_id",
    "source_order",
    "task_title",
    "raw_title",
    "l1_scene",
    "l2_skill",
    "normalized_key",
    "l1_scene_en",
    "l2_skill_en",
    "batch_label",
    "task_title_en",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fail(message: str) -> None:
    raise ValueError(message)


def js_json(value) -> str:
    # Keep the HTML self-contained without allowing catalog text to terminate
    # the inline script element.
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def validate_and_derive(tasks: list[dict], taxonomy: dict):
    if not isinstance(tasks, list) or not tasks:
        fail("data/task_catalog.json must be a non-empty JSON array")

    expected_fields = set(REQUIRED_FIELDS)
    record_ids: set[str] = set()
    for index, task in enumerate(tasks, start=1):
        missing = expected_fields.difference(task)
        if missing:
            fail(f"record {index} is missing fields: {', '.join(sorted(missing))}")
        blank = [field for field in REQUIRED_FIELDS if task[field] in (None, "")]
        if blank:
            fail(f"record {index} has blank fields: {', '.join(blank)}")
        record_id = str(task["record_id"])
        if record_id in record_ids:
            fail(f"duplicate record_id: {record_id}")
        record_ids.add(record_id)

    l1_defs = taxonomy.get("l1", [])
    l2_defs = taxonomy.get("l2", [])
    l1_names = [item["name"] for item in l1_defs]
    l2_names = [item["name"] for item in l2_defs]
    if len(l1_names) != len(set(l1_names)) or len(l2_names) != len(set(l2_names)):
        fail("taxonomy names must be unique")

    unknown_l1 = sorted({task["l1_scene_en"] for task in tasks}.difference(l1_names))
    unknown_l2 = sorted({task["l2_skill_en"] for task in tasks}.difference(l2_names))
    if unknown_l1:
        fail(f"catalog contains unknown L1 labels: {', '.join(unknown_l1)}")
    if unknown_l2:
        fail(f"catalog contains unknown L2 labels: {', '.join(unknown_l2)}")

    l1_counts = Counter(task["l1_scene_en"] for task in tasks)
    l2_counts = Counter(task["l2_skill_en"] for task in tasks)
    for item in l1_defs:
        item["count"] = l1_counts[item["name"]]
    for item in l2_defs:
        item["count"] = l2_counts[item["name"]]

    taxonomy.setdefault("counts", {})
    taxonomy["counts"].update(
        {
            "task_title_records": len(tasks),
            "normalized_semantic_keys": len({task["normalized_key"] for task in tasks}),
            "core_l1_scenes": sum(item.get("type") == "core" for item in l1_defs),
            "legacy_l1_buckets": sum(item.get("type") == "legacy" for item in l1_defs),
            "l2_families": len(l2_defs),
        }
    )

    batches: list[dict] = []
    by_batch: dict[str, dict] = {}
    for task in tasks:
        key = task["batch"]
        current = by_batch.get(key)
        metadata = (task["batch_label"], task["source_file"])
        if current is None:
            current = {
                "batch": key,
                "label": metadata[0],
                "source_file": metadata[1],
                "count": 0,
            }
            by_batch[key] = current
            batches.append(current)
        elif (current["label"], current["source_file"]) != metadata:
            fail(f"inconsistent label or source_file within batch {key}")
        current["count"] += 1

    return l1_names, l2_names, batches


def render_html(
    template: str,
    tasks: list[dict],
    taxonomy: dict,
    l1_names: list[str],
    l2_names: list[str],
    batches: list[dict],
) -> str:
    replacements = {
        "TASKS": js_json(tasks),
        "L1": js_json(l1_names),
        "L2": js_json(l2_names),
        "L1DESC": js_json({item["name"]: item["description"] for item in taxonomy["l1"]}),
        "L2DESC": js_json({item["name"]: item["description"] for item in taxonomy["l2"]}),
        "BATCHES": js_json(batches),
    }
    rendered = template
    for name, value in replacements.items():
        rendered, count = re.subn(
            rf"^const {name}=.*;$",
            lambda _: f"const {name}={value};",
            rendered,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            fail(f"could not locate exactly one const {name}=... line in index.html")

    legacy = [item["name"] for item in taxonomy["l1"] if item.get("type") == "legacy"]
    rendered, count = re.subn(
        r"^const LEGACY=new Set\(.*\);$",
        lambda _: f"const LEGACY=new Set({js_json(legacy)});",
        rendered,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        fail("could not locate exactly one LEGACY definition in index.html")
    return rendered


def render_csv(tasks: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(tasks[0].keys()), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(tasks)
    return "\ufeff" + output.getvalue()


def write_or_check(outputs: dict[Path, str], check: bool) -> None:
    stale: list[Path] = []
    for path, content in outputs.items():
        if check:
            current = path.read_bytes() if path.exists() else None
            if current != content.encode("utf-8"):
                stale.append(path.relative_to(ROOT))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    if stale:
        for path in stale:
            print(f"stale generated file: {path}", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate inputs and fail if generated files are out of date",
    )
    args = parser.parse_args()

    tasks = load_json(ROOT / "data/task_catalog.json")
    taxonomy = load_json(ROOT / "data/taxonomy.json")
    l1_names, l2_names, batches = validate_and_derive(tasks, taxonomy)
    template = (ROOT / "index.html").read_text(encoding="utf-8")
    html = render_html(template, tasks, taxonomy, l1_names, l2_names, batches)

    taxonomy_text = json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n"
    outputs = {
        ROOT / "index.html": html,
        ROOT / "site/index.html": html,
        ROOT / "data/task_catalog.csv": render_csv(tasks),
        ROOT / "data/taxonomy.json": taxonomy_text,
        ROOT / "task_titles/all_task_titles.txt": "".join(
            f"{task['task_title']}\n" for task in tasks
        ),
    }
    for batch in batches:
        outputs[ROOT / f"task_titles/{batch['batch']}.txt"] = "".join(
            f"{task['task_title']}\n" for task in tasks if task["batch"] == batch["batch"]
        )

    write_or_check(outputs, args.check)
    action = "Validated" if args.check else "Rebuilt"
    print(
        f"{action} {len(tasks)} records, {len(l1_names)} L1 buckets, "
        f"{len(l2_names)} L2 families, and {len(batches)} batches."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
