"""Shared validation, precision, timezone and merge semantics."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo

TITLES = ('ISSCC', 'VLSI', 'CICC', 'ESSERC', 'NeurIPS', 'ICLR', 'ICML', 'EMNLP', 'ECCV', 'ICCV')
KINDS = ('abstract', 'paper', 'arr', 'commitment', 'notification', 'conference')


def zone(name):
    if name in ('AoE', 'Anywhere on Earth', 'UTC-12'):
        return timezone(timedelta(hours=-12))
    match = re.fullmatch(r'UTC([+-])(\d{1,2})(?::(\d{2}))?', name)
    if match:
        offset = timedelta(hours=int(match[2]), minutes=int(match[3] or 0))
        return timezone(offset if match[1] == '+' else -offset)
    return ZoneInfo(name)


def instant(event):
    if event['precision'] != 'datetime':
        return None
    local = datetime.fromisoformat(event['date']).replace(tzinfo=zone(event['timezone']))
    # Ambiguous and nonexistent local wall times require manual clarification.
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        raise ValueError('ambiguous or nonexistent local time')
    return local.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def missing(kind):
    return dict(kind=kind, date='TBA', precision='tba', timezone='TBA', sources=[], checked_at=None)


def new_record(title, year, link, evidence):
    kinds = ('arr', 'commitment', 'notification', 'conference') if title == 'EMNLP' else ('abstract', 'paper', 'notification', 'conference')
    return dict(title=title, year=year, id=f'{title.lower()}{year % 100:02}', link=link,
                deadline='TBA', timezone='TBA', date='TBA', place='TBA',
                sub='Circuit' if title in TITLES[:4] else 'Algorithm',
                edition_sources=[evidence], events=[missing(k) for k in kinds],
                needs_review=True, issues=['Initial collection pending'])


def merge_events(record, candidates, errors, checked_at, overrides=None):
    """Conflicts retain old values; only an explicit extension supersedes dates."""
    result = deepcopy(record)
    result['last_attempt'] = checked_at
    issues = list(errors)
    events = {e['kind']: deepcopy(e) for e in record['events']}
    for kind in events:
        choices = [c for c in candidates if c['kind'] == kind]
        if not choices:
            if events[kind]['date'] != 'TBA':
                issues.append(f'{kind}: not extracted this attempt; retained previous value')
            continue
        if any(re.search(rf'(?:^|: ){kind}:', error) for error in errors):
            issues.append(f'{kind}: parsing incomplete; retained previous value')
            continue
        extended = [c for c in choices if c.get('extended')]
        if extended:
            choices = extended
        elif events[kind].get('extended') and any(c['date'] != events[kind]['date'] for c in choices):
            issues.append(f'{kind}: older source conflicts with confirmed extension; retained previous value')
            continue
        signatures = {(c['date'], c['precision'], c.get('timezone'), c.get('end'), c.get('place')) for c in choices}
        if len(signatures) > 1:
            issues.append(f'{kind}: conflicting official sources')
            continue
        value = deepcopy(choices[0])
        if value['date'] == 'TBA' and events[kind]['date'] != 'TBA':
            issues.append(f'{kind}: official value disappeared; retained previous value')
            continue
        value['sources'] = sorted(set(s for c in choices for s in c['sources']))
        value['checked_at'] = checked_at
        if value['precision'] == 'datetime':
            value['utc'] = instant(value)
        events[kind] = value
    for kind, value in (overrides or {}).get('events', {}).items():
        if kind not in events:
            raise ValueError(f'Unknown override kind: {kind}')
        if not value.get('reason') or not value.get('sources'):
            raise ValueError('Overrides require reason and sources')
        events[kind] = {**deepcopy(value), 'kind': kind, 'manual': True}
        if value['precision'] == 'datetime':
            events[kind]['utc'] = instant(value)
    result['events'] = list(events.values())
    for kind, event in events.items():
        if event['date'] == 'TBA':
            issues.append(f'{kind}: not announced or historical source unavailable')
    conference = events['conference']
    result['date'] = conference['date'] if conference['date'] == 'TBA' else conference['date'] + ' – ' + conference.get('end', conference['date'])
    venues = [c for c in candidates if c['kind'] == 'venue']
    if conference.get('place') and conference.get('checked_at') == checked_at:
        venues.append(dict(place=conference['place'], sources=conference['sources']))
    if venues:
        if any(re.search(r'(?:^|: )venue:', error) for error in errors):
            issues.append('venue: parsing incomplete; retained previous value')
        elif len({v['place'] for v in venues}) == 1:
            result['place'] = venues[0]['place']
            result['place_sources'] = sorted(set(s for v in venues for s in v['sources']))
            result['place_checked_at'] = checked_at
        else:
            issues.append('venue: conflicting official sources; retained previous value')
    if result['place'] == 'TBA':
        issues.append('venue: not announced or historical source unavailable')
    paper = events.get('paper', events.get('arr', missing('paper')))
    result['deadline'] = paper['date'] if paper['precision'] == 'datetime' else 'TBA'
    result['timezone'] = paper.get('timezone', 'TBA')
    result['issues'] = sorted(set(issues))
    result['needs_review'] = bool(issues)
    if candidates and not errors and not any('conflicting' in i for i in issues):
        result['last_success'] = checked_at
    return result


def validate(records, require_all=False):
    if require_all:
        assert {r['title'] for r in records} == set(TITLES), 'Dataset must contain all ten conferences'
    ids, editions = set(), set()
    for record in records:
        for key in ('title', 'year', 'id', 'link', 'deadline', 'timezone', 'date', 'place', 'sub', 'events', 'edition_sources'):
            if key not in record:
                raise ValueError(f'Missing {key}')
        assert record['title'] in TITLES, 'Unsupported conference'
        assert isinstance(record['year'], int) and 1900 <= record['year'] <= 2200, 'Invalid edition year'
        assert re.fullmatch(r'[a-z][a-z0-9]*', record['id']), 'Invalid stable ID'
        assert record['sub'] == ('Circuit' if record['title'] in TITLES[:4] else 'Algorithm'), 'Invalid category'
        assert record['link'].startswith('https://'), 'Invalid official link'
        assert record['id'] not in ids, 'Duplicate ID'
        edition = (record['title'], record['year'])
        assert edition not in editions, 'Duplicate edition'
        assert record['edition_sources'], 'Edition must have official evidence'
        ids.add(record['id'])
        editions.add(edition)
        kinds = set()
        for event in record['events']:
            assert event['kind'] in KINDS and event['kind'] not in kinds, 'Invalid/duplicate event'
            kinds.add(event['kind'])
            assert event['precision'] in ('date', 'datetime', 'tba'), 'Invalid precision'
            if event['precision'] == 'tba':
                assert event['date'] == 'TBA'
                assert not event.get('utc')
                continue
            assert event['sources'] and event['checked_at'], 'Missing provenance'
            assert all(s.startswith('https://') for s in event['sources']), 'Invalid source URL'
            assert datetime.fromisoformat(event['checked_at'].replace('Z', '+00:00')).tzinfo, 'Verification time needs a zone'
            if event['precision'] == 'date':
                date.fromisoformat(event['date'])
                assert not event.get('utc'), 'Date-only event cannot have an instant'
            else:
                assert re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', event['date']), 'Invalid local timestamp'
                assert instant(event) == event['utc'], 'Incorrect UTC conversion'
            if event.get('end'):
                assert date.fromisoformat(event['end']) >= date.fromisoformat(event['date'][:10]), 'Reversed interval'
            if event['kind'] == 'conference':
                assert int(event['date'][:4]) == record['year'], 'Conference belongs to a different year'
        required = {'arr', 'commitment', 'notification', 'conference'} if record['title'] == 'EMNLP' else {'abstract', 'paper', 'notification', 'conference'}
        assert kinds == required, 'Missing core event kinds'


def in_window(record, today):
    return record['year'] >= today.year - 2
