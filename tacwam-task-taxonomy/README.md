# TacWAM Task Taxonomy Explorer — English Interactive Version

This handoff contains the current **task-title taxonomy and coverage website only**. The vendor QA / automated data-quality pipeline is intentionally deferred.

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

## Add a future task-list batch

1. Append enriched records to `data/task_catalog.json`. Keep `task_title` unchanged as the canonical source-language title, add `task_title_en` for display, and assign the existing English L1/L2 labels explicitly.
2. Run `python3 scripts/build_site.py`. It validates identifiers and taxonomy labels, then refreshes the CSV, title exports, taxonomy counts, and both self-contained HTML entrypoints.
3. If any assignment is uncertain, add it to `docs/TAXONOMY_REVIEW_NOTES.md`; do not change the taxonomy silently.
4. Preview with `python3 -m http.server 8000`, review the diff, then commit and push the default branch. GitHub Pages will publish the updated root `index.html`.

The build step only keeps the catalog artifacts synchronized. It does not classify tasks or run vendor QA.

## Visual direction
The current UI follows a restrained enterprise/data-dashboard direction: neutral surfaces, minimal decoration, categorical color only where it carries taxonomy meaning, and sequential blue for density/coverage.
