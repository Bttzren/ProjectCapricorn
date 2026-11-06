"""A local AI that runs on the user's own computer (no key, no internet once installed). No Tk.

How: Capri downloads the official llama.cpp release (the `llama-server` program) and a small open
chat model (GGUF) into ~/.capri/localai, starts the server on 127.0.0.1 only (never reachable from other
computers) and talks to it with the OpenAI-style /v1/chat/completions API. If you already run Ollama or
LM Studio she uses that instead (set CAPRI_LOCAL_URL to point at any OpenAI-compatible server).

Nothing here sends your chats anywhere: the model and the server both run locally. Text only (no vision).
"""
import atexit
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
import zipfile

RELEASE_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
ASSET_PREFIX = "https://github.com/ggml-org/llama.cpp/releases/download/"
CREATE_NO_WINDOW = 0x08000000

# name -> (url, file name, approximate size in MB, what it is)
MODELS = {
    "small": ("https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
              "qwen2.5-1.5b-instruct-q4_k_m.gguf", 1100, "Qwen 2.5 1.5B: fast, fits any PC, simple replies"),
    "big": ("https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
            "qwen2.5-3b-instruct-q4_k_m.gguf", 2100, "Qwen 2.5 3B: smarter, slower, wants 4 GB free RAM"),
}
OLLAMA_URL = "http://127.0.0.1:11434"


def default_dir():
    return os.path.join(os.path.expanduser("~"), ".capri", "localai")


# ------------------------------------------------------------------ picking the download
def pick_asset(assets, platform=None, machine=None):
    """The llama.cpp release file to download for this computer, as (name, url). None if nothing fits.
    `assets` is the release's asset list ({'name', 'browser_download_url'}). CPU builds only: they run anywhere."""
    platform, machine = platform or sys.platform, (machine or "").lower()
    if platform.startswith("win"):
        want = [r"win-cpu-x64", r"win-avx2-x64", r"win-x64"] if "arm" not in machine else [r"win-cpu-arm64"]
    elif platform == "darwin":
        want = [r"macos-arm64"] if ("arm" in machine or "aarch" in machine) else [r"macos-x64"]
    else:
        want = [r"ubuntu-x64"] if "arm" not in machine and "aarch" not in machine else [r"ubuntu-arm64"]
    bad = re.compile(r"cuda|vulkan|hip|sycl|opencl|kompute|rocm|cudart|openvino|android|xcframework|-src", re.I)
    for pat in want:
        for a in assets or []:
            name, url = a.get("name", ""), a.get("browser_download_url", "")
            if (re.search(pat, name, re.I) and name.lower().endswith((".zip", ".tar.gz")) and not bad.search(name)
                    and url.startswith(ASSET_PREFIX)):
                return name, url
    return None


def safe_extract(archive, dest):
    """Unpack a .zip or .tar.gz, refusing any member that would land outside `dest`."""
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    def ok(path):
        full = os.path.abspath(os.path.join(dest, path))
        return full == dest or full.startswith(dest + os.sep)
    if archive.lower().endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                if not ok(n):
                    raise RuntimeError("the download contained an unsafe path")
            z.extractall(dest)
    else:
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                if not ok(m.name) or m.issym() or m.islnk() or m.isdev():
                    raise RuntimeError("the download contained an unsafe path")
            t.extractall(dest)


def find_server(folder):
    exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
    for root, _dirs, files in os.walk(folder):
        if exe in files:
            return os.path.join(root, exe)
    return None


def server_argv(binary, model, port, threads=None):
    threads = threads or max(2, (os.cpu_count() or 4) - 1)
    return [binary, "-m", model, "--host", "127.0.0.1", "--port", str(port), "-c", "4096", "-t", str(threads)]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ------------------------------------------------------------------ downloading
def download(url, dest, progress=None, opener=urllib.request.urlopen, min_bytes=1000, chunk=1 << 20, resume=True):
    """Download `url` to `dest` (through dest + '.part', resuming a partial file). progress(done, total)."""
    if not url.startswith("https://"):
        raise RuntimeError("downloads must be https")
    part = dest + ".part"
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    have = os.path.getsize(part) if resume and os.path.isfile(part) else 0
    req = urllib.request.Request(url, headers={"User-Agent": "capri-desktop"})
    if have:
        req.add_header("Range", f"bytes={have}-")
    try:
        resp = opener(req, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and have:                       # already complete
            os.replace(part, dest)
            return dest
        raise RuntimeError(f"download failed ({exc.code})")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"can't reach the download server ({exc.reason})")
    with resp:
        status = getattr(resp, "status", 200)
        if have and status != 206:
            have = 0                                        # server ignored Range: start over
        length = int(resp.headers.get("Content-Length") or 0)
        total = length + have if length else 0
        done = have
        with open(part, "ab" if have else "wb") as f:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                f.write(buf)
                done += len(buf)
                if progress:
                    progress(done, total)
    if total and done < total:
        raise RuntimeError("the download was cut off. Run the command again to resume.")
    if done < min_bytes:
        raise RuntimeError("the download was too small to be right")
    os.replace(part, dest)
    return dest


class Install:
    """Fetches the server and a model. run() blocks: call it on a background thread."""

    def __init__(self, folder=None, opener=urllib.request.urlopen, progress=None, platform=None, machine=None):
        self.folder = folder or default_dir()
        self.opener, self.progress = opener, progress or (lambda msg: None)
        self.platform, self.machine = platform, machine

    def binary(self):
        return find_server(os.path.join(self.folder, "bin"))

    def model_path(self, which):
        return os.path.join(self.folder, "models", MODELS[which][1])

    def installed(self, which="small"):
        return bool(self.binary() and os.path.isfile(self.model_path(which)))

    def _pct(self, label):
        last = [-10]

        def cb(done, total):
            if total:
                p = int(done * 100 / total)
                if p >= last[0] + 10:
                    last[0] = p
                    self.progress(f"{label}: {p}%")
        return cb

    def run(self, which="small", release=None):
        if which not in MODELS:
            raise RuntimeError("unknown model")
        if not self.binary():
            self.progress("Finding the AI engine (llama.cpp)...")
            if release is None:
                req = urllib.request.Request(RELEASE_API, headers={"User-Agent": "capri-desktop",
                                                                   "Accept": "application/vnd.github+json"})
                try:
                    with self.opener(req, timeout=30) as r:
                        release = json.loads(r.read().decode("utf-8"))
                except (urllib.error.URLError, ValueError) as exc:
                    raise RuntimeError(f"couldn't look up the AI engine ({getattr(exc, 'reason', exc)})")
            asset = pick_asset(release.get("assets", []), self.platform, self.machine)
            if not asset:
                raise RuntimeError("no ready-made AI engine for this computer. Install Ollama and she'll use it.")
            name, url = asset
            self.progress(f"Downloading the AI engine ({name})...")
            tmp = os.path.join(self.folder, "dl", name)
            download(url, tmp, self._pct("AI engine"), self.opener, min_bytes=100_000)
            safe_extract(tmp, os.path.join(self.folder, "bin"))
            os.remove(tmp)
            exe = self.binary()
            if not exe:
                raise RuntimeError("the AI engine download didn't contain llama-server")
            if not sys.platform.startswith("win"):
                os.chmod(exe, 0o755)
        url, fname, mb, _what = MODELS[which]
        path = self.model_path(which)
        if not os.path.isfile(path):
            self.progress(f"Downloading the AI model (about {mb} MB)...")
            download(url, path, self._pct("AI model"), self.opener, min_bytes=mb * 400_000)
        return self.binary(), path


# ------------------------------------------------------------------ talking to a server
def parse_chat(data):
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def chat_body(messages, persona, max_tokens=200, model="local"):
    msgs = [{"role": "system", "content": persona}] if persona else []
    msgs += [{"role": m["role"], "content": m["content"]} for m in messages]
    return {"model": model, "messages": msgs, "max_tokens": int(max_tokens), "temperature": 0.8, "stream": False}


def post_chat(base, body, opener=urllib.request.urlopen, timeout=90):
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with opener(req, timeout=timeout) as r:
            return parse_chat(json.loads(r.read().decode("utf-8")))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"local AI error {exc.code}")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"local AI isn't answering ({getattr(exc, 'reason', exc)})")


def alive(base, opener=urllib.request.urlopen, timeout=2):
    for path in ("/health", "/v1/models"):
        try:
            with opener(base.rstrip("/") + path, timeout=timeout) as r:
                if r.status == 200:
                    return True
        except Exception:
            continue
    return False


def ollama_model(base=OLLAMA_URL, opener=urllib.request.urlopen):
    """Name of the first model Ollama has, or ''."""
    try:
        with opener(base + "/api/tags", timeout=2) as r:
            models = json.loads(r.read().decode("utf-8")).get("models") or []
        return models[0].get("name", "") if models else ""
    except Exception:
        return ""


class LocalAI:
    """The thing llm_reply() calls. reply() starts the engine on first use and is safe from any thread."""

    def __init__(self, install=None, which="small", popen=subprocess.Popen, opener=urllib.request.urlopen,
                 argv_builder=server_argv, env_url=None, start_timeout=90, sleep=time.sleep):
        self.install = install or Install()
        self.which, self.popen, self.opener, self.argv_builder = which, popen, opener, argv_builder
        self.start_timeout, self.sleep = start_timeout, sleep
        self.external = (env_url if env_url is not None else os.environ.get("CAPRI_LOCAL_URL", "")).strip()
        self.base, self.proc, self.model_name = "", None, "local"
        self.error = ""
        self._lock = threading.Lock()
        self._seen = (0.0, "")
        atexit.register(self.stop)

    def refresh(self):
        self._seen = (0.0, "")

    def use(self, which):
        """Switch between the built-in models ('small' / 'big'). Stops the running engine so the next line starts
        the chosen model. Returns True if it changed."""
        if which not in MODELS:
            raise ValueError(which)
        if which == self.which:
            return False
        self.stop()
        self.which = which
        self.refresh()
        return True

    # what's available without starting anything
    def where(self, max_age=30.0):
        """'url' (CAPRI_LOCAL_URL), 'ollama', 'builtin' or '' (nothing). Cached for a few seconds because
        the answer is asked for very often."""
        at, val = self._seen
        if time.time() - at < max_age:
            return val
        if self.external:
            val = "url"
        elif self.install.installed(self.which):
            val = "builtin"
        elif ollama_model(opener=self.opener):
            val = "ollama"
        else:
            val = ""
        self._seen = (time.time(), val)
        return val

    def available(self):
        return bool(self.where())

    def status(self):
        w = self.where()
        label = {"url": f"your server at {self.external}", "ollama": "Ollama", "builtin": "built-in " + self.which,
                 "": "not installed (open Settings > LOCAL AI)"}[w]
        return label + (" (running)" if self.base and alive(self.base, self.opener) else "")

    def start(self):
        """Make sure there's a server to talk to. Returns its base URL; raises RuntimeError with a reason."""
        with self._lock:
            if self.base and (self.proc is None or self.proc.poll() is None) and alive(self.base, self.opener):
                return self.base
            w = self.where(max_age=0)
            if w == "url":
                self.base = self.external
            elif w == "ollama":
                self.base, self.model_name = OLLAMA_URL, ollama_model(opener=self.opener) or "local"
            elif w == "builtin":
                port = free_port()
                argv = self.argv_builder(self.install.binary(), self.install.model_path(self.which), port)
                flags = CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                try:
                    self.proc = self.popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, creationflags=flags)
                except OSError as exc:
                    raise RuntimeError(f"couldn't start the local AI ({exc})")
                self.base = f"http://127.0.0.1:{port}"
            else:
                raise RuntimeError("No local AI yet. Open Settings > LOCAL AI to install one.")
            end = time.time() + self.start_timeout
            while time.time() < end:
                if self.proc is not None and self.proc.poll() is not None:
                    self.base = ""
                    raise RuntimeError("the local AI program closed right after starting")
                if alive(self.base, self.opener):
                    self.error = ""
                    return self.base
                self.sleep(0.5)
            self.stop()
            raise RuntimeError("the local AI took too long to start")

    def reply(self, messages, persona, max_tokens=200):
        base = self.start()
        text = post_chat(base, chat_body(messages, persona, max_tokens, self.model_name), self.opener)
        return text or "(the local AI sent nothing, try again)"

    def stop(self):
        p, self.proc = self.proc, None
        if p is not None and p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except OSError:
                    pass
        if p is not None:
            self.base = ""

    def remove(self):
        self.stop()
        shutil.rmtree(self.install.folder, ignore_errors=True)
