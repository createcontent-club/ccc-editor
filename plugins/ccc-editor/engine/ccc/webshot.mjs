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

// Čišćenje: SVI fiksirani/lepljivi slojevi (zaglavlja, cookie/consent prozori, "heads up" kutije, chat dugmad),
// dijalozi, i reklamna mesta (prazni sivi pravougaonici i baneri) — na snimku ostaje samo sadržaj stranice.
const CLEAN = `(() => {
  if (!window.__cccClean) {
    window.__cccClean = () => {
      for (const dl of document.querySelectorAll('dialog')) { try { dl.close(); } catch (e) {} dl.remove(); }  // modalni <dialog> (siva ::backdrop)
      const AD = /(^|[-_ ])(ad|ads|adv|advert|advertisement|adslot|ad-slot|adunit|ad-unit|ad-container|dfp|gpt|sponsor|sponsored|promo-banner|taboola|outbrain|leaderboard|billboard|skyscraper)([-_ ]|$)/i;
      const OVER = /ab-in-app-message|ab-iam|braze|intercom|drift-|transcend|osano|truste|cookiebot|usercentrics|cookie|consent|gdpr|privacy-banner|modal|popup|pop-up|overlay|newsletter|subscribe-wall|paywall|toast|onetrust|didomi|sp_message|cmp|interstitial|heads-?up|notice-bar/i;
      // cela stranica, ne samo <body>: consent menadžeri (Transcend, OneTrust…) se kače pored body-ja, često u zatvorenom shadow DOM-u
      for (const e of [...document.querySelectorAll('*')]) {
        if (!e.isConnected || e === document.documentElement || e === document.head || e === document.body || e.closest('head')) continue;
        const st = getComputedStyle(e);
        const cls = (typeof e.className === 'string' ? e.className : '') + ' ' + (e.id || '');
        if (st.position === 'fixed' || st.position === 'sticky') { e.remove(); continue; }
    if (e.tagName === 'IFRAME' && +st.zIndex >= 1000) { e.remove(); continue; }
        if (e.getAttribute('role') === 'dialog' || e.getAttribute('aria-modal') === 'true') { e.remove(); continue; }
        if (OVER.test(cls) && (st.position === 'absolute' || +st.zIndex > 10)) { e.remove(); continue; }
        // prozor za newsletter/pretplatu koji lebdi preko sadržaja (visok z-index, apsolutno pozicioniran)
        if ((st.position === 'absolute') && +st.zIndex >= 100 && /subscribe|sign up|newsletter|join now/i.test(e.textContent || '') &&
            (e.textContent || '').length < 1500) { e.remove(); continue; }
        if (AD.test(cls) || (e.tagName === 'IFRAME' && /doubleclick|googlesyndication|adservice|amazon-adsystem|taboola|outbrain/i.test(e.src || '')) ||
            e.tagName === 'INS' && /adsbygoogle/.test(cls)) { e.style.setProperty('display', 'none', 'important'); }
      }
      // web komponente (shadow DOM) sa pristankom/kolačićima — npr. "Just a heads up" kutija
      for (const e of [...document.querySelectorAll('*')]) {
        if (!e.isConnected || !e.shadowRoot) continue;
        const t = (e.shadowRoot.textContent || '').toLowerCase();
        if (t.length < 3000 && /cookie|consent|privacy|third-party|heads up|accept all|do not sell/.test(t)) e.remove();
      }
      // reklamni baneri (leaderboard 728×90, billboard 970×250…) — široka niska slika/iframe
      for (const m of [...document.querySelectorAll('img, iframe')]) {
        const r = m.getBoundingClientRect();
        if (r.width >= 600 && r.width <= 1010 && r.height >= 60 && r.height <= 260 && r.width / r.height >= 3.5) {
          (m.closest('a, div, aside, section') || m).style.setProperty('display', 'none', 'important');
        }
      }
      document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto';
    };
    // sve što stigne POSLE čišćenja (Braze/Intercom poruke, newsletter prozori, sive pozadine) — ukloni čim se pojavi
    let pend = 0;
    new MutationObserver(() => { if (!pend) pend = setTimeout(() => { pend = 0; window.__cccClean(); }, 60); })
      .observe(document.documentElement, {childList: true, subtree: true});
  }
  window.__cccClean();
})()`;

if (!o.svg) {
  // Cookie/consent baneri: klik na "Accept/Agree/OK…", pa uklanjanje preostalih fiksnih slojeva i lepljivih zaglavlja.
  await js(`(() => {
    const re = /^\\s*(accept( all)?( cookies)?|allow( all)?( cookies)?|i agree|agree( and close)?|got it|ok(ay)?|continue|yes,? i agree|prihvat|slažem|alle akzeptieren|akzeptieren|tout accepter|accepter|aceptar( todo)?|accetta)/i;
    const all = (root) => { const out = [...root.querySelectorAll('*')]; for (const e of [...out]) if (e.shadowRoot) out.push(...all(e.shadowRoot)); return out; };
    const els = all(document).filter((e) => e.matches('button, a, [role=button], input[type=button], input[type=submit]'));
    const b = els.find((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && re.test((e.innerText || e.value || '').trim()); });
    if (b) b.click();
  })()`);
  await sleep(700);
  await js(CLEAN);
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
      window.__cccFound = el;
      const r = el.getBoundingClientRect();
      const cut = r.x < -2 || r.y < -2 || r.right > innerWidth + 2 || r.bottom > innerHeight + 2;
      return {x: Math.max(0, r.x), y: Math.max(0, r.y), w: Math.min(r.width, innerWidth), h: Math.min(r.height, innerHeight), cut};
    })()`);
  }
}

// Oznake (`marks`): tačan pravougaonik svake izgovorene fraze (ime, cifra) — za isticanje markerom na reč.
let marks = [];
if (o.marks && o.marks.length && !o.svg) {
  marks = await js(`(() => {
    const out = [];
    const want = ${JSON.stringify(o.marks || [])};
    const main = window.__cccFound || null;  // element nađen sa --find/--selector
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const all = []; while (walker.nextNode()) all.push(walker.currentNode);
    const nodes = main ? [...all.filter((n) => main.contains(n)), ...all.filter((n) => !main.contains(n))] : all;
    for (const m of want) {
      const needle = m.toLowerCase();
      let hit = null;
      for (const n of nodes) {
        const t = (n.nodeValue || '').toLowerCase(); const i = t.indexOf(needle);
        if (i < 0) continue;
        const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + m.length);
        const b = r.getBoundingClientRect();
        if (b.width && b.height && b.top >= 0 && b.bottom <= innerHeight) {
          const lines = [...r.getClientRects()].filter((q) => q.width > 2).map((q) => ({x: q.x, y: q.y, w: q.width, h: q.height}));
          hit = {x: b.x, y: b.y, w: b.width, h: b.height, lines}; break;
        }
      }
      out.push({text: m, rect: hit});
    }
    return out;
  })()`);
}

await js(CLEAN);  // iskačući prozori koji su stigli kasnije (newsletter posle par sekundi…)
await sleep(1500);
await js(CLEAN);
await sleep(250);

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
  rect: rect && !cropped ? {x: s(rect.x), y: s(rect.y), w: s(rect.w), h: s(rect.h)} : null, found: Boolean(rect) || !(o.find || o.selector),
  partial: Boolean(rect && rect.w && (rect.cut)),
  marks: marks.map((m) => ({text: m.text, rect: m.rect && !cropped ? {x: Math.round(m.rect.x * DSF), y: Math.round(m.rect.y * DSF),
    w: Math.round(m.rect.w * DSF), h: Math.round(m.rect.h * DSF)} : null,
    lines: m.rect && !cropped ? (m.rect.lines || []).map((q) => ({x: Math.round(q.x * DSF), y: Math.round(q.y * DSF), w: Math.round(q.w * DSF), h: Math.round(q.h * DSF)})) : []}))});
