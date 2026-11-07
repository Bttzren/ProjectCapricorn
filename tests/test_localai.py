import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
import urllib.error
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import localai as L  # noqa: E402

FAKE_SERVER = textwrap.dedent('''
    import json, sys
    from http.server import BaseHTTPRequestHandler, HTTPServer
    port = int(sys.argv[sys.argv.index("--port") + 1])
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            self.send_response(200 if self.path == "/health" else 404); self.end_headers(); self.wfile.write(b"{}")
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n))
            last = body["messages"][-1]["content"]
            if isinstance(last, list):                      # an image request
                img = [p for p in last if p.get("type") == "image_url"]
                txt = [p["text"] for p in last if p.get("type") == "text"]
                last = ("IMAGE " if img and img[0]["image_url"]["url"].startswith("data:image/") else "") + " ".join(txt)
                if "--mmproj" not in sys.argv:
                    last = "NO-PROJECTOR " + last
            out = json.dumps({"choices": [{"message": {"content": "echo: " + last}}]}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(out)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
''')


class Resp:
    def __init__(self, data, status=200, length=True):
        self.buf, self.status = io.BytesIO(data), status
        self.headers = {"Content-Length": str(len(data))} if length else {}

    def read(self, n=-1):
        return self.buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def asset(name):
    return {"name": name, "browser_download_url": L.ASSET_PREFIX + "b1/" + name}


class AssetTests(unittest.TestCase):
    ASSETS = [asset(n) for n in (
        "llama-b1-bin-win-cuda-12.4-x64.zip", "llama-b1-bin-win-vulkan-x64.zip", "llama-b1-bin-win-cpu-x64.zip",
        "llama-b1-bin-win-cpu-arm64.zip", "llama-b1-bin-macos-arm64.tar.gz", "llama-b1-bin-macos-x64.tar.gz",
        "llama-b1-bin-ubuntu-x64.tar.gz", "llama-b1-bin-ubuntu-vulkan-x64.tar.gz", "cudart-llama-bin-win-cuda-12.4-x64.zip")]

    def test_picks_cpu_build_per_platform(self):
        self.assertEqual(L.pick_asset(self.ASSETS, "win32", "AMD64")[0], "llama-b1-bin-win-cpu-x64.zip")
        self.assertEqual(L.pick_asset(self.ASSETS, "win32", "ARM64")[0], "llama-b1-bin-win-cpu-arm64.zip")
        self.assertEqual(L.pick_asset(self.ASSETS, "darwin", "arm64")[0], "llama-b1-bin-macos-arm64.tar.gz")
        self.assertEqual(L.pick_asset(self.ASSETS, "linux", "x86_64")[0], "llama-b1-bin-ubuntu-x64.tar.gz")

    def test_old_avx2_name_and_foreign_urls(self):
        self.assertEqual(L.pick_asset([asset("llama-b1-bin-win-avx2-x64.zip")], "win32", "AMD64")[0],
                         "llama-b1-bin-win-avx2-x64.zip")
        evil = [{"name": "llama-b1-bin-win-cpu-x64.zip", "browser_download_url": "https://evil.example/x.zip"}]
        self.assertIsNone(L.pick_asset(evil, "win32", "AMD64"))
        self.assertIsNone(L.pick_asset([], "win32", "AMD64"))


class ExtractTests(unittest.TestCase):
    def test_zip_slip_refused(self):
        d = tempfile.mkdtemp()
        z = os.path.join(d, "a.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("../evil.txt", "x")
        with self.assertRaises(RuntimeError):
            L.safe_extract(z, os.path.join(d, "out"))
        self.assertFalse(os.path.exists(os.path.join(d, "evil.txt")))

    def test_extract_and_find_server(self):
        d = tempfile.mkdtemp()
        z = os.path.join(d, "a.zip")
        exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("build/bin/" + exe, "bin")
            f.writestr("build/bin/ggml.dll", "x")
        L.safe_extract(z, os.path.join(d, "out"))
        self.assertTrue(L.find_server(os.path.join(d, "out")).endswith(exe))


class DownloadTests(unittest.TestCase):
    def test_download_progress_and_atomic(self):
        d = tempfile.mkdtemp()
        data = b"x" * 5000
        seen = []
        out = L.download("https://h/x", os.path.join(d, "m.bin"), lambda a, b: seen.append((a, b)),
                         lambda req, timeout: Resp(data), chunk=1000)
        self.assertEqual(os.path.getsize(out), 5000)
        self.assertEqual(seen[-1], (5000, 5000))
        self.assertFalse(os.path.exists(out + ".part"))

    def test_resume_and_restart(self):
        d = tempfile.mkdtemp()
        dest = os.path.join(d, "m.bin")
        open(dest + ".part", "wb").write(b"a" * 2000)
        got = {}

        def op(req, timeout):
            got["range"] = req.headers.get("Range")
            return Resp(b"b" * 3000, status=206)
        L.download("https://h/x", dest, opener=op)
        self.assertEqual(got["range"], "bytes=2000-")
        self.assertEqual(open(dest, "rb").read(), b"a" * 2000 + b"b" * 3000)
        open(dest + ".part", "wb").write(b"a" * 2000)
        L.download("https://h/x", dest, opener=lambda r, timeout: Resp(b"c" * 4000, status=200))   # Range ignored
        self.assertEqual(open(dest, "rb").read(), b"c" * 4000)

    def test_refuses_http_and_short_files(self):
        d = tempfile.mkdtemp()
        with self.assertRaises(RuntimeError):
            L.download("http://h/x", os.path.join(d, "a"), opener=lambda r, timeout: Resp(b"x" * 5000))
        with self.assertRaises(RuntimeError):
            L.download("https://h/x", os.path.join(d, "a"), opener=lambda r, timeout: Resp(b"x"), min_bytes=1000)

    def test_cut_off_download_is_not_kept(self):
        d = tempfile.mkdtemp()

        class Short(Resp):
            def __init__(self):
                super().__init__(b"x" * 100)
                self.headers = {"Content-Length": "5000"}
        with self.assertRaises(RuntimeError):
            L.download("https://h/x", os.path.join(d, "a"), opener=lambda r, timeout: Short(), min_bytes=10)
        self.assertFalse(os.path.exists(os.path.join(d, "a")))


class InstallTests(unittest.TestCase):
    def test_full_install_with_fakes(self):
        d = tempfile.mkdtemp()
        exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as f:
            f.writestr(exe, "x" * 200_000)
        release = {"assets": [asset("llama-b1-bin-win-cpu-x64.zip")]}
        msgs = []

        def opener(req, timeout=0):
            url = req if isinstance(req, str) else req.full_url
            return Resp(zbuf.getvalue() if url.endswith(".zip") else b"m" * 10)
        L.MODELS["tiny"] = ("https://h/m.gguf", "m.gguf", 0, "test")
        try:
            ins = L.Install(d, opener=opener, progress=msgs.append, platform="win32", machine="AMD64")
            binary, model = ins.run("tiny", release=release)
        finally:
            del L.MODELS["tiny"]
        self.assertTrue(os.path.isfile(binary))
        self.assertTrue(os.path.isfile(model))
        self.assertTrue(any("AI engine" in m for m in msgs))
        self.assertFalse(os.path.exists(os.path.join(d, "dl", "llama-b1-bin-win-cpu-x64.zip")))

    def test_no_matching_engine_gives_ollama_hint(self):
        ins = L.Install(tempfile.mkdtemp(), platform="win32", machine="AMD64")
        with self.assertRaises(RuntimeError) as cm:
            ins.run("small", release={"assets": []})
        self.assertIn("Ollama", str(cm.exception))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.script = os.path.join(self.d, "fake_server.py")
        open(self.script, "w").write(FAKE_SERVER)
        os.makedirs(os.path.join(self.d, "bin"))
        os.makedirs(os.path.join(self.d, "models"))
        exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
        open(os.path.join(self.d, "bin", exe), "w").write("x")
        open(os.path.join(self.d, "models", L.MODELS["small"][1]), "w").write("m")

    def make(self, **kw):
        ins = L.Install(self.d)
        argv = lambda b, m, port, threads=None: [sys.executable, self.script, "--port", str(port)]   # noqa: E731
        return L.LocalAI(ins, argv_builder=argv, env_url="", start_timeout=20, **kw)

    def test_starts_server_chats_and_stops(self):
        ai = self.make()
        try:
            self.assertEqual(ai.where(), "builtin")
            text = ai.reply([{"role": "user", "content": "hi there"}], "You are Capri.")
            self.assertEqual(text, "echo: hi there")
            self.assertIn("127.0.0.1", ai.base)
            first = ai.proc
            ai.reply([{"role": "user", "content": "again"}], "p")
            self.assertIs(ai.proc, first)                       # reused, not restarted
            self.assertIn("running", ai.status())
        finally:
            ai.stop()
        self.assertIsNone(ai.proc)

    def test_restarts_if_the_server_died(self):
        ai = self.make()
        try:
            ai.reply([{"role": "user", "content": "x"}], "p")
            ai.proc.kill()
            ai.proc.wait()
            self.assertEqual(ai.reply([{"role": "user", "content": "y"}], "p"), "echo: y")
        finally:
            ai.stop()

    def test_nothing_installed(self):
        ai = L.LocalAI(L.Install(tempfile.mkdtemp()), env_url="", opener=lambda *a, **k: (_ for _ in ()).throw(OSError()))
        self.assertEqual(ai.where(), "")
        self.assertFalse(ai.available())
        with self.assertRaises(RuntimeError) as cm:
            ai.reply([{"role": "user", "content": "x"}], "p")
        self.assertIn("/getbrain", str(cm.exception))

    def test_external_url_and_ollama_detection(self):
        ai = L.LocalAI(L.Install(tempfile.mkdtemp()), env_url="http://127.0.0.1:1234")
        self.assertEqual(ai.where(), "url")

        def opener(url, timeout=0):
            u = url if isinstance(url, str) else url.full_url
            if u.endswith("/api/tags"):
                return Resp(json.dumps({"models": [{"name": "llama3.2:3b"}]}).encode())
            raise OSError("no")
        ai2 = L.LocalAI(L.Install(tempfile.mkdtemp()), env_url="", opener=opener)
        self.assertEqual(ai2.where(), "ollama")

    def test_server_exiting_is_reported(self):
        ai = L.LocalAI(L.Install(self.d), argv_builder=lambda b, m, p, t=None: [sys.executable, "-c", "pass"],
                       env_url="", start_timeout=10)
        with self.assertRaises(RuntimeError) as cm:
            ai.start()
        self.assertIn("closed", str(cm.exception))

    def test_argv_binds_to_localhost_only(self):
        a = L.server_argv("/x/llama-server", "/m.gguf", 8123, threads=3)
        self.assertEqual(a[a.index("--host") + 1], "127.0.0.1")
        self.assertEqual(a[a.index("--port") + 1], "8123")


class VisionTests(unittest.TestCase):
    QWEN = ["README.md", "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", "Qwen2.5-VL-3B-Instruct-Q8_0.gguf",
            "Qwen2.5-VL-3B-Instruct-f16.gguf", "mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf",
            "mmproj-Qwen2.5-VL-3B-Instruct-f16.gguf"]
    SMOL = ["SmolVLM2-2.2B-Instruct-Q4_K_M.gguf", "mmproj-SmolVLM2-2.2B-Instruct-f16.gguf", ".gitattributes"]
    GEMMA = ["gemma-3-4b-it-Q4_K_M.gguf", "mmproj-model-f16.gguf"]

    def test_picks_files_in_every_naming_style(self):
        self.assertEqual(L.pick_vision_files(self.QWEN), ("Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
                                                          "mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf"))
        self.assertEqual(L.pick_vision_files(self.SMOL), ("SmolVLM2-2.2B-Instruct-Q4_K_M.gguf",
                                                          "mmproj-SmolVLM2-2.2B-Instruct-f16.gguf"))
        self.assertEqual(L.pick_vision_files(self.GEMMA), ("gemma-3-4b-it-Q4_K_M.gguf", "mmproj-model-f16.gguf"))
        self.assertEqual(L.pick_vision_files(["m-Q8_0.gguf", "big-Q4_K_M-00001-of-00002.gguf", "mmproj-x.gguf"]),
                         ("m-Q8_0.gguf", "mmproj-x.gguf"))                         # split files skipped
        self.assertIsNone(L.pick_vision_files(["only-model-Q4_K_M.gguf"]))         # no projector: can't see
        self.assertIsNone(L.pick_vision_files(["../../evil-Q4_K_M.gguf", "sub/mmproj-a.gguf", "mmproj-b.gguf"]))
        self.assertIn("%20", L.hf_file_url("r/x", "a b.gguf"))

    def test_vision_body_has_the_image(self):
        b = L.vision_body("sys", "image/jpeg", "QUJD", "what?", 100)
        part = b["messages"][-1]["content"]
        self.assertEqual(part[1]["image_url"]["url"], "data:image/jpeg;base64,QUJD")
        self.assertEqual(b["messages"][0], {"role": "system", "content": "sys"})

    def test_vision_install_updates_an_old_engine_and_writes_a_manifest(self):
        d = tempfile.mkdtemp()
        exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
        os.makedirs(os.path.join(d, "bin"))
        open(os.path.join(d, "bin", exe), "w").write("old")                       # an engine without --mmproj
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as f:
            f.writestr(exe, "n" * 200_000)
        release = {"assets": [asset("llama-b1-bin-win-cpu-x64.zip")]}
        urls, msgs = [], []

        def opener(req, timeout=0):
            url = req if isinstance(req, str) else req.full_url
            urls.append(url)
            if url.endswith(".zip"):
                return Resp(zbuf.getvalue())
            if url.startswith(L.HF_API):
                return Resp(json.dumps({"siblings": [{"rfilename": n} for n in self.QWEN]}).encode())
            return Resp(b"g" * 1_200_000)
        ins = L.Install(d, opener=opener, progress=msgs.append, platform="win32", machine="AMD64",
                        check_mmproj=lambda b: open(b).read(3) != "old")
        self.assertFalse(ins.installed("see"))
        ins.run("see", release=release)
        self.assertTrue(ins.installed("see"))
        self.assertTrue(any("too old" in m for m in msgs))
        self.assertTrue(ins.mmproj_path("see").endswith("mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf"))
        self.assertIn(L.HF_HOST + "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", urls)
        self.assertEqual(L.server_argv("b", "m", 1, 2, mmproj="p")[-2:], ["--mmproj", "p"])
        self.assertNotIn("--mmproj", L.server_argv("b", "m", 1, 2))

    def test_local_server_sees_an_image(self):
        d = tempfile.mkdtemp()
        script = os.path.join(d, "fake_server.py")
        open(script, "w").write(FAKE_SERVER)
        exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
        os.makedirs(os.path.join(d, "bin"))
        open(os.path.join(d, "bin", exe), "w").write("x")
        md = os.path.join(d, "models", "see")
        os.makedirs(md)
        for n in ("m.gguf", "mmproj-m.gguf"):
            open(os.path.join(md, n), "w").write("x")
        json.dump({"model": "m.gguf", "mmproj": "mmproj-m.gguf"}, open(os.path.join(md, "files.json"), "w"))
        seen = []

        def argv(b, m, port, threads=None, mmproj=None):
            seen.append(mmproj)
            return [sys.executable, script, "--port", str(port)] + (["--mmproj", mmproj] if mmproj else [])
        ai = L.LocalAI(L.Install(d), which="see", argv_builder=argv, env_url="", start_timeout=20)
        try:
            self.assertTrue(ai.can_see())
            out = ai.see("sys", "image/jpeg", "QUJD", "DOING?")
            self.assertEqual(out, "echo: IMAGE DOING?")
            self.assertTrue(seen[0].endswith("mmproj-m.gguf"))
            self.assertTrue(ai.reply([{"role": "user", "content": "hi"}], "p").startswith("echo: hi"))  # it chats too
        finally:
            ai.stop()
        text_only = L.LocalAI(L.Install(d), which="small", env_url="")
        self.assertFalse(text_only.can_see())

    def test_ollama_vision_model(self):
        def opener(url, timeout=0):
            return Resp(json.dumps({"models": [{"name": "qwen2.5:3b"}, {"name": "llava:7b"}]}).encode())
        self.assertEqual(L.ollama_vision_model(opener=opener), "llava:7b")
        self.assertEqual(L.ollama_vision_model(opener=lambda u, timeout=0: Resp(b'{"models": [{"name": "qwen2.5:3b"}]}')), "")


if __name__ == "__main__":
    unittest.main()
