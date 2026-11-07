# Capri — handoff for the next session

Read this first, then `README.txt` (user-facing feature docs). State as of branch tip
`claude/zen-ptolemy-6a26qh`, **355 unit tests passing** (1 skipped), nothing uncommitted.

**Fresh container setup** (both were missing in the last session; without them 4 tests error and every smoke
script dies on `import tkinter`):
`apt-get install -y python3-tk python3-pil.imagetk` and
`/usr/bin/python3.12 -m pip install --user --break-system-packages numpy pyflakes`.

## 1. What this is, and who it's for

Capri is a Tkinter **desktop pet** (Petdex/Codex "Capri" sprite sheet, Cyberpunk/Night City personality) for a
hobbyist and their **friend group**. They run it on **Windows** (use `py capri.py`), school email, cannot draw,
often can't test (e.g. on a streetcar). I test **headless on Linux** with fakes; almost nothing has run on real
Windows hardware. Be honest about that every time.

### How the user wants you to work
- "Work autonomously." No PR was ever requested. Commit + push to the branch the harness names (last:
  `claude/zen-ptolemy-6a26qh`; before that `claude/amazing-allen-ur4fi2`).
- They want **useful and cool, not corny**. They told me to *stop* "corny things" (mini games, badges, streaks,
  daily gigs were built and **reverted** — do not bring them back). Habit streaks were **removed** too (user said
  yes); `/habit` is a plain daily checklist. Game-mode kill/death streak *commentary* was kept (it's not a tracker).
- They get angry when something unrequested is visible: they hated the cyan **glowing outline** I made default
  (now off, opt-in only). **Never change her default look without being asked.** Default accent = original green.
- "make her better" was answered: **"ALL OF EM"** (look, movement, personality, bugs, useful features). Done in
  the zen-ptolemy session — see §10. They like high energy replies and short status lines; don't ask more
  questions when they've said "all".
- The user can attach an **advisor** (`/advisor`); use it before big changes and before declaring done.
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
  23 call mode · 24 chat+settings screenshots · 25 other windows regression · 26 outline-off check ·
  27 notes (typed + spoken) · 28 quiet in calls (faked mic registry) · 29 `/do` with a Gemini key ·
  30 movement trace (eased walk, edge turn, steps, landing squash).
  Also grep each run's `$HOME/.capri/capri.log` for `tick error` — that's how a frozen-pet bug shows up.
  (smoke20 sets `state="fly"` by hand; that used to log IndexErrors, now guarded.)
- Every behaviour change: add/adjust unit tests in `tests/` for the pure module. When an old test breaks because
  behaviour changed *on purpose*, update the expectation (and say so); when a test finds a real bug, fix the code.
- Commits end with the attribution lines the harness gives (Co-Authored-By / Claude-Session).
- Don't `pip download` into the repo (I committed 13 `.whl` files by accident once; removed, `*.whl` ignored).
- Sandbox network: PyPI works; GitHub API, Hugging Face, Microsoft voice servers, TikTok are **blocked** — so real
  downloads/voices/models can't be exercised here.

## 3. Architecture (one line each)

Pure modules (all unit-tested, no Tk): `speech.py` (prompts, sanitize, Budget 14/min & 800/day) ·
`vision.py` (screenshot→AI JSON events, Spotter) · `gamemode.py` · `reactor.py` (template detectors, optional) ·
`ledges.py` (find boxes to sit on) · `notes.py` (voice/typed notes, keyword recall) · `meeting.py` (in a
call? title patterns + Windows mic-in-use registry, grace period) · `motion.py` (walk easing, step clock,
landing squash) · `hands.py` (keys/click/launch, levels visual<media<full, rate limits, blocked
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

1. (done) "make her better" → all of it; see §10. Next: get real-Windows feedback on §10 items.
2. Real-hardware feedback loop: have the user run `py capri.py`, try `/call setup`, `/getbrain`, `/getears`,
   `/do open notepad and type hello`, and report `[ERR]` text.
3. (done) Habit streaks removed.
4. Possible next *useful* features (user wants useful, not gimmicks): notes with voice recall, per-app muting of
   her chatter during calls/meetings, saving presets of her settings per profile, speaker separation in call mode
   (currently everyone = "Friend"; needs model downloads, HF is blocked here). Notes, call/meeting quiet and
   Gemini `/do` are DONE.
5. Optionally turn `tools/smoke/*.py` into a runnable suite (they're scripts with prints, not asserts).

## 9. First moves for the new session

1. `git pull`/checkout `claude/amazing-allen-ur4fi2`; run the unit tests (expect 333 OK).
2. Skim `README.txt` and this file; do not re-derive decisions listed above.
3. Ask the user for real-Windows feedback on the §10 changes (exact `[ERR]` text + `capri.log`).

## 10. zen-ptolemy session (what changed; all unit/fake-tested, NOT run on real Windows)

- **Habit streaks removed** (`habits.check` returns `(ok, name)`; no confetti at 7/30).
- **Notes**: "Capri, note that …" / "take a note: …" / "write this down …" / `/note <text>`; recall with
  "what did I note about X" / "read my notes" / `/notes [query]`, `/notes rm N`. `listen.note_intent` runs
  before controls/remind/launch; tests pin that "open notepad", remind, brief, hear, tasks, chat still route.
  Stored as text in settings.json (`notes`), never sent to the AI. Spoken recall reads the best match only.
- **Quiet in calls/meetings** (setting `meeting_quiet`, default ON, Settings > Gaming): meeting window titles
  (Awareness on) or a known CALL app with the mic open (HKCU ConsentStore\microphone, `LastUsedTimeStop == 0`;
  allow-list `meeting.CALL_APPS`, so OBS/NVIDIA Broadcast/Voicemeeter/Sonar/Krisp never trigger it; a mic
  signal stuck 4 h with no meeting window is ignored until it changes). Sets calm (stash/restore like game mode), 45 s grace, manual calm toggle
  during a call wins. The registry reading is the riskiest unverified part — ask the user if she goes quiet in
  a Discord call and back afterwards.
- **`/do` with Gemini**: only the provider guard blocked it. Gemini agent calls add a "pixels, not 0-1000" note
  and 8x maxOutputTokens (thinking tokens). Accuracy vs Claude unknown.
- **Personality**: persona/STYLE ask for sparse slang + dry humour; preset lines rewritten with far fewer
  "choom"s (test now requires slang in >10% and <50% of preset lines, "choom" ≤ 3); `Mind.pick` shuffle-bag
  so preset lines don't repeat until a pool is used up.
- **Movement**: `motion.py` — 0.35 s ease in/out per walk, random pace 0.85–1.15, slow near edges, 0.25 s turn
  pause then ease back up, bob + run frames follow a distance-based step clock (`SheetSprites.frame(..., phase)`),
  landing squash by fall speed. Fixed an edge flip-flop found by the smoke 30 trace. `fly` with no waypoints
  now drops to `air`.
- **Look**: only a ~0.1 s width squash when she turns (NEAREST scaling, alpha stays 0/255). Default look,
  green accent, outline-off all unchanged.
