"""Journal deadlines remain independent through parsing, merging and sync."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import json
import unittest

import yaml

from utils.collector.model import event_key, merge_events, new_record, validate
from utils.collector.parsers import parse_source
import test_sync

URL = 'https://example.org/isicas26'
STAMP = '2026-05-01T00:00:00Z'
TRACKS = [dict(track='tcas-i', track_label='TCAS-I'), dict(track='ojcas', track_label='OJCAS')]


def paper(track, day):
    return dict(kind='paper', date=day, precision='date', timezone='TBA', sources=[URL], **track)


def by_key(record):
    return {event_key(e): e for e in record['events']}


class JournalModelTests(unittest.TestCase):
    def setUp(self):
        self.record = new_record('ISICAS', 2026, URL, URL, TRACKS)
        self.values = [paper(TRACKS[0], '2026-05-11'), paper(TRACKS[1], '2026-06-01')]

    def test_initialization_ids_and_categories(self):
        self.assertNotIn('paper', by_key(self.record))
        self.assertEqual(len([e for e in self.record['events'] if e['kind'] == 'paper']), 2)
        for title, expected in [('ESSERC', 'esserc26'), ('A-SSCC', 'asscc26'), ('ISICAS', 'isicas26')]:
            record = new_record(title, 2026, URL, URL)
            self.assertEqual((record['id'], record['sub']), (expected, 'Circuit'))
            validate([record])

    def test_date_only_earliest_keeps_legacy_deadline_tba(self):
        later = {**self.values[1], 'date': '2026-06-01 20:00:00', 'precision': 'datetime', 'timezone': 'UTC'}
        result = merge_events(self.record, [later, self.values[0]], [], STAMP)
        self.assertEqual(result['deadline'], 'TBA')
        self.assertNotIn('utc', by_key(result)['paper:tcas-i'])
        earlier = {**self.values[0], 'date': '2026-05-11 20:00:00', 'precision': 'datetime', 'timezone': 'UTC'}
        result = merge_events(self.record, [later, earlier], [], STAMP)
        self.assertEqual(result['deadline'], earlier['date'])
        validate([result])

    def test_conflict_and_parse_failure_are_isolated(self):
        initial = merge_events(self.record, self.values, [], STAMP)
        updated = [paper(TRACKS[0], '2026-05-12'), paper(TRACKS[1], '2026-06-02')]
        failed = merge_events(initial, updated, [URL + ': paper:tcas-i: malformed'], STAMP)
        self.assertEqual(by_key(failed)['paper:tcas-i'], by_key(initial)['paper:tcas-i'])
        self.assertEqual(by_key(failed)['paper:ojcas']['date'], '2026-06-02')
        conflict = merge_events(initial, self.values + [updated[0]], [], STAMP)
        self.assertEqual(by_key(conflict)['paper:tcas-i'], by_key(initial)['paper:tcas-i'])
        self.assertTrue(any('paper:tcas-i: conflicting' in e for e in conflict['issues']))

    def test_extension_and_override_do_not_change_other_journals(self):
        extension = {**self.values[0], 'date': '2026-05-20', 'extended': True}
        initial = merge_events(self.record, self.values + [extension], [], STAMP)
        repeated = merge_events(initial, self.values, [], STAMP)
        self.assertEqual(by_key(repeated)['paper:tcas-i']['date'], '2026-05-20')
        corrected = {**self.values[1], 'date': '2026-06-03', 'checked_at': STAMP, 'reason': 'Official correction'}
        result = merge_events(initial, self.values, [], STAMP, {'events': {'paper:ojcas': corrected}})
        self.assertEqual(by_key(result)['paper:ojcas']['date'], corrected['date'])
        self.assertTrue(by_key(result)['paper:ojcas']['manual'])
        self.assertEqual(by_key(result)['paper:tcas-i'], by_key(initial)['paper:tcas-i'])
        validate([result])
        with self.assertRaises(ValueError):
            merge_events(initial, [], [], STAMP, {'events': {'paper:unknown': corrected}})

    def test_duplicates_common_paper_and_invalid_tracks_rejected(self):
        validate([self.record])
        for extra in [deepcopy(self.record['events'][1]), dict(kind='paper', date='TBA', precision='tba')]:
            invalid = deepcopy(self.record)
            invalid['events'].append(extra)
            with self.assertRaises(AssertionError):
                validate([invalid])
        for field, value in [('track', 'TCAS I'), ('track_label', '')]:
            invalid = deepcopy(self.record)
            invalid['events'][1][field] = value
            with self.assertRaises(AssertionError):
                validate([invalid])

    def test_rule_failure_reports_exact_journal(self):
        source = dict(url=URL, rules=[dict(kind='paper', pattern=r'TCAS: (?P<date>May \d+, 2026)', **TRACKS[0]),
                                      dict(kind='paper', pattern=r'OJCAS: (?P<date>June \d+, 2026)', **TRACKS[1])])
        events, errors = parse_source(b'<h1>ISICAS 2026</h1><p>OJCAS: June 1, 2026</p>', source, 'ISICAS', 2026)
        self.assertEqual(event_key(events[0]), 'paper:ojcas')
        self.assertEqual(events[0]['track_label'], 'OJCAS')
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('paper:tcas-i: '))

    def test_missing_and_tba_observations_preserve_journals(self):
        initial = merge_events(self.record, self.values, [], STAMP)
        missing = {**self.values[0], 'date': 'TBA', 'precision': 'tba'}
        result = merge_events(initial, [missing], [], STAMP)
        self.assertEqual(by_key(result)['paper:tcas-i'], by_key(initial)['paper:tcas-i'])
        self.assertEqual(by_key(result)['paper:ojcas'], by_key(initial)['paper:ojcas'])

    def test_manual_conference_venue_preserves_its_verification_time(self):
        correction = dict(date='2026-12-04', end='2026-12-06', precision='date', timezone='TBA',
                          sources=[URL], checked_at=STAMP, reason='Official indexed venue', place='Torino, Italy')
        result = merge_events(self.record, [], ['venue: Offline'], '2026-06-01T00:00:00Z',
                              {'events': {'conference': correction}})
        self.assertEqual(result['place'], 'Torino, Italy')
        self.assertEqual(result['place_checked_at'], STAMP)
        validate([result])


class JournalSyncTests(unittest.TestCase):
    setUp = test_sync.SyncTests.setUp
    write = test_sync.SyncTests.write
    read = test_sync.SyncTests.read
    fetch = test_sync.SyncTests.fetch

    def test_declaring_journals_does_not_copy_a_common_deadline(self):
        from utils.collector.sync import run
        existing = new_record('ISICAS', 2026, URL, URL)
        common = dict(kind='paper', date='2026-06-01', precision='date', timezone='TBA', sources=[URL])
        existing = merge_events(existing, [common], [], STAMP)
        self.write('_data/conferences.yml', [existing])
        config = next(c for c in self.registry if c['title'] == 'ISICAS')
        config['editions'][2026]['submission_tracks'] = TRACKS
        self.write('utils/sources.yml', self.registry)
        run(self.root, self.now, self.fetch)
        current = next(r for r in self.read() if r['title'] == 'ISICAS')
        self.assertNotIn('paper', by_key(current))
        self.assertEqual(by_key(current)['paper:tcas-i']['date'], 'TBA')
        self.assertEqual(by_key(current)['paper:ojcas']['date'], 'TBA')

    def test_journal_fetch_failure_repeat_and_manual_correction(self):
        config = next(c for c in self.registry if c['title'] == 'ISICAS')
        edition = config['editions'][2026]
        edition['submission_tracks'] = TRACKS
        for index, track in enumerate(TRACKS):
            edition['sources'].append(dict(url=URL + '/' + track['track'], identity='ISICAS 2026', rules=[dict(
                kind='paper', pattern=r'Deadline: (?P<date>June \d+, 2026)', **track)]))
        self.write('utils/sources.yml', self.registry)
        def fetch(url):
            if url.startswith(URL):
                return b'<h1>ISICAS 2026</h1><p>Deadline: June 1, 2026</p>'
            return self.fetch(url)
        from utils.collector.sync import run
        run(self.root, self.now, fetch)
        initial = self.read()
        run(self.root, self.now, fetch)
        self.assertEqual(initial, self.read())
        prior = next(r for r in initial if r['title'] == 'ISICAS')
        def partial(url):
            if url.endswith('/tcas-i'):
                raise OSError('Offline')
            return fetch(url).replace(b'June 1,', b'June 2,')
        run(self.root, datetime(2027, 1, 1, tzinfo=timezone.utc), partial)
        current = next(r for r in self.read() if r['title'] == 'ISICAS')
        self.assertEqual(by_key(current)['paper:tcas-i'], by_key(prior)['paper:tcas-i'])
        self.assertEqual(by_key(current)['paper:ojcas']['date'], '2026-06-02')
        correction = {**paper(TRACKS[0], '2026-06-03'), 'reason': 'Official source checked', 'checked_at': STAMP}
        self.write('_data/overrides.yml', {'isicas26': {'events': {'paper:tcas-i': correction}}})
        run(self.root, self.now, partial)
        current = next(r for r in self.read() if r['title'] == 'ISICAS')
        self.assertTrue(by_key(current)['paper:tcas-i']['manual'])
        self.assertEqual(by_key(current)['paper:tcas-i']['date'], '2026-06-03')


class NewOfficialSamples(unittest.TestCase):
    def test_registered_new_sources(self):
        root = Path(__file__).resolve().parents[1]
        fixtures = root / 'tests/fixtures/raw'
        files = {e['url']: e['file'] for e in json.loads((fixtures / 'manifest.json').read_text())}
        registry = yaml.safe_load((root / 'utils/sources.yml').read_text())
        expected = {
            ('ISICAS', 2024): {'tcas-i': '2024-04-29', 'tcas-ii': '2024-04-29', 'tbiocas': '2024-04-29', 'ojcas': '2024-04-29'},
            ('ISICAS', 2025): {'tcas-i': '2025-03-06', 'tcas-ii': '2025-03-06', 'tbiocas': '2025-03-20', 'tcas-ai': '2025-03-06', 'tvlsi': '2025-03-20', 'ojcas': '2025-03-20'},
            ('ISICAS', 2026): {'tcas-i': '2026-05-11', 'tbiocas': '2026-05-11', 'tcas-ai': '2026-05-11', 'tvlsi': '2026-05-11', 'tcas-ii': '2026-06-01', 'ojcas': '2026-06-01'},
        }
        for config in (c for c in registry if c['title'] in ('A-SSCC', 'ISICAS')):
            for year, edition in config['editions'].items():
                values = []
                for source in edition['sources']:
                    if source['url'] not in files:
                        continue
                    with self.subTest(title=config['title'], year=year, url=source['url']):
                        events, errors = parse_source((fixtures / files[source['url']]).read_bytes(), source, config['title'], year)
                        self.assertFalse(errors)
                        values.extend(events)
                if not values:
                    continue
                papers = [e for e in values if e['kind'] == 'paper']
                if config['title'] == 'ISICAS':
                    self.assertEqual({e['track']: e['date'] for e in papers}, expected.get(('ISICAS', year), {}))
                    self.assertTrue(all(e['precision'] == 'date' and not e.get('utc') for e in papers))
                    if year in (2024, 2025):
                        self.assertTrue(all(e['extended'] for e in papers))
                else:
                    day = '2025-06-18' if year == 2025 else '2026-06-03'
                    self.assertEqual(papers[0]['date'], day + ' 20:00:00')
                    self.assertEqual(papers[0]['utc'], day + 'T20:00:00Z')
                    if year == 2025:
                        self.assertTrue(papers[0]['extended'])
                meeting = next(e for e in values if e['kind'] == 'conference')
                self.assertEqual((meeting['date'], meeting['end']), {
                    ('A-SSCC', 2026): ('2026-11-01', '2026-11-04'),
                    ('A-SSCC', 2025): ('2025-11-03', '2025-11-05'),
                    ('ISICAS', 2024): ('2024-10-18', '2024-10-19'),
                    ('ISICAS', 2025): ('2025-10-26', '2025-10-27'),
                    ('ISICAS', 2026): ('2026-12-04', '2026-12-06'),
                    ('ISICAS', 2027): ('2027-10-25', '2027-10-27'),
                }[(config['title'], year)])
