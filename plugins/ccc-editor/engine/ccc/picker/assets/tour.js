/* CCC vodič kroz stranicu (PLAN §14, faza 3): istakne jedan deo stranice, ispod/iznad kratko objašnjenje,
   "1 of 4", Back / Next / Skip. Sam se pokrene samo prvi put (editor pamti u <HOME>/ui-state.json, jer je port
   stranice svaki put drugi); kasnije dugme "How does this work?". Tastatura: Esc preskače, ← → koraci.
   Tekst za klijenta je na engleskom i bez znaka em dash. */
(function () {
  const CSS = `
  .tour-block { position: fixed; inset: 0; z-index: 1000; }
  .tour-hole { position: fixed; z-index: 1001; border-radius: 16px; pointer-events: none;
    box-shadow: 0 0 0 3px #3D8BFF, 0 0 30px rgba(0,102,255,.55), 0 0 0 200vmax rgba(0,0,0,.68); transition: all .28s ease; }
  .tour-tip { position: fixed; z-index: 1002; width: min(360px, calc(100vw - 32px)); background: #0B0F18; border: 1px solid rgba(0,102,255,.45);
    border-radius: 16px; padding: 18px 20px 16px; color: #fff; box-shadow: 0 20px 60px rgba(0,0,0,.6); transition: top .28s ease, left .28s ease;
    font: 400 14.5px/1.5 "Inter", system-ui, sans-serif; }
  .tour-tip .step { color: #3D8BFF; font: 800 11.5px/1 "Montserrat", "Inter", sans-serif; letter-spacing: .14em; text-transform: uppercase; }
  .tour-tip h3 { margin: 8px 0 6px; font: 800 18px/1.25 "Montserrat", "Inter", sans-serif; }
  .tour-tip p { margin: 0 0 14px; color: #C9D2E4; }
  .tour-tip .row { display: flex; align-items: center; gap: 10px; }
  .tour-tip .sp { flex: 1; }
  .tour-tip button { border-radius: 10px; padding: 9px 16px; font: 700 14px/1 "Montserrat", "Inter", sans-serif; cursor: pointer; transform: none; }
  .tour-tip .skip { background: none; border: 0; color: #8C95A8; padding: 9px 4px; box-shadow: none; text-decoration: underline; text-underline-offset: 3px; }
  .tour-tip .back { background: transparent; border: 1px solid rgba(255,255,255,.18); color: #DCE6FA; box-shadow: none; }
  .tour-tip .next { background: #0066FF; border: 0; color: #fff; box-shadow: 0 0 18px rgba(0,102,255,.5); }
  .tour-tip button:focus-visible { outline: 3px solid #3D8BFF; outline-offset: 2px; }
  .tour-tip button:hover { transform: none; }
  @media (prefers-reduced-motion: reduce) { .tour-hole, .tour-tip { transition: none; } }`;
  let st = null;
  const reduced = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function el(step) { const e = typeof step.el === "function" ? step.el() : document.querySelector(step.el); return e && e.getClientRects().length ? e : null; }

  function place() {
    if (!st) return;
    const step = st.steps[st.i], target = el(step);
    const pad = 8, vw = innerWidth, vh = innerHeight;
    const r = target ? target.getBoundingClientRect() : { left: vw / 2, top: vh / 2, width: 0, height: 0, right: vw / 2, bottom: vh / 2 };
    Object.assign(st.hole.style, { left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px` });
    const tw = st.tip.offsetWidth, th = st.tip.offsetHeight;
    let top = r.bottom + pad + 14;
    if (top + th > vh - 12) top = r.top - pad - 14 - th;            // nema mesta ispod → iznad
    if (top < 12) top = Math.max(12, Math.min(vh - th - 12, r.top + 12));  // ni iznad → preko gornjeg dela
    const left = Math.max(16, Math.min(vw - tw - 16, r.left + r.width / 2 - tw / 2));
    Object.assign(st.tip.style, { top: `${top}px`, left: `${left}px` });
  }

  function show(i) {
    st.i = i;
    const step = st.steps[i], n = st.steps.length;
    st.tip.innerHTML = `<div class="step">${i + 1} of ${n}</div><h3 id="tour-title">${esc(step.title)}</h3><p>${esc(step.text)}</p>
      <div class="row"><button type="button" class="skip">${i === n - 1 ? "" : "Skip tour"}</button><span class="sp"></span>
      ${i > 0 ? '<button type="button" class="back">Back</button>' : ""}<button type="button" class="next">${i === n - 1 ? "Got it" : "Next"}</button></div>`;
    const skip = st.tip.querySelector(".skip");
    if (i === n - 1) skip.style.visibility = "hidden";
    skip.onclick = () => finish();
    st.tip.querySelector(".next").onclick = () => (i === n - 1 ? finish() : show(i + 1));
    const back = st.tip.querySelector(".back");
    if (back) back.onclick = () => show(i - 1);
    const target = el(step);
    if (target) target.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "center" });
    setTimeout(() => { place(); st && st.tip.querySelector(".next").focus({ preventScroll: true }); }, reduced() ? 0 : 380);
    place();
  }

  function finish() {
    if (!st) return;
    const { key, block, hole, tip, onKey, back } = st;
    [block, hole, tip].forEach(x => x.remove());
    removeEventListener("keydown", onKey, true); removeEventListener("resize", place); removeEventListener("scroll", place, true);
    st = null;
    try { fetch("/api/ui", { method: "POST", body: JSON.stringify({ key, value: true }) }); } catch (e) {}
    if (back) try { back.focus(); } catch (e) {}
  }

  function start(key, steps, opts = {}) {
    steps = steps.filter(s => el(s));
    if (!steps.length || st) return;
    if (!document.getElementById("tour-css")) { const s = document.createElement("style"); s.id = "tour-css"; s.textContent = CSS; document.head.appendChild(s); }
    const block = document.createElement("div"); block.className = "tour-block";
    const hole = document.createElement("div"); hole.className = "tour-hole";
    const tip = document.createElement("div"); tip.className = "tour-tip";
    tip.setAttribute("role", "dialog"); tip.setAttribute("aria-modal", "true"); tip.setAttribute("aria-labelledby", "tour-title");
    document.body.append(block, hole, tip);
    const onKey = (e) => {
      if (!st) return;
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); finish(); }
      else if (e.key === "ArrowRight") { e.preventDefault(); st.i < st.steps.length - 1 ? show(st.i + 1) : finish(); }
      else if (e.key === "ArrowLeft" && st.i > 0) { e.preventDefault(); show(st.i - 1); }
      else if (e.key === "Tab") {  // fokus ostaje u vodiču
        const f = [...tip.querySelectorAll("button")].filter(b => b.style.visibility !== "hidden");
        const k = f.indexOf(document.activeElement);
        e.preventDefault(); f[(k + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus();
      }
    };
    st = { key, steps, i: 0, block, hole, tip, onKey, back: opts.returnFocus || null };
    addEventListener("keydown", onKey, true); addEventListener("resize", place); addEventListener("scroll", place, true);
    show(0);
  }

  // Sam se pokrene prvi put; podaci sa servera (ne iz pregledača). Greška → bez vodiča, stranica radi normalno.
  async function auto(key, steps, delay = 700) {
    try {
      const r = await fetch("/api/ui");
      const seen = r.ok ? await r.json() : { [key]: true };
      if (!seen[key]) setTimeout(() => start(key, steps), delay);
    } catch (e) {}
  }

  window.CCCTour = { start, auto, finish };
})();
