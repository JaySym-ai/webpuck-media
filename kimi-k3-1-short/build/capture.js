// Capture a page and record page-pixel boxes (at DPR 2) of phrases / selectors.
// usage: node capture.js jobs.json [onlyName]
const { chromium } = require('playwright');
const fs = require('fs');
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const only = process.argv[3];
const OUT = __dirname + '/../cap/';

async function run(b, j) {
  const ctx = await b.newContext({ viewport: { width: j.w || 1440, height: j.h || 900 }, deviceScaleFactor: 2, colorScheme: 'light', locale: 'en-US' });
  const p = await ctx.newPage();
  try { await p.goto(j.url, { waitUntil: 'networkidle', timeout: 45000 }); } catch (e) { console.error(j.name, 'goto', e.message); }
  await p.waitForTimeout(j.wait || 3000);
  for (const t of (j.clicks || [])) {
    try { await p.getByRole('button', { name: t }).first().click({ timeout: 10000 }); await p.waitForTimeout(800); }
    catch (e) { console.error(j.name, 'no button', t); }
  }
  if (j.full) {
    const H = await p.evaluate(() => document.body.scrollHeight);
    for (let y = 0; y < H; y += 700) { await p.evaluate(y => window.scrollTo(0, y), y); await p.waitForTimeout(120); }
    await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(800);
  }
  if (j.scrollTo !== undefined) {
    await p.mouse.move(300, 500); await p.mouse.wheel(0, j.scrollTo); await p.waitForTimeout(6000);
  }
  if (j.clipTo) {
    const y = await p.evaluate(ph => {
      let best = null;
      for (const el of document.querySelectorAll('body *')) {
        if (el.textContent.includes(ph)) { const r = el.getBoundingClientRect(); if (r.height > 0 && (!best || r.height < best.h)) best = { y: r.top + scrollY, h: r.height }; }
      }
      return best ? best.y : 0;
    }, j.clipTo);
    j.clip = [0, Math.max(0, Math.round(y - (j.clipAbove || 500))), j.w || 1440, j.clipH || 1500];
  }
  if (j.clip && !j.noScrollLoop) {
    const [cx, cy, cw, ch] = j.clip;
    for (let y = 0; y <= cy + ch; y += 300) { await p.evaluate(y => window.scrollTo(0, y), y); await p.waitForTimeout(250); }
    await p.evaluate(y => window.scrollTo(0, y), Math.max(0, cy + ch / 2 - (j.h || 900) / 2)); await p.waitForTimeout(2500);
  }
  if (j.eval) { try { await p.evaluate(j.eval); await p.waitForTimeout(1500); } catch (e) { console.error(j.name, 'eval', e.message); } }
  const boxes = await p.evaluate(({ phrases, sels }) => {
    const out = {};
    const sx = window.scrollX, sy = window.scrollY;
    const vis = r => r.width > 0 && r.height > 0;
    // concatenated visible text with node offsets, phrase may span nodes
    const nodes = []; let full = '';
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let nd;
    while ((nd = tw.nextNode())) {
      const pe = nd.parentElement; if (!pe) continue;
      const cs = getComputedStyle(pe); if (cs.display === 'none' || cs.visibility === 'hidden' || pe.closest('script,style,noscript')) continue;
      nodes.push([nd, full.length]); full += nd.textContent;
    }
    const lowFull = full.toLowerCase();
    const locate = off => { let lo = 0, hi = nodes.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (nodes[m][1] <= off) lo = m; else hi = m - 1; } return [nodes[lo][0], off - nodes[lo][1]]; };
    for (const ph of phrases || []) {
      const low = ph.toLowerCase(); const occ = []; const blks = []; let i = -1;
      while ((i = lowFull.indexOf(low, i + 1)) >= 0 && occ.length < 12) {
        const [sn, so] = locate(i); const [en, eo] = locate(i + ph.length - 1);
        const r = document.createRange(); r.setStart(sn, so); r.setEnd(en, eo + 1);
        const rects = [...r.getClientRects()].filter(q => q.width > 1 && q.height > 1);
        // merge rects on same line
        const lines = [];
        for (const q of rects) { const L = lines.find(l => Math.abs(l[1] - q.top) < q.height * 0.5); if (L) { L[0] = Math.min(L[0], q.left + sx); L[2] = Math.max(L[2], q.right + sx); L[3] = Math.max(L[3], q.bottom + sy); } else lines.push([q.left + sx, q.top + sy, q.right + sx, q.bottom + sy]); }
        if (lines.length) {
          occ.push(lines);
          let el = sn.parentElement;
          while (el && el.parentElement && ['inline', 'inline-block', 'contents', 'inline-flex'].includes(getComputedStyle(el).display)) el = el.parentElement;
          const q = el.getBoundingClientRect();
          blks.push([[q.left + sx, q.top + sy, q.right + sx, q.bottom + sy]]);
        }
      }
      out[ph] = occ.length ? occ : null;
      out[ph + '@blk'] = blks.length ? blks : null;
    }
    for (const [k, s] of Object.entries(sels || {})) {
      const el = document.querySelector(s);
      if (el) { const q = el.getBoundingClientRect(); out[k] = [[[q.left + sx, q.top + sy, q.right + sx, q.bottom + sy]]]; } else out[k] = null;
    }
    out.__sy = [[[window.scrollY, window.scrollY, window.scrollY, window.scrollY]]];
    return out;
  }, { phrases: j.phrases, sels: j.sels });
  const SY = boxes.__sy[0][0][0]; delete boxes.__sy;
  for (const k in boxes) if (boxes[k]) boxes[k] = boxes[k].map(o => o.map(r => r.map(v => Math.round(v * 2))));
  if (j.scrollTo !== undefined && !j.clip) {
    const sy = SY;
    for (const k in boxes) if (boxes[k]) boxes[k] = boxes[k].map(o => o.map(r => [r[0], r[1] - sy * 2, r[2], r[3] - sy * 2]));
    await p.screenshot({ path: OUT + j.name + '.png' });
  } else if (j.clip) {
    const [cx, cy, cw, ch] = j.clip;
    for (const k in boxes) if (boxes[k]) boxes[k] = boxes[k].map(o => o.map(r => [r[0] - cx * 2, r[1] - cy * 2, r[2] - cx * 2, r[3] - cy * 2]));
    await p.screenshot({ path: OUT + j.name + '.png', fullPage: true, clip: { x: cx, y: cy, width: cw, height: ch } });
  } else
  await p.screenshot({ path: OUT + j.name + '.png', fullPage: !!j.full });
  fs.writeFileSync(OUT + j.name + '.txt', await p.evaluate(() => document.body.innerText));
  fs.writeFileSync(OUT + j.name + '.json', JSON.stringify(boxes, null, 1));
  const missing = Object.keys(boxes).filter(k => !boxes[k]);
  console.log(j.name, 'ok', missing.length ? 'MISSING: ' + missing.join(' | ') : '');
  await ctx.close();
}

(async () => {
  const b = await chromium.launch();
  const list = jobs.filter(j => !only || only.split(',').includes(j.name));
  for (let i = 0; i < list.length; i += 4) await Promise.all(list.slice(i, i + 4).map(j => run(b, j)));
  await b.close();
})();
