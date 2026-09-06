"""Regression expectations from downloaded official HTML/PDF, not synthetic dates."""
from pathlib import Path
import unittest

from utils.collector.parsers import parse_source

FIXTURES = Path(__file__).parent / 'fixtures' / 'raw'


class OfficialSamples(unittest.TestCase):
    def test_eventhosts_main_track_and_meeting_ranges(self):
        cases = [
            ('NeurIPS', 'neurips.cc', 2024, '2024-05-22 20:00:00', '2024-12-11', '2024-12-13'),
            ('NeurIPS', 'neurips.cc', 2026, '2026-05-06 23:59:59', '2026-12-08', '2026-12-11'),
            ('ICLR', 'iclr.cc', 2025, '2024-10-01 23:59:59', '2025-04-24', '2025-04-26'),
            ('ICLR', 'iclr.cc', 2027, '2026-09-25 23:59:59', '2027-04-26', '2027-04-28'),
            ('ICML', 'icml.cc', 2024, '2024-02-01 23:59:59', '2024-07-23', '2024-07-25'),
            ('ECCV', 'eccv.ecva.net', 2026, '2026-03-05 22:00:00', '2026-09-10', '2026-09-12'),
            ('ICCV', 'iccv.thecvf.com', 2025, '2025-03-07 23:59:59', '2025-10-21', '2025-10-23'),
        ]
        for title, host, year, deadline, start, end in cases:
            with self.subTest(title=title, year=year):
                source = dict(url=f'https://{host}/Conferences/{year}/Dates', parser='eventhosts')
                events, errors = parse_source((FIXTURES / f'{host}_Conferences_{year}_Dates.html').read_bytes(), source, title, year)
                self.assertFalse(errors)
                self.assertEqual(next(e for e in events if e['kind'] == 'paper')['date'], deadline)
                meeting = next(e for e in events if e['kind'] == 'conference')
                self.assertEqual((meeting['date'], meeting['end']), (start, end))
                self.assertLessEqual({e['kind'] for e in events}, {'abstract', 'paper', 'notification', 'conference'})

    def test_emnlp_two_stages_remain_distinct(self):
        for year, arr, commitment, start, end in [
            (2024, '2024-06-15', '2024-08-20', '2024-11-12', '2024-11-14'),
            (2025, '2025-05-19', '2025-08-01', '2025-11-05', '2025-11-09'),
            (2026, '2026-05-25', '2026-08-02', '2026-10-24', '2026-10-29'),
        ]:
            source = dict(url=f'https://{year}.emnlp.org/calls/main_conference_papers/', parser='emnlp', identity=f'EMNLP {year}')
            events, errors = parse_source((FIXTURES / f'{year}.emnlp.org_calls_main_conference_papers.html').read_bytes(), source, 'EMNLP', year)
            values = {event['kind']: event for event in events}
            self.assertEqual(values['arr']['date'], arr)
            self.assertEqual(values['commitment']['date'], commitment)
            self.assertEqual((values['conference']['date'], values['conference']['end']), (start, end))
            self.assertTrue(all(e['precision'] == 'date' for e in events))


    def test_emnlp_program_excludes_workshop_days(self):
        for year, start, end in [(2025, '2025-11-05', '2025-11-07'), (2026, '2026-10-25', '2026-10-27')]:
            source = dict(url=f'https://{year}.emnlp.org/program/', parser='emnlp_program', identity=f'EMNLP {year}')
            events, errors = parse_source((FIXTURES / f'{year}.emnlp.org_program.html').read_bytes(), source, 'EMNLP', year)
            self.assertFalse(errors)
            self.assertEqual((events[0]['date'], events[0]['end']), (start, end))

class CircuitSamples(unittest.TestCase):
    def test_registered_circuit_sources(self):
        import yaml
        registry = {c['title']: c for c in yaml.safe_load((FIXTURES.parents[2] / 'utils/sources.yml').read_text())}
        for title, year, expected in [('ISSCC', 2027, '2026-09-09 15:00:00'), ('VLSI', 2024, '2024-02-05 23:59:00'), ('CICC', 2027, '2026-11-16 23:59:00'), ('ESSERC', 2026, '2026-04-10 23:59:00')]:
            with self.subTest(title=title):
                source = registry[title]['editions'][year]['sources'][0]
                name = source['url'].split('//')[1].strip('/').replace('/', '_')
                name += '' if name.endswith('.pdf') else '.html'
                events, errors = parse_source((FIXTURES / name).read_bytes(), source, title, year)
                self.assertFalse(errors)
                paper = next(e for e in events if e['kind'] == 'paper')
                self.assertEqual(paper['date'], expected)
                if title == 'ESSERC':
                    self.assertTrue(paper['extended'])
                if title == 'ISSCC':
                    self.assertEqual(paper['utc'], '2026-09-09T19:00:00Z')

    def test_pdf_error_page_is_not_a_schedule(self):
        from utils.collector.parsers import ParseError
        with self.assertRaises(ParseError):
            parse_source(b'<html>Temporarily unavailable</html>', {'url': 'https://example.org/cfp.pdf', 'format': 'pdf'}, 'ISSCC', 2024)


class FutureSamples(unittest.TestCase):
    def test_vlsi_future_dates_are_from_announcement(self):
        from utils.collector.parsers import announcement_entries
        source = dict(url='https://www.vlsisymposium.org/future-symposia/', parser='vlsi_future')
        values = announcement_entries((FIXTURES / 'www.vlsisymposium.org_future-symposia.html').read_bytes(), source, 'VLSI')
        self.assertEqual(values[2027]['date'], '2027-06-20')
        self.assertEqual(values[2028]['end'], '2028-06-15')
        self.assertNotIn(2029, values)

    def test_future_lists_do_not_invent_unheld_years(self):
        from utils.collector.parsers import announcement_entries
        source = dict(url='https://www.thecvf.com/?page_id=100', parser='cvf_venue')
        content = (FIXTURES / 'www.thecvf.com__page_id=100.html').read_bytes()
        iccv = announcement_entries(content, source, 'ICCV')
        self.assertEqual(iccv[2027]['place'], 'Hong Kong')
        self.assertIn(2031, iccv)
        self.assertNotIn(2024, iccv)
        self.assertNotIn(2026, iccv)
        self.assertNotIn(2025, announcement_entries(content, source, 'ECCV'))

    def test_future_meetings_keep_dates_unannounced(self):
        source = dict(url='https://icml.cc/Conferences/FutureMeetings', parser='future_meetings')
        events, errors = parse_source((FIXTURES / 'icml.cc_Conferences_FutureMeetings.html').read_bytes(), source, 'ICML', 2027)
        self.assertEqual(events, [{'kind': 'venue', 'place': 'South America', 'sources': [source['url']]}])

    def test_esserc_future_year_and_location_columns(self):
        from utils.collector.parsers import announcement_entries
        source = dict(url='https://www.esserc.org/', parser='esserc_future', dates_selector='#comp-lezhdn2a', places_selector='#comp-lezhg2rz')
        values = announcement_entries((FIXTURES / 'www.esserc.org.html').read_bytes(), source, 'ESSERC')
        self.assertEqual(values[2027], dict(date='2027-09-06', end='2027-09-09', place='HELSINKI, Finland'))
        self.assertEqual(values[2028]['place'], 'BORDEAUX, France')
