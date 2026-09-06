# Implementation and verification status

Updated 2026-09-07. Implementation, local visual verification, ordinary push and live GitHub Pages deployment are complete.

## Live deployment

- Site: https://ojy0216.github.io/mms-deadlines/
- Successful run: https://github.com/ojy0216/mms-deadlines/actions/runs/34047195498
- Job/logs: https://github.com/ojy0216/mms-deadlines/actions/runs/34047195498/job/101524260050
- Implementation commit: `5984443`; pushed merge: `c9a9e72`; same-run automatic data commit: `d3d729e`.
- Pages source is GitHub Actions, custom domain is empty, HTTPS is enforced.
- Daily schedule is **00:00 KST**, cron **`0 15 * * *`**, with `workflow_dispatch` retained. GitHub scheduling may be delayed; configuration is not an exact-start guarantee.
- Run #1 succeeded in 1m 15s. Logs show 41 collected editions, 30 passing tests, 107 published milestones in JSON and 42 ICS files, ordinary data push `c9a9e72..d3d729e`, and Pages `Reported success!`.
- Artifact `9993470818` was built and deployed by the same execution after collection, validation, build and data commit. Failed validation/build/push blocks later deployment steps. `conference-pages` concurrency serializes executions without forced push.

## Scope delivered

- Circuit: ISSCC, VLSI, CICC, ESSERC. Algorithm: NeurIPS, ICLR, ICML, EMNLP, ECCV, ICCV.
- Rolling hosting-year window (current year and previous two years), plus officially announced future editions. URL-year substitution alone is not announcement evidence.
- Official HTML/PDF collection and future-list discovery, per-event provenance, time precision, conflict preservation, isolated source failures and separate `_data/overrides.yml` corrections.
- Abstract/paper submission, EMNLP ARR/commitment, notification, meeting dates and venue. Workshops and additional submission tracks are excluded. Separately labeled main-session dates are preferred; otherwise the advertised meeting interval is retained.
- Shared list/detail/calendar/ICS data, category/conference/year filters, local and official times, precise-time-only countdowns, collection health and source links.
- README documents setup, manual sync, missing data, source recovery and overrides. User-provided `AGENTS.md` is preserved.

## Verification evidence

All requested commands passed locally with the Ruby environment below:

```sh
.venv/bin/python -B -m utils.collector.sync --validate-only
.venv/bin/python -B -m unittest discover -s tests
bundle exec jekyll build --future
.venv/bin/python -B -m utils.validate_site
bundle exec htmlproofer ./_site --only-4xx --check-favicon --check-html --url-ignore '/#.*/' --http-status-ignore '400,441' --url-swap '^/mms-deadlines/:/'
git diff --check
```

- All 30 tests also passed in Actions on Python 3.12. Twenty official HTML/PDF fixtures cover all ten families, precision/timezones, extensions, conflicting/failed sources, duplicate input, repeated runs, overrides and year rollover. Original fixture bytes and manifest SHA-256 hashes are preserved using `.gitattributes`.
- JSON/source equality, all 107 published milestones, stable UIDs, aggregate/personal feed equality, UTC instants, all-day exclusive end dates, CRLF/75-byte folding and project-prefix URLs passed the generated-site validator.
- HTMLProofer passed on all three HTML shells. Dynamic source access is separately exercised by the collector; external failures are listed below.
- Local and public HTTP checks each verified **49 URLs** with status 200 and exact byte equality to the rebuilt latest data: three HTML pages, JSON, CSS, JavaScript, favicon, aggregate ICS and all 41 individual feeds.
- Public pages displayed the Actions collection timestamp **2026-09-07 02:00:29 KST**. Public JSON/ICS matched Actions data commit `d3d729e`, proving newly collected data was included in the same-run deployment.

## Browser checks

- Used the current CUA Chrome connection with fresh discovery. The existing local server on port 4000 was reused. Shell sandbox restrictions initially made it appear unreachable; an unsandboxed check confirmed it, so no duplicate server was started.
- Inspected desktop and 390px-wide list/detail/calendar. Screenshots: [desktop list](screenshots/list-desktop.png), [desktop detail](screenshots/detail-desktop.png), [desktop calendar](screenshots/calendar-desktop.png), [mobile list](screenshots/list-mobile.png), [mobile detail](screenshots/detail-mobile.png), [mobile calendar](screenshots/calendar-mobile.png), [deployed list](screenshots/deployed-list.png).
- Verified Circuit/2027 and Algorithm/EMNLP/2026 filter combinations. EMNLP 2026 stays upcoming after submissions and notification have passed. Records separate into 11 upcoming/ongoing, 7 meeting-date-unannounced and 23 past editions at verification time.
- ISSCC 2027 detail shows official timestamps, Asia/Seoul conversions and ticking countdowns. Date-only/TBA events have no countdown. EMNLP detail and calendar keep ARR and commitment distinct.
- Expanded health shows attempt/success, source links and per-conference issues. At 390px viewport, expanded health had client/scroll widths of 375px with no horizontal overflow.
- Fixed CSS overriding the detail filter's `hidden` attribute and wrapped long health errors/URLs. Explicit ICS download attributes prevent navigating away. Aggregate and individual download events succeeded locally and publicly. Public list, filtered detail and calendar showed no console errors.

## Remaining official-data limitations

The 41 editions contain **107 published** and **57 TBA milestones**, with 23 editions flagged for review. These are explicit source limitations, not inferred dates.

- Meeting dates remain TBA for ICCV 2027/2029/2031, NeurIPS 2027/2028 and ICML 2027/2028. These future editions have official announcement evidence.
- Venue remains TBA for CICC 2024 and ICCV 2029. CICC 2024's additional official overview PDF returned HTTP 403 during historical backfill.
- VLSI 2027 source `https://dev.vlsisymposium.org/` returns HTTP 401. Its verified deadline is preserved in the override.
- ESSERC 2025 source `https://www.esserc2025.org/papers` refuses connections. Previously verified paper/notification values remain in overrides with official URLs and reasons.
- CICC 2026 official notification sources conflict; the previous confirmed value is preserved and marked for review.
- Other unavailable historical or unannounced milestones remain TBA; detail pages and `_data/sync_status.yml` identify them. NeurIPS 2025 retains both officially advertised venues; its official Mexico City program confirms December 3–5 main sessions.
- Actions emitted a non-blocking Node 20 action-runtime deprecation notice while successfully running under Node 24. No security setting was weakened.

## Local runtime and publication notes

System Ruby 2.6 reports a universal platform despite arm64 native gems. Local commands use:

```sh
GEM_HOME=/private/tmp/mms-gems GEM_PATH=/private/tmp/mms-gems \
RUBYOPT=-r/private/tmp/mms-ruby-platform.rb \
/private/tmp/mms-gems/bin/bundle exec jekyll build --future
```

The platform helper sets `Gem::Platform.local` to `arm64-darwin-25`. Dependencies are ignored in `vendor/bundle`. Local Python 3.9 emits a LibreSSL warning; CI uses Ruby 3.1/Python 3.12 and passes. Keep `github-pages` as `require: false`: auto-loading enables safe mode and skips the local JSON/ICS generator.

The HTTPS Git token lacked workflow scope and SSH authentication was unavailable. The same verified workflow was registered through the already-authenticated web editor (`aa4a249`, initial registration skipped CI), merged locally without content changes, then the full implementation was pushed normally. No token permission expansion, forced push, reset or loss of existing changes was used. The Actions data commit was pulled with `--ff-only` for final public verification.

## Upcoming ordering follow-up (2026-09-07)

Upcoming & ongoing cards now sort by their next published milestone, earliest first, using the same event selection as the card's Next label. Ties use the conference ID; missing milestones sort last. Category filters retain this order. Local browser verification (all categories and Algorithm), Jekyll build, HTMLProofer and `git diff --check` passed. Screenshot: `docs/screenshots/upcoming-sorted.png`.
