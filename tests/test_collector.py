from copy import deepcopy
from datetime import date
from pathlib import Path
import unittest

from utils.collector.model import in_window, instant, merge_events, new_record, validate
from utils.collector.parsers import ParseError, discover, parse_source, parse_value

STAMP = '2026-09-07T00:00:00Z'
URL = 'https://example.org/2026/dates'


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.record = new_record('ICLR', 2026, URL, URL)
        self.value = dict(kind='paper', date='2025-09-24 23:59:59', precision='datetime', timezone='UTC-12', sources=[URL])

    def test_aoe_rolls_to_next_utc_day(self):
        self.assertEqual(instant(self.value), '2025-09-25T11:59:59Z')

    def test_dst_conversion(self):
        event = {**self.value, 'date': '2026-07-01 23:59:00', 'timezone': 'America/Los_Angeles'}
        self.assertEqual(instant(event), '2026-07-02T06:59:00Z')
        event['date'] = '2026-11-01 01:30:00'
        with self.assertRaises(ValueError):
            instant(event)

    def test_date_without_clock_has_no_countdown(self):
        event = parse_value('May 4, 2026 (Anywhere on Earth)', 'paper', {'url': URL}, 2026)
        self.assertEqual(event['precision'], 'date')
        self.assertIsNone(instant(event))

    def test_no_year_inference(self):
        with self.assertRaises(ParseError):
            parse_value('September 24', 'paper', {'url': URL}, 2026)

    def test_conflict_retains_previous_value(self):
        first = merge_events(self.record, [self.value], [], STAMP)
        other = {**self.value, 'date': '2025-09-25 23:59:59'}
        result = merge_events(first, [self.value, other], [], STAMP)
        self.assertEqual(result['events'][1], first['events'][1])
        self.assertTrue(any('conflicting' in s for s in result['issues']))

    def test_explicit_extension_wins(self):
        later = {**self.value, 'date': '2025-09-26 23:59:59', 'extended': True}
        result = merge_events(self.record, [self.value, later], [], STAMP)
        self.assertEqual(result['events'][1]['date'], later['date'])

    def test_fetch_failure_retains_known_value(self):
        first = merge_events(self.record, [self.value], [], STAMP)
        result = merge_events(first, [], ['HTTP 503'], '2026-09-08T00:00:00Z')
        self.assertEqual(result['events'], first['events'])
        self.assertEqual(result['last_success'], STAMP)
        self.assertTrue(result['needs_review'])

    def test_tba_cannot_erase_a_published_deadline(self):
        first = merge_events(self.record, [self.value], [], STAMP)
        tba = parse_value('TBA', 'paper', {'url': URL}, 2026)
        second = merge_events(first, [tba], [], '2026-09-08T00:00:00Z')
        self.assertEqual(second['events'][1], first['events'][1])
        self.assertTrue(any('disappeared' in issue for issue in second['issues']))

    def test_partial_source_failure_preserves_affected_field_only(self):
        first = merge_events(self.record, [self.value], [], STAMP)
        changed = {**self.value, 'date': '2025-09-26 23:59:59'}
        notification = parse_value('January 25, 2026', 'notification', {'url': URL}, 2026)
        second = merge_events(first, [changed, notification], [URL + ': paper: malformed date'], STAMP)
        self.assertEqual(second['events'][1], first['events'][1])
        self.assertEqual(second['events'][2]['date'], '2026-01-25')

    def test_older_cfp_cannot_roll_back_confirmed_extension(self):
        extended = {**self.value, 'date': '2025-09-26 23:59:59', 'extended': True}
        first = merge_events(self.record, [extended], [], STAMP)
        second = merge_events(first, [self.value], [], '2026-09-08T00:00:00Z')
        self.assertEqual(second['events'][1], first['events'][1])
        self.assertTrue(any('confirmed extension' in issue for issue in second['issues']))

    def test_override_survives_collection(self):
        override = {**self.value, 'date': '2025-09-27 23:59:59', 'checked_at': STAMP, 'reason': 'Official correction'}
        result = merge_events(self.record, [self.value], [], STAMP, {'events': {'paper': override}})
        self.assertEqual(result['events'][1]['date'], override['date'])
        self.assertTrue(result['events'][1]['manual'])

    def test_idempotent_same_observation(self):
        first = merge_events(self.record, [self.value], [], STAMP)
        second = merge_events(first, [self.value], [], STAMP)
        self.assertEqual(first, second)
        validate([second])

    def test_duplicate_edition_rejected(self):
        with self.assertRaises(AssertionError):
            validate([self.record, deepcopy(self.record)])

    def test_year_window_moves(self):
        self.assertTrue(in_window({'year': 2024}, date(2026, 12, 31)))
        self.assertFalse(in_window({'year': 2024}, date(2027, 1, 1)))
        self.assertTrue(in_window({'year': 2028}, date(2027, 1, 1)))

    def test_discovery_requires_official_link(self):
        html = '<a href="/Conferences/2027">2027</a><a href="https://evil.org/2028">2028</a>'
        found = discover(html, 'https://iclr.cc/', 'ICLR', ['iclr.cc'], 2024)
        self.assertEqual(set(found), {2027})
        self.assertEqual(discover('2028', 'https://iclr.cc/', 'ICLR', ['iclr.cc'], 2024), {})

    def test_wrong_year_heading_rejected(self):
        with self.assertRaises(ParseError):
            parse_source(b'<title>ICLR 2025</title><nav>2026</nav>', {'url': URL}, 'ICLR', 2026)


if __name__ == '__main__':
    unittest.main()
