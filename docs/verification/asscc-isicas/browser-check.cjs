const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.SITE_ORIGIN || 'http://127.0.0.1:4000';
const base = `${origin}/mms-deadlines`;
const output = __dirname;
fs.mkdirSync(output, { recursive: true });
let browser;
(async () => {
  browser = await chromium.launch({headless:true});
  const context = await browser.newContext({ viewport:{width:1280,height:1000}, timezoneId:'Asia/Seoul', acceptDownloads:true });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', r => { if (r.url().startsWith(origin) && r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  await page.clock.setFixedTime(new Date('2026-11-03T09:00:00Z'));
  const load = async url => { await page.goto(url); await page.waitForFunction(() => !document.getElementById('content').textContent.includes('Loading official')); };
  const snap = async name => page.screenshot({path:path.join(output,name),fullPage:true});
  await load(`${base}/?category=Circuit`);
  for (const year of [2024,2025,2026,2027,2028]) assert.equal(await page.getByRole('link',{name:`ESSERC ${year}`,exact:true}).count(),1);
  await page.selectOption('#year','2026');
  assert.equal(await page.locator('#content article').count(),6);
  for (const title of ['ESSERC','A-SSCC','ISICAS']) assert.equal(await page.getByRole('link',{name:`${title} 2026`,exact:true}).count(),1);
  await snap('circuit-2026.png');
  const downloads = [];
  for (const id of ['esserc26','asscc26','isicas26']) {
    await load(`${base}/conference/?id=${id}`);
    assert.equal(await page.locator('#content .detail').count(),1);
    const promise=page.waitForEvent('download');
    await page.getByRole('link',{name:'Download all milestones (ICS)'}).click();
    const download=await promise;
    const file=await download.path(); const ics=fs.readFileSync(file,'utf8').replace(/\r\n[ \t]/g,'');
    assert.ok(ics.includes('BEGIN:VCALENDAR'));
    assert.equal(download.suggestedFilename(),`${id}.ics`);
    downloads.push({id,events:(ics.match(/BEGIN:VEVENT/g)||[]).length});
    if(id==='isicas26') {
      const labels=await page.locator('#content .event h3').allTextContents();
      for(const journal of ['TCAS-I','TBioCAS','TCAS-AI','TVLSI','TCAS-II','OJCAS']) {
        assert.ok(labels.includes(`Paper submission · ${journal}`));
        assert.ok(ics.includes(`SUMMARY:ISICAS 2026 — paper · ${journal}`));
      }
      assert.equal(downloads.at(-1).events,8);
      assert.ok(ics.includes('UID:isicas26-paper-tcas-i@mms-deadlines'));
      await snap('isicas-2026-detail.png');
    }
    if(id==='asscc26') await snap('asscc-2026-detail.png');
  }
  await load(`${base}/calendar.html?category=Circuit&conference=ISICAS&year=2026`);
  assert.equal(await page.locator('#content .event').count(),8);
  for(const journal of ['TCAS-I','TBioCAS','TCAS-AI','TVLSI','TCAS-II','OJCAS'])
    assert.equal(await page.getByRole('heading',{name:`Paper submission · ${journal}`,exact:true}).count(),1);
  await snap('isicas-2026-calendar.png');
  await page.clock.setFixedTime(new Date('2026-05-20T03:00:00Z'));
  await load(`${base}/?category=Circuit&conference=ISICAS&year=2026`);
  assert.match(await page.locator('#content').innerText(), /Upcoming & ongoing/);
  assert.doesNotMatch(await page.locator('#content').innerText(), /Submissions closed/);
  assert.match(await page.locator('#content').innerText(), /Next: Paper submission · TCAS-II/);
  await snap('isicas-between-deadlines.png');
  await page.clock.setFixedTime(new Date('2026-06-02T03:00:00Z'));
  await page.reload();await page.waitForSelector('#content article');
  assert.match(await page.locator('#content').innerText(), /Submissions closed/);
  await page.route('**/schedule.json',async route=>{
    const response=await route.fetch();const data=await response.json();
    const record=data.conferences.find(r=>r.id==='isicas26');
    Object.assign(record.events.find(e=>e.track==='ojcas'),{date:'TBA',precision:'tba'});
    await route.fulfill({response,json:data});
  });
  await page.reload();await page.waitForSelector('#content article');
  assert.match(await page.locator('#content').innerText(), /Upcoming & ongoing/);
  assert.doesNotMatch(await page.locator('#content').innerText(), /Submissions closed/);
  await page.unroute('**/schedule.json');
  await page.clock.setFixedTime(new Date('2027-01-01T03:00:00Z'));
  await page.route('**/schedule.json',async route=>{
    const response=await route.fetch();const data=await response.json();
    const record=data.conferences.find(r=>r.id==='isicas27');
    Object.assign(record.events.find(e=>e.kind==='conference'),{date:'TBA',precision:'tba',end:undefined});
    await route.fulfill({response,json:data});
  });
  await load(`${base}/conference/?id=isicas27`);
  const historical=page.locator('.historical-reference');
  for(const journal of ['TCAS-I','TBioCAS','TCAS-AI','TVLSI','TCAS-II','OJCAS'])
    assert.equal(await historical.getByRole('heading',{name:`Paper submission · ${journal}`,exact:true}).count(),1);
  await page.unroute('**/schedule.json');
  await page.setViewportSize({width:390,height:844});
  await load(`${base}/conference/?id=isicas26`);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  assert.deepEqual(errors,[]);
  const report={browser:'Chromium',timezone:'Asia/Seoul',circuitEditions:'ESSERC 2024–2028 preserved; 2026 Circuit filter contains six conferences',downloads,
    isicasJournalLabels:6,isicasCalendarEvents:8,betweenDeadlines:'open on 2026-05-20, next TCAS-II',
    afterAllDeadlines:'closed on 2026-06-02',unknownJournalDeadline:'open with OJCAS TBA',historicalJournalLabels:6,mobileOverflow:false,errors};
  fs.writeFileSync(path.join(output,'browser-checks.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));await browser.close();
})().catch(async error=>{console.error(error);if(browser) await browser.close();process.exitCode=1});
