# 29: /do with a Gemini key — ready check passes, request goes to Gemini with pixel note + room for thinking
import os, sys, tempfile, json
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda: "AIzaFAKEKEY0123456789"
sent = []
def fake_http(req, timeout=25):
    sent.append((req.full_url, json.loads(req.data)))
    return {"candidates": [{"content": {"parts": [{"text": '{"action": "done", "summary": "ok"}'}]}}]}
capri.http_json = fake_http
p = capri.Capri(); p.boot = None
print("provider:", capri.detect_provider(capri.read_api_key()))
p.hands.level = "full"; p.settings["agent"] = True
print("ready:", p.agent_ready())
out = p._agent_ask("image/jpeg", "AAAA", "SYSTEM RULES.", "next?")
url, body = sent[-1]
print("reply:", out)
print("url:", url.split("/models/")[1])
print("tokens:", body["generationConfig"]["maxOutputTokens"], "| pixel note:", "PIXELS" in body["systemInstruction"]["parts"][0]["text"])
capri.read_api_key = lambda: "sk-ant-x"
capri.http_json = lambda req, timeout=25: sent.append((req.full_url, json.loads(req.data))) or {"content": [{"type": "text", "text": "{}"}]}
p._agent_ask("image/jpeg", "AAAA", "SYSTEM RULES.", "next?")
print("claude model:", sent[-1][1]["model"], "| tokens:", sent[-1][1]["max_tokens"], "| note leaked:", "PIXELS" in sent[-1][1]["system"])
print("ok")
