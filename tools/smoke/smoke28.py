# 28: quiet during calls — fake "Discord has the mic", check calm/speech, then call ends; manual calm respected
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, meeting
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.root.update()
spoken = []
p.speaker.speak = lambda text, priority=False: spoken.append((text, priority)) or True
mic = [[]]
meeting.read_mic_entries = lambda: mic[0]
print("calm before:", p.calm)
mic[0] = [(r"C:#Discord#Discord.exe", 5, 0)]
p.meeting_tick(100.0); print("in call -> calm:", p.calm, "| bubble:", p.bubble, "| why:", p.meeting.why)
p.speak("ambient chatter"); p.speak("reply to you", priority=True)
print("spoken during call:", spoken)
mic[0] = []
p.meeting_tick(120.0); print("20s after hang-up calm:", p.calm)
p.meeting_tick(150.0); print("50s after hang-up calm:", p.calm)
mic[0] = [(r"C:#Zoom#Zoom.exe", 5, 0)]
p.meeting_tick(200.0); p.toggle_calm(); p.toggle_calm()        # user turns calm off and on by hand
mic[0] = []; p.meeting_tick(300.0); print("manual calm kept after call:", p.calm)
p.settings["meeting_quiet"] = False; mic[0] = [(r"C:#Discord#Discord.exe", 5, 0)]; p.calm = False
p.meeting_tick(400.0); print("setting off -> calm:", p.calm)
print("ok")
