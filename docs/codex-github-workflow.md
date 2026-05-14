# Codex GitHub Workflow

This file records the GitHub repository and PR workflow used by this local OA workspace so parallel Codex sessions can coordinate safely.

## Repository

- Local workspace: `C:\Users\946355064\Desktop\OA-main`
- GitHub repository: `https://github.com/ZLZ1995/OA`
- Git remote name: `origin`
- Fetch URL: `https://github.com/ZLZ1995/OA`
- Push URL: `https://github.com/ZLZ1995/OA`
- Main/base branch: `main`
- Current Codex working branch: `codex/independent-invoice-archive-fix`

## Upload / Push

Push local commits to the current Codex branch:

```powershell
git push origin codex/independent-invoice-archive-fix
```

If GitHub push fails because the local proxy is unavailable, retry once with proxy disabled only for that command:

```powershell
git -c http.proxy= -c https.proxy= push origin codex/independent-invoice-archive-fix
```

Current proxy values observed in this workspace:

```text
http.proxy=http://127.0.0.1:9910
https.proxy=http://127.0.0.1:9910
```

## Pull Request

Create or update a PR from:

- Base: `main`
- Compare/head: `codex/independent-invoice-archive-fix`

PR creation URL:

```text
https://github.com/ZLZ1995/OA/compare/main...codex/independent-invoice-archive-fix?expand=1
```

If a PR already exists for this branch, pushing new commits to `codex/independent-invoice-archive-fix` automatically updates that PR.

## Merge

Recommended merge path:

1. Push all local commits to `origin/codex/independent-invoice-archive-fix`.
2. Open the GitHub PR from `codex/independent-invoice-archive-fix` into `main`.
3. Confirm the PR diff and checks.
4. Merge the PR into `main` through GitHub.

Avoid force-pushing or rewriting branch history unless the user explicitly approves it.

## Safety Notes

- Do not use `git reset --hard` or destructive checkout commands without explicit approval.
- The worktree may contain user or parallel-agent edits; check `git status --short --branch` before committing.
- Prefer small descriptive commits for each completed change set.
