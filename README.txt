CAPRI - desktop companion

RUN
  Windows: double-click 1_RUN_Capri_Windows.bat   (needs Python 3.9+ from python.org)
  Mac:     double-click 1_RUN_Capri_Mac.command   (first time: right-click > Open)
  Linux:   ./run_linux.sh   (needs python3-tk)
  Real .exe: run 2_BUILD_exe_Windows.bat -> dist\Capri.exe

WHAT SHE DOES
  Roams, lounges, naps, dances, glitch-teleports, gets curious about your cursor,
  startles if you swipe at her, and gets annoyed if you spam-click.
  On Windows she can perch on the top edge of your active window (and always on the
  chat window). Drag to pick her up, fling to throw her, she bounces and lands.
  Click: poke. Double-click: chat. Right-click (Ctrl-click Mac): menu
  (focus timer, reminders, teleport, dance, lounge, nap, calm mode, check-ins).

CHAT
  Paste a Claude key (sk-ant...) or a Gemini key into api_key.txt. Auto-detected.
  Enter sends, Shift+Enter = new line. Click a bubble to copy it. History is saved.
  Slash commands: /help /focus [min] /remind <min> <text> /tp /dance /sleep /calm /clear
  Edit personality: create persona.txt next to capri.py with your own instructions.

PETDEX / CODEX PET (optional, animated)
  Run on your own computer:  npx petdex install capri
  If it lands in ~/.codex/pets/capri, Capri uses its animated sheet automatically
  (or copy the files into a folder named "pet" next to capri.py).
  Preview what she found:  python capri.py --pet-preview
  If animations look mismatched, add pet_map.json next to capri.py, e.g.
  {"idle":0,"running-right":1,"running-left":2,"waving":3,"jumping":4,"failed":5,"waiting":6,"running":7}

FILES she writes: ~/.capri/ (settings, chat history, capri.log for errors)
Linux has no real transparency (dark box). Perching on other apps' windows is Windows-only.
