# Capri — handoff for the next session

Read this first, then `README.txt` (user-facing feature docs). State as of branch tip
`claude/zen-ptolemy-6a26qh`, **409 unit tests passing** (1 skipped), nothing uncommitted.

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
- **Run all smoke scripts: `tools/smoke/run_all.sh` (or `run_all.sh 'smoke3*'`)** — own TMPDIR per script, fails
  on exit code, traceback, or `tick error`/`failed:` in that run's capri.log. Single script by hand:
  `xvfb-run -a -s "-screen 0 1280x1400x24" /usr/bin/python3.12 tools/smoke/smokeNN.py`
  (scripts hard-code `/home/user/ProjectCapricorn`; they monkeypatch Tk dialogs, AI, audio, hands with fakes and
  use `PIL.ImageGrab` for screenshots — look at screenshots with the Read tool; they caught real bugs).
  Index: 15 `/do` agent · 16 voice→local AI + offline fallback · 17 wake word · 18 size/presets/clip ·
  19 clip + settings shot · 20 launcher/controls/brief/neon · 21 boot animation frames · 22 hear PC audio ·
  23 call mode · 24 chat+settings screenshots · 25 other windows regression · 26 outline-off check ·
  27 notes (typed + spoken) · 28 quiet in calls (faked mic registry) · 29 `/do` with a Gemini key ·
  30 movement trace (eased walk, edge turn, steps, landing squash) · 31 no popups / explain-once · 32 skin poses · 33 expressions (fake AI tag) · 34 face pop-up + cut-in
  screenshots · 35 mini face chat avatar + tiny mode · 36 launch intro. All smoke scripts call `p.cancel_intro()`.
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
`sizing.py` · `clip.py` · `cmdargs.py` (numbers after commands) · `updater.py` (/update) · `brief.py` · `boot.py` · `neon.py` · `ui.py` (cyberpunk widgets) · `personality.py`,
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

**Changed by the user's explicit request (zen-ptolemy):** "remove ALL the are-you-sure popups". Per-action
confirmations are gone: no "Do this task?", no "Type this?" (typed text is shown in chat instead), presets and
repeat feature toggles don't ask. Features that open the mic/screen or let her act (`ledges`, `vision`, `hear`,
`wake`, `call`, `agent`, `full`, each preset) explain themselves ONCE ever via `Capri.ask_once(key, ...)`, stored
in `settings["consented"]`; anything already on at startup counts as consented. Don't re-add popups.

- **The AI never triggers actions.** Actions come only from user commands, user-enabled reflexes, or `/do` after a
  confirm dialog. Voice can lower permissions ("privacy mode"→NONE) but **never raise** them (no voice/AI path to FULL).
- Every capture feature is **opt-in with a consent dialog**: screen watching (vision), ledges, wake word,
  hearing PC audio, call mode, `/do`. Audio/screenshots stay **in memory**, never saved; text of friends' speech
  only leaves the PC if a cloud AI writes the reply (dialog says so; `/brain local` keeps it on-PC).
- `/do`: no confirm popups (see above); typed text shown in chat; stop on mouse move / click on her / `/stop`, 20 steps, 250/day,
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

1. `git pull`/checkout `claude/amazing-allen-ur4fi2`; run the unit tests (expect 409 OK, 1 skipped) and `tools/smoke/run_all.sh`.
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

## 11. Self-expression + art (same session, user supplied art; NOT run on Windows)

User asked for "more ability of self expression" and sent two zips (unpacked outside the repo, copied into
`pet/` so both build scripts bundle them; credits in `pet/CREDITS.md`, art by **xilia_world00** on Discord).
User decisions: **new skin is the default**, mini face = **chat avatar + tiny mode**.
- **Skins** (`SkinSprites`, `pet/skins/<name>/`): `capri` (default), `watcher`, `classic` (= old Petdex sheet).
  Lazy strip loading, scaled by idle figure height, crisp'd. Blink, mouth overlay for talking, dangle on drag,
  perch strip when perched, lay poses for sleep/lounge (`art.lies` = no 90° rotation), wake, drawn glitch.
  Right-click > Skins, `/skin`.
- **Expressions** (`expression.py`): `say_ai` asks for a leading `[emotion]` tag (only that path; parsed off
  BEFORE `speech.sanitize`, never shown/spoken/kept in `recent_lines`). `Capri.express()` = pose + in-place
  motion + icon, `Gate` rate limit, blocked while calm/agent/drag/tp/sleep. Face close-ups above the bubble
  (`pet/faces`, `FACES` map) and rare cut-ins (`pet/cutins`, laugh/excited/surprised, 5-min gap). Settings
  `expressive`, `faces`, `cutins` (all on). `/express [name]`.
- **Mini face** (`MiniFaces`, `pet/mini`, `expression.mini_pick`): chat avatar; tiny mode `/tiny on|off|auto`
  (auto = during a game or focus timer).
- **Intro** (`intro.py`, `pet/intro`): own topmost color-key window at launch instead of the beam boot (new
  skins only; `/intro off` = beam, `/boot off` = none). `fast_crisp` for big frames.
- **Icons**: `iconphoto` + `.ico` on Windows; Windows build uses `--icon pet\icons\capri.ico`. Mac build
  has no .icns (none supplied). `pet/fonts/ShareTechMono` is bundled but NOT used yet (Tk can't load a TTF
  without registering it on Windows).
- Not used on purpose: `capri-cutout.png`, `capri-full.png`, `tray.png` (no tray feature), dangle beyond drag.
- Riskiest on real Windows: intro window transparency/focus, perch alignment on window edges, lay pose size.

## 12. "do more stuff" batch (same session)

- `tools/smoke/run_all.sh` gate (it caught images bound to the wrong Tk root in smoke31's two-app run; all
  PhotoImages now pass `master=`).
- Chat replies act out a feeling (`expression.split_reply` / `strip_tags` in `ChatWindow.work`, before
  history/bubble/voice/call see the text; same `expressive` switch). Smoke 37.
- New skin: `air` state (falling/hopping) uses the dangle pose. Smoke 38.
- `/intro on|once|off` (`intro_mode()`; once = only while `booted` unset). Default still every launch —
  **user hasn't answered whether it should be first-launch only**.
- Considered and skipped: vectorising `crisp` (6 ms/frame, strips already build in a background thread);
  registering Share Tech Mono (Windows-only, untestable here).

## 13. Feedback from the first real Windows run + local vision

- Fixed: Settings didn't scroll on Windows (wheel went to the focused pet window) → `install_wheel` router by
  pointer position; intro now full screen (frames built in a thread); browser/site titles never count as gaming.
- `/see on` (+ Settings button): awareness + ledges + timed screen looks. Looks every `vision_interval` s
  (1-90, default 10, `/see every N`, Settings > AI slider), NO daily limit (user's call), unchanged screens not
  sent, speaks only when the activity changes.
- Local vision: `/getbrain see` (ggml-org/Qwen2.5-VL-3B-Instruct-GGUF) or `see-fast` (SmolVLM2-2.2B). Files are
  picked from the HF API listing at install time (`localai.pick_vision_files`, manifest `models/<which>/files.json`),
  engine re-downloaded if `--help` lacks `--mmproj`. Served with `--mmproj`, OpenAI `image_url` data URI. The
  vision model also chats. Routing: glances and /look use it unless `/brain cloud`; `/do` and the game spotter
  are cloud-only on purpose. NOT downloadable/runnable in this sandbox (HF blocked) — verified with fakes only.

## 14. Overnight batch (user asleep: "keep doing stuff")

- Python 3.13 check: every file compiles with no SyntaxWarnings; all non-Tk tests pass on 3.13 (no Tk for 3.13
  in the sandbox). No modules removed in 3.13 are used.
- `/report` (+ right-click > Copy bug report): `report.py` builds a scrubbed report (versions, allow-listed
  settings, recent log errors with tracebacks; keys/emails/home path removed) to clipboard + capri-report.txt.
  Loop errors now show a notice pointing at /report (max every 10 min). capri.log rotates at 1 MB.
- `read_api_key()` cached 2 s (was re-read from disk up to 50x/s via the look timer); save invalidates.
- Settings jump bar (sections register in `section()`).
- Sitting on windows (`ledges.py`), found by smoke 44 with a real window from another process:
  1. her own window is masked out of scans, which hid the corner of the box she sat on -> it stopped being a
     box -> she fell after ~2 s. `hold()` keeps her seat while part of its edge is visible.
  2. `detect()` treats an edge that runs into her window as continuing behind it (box side + extended span).
  3. `track()` pairs old/new ledges globally, closest first, box<->edge penalty (moved windows keep ids).
  Known flake: ~1 in 9 runs she drops to the floor when the window moves (harmless).
- Smoke 42 (/report scrub), 43 (jump bar), 44 (sit / ride a moving window / drop when closed), 45 (soak:
  invariants every frame; also toggles focus/tiny, game mode, meeting quiet, /see with a fake vision AI;
  SOAK_SECS / SOAK_SEED), 46 (/see every 1 with a 3 s vision AI: one look at a time, chat still answers).
- Later fixes: the behind-her edge rule applies only to the pet window (not chat/Settings, `self_mask`);
  cut-ins are never set in tiny mode. `Win32.foreground()` already skips her own process (checked).

## 15. "keep doing stuff" batch 2 (user away from the PC; NOT run on Windows)

- **Command fuzz** (`tools/smoke/smoke47.py`): every slash command x ~100 missing/weird/huge arguments (10k
  inputs), then a restart on whatever got saved. `ChatWindow.command()` is NOT wrapped in try/except, so a raise
  = "typed it, nothing happened". Found `/focus 1.2.3` (ValueError) and the `'²'.isdigit()` trap. All numbers
  typed after commands now go through `cmdargs.minutes()` / `cmdargs.index()`. New commands are picked up
  automatically (the list is read from the source); **stub any new command with real-world side effects in
  smoke 47** (`/update` is stubbed: it would `git pull` this repo).
- **Intro on 4K+**: `intro.zoom(W)` (2 from 2881 px wide): frames are built at 1/zoom and enlarged by Tk
  (`Capri.intro_photo`), and become Tk images one per tick while loading. 4K: ready in 2.6 s (was ~4 s),
  longest freeze 0.3 s (was 1.4 s), peak RSS 425 MB (was 720 MB).
- **`/update`** (+ `/update check`, right-click > Get the newest version): `updater.py` parses
  `git pull --ff-only --no-rebase` and builds chat lines with a what's-new list from the pulled commit titles
  (so keep commit titles readable). User-started only, prompts disabled (`GIT_TERMINAL_PROMPT=0`), never
  overwrites local edits, never switches branch. Not offered in a frozen exe or a non-git copy. Tests and
  smoke 48 run it against a real local git origin (monkeypatch `capri.app_dir`).
- `/report` scrubbing also removes GitHub tokens and `user:password@` inside URLs.
- **Awareness by program name** (the user's "she always gets what I'm looking at wrong", for the no-AI path):
  `Win32.foreground_app()` (OpenProcess 0x1000 + QueryFullProcessImageNameW on its own `WinDLL("kernel32")`,
  cached per pid, '' on any failure, e.g. anti-cheat protected games) -> `awareness.classify(title, app)`:
  1. program (`APPS`, `GAME_APPS`, any `*-win64-shipping` = Unreal game, `BROWSER_APPS` = web),
  2. the app/site named at the END of the title (`TAILS`, then keywords on the last segment),
  3. keywords anywhere, as whole words ("vim" is not in "Vimeo").
  "" in APPS/TAILS = launcher/system window: no activity (the Steam client is no longer "playing").
  `gamemode.detect_game(title, app)` maps exe -> supported game (`APP_GAMES`); unknown games set ctx "game" but
  do NOT start game mode (on purpose: it would make her calm in every game without being asked).
  Privacy wording (README, Settings, awareness.py docstring) now says "title and program name"; neither is kept
  (smoke 49 checks settings + log).
- Tiny mode "auto" and auto-size use `Capri.in_game()`: a game session OR any recognised game in front within
  the last 90 s (`played_at`), so unknown games shrink her too and alt-tabbing doesn't flap.
- Settings: the text beside "LET HER SEE MY SCREEN" was clipped on both sides; it's now a wrapped line below.
  (Found by looking at a real screenshot: `ImageGrab.grab(bbox=...)` of the windows under Xvfb is worth doing
  after any UI change.)
- Settings > AI: `ui.NeonSlider` (canvas; click/drag/arrow keys) replaces the stock `tk.Scale`, which was a dark
  knob on a dark trough with a clipped label. Settings > Local AI has INSTALL ONE THAT SEES / FASTER buttons
  (`install_brain("see" | "see-fast")`). Smoke 50 drives both.
- Not a bug: under Xvfb her body looks shredded on the dark fallback window because the art is black-bodied;
  on Windows the window is transparent.
