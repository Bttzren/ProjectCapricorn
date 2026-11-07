import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.root.update()
p.open_chat(); c = p.chat
c.win.geometry("420x640+10+10")
c.add_bubble("assistant", "Hey. I'm here. Type something, or tap a button below.", animate=False)
c.add_bubble("user", "what's on my plate today?", animate=False)
c.add_bubble("assistant", "Two to-dos and a reminder in 25 min. Don't ghost the homework, choom.", animate=False)
c.system_line("To-dos (2): finish homework, call mom")
c.system_line("Couldn't reach the AI: no key.", err=True)
c.win.update(); time.sleep(0.4); c.win.update()
ImageGrab.grab(bbox=(10, 10, 430, 650)).save("/tmp/ui_chat.png")
c.win.withdraw()
p.open_settings(); w = p.settings_win.win
w.geometry("470x1250+10+10"); w.update(); time.sleep(0.4); w.update()
import sys as _s
ImageGrab.grab(bbox=(10, 10, 480, 1260)).save("/tmp/ui_settings.png")
print("ok")
p.settings_win.canvas.yview_moveto(0.55); w.update(); time.sleep(0.3); w.update()
ImageGrab.grab(bbox=(10, 10, 480, 1260)).save("/tmp/ui_settings2.png")
p.settings_win.canvas.yview_moveto(1.0); w.update(); time.sleep(0.3); w.update()
ImageGrab.grab(bbox=(10, 10, 480, 1260)).save("/tmp/ui_settings3.png")
w.geometry("470x1250+10+10"); p.settings_win.canvas.yview_moveto(0.0); w.update(); time.sleep(0.3); w.update()
ImageGrab.grab(bbox=(10, 10, 480, 640)).save("/tmp/ui_settings_top.png")
