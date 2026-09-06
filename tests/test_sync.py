"""Exercise the write boundary, isolation and rollover without network access."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from utils.collector.model import TITLES, merge_events, new_record
from utils.collector.sync import run


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'utils').mkdir()
        (self.root / '_data').mkdir()
        self.now = datetime(2026, 12, 31, tzinfo=timezone.utc)
        self.registry = []
        for title in TITLES:
            url = f'https://example.org/{title}'
            source = dict(url=url, identity=title + ' 2026', rules=[
                dict(kind='conference', range=True, pattern=r'Meeting: (?P<date>June 1-3, 2026)')])
            self.registry.append(dict(title=title, hosts=['example.org'], discovery=[], editions={
                2026: dict(link=url, evidence=url, sources=[source])}))
        self.write('utils/sources.yml', self.registry)
        self.write('_data/conferences.yml', [])

    def write(self, path, value):
        (self.root / path).write_text(yaml.safe_dump(value))

    def read(self):
        return yaml.safe_load((self.root / '_data/conferences.yml').read_text())

    def fetch(self, url):
        title = url.rsplit('/', 1)[-1]
        return f'<h1>{title} 2026</h1><p>Meeting: June 1-3, 2026</p>'.encode()

    def test_failure_isolated_and_repeat_is_idempotent(self):
        run(self.root, self.now, self.fetch)
        first = self.read()
        run(self.root, self.now, self.fetch)
        self.assertEqual(first, self.read())

        def partial(url):
            if url.endswith('/ISSCC'):
                raise OSError('Offline')
            return self.fetch(url)

        run(self.root, datetime(2027, 1, 1, tzinfo=timezone.utc), partial)
        records = {r['title']: r for r in self.read()}
        old = next(r for r in first if r['title'] == 'ISSCC')
        self.assertEqual(records['ISSCC']['events'], old['events'])
        self.assertTrue(records['ISSCC']['needs_review'])
        self.assertEqual(records['ICML']['last_success'], '2027-01-01T00:00:00Z')

    def test_duplicate_input_fails_before_output(self):
        record = new_record('ISSCC', 2026, 'https://example.org/ISSCC', 'https://example.org/ISSCC')
        self.write('_data/conferences.yml', [record, deepcopy(record)])
        before = (self.root / '_data/conferences.yml').read_bytes()
        with self.assertRaises(AssertionError):
            run(self.root, self.now, self.fetch)
        self.assertEqual(before, (self.root / '_data/conferences.yml').read_bytes())
        self.assertFalse((self.root / '_data/sync_status.yml').exists())

    def test_year_rollover_removes_old_edition_without_inventing_new_one(self):
        record = new_record('ISSCC', 2024, 'https://example.org/ISSCC', 'https://example.org/ISSCC')
        self.write('_data/conferences.yml', [record])
        run(self.root, self.now, self.fetch)
        self.assertIn('isscc24', {r['id'] for r in self.read()})
        run(self.root, datetime(2027, 1, 1, tzinfo=timezone.utc), self.fetch)
        self.assertNotIn('isscc24', {r['id'] for r in self.read()})
        self.assertEqual({r['year'] for r in self.read()}, {2026})

    def test_unknown_override_fails_without_writing(self):
        self.write('_data/overrides.yml', {'icml99': {'events': {}}})
        with self.assertRaises(ValueError):
            run(self.root, self.now, self.fetch)
        self.assertEqual(self.read(), [])

    def test_failed_venue_does_not_refresh_provenance(self):
        record = new_record('ICML', 2026, 'https://example.org/ICML', 'https://example.org/ICML')
        value = dict(kind='conference', date='2026-06-01', end='2026-06-03',
                     precision='date', timezone='TBA', place='Seoul', sources=[record['link']])
        first = merge_events(record, [value], [], '2026-01-01T00:00:00Z')
        second = merge_events(first, [], ['conference: Offline'], '2026-01-02T00:00:00Z')
        self.assertEqual(second['place_checked_at'], first['place_checked_at'])


if __name__ == '__main__':
    unittest.main()
