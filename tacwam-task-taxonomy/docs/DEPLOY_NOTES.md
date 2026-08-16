# Hosting Recommendation

## Recommended: GitHub Pages

This package is a self-contained static HTML/CSS/JavaScript site. GitHub Pages is the simplest long-term default because the repository itself becomes the source of truth and any future coding agent can update the same project.

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

No build step is required.

## Alternatives

Vercel or Netlify are suitable fallbacks. Keep GitHub as the canonical repository even if deployment is handled by another host.

## Privacy note

Do not assume a private repository automatically gives a private hosted site. Confirm organization access-control requirements before publishing internal task catalogs to a public URL.
