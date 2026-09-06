/* One schedule dataset powers list, detail, calendar and generated ICS feeds. */
(function () {
  'use strict';
  const labels = { abstract: 'Abstract submission', paper: 'Paper submission', arr: 'ARR submission', commitment: 'EMNLP commitment', notification: 'Acceptance notification', conference: 'Main conference' };
  const base = document.body.dataset.base || '';
  const view = document.body.dataset.view;
  const content = document.getElementById('content');
  const params = new URLSearchParams(location.search);
  const localZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  let records = [];
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function link(text, href) {
    const element = node('a', text);
    element.href = href;
    if (href.endsWith('.ics')) element.download = '';
    return element;
  }
  function today() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }
  function dateLabel(event) {
    if (event.precision === 'tba') return 'TBA';
    return event.date + (event.end ? ` – ${event.end}` : '') + (event.timezone !== 'TBA' ? ` (${event.timezone})` : ' (time zone unannounced)');
  }
  function localLabel(event) {
    return event.precision === 'datetime' ? `${new Date(event.utc).toLocaleString()} (${localZone})` : 'Date only · no precise countdown';
  }
  function future(event) {
    return event.precision === 'datetime' ? Date.parse(event.utc) > Date.now() : event.precision === 'date' && (event.end || event.date) >= today();
  }
  function sortKey(event) { return event.utc || event.date; }
  function nextEvent(record) {
    return record.events.filter(future).sort((a, b) => sortKey(a).localeCompare(sortKey(b)))[0];
  }
  function phase(record) {
    const conference = record.events.find(e => e.kind === 'conference');
    if (conference.precision === 'tba') return 'Dates to be announced';
    return (conference.end || conference.date.slice(0, 10)) < today() ? 'Past conferences' : 'Upcoming & ongoing';
  }
  function timer(event) {
    const element = node('span', '', 'countdown');
    if (event.precision === 'datetime' && future(event)) element.dataset.utc = event.utc;
    return element;
  }
  function tick() {
    document.querySelectorAll('[data-utc]').forEach(element => {
      const remaining = Math.floor((Date.parse(element.dataset.utc) - Date.now()) / 1000);
      if (remaining <= 0) { render(); return; }
      element.textContent = `${Math.floor(remaining / 86400)}d ${Math.floor(remaining / 3600) % 24}h ${Math.floor(remaining / 60) % 60}m ${remaining % 60}s`;
    });
  }
  function eventView(event) {
    const element = node('div', undefined, 'event');
    element.append(node('h3', labels[event.kind]), node('p', `Official: ${dateLabel(event)}`));
    if (event.precision !== 'tba') element.append(node('p', localLabel(event), 'meta'));
    if (event.place) element.append(node('p', event.place));
    if (event.unresolved_time) element.append(node('p', `Published time: ${event.unresolved_time}; time zone needs confirmation.`, 'warning'));
    element.append(timer(event));
    event.sources.forEach((source, index) => element.append(link(`Official source ${index + 1} ↗`, source)));
    if (event.checked_at) element.append(node('p', `Verified: ${new Date(event.checked_at).toLocaleString()}${event.manual ? ' · Manual correction' : ''}`, 'meta'));
    return element;
  }
  function card(record) {
    const element = node('article', undefined, 'card');
    element.append(node('span', record.sub, `tag ${record.sub.toLowerCase()}`));
    const heading = node('h3');
    heading.append(link(`${record.title} ${record.year}`, `${base}/conference/?id=${encodeURIComponent(record.id)}`));
    element.append(heading, node('div', `${record.date} · ${record.place}`, 'meta'));
    const next = nextEvent(record);
    const milestone = node('div', undefined, 'milestone');
    if (next) {
      milestone.append(node('strong', `Next: ${labels[next.kind]}`), node('div', dateLabel(next), 'meta'), node('div', localLabel(next), 'meta'), timer(next));
    } else milestone.append(node('span', phase(record) === 'Past conferences' ? 'Conference completed' : 'Next milestone: TBA'));
    element.append(milestone);
    if (record.needs_review) element.append(node('p', 'Needs review · see schedule and sources', 'warning'));
    const links = node('div', undefined, 'links');
    links.append(link('Full schedule →', `${base}/conference/?id=${encodeURIComponent(record.id)}`), link('Download ICS', `${base}/calendar/${record.id}.ics`));
    element.append(links);
    return element;
  }
  function selected() {
    return records.filter(record => ['category', 'conference', 'year'].every(key => {
      const value = document.getElementById(key).value;
      return !value || String(record[{ category: 'sub', conference: 'title', year: 'year' }[key]]) === value;
    }));
  }
  function render() {
    content.replaceChildren();
    if (view === 'detail') {
      document.getElementById('filters').hidden = true;
      const record = records.find(r => r.id === params.get('id'));
      if (!record) { content.append(node('p', 'Conference not found. Select a conference from the list.'), link('View conferences', `${base}/`)); return; }
      document.querySelector('h1').textContent = `${record.title} ${record.year}`;
      const detail = node('article', undefined, 'detail');
      detail.append(node('p', `${record.sub} · ${record.place} · ${phase(record)}`), link('Official website ↗', record.link), node('span', ' · '), link('Download all milestones (ICS)', `${base}/calendar/${record.id}.ics`));
      if (record.place_sources && record.place_sources.length) {
        const venue = node('p', 'Venue: ', 'meta');
        record.place_sources.forEach((source, index) => venue.append(link(`Official source ${index + 1} ↗ `, source)));
        if (record.place_checked_at) venue.append(node('span', ` · Verified: ${new Date(record.place_checked_at).toLocaleString()}`));
        detail.append(venue);
      }
      record.events.forEach(event => detail.append(eventView(event)));
      if (record.issues.length) {
        const issues = node('details');
        issues.append(node('summary', `Needs review (${record.issues.length})`));
        const list = node('ul');
        record.issues.forEach(issue => list.append(node('li', issue)));
        issues.append(list); detail.append(issues);
      }
      content.append(detail);
    } else if (view === 'calendar') {
      const events = selected().flatMap(record => record.events.filter(e => e.precision !== 'tba').map(event => ({ record, event })));
      events.sort((a, b) => sortKey(a.event).localeCompare(sortKey(b.event)));
      let month;
      events.forEach(({ record, event }) => {
        const nextMonth = event.date.slice(0, 7);
        if (nextMonth !== month) { content.append(node('h2', nextMonth)); month = nextMonth; }
        const row = eventView(event);
        row.prepend(link(`${record.title} ${record.year}`, `${base}/conference/?id=${record.id}`));
        content.append(row);
      });
      if (!events.length) content.append(node('p', 'No published dates match these filters.'));
      content.append(node('p', 'Unannounced (TBA) milestones appear on each conference’s full schedule.'));
    } else {
      const filtered = selected();
      ['Upcoming & ongoing', 'Dates to be announced', 'Past conferences'].forEach(group => {
        const matches = filtered.filter(record => phase(record) === group);
        if (group === 'Upcoming & ongoing') {
          matches.sort((a, b) => {
            const aNext = nextEvent(a);
            const bNext = nextEvent(b);
            return (aNext ? sortKey(aNext) : '9999').localeCompare(bNext ? sortKey(bNext) : '9999') || a.id.localeCompare(b.id);
          });
        }
        if (!matches.length) return;
        content.append(node('h2', `${group} · ${matches.length}`));
        const grid = node('div', undefined, 'grid');
        matches.forEach(record => grid.append(card(record))); content.append(grid);
      });
      if (!filtered.length) content.append(node('p', 'No conferences match these filters.'));
    }
    tick();
  }
  fetch(`${base}/schedule.json`).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then(data => {
    records = data.conferences;
    const status = data.status || {};
    const when = value => value ? new Date(value).toLocaleString() : 'No successful collection yet';
    document.getElementById('sync-status').textContent = `Last attempt: ${when(status.last_attempt)} · Last successful collection: ${when(status.last_success)} · Times shown in ${localZone}`;
    ['conference', 'year'].forEach(key => {
      const values = [...new Set(records.map(r => r[key === 'conference' ? 'title' : 'year']))];
      values.sort(key === 'year' ? (a, b) => b - a : undefined);
      values.forEach(value => { const option = node('option', value); option.value = value; document.getElementById(key).append(option); });
    });
    ['category', 'conference', 'year'].forEach(key => {
      const select = document.getElementById(key);
      select.value = params.get(key) || '';
      if (select.selectedIndex === -1) select.value = '';
      select.addEventListener('change', () => {
        const query = new URLSearchParams();
        ['category', 'conference', 'year'].forEach(k => { if (document.getElementById(k).value) query.set(k, document.getElementById(k).value); });
        history.replaceState(null, '', location.pathname + (query.size ? `?${query}` : ''));
        render();
      });
    });
    document.getElementById('reset').addEventListener('click', () => {
      ['category', 'conference', 'year'].forEach(key => { document.getElementById(key).value = ''; });
      history.replaceState(null, '', location.pathname); render();
    });
    Object.entries(status.conferences || {}).forEach(([title, health]) => {
      const row = node('div');
      row.append(node('strong', `${title} · ${health.needs_review ? 'Needs review' : 'Verified'}`), node('p', `Attempt: ${when(health.last_attempt)} · Success: ${when(health.last_success)}`));
      health.sources.forEach(source => row.append(link(`${source} ↗ `, source)));
      if (health.issues.length) { const list = node('ul'); health.issues.forEach(issue => list.append(node('li', issue))); row.append(list); }
      document.getElementById('health').append(row);
    });
    render(); setInterval(tick, 1000);
  }).catch(error => { content.replaceChildren(node('p', `Unable to load schedules: ${error.message}. Please retry.`)); });
}());
