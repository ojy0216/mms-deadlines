/* Dependency-free rendering regressions; run with: node tests/test_schedule.js */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '../static/js/schedule.js'), 'utf8');

// Exercise both daylight saving transitions regardless of the host time zone.
process.env.TZ = 'America/New_York';

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.value = ''; this.selectedIndex = 0; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return (this.text || '') + this.children.map(e => e.textContent).join('\n'); }
  append(...elements) { this.children.push(...elements); }
  prepend(...elements) { this.children.unshift(...elements); }
  replaceChildren(...elements) { this.children = elements; this.text = ''; }
  setAttribute() {}
  addEventListener() {}
}
const journals = ['TCAS-I', 'TBioCAS', 'TCAS-AI', 'TVLSI', 'TCAS-II', 'OJCAS'];
function edition(year = 2026) {
  return {
    title: 'ISICAS', id: `isicas${year % 100}`, year, sub: 'Circuit', date: `${year}-12-04 – ${year}-12-06`,
    place: 'Torino, Italy', link: 'https://2026.ieee-isicas.org/', issues: [],
    events: [
      ...journals.map((label, i) => ({ kind: 'paper', track: label.toLowerCase(), track_label: label,
        date: `${year}-${i < 4 ? '05-11' : '06-01'}`, precision: 'date', timezone: 'TBA', sources: [] })),
      { kind: 'conference', date: `${year}-12-04`, end: `${year}-12-06`, precision: 'date', timezone: 'TBA', sources: [] }
    ]
  };
}
async function render(records, view = 'list', search = '?category=Circuit', now = '2026-05-20T12:00:00Z') {
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element('div')); return elements.get(id); };
  const body = new Element('body'); body.dataset = { base: '/mms-deadlines', view };
  let stamp = Date.parse(now);
  let tick;
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [stamp])); } static now() { return stamp; } }
  vm.runInNewContext(script, {
    document: { body, createElement: tag => new Element(tag), getElementById: get,
      querySelector: () => get('h1'), querySelectorAll: selector => {
        assert.equal(selector, '[data-utc]');
        return allNodes(get('content')).filter(element => 'utc' in element.dataset);
      } },
    location: { search, pathname: '/' }, history: { replaceState() {} }, URLSearchParams, Intl, Date: Clock,
    fetch: async () => ({ ok: true, json: async () => ({ conferences: records, status: {} }) }),
    setInterval(callback, delay) { assert.equal(delay, 1000); tick = callback; }
  });
  await new Promise(resolve => setImmediate(resolve));
  const content = get('content');
  assert.doesNotMatch(content.textContent, /Unable to load/);
  return {
    content,
    advanceTo(now) {
      stamp = Date.parse(now);
      tick();
    }
  };
}
function allNodes(element) { return [element, ...element.children.flatMap(allNodes)]; }

test('between first and last journal deadlines the edition remains open and names the next journal', async () => {
  const { content } = await render([edition()]);
  assert.match(content.textContent, /Upcoming & ongoing/);
  assert.doesNotMatch(content.textContent, /Submissions closed/);
  assert.match(content.textContent, /Next: Paper submission · TCAS-II/);
});

test('only all confirmed past deadlines close submissions; a TBA keeps them open', async () => {
  const { content: closed } = await render([edition()], 'list', '', '2026-06-02T12:00:00Z');
  assert.match(closed.textContent, /Submissions closed/);
  const record = edition();
  record.events[5] = { ...record.events[5], date: 'TBA', precision: 'tba' };
  const { content: open } = await render([record], 'list', '', '2026-06-02T12:00:00Z');
  assert.match(open.textContent, /Upcoming & ongoing/);
  assert.doesNotMatch(open.textContent, /Submissions closed/);
  const { content: onDeadline } = await render([edition()], 'list', '', '2026-06-01T12:00:00Z');
  assert.doesNotMatch(onDeadline.textContent, /Submissions closed/);
});

test('detail and calendar render all six journal deadlines and retain download addresses', async () => {
  for (const [view, search] of [['detail', '?id=isicas26'], ['calendar', '?category=Circuit']]) {
    const { content } = await render([edition()], view, search);
    const headings = allNodes(content).filter(e => e.tag === 'h3').map(e => e.textContent);
    assert.deepEqual(headings.filter(h => h.startsWith('Paper submission')), journals.map(j => `Paper submission · ${j}`));
    if (view === 'detail') assert.ok(allNodes(content).some(e => e.href === '/mms-deadlines/calendar/isicas26.ics'));
  }
});

test('historical reference retains each journal label when current dates are TBA', async () => {
  const current = edition(2027);
  current.events = current.events.map(e => ({ ...e, date: 'TBA', precision: 'tba', end: undefined }));
  const { content } = await render([current, edition()], 'detail', '?id=isicas27', '2027-01-01T12:00:00Z');
  assert.match(content.textContent, /Most recent completed edition · ISICAS 2026/);
  for (const journal of journals) assert.ok(content.textContent.includes(`Paper submission · ${journal}`));
  const reference = allNodes(content).find(element => element.className === 'historical-reference');
  assert.ok(allNodes(reference).every(element => element.className !== 'countdown'));
});

test('the list leaves the counter absent when its next milestone is TBA', async () => {
  const events = [{ kind: 'conference', date: 'TBA', precision: 'tba', timezone: 'TBA', sources: [] }];
  const { content } = await render([{ ...edition(), events }]);
  assert.match(content.textContent, /Next milestone: TBA/);
  assert.ok(allNodes(content).every(element => element.className !== 'countdown'));
});

test('Circuit filter includes ESSERC, A-SSCC, ISICAS and excludes Algorithm records', async () => {
  const records = ['ESSERC', 'A-SSCC', 'ISICAS', 'ICML'].map((title, i) => ({ ...edition(),
    title, id: `conference${i}`, sub: title === 'ICML' ? 'Algorithm' : 'Circuit' }));
  const { content } = await render(records);
  const cards = allNodes(content).filter(e => e.tag === 'article').map(e => e.textContent);
  assert.equal(cards.length, 3);
  for (const title of ['ESSERC', 'A-SSCC', 'ISICAS']) assert.ok(cards.some(card => card.includes(`${title} 2026`)));
  assert.ok(cards.every(card => !card.includes('ICML')));
});

const views = { list: '', detail: '?id=isicas26', calendar: '?category=Circuit' };
function dateEvent(kind, date, end) {
  return { kind, date, end, precision: 'date', timezone: 'TBA', sources: [] };
}
function scheduleEntry(content, label) {
  return allNodes(content).find(element =>
    ['event', 'milestone'].includes(element.className) &&
    element.children.some(child => child.textContent === label || child.textContent === `Next: ${label}`));
}
function countdown(content, label) {
  return scheduleEntry(content, label)?.children.find(child => child.className === 'countdown')?.textContent;
}

test('date-only countdowns and the next milestone update at local midnight in all views', async () => {
  const events = [
    dateEvent('paper', '2026-11-25'),
    dateEvent('conference', '2026-11-27'),
    { kind: 'notification', date: 'TBA', precision: 'tba', timezone: 'TBA', sources: [] }
  ];
  for (const [view, search] of Object.entries(views)) {
    const { content, advanceTo } = await render([{ ...edition(), events }], view, search, '2026-11-18T12:00:00-05:00');
    assert.equal(countdown(content, 'Paper submission'), 'D-7', view);
    assert.match(scheduleEntry(content, 'Paper submission').textContent, /Date only · countdown uses your local date/);
    advanceTo('2026-11-24T23:59:59-05:00');
    assert.equal(countdown(content, 'Paper submission'), 'D-1', view);
    advanceTo('2026-11-25T00:00:00-05:00');
    assert.equal(countdown(content, 'Paper submission'), 'D-Day', view);
    advanceTo('2026-11-25T23:59:59-05:00');
    assert.equal(countdown(content, 'Paper submission'), 'D-Day', view);
    advanceTo('2026-11-26T00:00:00-05:00');
    assert.equal(countdown(content, 'Main conference'), 'D-1', view);
    if (view === 'list') {
      assert.equal(scheduleEntry(content, 'Paper submission'), undefined);
      assert.match(content.textContent, /Submissions closed/);
    } else {
      assert.equal(countdown(content, 'Paper submission'), '', view);
    }
    if (view === 'detail') {
      assert.match(scheduleEntry(content, 'Acceptance notification').textContent, /Official: TBA/);
      assert.equal(countdown(content, 'Acceptance notification'), '');
    }
    if (view === 'calendar') assert.equal(scheduleEntry(content, 'Acceptance notification'), undefined);
  }
});

test('a multi-day conference counts down to opening and remains ongoing through its last day', async () => {
  const events = [dateEvent('conference', '2026-11-27', '2026-11-29')];
  for (const [view, search] of Object.entries(views)) {
    const { content, advanceTo } = await render([{ ...edition(), events }], view, search, '2026-11-26T23:59:59-05:00');
    assert.equal(countdown(content, 'Main conference'), 'D-1', view);
    advanceTo('2026-11-27T00:00:00-05:00');
    assert.equal(countdown(content, 'Main conference'), 'D-Day', view);
    advanceTo('2026-11-28T00:00:00-05:00');
    assert.equal(countdown(content, 'Main conference'), 'Ongoing', view);
    advanceTo('2026-11-29T23:59:59-05:00');
    assert.equal(countdown(content, 'Main conference'), 'Ongoing', view);
    advanceTo('2026-11-30T00:00:00-05:00');
    if (view === 'list') {
      assert.match(content.textContent, /Conference completed/);
      assert.equal(countdown(content, 'Main conference'), undefined);
    } else {
      assert.equal(countdown(content, 'Main conference'), '', view);
    }
  }
});

test('a 23-hour or 25-hour day still counts as one calendar day', async () => {
  for (const [before, midnight, date] of [
    ['2026-03-08T00:00:00-05:00', '2026-03-09T00:00:00-04:00', '2026-03-09'],
    ['2026-11-01T00:00:00-04:00', '2026-11-02T00:00:00-05:00', '2026-11-02']
  ]) {
    const events = [dateEvent('conference', date)];
    for (const [view, search] of Object.entries(views)) {
      const { content, advanceTo } = await render([{ ...edition(), events }], view, search, before);
      assert.equal(countdown(content, 'Main conference'), 'D-1', `${view} at ${before}`);
      advanceTo(midnight);
      assert.equal(countdown(content, 'Main conference'), 'D-Day', `${view} at ${midnight}`);
    }
  }
});

test('timed milestones retain the live seconds countdown and expire at their announced time', async () => {
  const events = [
    { kind: 'paper', date: '2026-11-25 12:00:02', precision: 'datetime', timezone: 'UTC',
      utc: '2026-11-25T12:00:02Z', sources: [] },
    dateEvent('conference', '2026-11-27')
  ];
  for (const [view, search] of Object.entries(views)) {
    const { content, advanceTo } = await render([{ ...edition(), events }], view, search, '2026-11-25T12:00:00Z');
    assert.equal(countdown(content, 'Paper submission'), '0d 0h 0m 2s', view);
    advanceTo('2026-11-25T12:00:01Z');
    assert.equal(countdown(content, 'Paper submission'), '0d 0h 0m 1s', view);
    advanceTo('2026-11-25T12:00:01.500Z');
    assert.equal(countdown(content, 'Paper submission'), '0d 0h 0m 0s', view);
    advanceTo('2026-11-25T12:00:02Z');
    if (view === 'list') {
      assert.equal(scheduleEntry(content, 'Paper submission'), undefined);
      assert.equal(countdown(content, 'Main conference'), 'D-2');
    } else {
      assert.equal(countdown(content, 'Paper submission'), '', view);
    }
  }
});
