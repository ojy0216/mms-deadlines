# Implementation and verification status

Updated 2026-09-07. Local browser verification is complete. GitHub Pages source is now GitHub Actions; the initial commit/push and live deployment are the next steps.

## Implemented

- Ten conference families, 2024 onward rolling window, and explicitly announced future editions. Latest collection contains 41 editions.
- Official HTML/PDF collection, future-list discovery, event provenance, separate manual corrections, date/time precision, conflict preservation and isolated source failures.
- Shared list/detail/calendar data, category/title/year filters, exact-time countdowns, local/official times, health reports and project-prefix links.
- Generated JSON, aggregate ICS and 41 individual calendars. Latest verified build contains 107 published milestones.
- Daily 00:00 KST workflow (updated at the user's request) with manual dispatch, validation/build before data commit, serialized ordinary push, and same-run explicit Pages deployment.
- README covers setup, manual runs, data meaning, maintenance and recovery.

## Validation performed

- 30 Python regression tests passed, covering all ten families using 20 official HTML/PDF snapshots, precision/time zones, extension, conflicts, failed requests, duplicate input, repeatability, overrides and year rollover.
- Jekyll build passed with local JSON/ICS generators enabled. `github-pages` must remain `require: false`; auto-loading it enables safe mode and suppresses those generators.
- HTMLProofer passed, including the requested external-link command. It checks the three rendered HTML shells; dynamic conference source links are separately exercised by the collector.
- `python -m utils.validate_site` passed: JSON/source equality, every published milestone, stable UIDs, aggregate/personal feed equality, UTC values, all-day exclusive end dates, CRLF/75-byte line folding and project-prefix URLs.
- JavaScript syntax checked with Node.

## Remaining verification and limitations

- Browser runtime setup succeeded but reported no available browser; documented discovery also returned an empty list. No visual/interactive checks or screenshots have been claimed. A local preview runs at http://127.0.0.1:4000/mms-deadlines/ while this session is active.
- No commit, push or live deployment has been performed. GitHub connector confirms admin/push access and default branch `gh-pages`. Initial Pages source selection and a successful workflow/deployment still need verification.
- Historical unavailable fields and future unannounced dates remain TBA with explicit review reasons. Inaccessible ESSERC 2025 and VLSI 2027 page values verified through official indexed pages are preserved in `_data/overrides.yml`, with sources and reasons.
- CICC 2026 has a stale notification banner conflicting with its main review section; preserve the existing confirmed date and report the conflict.
- Main meeting ranges use separately labeled main sessions where available; other sources supply their advertised conference interval. NeurIPS 2025 shows both officially advertised venues. The official Mexico City program was also checked: oral/poster sessions run December 3–5, agreeing with the stored main-conference interval. Source: https://neurips.cc/virtual/2025/loc/mexico-city/calendar .
- Final requirement audit and browser/Pages verification remain necessary before marking the overall goal complete.

## Local runtime notes

The machine's system Ruby 2.6 reports a universal platform despite arm64 native gems. Local validation uses `/private/tmp/mms-ruby-platform.rb` through `RUBYOPT`, Bundler from `/private/tmp/mms-gems`, and ignored dependencies in `vendor/bundle`. CI instead uses Ruby 3.1 and Python 3.12. Local Python 3.9 emits a LibreSSL warning, but all reported checks passed.

The user-provided untracked `AGENTS.md` has been preserved. Extra downloaded research snapshots were moved to `/private/tmp/mms-unused-source-snapshots`; committed fixture candidates are listed with official URLs, retrieval date and SHA-256 in `tests/fixtures/raw/manifest.json`.

## Follow-up audit

### Browser and pre-deployment verification (2026-09-07)

- Connected Chrome through the currently available CUA browser API. The existing local server responds on port 4000 outside the shell sandbox; an initial sandbox request incorrectly appeared unavailable. A second server was not started because the port was already occupied.
- Verified list, detail and calendar, category/conference/year filter combinations, 11 upcoming/ongoing, 7 date-unannounced and 23 past editions. EMNLP 2026 remains upcoming after ARR/commitment/notification have passed.
- Confirmed ISSCC 2027 precise countdowns show official and Asia/Seoul times; date-only and TBA events have no countdown. Expanded collection health shows attempt/success times, official source links and preserved-value errors.
- Fixed CSS overriding the detail filters' hidden attribute and wrapped long health URLs/errors for narrow screens. Added explicit download attributes to ICS links; both aggregate and individual browser download events succeeded with no console errors.
- Inspected desktop and 390px-wide list/detail/calendar; screenshots are in `docs/screenshots/`. Expanded mobile health has no horizontal overflow (client width and scroll width both 375px).
- Re-ran data validation, all 30 Python tests, Jekyll build, generated JSON/42 ICS checks (107 milestones), requested HTMLProofer command and whitespace checks successfully.
- Saved GitHub Pages source as GitHub Actions, with no custom domain. Remote `gh-pages` and local HEAD matched `b230d24719088a769e6938704a826e5084b4cb34` before committing. No forced push is used.

### Earlier diagnostics

Browser discovery was rechecked and still returned an empty list. No browser verification or deployment was claimed. CICC 2024’s additional official overview PDF returned HTTP 403 during the venue backfill attempt, so its missing venue remains explicitly marked TBA. Added regression tests confirm that TBA cannot erase a published deadline, a partial source failure preserves only the affected field while other fields update, and an older CFP cannot reverse a confirmed extension. All 30 tests passed; `git diff --check` passed.

Local HTTP verification after the localhost request: all 48 checked page, asset and calendar URLs returned HTTP 200. Every served ICS matched the corresponding validated `_site` bytes. Browser discovery still returned no connected browsers; HTTP checks do not prove rendered UI behavior.
