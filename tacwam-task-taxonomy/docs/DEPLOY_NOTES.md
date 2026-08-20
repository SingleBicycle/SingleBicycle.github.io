# Hosting Recommendation

## Recommended: GitHub Pages

This package is a static HTML/CSS/JavaScript site. GitHub Pages is the simplest long-term default because the repository itself becomes the source of truth and any future coding agent can update the same project. The S3 recordings page fetches its committed aggregate JSON snapshot from `data/`; it never connects to AWS from the browser.

Suggested repository: `tacwam-task-taxonomy`

Suggested layout:

```text
/
  index.html
  data/
  task_titles/
  docs/
  README.md
  AGENT_PROMPT.md
```

No deployment-time build step is required. Refresh the S3 snapshot before publishing when current recording statistics are needed.

## Alternatives

Vercel or Netlify are suitable fallbacks. Keep GitHub as the canonical repository even if deployment is handled by another host.

## Privacy note

Do not assume a private repository automatically gives a private hosted site. Confirm organization access-control requirements before publishing internal task catalogs to a public URL.
