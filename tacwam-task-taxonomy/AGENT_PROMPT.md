# Prompt for Codex / Claude Code

You are taking over a static website project called **TacWAM Task Taxonomy Explorer**.

## Goal

Publish the supplied **English, interactive taxonomy website** as a long-lived URL and keep the GitHub repository easy to update when new task lists arrive.

The current handoff covers **task taxonomy and coverage only**. Do **not** build the vendor QA / automated data-quality pipeline yet.

## Current website design

The website is intentionally professional and minimal. Preserve this design direction.

The main visualization is a **two-ring hierarchical donut / sunburst-style chart**:

- **Inner ring = L1 scene**
- **Outer ring = L2 skill family within each L1 scene**
- Hover must show: L1 scene, L2 skill (when applicable), task count, share of all tasks, and share within the selected scene
- Clicking an inner-ring scene filters the task registry by L1
- Clicking an outer-ring segment filters by both L1 and L2
- The center control resets the selection

The site also includes:

- total task count and taxonomy summary
- coverage insights
- L1 × L2 coverage matrix
- searchable / filterable task registry
- taxonomy definitions
- source batch summary

## Data conventions

1. Preserve taxonomy semantics:
   - L1 = scene
   - L2 = primary manipulation/contact family
   - 7 core scenes + 2 legacy/general buckets
   - 12 L2 families
2. The UI and taxonomy labels are English.
3. Display the supplied `task_title_en` as the primary English title, but **do not overwrite `task_title`**, which remains the canonical source-language title for exact historical/vendor matching.
4. Do not add task execution details to the task registry. Keep it title-centric.
5. If a task appears misclassified, create a separate review note or PR comment; do not silently change taxonomy assignments.
6. Keep the site static. No backend or database is needed at this stage.
7. Keep the interaction dependency-free unless there is a strong reason to add a small pinned library. The provided version is self-contained HTML/CSS/vanilla JS.

## Preferred hosting

Use **GitHub Pages** first, with GitHub as the source of truth.

Preferred repository name: `tacwam-task-taxonomy`

If repository access is available:

1. Create or use the repository.
2. Put the deployable `index.html` at the repository root.
3. Commit all handoff files.
4. Push to GitHub.
5. Enable GitHub Pages from the default branch/root.
6. Verify the live URL on desktop and mobile widths.
7. Report the final URL, repository, branch, and deployment method.

If GitHub Pages is not suitable, deploy to Vercel or Netlify while keeping GitHub as the source of truth.

## Privacy

Before public deployment, confirm that task titles and internal project naming are allowed to be public. Do not assume a private GitHub repository automatically produces a private Pages site.

## Definition of done

Return:

1. live website URL
2. GitHub repository URL/name
3. deployment method
4. files changed
5. concise instructions for adding a future task-list batch


## Visual design guardrails

Maintain a restrained enterprise/data-product visual language.

- Use neutral gray surfaces and borders as the dominant UI.
- Use blue for interaction/focus states only.
- Use the defined categorical palette only for taxonomy encoding.
- Use sequential blue values for the coverage matrix.
- Do not add gradients, glassmorphism, glow effects, decorative AI motifs, oversized rounded cards, or excessive pill badges.
- Keep radii small (0–2 px for most controls and panels).
- Prefer flat layout, clear dividers, compact typography, and information density similar to mature engineering/data products.
- Preserve the nested donut interaction: inner ring = L1 scene, outer ring = L2 skill.
