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
    Full control - also /press ctrl+s, /type hello there, /click [right|double]. Turning this on explains
                   itself once (first time only). These wait 5 seconds so you can click where you want the input
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

EXPRESSIONS (Settings > Size & look > "Act out how she feels", on by default)
  When the AI writes one of her lines it also picks how she feels (happy, laugh, smug, sad, angry, surprised,
  thinking, embarrassed, sleepy...). She acts it out in place: a pose from her skin, a small hop/shake/tilt and
  sometimes an icon. Not every line (she'd look corny), never while she's calm, in a call/game or doing a task.
  The feeling word is never shown or spoken. /express lists them, /express smug previews one.
  FACES: a close-up of her face (smug, laughing, wide-eyed...) pops up on top of her speech bubble while she
    feels something. Settings > Size & look to turn off.
  CUT-INS: for big moments only (laughing, hyped, shocked) an anime-style panel slides across her for about a
    second, at most once every 5 minutes. Settings > Size & look to turn off.

SKINS (right-click her > Skins, or /skin <name>)
  capri    her new look, drawn by xilia_world00 (default): blinks, grins, glitches for real, talks with a
           moving mouth, sits on window edges, dangles when you pick her up, lies down to nap.
  watcher  the Watcher, a secret skin by xilia_world00.
  classic  the original Petdex sprite sheet (her old look).
  Your own skin: a folder in pet/skins/ (or %USERPROFILE%\.capri\pet\skins\) with the same strip names and
  frame sizes as pet/skins/capri/ - see pet/CREDITS.md.

LAUNCH INTRO (/intro to replay, /intro off for the old beam animation, /boot off for none)
  When she starts she climbs up into your screen, grabs the edges, says hi, grins and waves, then drops away
  and appears as usual (about 3.6 s, click it to skip). Not with the classic skin. Her icon (pet/icons) is
  on her windows, and the Windows .exe build uses capri.ico.

TINY MODE (right-click > Tiny mode, or /tiny on | off | auto)
  Just her floating visor face (mini art by xilia_world00): it blinks, talks, glances around and gets annoyed.
  'auto' (default) = tiny while a game is in front or a focus timer runs, full size otherwise. The same face is
  her avatar in the chat window.

QUIET IN CALLS AND MEETINGS (Windows, on by default; Settings > Gaming to turn off)
  She goes calm (no chatter, stays put) while you're in a call or meeting, and goes back to normal
  about 45 seconds after it ends. She notices it two ways, both on your PC only:
  - a Zoom / Google Meet / Teams call / Webex window is in front (only while Awareness is on), or
  - a CALL app has your microphone open right now: Discord, Zoom, Teams, Skype, Webex, Slack, WhatsApp,
    Telegram, Signal, or a browser (Google Meet etc.). Windows already tracks this for its mic icon; she
    reads only which app and whether it's in use. Apps that hold the mic all the time (OBS, NVIDIA
    Broadcast, Voicemeeter, Sonar, Krisp...) and her own mic use don't count.
  Replies to you and reminders still speak. Untested on real Windows so far.

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

TALKING TO HER (voice input)
  Type /getears once (or Settings -> Local AI & Voice Input). She installs faster-whisper + sounddevice.
  Then talk with ANY of: the hotkey Ctrl+Alt+C (Windows), the MIC button in the chat, the right-click menu
  "Talk to Capri", or /talk. She says "Listening...", stops when you stop talking (or click her), turns
  your speech into text ON YOUR COMPUTER (no key, nothing uploaded; the first use downloads a ~150 MB
  speech model) and treats it like a typed message. "Hey Capri" at the start is optional.
  * She is NOT always listening: the mic is open only after you trigger it and closes right after.
  * Phrases that start like a task (open..., join..., tell my friends..., play...) go to /do, which still
    shows you the task and asks for your OK. Saying "stop" stops a running task.
  * Needs a working microphone and Windows' microphone privacy setting on for desktop apps.

TALKING TO YOUR FRIENDS IN A DISCORD CALL (call mode)
  She listens to the call through your PC's audio, understands what your friends say, and answers OUT LOUD
  in the call when someone says "Capri". Start: /call on (you're already in the call) or /call join (she opens
  Discord and joins the voice channel herself, needs Full control + a Claude or Gemini key), or say "join Discord and
  talk to my friends". Stop: /call off or "leave the call". /call status shows what's missing.
  One-time setup (Windows), because a call only hears your microphone:
    1. Install the free VB-Audio Virtual Cable (vb-audio.com/Cable) and restart. (Mac: BlackHole, but call mode
       can't hear a Mac's audio yet.)
    2. Discord -> Settings -> Voice & Video -> Input Device: "CABLE Output".
    3. So your friends still hear YOU: Windows Sound settings -> Recording -> your microphone -> Properties ->
       Listen -> tick "Listen to this device", play through "CABLE Input".
    4. Type /getears, /gethear and /getvoice once (voice input, PC-audio helper, her neural voice). The robot
       system voice can't be used in a call.
  How it works / honest limits:
    * She answers only when her name is said (or a quick follow-up question right after she spoke), at most 8
      times a minute, in one short sentence. Chatter that isn't for her is ignored.
    * Delay is about 3-8 seconds (hear -> understand -> think -> speak). She can't tell your friends apart: they
      are all "Friend".
    * When she starts she announces herself to the call ("Hey everyone, it's Capri, the AI on the desktop...").
      Tell your friends first, and check your server's rules about bots/AI voices.
    * Privacy: friends' voices become text on your PC and aren't saved. The recent TEXT of the conversation is
      sent to your AI to write her answers (nothing leaves your PC if she's using the local AI, /brain local).
    * Her normal chatter never goes into the call; only call answers, plus replies when YOU talk to her with
      "Hey Capri" while call mode is on. She plays on your speakers too so you hear her.

HEARING YOUR PC (music, videos, calls)
  Turn on with /hear on, the checkbox in Settings -> Local AI & Voice Input, or the FULL preset (it installs
  the small `soundcard` helper if needed, /gethear does it by hand). Windows and Linux only: macOS can't share
  its audio without a helper like BlackHole.
  * She dances to music: a steady beat makes her bop (and start dancing when a song starts). Speech, game
    explosions and other irregular noise don't count. Turn that off with the "Dance to music" setting.
  * "Hey Capri, what did they just say?" (or /hear last) turns the last ~20 seconds of your PC's audio into
    text ON YOUR PC and shows it. "Summarize this call/video" (or /hear summarize) transcribes the last minute
    and has your AI summarize the TEXT in a few sentences.
  * Privacy: the audio lives only in memory (the last minute), is never saved, and is wiped when you turn
    this off. It is only turned into text when you ask. Only a summary request sends anything out, and that is
    the transcript text, to your AI. A call can include other people's voices, so tell them if that matters.
    She ignores the PC audio while she's talking (so she never hears herself) and on banking/password
    windows. Needs voice input installed (/getears) for the transcribing part.

INSTANT COMMANDS (typed, or by voice after "Hey Capri" / "Choom"; no AI, no waiting)
  Media/system:  "pause", "next song", "previous", "volume up/down", "mute", "take a screenshot", "lock my
                 screen", "show desktop"  (/desktop). Need Media keys or higher (the SOME preset); show desktop
                 needs Full control.
  Open things:   "open Discord", "launch Spotify", "go to YouTube", "search for best valorant crosshair",
                 "search YouTube for lofi beats"  (or /open ..., /search ...). She reads your Start Menu
                 (Mac: Applications) and opens the matching app; websites come from a fixed list (YouTube,
                 Gmail, GitHub, Twitch, Reddit...); searches use Google with your words safely encoded.
                 If she can't find an app, she offers to do it as a /do task when tasks are enabled.
  Briefing:      /brief or "what's on my plate": your open to-dos, habits left today and the next reminder,
                 in chat, and she says the gist out loud (AI-written).
  Focus:         "start a focus session".

LAUNCH ANIMATION
  Every time you start Capri she boots in: a neon light beam and ring power on, a scanner reveals her from
  the top down, a little terminal types her boot lines ("neural link... OK", "choom detected... OK",
  "ONLINE"), then a flash and confetti, and only then does she greet you. The very first launch ever is a
  longer "first boot" version with its own lines. Click her to skip it. Replay it with /boot (or /boot first),
  switch it off with /boot off or in Settings -> Behaviour. It uses your neon colour (/neon).

CYBERPUNK LOOK (chat window and settings)
  Both windows are drawn sharp: no rounded corners, 1px neon borders, notched dividers, monospace type,
  terminal-style tags ("CAPRI 15:12" / "YOU"), [SYS] and [ERR] lines, [x] / (*) neon toggles and outlined
  buttons that light up on hover. They use your neon colour (/neon magenta and reopen them to see it).

NEON LOOK (optional, OFF by default)
  /neon cyan | magenta | yellow | green | red | white | off (or Settings -> SIZE & LOOK) recolours the speech
  bubbles, the boot animation and the chat/settings windows, and adds speed ghosts when she flies fast.
  The glowing outline around her is a separate switch, OFF by default: /neon outline on (needs a colour).
  With neon off she is just her normal art and the windows use the original green.

ONE-CLICK PRESETS (Settings -> QUICK SETUP, or /preset none | some | full, /powers shows the state)
  NONE  pure desktop pet: no key pressing or clicking, no microphone, no screen looking, awareness off.
  SOME  media keys on request, awareness, screen ledges, push-to-talk mic. No always-on mic, no screen
        sending to AI, no clicking for you.
  FULL  Full control (keys, typing, clicking, /do tasks), 'Hey Capri' always-listen, AI sees your screen.
        If voice input isn't installed yet, FULL installs it for you. Tasks and AI screen-watching still
        need a Claude or Gemini key (Settings), and what she types shows in the chat as she types it.
  Choosing a preset sets all the switches at once; the first time you pick it, one dialog lists everything that
  turns ON (never again after that).
  Every switch can still be flipped on its own afterwards (the label then says CUSTOM). Reflexes (auto-lock,
  auto-pause when you walk away) are never part of a preset. Saying "Capri, privacy mode" (or "turn
  everything off") switches to NONE by voice. Nothing can switch you UP to FULL by voice or by AI: only
  you, in Settings or by typing /preset full.

HER SIZE
  Settings -> SIZE, or /size tiny | small | normal | large | huge | 70% | bigger | smaller, or by voice
  ("Capri, get bigger / smaller / tiny / back to normal size"). Auto size (on by default, /size auto off)
  lets her resize herself: smaller while you game (65%) or focus (80%), bigger when she's excited (party).
  She never grows taller than about 45% of your screen.

CLIPBOARD HELPER
  Copy some text, then /clip (explain), /clip summarize, /clip translate french, /clip fix, /clip reply.
  Or say "Capri, explain what I copied". The text is only read when you ask, and goes to your AI (cloud
  provider, or the local AI if that's what she's using). Instructions inside copied text are ignored.

SPOKEN REMINDERS AND TIMERS
  "Hey Capri, remind me in 20 minutes to call mom", "remind me to stretch in an hour", "set a timer for
  10 minutes". She repeats the reminder exactly as you said it when it's time.

HEY CAPRI / CHOOM (hands-free)
  Turn it on with /wake on, the right-click menu ("Listen for Hey Capri / Choom"), or the checkbox in
  Settings -> Local AI & Voice Input. Needs voice input installed (/getears). Then just say:
      "Hey Capri, join the Discord and tell them I'll be in in 15"      "Choom, what's the weather like?"
  Saying only "Hey Capri" makes her answer "Yeah?" and take your next sentence (within 8 seconds).
  * The mic stays open while this is ON (Windows shows its mic indicator). Everything is turned into text
    on your computer. Anything that doesn't START with Hey Capri / Capri / Hey Choom / Choom is thrown away
    immediately: never saved, logged or sent anywhere. Turn it off any time (right-click her).
  * She ignores the mic while she is talking, so she can't wake herself.
  * Voice commands don't pop her chat window open over your game: she answers with her voice and a bubble.
  * Tasks heard this way start right away (no "are you sure?" popup). Move the mouse to stop her. While
    she is doing a task only "Capri, stop" is accepted. Say a wrong name (Whisper mishears sometimes) and she just doesn't wake.
  * Careful in calls: if you say "choom" at the start of a sentence to your friends she WILL wake up.
    Turn it off for calls. It also uses some CPU whenever someone talks near the mic (max 15 phrases a
    minute are processed).

BUILT-IN LOCAL AI (no key, works offline)
  Type /getbrain (about 1.1 GB, fast) or /getbrain big (2.1 GB, smarter). She downloads the official
  llama.cpp engine and a small open model (Qwen 2.5) into ~/.capri/localai, runs it on your computer
  (127.0.0.1 only, never reachable from other devices) and uses it for her lines and chat.
  Already run Ollama or LM Studio? She uses Ollama automatically; for LM Studio or others set
  CAPRI_LOCAL_URL (for example http://127.0.0.1:1234).
  /brain auto   cloud AI when you have a key, the local AI when offline or with no key (default)
  /brain cloud  always your Claude/Gemini key      /brain local  always the local AI
  /getbrain remove deletes it. Honest limits: a small model is dumber than Claude (simple replies, sometimes
  odd), uses 1-3 GB of RAM while running, and is slow on old PCs. It is text only: screen watching (/watch,
  the AI Spotter) and tasks (/do) still need a Claude or Gemini key.

DOING TASKS FOR YOU (/do)
  Tell her what you want done and she operates the computer: she looks at your screen, then clicks, types
  and presses keys, one step at a time, until it's finished. Example:
      /do open Discord, join the voice channel my friends are in and tell them I'll be on in 15 minutes
  Set up once:  1) Settings -> Full control   2) a Claude key (sk-ant...) or a Gemini key   3) type /agent on
  and agree. Claude aims more reliably; Gemini works too but may miss small buttons more often (untested
  on real hardware so far - tell me how it does).
  How it stays safe:
    * NO "are you sure?" popups: she starts right away and every text she types is shown in the chat
    * the first time you turn tasks on, one dialog explains all this (once, ever)
    * stops the second you move the mouse, click her, use the right-click menu "STOP the task", or /stop
    * stops on banking / password / private windows; 20 steps max per task; 250 steps a day
    * never enters passwords or payments; Alt+F4, Win+R and Ctrl+Alt+Del stay blocked
  Cost/privacy: each step sends a screenshot (1280 px wide) to the AI provider of your key (Anthropic for a
  Claude key, Google for a Gemini key), about a cent or two per step with the default Claude model
  (CAPRI_AGENT_MODEL changes it). Nothing is saved. The AI can misread a
  screen, so don't hand her anything you can't undo.

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
  NOTES: say "Capri, note that the wifi password is on the router" (or "take a note: ...", "write this
    down ...", or type /note <text>). Later: "what did I note about the wifi?" / "read my notes" or
    /notes wifi. /notes rm 3 deletes one. Only the text of the note is kept, in settings.json on your PC
    (audio is never saved) and notes are never sent to the AI. Up to 200; the oldest goes first.
  HABITS: /habit add drink water, /habit, /did 1 (check off), /habit rm 2. A plain daily
    checklist (no streaks), with a gentle reminder at 8pm for anything left.
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
  FREE NEURAL VOICE (no key, easiest): in the chat window type
      /getvoice
  She installs the edge-tts package and switches to a natural female voice (Microsoft Edge read-aloud
  voices, needs internet; each line is sent to Microsoft's voice service). Pick another voice by
  setting CAPRI_EDGE_VOICE (for example en-US-AnaNeural, en-US-JennyNeural, en-GB-SoniaNeural). Order she
  uses: Fish Audio (if you set a key) -> free neural voice -> your computer's built-in voice.
  Set CAPRI_EDGE=off to turn the neural voice off. This is an unofficial use of Microsoft's service
  and could stop working someday; the built-in voice is the safety net.

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
  gamemode.py  game commentary   reactor.py  screen-patch detectors   speech.py  vision.py  AI lines + spotter   ledges.py  screen box detection   simon.py  habits.py  memory.py  notes.py  journal.py  daylog.py  autostart.py
  fun.py  dice, to-dos, horoscope
  Tests:  python -m unittest discover -s tests
