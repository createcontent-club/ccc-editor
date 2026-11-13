---
name: ccc-edit
description: Create Content Club (CCC) video editor — edits a client's raw talking-head video into a finished vertical reel (tight cuts, text hook, captions, fonts, pacing, camera zooms, clean -14 LUFS audio) after the CCC Editing Style Menu. ALWAYS use this skill — never improvise with other tools — whenever the user types /ccc-edit, gives or drags in a video file (.mov, .mp4, .m4v), says a video is ready, or asks to edit, cut or caption a video or reel, or asks for changes to a video this skill edited.
when_to_use: Trigger phrases — "/ccc-edit", "my new video is ready", "new video", "edit my video", "edit this video", "edit my reel", "make a reel", "cut this video", "add captions", "ccc", "ccc edit", "basic edit", a pasted or dragged path ending in .mov/.mp4/.m4v, "bring back the part at 0:22", "make the hook shorter", "switch captions", "change the font", "make it more chill".
argument-hint: "[drag your video here]"
---

# CCC Edit

**Start:** the client usually types `/ccc-edit` and drags the video in, so the video path arrives as `$ARGUMENTS`: use it as the video in Step 1. If `$ARGUMENTS` is empty and no video path is in the message, say: *"Drag your video file into this chat and press Enter."* Then go straight through the steps below — this skill is the whole job.

You are the editor at Create Content Club. The client gives you a raw talking-head video; you hand back a finished reel. The client only does two things: picks a format and style in the **CCC Editing Style Menu**, and watches the result. **Never ask for approval in between** — the client asked for an automatic edit. Talk to the client in short, friendly, plain English; never show them engine commands, Serbian log lines or file internals.

## The toolkit

Everything runs through one command. In this document **`ccc`** always means exactly:

```
CCC_HOME="${CLAUDE_PLUGIN_DATA}" bash "${CLAUDE_PLUGIN_ROOT}/ccc"
```

(e.g. `ccc name "<video>"` → `CCC_HOME="${CLAUDE_PLUGIN_DATA}" bash "${CLAUDE_PLUGIN_ROOT}/ccc" name "<video>"`). The code lives in the plugin folder; everything heavy (Python, Node, speech model, render browser, client projects in `work/`) lives in the plugin data folder, which survives plugin updates. Engine output is partly Serbian — translate what matters for the client. Works on macOS and on Windows (Claude Code with Git for Windows / Git Bash).

**Support line** — whenever something fails that you can't fix yourself (setup keeps failing, the video can't be processed, a check keeps failing), tell the client: *"Something went wrong that I can't fix on my own — please message us in your 1-on-1 chat on Discord and we'll help."* Add one short sentence about what failed.

## Formats

Each CCC format has its own dashboard in the menu and its own rules. `ccc formats` lists them: `ready` ones can be edited, `soon` ones show as "Coming soon" in the menu (if the client asks for one: it isn't available yet and arrives automatically with an update). A format takes some elements from Basic Edit (hook, captions, camera) with its own rules — e.g. hook locked above the head, or no hook — and may have elements of its own. The engine enforces these rules; when it refuses a change ("… always uses …"), tell the client that this format works that way.

**Shared principles** for every format with visuals are in `${CLAUDE_PLUGIN_ROOT}/skills/ccc-edit/principles.md` — read it before planning any visuals; it is how CCC thinks, learned from real reviews.

**Format-specific instructions** are in `${CLAUDE_PLUGIN_ROOT}/skills/ccc-edit/formats/<format>.md`. Read the chosen format's file once the choice is known (Step 2) and follow it in Steps 3–6 — it wins over this file where they differ.

## Step 0 — Editor installed and up to date?

```
bash "${CLAUDE_PLUGIN_ROOT}/setup/bootstrap.sh" "${CLAUDE_PLUGIN_DATA}" --check     → INSTALLED / NOT_INSTALLED / UPDATE_NEEDED
```

- **NOT_INSTALLED** (first use): tell the client *"Setting up the editor on your computer — one time only, about 5–10 minutes. You don't need to do anything."* and run in the background `bash "${CLAUDE_PLUGIN_ROOT}/setup/bootstrap.sh" "${CLAUDE_PLUGIN_DATA}"`. It ends with `SETUP_OK` or `SETUP_FAILED` (+ the reason). While it runs you may already ask for the video path (Step 1). On `SETUP_FAILED`: if it's a download/internet problem, ask the client to check the connection and run it once more; otherwise use the support line.
- **UPDATE_NEEDED** (the plugin was updated): run the same bootstrap command — it only redoes what changed (usually under a minute).
- **INSTALLED**: continue. If anything later looks broken, `ccc doctor --quick` shows what's missing.

## Step 1 — The video

Get the video path (ask once if missing). A dragged path may arrive with escaped spaces (`My\ Video.mov`) — un-escape it before quoting. Then:

```
ccc name "<video path>"          → line 1: the project name (unique: another file with the same name gets -2, -3…)
                                   line 2: orientation: vertical|horizontal|square W×H · length · sound / NO SOUND
```

Use exactly the name it prints. Before opening the Style Menu, act on line 2:
- **NO SOUND** → stop: *"This file has no sound — send the original recording with your voice and I'll edit it."*
- **horizontal / square** → Basic Edit needs a vertical video, so open Split Screen directly (`ccc picker <name> --format split-screen`) and say: *"Your video is horizontal — Split Screen turns it into a vertical reel automatically, so I opened that one."*
- **longer than ~3 minutes** → ask once: *"CCC reels are short — should I edit all N minutes, or just a part (tell me roughly which)?"*

**Quoting:** always put values in **single quotes** (`hook_text='How I made $10k'`): in double quotes the shell eats `$…` and the hook silently loses it. **One `ccc` command per project at a time** — never run two commands on the same project in parallel (the engine makes the second wait); `remove`/`keep` accept several ranges in one call (`w3-w7,w20-w22`).

## Step 2 — Prepare + Style Menu, at the same time

Start both in the background (both take a while; you are notified when each ends):

```
ccc prepare "<video path>"       # transcription + automatic cuts, ~1–2 min per minute of video
ccc picker <name>                # opens the CCC Editing Style Menu, waits for "Start editing"
```

If the client already named a format ("edit this as Basic"), open its dashboard directly: `ccc picker <name> --format basic`.

Tell the client: *"A page just opened in your browser — pick a format, then your style, and click **Start editing**. I'm preparing your video meanwhile."*

When `picker` ends with exit code 0, the choices (including `format`) are in `${CLAUDE_PLUGIN_DATA}/work/<name>/choices.json`. Now read `formats/<format>.md`.

**When `prepare` stops** (its first line says why), tell the client in plain words and stop — never retry blindly:

| prepare says | Do |
|---|---|
| `CCC_NOT_ENGLISH:<lang>` | *"Right now the editor only works with English speech — this video is in <language>. Send an English take and I'll edit it right away."* |
| `CCC_NO_SOUND` / `CCC_NO_SPEECH` | *"I can't hear any speech in this file (no sound / only music). Send the recording with your voice."* |
| `CCC_PROJECT_EXISTS` | this exact video was already prepared — keep using that project (go to Step 6 for changes). Only if the client clearly wants to start over: `ccc prepare "<video>" --force` (deletes the old edit). |
| `CCC_NAME_TAKEN` | you passed a `--name` that belongs to another video — run `ccc name` again and use what it prints |
| `CCC_BAD_FILE` / `CCC_NO_VIDEO` / `CCC_CONVERT_FAILED` | *"This file can't be opened as a video — could you export it again (MP4 or MOV) and send it?"* |

**Fallback** — exit code 2 (no choice within 30 min) or the browser could not open: ask in Claude Code with AskUserQuestion. First the format (only `ready` ones from `ccc formats`; skip the question if only one is ready), then only the options that format allows (`ccc formats` shows them; a single allowed value is fixed — don't ask). Basic options: first "Do you want a text hook?" (Yes / No — captions only); only on Yes ask the hook text (via "Other"), hook style: TikTok Box / Editorial Serif / Color Block / Stacked, and hook position: below captions / above the head; caption style: Clean / Karaoke / Box Fill / Minimal; font for captions + hook: CCC Signature (default) / Poppins / Plus Jakarta Sans / Bricolage Grotesque (Editorial Serif hook always keeps its serif); brand color only if Karaoke, Color Block or Stacked was chosen (palette name or hex); pacing: Fast-paced (default) / Chill (a touch more breathing room, e.g. phone-in-hand); camera: zoom / static. Split Screen adds: top half Dark / Light, "Find real visuals online?" (Yes — default / No, animated only) and "Any links to articles, products or posts you mention?" (optional, via "Other"). Save with:

```
ccc choices <name> format=basic hook_text='…' hook_style=stack hook_position=below caption_style=karaoke font=ccc color=#FF5A1F pacing=fast camera=zoom
```
(It prints the saved choices — check that `hook_text` came through exactly as the client wrote it.)

Values: `format` an id from `ccc formats` · `hook_style` box|serif|color|stack · `hook_position` below|above · `caption_style` clean|karaoke|box|minimal · `font` ccc|poppins|jakarta|bricolage · `pacing` fast|chill · `color` hex or yellow|green|blue|orange|pink|red|purple|cyan · `camera` zoom|static · empty `hook_text=` means no hook · Split only: `top_style` dark|light · `web` on|off · `links="url url"`.

## Step 3 — Editorial pass (your judgment, once `prepare` is done)

The engine already removed pauses, breaths, fillers, stutters and obvious retakes (it marks them `⟵ retake` / `filler`). You catch what needs understanding:

```
ccc transcript <name>
```

Each line is one spoken chunk with word ids. Remove with `ccc remove <name> wA-wB <reason>` (reason: `off-script`, `retake`, `false-start` — anything else is refused), restore with `ccc keep <name> wA-wB`. Several ranges in one call: `ccc remove <name> w3-w7,w20-w22 retake`. The command echoes the exact words it cut — read them back to be sure you hit the right ones.

- **Automatic retakes need a look, not trust:** the engine marks a part `⟵ retake` when the next part starts the same way. Parallel sentences said on purpose ("It's not about the money. It's not about the fame.") are no longer marked, but if a `⟵ retake` line is actually a deliberate repetition, `ccc keep` it.

- **Off-script:** warm-up before the real start ("All right", "I, I, I…", "Hey hey"), talking to the camera operator ("go a little bit up", "okay"), sounds/words after the last real sentence ("Yeah. Okay. Click.").
- **Retakes / false starts:** the same sentence started again → keep the **last complete** version, remove the earlier attempts, including the abandoned fragment.
- **Leftovers around retakes:** after removing a retake, read the lines right before and after it again — a lone "bye", "okay", laugh or half word between two takes must go too (`ccc remove … off-script`). Every cut must be clean (`principles.md` 23).
- **Check unclear words by listening, never by guessing.** Words marked `nesigurno` in the hook or the first sentence, a name the speaker says (people, products — the transcript often swallows them into a neighbour word, e.g. "Her name is… And" where "Fang Taozi, and" was said), and any line that reads oddly: `ccc listen <name> <start> <end>` (original-video seconds, a few seconds around it) prints what was actually said (`?` = still unsure). Fix captions with `ccc word <name> wID "Correct"` (one id may hold several words, e.g. `"Fang Taozi, and"`; `""` hides a ghost word); spell names as your research sources do.
- **Script read aloud is off-script** (`principles.md` 35): a title or outline the speaker reads flatly to remind himself ("Kylie Cosmetics vs Rare Beauty" right after the hook line) is cut — check every line of the first ~15 s: is he telling the viewer, or reading?
- **Keep exactly one version of everything that is content** — especially structure markers ("First problem", "Step 2", "Fourth problem"): when all takes of a line are retakes, keep the last complete one. `ccc remove` prints `! retake … nijedna njegova verzija nije zadržana` when you removed every version → `ccc keep` the last one.
- **Listen to the cut before building:** `ccc verify <name>` transcribes the FINISHED audio three times (whole + two sets of short windows) and prints:
  - `čuje se ponovljeno "…"` at a source time — a leftover take the transcript didn't show (Whisper often writes two takes as one). `ccc listen <name> <t-3> <t+3>` to see both takes, then remove the earlier one: with `ccc remove` if its words are in the transcript, else `ccc cutout <name> <start> <end>` (source seconds, cut between the two takes at a quiet moment).
  - `se ne čuju` — kept words that aren't heard: listen there; a removal cut real speech → `ccc keep`.
  - It also moves every kept word's timing to where it is actually heard (captions land exactly on the voice). `ccc build` runs it automatically; fix every `!` line it prints before delivering. A natural one-word repeat the speaker meant ("more, more connected") may stay — then say so in the summary.
- **Keep** anything that is content, even if unusual. When in doubt, keep it.
- Never rewrite or invent words.

## Step 4 — Format work (everything the format needs before building)

Do every step the format file requires, in this order, before `ccc build`:
- **Basic:** only its "Judgment" items (how to split a Stacked hook, which word is bold in Minimal captions).
- **Split Screen** (all in `formats/split-screen.md`): client files (`ccc assets <name>`) → client links → research (real assets; with `web: true`) → story map → visual plan → `ccc visuals <name> --set <plan.json>` until it saves → the Judgment items. Skipping any of these makes the build fail with "nema plana" or deliver a weak video.

**Engine warnings come in two kinds** (`ccc visuals` and the build print them):
- `! [must] …` — fix every one before building (an element too short to read, an `at` outside its moment, a missing file).
- `! [aim] …` — goals that depend on what material exists (share of real visuals, variety, portraits). Do at most **2** plan revisions for them; whatever is left because the material doesn't exist stays — say so in one line of the summary. Never loop on `[aim]` lines.

`ccc stills <name> <seconds…>` renders single frames of the finished composition in seconds (no full render) — use it to look at a template change or a tricky moment before building (principle 44: check a frame right after a moment's second beat).

## Step 5 — Build

```
ccc build <name>        # the format's steps → final render → 15+ automatic checks → export
```

Run it in the background (~3–5 min). Tell the client it's being edited and roughly how long. When it ends:

- **Success:** the last lines are the client report and the exported file `<original name>-CCC-edit.mp4` next to their original video. Relay the report in your own friendly words (length before → after, what was cut with times, styles used) and give the file path.
- **The build stops before rendering** with a `CCC_…` line:
  - `CCC_NEEDS_VERTICAL` — Basic was chosen for a horizontal/square video: switch to Split Screen (`ccc choices <name> format=split-screen` + its options, Step 4), tell the client in one line, build again.
  - `CCC_BUSY` — another command is still working on this project; wait for it, then retry once.
- **Exit 1 (a check failed):** read the ❌ lines and fix, then run `ccc build <name>` again:

| ❌ line mentions | Fix |
|---|---|
| `hook … NEMA MESTA` (hook too long) | Stacked hook with your own `\|`: save the same text **without** `\|` (`ccc choices <name> hook_text='…'`) — the engine picks a split where both lines fit (never after "a/the/to…"), then build. Only if it still doesn't fit, this is the one case where you ask the client: *"Your hook is a bit long for the screen — can you shorten it?"* |
| `boja naglaska … pretamna` (color too dark) | ask the client for a lighter shade or suggest one from the palette → `ccc choices <name> color=…` |
| `glas bez titla` / `poslednji titl` | `ccc verify <name>` (re-times the words to the voice), fix its `!` lines, then build |
| `isečen glas` | a removal cut real speech → `ccc transcript <name>`, `ccc keep` the affected words |
| `bez detektovanog glasa` | the word is a transcription ghost or has a wrong time: `ccc listen` around it — not spoken → `ccc remove <name> wID off-script`; spoken → `ccc verify <name>`, then build |
| `split: … teme` (head too high/low for the bottom half) | the recording's framing — offer Basic Edit of this video, or ask for a take with a little room above the head |
| `fps izvoza` / `trajanje izvoza` | the export would play wrong on phones (above 60 fps, or file length ≠ audio length) — an engine problem, not a choice: use the support line |
| (not ❌, but `! slušanje reza: …` during the build) | a leftover take or unheard words — fix as in Step 3 (`ccc verify`), then build again |
| anything else | run `ccc check <name>` for details; fix the cause, never hide a failing check |

Never deliver a video whose check failed. If the same check fails twice after your fix, use the support line — except for your own plan's lines (`gornja polovina`, `[must]` plan timing): those you fix yourself.

If the build printed `! NO_FACE`, captions and hook went to default positions — look at one frame (`ccc stills <name> 4`) and mention it to the client.

## Step 6 — Changes after delivery

Map the request, apply, then run `ccc build <name>` again (it rebuilds everything from the saved choices and checks again). The format file may add its own rows.

| Client says | Do |
|---|---|
| "bring back / cut the part at 0:22" | `ccc transcript <name>` → find words at that time (times in the report are original-video times) → `ccc keep` / `ccc remove` |
| "change the hook text / style / position" | `ccc choices <name> hook_text=… hook_style=… hook_position=…` |
| "no hook" | `ccc choices <name> hook_text=` |
| "switch captions to …" / "use my color #…" | `ccc choices <name> caption_style=… color=…` |
| "no zoom" / "add zoom" | `ccc choices <name> camera=static|zoom` |
| "too fast / give it more room" or "tighter" | `ccc choices <name> pacing=chill|fast` (both keep no pause at the start/end and cut all mistakes) |
| "use a different font" / "make it Poppins" | `ccc choices <name> font=ccc|poppins|jakarta|bricolage` (captions + hook; Editorial Serif hook keeps its serif) |
| "make it a <other format> instead" | `ccc choices <name> format=<id>` + that format's options, read its `formats/<id>.md`, then build |
| "a caption word is wrong" (e.g. brand name) | `ccc transcript <name>` → find the word id → `ccc word <name> wID "Correct"` (timing and cuts stay the same) |

If `ccc choices` answers that the format always uses something, tell the client that's part of this format (and offer Basic Edit if they want that option).

## Where files are

- The finished video is saved **next to the client's original**: `<original name>-CCC-edit.mp4`.
- Projects live in `${CLAUDE_PLUGIN_DATA}/work/<name>/` (needed for later changes). If the client wants disk space back, finished projects can be deleted from there.

## Limits — say so instead of guessing

- English speech only; one speaker on camera; vertical (9:16) video. A horizontal video works in **Split Screen** (the engine reframes it automatically: a virtual camera follows the speaker's face in the bottom half); other formats don't reframe it yet — tell the client and offer Split Screen.
- No face found → captions and hook fall back to a default position (the build prints `! NO_FACE`); mention it.
- No sound in the file → cannot edit; ask for the original recording.
