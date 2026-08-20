# TacWAM Task Taxonomy Explorer — English Interactive Version

This directory contains two linked static views: the historical **task-title catalog** and an aggregate **S3 recording inventory**. The recording page reports coverage and duration; it is not a replacement for the vendor QA pipeline.

## Current scope

- **302** historical task-title records
- **297** normalized semantic keys
- **7** core L1 scenes + **2** legacy/general buckets
- **12** L2 manipulation/contact families
- **5** source task-list batches

## Website

Open `index.html` or `site/index.html`.

The main visualization is an **interactive two-ring hierarchy chart**:

- **Inner ring:** L1 scene
- **Outer ring:** L2 skill families within each L1 scene
- Hover shows scene, skill, count, share of all tasks, and share within the scene
- Click a segment to filter the task registry
- Click the chart center or **Clear selection** to reset

The linked `s3-recordings/index.html` view applies the same taxonomy to complete recordings currently present under the configured S3 date prefixes. It includes:

- complete recording count and excluded incomplete-upload count
- total recorded duration
- recording-count and duration-weighted hierarchy views
- per-task total, median, and P90 duration
- per-date recording and duration summaries
- visible mapping provenance for catalog-linked and rule-classified S3 task names

## Important data convention

The website UI, taxonomy labels, and primary task display titles are English. The original canonical task title is retained as a secondary field so historical PDFs, vendor labels, and source records still match exactly.

## Key files

- `index.html` — deployable static website
- `site/index.html` — duplicate deployable entrypoint
- `data/task_catalog.csv` — enriched master catalog
- `data/task_catalog.json` — same catalog as JSON
- `data/taxonomy.json` — English taxonomy metadata
- `task_titles/*.txt` — canonical title-only exports
- `docs/PROJECT_SUMMARY.md`
- `docs/CURRENT_TASK_SUMMARY.md`
- `docs/TAXONOMY_REVIEW_NOTES.md` — open classification questions; no silent reassignment
- `docs/DEPLOY_NOTES.md`
- `AGENT_PROMPT.md`
- `scripts/build_site.py` — validates catalog inputs and refreshes generated static files
- `scripts/build_s3_inventory.py` — read-only S3 inventory refresh; writes aggregate metadata only
- `data/s3_recordings_summary.json` — deployable aggregate snapshot with no object paths or recording IDs
- `data/s3_task_aliases.json` — reviewed S3-title to catalog-record aliases
- `s3-recordings/index.html` — S3 recording taxonomy and duration page

## Add a future task-list batch

1. Append enriched records to `data/task_catalog.json`. Keep `task_title` unchanged as the canonical source-language title, add `task_title_en` for display, and assign the existing English L1/L2 labels explicitly.
2. Run `python3 scripts/build_site.py`. It validates identifiers and taxonomy labels, then refreshes the CSV, title exports, taxonomy counts, and both self-contained HTML entrypoints.
3. If any assignment is uncertain, add it to `docs/TAXONOMY_REVIEW_NOTES.md`; do not change the taxonomy silently.
4. Preview with `python3 -m http.server 8000`, review the diff, then commit and push the default branch. GitHub Pages will publish the updated root `index.html`.

The build step only keeps the catalog artifacts synchronized. It does not classify tasks or run vendor QA.

## Refresh the S3 recording page

Install `requirements-s3.txt`, provide AWS credentials through the standard environment or AWS profile, then run:

```bash
python3 scripts/build_s3_inventory.py
```

By default the snapshot includes top-level prefixes matching `^itw\d{2}-\d{2}$`. A recording is included only when `task_info.json` and the required camera, wrist, and tactile files are present and larger than 100 bytes. The committed snapshot is aggregate-only: it does not contain credentials, recording UUIDs, or S3 object paths.

Catalog titles are matched first. Previously unseen S3 title variants are classified reproducibly from `task_scene` and ordered title rules, and their mapping method remains visible in the registry so it can be reviewed rather than presented as hand-verified taxonomy.

## Visual direction
The current UI follows a restrained enterprise/data-dashboard direction: neutral surfaces, minimal decoration, categorical color only where it carries taxonomy meaning, and sequential blue for density/coverage.
