---
description: Stage, commit with conventional message, and push to GitHub
---

# Git Push Workflow

Use this workflow after completing a meaningful unit of work to push changes to GitHub.

## Steps

1. Check the current git status to see what files changed:
```bash
git status --short
```

// turbo
2. Stage all changes:
```bash
git add -A
```

3. Generate a conventional commit message based on the changes and commit. Use one of these prefixes:
   - `feat:` — new feature or file
   - `docs:` — documentation changes (PRD, ADR, README, etc.)
   - `fix:` — bug fix
   - `refactor:` — code restructuring
   - `chore:` — config, tooling, CI
   - `test:` — adding or updating tests

   Example:
```bash
git commit -m "docs: publish Authority Pack (PRD, ADRs, System Design, Roadmap)"
```

// turbo
4. Push to the remote on the current branch:
```bash
git push origin main
```

## Notes
- The workflow runs from the current working directory. Git reads `.git/config` to determine the remote URL automatically.
- If no remote is set, you will need to add one first: `git remote add origin <your-github-url>`
- Always review the `git status` output before committing.
