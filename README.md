# CCC Editor for Claude Code

**Create Content Club's video editor.** Give it a raw talking-head video and get back a finished vertical reel:

- tight cuts — pauses, breaths, filler words, repeated takes and off-camera talk removed
- a text hook in the first seconds
- captions in your style (and your brand color)
- camera zooms on jump cuts (optional)
- clean, loud-enough audio for Instagram / TikTok / Shorts

You pick a format and style on a simple page, and the rest happens automatically.

---

## What you need

| | |
|---|---|
| Computer | **Mac** (macOS 12 or newer) or **Windows 10 / 11** PC |
| Disk space | about **6 GB free** |
| Internet | needed for the one-time setup (it downloads about 2.5 GB) |
| Claude | a Claude account with **Claude Code** (Pro or Max plan) |

---

## Step 1 — Install Claude Code

Pick **one** of these:

- **Claude desktop app** — download it from **claude.ai/download**, install it, sign in, and open the **Code** tab.
- **Terminal version**
  - **Mac:** open the **Terminal** app and paste:
    ```
    curl -fsSL https://claude.ai/install.sh | bash
    ```
  - **Windows:** open **PowerShell** and paste:
    ```
    irm https://claude.ai/install.ps1 | iex
    ```
  Then type `claude` and sign in.

## Step 2 — Windows only: install Git

1. Go to **git-scm.com/download/win** and download **Git for Windows**.
2. Run the installer and keep **all the default options** (just click *Next* until *Install*).
3. **Restart your computer** (or at least close and reopen Claude Code).

Mac users skip this step.

## Step 3 — Add the CCC Editor (one time)

**In the terminal** (Mac: *Terminal* app · Windows: *PowerShell*), paste these two lines one by one:

```
claude plugin marketplace add createcontent-club/ccc-editor
```
```
claude plugin install ccc-editor@createcontent-club --scope user
```

> Already inside Claude Code? You can type the same thing as commands instead:
> `/plugin marketplace add createcontent-club/ccc-editor` and then `/plugin install ccc-editor@createcontent-club`

Then **close and reopen Claude Code** (desktop app or terminal) so it picks up the editor.

## Step 4 — Edit your first video

1. Open Claude Code and start a new session.
2. Type something like:

   > My new video is ready: *(drag your video file into the chat)*

   Dragging the file in pastes its location — that's all Claude needs.
3. **First time only:** Claude sets up the editor on your computer. This takes about **5–10 minutes** and you don't need to do anything. If your computer asks for permission to let a command run, allow it.
4. The **CCC Editing Style Menu** opens in your browser:
   - pick a **format** — e.g. **Basic Edit** (formats marked *Coming soon* arrive with updates)
   - on the format's page, choose your details. For Basic Edit:
     - type your **text hook** (or tick *No text hook*)
     - choose a **hook style** and where it sits (**below the captions** or **above your head**)
     - choose a **caption style**
     - pick your **brand color** (if your styles use one) — from the palette or type your hex code, e.g. `#FF5A1F`
     - choose **Zoom** or **Static** camera
   - click **Start editing**
5. A few minutes later your finished video is saved **next to your original**, named `<your file>-CCC-edit.mp4`. Claude tells you what was cut and how long the video is now.

> **Stacked hook tip:** use `|` to split it into a main line and a smaller second line, e.g.
> `how to go viral | start growing, stop guessing`

## Asking for changes

Just say it in plain words in the same chat, for example:

- "bring back the part at 0:22"
- "make the hook shorter: how to go viral"
- "put the hook above my head"
- "switch the captions to Clean"
- "use my color #2EF2FF"
- "no zoom please"
- "the word at 0:15 should be **Notion**, not *notion*"

Claude updates the video and saves it again in the same place.

## Getting updates

New video formats (the *Coming soon* cards in the menu) and styles are added over time. To get them:

- **Easiest:** in Claude Code type `/plugin`, open **Marketplaces → createcontent-club** and turn on **auto-update**.
- **Or** in the terminal:
  ```
  claude plugin update ccc-editor@createcontent-club
  ```

After an update, the first edit may take a minute longer while the editor refreshes itself.

## Tips for the best result

- Film **vertical (9:16)**, one person talking to the camera, in **English**.
- A clip-on or shotgun mic makes a big difference.
- Don't worry about mistakes — just repeat the sentence. The editor keeps your **last complete take**.
- Leave a second of silence before you start and after you finish.

## Privacy

Your video files never leave your computer — all editing and rendering happens locally. To decide what to cut, Claude reads the **text transcript** of what you said, as part of your normal Claude Code conversation.

## Removing the editor

```
claude plugin uninstall ccc-editor@createcontent-club
```

This also deletes the downloaded tools (about 5 GB). Your original and edited videos stay where they are.

## Need help?

**Message us in your 1-on-1 chat on Discord** — tell us what you were doing and what Claude said, and we'll help.
