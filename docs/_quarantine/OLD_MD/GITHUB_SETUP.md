# GitHub Setup for northstar-engines

Canonical remote: `https://github.com/jamienowman-glitch/engine`
Default branch: `main`

## Switch origin to jamienowman-glitch/engine
```bash
cd ~/dev/northstar-engines
git remote set-url origin https://github.com/jamienowman-glitch/engine.git
git push --set-upstream origin main
```

## Auth
- Use HTTPS with Git credential helper (macOS keychain) and a PAT for `jamienowman-glitch` (scope: `repo`).
- Avoid embedding the PAT in the remote URL; Git will prompt on first push.

## Notes
- Do not change env var, GSM secret, or connector naming patterns; see `docs/infra/CONNECTORS_SECRETS_NAMING.md` and `docs/02_REPO_PLAN.md`.
