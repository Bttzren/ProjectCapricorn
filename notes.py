"""Quick notes you tell Capri (typed or spoken), found again by keyword. Pure logic, no Tk.

Only the TEXT of a note you deliberately dictate or type is kept, in the list you pass in (settings.json, on
your PC). Audio is never saved. Notes are not sent to the AI.
"""
import re

MAX_NOTES = 200
MAX_LEN = 500

STOP = {"a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "about", "with", "my", "me", "i", "is", "it",
        "that", "this", "at", "be", "was", "what", "did", "do", "any", "note", "notes", "from", "by", "up"}


def words(text):
    return [w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if w not in STOP]


def _stem(w):
    for suf in ("'s", "ing", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


class Notes:
    def __init__(self, items):
        self.items = items

    def add(self, text, ts=""):
        text = " ".join((text or "").split()).strip(" ,:;-")[:MAX_LEN]
        if not text:
            return None
        if any(n["text"].lower() == text.lower() for n in self.items):
            return None
        if len(self.items) >= MAX_NOTES:
            self.items.pop(0)                                    # oldest goes
        self.items.append({"text": text, "ts": ts})
        return text

    def remove(self, number):
        if not (1 <= number <= len(self.items)):
            return None
        return self.items.pop(number - 1)["text"]

    def find(self, query, limit=5):
        """Notes matching `query`, best first (newest wins ties). Empty query: the newest notes.
        Returns [(number, note)] with 1-based numbers you can pass to remove()."""
        numbered = list(enumerate(self.items, 1))
        q = {_stem(w) for w in words(query)}
        if not q:
            return list(reversed(numbered))[:limit]
        scored = []
        for n, note in numbered:
            have = {_stem(w) for w in words(note["text"])}
            hits = len(q & have)
            if hits:
                scored.append((hits, n, note))
        scored.sort(key=lambda s: (-s[0], -s[1]))
        return [(n, note) for _h, n, note in scored[:limit]]

    @staticmethod
    def line(number, note):
        return f"{number}. {note['text']}" + (f"  ({note['ts']})" if note.get("ts") else "")

    def lines(self, query=""):
        if not self.items:
            return ["No notes yet. Say 'Capri, note that the wifi password is on the router' or type /note <text>."]
        found = self.find(query, limit=10)
        if not found:
            return [f"Nothing in your notes about '{query}'."]
        return [self.line(n, note) for n, note in found]

    def spoken(self, query=""):
        """One short sentence to say out loud for a spoken 'what did I note about ...'."""
        if not self.items:
            return "You haven't told me any notes yet."
        found = self.find(query, limit=3)
        if not found:
            return f"Nothing in your notes about {query}." if query else "No notes."
        first = found[0][1]["text"].rstrip(".!?")
        more = len(found) - 1
        return f"You noted: {first}." + (f" And {more} more, type /notes to see them." if more else "")
