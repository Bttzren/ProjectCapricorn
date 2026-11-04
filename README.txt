CAPRI - desktop companion

RUN
  Windows: double-click 1_RUN_Capri_Windows.bat   (needs Python 3.9+ from python.org)
  Mac:     double-click 1_RUN_Capri_Mac.command   (first time: right-click > Open)
  Linux:   ./run_linux.sh   (needs python3-tk and python3-pil.imagetk)
  Real .exe: run 2_BUILD_exe_Windows.bat -> dist\Capri.exe

WHAT SHE DOES
  She is the animated Petdex Capri (the pet/ folder: spritesheet + pet.json). She idles,
  walks, waves, jumps, droops when something goes wrong, and her moods change what she does.
  She roams, lounges, naps, glitch-teleports, gets curious about your cursor, startles if you
  swipe at her, and gets annoyed (sassy for a few minutes) if you spam-click.
  On Windows she can perch on the top edge of your active window (and always on the chat window).
  Drag to pick her up, fling to throw her. Click: poke. Double-click: chat.
  Right-click (Ctrl-click Mac): menu (focus timer, reminders, teleport, dance, lounge, nap, calm mode).

FLYING & EXPRESSION
  She flies around the screen on her own (sometimes a slow tour, sometimes a fast zoom, sometimes
  circling your cursor) and lands when she's done. Playful moods fly more, sleepy ones less,
  lonely ones circle your cursor. Right-click > Fly around / Orbit my cursor / Party!, or /fly /zoom
  /orbit /party in chat. Finishing a focus timer sets off a confetti party. Over her head she shows
  icons: ! ? hearts, stars, music notes, anger marks.

AWARENESS (Windows only)
  She can tell roughly what you're doing and react: coding, watching a video, music, school work,
  chatting, writing, games (extra excited about Cyberpunk 2077), social media (she'll nudge you if
  you scroll for 25 minutes), or chatting with another AI. She also notices when you've been away
  for 10+ minutes (she naps) and greets you when you're back.
  PRIVACY: she only reads the TITLE of the front window and turns it into a one-word category.
  The title is never stored, logged or sent anywhere. She never sees what you type or what's on
  your screen. When you chat, only a short hint such as "coding" is added to the AI's instructions.
  Turn it off any time: right-click > Awareness, or /aware off.

SETTINGS & HANDS
  Right-click her > Settings... (or /settings) opens one window: hands, voice, behaviour, keys.
  HANDS decides what she may do on your computer. It is enforced in code, not just in the menu:
    Visual only  (default) - she mimes typing along while you're busy; sends nothing to your computer
    Media keys   - on request: /pause /next /prev /volup /voldown /mute /shot (screenshot) /lock
    Full control - also /press ctrl+s, /type hello there, /click [right|double]. Turning this on asks
                   for confirmation. These wait 5 seconds so you can click where you want the input
                   to go; click her to cancel.
  Optional REFLEXES (Full control only, off by default): lock the screen after 15 minutes away; pause
  video/music after 5 minutes away. She announces them 10 seconds ahead; click her or touch the
  mouse/keyboard to cancel.
  Safety: real input only comes from YOUR commands or reflexes YOU switched on - never from the AI's
  replies. Shortcuts like Alt+F4 and Ctrl+Alt+Del are blocked. Typed text can't press Enter and is
  capped at 200 characters. Max 12 actions a minute. Lowering the level cancels anything pending.
  Only the action name is logged (never what she typed). Real key presses are fully supported on
  Windows; Mac and Linux use osascript / xdotool / playerctl / pactl if installed.

GAMES & TOYS
  TAG: /tag (or right-click > Play tag). She runs from your cursor for 25 seconds and glitch-
  teleports out of corners. Touch her with your cursor to win. Best time is kept.
  TO-DO: /todo add <thing>, /todo, /done <number>, /todo clear. She nags about what's left roughly
  hourly (not in calm mode).
  TOYS: /roll d20 (or 2d6, 100), /coin, /8ball <question>
  She also glitches (RGB split) for a moment every minute or so, because she's a glitchy AI.

MORE STUFF
  BREACH PROTOCOL (hacking minigame): /hack or right-click > Hack. Fill the buffer so it contains the
    daemon sequences. First pick is in the TOP row, then alternate column / row; cells can't be
    reused; 45 seconds. Every puzzle is solvable.
  SOUND EFFECTS: little synthesized blips and jingles (no audio files). Never cuts her voice off.
    Settings > Sound effects, or /sfx on|off.
  PEEKING: she sometimes peeks out from the edge of the screen, then slides back in.
  RAMEN: /feed (or right-click > Feed ramen) makes her very happy. If you haven't
    fed her in 6+ hours she'll hint at it now and then.
  NIGHT CITY RADIO: /radio on for a DJ drop every few minutes (off by default).
  SPECIAL DAYS: she greets you on holidays (New Year, Valentine's, Pi Day, Halloween, Night City Day,
    Christmas) and on YOUR birthday: /birthday 03-27.
  BATTERY (Windows laptops): she warns you at 20% and cheers when you plug in.

GAME MODE (she hypes your kills and roasts your deaths)
  When a supported game is in front (Valorant, CS2, Apex, Overwatch, Fortnite, League, Rocket League,
  Cyberpunk 2077; needs Windows + Awareness on) she tucks into a corner, stays quiet, and keeps a K/D
  for the session. When you close the game she gives a recap ("Valorant: 15 kills, 12 deaths..."). Only
  the numbers are kept (last 20 sessions), never what you did.
  TELL HER WHAT HAPPENED (works for any game, any OS):
     /kill [2-5]   /death   /ace   /clutch   /rw (round won)   /rl (round lost)
     /gg win|loss  (match over)   /kd (status)   /match 13-7 15/12 (rounds 13-7, kills/deaths)
  ROAST LEVEL: /roast off | mild | spicy  (or Settings > Gaming). off = only supportive. mild (default)
     = "that was tragic, gonk". spicy = she'll tell you that was ass (mild swearing, never slurs).
  Her chat replies know what you're playing and your session K/D too.
  IMPORTANT FOR FULLSCREEN: games in "Fullscreen" can hide her. Use "Windowed Fullscreen" / borderless.
  AUTOMATIC KILL/DEATH DETECTION - the AI SPOTTER (works for ANY game):
     Turn on Settings > AI > "AI Spotter" (she asks first). While a game is in front (or after /watch on)
     she takes a small shrunken screenshot every few seconds and asks the AI (Claude or Gemini, your key)
     whether something just happened: a kill, a death, round/match won or lost, a clutch, an ace. It tells
     her what it saw AND what to say, so K/D and commentary update by themselves. A small eye shows next
     to her whenever she's looking (grey while paused). /watch shows status, /watch off stops,
     /look what is this error?  = one-off look at the screen with a question.
     PRIVACY & COST, plainly: the shrunken screenshot IS SENT to your AI provider (Anthropic or Google),
     so it can include anything visible on your screen. Capri never saves it. It is only sent when the
     screen changed, she pauses on banking / password / sign-in / private-browsing windows, while you're
     away, and while her own windows are in front. It uses your API credits: very roughly $1-3 an hour with
     Claude (Haiku); set the interval to 10s to cut that, and there's a daily limit (600 looks by default,
     vision_daily_cap in settings.json). She never acts on what the AI says: it can only make her talk
     and count K/D.
  (There's also an offline option: game_events.json with reference images of fixed screen patches, see
   game_events.example.json. It never sends anything anywhere, but needs setting up per game.)

AI-WRITTEN LINES (everything she says out loud)
  With a Claude or Gemini key, the words she speaks and shows in her bubble are written by the AI, not
  chosen from a list: pokes, idle chatter, check-ins, greetings, startling or annoying her, flying,
  peeking, teleporting, tag, ramen, the minigames, battery, radio, hunger, habit and to-do nags, memory
  callbacks, welcome back, holidays, focus timer endings, game kills/deaths/recaps. For each moment she's
  told WHAT JUST HAPPENED plus her mood, what you're doing, your /remember facts and roast level, and what
  she said recently so she doesn't repeat herself. One short sentence each (Haiku, ~80 tokens).
  Stays EXACT (never AI): reminder text, timer confirmations, countdowns like "locking in 3...", privacy
  and settings messages.
  The preset lines are only a fallback: no key, no internet, AI error, a quick reaction where the AI is
  slower than ~2.5s (longer moments wait 4-5s), or the limit (14 a minute, 800 a day). After 3 failures in
  a row she uses presets for 5 minutes and says why. /ailines on|off shows today's count.

SCREEN LEDGES (she sits on boxes on your screen)  - OFF by default, needs your OK
  She can look at your screen, find boxes (cards, text boxes, images, panels) and fly over to sit on
  their top edge. If the page scrolls she rides along; if the box goes away she falls.
  Turn on: Settings > "Screen ledges", or /ledges on (she asks first). /sit makes her perch on one now,
  right-click > Sit on something. /ledges off stops it.
  PRIVACY, in plain words: every few seconds she takes a screenshot IN MEMORY, looks for box edges on
  your own computer, and throws the screenshot away. Nothing is saved to disk or sent anywhere. Her own
  windows are ignored. She stops looking while the front window looks private (banking, passwords,
  sign-in, private browsing) and while you're away. Anything on screen is briefly visible to her code,
  so only turn it on if you're comfortable with that. Windows/Mac need nothing extra (Mac asks for
  Screen Recording permission); Linux needs an X11 session.

SHE KNOWS YOU
  MEMORY: /remember my favorite game is Minecraft, /facts, /forget 1. She brings facts up now and
    then, and they're added to her chat instructions (only what you told her to remember). Local only.
  HABITS: /habit add drink water, /habit, /did 1 (check off), /habit rm 2. Streaks, with a
    confetti celebration at 7 and 30 days, a gentle reminder at 8pm for anything left.
  JOURNAL: around 8:30pm she asks how today was. /feel 4 good day, /journal for the last week.
  DAILY RECAP (Windows): /day shows time per KIND of app (coding 2h, videos 45m...), with an evening
    recap. Only category totals are kept for 14 days. Never window titles. Settings > Track time.
  SIMON: /simon (or right-click > Memory game). Repeat the growing colour sequence. How many rounds can you get?
  HOROSCOPE & LORE: /horoscope (uses your /birthday), /lore.
  START WITH WINDOWS: Settings > "Start Capri when I log in" (puts a tiny Capri.vbs in your Startup
    folder; untick it to remove).

PERSONALITY
  She talks like a Night City local (choom, preem, nova, gonk, eddies, chrome...), kept PG.
  The same slang is built into her canned lines and into the AI persona prompt.
  She has moods: sleepy, lonely, sassy, playful, content. Her mood depends on the time of day,
  how much you interact with her (affection), and whether you annoyed her. Mood changes what she
  does (a sleepy Capri naps, a playful one dances and teleports, a lonely one follows your cursor),
  what she says, and how she answers in chat. She greets you by time of day, notices if you were
  away for hours, and remembers your name (/name <you>). Affection is kept between runs.

VOICE
  She talks out loud. Right-click her > Voice: Off / Replies & alerts only / Chatty, or type
  /voice off|replies|chatty in the chat. Her mouth moves while she speaks. Calm mode mutes her
  ambient chatter.
  Capri's real voice (Fish Audio): get an API key from fish.audio, then in the chat window type
      /fishkey <your key>
  (or set FISH_API_KEY, or put the key in fish_key.txt next to capri.py). She uses voice model
  ef387f44931d4ab6a3f959a083c9fbb1 (override with CAPRI_FISH_VOICE). Note: every line she speaks is
  sent to Fish Audio, which uses your credits. Lines are cached in ~/.capri/voice_cache so repeats
  are free. /fishkey off goes back to the built-in voice. If Fish fails (no internet, bad key, no
  credits) she falls back to the built-in voice and tells you why.
  Without a Fish key she uses your computer's built-in speech (nothing to install on Windows or Mac;
  on Linux install espeak-ng). Set CAPRI_VOICE to pick a different installed voice.

CHAT
  Works right away in offline mode (canned, mood-based replies). For real AI chat, double-click her,
  paste a Claude key (sk-ant...) or a Gemini key into the box at the top of the chat window and press
  SAVE KEY. It is stored in ~/.capri/api_key.txt. (You can also use /key <key>, an environment
  variable, or copy api_key.example.txt to api_key.txt next to capri.py.)
  Enter sends, Shift+Enter = new line. Click a bubble to copy it. History is saved.
  Slash commands: /help /focus [min] /remind <min> <text> /name <you> /mood /voice /key <key> /tp /dance /sleep /calm /clear
  Edit personality: create persona.txt next to capri.py with your own instructions.

HER LOOK (pet/ folder)
  The bundled pet/ folder is used first. To use a different Codex/Petdex pet, install it
  (npx petdex@latest install <name>) or point CAPRI_PET_DIR at its folder.
  Preview every animation row she loaded:  python capri.py --pet-preview
  If animations look mismatched, add pet_map.json next to capri.py, e.g.
  {"idle":0,"running-right":1,"running-left":2,"waving":3,"jumping":4,"failed":5,"waiting":6,"running":7}
  (The sheet has two extra rows of 8 frames at the bottom that she doesn't use yet.)

FILES she writes: ~/.capri/ (settings, chat history, capri.log for errors)
Linux has no real transparency (dark box). Perching on other apps' windows is Windows-only.

DEVELOPING
  personality.py  moods, memory, lines (no Tk)       awareness.py  window title -> activity (no Tk)
        voice.py  speech: Fish Audio + system voice (no Tk)
  hands.py        key presses / clicks with safety rails (no Tk)
  breach.py  hacking puzzle   sfx.py  sound effects   world.py  holidays, radio, battery (all no Tk)
  gamemode.py  game commentary   reactor.py  screen-patch detectors   speech.py  vision.py  AI lines + spotter   ledges.py  screen box detection   simon.py  habits.py  memory.py  journal.py  daylog.py  autostart.py
  fun.py  dice, to-dos, horoscope
  Tests:  python -m unittest discover -s tests
