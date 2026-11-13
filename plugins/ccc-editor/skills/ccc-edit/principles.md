# CCC editing principles — every format

These are how CCC thinks about visuals, learned from the owner's storyboard reviews. They apply to **every format that
shows animated or real visuals** (Split Screen today, every future format). A format file (`formats/<id>.md`) only adds
its own layout and exceptions. Read this file before planning any visuals.

Each principle: the rule, then **Why** (the thinking behind it), then where the engine checks it (`!` lines in
`ccc visuals` / the build check — fix every `[must]`; `[aim]` lines get at most 2 plan revisions, see SKILL.md Step 4).

## Timing — the ONE table (every other mention of seconds points here)

| What | Rule |
|---|---|
| One look (layout) on screen | 3–5 s, then the presentation changes (same people/idea may continue — principle 37) |
| New beat (a value, a line, a tag, a new card) | at least every ~3 s; never more than 5 s without anything new |
| A single moment | at least 1.2 s; every element stays long enough to read (the engine prints `[must]` when it doesn't) |
| Real video clip (subject footage, interview, ad) | may run up to 8 s on its own — it moves by itself |
| Client's own screen recording | may run up to 15 s |
| The hook | one IDEA for the whole first claim (often ~10 s), built as 2–3 consecutive moments that keep the same subjects (principles 30–34) |
| Clip downloads | ≤ 20 s each, only the part you will show |

## Meaning first — show the idea, not a picture of something related

1. **Dramatize what is said, literally.** Turn the speaker's metaphor or claim into its own little scene: "you use
   Claude like a search engine and waste 90% of its power" → a search bar with Claude's logo where a query gets typed,
   then a power meter: 10% used, 90% wasted in red, counting up on "90%" (`search` + `meter`).
   **Why:** the viewer must understand the sentence with the sound off; a related picture (a homepage, a stock image)
   adds nothing.
2. **A screenshot only when the page itself is the subject** — an article, a post, a launch page, a review the speaker
   is talking about, with the spoken words highlighted on it. Never a screenshot as decoration or as "proof the
   product exists", and never a screenshot squeezed next to text. Otherwise: logo + custom animation.
   **Why:** a random page gives no context; the eye searches it for meaning and finds none. *Engine:* screenshot whose
   highlighted text isn't what's said; screenshot used as media next to text.
3. **Every tool, platform or brand named in the hook is visibly in the hook** — its whole logo, clearly, in the
   opening animation (inside the recreated UI, a tile, a hub). *Engine:* hook mentions X without X's logo.
4. **"X does A, B and C" → X connects to A, B, C.** The actor (logo) on top, the things it does below, a line drawn to
   each on its word (`flow` `layout: "hub"`, first node = the logo `file`, no label).
   **Why:** it shows the relationship (one tool → many jobs), not three separate facts.
5. **Abstract concepts get a shape, never a lone word.** "Self-improving loop" → the system's parts connected in a
   closed loop with the dots circling and the name in the middle (`flow` `quad` + `loop` + `center`). A single word
   never stands alone in its own line (the `key` template merges it into the title).

12. **Asset fitness test — before using any real asset, ask: "with the sound off, does THIS picture explain THIS
    sentence better than a custom animation would?"** A found screenshot, photo or page that only *relates* to the
    sentence fails → build the custom animation instead (with the real logo inside it). Finding an asset is not a
    reason to use it. **The hook never uses a screenshot** — it is too static for the first seconds; the hook is real
    footage of the subject or a custom animation that dramatizes the sentence.
    *Engine:* hook is a screenshot / static page.

## Frameworks — announce once, reuse everywhere

6. **When the video announces a number of things ("4 files", "3 steps", "5 mistakes"), show it as a framework the
   moment it's announced:** N tiles with icons, content hidden ("?"), so the viewer sees the shape of what's coming
   without spoilers. A total that belongs to all of them ("took 20 minutes") joins them: tiles slide down, a bracket
   connects them, the value appears above (`steps` `active: -1` + `total`).
7. **The same framework returns for EVERY item, through the whole video** (`steps` `active: 0…n-1`), and again at
   the end when all of them are delivered (`active: n` — all revealed, e.g. "a template with all four files").
   Never cover 2 of 4 steps and switch to something else for the rest.
   **Why:** continuity — the viewer always knows where they are; a framework used halfway reads as an accident.
   *Engine:* framework covers k of N steps.

## Brand assets

8. **Logos are never cropped.** Whole, inside the neon tile or alone with a gentle float — never as a photo filling a
   frame (`cover` crops it). The engine renders logo files (`web-logo-*`, transparent PNGs) whole automatically.

## Layout and design

9. **Respect the safe zone and proximity.** Nothing touches the edges of the safe zone; related elements sit close
   together (a comparison's two cards are a pair, not two islands). Connectors (arrows, lines) are *created* over the
   elements they connect, overlapping them, on the beat — not a small symbol floating in a gap.
10. **Every mark must read as intended.** A line, stroke or shape that can be mistaken for a glitch (a strike-through
    passing between two lines of text) is worse than no mark — show "old/bad" with dimming, desaturation and the red ✗.

13. **Always breathing room between elements.** No element is ever pushed against another (a value pill touching a
    title, a label touching a line): keep at least ~40 px between separate elements and let the layout move to make
    room when something new arrives — alignment comes from consistent gaps, never from squeezing.
14. **The drawn highlight is only for text that stands alone with room around it** (a headline, a news title being
    read along). Inside diagrams, flows, cards and lists there is no drawn highlight — emphasis there comes from
    weight, color and focus (dimming the rest). Templates follow this automatically.

## Calls to action

11. **CTA moments get the most care.** When the speaker offers something (a template, a guide, a checklist, a free
    resource), show *that resource* as a custom visual — ideally the video's own framework delivered complete (all
    items revealed). "Comment KEYWORD" is a native Instagram comment: the keyword typed into "Add a comment…", posted
    as a normal comment, a heart, then the creator's reply (`comment` `platform: "instagram"` `typing: true`) —
    prominent through the size of the whole card, never plain text that can be missed (see 29: native proportions). *Engine:* "comment …" spoken without a comment visual.

## Real subject — fill the video with the real thing (review ai-actor-0 v1)

15. **A video about a concrete person, product or event is filled with REAL visuals of it, as much as possible.**
    Find several different photos/clips of the subject — one for each moment being described (her daily posts, her
    role, the ad, the backlash) — not one or two photos repeated. A template only for what is truly abstract.
    **Why:** the viewer came for that person/thing; animations about a real subject feel like filler and lower trust.
    *Engine:* real material in < 50% of moments; a person/character subject shown in < 4 different pictures.
16. **Concrete claims and numbers are proven, never drawn.** "400,000 followers", "$38,000 per ad" → the source that
    says it (article, profile, report) as a screenshot with that exact figure marked on the word. Custom stat/chart
    cards only for general numbers that have no source to show. **Why:** proof makes the video credible; a custom
    counter of a real claim looks invented. *Engine:* number in a stat/notify/checklist/… while the speaker says it in a
    video with a concrete subject.
17. **On a screenshot, mark exactly what is being said.** When a larger piece of text stays on screen (a headline,
    a paragraph), the figure or name the speaker says gets a marker in the brand color on that word — and the camera
    ends its ONE move with the marked text **in the middle of the frame and big** (a line of text ~70 px), never
    drifting to a corner or staying small. A light article page with marks is shown full-view (not in a small browser
    window) so the camera can come close. *Engine:* long highlighted part without marks; template centers all marks
    together, in the window or full-view alike.

## Never broken framing (review ai-actor-0 v1)

18. **A face inside a shape is centered on the face** — horizontally in the middle, eyes a little above the middle
    (automatic from face detection). **A picture is never cropped into a shape it doesn't fit:** a wide picture, a
    collage or a two-shot goes full-width (spotlight / photo / image) — choose the animation FROM the picture you
    found, not the picture for a planned animation. *Engine:* mediatext with a wide image without a face or with 2+
    faces → error.
19. **Never an empty frame.** Something is on screen from the first frame of every scene: a card with its label enters
    at once and the number counts up on its word; a list or flow starts at the moment's first word. *Engine:* first
    element later than 0.7 s → warning; `stat` template shows the card immediately.
20. **Long picture scenes change pictures.** A mediatext/photo scene longer than ~5 s swaps 2–3 pictures inside the
    same shape on the words (`more: [{file, at}]`), so one image never stands for 8 seconds. *Engine:* warning.
21. **A reveal is shown on the subject itself.** "And she doesn't exist" → her photo glitches and fades to a ghost on
    the word (`spotlight` `fx: {type: "vanish", at}` + short title), not a text card.
22. **The CTA arrives exactly on its word.** The comment visual enters on "comment"; the offer before it (a report, a
    template) gets its own dynamic visual that leads into it. *Engine:* comment moment starting > 0.6 s before the word.
23. **Every cut is clean.** No visible pause, restart, laugh or wrong word left in the edit — after the editorial pass,
    look at every kept line around a retake (the frames and the words) and cut what doesn't belong.

## Precise framing and native look (review ai-actor-0 v2)

24. **Positions are measured against the SHAPE, not the screen.** The shape (frame, card, panel) is always centered
    in its area; the picture inside is cropped so the subject (the face) sits in the middle of the shape. A picture
    that already contains a frame — a portrait in the middle with blurred or flat side bars (screenshots of vertical
    videos, magazine embeds) — is first cut to its real frame, so the blurred sides never count as content.
    *Engine:* `assets.inner_panel` cuts the real frame when preparing every photo; `facePos` centers the face in the shape.
25. **Big overlay text sits low, just above the captions** (spotlight title), never in the upper part of the top half —
    safe zones of the platforms. *Template.*
26. **A picture that doesn't fit the full top half is shown whole, smaller, on a clean background** — never cropped
    to fill (full-bleed only when ≤ 12 % would be cut). Photos in a frame have no browser bar. *Template* (`picPlan`).
27. **Emphasis uses only the brand color — or red for bad/risk.** Never a third color (yellow/orange) for highlights,
    lines or tags. *Template:* `tone: "warn"` is drawn in the brand color.
28. **The CTA follows the words with visuals of the offer itself.** "Want to see China's top 25 companies? Comment …"
    → the report as an object (`resource`: pages enter, title on its word, rows fill, "FREE REPORT" badge), then the
    comment on "comment". A random template (a dot grid) next to a CTA is wrong.
29. **Native UI keeps native proportions.** An Instagram comment looks like the app: username + time, the comment in
    regular text, "Reply", the heart — clean and professional. The whole card is big enough to read; the keyword is
    not blown up.

## The hook — how to decide what goes in it (review aazar-trial-1 v1 + the owner's own answers, 13 Nov 2026)

The hook is not "the first scene". It is the first CLAIM of the video shown as one connected visual. Decide it in this
order, every time, before planning anything else:

30. **First: WHO or WHAT is this video about? Show exactly that, recognizably, from the first frame.** The faces,
    the products, the brands the video is about — the thing a viewer recognizes at a glance and that tells them what
    the video will be about. That is what stops the scroll, not speed.
    **Why (owner):** "it doesn't have to be crazy dynamic — just present what will catch the viewer's attention and
    hints at what the video will talk about." Two logo tiles were "too slow and didn't show what's adequate" because a
    logo alone doesn't say who is fighting; the founders' faces do. *Engine:* first moment without a real picture of the
    subject while research.json has one → warning.
31. **Is the video a comparison / a conflict ("X vs Y", "A did this, B did that")? Then BOTH sides are in frame at the
    same time, for the whole comparison — and the animation happens ON them** (`faceoff`: two cards side by side, VS
    in the middle, each side's numbers land on their word, the losing side in red and slightly muted). Never one side,
    then the other in a separate shot; never the two sides as separate scenes.
    **Why (owner, s03):** "they are compared the whole time, which by itself says both have to be in frame at the same
    time, and then animate what is being talked about." *Engine:* the first claim says "vs"/names two subjects that
    research has pictures of, and the opening isn't a two-sided visual → warning.
32. **The hook lasts until the first claim is complete, as ONE idea** — here "Beauty Wars … Rare did 4.2M while
    Kylie only did 740K" (~10 s), and it keeps going while the next sentences are still about the same comparison
    ("you might think Selena has a smaller audience… wrong, 430M vs 390M"). The same subjects stay on screen the
    whole time, but the look changes every 3–5 s (principle 37 and the timing table): faces face-off → their
    revenue as pillars → the question on their faces → follower pillars.
    **Why:** the opening sets up the question the video answers; cutting it into 3-second scenes breaks the setup and
    makes the opening look like scenes from the middle.
33. **Numbers of the first claim live on the subject they belong to** — Rare's revenue under Selena/Rare, Kylie's under
    Kylie — never as a separate stat card next to a picture of something else.
34. **Calm is fine; empty or abstract is not.** The hook may be still and simple (slow zoom, gentle float, values
    counting up) as long as the subject is big and clear. A plain headline, an icon, a screenshot or a lone logo is
    never the hook when the real subject exists (principles 3, 12).
35. **The speaker reading the script aloud is not content.** A title or outline read out to remind himself ("Kylie
    Cosmetics vs Rare Beauty" right after the hook line, said flatly, not to the viewer) is cut as `off-script` in the
    editorial pass — check every line in the first ~15 s against: is he telling the viewer something, or reading?

## Recreate the process — custom animation over templates (review aazar-trial-1 v3 + the owner's answers)

36. **When the speaker explains something the viewer has to IMAGINE, recreate that process as a full-screen custom
    animation (`scene`)** — the top half becomes the stage and the things being described act it out on their words:
    "running the same ad with 10 different versions, recycled over and over" → one real ad in the middle, it multiplies
    into 10 copies, the copies cycle around a recycle loop, "just pushing the product" lands as a tag. The actors are
    the REAL assets (the actual ad, product, logo, face); graphics only where no real asset exists.
    **Why (owner):** "a custom card that says one ad is duplicated 10 times means nothing to them — you catch attention
    by recreating the process being explained. Use the template cards as little as possible: custom animations that
    show something happening all the time, combined with the main assets. Templates only when there is literally no
    other solution, or for something abstract that isn't worth explaining in a custom animation."
    *Engine:* a moment with a template card while the sentence describes an action on concrete things → warning.
37. **One presentation stays on screen 3–5 s at most** — the idea and the people may continue (keep following the two
    founders), but the way the information is shown changes: faces face-off → their revenue as pillars → the question
    on their faces → follower pillars that turn into revenue pillars. Real video clips may run longer (they move on
    their own), up to ~6–8 s. This refines 32: the hook is one continuous IDEA, not one frozen layout.
    **Why (owner, s01):** "20 seconds of the same scene must never happen; after 3–5 seconds it has to change."
    *Engine:* non-clip moment longer than 5 s, or a moment whose last new beat is > 5 s before its end → warning.
38. **Numbers of two compared subjects → pillars with each subject's face on top of its own bar** (`pillars`), so the
    viewer sees whose bar is whose and the gap itself ("6x") — never a lone "6x" stat card.
    **Why (owner, s02/s27):** "two pillar charts with their pictures on top of each, so it's clear which chart belongs
    to whom."
39. **A concrete thing that is mentioned is shown with the real thing** — a type of ad ("before and after with reviews
    layered on top"), an offer ("free shipping over $40"), a fact ("it's sold out") — the actual ad, page or article,
    with animation only if it adds something. Extends 15–16 to ad formats, offers and features, not only people.
40. **A connector only connects things that are both on screen.** An arrow from left to right needs the left thing
    visible from the start; never an arrow, line or "→" pointing from empty space.
    **Why (owner, s14):** "it makes no sense that the arrow points from left to right while there is no visual on the
    left from the start."
41. **Never two similar-looking animations back to back** — not only the same template: two lists (checklist then
    notify), two card stacks, two number cards in a row read as the same thing and the viewer scrolls away.
    *Engine:* consecutive moments from the same visual family → warning.
42. **The people the video is about stay visible through the whole video**, not only in the opening — in every
    comparison and wherever the speaker describes what they do (real clips of Selena making content, telling her
    founder story, showing before/after).
    **Why (owner, s24):** "the two of them are missing a lot in the video, since the whole topic is about them."
43. **CTA: show the content of what is being sent right away** — at the first words of the CTA the resource opens and
    its real contents are visible (sections, pages, the framework of the video delivered), so the viewer waits to hear
    how to get it. That keeps them watching to the end.
    **Why (owner, s28):** "show the data of the document right away so people wait to hear what they need to do to get
    it — which increases watch time."

44. **What is already on screen never resets when something new arrives.** When the next value, set or line
    lands, only the thing that CHANGED animates; everything that stays the same (a number already counted up, a label,
    a face, a bar height) stays exactly as it was — no recount from zero, no fade-out/fade-in, no jump.
    **Why (owner, v4 s02):** "when Kylie's counter appeared, the counter above Selena that was already in frame reset —
    a random error." It reads as a glitch and breaks trust in the whole graphic. *Template:* `pillars` keeps unchanged
    values and labels still; new templates must follow the same rule (test: render a frame just after the second beat).
