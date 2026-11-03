/* Dependency-free rendering regressions; run with: node tests/test_schedule.js */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '../static/js/schedule.js'), 'utf8');

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
  const stamp = Date.parse(now);
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [stamp])); } static now() { return stamp; } }
  vm.runInNewContext(script, {
    document: { body, createElement: tag => new Element(tag), getElementById: get,
      querySelector: () => get('h1'), querySelectorAll: () => [] },
    location: { search, pathname: '/' }, history: { replaceState() {} }, URLSearchParams, Intl, Date: Clock,
    fetch: async () => ({ ok: true, json: async () => ({ conferences: records, status: {} }) }), setInterval() {}
  });
  await new Promise(resolve => setImmediate(resolve));
  const content = get('content');
  assert.doesNotMatch(content.textContent, /Unable to load/);
  return content;
}
function allNodes(element) { return [element, ...element.children.flatMap(allNodes)]; }

test('between first and last journal deadlines the edition remains open and names the next journal', async () => {
  const content = await render([edition()]);
  assert.match(content.textContent, /Upcoming & ongoing/);
  assert.doesNotMatch(content.textContent, /Submissions closed/);
  assert.match(content.textContent, /Next: Paper submission · TCAS-II/);
});

test('only all confirmed past deadlines close submissions; a TBA keeps them open', async () => {
  const closed = await render([edition()], 'list', '', '2026-06-02T12:00:00Z');
  assert.match(closed.textContent, /Submissions closed/);
  const record = edition();
  record.events[5] = { ...record.events[5], date: 'TBA', precision: 'tba' };
  const open = await render([record], 'list', '', '2026-06-02T12:00:00Z');
  assert.match(open.textContent, /Upcoming & ongoing/);
  assert.doesNotMatch(open.textContent, /Submissions closed/);
  const onDeadline = await render([edition()], 'list', '', '2026-06-01T12:00:00Z');
  assert.doesNotMatch(onDeadline.textContent, /Submissions closed/);
});

test('detail and calendar render all six journal deadlines and retain download addresses', async () => {
  for (const [view, search] of [['detail', '?id=isicas26'], ['calendar', '?category=Circuit']]) {
    const content = await render([edition()], view, search);
    const headings = allNodes(content).filter(e => e.tag === 'h3').map(e => e.textContent);
    assert.deepEqual(headings.filter(h => h.startsWith('Paper submission')), journals.map(j => `Paper submission · ${j}`));
    if (view === 'detail') assert.ok(allNodes(content).some(e => e.href === '/mms-deadlines/calendar/isicas26.ics'));
  }
});

test('historical reference retains each journal label when current dates are TBA', async () => {
  const current = edition(2027);
  current.events = current.events.map(e => ({ ...e, date: 'TBA', precision: 'tba', end: undefined }));
  const content = await render([current, edition()], 'detail', '?id=isicas27', '2027-01-01T12:00:00Z');
  assert.match(content.textContent, /Most recent completed edition · ISICAS 2026/);
  for (const journal of journals) assert.ok(content.textContent.includes(`Paper submission · ${journal}`));
});

test('Circuit filter includes ESSERC, A-SSCC, ISICAS and excludes Algorithm records', async () => {
  const records = ['ESSERC', 'A-SSCC', 'ISICAS', 'ICML'].map((title, i) => ({ ...edition(),
    title, id: `conference${i}`, sub: title === 'ICML' ? 'Algorithm' : 'Circuit' }));
  const content = await render(records);
  const cards = allNodes(content).filter(e => e.tag === 'article').map(e => e.textContent);
  assert.equal(cards.length, 3);
  for (const title of ['ESSERC', 'A-SSCC', 'ISICAS']) assert.ok(cards.some(card => card.includes(`${title} 2026`)));
  assert.ok(cards.every(card => !card.includes('ICML')));
});
