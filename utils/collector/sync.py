"""Daily bounded collection with failure isolation and atomic output."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests
import yaml

from .model import TITLES, in_window, merge_events, new_record, validate
from .parsers import announcement_entries, assert_edition, discover, document, parse_source

ROOT = Path(__file__).resolve().parents[2]


def read_yaml(path, default):
    return yaml.safe_load(path.read_text()) if path.exists() else default


def atomic_yaml(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120))
    temporary.replace(path)


class Fetcher:
    def __init__(self, cache=None):
        self.cache = cache
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'mms-deadlines/1.0 (official academic schedule monitor)'
        self.memo = {}

    def __call__(self, url):
        if url in self.memo:
            return self.memo[url]
        if urlparse(url).scheme != 'https':
            raise ValueError('Only HTTPS official sources are supported')
        response = self.session.get(url, timeout=(10, 35))
        response.raise_for_status()
        if len(response.content) > 20_000_000:
            raise ValueError('Source exceeds 20 MB')
        self.memo[url] = response.content
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)
            (self.cache / (sha256(url.encode()).hexdigest() + '.bin')).write_bytes(response.content)
        return response.content


def discover_editions(config, fetch, year):
    candidates, errors = {}, []
    for root in config['discovery']:
        try:
            candidates.update(discover(fetch(root), root, config['title'], config['hosts'], year - 2))
        except Exception as exc:
            errors.append(f'{root}: {type(exc).__name__}: {exc}')
    for source in config.get('announcements', []):
        try:
            entries = announcement_entries(fetch(source['url']), source, config['title'])
            for edition_year in entries:
                if edition_year >= year:
                    candidates.setdefault(edition_year, dict(url=source['url'], discovered_from=source['url'], source=source))
        except Exception as exc:
            errors.append(f"{source['url']}: {type(exc).__name__}: {exc}")
    return candidates, errors


def source_for_discovery(config, candidate, fetch, year):
    if candidate.get('source'):
        return candidate['source']
    url = candidate['url']
    body = fetch(url)
    pdf = body.startswith(b'%PDF')
    text, soup = document(body, pdf)
    if pdf:
        source = {**deepcopy(config.get('discovered_pdf', {})), 'url': url, 'format': 'pdf',
                  'identity': rf'{config["title"]}\s*{year}\b'}
        assert_edition(text, soup, source, config['title'], year)
        return source
    if config.get('parser') == 'eventhosts':
        links = [urljoin(url, a['href']) for a in soup.select('a[href]')
                 if a.get_text(' ', strip=True) == 'Dates' and f'/{year}/' in urljoin(url, a['href'])]
        if links:
            source = dict(url=links[0], parser='eventhosts')
            target_text, target_soup = document(fetch(links[0]))
            assert_edition(target_text, target_soup, source, config['title'], year)
            return source
    assert_edition(text, soup, {}, config['title'], year)
    # Confirmed edition can exist with TBA dates until a parser/source is registered.
    return dict(url=url, identity=rf"{config['title']}\s*{year}|{year}\s*{config['title']}")


def run(root=ROOT, now=None, fetch=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat(timespec='seconds').replace('+00:00', 'Z')
    fetch = fetch or Fetcher(root / '.sync-cache')
    registry = read_yaml(root / 'utils/sources.yml', [])
    if sorted(c['title'] for c in registry) != sorted(TITLES):
        raise ValueError('Registry must contain each of the ten conferences exactly once')
    previous = read_yaml(root / '_data/conferences.yml', [])
    # Validate before indexing: a dict would silently discard duplicate editions.
    validate(previous)
    old = {(r['title'], r['year']): r for r in previous if r['title'] in TITLES and 'events' in r}
    overrides = read_yaml(root / '_data/overrides.yml', {}) or {}
    records = []
    status = read_yaml(root / '_data/sync_status.yml', {}) or {}
    status.update(last_attempt=stamp, conferences={})
    for config in registry:
        title = config['title']
        discovered, discovery_errors = discover_editions(config, fetch, now.year)
        editions = {int(y): deepcopy(e) for y, e in config.get('editions', {}).items()}
        for (old_title, year), record in old.items():
            if old_title == title and year not in editions:
                editions[year] = dict(link=record['link'], evidence=record['edition_sources'][0], sources=record.get('collection_sources', []))
        for year, candidate in discovered.items():
            if year in editions:
                continue
            try:
                source = source_for_discovery(config, candidate, fetch, year)
                editions[year] = dict(link=candidate['url'], evidence=candidate['discovered_from'], sources=[source])
            except Exception as exc:
                discovery_errors.append(f'Discovery {year}: {exc}')
        conf_errors = list(discovery_errors)
        for year, edition in sorted(editions.items()):
            if year < now.year - 2:
                continue
            record = old.get((title, year)) or new_record(title, year, edition['link'], edition['evidence'])
            candidates, errors = [], []
            # Past editions remain eligible for missing-information repairs.
            for source in edition['sources']:
                try:
                    values, failures = parse_source(fetch(source['url']), source, title, year)
                    candidates.extend(values)
                    errors.extend(f"{source['url']}: {e}" for e in failures)
                    if not values:
                        errors.append(f"{source['url']}: schedule not announced or parser not configured")
                except Exception as exc:
                    kinds = {rule['kind'] for rule in source.get('rules', [])}
                    if source.get('parser') == 'eventhosts':
                        kinds.update(('abstract', 'paper', 'notification', 'conference'))
                    if source.get('parser') == 'emnlp':
                        kinds.update(('arr', 'commitment', 'notification', 'conference'))
                        kinds.difference_update(source.get('exclude_kinds', []))
                    if source.get('parser') == 'emnlp_program':
                        kinds.add('conference')
                    if source.get('venue_pattern'):
                        kinds.add('venue')
                    errors.extend(f"{source['url']}: {kind}: {type(exc).__name__}: {exc}" for kind in sorted(kinds or {'source'}))
            record = merge_events(record, candidates, errors, stamp, overrides.get(record['id']))
            record['collection_sources'] = edition['sources']
            records.append(record)
            conf_errors.extend(f'{year}: {e}' for e in record['issues'])
        prior_status = (read_yaml(root / '_data/sync_status.yml', {}) or {}).get('conferences', {}).get(title, {})
        checked = [r for r in records if r['title'] == title]
        conf_status = dict(last_attempt=stamp, last_success=prior_status.get('last_success'),
                           needs_review=bool(conf_errors) or not checked, issues=conf_errors,
                           sources=config['discovery'])
        if checked and all(r.get('last_success') == stamp for r in checked) and not discovery_errors:
            conf_status['last_success'] = stamp
        status['conferences'][title] = conf_status
    validate(records, require_all=True)
    unknown_overrides = set(overrides) - {r['id'] for r in records} - {
        r['id'] for r in previous if not in_window(r, now.date())}
    if unknown_overrides:
        raise ValueError(f'Unknown override IDs: {sorted(unknown_overrides)}')
    records.sort(key=lambda r: (-r['year'], TITLES.index(r['title'])))
    if any(r.get('last_success') == stamp for r in records):
        status['last_success'] = stamp
    status['record_count'] = len(records)
    atomic_yaml(root / '_data/conferences.yml', records)
    atomic_yaml(root / '_data/sync_status.yml', status)
    print(json.dumps(dict(records=len(records), review=sum(r['needs_review'] for r in records))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.validate_only:
        validate(read_yaml(ROOT / '_data/conferences.yml', []), require_all=True)
    else:
        run()
