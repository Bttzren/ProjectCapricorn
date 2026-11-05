"""The daily briefing: what's on your plate right now (pure logic, no Tk)."""


def build(todos, habits_pending, reminders, now, timer=None):
    """(lines, one_sentence_facts).

    todos: list of open to-do texts. habits_pending: habit names not done today. reminders: [(due_time, text)].
    timer: None or ('focus', seconds_left). Returns the chat lines and a compact fact string for the AI."""
    lines, facts = [], []
    if todos:
        shown = ", ".join(todos[:3]) + (f" (+{len(todos) - 3} more)" if len(todos) > 3 else "")
        lines.append(f"To-dos ({len(todos)}): {shown}")
        facts.append(f"{len(todos)} open to-dos ({', '.join(todos[:3])})")
    if habits_pending:
        lines.append("Habits left today: " + ", ".join(habits_pending[:5]))
        facts.append("habits not done yet today: " + ", ".join(habits_pending[:5]))
    upcoming = sorted((t, x) for t, x in reminders if t > now)
    if upcoming:
        mins = max(1, int((upcoming[0][0] - now) / 60))
        when = f"{mins} min" if mins < 90 else f"{mins // 60} h"
        more = f" (+{len(upcoming) - 1} more)" if len(upcoming) > 1 else ""
        lines.append(f"Next reminder in {when}: {upcoming[0][1]}{more}")
        facts.append(f"next reminder in {when}: {upcoming[0][1]}")
    if timer and timer[1] > 0:
        lines.append(f"{timer[0].title()} timer: {int(timer[1] // 60)} min left")
        facts.append(f"a {timer[0]} timer with {int(timer[1] // 60)} minutes left")
    if not lines:
        lines.append("Nothing on your plate. Nova.")
        facts.append("nothing is pending: no to-dos, habits or reminders")
    return lines, "; ".join(facts)


def fallback(lines):
    """A short sentence made from the lines, for when the AI isn't available."""
    return lines[0] if len(lines) == 1 else f"{lines[0]}. And {len(lines) - 1} more thing(s) in chat."
