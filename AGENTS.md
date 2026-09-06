# Repository Guidelines

## Project Structure & Module Organization

This repository is a Jekyll site for AI conference deadline countdowns. `_data/conferences.yml` holds conference records; `_data/types.yml` defines subject categories. Root pages (`index.html`, `calendar.html`) use Liquid templates and shared fragments in `_includes/`. `_pages/` contains the conference page, `_layouts/` contains the calendar feed layout, and `_plugins/` contains Ruby page-generation code. Assets live under `static/css/`, `static/js/`, `static/img/`, and `static/fonts/`. `utils/process.py` supports data cleanup. Generated output goes into ignored `_site/`.

## Build, Test, and Development Commands

Run commands from the repository root with Ruby and Bundler installed:

- `bundle install`: install dependencies from `Gemfile` and `Gemfile.lock`.
- `bundle exec jekyll serve --future`: build and serve locally at `http://localhost:4000`.
- `bundle exec jekyll build --future`: generate the site using the build command in `.travis.yml`.
- Run the existing HTML/link validation after building:

```sh
bundle exec htmlproofer ./_site --only-4xx --check-favicon --check-html --url-ignore "/#.*/" --http-status-ignore "400,441"
```

## Coding Style & Naming Conventions

Match surrounding formatting; use two-space indentation in YAML, CSS, and JavaScript, and four spaces in Python. Preserve existing Ruby and Liquid conventions. No formatter or linter configuration is checked in. Avoid editing bundled minified libraries for application changes.

Conference IDs use a lowercase title plus two-digit year, such as `cvpr25`; keep IDs unique. Include `title`, `year`, `id`, `link`, `deadline`, `timezone`, `date`, `place`, and `sub`. Quote deadline timestamps as `'YYYY-MM-DD HH:MM:SS'`. Use supported timezone names or existing UTC-offset conventions and subject codes from `_data/types.yml`.

## Testing Guidelines

There is no dedicated unit-test suite or coverage threshold. Build the site and run HTMLProofer. For data updates, verify dates and timezones against the official conference announcement. For interface changes, manually check countdowns, subject filters, the calendar, and calendar downloads in the local preview. Distinguish external-link failures from rendering errors when reporting validation.

## Commit & Pull Request Guidelines

History uses short descriptive subjects such as `Added CVPR 2025` and `fix AISTATS`; no enforced prefix convention is evident. Keep commits focused. In pull requests, describe the change, link official sources for deadline updates and related issues when applicable, and report validation results. Include screenshots for visible interface changes.
