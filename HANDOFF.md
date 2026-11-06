# Capri — handoff for the next session

Read this first, then `README.txt` (user-facing feature docs). State as of branch tip
`claude/amazing-allen-ur4fi2`, **333 unit tests passing**, nothing uncommitted.

## 1. What this is, and who it's for

Capri is a Tkinter **desktop pet** (Petdex/Codex "Capri" sprite sheet, Cyberpunk/Night City personality) for a
hobbyist and their **friend group**. They run it on **Windows** (use `py capri.py`), school email, cannot draw,
often can't test (e.g. on a streetcar). I test **headless on Linux** with fakes; almost nothing has run on real
Windows hardware. Be honest about that every time.

### How the user wants you to work
- "Work autonomously." No PR was ever requested. Commit + push to `claude/amazing-allen-ur4fi2` only.
- They want **useful and cool, not corny**. They told me to *stop* "corny things" (mini games, badges, streaks,
  daily gigs were built and **reverted** — do not bring them back). Habit streaks in `/habit` still exist (ask if
  they want those gone too).
- They get angry when something unrequested is visible: they hated the cyan **glowing outline** I made default
  (now off, opt-in only). **Never change her default look without being asked.** Default accent = original green.
- **Open request, unanswered:** "make her better" (after the outline rant). Unclear whether it means look /
  movement / personality / something broken. I asked; no reply yet. Ask again briefly, then act.
- Their message style is blunt/profane when frustrated. Don't over-apologise; fix it and say what changed.

## 2. Workflow rules that matter

- Python: **`/usr/bin/python3.12`** (has tkinter + Pillow + numpy; `python3` is 3.13 without tkinter).
- Tests: `/usr/bin/python3.12 -m unittest discover -s tests > /tmp/all.txt 2>&1; rc=$?` then commit **only if
  rc is 0** (never pipe through `| tail` before checking the code — I once pushed a failing test that way).
- Edit `capri.py` (≈5,400 lines) with **patch scripts**: Python that does `assert s.count(old) == 1` for every
  replacement and writes only if all match. Never do blind sed on it. `ast.parse` it after patching.
- Headless GUI checks: `xvfb-run -a -s "-screen 0 1280x1400x24" /usr/bin/python3.12 tools/smoke/smokeNN.py`
  (scripts hard-code `/home/user/ProjectCapricorn`; they monkeypatch Tk dialogs, AI, audio, hands with fakes and
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
conversation) · `localai.py` (llama.cpp + Qwen / Ollama / `CAPRI_LOCAL_URL`) · `launcher.py` · `presets.py` ·
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

Chat/AI: `/key /fishkey /voice /ailines /brain /getbrain /getvoice /getears /gethear /clip /brief`.
Hands: `/pause /next /prev /volup /voldown /mute /shot /lock /press /type /click /hands /desktop`.
Agent: `/agent on|off`, `/do <task>`, `/stop`, right-click "STOP the task", clicking her stops it.
Voice in: `/talk` (push-to-talk, Ctrl+Alt+C, MIC button), `/wake on|off` ("Hey Capri"/"Choom"),
`/hear on|off|last|summarize` (PC audio), `/call on|join|off|setup` (talk to friends in a Discord call via virtual cable).
Launch: `/open`, `/search`, voice "open Discord"/"go to YouTube"/"search for…".
Presets: `/preset none|some|full`, `/powers`; Settings → QUICK SETUP. Size: `/size …`, auto-size.
Look: `/neon <color>|off`, `/neon outline on|off`, `/boot [first|on|off]` launch animation.
Pet life: `/fly /zoom /orbit /party /tp /dance /sleep /calm /sit /ledges /tag /feed /radio /sfx`,
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
- Voice engine order: Fish (if key) → Edge neural (if `edge-tts` installed) → system voice. Robot voice can't go
  into a call. In the sandbox Edge fails (network) and she says "my voice is acting up…" — expected here only.
- Call mode needs VB-Audio Virtual Cable + Discord input = "CABLE Output" + Windows "Listen to this device"
  on the mic → "CABLE Input" (so friends still hear the user). Mac can't do call mode/hearing.
- `listen.intent` regexes are the most fragile part (phrases like "what was that they said"); add a test for
  every phrasing the user reports.
- Fish voice id for Capri: `ef387f44931d4ab6a3f959a083c9fbb1` (needs the user's own Fish key; I have none).

## 8. Open items / ideas (none started)

1. **Answer "make her better"** (see §1) — ask which of look / movement / personality / bug.
2. Real-hardware feedback loop: have the user run `py capri.py`, try `/call setup`, `/getbrain`, `/getears`,
   `/do open notepad and type hello`, and report `[ERR]` text.
3. Ask whether to remove habit streaks too (user said "remove the streaks and allat" about the corny batch).
4. Possible next *useful* features (user wants useful, not gimmicks): notes with voice recall, per-app muting of
   her chatter during calls/meetings, saving presets of her settings per profile, Gemini support for `/do`
   (currently Claude-only), speaker separation in call mode (currently everyone = "Friend").
5. Optionally turn `tools/smoke/*.py` into a runnable suite (they're scripts with prints, not asserts).

## 9. First moves for the new session

1. `git pull`/checkout `claude/amazing-allen-ur4fi2`; run the unit tests (expect 333 OK).
2. Skim `README.txt` and this file; do not re-derive decisions listed above.
3. Reply to the user about "make her better" with one short question, unless they've already answered.
