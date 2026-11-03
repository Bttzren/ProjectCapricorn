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

PERSONALITY
  She has moods: sleepy, lonely, sassy, playful, content. Her mood depends on the time of day,
  how much you interact with her (affection), and whether you annoyed her. Mood changes what she
  does (a sleepy Capri naps, a playful one dances and teleports, a lonely one follows your cursor),
  what she says, and how she answers in chat. She greets you by time of day, notices if you were
  away for hours, and remembers your name (/name <you>). Affection is kept between runs.

CHAT
  Works right away in offline mode (canned, mood-based replies). For real AI chat, double-click her,
  paste a Claude key (sk-ant...) or a Gemini key into the box at the top of the chat window and press
  SAVE KEY. It is stored in ~/.capri/api_key.txt. (You can also use /key <key>, an environment
  variable, or copy api_key.example.txt to api_key.txt next to capri.py.)
  Enter sends, Shift+Enter = new line. Click a bubble to copy it. History is saved.
  Slash commands: /help /focus [min] /remind <min> <text> /name <you> /mood /key <key> /tp /dance /sleep /calm /clear
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
  personality.py  moods, memory, lines (no Tk)
  Tests:  python -m unittest discover -s tests
