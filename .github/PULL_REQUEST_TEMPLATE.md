## What and why

<!-- One platform or one runtime change per pull request. -->

## Evidence

<!-- For catalog changes: the documentation pages you opened (URLs) and the date. Anything UNCONFIRMED? -->

## Checklist

- [ ] `python -m platform_mcp_hub lint` has no errors
- [ ] `python tools/gen_all.py` leaves no diff (generated files committed)
- [ ] `python -m pytest -q tests` and `node --test tests/*.test.mjs` pass
- [ ] New or changed entries have contract tests in both languages; runtime changes are in both runtimes
- [ ] Live check (`platform-mcp-hub verify --only <category>/<id> --lang both`) if the platform is keyless, or why not
- [ ] No secrets, account data or recorded responses containing them
- [ ] `CHANGELOG.md` updated for user-visible changes
- [ ] Commits are signed off (`git commit -s`, DCO)
