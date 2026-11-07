import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import listen  # noqa: E402
import notes  # noqa: E402


class NotesTests(unittest.TestCase):
    def test_add_dedupe_trim_and_limit(self):
        n = notes.Notes([])
        self.assertEqual(n.add("  wifi  password is on the router. ", "11-07 14:00"),
                         "wifi password is on the router.")
        self.assertIsNone(n.add("WIFI PASSWORD IS ON THE ROUTER."))
        self.assertIsNone(n.add("   "))
        self.assertLessEqual(len(n.add("x" * 900)), notes.MAX_LEN)
        for i in range(notes.MAX_NOTES + 5):
            n.add(f"note {i}")
        self.assertEqual(len(n.items), notes.MAX_NOTES)
        self.assertEqual(n.items[-1]["text"], f"note {notes.MAX_NOTES + 4}")      # newest kept

    def test_find_by_keyword_best_and_newest_first(self):
        n = notes.Notes([])
        n.add("dentist on friday at 3")
        n.add("wifi password is on the router")
        n.add("bring the router back to the store friday")
        found = n.find("router")
        self.assertEqual([num for num, _ in found], [3, 2])                    # both match, newest first
        self.assertEqual(n.find("friday dentist")[0][0], 1)                    # 2 words beat 1
        self.assertEqual(n.find("passwords")[0][0], 2)                         # simple plural stemming
        self.assertEqual(n.find("pizza"), [])
        self.assertEqual([num for num, _ in n.find("")], [3, 2, 1])            # no query: newest

    def test_lines_spoken_and_remove(self):
        n = notes.Notes([])
        self.assertIn("No notes yet", n.lines()[0])
        self.assertIn("haven't", n.spoken("x"))
        n.add("locker code 1234", "11-07 09:00")
        n.add("locker is number 88")
        self.assertEqual(n.lines("code"), ["1. locker code 1234  (11-07 09:00)"])
        self.assertIn("Nothing in your notes", n.lines("pizza")[0])
        self.assertTrue(n.spoken("locker").startswith("You noted: locker is number 88"))
        self.assertIn("1 more, type /notes", n.spoken("locker"))
        self.assertEqual(n.remove(1), "locker code 1234")
        self.assertIsNone(n.remove(5))


class NoteIntentTests(unittest.TestCase):
    def test_taking_notes(self):
        i = listen.intent
        self.assertEqual(i("Hey Capri, note that the wifi password is on the router."),
                         ("note", "the wifi password is on the router"))
        self.assertEqual(i("take a note: dentist friday at 3"), ("note", "dentist friday at 3"))
        self.assertEqual(i("Capri make a note of my locker code 1234"), ("note", "my locker code 1234"))
        self.assertEqual(i("note to self buy milk"), ("note", "buy milk"))
        self.assertEqual(i("write this down, the essay is due monday"), ("note", "the essay is due monday"))
        self.assertEqual(i("jot down call grandma sunday"), ("note", "call grandma sunday"))
        self.assertEqual(i("take a note"), ("note", ""))

    def test_finding_notes(self):
        i = listen.intent
        self.assertEqual(i("what did I note about the wifi?"), ("notes", "the wifi"))
        self.assertEqual(i("Hey Capri, what did I write down about the dentist"), ("notes", "the dentist"))
        self.assertEqual(i("read my notes"), ("notes", ""))
        self.assertEqual(i("do I have any notes about my locker"), ("notes", "my locker"))
        self.assertEqual(i("what are my notes"), ("notes", ""))
        self.assertEqual(i("search my notes for router"), ("notes", "router"))

    def test_existing_phrases_are_not_stolen(self):
        i = listen.intent
        self.assertEqual(i("open notepad")[0], "launch")
        self.assertEqual(i("remind me in 20 minutes to call mom")[0], "remind")
        self.assertEqual(i("set a timer for 10 minutes")[0], "remind")
        self.assertEqual(i("what's on my plate today")[0], "brief")
        self.assertEqual(i("what did they just say")[0], "hear")
        self.assertEqual(i("join the discord and tell them I'll be late")[0], "task")
        self.assertEqual(i("tell me a joke")[0], "chat")
        self.assertEqual(i("I noticed something weird")[0], "chat")
        self.assertEqual(i("notes are boring")[0], "chat")
        self.assertEqual(i("remember that I like pizza")[0], "chat")
        self.assertEqual(i("pause the music")[0], "control")


if __name__ == "__main__":
    unittest.main()
