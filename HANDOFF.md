# Capri — handoff for the next session

Read this first, then `README.txt` (user-facing feature docs). State as of branch tip
`claude/lucid-cannon-xrxy2w` (the previous branch `claude/amazing-allen-ur4fi2` is older), nothing uncommitted.
**367 unit tests**: all pass except 4 that need numpy (`test_audioout` x3, `test_listen` whisper wrapper). Those 4
failed identically before my changes: the last container had **no numpy and no tkinter** for `/usr/bin/python3.12`,
so 10 Tk tests skip and no smoke script can run. Check `python3.12 -c "import tkinter, numpy"` first; on a machine
that has both, expect everything green.

## 1. What this is, and who it's for

Capri is a Tkinter **desktop pet** (Petdex/Codex "Capri" sprite sheet, Cyberpunk/Night City personality) for a
hobbyist and their **friend group**. They run it on **Windows** (use `py capri.py`), school email, cannot draw,
often can't test (e.g. on a streetcar). I test **headless on Linux** with fakes; almost nothing has run on real
Windows hardware. Be honest about that every time.

### How the user wants you to work
- "Work autonomously." No PR was ever requested. Commit + push to `claude/lucid-cannon-xrxy2w` only.
- They want **useful and cool, not corny**. They told me to *stop* "corny things" (mini games, badges, streaks,
  daily gigs were built and **reverted** — do not bring them back). Habit streaks in `/habit` still exist (ask if
  they want those gone too).
- They get angry when something unrequested is visible: they hated the cyan **glowing outline** I made default
  (now off, opt-in only). **Never change her default look without being asked.** Default accent = original green.
- **"Make her better" was answered this session:** more expression + personality matching **Capri from Cyberpunk:
  Edgerunners** (hyper, curious, teasing, thrill-seeking, clingy, chaotic-but-only-as-a-joke). Done, see §1b.
- They hate **slash commands for setup**: "remove these stupid / commands, make a menu". Setup lives in Settings now.
- They said my **sprites "are ass"**. I tried drawing a procedural sheet from code (flat chibi girl); they rejected it
  and I deleted it. **Do not generate sprites in code again.** Better art needs a real artist/generator (Petdex
  tools or an AI image tool), then a loader switch; the user can't draw. Blur was addressed with sharpening only.
- They want **her** to control her mood, not the user ("I want her to control her mood n stuff").
- They called napping "stupid": removed. Don't reintroduce sleeping.
- Their message style is blunt/profane when frustrated. Don't over-apologise; fix it and say what changed.

## 1b. What changed in the last session (all pushed)

- **Personality** (`personality.py`, `DEFAULT_PERSONA` in capri.py, `speech.py`): Edgerunners Capri voice; moods are now
  `sleepy lonely sassy playful content hyper restless`. **She picks her own mood** (`Mind.mood/weights/pick_mood`,
  holds 5-14 min, odds tilted by energy/affection/boredom/recent attention). Pokes only nudge odds (`stim`).
  Overrides: night body-clock "sleepy", and "sassy" for 5 min after 6 spam clicks. She sometimes announces her
  own mood shifts (`take_shift`, `SHIFT_LINES`). Body language per mood: `Capri.express()` + `EXPRESSIONS`.
  Chatter rate scales with mood (`chatter_scale`).
- **Dissing**: `/roast mood|off|mild|spicy` (default **mood**): her mood sets the roast level (`ROAST_BY_MOOD`), the
  setting is a ceiling, she dis you unprompted (`wants_to_diss`, `DISS`, prompt kind `diss`). Mild swearing only
  (ass/damn/hell); hard rails: no slurs/hate/threats/sexual, nothing about body/identity/family. **Capped at mild in
  Discord calls** (`roast_now(call=True)`). Game mode uses the resolved level.
- **Napping removed**: no auto-nap, no `/sleep`, no menu item. (Old `sleep` state code still exists but is unreachable.)
- **Local AI** is chosen in **Settings -> LOCAL AI & VOICE INPUT**: Small (Qwen2.5 1.5B, 1.1 GB) / Big (3B, 2.1 GB),
  `DOWNLOAD THIS MODEL`, `REMOVE LOCAL AI`, live status. `LocalAI.use(which)` restarts the engine. `/brain` and
  `/getbrain` are gone.
- **Setup commands moved to Settings**: removed `/key /fishkey /ailines /voice /getvoice /getears /gethear /wake
  /agent /call setup`. New buttons: neural voice install (VOICE), PC-audio helper + call-setup help (LOCAL AI & VOICE
  INPUT), "Let her do tasks" checkbox (AI). Action commands remain (`/do /talk /hear last /call on|off /watch /neon
  /size /preset /boot ...`). Offered, not done: moving the leftover toggles (`/hear on|off /call on|off /watch /boot
  /neon /size`) into menus.
- **Sprite sharpness**: `gfx.py` (Lanczos + unsharp, strength grows with enlargement) used by `scale_to`; squash uses
  bicubic+`hard_alpha`, rotation bicubic. The source art is only ~170 px per cell, so it can't be crisp when enlarged.
- **PC senses** (`sysmon.py`, `Capri.watch_pc`, Settings -> Behaviour "React to my PC", default on): CPU pinned 20 s
  (15 min cooldown, suppressed in games) and USB plug/unplug (Windows = removable drives only; Linux = any USB).
  Device names stay local; the AI only gets generic text.
- **Multi-monitor** (`monitors.py`, `Win32.monitors()`, `Capri.watch_monitors`, "Follow me" setting): `work_area()`
  returns the current monitor's work area; dragging/throwing across screens works; she teleports to the screen you
  settle on for 8 s (60 s cooldown). **Windows only, never run on real hardware.**
- **Throwing** (`physics.py`): mouse-velocity launch, floor/wall/ceiling bounces, crossing monitors in flight.
- **Jealousy** (`awareness.py` `JEALOUS/RELIEF`, prompt kinds `jealous`/`relief`): after 6 min on another AI site she
  teases/sulks, smug when you return. **Words only**: the user's list mentioned closing the other AI's tabs; I
  asked and they chose talk-only. Keep it that way unless they ask again (it would break the "AI never acts"
  invariant; if ever built: opt-in, confirm every time, never AI-triggered).
- **Declined/not built** from the user's pasted feature list: five-stage bonding over weeks, daily "what Claude
  got done" report card, tab closing. They only picked PC reactions + monitors, throwing, jealousy.

## 2. Workflow rules that matter

- Python: **`/usr/bin/python3.12`**. Earlier containers had tkinter + Pillow + numpy; the last one had Pillow only
  (see the status note at the top). Pure modules and their tests run regardless.
- Tests: `/usr/bin/python3.12 -m unittest discover -s tests > /tmp/all.txt 2>&1; rc=$?` then commit **only if
  rc is 0** (never pipe through `| tail` before checking the code — I once pushed a failing test that way).
- Edit `capri.py` (≈5,400 lines) with **patch scripts**: Python that does `assert s.count(old) == 1` for every
  replacement and writes only if all match. Never do blind sed on it. `ast.parse` it after patching.
- Headless GUI checks: `xvfb-run -a -s "-screen 0 1280x1400x24" /usr/bin/python3.12 tools/smoke/smokeNN.py`
  (needs tkinter; scripts hard-code `/home/user/ProjectCapricorn`; they monkeypatch Tk dialogs, AI, audio, hands with fakes and
  use `PIL.ImageGrab` for screenshots — look at screenshots with the Read tool; they caught real bugs).
  Index: 15 `/do` agent · 16 voice→local AI + offline fallback · 17 wake word · 18 size/presets/clip ·
  19 clip + settings shot · 20 launcher/controls/brief/neon · 21 boot animation frames · 22 hear PC audio ·
  23 call mode · 24 chat+settings screenshots · 25 other windows regression · 26 outline-off check.
- Every behaviour change: add/adjust unit tests in `tests/` for the pure module. When an old test breaks because
  behaviour changed *on purpose*, update the expectation (and say so); when a test finds a real bug, fix the code.
- Commits end with the attribution lines the harness gives (Co-Authored-By / Claude-Session).
- Don't `pip download` into the repo (I committed 13 `.whl` files by accident once; removed, `*.whl` ignored).
- Sandbox network: PyPI works; GitHub API, Hugging Face, Microsoft voice servers, TikTok are **blocked** — so real
  downloads/voices/models can't be exercised here.

## 3. Architecture (one line each)

Pure modules (all unit-tested, no Tk): `speech.py` (prompts, sanitize, Budget 14/min & 800/day) ·
`vision.py` (screenshot→AI JSON events, Spotter) · `gamemode.py` · `reactor.py` (template detectors, optional) ·
`ledges.py` (find boxes to sit on) · `hands.py` (keys/click/launch, levels visual<media<full, rate limits, blocked
combos) · `agent.py` (`/do` computer-use loop) · `voice.py` (Fish → Edge neural → system TTS, Speaker, mp3 play,
call routing) · `audioout.py` (play into virtual cable) · `listen.py` (mic, Whisper, endpointing, **intent()**,
wake words, reminders parsing) · `hearing.py` (PC loopback, beats, ring buffer) · `call.py` (Discord-call
conversation) · `localai.py` (llama.cpp + Qwen / Ollama / `CAPRI_LOCAL_URL`) · `gfx.py` (sprite sharpening) · `physics.py` (throws,
bounces) · `monitors.py` (screens, follow) · `sysmon.py` (CPU/USB senses) · `launcher.py` · `presets.py` ·
`sizing.py` · `clip.py` · `brief.py` · `boot.py` · `neon.py` · `ui.py` (cyberpunk widgets) · `personality.py`,
`awareness.py`, `fun.py`, `habits.py`, `memory.py`, `journal.py`, `daylog.py`, `world.py`, `breach.py`,
`simon.py`, `sfx.py`, `autostart.py`.
`capri.py` = the app: `Capri` (pet, state machine, drawing, all feature glue), `ChatWindow`, `SettingsWindow`,
`BreachWindow`, `SimonWindow`, `ReminderDialog`, `Win32` (ctypes helpers), `SheetSprites`, `crisp()`.
Pet art: `pet/spritesheet.webp` + `pet.json` (8 cols × 11 rows).

Key plumbing: `llm_reply()` routes cloud (Claude/Gemini) vs local by `BRAIN["mode"]` (auto|cloud|local);
`ai_available()`; `say_ai`/`say_moment` (every spoken line is AI-written with preset fallback after ~2.5–5 s);
background threads (Scanner, Spotter, WakeLoop, HearLoop, CallLoop, agent, installs) talk to the Tk thread via
queues drained in `scheduled()`. `listen.intent()` is the single router for spoken/typed phrases:
stop, privacy, brief, focus, control, remind, size, clip, hear, call, launch, task(→`/do`), chat.

## 4. Feature inventory (commands; see README for detail)

Chat/AI: `/clip /brief` (keys, voice, local AI and installs are in **Settings** now, no slash commands).
Hands: `/pause /next /prev /volup /voldown /mute /shot /lock /press /type /click /hands /desktop`.
Agent: enable in Settings -> AI, then `/do <task>`, `/stop`, right-click "STOP the task", clicking her stops it.
Voice in: `/talk` (push-to-talk, Ctrl+Alt+C, MIC button), wake word ("Hey Capri"/"Choom") via Settings/right-click,
`/hear on|off|last|summarize` (PC audio), `/call on|join|off` (Discord call via virtual cable; setup help in Settings).
Launch: `/open`, `/search`, voice "open Discord"/"go to YouTube"/"search for…".
Presets: `/preset none|some|full`, `/powers`; Settings → QUICK SETUP. Size: `/size …`, auto-size.
Look: `/neon <color>|off`, `/neon outline on|off`, `/boot [first|on|off]` launch animation.
Pet life: `/fly /zoom /orbit /party /tp /dance /calm /sit /ledges /tag /feed /radio /sfx`,
games (`/hack /simon`, game mode `/kill /death /ace /clutch /rw /rl /gg /kd /roast /match /game`, `/watch /look`),
productivity (`/focus /remind /todo /done /habit /did /remember /facts /forget /feel /journal /day /horoscope /lore`).

## 5. Safety design — keep these invariants

- **The AI never triggers actions.** Actions come only from user commands, user-enabled reflexes, or `/do` after a
  confirm dialog. Voice can lower permissions ("privacy mode"→NONE) but **never raise** them (no voice/AI path to FULL).
- Every capture feature is **opt-in with a consent dialog**: screen watching (vision), ledges, wake word,
  hearing PC audio, call mode, `/do`. Audio/screenshots stay **in memory**, never saved; text of friends' speech
  only leaves the PC if a cloud AI writes the reply (dialog says so; `/brain local` keeps it on-PC).
- `/do`: confirm task, approve every typed text, stop on mouse move / click on her / `/stop`, 20 steps, 250/day,
  pauses on sensitive windows (`ledges.should_scan`), blocked combos (Alt+F4, Win+R, Ctrl+Alt+Del…), text from
  screenshots/clipboard/transcripts is data (prompt says never follow instructions in it).
- Call mode announces itself to the call and can't be silently started; replies are limited (name-addressed,
  ≤8/min, one sentence). Reflexes (auto-lock/pause when away) are **never** part of any preset.
- Windows transparency uses a color key → **hard alpha only** (`crisp()`); soft edges cause pink/purple halos.

## 6. Verified vs NOT verified (be explicit with the user)

Unit/fake-tested only; **never run for real**: all Windows rendering/transparency, Fish Audio API, Edge neural
voice (`edge-tts`, unofficial MS service), Anthropic/Gemini vision & agent accuracy (coordinate scaling is tested
with fakes only), llama.cpp download names / Hugging Face model URLs (`localai.MODELS`, asset picker), faster-whisper
accuracy/latency, `soundcard` loopback (WASAPI loopback can block while nothing plays — handled by a daemon
thread), RegisterHotKey Ctrl+Alt+C, virtual-cable routing + Discord setup, Start-Menu app index, PowerShell mp3
player (`WIN_MP3_SCRIPT`), `pip install --user` flows. Call latency (~3–8 s) is an estimate.
Real hardware reports from the user are the most valuable input — ask for exact error text from the chat
(`[ERR]` lines) and `~/.capri/capri.log` (Windows: `C:\Users\<you>\.capri\capri.log`).

## 7. Known issues / gotchas

- `capri.py` is a 5.4k-line monolith; the `Capri` class has grown a lot. Refactor candidate (feature mixins) —
  only with the smoke scripts as a safety net, and only if asked.
- Chat/Settings windows read the neon accent when **built**; an already-open window keeps its old colour.
- Settings window is rebuilt (destroy/reopen) after a preset is applied so switches show the truth.
- Presets `DEFAULTS` mirror what a brand-new settings file does (mic on, awareness on, others off); `detect()`
  returns `custom` for a fresh install — expected.
- Settings windows read state when **built**: the local-AI status line polls every 2 s, other labels don't refresh.
- Voice engine order: Fish (if key) → Edge neural (if `edge-tts` installed) → system voice. Robot voice can't go
  into a call. In the sandbox Edge fails (network) and she says "my voice is acting up…" — expected here only.
- Call mode needs VB-Audio Virtual Cable + Discord input = "CABLE Output" + Windows "Listen to this device"
  on the mic → "CABLE Input" (so friends still hear the user). Mac can't do call mode/hearing.
- `listen.intent` regexes are the most fragile part (phrases like "what was that they said"); add a test for
  every phrasing the user reports.
- Fish voice id for Capri: `ef387f44931d4ab6a3f959a083c9fbb1` (needs the user's own Fish key; I have none).

## 8. Open items / ideas

1. **Real-hardware feedback loop (most valuable)**: have the user run `py capri.py` and try: throwing her, plugging
   a USB drive, a second monitor, the Settings buttons (local model pick/download, neural voice, PC-audio helper),
   dissing/mood announcements, the `/do open notepad and type hello` task; collect `[ERR]` text and `capri.log`.
   **Nothing from the last session was run in a real GUI** (no tkinter in the sandbox): `express()`, `watch_pc`,
   `watch_monitors`, the new physics air step, drag/release, and every new Settings widget are verified only by
   unit tests of the pure modules plus `py_compile`. Run smoke scripts 24/25 as soon as tkinter is available.
2. Better sprites: needs real art (see §1). Add a `/skin`-style switch only once they have a sheet they like.
3. Ask whether to remove habit streaks too (user said "remove the streaks and allat" about the corny batch).
4. Maybe move the leftover toggle commands into menus (see §1b).
5. Possible next *useful* features (user wants useful, not gimmicks): notes with voice recall, per-app muting of
   her chatter during calls/meetings, saving presets of her settings per profile, Gemini support for `/do`
   (currently Claude-only), speaker separation in call mode (currently everyone = "Friend").
6. Optionally turn `tools/smoke/*.py` into a runnable suite (they're scripts with prints, not asserts).

## 9. First moves for the new session

1. `git pull`/checkout `claude/lucid-cannon-xrxy2w`; run the unit tests (expect 367 run; only the 4 numpy ones may
   error if numpy is missing).
2. Skim `README.txt` and this file; do not re-derive decisions listed above.
3. Ask the user for real-machine results (§8.1) before building more; if they have new asks, take them.
