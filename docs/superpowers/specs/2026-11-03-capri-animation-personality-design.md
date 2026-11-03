# Capri: animation + personality upgrade

## Intent
Capri is a Tkinter desktop pet shared with friends via a zip. Today she has one static
pose that is rotated/squashed/glitched, one persona prompt and a handful of random lines.
Goal: make her feel alive (real animation), give her personality (moods, memory, context),
and make first-run painless for friends (no file editing, works without an API key).

Priorities (from the owner): 1) looks & animation, 2) personality & behaviour.
Audience: friends / small group. Owner can't draw; art must come from the existing sprites.

## Non-goals
Redesigning her look, new art from the internet (licensing, identity), a web/mobile port.

## Design
### 1. `rig.py` - procedural puppet animation (PIL only, no Tk)
- Input: `idle.png`. Detect eyes (blue pixels) and mouth (white run below the eyes);
  fall back to height ratios when detection fails.
- Each frame is built by a per-row displacement field over the source rows:
  vertical lift (breathing/bob), jaw drop (talking), global stretch (jump/startle),
  horizontal sway (head), lean and leg shear (walk/dance). No gaps, crisp pixels.
- Blink / closed eyes by painting over detected eye boxes (separate cached source).
- Animations: idle, walk, wave/dance, jump, startle, wait/think, fail, talk, sleep, lounge.
- Frames are quantised and cached by key. A Petdex spritesheet (`pet/` or
  `~/.codex/pets/capri`) still overrides the rig exactly as before.

### 2. `personality.py` - mood, memory, lines (pure logic, no Tk)
- Mood derived from energy (time of day + recent activity), affection (pokes/chats,
  decays when ignored) and boredom. Moods: sleepy, playful, content, sassy, lonely.
- Mood biases `choose_next` weights and selects line pools; greetings depend on time of
  day and time since last seen; persisted in `~/.capri/settings.json`.
- Dynamic context (mood, time, what she is doing, user's name) is appended to the LLM
  system prompt so chat replies match her state. `/name <x>` stores the user's name.
- Offline replies from line pools when no API key is set, so friends can still play.

### 3. Friend-friendly setup
- First chat with no key shows an in-window key box; saves to `~/.capri/api_key.txt`.
- `api_key.txt` is git-ignored; `api_key.example.txt` is the template.

## Testing
- `tests/` (stdlib `unittest`): rig geometry/frames/caching/eye+mouth detection,
  personality mood/lines/greetings/offline replies.
- Headless smoke test of the real app under Xvfb with a screenshot.

## Update: Petdex art replaces the sprite rig
The owner supplied the real animated Petdex Capri (8x11 sheet + pet.json). It is now bundled in
`pet/` and is the only art. The original `sprites/` and the procedural `rig.py` (written to animate
them) were removed. A tiny placeholder is shown only if the sheet is missing or unreadable. The
sheet loader slices by fractional cell size so scaled exports (1343x2000) are not clipped.
The two extra 8-frame rows at the bottom of the sheet are not used yet (names unknown).
