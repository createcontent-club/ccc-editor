# Split Screen

You and what you're talking about, on screen at once: the screen is split 50/50 — visuals on top, the client (their talking-head video) below.

**From Basic:** text hook Yes/No and its 4 styles, 4 caption styles, 4 fonts, brand color, Fast/Chill pacing — the client chooses them like in Basic.
**Set by this format (locked):** the hook sits on the split line for the first ~3 seconds, then the captions appear in the same spot (no hook → captions from the start); the camera is always static (no zoom).
**Own elements:** the 50/50 layout (the engine crops the client's video into the bottom half); the **top half** — Dark or Light style (`top_style`), filled with "moments" you plan from the transcript (below).

## Top half — real assets first (research, before the visual plan)

**Hierarchy — for every moment take the FIRST level that has good material:**
0. the client's own file (dashboard / chat) → 1. a link the client gave → 2. **a real asset from the internet** (logo, news headline, website/app screenshot, product photo, short video clip) → 3. native platform recreation (Instagram DM/comment…) → 4. real numbers as stat/chart → 5. custom animated template (flow, versus, steps…) → 6. kinetic headline.
Real assets always beat custom animations when the speaker talks about something concrete that exists (a company, product, app, website, person in the public eye, news, event, study). Custom animations fill everything else.

**The client's choice (dashboard → `choices.json`):** `web` (true = "Find real visuals online", the default; false = "Animated visuals only") and `links` (pages the client says they mention). `ccc research <name>` prints both.
- **Links first (level 1), always — even with `web: false`.** For each link: open it (WebFetch), find the word ids where the client talks about it, and download the right asset from that exact URL (`ccc shot <link> --find "<headline>"`, an X/Twitter status link → the embed URL with the same id, `ccc fetch` for an image link, `ccc clip` for a video). A link that matches nothing in the transcript: don't force it — say so in one sentence in the summary.
- **`web: false`** → no searching and no other downloads (the engine refuses them and the check fails): only the client's links, their files and the animated templates (levels 0, 1, 3–6).
- **`web: true`** → the full research step below.

**Research step** (after the editorial pass, only with `web: true`):
1. Read the kept transcript and list every concrete entity with the word ids where it's mentioned: brands/companies, products/apps, websites, public figures, news/events (with date), studies/numbers. Decide the ideal asset for each (logo / headline / screenshot / photo / clip). Write `work/<name>/research.json`:
   `{"entities": [{"name": "Instagram", "type": "brand", "words": ["w13"], "want": "logo", "status": "found", "assets": ["web-logo-instagram.png"]}]}` (status: found / not found / skipped).
2. Find sources with WebSearch / WebFetch, then download with the engine (every file gets its source recorded — never save web files any other way):
   - **Logo:** `ccc logo <name> "<Brand>" --domain brand.com` → look at the candidates sheet (Read the path) → `ccc fetch <name> <url> --for <wID> --as logo-<brand>`. Prefer the official, current, full-color logo (Wikimedia's "… logo 2022.svg" style or the site's own); never a random site. The sheet can contain look-alikes — pick the logo of exactly that brand (Meta ≠ Meta AI, Notion ≠ Notion Press), the current one (X, not the Twitter bird; candidates marked ⚠ are old/parody/"prohibited" versions), compare with the brand's own site when unsure. "nema nijednog kandidata" → a flow node with an icon + the name, or a screenshot of their site.
   - **News / article / website / app page:** `ccc shot <name> <url> --for <wID> --find "<exact headline or phrase on the page>"` (add `--mobile` for a phone layout). It closes cookie banners and finds the phrase; use a distinctive phrase (the headline), not a single word. Prefer the publisher's/brand's own page. The engine refuses walls — `Nije sačuvano: …` for a bot/captcha check, 404, paywall, login wall or HTTP error (preview in `_candidates/`); only if you looked at the preview and it's actually fine, repeat with `--keep`. Known from the stress test: NYT, WSJ, G2 and Instagram profiles are walled for automated visits; BBC, Guardian, Spiegel, Le Monde, Wikipedia, Reddit, LinkedIn company pages and X profiles work. For a walled news site: the same story from another outlet, or a `news` card with the real headline (find it with WebSearch), the outlet's logo and date. `nije nađen` for `--find` → the shot is kept without a focus; `--crop` with a missing element fails (post deleted/private).
   - **Photo / image:** `ccc fetch <name> <image-url> --for <wID>` — official/press images or Wikimedia Commons; no watermarked stock (Getty, Shutterstock), no private people. Photos of people: only public figures in their public role (CEO, creator, politician), a current, flattering, sharp portrait.
   - **A real post the speaker quotes or refers to** (a tweet, a Reddit thread, a LinkedIn post): find the actual post. X/Twitter: `ccc shot <name> "https://platform.twitter.com/embed/Tweet.html?id=<id>&theme=dark" --selector article --crop --for <wID>` — gives just the post card on a transparent background. Other sites: `ccc shot … --selector "<post element>" --crop` if the page allows it; otherwise recreate it natively with a `post` card using the post's exact text, author and numbers.
   - **A number from a study/report:** find the original source; put the number in a `stat`/`chart` and the source in `"source"` (never shown on screen — it goes to the report). If the speaker's number differs from the source, use the speaker's words and mention it in the report.
   - **Video clip:** `ccc clip <name> <url> --for <wID> --from <s> --to <s>` (≤ 20 s, the part that matters; YouTube, news sites, reels work).
3. **Look at every downloaded file** (Read it) before using it: correct entity, current (date fits), sharp enough, no watermark, readable on a phone. If it fails, try the next source, then go one level down the hierarchy.
4. Budget per video: about 15 searches, 25 downloads, 4 minutes. Hero opening and the main claims first.
5. `ccc research <name>` shows the entity list and everything downloaded with sources.
6. Never show source labels on screen. The final report lists every real visual with its source automatically (from the recorded sources and `source` fields) — read it out to the client in the summary.

**Real-asset kinds:**
- `logo` — `file` (+ `name`, `sub`) for one brand on a light plate; or `logos: [{file, name, at}]` for a row (comparison / list). A `flow` node can also show a real logo: `{"file": "web-logo-x.png", "label": "X", "at": …}`.
- `screenshot` — `file` from `ccc shot`; the engine already knows where the `--find` phrase is (`focus`), so usually just add `"highlight": {"at": "<wID>"}` — the camera eases in to that part and a highlight box draws on that word while the rest dims. Optional `focus {x,y,w,h}` / `highlight {x,y,w,h,at}` in image pixels, `device: "phone"`.
- `news` — `headline` (exact), `outlet`, `date`, `logo` (outlet logo file), optional `image` (article image file; a face in it is kept in frame), `highlight: [{"text": "words from the headline", "at": wID}]` — highlighted when said. Long headlines need reading time (~3.5 words/s; the engine warns `ima N reči … treba ~Xs`): give the moment that time, or keep the real headline's main clause and end it with "…".
- `photo` — a real person / product / place: `file`, `name` (e.g. "Adam Mosseri"), `sub` (role, e.g. "Head of Instagram"), optional `at` for the name tag. A portrait whose face fits the safe zone fills the whole top half with a glass name tag; otherwise it shows in a frame with the name under it.
- `post` — a social post: `platform` (`x` | `reddit` | `linkedin` | `threads`), `text` (exact), `name`, `handle`, `avatar` (file), `time`, `verified`, `likes`/`comments`/`reposts`/`views`, Reddit `community` + `title`, LinkedIn `headline`; `highlight: [{"text": "exact words from the post", "at": wID}]` — marked as the speaker reads them (read-along). Or `file` = a real post screenshot from `ccc shot … --crop` (shown as a floating native card). **Never invent a post and attribute it to a real person or brand** — a native `post` only recreates a real post the speaker quotes, with its real text; for a hypothetical example use a generic name ("a founder", handle like `@yourclient`), never a real account.
- `image` / `video` work for downloaded web files too.
- `stat` / `chart` with numbers from a source: add `"source": "Hootsuite Digital Report 2026"` (report only, never on screen).

**How pictures are shown (automatic — know it when planning):** an image or screenshot fills the WHOLE top half (no window) whenever the highlighted part can sit in the middle of the safe zone without touching an edge or being cut; a picture with a one-color edge (phone screenshots, white websites) blends into a top-half background of that color so any part can be zoomed; only otherwise it gets a browser/phone window. The camera always zooms in a straight, smooth line to the highlighted part, and the highlight is a flat cut-out: that part stays full, the rest fades into the background color. So choose `--find` phrases that are the exact thing being talked about — that's where the camera goes. Camera timing fits the scene: the move is quick (0.7–1.2 s) and the last ~35% of the scene (0.9–1.6 s) is still so people can read it — give every screenshot moment at least 1.8 s and let the highlighted word come at least 1.2 s before the moment ends (the engine warns otherwise). Real logos always sit in the same dark neon tile as icons.

## Top half — the visual plan (your job, after the research, before `ccc build`)

**Editing psychology — follow it strictly (these come from CCC's own reviews):**
1. **Hero opening.** The first moment (while the text hook is on screen) is the richest, biggest visual of the video and follows the words 1:1 — a `flow`, `versus`, `chart`, `filter` or `week`, never a plain `headline`/`key`/`stat`.
2. **Something new every 1.5–3 s.** A moment lasts 1.2–4 s; about one per phrase.
3. **Show, don't repeat.** The visual explains or dramatizes what's said (process, comparison, filter, growth, time, checklist, chat) — never just the caption again. `headline` only for abstract punch lines.
4. **Every graphic must be readable without sound.** No bar, line or number without its meaning: give scales (`of`), axis labels (`y`, `x`), and the takeaway (`note`). If you can't explain a number visually, don't draw a bar.
5. **Sync every part to its word** with `"at": "<word id>"` — including secondary labels (`sub`, `note`, chart values). Nothing appears before it's said; the first part appears immediately.
6. **No lone fragments.** Never let a single filler word ("Your", "The", "So") stand alone — the first chunk on screen must carry meaning by itself (e.g. "Your lead magnet", not "Your" … "lead magnet"). If the meaningful word comes later, start the moment later.
7. **Never reveal what's coming.** Steps: one `steps` moment per step; the card shows the full shape with the text hidden until it's said. Lists/checklists/chats only show items that were said.
8. **Enter at the start of the phrase that introduces it** — `at` = the first word of that phrase ("**has** to work", "**your** ICP"), never its last word. Late entries force rushed animation.
9. **Time to process.** Every element must stay long enough to be read and for its animation to finish (the engine prints `'…' je na ekranu Xs, a treba bar Ys` — fix every such line: enter earlier, or end the moment later).
10. **No redundant beats.** If the next visual carries the same idea ("views" → a Views-vs card), don't show it as text first — start that visual on that word.
11. **Color psychology.** Bad / risk / loss → `"tone": "bad"` (red); warning → `"tone": "warn"` (amber); good → default brand color. Use it on headline highlights, checklist items (bad = red ✗), notifications, stat subs and chart notes (a declining chart is red automatically).
12. **Native to the platform.** When a visual recreates a real app (DMs, comments), use `"platform": "instagram"` so the design and colors say Instagram without any logo (not the brand glass style).
13. **Light sweep is an accent, not a default.** The engine puts it on the opening and on a few payoff moments, at least 12 s apart, only on the main card. To force it on a special moment add `"sweep": true` to that item (still spaced); `"sweep": false` turns it off.
14. **Focus control** happens automatically: in lists, flows and chats the earlier items dim when a new one arrives — so plan lists in the order they're spoken.
15. Use the client's exact words and numbers; never invent facts or numbers.

The templates already handle the rest automatically: every visual is sized to fill the safe zone, groups re-center smoothly as parts are added, lists grow downward in reading order, lone headline text gets a highlight that draws under the accent word, and the background stays subtle.

Read the kept transcript (`ccc transcript <name>`, ignore removed lines; word ids are in `work/<name>/project.json` → `words`) and write a plan file, then save it:

```
ccc visuals <name> --set <plan.json>     → prints every moment with times and beat times, plus any problem (! lines)
```

```json
{"items": [
  {"from": "w9",   "kind": "flow",     "data": {"nodes": [{"icon": "instagram", "label": "Instagram", "at": "w13"}, {"icon": "crown", "label": "High-ticket offer", "at": "w17"}]}},
  {"from": "w38",  "kind": "stat",     "data": {"label": "on content, per week", "value": "3–4 hrs", "sub": "MAX", "ring": 30}},
  {"from": "w99",  "kind": "versus",   "data": {"left": {"label": "Views"}, "right": {"label": "Right people", "at": "w107"}}},
  {"from": "w189", "kind": "steps",    "data": {"items": ["Top-of-funnel content", {"text": "Keyword CTA", "at": "w189"}, "AI comment filter"], "active": 1}},
  {"from": "w241", "kind": "filter",   "data": {"label": "Who's commenting?", "at": "w249", "sub": "only dream clients", "keep": 3}},
  {"from": "w253", "kind": "chat",     "data": {"title": "Setter DMs", "messages": [{"from": "them", "text": "AUDIT 🔥"}, {"from": "you", "text": "Here's your audit 👇", "at": "w257"}]}},
  {"from": "w315", "kind": "headline", "data": {"words": [{"text": "Free"}, {"text": "AI audit", "at": "w324"}], "accent": "AI audit"}}
]}
```

**Kinds** (short texts — labels ≤ 22 characters, headline words ≤ 14):
- `flow` — a process / cause → effect: 2–4 `nodes` `{icon, label, at}`, line draws to each node as it's said.
- `versus` — old way vs new way / wrong vs right: `left {label, sub}` gets crossed out, `right {label, sub, at}` glows with ✓.
- `steps` — the speaker's numbered points: 2–5 `items`, `active` = current step (0-based). One moment per step.
- `checklist` — qualities / requirements: `title`, `items` `{text, at, tone}` appear and tick one by one (`tone: "bad"` = red ✗).
- `filter` — selecting the right people from many: `label`, `at` (when the filter happens), `keep` (1–6), `sub`, `total` (12–28).
- `chart` — growth or decline: `bars` (2–7 numbers, the shape only unless the client said the numbers), `label` (what is measured), `y` (axis, e.g. "Engagement"), `x` (one short label per bar, e.g. ["Post 1", …]), `note` (`{text, at}` — the takeaway, e.g. "Audience burned out"), optional `value`.
- `stat` — a number the client says: `value` (counts up), `label`, `sub` (`{text, at}`), and only if there is a real scale: `of` (e.g. "of 168 h in a week") + `ring` (0–100 = the share).
- `week` — time per week/day: `value` ("3–4 hrs"), `label`, `per` ("≈30 min a day"), `days` (default 7), `sub` (`{text, at}`) — 7 day columns fill one by one, the total counts up.
- `chat` — DMs: `title` (the other person's username), `messages` `{from: "them"|"you", text, at}`, `platform: "instagram"` for a native Instagram DM look.
- `notify` — things piling up (calls, leads, followers, sales): `items` `{icon, title, body, at, tone}` (max 4), top to bottom.
- `comment` — one comment + reply: `text`, `user`, `reply`, `author`, `at` (when the reply appears), `platform: "instagram"` for the native look.
- `headline` — abstract punch line: `words` = meaningful chunks `{text, at}` (never a lone filler word), `accent` = the chunk that gets the drawn highlight, optional `sub` (`{text, at}`).
- `key` — fallback only: `icon`, `line1`, `line2`.
- `image` / `video` — the client's own file (see Client files below): `file`, optional `start` (video), optional `caption` (`{text, at}`, only if it adds information).

Icons: clock, calendar, chart, trending, money, users, user, message, mail, target, zap, rocket, check, x, eye, search, star, heart, bot, phone, camera, video, lock, gift, lightbulb, megaphone, filter, link, sparkles, trophy, instagram, send, file, bell, handshake, inbox, play, comment, crown, flame, ban, hourglass, shield.

**Client files (optional).** The client can drop screenshots, screen recordings or clips on the dashboard (with an optional note per file); they're listed in `choices.json → assets`. Before planning:

```
ccc assets <name>      → prepares every file and lists: name · image/video · size and shape (vertical / horizontal / square) · length · the client's note · preview path
```

- **Look at every preview** (Read the preview path — an image, or 4 frames with times for a video) so you know what is in each file.
- Place each file on the sentence it belongs to: the client's note first, then what the file shows, then the file name. A file replaces the auto visual for that moment (`kind: "image"` / `"video"`, `file` = the exact name from the list, optional `start` = second in the clip to start from). Everything without a file keeps auto visuals.
- An image stays ≥ 1.5 s; a video moment may be as long as the part of the clip you want (a long screen recording can cover a long stretch — it moves on its own). Short clips freeze on their last frame.
- Use every file once if it fits anywhere; if a file fits nowhere (or can't be used — the list shows `✗` with the reason), don't force it: tell the client in one sentence which file wasn't used and why.
- `caption` on a file only if it adds information the speech doesn't (e.g. a label on a screenshot) — never repeat the spoken words.
- `⚠ niska rezolucija` in the list: the file will show small (never stretched more than 2×). Use it only if it still makes sense small; otherwise tell the client it's too small and ask for a bigger version.
- Transparent PNGs (logos, cut-out objects) are shown without a frame, floating with a shadow — good for brand logos and product shots.
- Files sent later in chat: `ccc assets <name> --add "<path>" --note "<when>"`, then re-plan and build.

Then `ccc build <name>`. The check line `gornja polovina: …` must pass (whole video covered, every moment ≥ 1.2 s, every `at` inside its moment, files exist).

## Judgment

- Same as Basic for Stacked hooks and Minimal captions (see `formats/basic.md`).
- If the check line `split: … teme …` fails, the client's head sits too high or too low in their recording for the bottom half — tell them in one sentence and ask for a recording with a little space above the head.

## Extra changes

| Client says | Do |
|---|---|
| "show X at 0:20" / "change the visual about …" | edit the plan file → `ccc visuals <name> --set <plan.json>` → `ccc build <name>` |
| "make the top light / dark" | `ccc choices <name> top_style=light|dark` → build |
| "no internet stuff" / "only animations" | `ccc choices <name> web=off` → replace every `web-…` moment that isn't from their links with an animated one → build |
| "add real logos/screenshots" | `ccc choices <name> web=on` → research step → re-plan → build |
| "here's the link to the article I mention" | `ccc choices <name> links="<all their links, space-separated>"` (keep the old ones) → download from it → put it on the sentence → build |
| "don't show the news site / that photo" | remove or replace that moment (next level of the hierarchy) → build |
| "use a different photo of X" / "use my logo instead" | find another official/press source (or `ccc assets <name> --add` their file) → swap `file` in that moment → build |
| "where is this from?" | `ccc report <name>` — the "Real visuals used" list has every source |
| "use this screenshot when I talk about X" (file in chat) | `ccc assets <name> --add "<path>" --note "X"` → look at its preview → put it in the plan → build |
| "put the hook somewhere else" / "zoom please" | that's fixed in Split Screen — offer Basic Edit if they want those options |
