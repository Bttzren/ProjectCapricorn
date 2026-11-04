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
  Tests:  python -m unittest discover -s tests
