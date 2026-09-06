"""Verify built JSON/ICS parity and repository-prefix URLs after Jekyll."""
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_calendar(path):
    raw = path.read_bytes()
    assert raw.endswith(b'\r\n'), f'{path}: missing CRLF'
    assert all(len(line) <= 75 for line in raw.split(b'\r\n')), f'{path}: unfolded long line'
    text = re.sub(r'\r\n[ \t]', '', raw.decode())
    events = {}
    for block in text.split('BEGIN:VEVENT\r\n')[1:]:
        fields = dict(line.split(':', 1) for line in block.split('END:VEVENT')[0].split('\r\n') if ':' in line)
        assert fields['UID'] not in events, 'Duplicate ICS UID'
        events[fields['UID']] = fields
    return events


def run():
    site = ROOT / '_site'
    records = yaml.safe_load((ROOT / '_data/conferences.yml').read_text())
    data = json.loads((site / 'schedule.json').read_text())
    assert data['conferences'] == records, 'Built JSON differs from validated source'
    expected = {}
    for record in records:
        personal = read_calendar(site / 'calendar' / (record['id'] + '.ics'))
        published = [e for e in record['events'] if e['precision'] != 'tba']
        assert len(personal) == len(published), 'TBA or duplicate events in personal feed'
        for event in published:
            uid = f"{record['id']}-{event['kind']}@mms-deadlines"
            fields = personal[uid]
            assert fields['URL'] == f"https://ojy0216.github.io/mms-deadlines/conference/?id={record['id']}"
            if event['precision'] == 'date':
                assert fields['DTSTART;VALUE=DATE'] == event['date'].replace('-', '')
                end = date.fromisoformat(event.get('end', event['date'])) + timedelta(days=1)
                assert fields['DTEND;VALUE=DATE'] == end.strftime('%Y%m%d'), 'All-day end must be exclusive'
            else:
                start = datetime.fromisoformat(event['utc'].replace('Z', '+00:00'))
                assert fields['DTSTART'] == start.strftime('%Y%m%dT%H%M%SZ')
                assert fields['DTEND'] == (start + timedelta(minutes=1)).strftime('%Y%m%dT%H%M%SZ')
            expected[uid] = fields
    assert read_calendar(site / 'ai-deadlines.ics') == expected, 'Aggregate and personal feeds disagree'
    assert not (site / 'CNAME').exists(), 'Upstream domain survived build'
    print(f'Built JSON and {len(records) + 1} calendars verified: {len(expected)} published milestones.')


if __name__ == '__main__':
    run()
