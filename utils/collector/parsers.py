"""Small, conservative parsers shared by official HTML and PDF sources."""
from datetime import datetime
from io import BytesIO
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from pypdf import PdfReader

from .model import instant, zone


class ParseError(ValueError):
    pass


def document(content, pdf=False):
    if pdf:
        if not content.startswith(b'%PDF'):
            raise ParseError('Official PDF URL returned non-PDF content')
        text = ' '.join(page.extract_text() or '' for page in PdfReader(BytesIO(content)).pages)
        return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)), None
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup.select('del, s, strike'):
        tag.decompose()
    return soup.get_text(' ', strip=True), soup


def assert_edition(text, soup, source, title, year):
    # A year in the navigation/footer or URL alone does not verify an edition.
    if source.get('identity'):
        identity = re.search(source['identity'], text, re.I)
        if not identity:
            raise ParseError(f'Edition identity not found: {title} {year}')
    elif soup:
        headings = ' '.join(t.get_text(' ', strip=True) for t in soup.select('h1,h2,h3,title'))
        if not re.search(rf'\b{re.escape(title)}\s*{year}\b|\b{year}\s*{re.escape(title)}\b', headings, re.I):
            raise ParseError(f'Edition heading not found: {title} {year}')
    else:
        raise ParseError('PDF needs an explicit edition identity pattern')


def parse_value(raw, kind, source, year):
    raw = re.sub(r'\s+', ' ', raw).strip()
    if re.fullmatch(r'TBA|TBD|to be (?:announced|determined)', raw, re.I):
        return dict(kind=kind, date='TBA', precision='tba', timezone='TBA', sources=[source['url']])
    # Never supply a deadline year from the conference year: ICLR/ISSCC cross years.
    if not re.search(r'\b20\d{2}\b|[\x27’]\d{2}\b', raw):
        raise ParseError(f'Explicit year missing: {raw}')
    raw = re.sub(r"[\x27’](\d{2})\b", r'20\1', raw)
    explicit_time = bool(re.search(r'\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)\b', raw, re.I))
    tz = source.get('timezone', 'TBA')
    if re.search(r'Anywhere on Earth|\bAOE\b', raw, re.I):
        tz = 'UTC-12'
    elif re.search(r'\bUTC\b', raw):
        tz = 'UTC'
    for abbreviation, name in {'HST': 'Pacific/Honolulu', 'PST': 'UTC-08', 'PDT': 'UTC-07', 'EDT': 'UTC-04', 'EST': 'UTC-05', 'JST': 'Asia/Tokyo', 'PT': 'America/Los_Angeles', 'ET': 'America/New_York'}.items():
        if re.search(rf'\b{abbreviation}\b', raw):
            tz = name
    cleaned = re.sub(r'\(?Anywhere on Earth\)?|\bAOE\b|\bUTC\b', '', raw, flags=re.I)
    cleaned = cleaned.replace('•', ' ').replace('·', ' ')
    cleaned = re.sub(r'\b(?:HST|PST|PDT|EDT|EST|JST|PT|ET)\b', '', cleaned)
    parsed = parse_date(cleaned, fuzzy=False, default=datetime(2000, 1, 1))
    if abs(parsed.year - year) > 1:
        raise ParseError(f'Date outside edition interval: {raw}')
    event = dict(kind=kind, date=parsed.date().isoformat(), precision='date', timezone=tz, sources=[source['url']])
    # AoE alone names a zone, not a clock time. An explicit source-wide rule can supply time.
    if not explicit_time and source.get('deadline_time') and kind != 'conference':
        parsed = datetime.combine(parsed.date(), datetime.strptime(source['deadline_time'], '%H:%M:%S').time())
        explicit_time = True
    if explicit_time and tz != 'TBA':
        event.update(date=parsed.strftime('%Y-%m-%d %H:%M:%S'), precision='datetime')
        event['utc'] = instant(event)
    elif explicit_time:
        event['unresolved_time'] = raw
    return event


LABELS = {
    'abstract': r'(?:Paper)?Abstract(?:Submission|Registration)?Deadline|PaperRegistrationDeadline',
    'paper': r'(?:MainConference)?(?:Full)?Paper(?:Submission)?Deadline|MainConferenceFullPaperSubmissionDeadline|Submission(?:andSupplementaryMaterials)?Deadline|MainConferenceSubmissionDeadline',
    'notification': r'(?:MainConference)?(?:Paper)?(?:AuthorNotifications?|DecisionNotification)|FinalDecisions|DecisionsCommunicatedToAuthors|MainConferencePaperDecisions',
}


def eventhosts(soup, source, year):
    """NeurIPS/ICLR/ICML/ECCV/ICCV share EventHosts markup."""
    events = []
    section = None
    for row in soup.select('tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 1 and cells[0].has_attr('colspan'):
            section = cells[0].get_text(' ', strip=True)
        if section not in ('Main Conference Paper Submission', 'Paper Submissions', 'Main Conference'):
            continue
        for kind, label in LABELS.items():
            target = next((cell for cell in cells if re.fullmatch(label, re.sub(r'\s+', '', cell.get_text(' ', strip=True)), re.I)), None)
            if not target:
                continue
            raw = target.find_next_sibling('td').get_text(' ', strip=True)
            event = parse_value(raw, kind, source, year)
            # Official embedded countdown supplies the exact instant; never execute script.
            times = set(re.findall(r'"(20\d\d/\d\d/\d\d \d\d:\d\d:\d\d UTC)"', str(row)))
            if len(times) == 1:
                utc = datetime.strptime(times.pop(), '%Y/%m/%d %H:%M:%S %Z').replace(tzinfo=zone('UTC'))
                tz = event['timezone'] if event['timezone'] != 'TBA' else 'UTC'
                local = utc.astimezone(zone(tz))
                if local.date().isoformat() != event['date'][:10]:
                    raise ParseError('Countdown and visible date disagree')
                event.update(date=local.strftime('%Y-%m-%d %H:%M:%S'), precision='datetime', timezone=tz)
                event['utc'] = instant(event)
            events.append(event)
    if not events:
        raise ParseError('Main paper schedule table missing or changed')
    return events


def meeting_range(raw, year):
    """Conference dates inherit the verified meeting heading's year, never deadlines."""
    years = re.findall(r'\b20\d{2}\b', raw)
    if years and any(int(y) != year for y in years):
        raise ParseError('Conference range year differs from edition')
    raw = re.sub(r',?\s*\b20\d{2}\b', '', raw)
    raw = re.sub(r'^(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+)$', r'\3 \1 - \3 \2', raw.strip())
    raw = re.sub(r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)\.?\b|\bthe\b', '', raw, flags=re.I)
    raw = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    listed_days = re.fullmatch(r'([A-Za-z]+) (\d{1,2})(?:, \d{1,2})+,?', raw)
    if listed_days:
        days = [int(d) for d in re.findall(r'\d+', raw)]
        if days != list(range(days[0], days[-1] + 1)):
            raise ParseError('Noncontiguous meeting days require separate sessions')
        raw = f'{listed_days[1]} {days[0]} - {days[-1]}'
    parts = re.split(r'\s*(?:through|[–—-]|&)\s*', raw)
    start = parse_date(parts[0], default=datetime(year, 1, 1))
    end = parse_date(parts[-1], default=start) if len(parts) > 1 else start
    return start.date().isoformat(), end.date().isoformat()


def meeting(soup, source, year):
    container = soup.select_one('.date-sessions-table')
    if not container:
        return []
    ranges = []
    places = []
    for row in container.select('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) != 2:
            continue
        values = [c.get_text(' ', strip=True) for c in cells]
        for i, value in enumerate(values):
            if value in ('Main Conference', 'Conference Sessions', 'Main Conference + Tutorials'):
                ranges.append(meeting_range(values[1-i], year))
                heading = row.find_previous('th', colspan=True)
                if heading and heading in container.descendants:
                    places.append(heading.get_text(' ', strip=True))
    text = container.get_text(' ', strip=True)
    if not ranges:
        match = re.search(r'Main Conference begins (.+?) Main Conference ends (.+?)(?:$| Workshops)', text)
        if match:
            ranges = [(meeting_range(match[1], year)[0], meeting_range(match[2], year)[0])]
        else:
            match = re.search(r'Main Conference\s*:\s*(.+?) Workshops', text)
            if not match:
                match = re.search(r'([A-Za-z]+ \d+\s*[-–]\s*\d+): Main Conference', text)
            if match:
                ranges = [meeting_range(match[1], year)]
    if not ranges:
        raise ParseError('Main conference meeting range missing')
    event = dict(kind='conference', date=min(r[0] for r in ranges), end=max(r[1] for r in ranges),
                 precision='date', timezone='TBA', sources=[source['url']])
    if places:
        event['place'] = ' / '.join(dict.fromkeys(places))
        event['sessions'] = [dict(date=r[0], end=r[1]) for r in ranges]
    return [event]


def emnlp(soup, source, year):
    events = []
    labels = {'arr': r'ARR submission deadline', 'commitment': r'(?:EMNLP )?Commitment deadline',
              'notification': r'Notification of acceptance', 'conference': r'Main Conference'}
    for row in soup.select('table tr'):
        cells = row.find_all('td')
        if len(cells) != 2:
            continue
        label, raw = [cell.get_text(' ', strip=True) for cell in cells]
        for kind, pattern in labels.items():
            if not re.match(pattern, label, re.I):
                continue
            if kind == 'conference':
                start, end = meeting_range(raw, year)
                events.append(dict(kind=kind, date=start, end=end, precision='date', timezone='TBA', sources=[source['url']]))
            else:
                events.append(parse_value(raw, kind, source, year))
    if {e['kind'] for e in events} != set(labels):
        raise ParseError('EMNLP two-stage main schedule missing or changed')
    return events


def parse_source(content, source, title, year):
    text, soup = document(content, source.get('format') == 'pdf')
    if source.get('parser') in ('future_meetings', 'cvf_venue', 'esserc_future', 'vlsi_future'):
        entries = announcement_entries(content, source, title)
        if year not in entries:
            raise ParseError('Edition no longer present in official announcement list')
        entry = entries[year]
        events = []
        if entry.get('place') and entry['place'] not in ('TBD', 'TBA'):
            events.append(dict(kind='venue', place=entry['place'], sources=[source['url']]))
        if entry.get('date'):
            events.append(dict(kind='conference', date=entry['date'], end=entry['end'], precision='date', timezone='TBA', sources=[source['url']]))
        return events, []
    assert_edition(text, soup, source, title, year)
    events, errors = [], []
    if source.get('venue_pattern'):
        locations = {m['place'].strip() for m in re.finditer(source['venue_pattern'], re.sub(r'\s+', ' ', text), re.I)}
        if not locations:
            errors.append('venue: expected location text missing')
        if source.get('venue_multiple') and locations:
            locations = {' / '.join(sorted(locations))}
        events.extend(dict(kind='venue', place=place, sources=[source['url']]) for place in sorted(locations))
    if source.get('parser') == 'eventhosts':
        try:
            events.extend(eventhosts(soup, source, year))
        except (ValueError, TypeError, AttributeError) as exc:
            errors.extend(f'{kind}: {exc}' for kind in ('abstract', 'paper', 'notification'))
        try:
            events.extend(meeting(soup, source, year))
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f'conference: {exc}')
    elif source.get('parser') == 'emnlp':
        events.extend(e for e in emnlp(soup, source, year) if e['kind'] not in source.get('exclude_kinds', []))
    elif source.get('parser') == 'emnlp_program':
        days = []
        for heading in soup.select('h2,h3'):
            match = re.fullmatch(r'(.+?)\s*—\s*Main Conference(?: Day \d+)?', heading.get_text(' ', strip=True))
            if match:
                days.append(meeting_range(match[1], year)[0])
        if not days:
            errors.append('conference: main conference program headings missing')
        else:
            events.append(dict(kind='conference', date=min(days), end=max(days), precision='date', timezone='TBA', sources=[source['url']]))
    for rule in source.get('rules', []):
        try:
            scope = text
            if rule.get('selector'):
                selected = soup.select(rule['selector'])
                if not selected:
                    raise ParseError('CSS selector no longer matches')
                scope = ' '.join(t.get_text(' ', strip=True) for t in selected)
            matches = list(re.finditer(rule['pattern'], scope, re.I))
            if not matches:
                raise ParseError('Expected schedule text missing')
            for match in matches:
                values = match.groupdict()
                if rule.get('range'):
                    start, end = meeting_range(values['date'], year)
                    event = dict(kind=rule['kind'], date=start, end=end, precision='date', timezone='TBA', sources=[source['url']])
                else:
                    event = parse_value(values['date'], rule['kind'], {**source, **rule}, year)
                if values.get('end'):
                    event['end'] = parse_value(values['end'], 'conference', source, year)['date']
                if values.get('place'):
                    event['place'] = values['place'].strip()
                if rule.get('extended'):
                    event['extended'] = True
                events.append(event)
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append(f"{rule['kind']}: {exc}")
    return events, errors


def announcement_entries(content, source, title):
    """Parse explicitly published future lists, including editions without a website."""
    _, soup = document(content)
    entries = {}
    if source['parser'] == 'future_meetings':
        for item in soup.select('li'):
            match = re.fullmatch(r'(20\d{2})\s*--\s*(.+)', item.get_text(' ', strip=True))
            if match:
                entries[int(match[1])] = dict(place=match[2])
    elif source['parser'] == 'cvf_venue':
        for table in soup.select('table'):
            first = table.find(['th', 'td'])
            if not first or first.get_text(' ', strip=True) != title:
                continue
            for row in table.select('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2 and re.fullmatch(r'20\d{2}', cells[0].get_text(strip=True)):
                    entries[int(cells[0].get_text(strip=True))] = dict(place=cells[1].get_text(' ', strip=True))
    elif source['parser'] == 'esserc_future':
        dates = soup.select_one(source['dates_selector'])
        places = soup.select_one(source['places_selector'])
        if not dates or not places:
            raise ParseError('ESSERC future list structure changed')
        dates, places = dates.get_text('|', strip=True).split('|'), places.get_text('|', strip=True).split('|')
        if len(dates) % 2 or len(dates) != len(places):
            raise ParseError('ESSERC future list columns no longer align')
        for i in range(0, len(dates), 2):
            year = int(dates[i])
            start, end = meeting_range(dates[i+1], year)
            entries[year] = dict(date=start, end=end, place=', '.join(places[i:i+2]))
    elif source['parser'] == 'vlsi_future':
        text = soup.get_text(' ', strip=True)
        if 'Future Symposia' not in text:
            raise ParseError('Future Symposia heading missing')
        pattern = r'(June \d+[-–]\d+, (20\d{2}))[.,] (Rihga Royal Hotel, Kyoto, Japan|Hilton Hawaiian Village, Honolulu, HI, USA)'
        for match in re.finditer(pattern, text, re.I):
            year = int(match[2])
            start, end = meeting_range(match[1], year)
            entries[year] = dict(date=start, end=end, place=match[3])
    if not entries:
        raise ParseError('Official future list missing or changed')
    return entries


def discover(content, root_url, title, allowed_hosts, minimum_year):
    """Only official links visibly identifying an edition are candidates."""
    soup = BeautifulSoup(content, 'html.parser')
    found = {}
    for anchor in soup.select('a[href]'):
        label = anchor.get_text(' ', strip=True)
        # Year selectors are valid, unrelated dated news links are not.
        match = re.fullmatch(r'(?:' + re.escape(title) + r'\s*)?(20\d{2})', label, re.I)
        if not match:
            match = re.search(r'\b' + re.escape(title) + r'\s*(20\d{2})\b', label, re.I)
        if not match:
            continue
        year = int(match[1])
        url = urljoin(root_url, anchor['href'])
        if year >= minimum_year and urlparse(url).hostname in allowed_hosts:
            found[year] = dict(url=url, discovered_from=root_url)
    return found
