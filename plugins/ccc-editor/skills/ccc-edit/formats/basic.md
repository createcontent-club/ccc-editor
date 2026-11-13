# Basic Edit

The CCC essentials for one talking-head video: tight cuts, a text hook, captions, camera zooms and clean audio.

**From Basic:** everything — the client chooses whether to have a text hook (and its text / style / position), caption style, font (captions + hook), brand color, pacing (fast / chill) and camera.
**Own elements:** none.

## Judgment

- **Stacked hook** (`hook_style=stack`): the text is shown as a big main line + a smaller brand-color line. If the client's text has no `|`, choose the split yourself at a natural point (main idea | supporting phrase) and save it: `ccc choices <name> hook_text="how to go viral | start growing, stop guessing"`. Both lines must fit one line each on screen — if the build says `NEMA MESTA`, save the text without `|` and the engine picks the natural split that fits.
- **Minimal captions** (`caption_style=minimal`): one key word per caption is bold. Run `ccc captions <name> --style minimal`, then `ccc keys <name>` and fix wrong picks with `ccc key <name> <caption number> <word>` (pick the word that carries the meaning — the noun, number or verb the sentence is about, never "the/is/you").

## Extra changes

| Client says | Do |
|---|---|
| "wrong bold word at 0:15" (Minimal) | `ccc keys <name>` → `ccc key <name> <n> <word>` |
