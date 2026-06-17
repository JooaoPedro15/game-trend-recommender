# Release Checklist (v1.0)

Run this before making the repository public, cutting a release, or showing the project to
someone. It is a repeatable pre-flight — the security items (API key, `.env`) are the ones
where a mistake is costly, so do not skip them.

Tick every box. If any check fails, fix it before sharing.

## Quick verification commands

```bash
# 1. All tests pass
python -m pytest

# 2. Working tree is clean (nothing unexpected staged or untracked)
git status --short

# 3. .env is ignored by Git (prints the matching .gitignore rule)
git check-ignore -v .env

# 4. No real API key leaked (only variable-name usages should appear)
git grep "YOUTUBE_API_KEY"
```

How to read the output:

- **`python -m pytest`** → ends with `N passed` and no failures.
- **`git status --short`** → empty, or only changes you intend to commit. No `__pycache__/`,
  no `.env`, no personal data files.
- **`git check-ignore -v .env`** → prints a line like `.gitignore:18:.env  .env`. If it
  prints **nothing**, `.env` is NOT ignored — stop and fix `.gitignore`.
- **`git grep "YOUTUBE_API_KEY"`** → only the variable name in code, tests (fake keys such
  as `CHAVE_FAKE`), `.env.example` and docs. A real key (long random string) must never
  appear.

## Checklist

- [ ] **Tests pass** — `python -m pytest` is green.
- [ ] **`.env` is ignored** — `git check-ignore -v .env` prints a matching rule; `.env`
      never appears in `git status`.
- [ ] **`.env.example` has no real key** — only the variable *names* with empty values
      (`YOUTUBE_API_KEY=`, `MEU_CANAL_YOUTUBE_ID=`).
- [ ] **README is up to date** — features, the main workflow, the CLI command table and the
      project status match the current code.
- [ ] **Main commands work** — the offline ones run without any key:
      `python src/main.py status_sistema`, `python src/main.py validar_dados`,
      `python src/main.py ranking --top 5`, `python src/main.py --help`.
- [ ] **Only safe example data is committed** — the CSVs in `data/` are fictional examples
      or data you are comfortable publishing (see `docs/publicacao_github.md`).
- [ ] **No `__pycache__` is tracked** — `git ls-files | grep __pycache__` returns nothing.
- [ ] **Sensitive personal reports are out of the commit** — real `reports/` exports or
      private channel data stay local (use `data/private/` or `*.local.csv`), not in Git.
- [ ] **API key is not leaked** — `git grep "YOUTUBE_API_KEY"` shows only variable-name
      usages; the real key lives only in your local `.env`.
- [ ] **(Optional) Screenshots** — if you want them in the README, add example output of
      `ranking` or `relatorio_diario`, taken from fake/example data only.

## Notes

- The runtime uses the standard library only; `pytest` is the single dev dependency.
- Nothing in this repository should require a real API key to review: the whole ranking and
  reporting pipeline runs offline from the example CSVs.
