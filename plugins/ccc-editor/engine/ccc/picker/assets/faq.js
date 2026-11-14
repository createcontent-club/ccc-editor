/* CCC FAQ (PLAN §14, faza 4): mali prozor sa najčešćim pitanjima, isti na obe stranice. Pitanja su u
   /assets/help.json ("faq"). Pitanje se otvara klikom (details/summary, radi i tastaturom i čitačem ekrana);
   prozor se zatvara na ✕, klik van njega ili Esc, a fokus se vraća na dugme koje ga je otvorilo. */
(function () {
  const CSS = `
  .faq-back { position: fixed; inset: 0; z-index: 900; background: rgba(0,0,0,.7); display: grid; place-items: center; padding: 16px; }
  .faq-box { width: min(620px, 100%); max-height: min(80vh, 760px); overflow: auto; background: #0B0F18; border: 1px solid rgba(0,102,255,.45);
    border-radius: 18px; padding: 22px 22px 12px; color: #fff; box-shadow: 0 24px 70px rgba(0,0,0,.7); position: relative;
    font: 400 14.5px/1.55 "Inter", system-ui, sans-serif; }
  .faq-box h2 { margin: 0 40px 14px 0; font: 800 20px/1.25 "Montserrat", "Inter", sans-serif; }
  .faq-box details { border-top: 1px solid rgba(255,255,255,.08); }
  .faq-box summary { cursor: pointer; list-style: none; padding: 14px 30px 14px 0; font: 700 15px/1.35 "Inter", sans-serif; position: relative; }
  .faq-box summary::-webkit-details-marker { display: none; }
  .faq-box summary::after { content: "+"; position: absolute; right: 4px; top: 11px; color: #3D8BFF; font: 700 20px/1 "Inter", sans-serif; }
  .faq-box details[open] summary::after { content: "−"; }
  .faq-box summary:focus-visible { outline: 3px solid #3D8BFF; outline-offset: 2px; border-radius: 6px; }
  .faq-box details p { margin: 0 0 14px; color: #C9D2E4; }
  .faq-box .x { position: absolute; top: 14px; right: 14px; width: 32px; height: 32px; border-radius: 9px; border: 1px solid rgba(255,255,255,.12);
    background: transparent; color: #8C95A8; font: 700 16px/1 "Inter", sans-serif; cursor: pointer; padding: 0; box-shadow: none; }
  .faq-box .x:hover, .faq-box .x:focus-visible { color: #fff; border-color: rgba(0,102,255,.6); outline: none; transform: none; box-shadow: none; }`;
  let open = null;
  const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function close() {
    if (!open) return;
    const { back, from, onKey } = open;
    back.remove(); removeEventListener("keydown", onKey, true); open = null;
    if (from) try { from.focus(); } catch (e) {}
  }

  async function show(from) {
    if (open) return;
    let faq = [];
    try { const r = await fetch("/assets/help.json"); if (r.ok) faq = (await r.json()).faq || []; } catch (e) {}
    if (!faq.length) return;
    if (!document.getElementById("faq-css")) { const s = document.createElement("style"); s.id = "faq-css"; s.textContent = CSS; document.head.appendChild(s); }
    const back = document.createElement("div");
    back.className = "faq-back";
    back.innerHTML = `<div class="faq-box" role="dialog" aria-modal="true" aria-labelledby="faq-title">
      <button type="button" class="x" aria-label="Close questions">✕</button>
      <h2 id="faq-title">Questions people ask</h2>
      ${faq.map(f => `<details><summary>${esc(f.q)}</summary><p>${esc(f.a)}</p></details>`).join("")}</div>`;
    back.addEventListener("click", (e) => { if (e.target === back) close(); });
    back.querySelector(".x").onclick = close;
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
      else if (e.key === "Tab") {  // fokus ostaje u prozoru
        const f = [...back.querySelectorAll("button, summary")];
        const k = f.indexOf(document.activeElement);
        e.preventDefault(); f[(k + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus();
      }
    };
    addEventListener("keydown", onKey, true);
    document.body.appendChild(back);
    open = { back, from, onKey };
    back.querySelector("summary").focus();
  }

  window.CCCFaq = { show, close };
})();
