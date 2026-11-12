// Screenshot web stranice u headless Chrome-u koji već imamo (Remotion) — bez dodatnih paketa.
// node webshot.mjs '<json>'  →  stdout: {"ok":true,"rect":{x,y,w,h}|null,"title":"…","url":"…","w":…,"h":…} | {"ok":false,"error":"…"}
// Opcije: chrome, url, out, mobile (bool), find (tekst), selector (css), svg (bool: url je lokalni .html sa slikom, providna pozadina)
import {spawn} from 'node:child_process';
import {writeFileSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const o = JSON.parse(process.argv[2]);
if (typeof WebSocket === 'undefined') { process.stdout.write(JSON.stringify({ok: false, error: `Node ${process.version} is too old (need 22+) — run setup again`}) + '\n'); process.exit(1); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = (x) => { process.stdout.write(JSON.stringify(x) + '\n'); };
const port = 9400 + Math.floor(Math.random() * 500);
const prof = mkdtempSync(join(tmpdir(), 'ccc-shot-'));
const UA_DESK = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
const UA_MOB = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';

const proc = spawn(o.chrome, ['--headless=new', `--remote-debugging-port=${port}`, '--no-first-run', '--hide-scrollbars',
  '--mute-audio', '--disable-gpu', `--user-data-dir=${prof}`, 'about:blank'], {stdio: 'ignore'});
const done = (x, code = 0) => { out(x); try { proc.kill(); } catch {} try { rmSync(prof, {recursive: true, force: true}); } catch {} process.exit(code); };
setTimeout(() => done({ok: false, error: 'timeout (the page took too long)'}, 1), 45000);

let list;
for (let i = 0; i < 80 && !list; i++) {
  try { list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch { await sleep(150); }
}
if (!list) done({ok: false, error: 'browser did not start'}, 1);
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let docStatus = null;
let id = 0; const pend = new Map(); const waiters = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); }
  else if (m.method === 'Network.responseReceived' && m.params.type === 'Document' && docStatus === null) docStatus = m.params.response.status;
  if (m.method) waiters.filter((w) => w.m === m.method).forEach((w) => { waiters.splice(waiters.indexOf(w), 1); w.res(m.params); });
});
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, {res, rej}); ws.send(JSON.stringify({id: i, method, params})); });
const once = (m, ms = 20000) => Promise.race([new Promise((res) => waiters.push({m, res})), sleep(ms)]);
const js = async (expr) => (await send('Runtime.evaluate', {expression: expr, awaitPromise: true, returnByValue: true})).result.value;

const mob = Boolean(o.mobile);
const W = mob ? 390 : 1280, H = mob ? 844 : 800, DSF = mob ? 3 : 2;
await send('Page.enable');
await send('Network.enable');
await send('Network.setUserAgentOverride', {userAgent: mob ? UA_MOB : UA_DESK, acceptLanguage: 'en-US,en'});
await send('Emulation.setDeviceMetricsOverride', {width: W, height: H, deviceScaleFactor: DSF, mobile: mob});
if (o.svg || o.crop) await send('Emulation.setDefaultBackgroundColorOverride', {color: {r: 0, g: 0, b: 0, a: 0}});
const loaded = once('Page.loadEventFired', 25000);
const nav = await send('Page.navigate', {url: o.url});
if (nav.errorText) done({ok: false, error: `can't open the page (${nav.errorText})`}, 1);
await loaded;
await sleep(o.svg ? 300 : 1800);

if (!o.svg) {
  // Cookie/consent baneri: klik na "Accept/Agree/OK…", pa uklanjanje preostalih fiksnih slojeva i lepljivih zaglavlja.
  await js(`(() => {
    const re = /^\\s*(accept( all)?( cookies)?|allow( all)?( cookies)?|i agree|agree( and close)?|got it|ok(ay)?|continue|yes,? i agree|prihvat|slažem|alle akzeptieren|akzeptieren|tout accepter|accepter|aceptar( todo)?|accetta)/i;
    const els = [...document.querySelectorAll('button, a, [role=button], input[type=button], input[type=submit]')];
    const b = els.find((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && re.test((e.innerText || e.value || '').trim()); });
    if (b) b.click();
  })()`);
  await sleep(700);
  await js(`(() => {
    const vh = innerHeight;
    for (const e of document.querySelectorAll('body *')) {
      const s = getComputedStyle(e);
      if ((s.position === 'fixed' || s.position === 'sticky')) {
        const r = e.getBoundingClientRect();
        if (r.height > vh * 0.12 || +s.zIndex > 999 || /cookie|consent|gdpr|banner|modal|popup|newsletter/i.test(e.className + ' ' + e.id)) e.remove();
      }
    }
    document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto';
  })()`);
}

let rect = null;
if (o.find || o.selector) {
  rect = await js(`(() => {
    let el = null;
    const sel = ${JSON.stringify(o.selector || '')}, needle = ${JSON.stringify((o.find || '').toLowerCase().replace(/\s+/g, ' ').trim())};
    if (sel) el = document.querySelector(sel);
    if (!el && needle) {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let best = null;
      while (w.nextNode()) {
        const n = w.currentNode, p = n.parentElement;
        if (!p) continue;
        const t = (p.innerText || '').toLowerCase().replace(/\\s+/g, ' ');
        if (t.includes(needle)) { const r = p.getBoundingClientRect(); if (r.width && r.height && (!best || t.length < best.t)) best = {p, t: t.length}; }
      }
      el = best && best.p;
    }
    if (!el) return null;
    el.scrollIntoView({block: 'center'});
    return true;
  })()`);
  if (rect) {
    await sleep(900);
    rect = await js(`(() => {
      const sel = ${JSON.stringify(o.selector || '')}, needle = ${JSON.stringify((o.find || '').toLowerCase().replace(/\s+/g, ' ').trim())};
      let el = sel ? document.querySelector(sel) : null;
      if (!el) {
        const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let best = null;
        while (w.nextNode()) { const p = w.currentNode.parentElement; if (!p) continue;
          const t = (p.innerText || '').toLowerCase().replace(/\\s+/g, ' ');
          if (t.includes(needle)) { const r = p.getBoundingClientRect(); if (r.width && r.height && (!best || t.length < best.t)) best = {p, t: t.length}; } }
        el = best && best.p;
      }
      const r = el.getBoundingClientRect();
      return {x: Math.max(0, r.x), y: Math.max(0, r.y), w: Math.min(r.width, innerWidth), h: Math.min(r.height, innerHeight)};
    })()`);
  }
}

let clip;
if (o.crop && rect && rect.w) {
  // samo element na providnoj podlozi: stranica oko njega (beli body, kontejneri) postaje providna
  await js(`(() => { const sel = ${JSON.stringify(o.selector || '')}; const el = sel && document.querySelector(sel);
    const keep = new Set(); for (let e = el; e; e = e.parentElement) keep.add(e);
    for (const e of keep) if (e !== el) e.style.setProperty('background', 'transparent', 'important');
    document.documentElement.style.setProperty('background', 'transparent', 'important'); })()`);  // samo traženi element (npr. objava), sa malo vazduha
  const pad = 12;
  clip = {x: Math.max(0, rect.x - pad), y: Math.max(0, rect.y - pad), width: rect.w + pad * 2, height: rect.h + pad * 2, scale: 1};
}
if (o.svg) {
  const r = await js(`(() => { const r = document.querySelector('img,svg').getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; })()`);
  clip = {...r, scale: 1};
}
const shot = await send('Page.captureScreenshot', {format: 'png', clip, captureBeyondViewport: false});
writeFileSync(o.out, Buffer.from(shot.data, 'base64'));
const title = await js('document.title');
// Zid umesto sadržaja: HTTP greška, bot/captcha provera, prijava ili paywall — Claude to mora da zna (ne koristi se).
const wall = o.svg ? null : await js(`(() => {
  const t = (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').slice(0, 4000).toLowerCase();
  const title = document.title.toLowerCase(), host = location.hostname.replace(/^www\\./, '');
  const has = (re) => re.test(t) || re.test(title);
  if (has(/just a moment|verify you are human|you are human|verification required|slide right to (secure|verify|complete)|press (and|&) hold|checking your browser|are you a robot|captcha|unusual traffic|access denied|request blocked|attention required|enable javascript and cookies|pardon our interruption|not a robot|bot detection/)) return 'bot check';
  if (has(/\\b404\\b|page not found|not found|doesn.t exist|no longer available|page isn.t available|this page could not be found/) && t.length < 3000) return 'page not found';
  if (has(/subscribe to (continue|read)|subscribers only|to continue reading|already a subscriber|create a free account to continue|this content is for subscribers/)) return 'paywall';
  if (has(/see photos, videos and more from|never miss a post from|(log in|sign in|sign up) to (see|view|continue|see more)|join now to see|you must log in|log in or sign up/)) return 'login wall';
  if (t.length < 200 && (title === host || title === '' )) return 'empty or blocked page';
  return null;
})()`);
const href = await js('location.href');
const s = (v) => (rect ? Math.round(v * DSF) : null);
const cropped = Boolean(clip && o.crop);
done({ok: true, title, url: href, w: clip ? Math.round(clip.width * (o.svg ? 1 : DSF)) : W * DSF, h: clip ? Math.round(clip.height * (o.svg ? 1 : DSF)) : H * DSF,
  status: docStatus, wall: docStatus >= 400 ? (docStatus === 404 || docStatus === 410 ? 'page not found' : `HTTP ${docStatus}`) : wall,
  rect: rect && !cropped ? {x: s(rect.x), y: s(rect.y), w: s(rect.w), h: s(rect.h)} : null, found: Boolean(rect) || !(o.find || o.selector)});
