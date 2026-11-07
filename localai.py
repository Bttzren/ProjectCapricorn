"""A local AI that runs on the user's own computer (no key, no internet once installed). No Tk.

How: Capri downloads the official llama.cpp release (the `llama-server` program) and a small open
chat model (GGUF) into ~/.capri/localai, starts the server on 127.0.0.1 only (never reachable from other
computers) and talks to it with the OpenAI-style /v1/chat/completions API. If you already run Ollama or
LM Studio she uses that instead (set CAPRI_LOCAL_URL to point at any OpenAI-compatible server).

Nothing here sends your chats anywhere: the model and the server both run locally.

Vision ("/getbrain see"): a small model that can SEE (Qwen 2.5 VL 3B, or SmolVLM2 2.2B with "see-fast") plus its
image encoder (the "mmproj" file). The file names are looked up on Hugging Face at install time. The same model
also chats, so only one local AI program runs. Screenshots for it never leave the computer.
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
import urllib.parse
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
# vision models: name -> (Hugging Face repo, approximate total MB, what it is). Files are picked at install time.
VISION_MODELS = {
    "see": ("ggml-org/Qwen2.5-VL-3B-Instruct-GGUF", 3000,
            "Qwen 2.5 VL 3B: sees your screen and reads text on it well; wants about 6 GB free RAM"),
    "see-fast": ("ggml-org/SmolVLM2-2.2B-Instruct-GGUF", 2000,
                 "SmolVLM2 2.2B: sees your screen, faster on older laptops but rougher"),
}
HF_API = "https://huggingface.co/api/models/"
HF_HOST = "https://huggingface.co/"
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_VISION = ("llava", "bakllava", "vl", "vision", "moondream", "gemma3", "gemma4", "minicpm-v", "granite3.2-vision")


def is_vision(which):
    return which in VISION_MODELS


def all_models():
    """Every name /getbrain accepts."""
    return list(MODELS) + list(VISION_MODELS)


def _clean_name(n):
    return isinstance(n, str) and n and "/" not in n and "\\" not in n and ".." not in n


def pick_vision_files(names):
    """(model file, mmproj file) from a Hugging Face repo's file list, or None. The list is outside data, so
    names with path parts are refused. Model: a .gguf that isn't the projector and isn't split, preferring
    Q4_K_M. Projector: 'mmproj*', preferring Q8_0, then f16."""
    ggufs = [n for n in names if _clean_name(n) and n.lower().endswith(".gguf")]
    proj = [n for n in ggufs if n.lower().startswith("mmproj")]
    main = [n for n in ggufs if not n.lower().startswith("mmproj") and not re.search(r"-\d{5}-of-\d{5}", n)]

    def best(cands, prefs):
        for p in prefs:
            for n in sorted(cands):
                if p in n.lower():
                    return n
        return sorted(cands)[0] if cands else None
    m = best(main, ["q4_k_m", "q4_k_s", "q4_0", "q5_k_m", "q8_0"])
    pj = best(proj, ["q8_0", "f16", "bf16"])
    return (m, pj) if m and pj else None


def hf_file_url(repo, name):
    return HF_HOST + repo + "/resolve/main/" + urllib.parse.quote(name)


def vision_body(system, media_type, b64, prompt, max_tokens=160, model="local"):
    """OpenAI-style request with one image (llama-server accepts data: URIs in image_url)."""
    msgs = [{"role": "system", "content": system}] if system else []
    msgs.append({"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}]})
    return {"model": model, "messages": msgs, "max_tokens": int(max_tokens), "temperature": 0.3, "stream": False}


def supports_mmproj(binary, run=subprocess.run):
    """Older llama-server builds can't load a vision projector. Ask the program itself."""
    try:
        r = run([binary, "--help"], capture_output=True, text=True, timeout=30,
                creationflags=CREATE_NO_WINDOW if sys.platform.startswith("win") else 0)
        return "--mmproj" in ((r.stdout or "") + (r.stderr or ""))
    except (OSError, subprocess.SubprocessError):
        return False


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


def server_argv(binary, model, port, threads=None, mmproj=None):
    threads = threads or max(2, (os.cpu_count() or 4) - 1)
    argv = [binary, "-m", model, "--host", "127.0.0.1", "--port", str(port), "-c", "4096", "-t", str(threads)]
    if mmproj:
        argv += ["--mmproj", mmproj]
    return argv


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

    def __init__(self, folder=None, opener=urllib.request.urlopen, progress=None, platform=None, machine=None,
                 check_mmproj=supports_mmproj):
        self.folder = folder or default_dir()
        self.opener, self.progress = opener, progress or (lambda msg: None)
        self.platform, self.machine, self.check_mmproj = platform, machine, check_mmproj

    def binary(self):
        return find_server(os.path.join(self.folder, "bin"))

    def manifest(self, which):
        p = os.path.join(self.folder, "models", which, "files.json")
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            return d if _clean_name(d.get("model")) and _clean_name(d.get("mmproj")) else {}
        except (OSError, ValueError, AttributeError):
            return {}

    def model_path(self, which):
        if is_vision(which):
            m = self.manifest(which).get("model")
            return os.path.join(self.folder, "models", which, m) if m else ""
        return os.path.join(self.folder, "models", MODELS[which][1])

    def mmproj_path(self, which):
        m = self.manifest(which).get("mmproj") if is_vision(which) else None
        return os.path.join(self.folder, "models", which, m) if m else ""

    def installed(self, which="small"):
        if is_vision(which):
            mp, pp = self.model_path(which), self.mmproj_path(which)
            return bool(self.binary() and mp and pp and os.path.isfile(mp) and os.path.isfile(pp))
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

    def run(self, which="small", release=None, listing=None):
        if is_vision(which):
            return self.run_vision(which, release, listing)
        if which not in MODELS:
            raise RuntimeError("unknown model")
        self.ensure_engine(release)
        url, fname, mb, _what = MODELS[which]
        path = self.model_path(which)
        if not os.path.isfile(path):
            self.progress(f"Downloading the AI model (about {mb} MB)...")
            download(url, path, self._pct("AI model"), self.opener, min_bytes=mb * 400_000)
        return self.binary(), path

    def run_vision(self, which, release=None, listing=None):
        """Engine (one that can load an image encoder), then the vision model + its mmproj from Hugging Face."""
        self.ensure_engine(release, need_vision=True)
        repo, mb, _what = VISION_MODELS[which]
        if listing is None:
            self.progress("Looking up the vision model files...")
            req = urllib.request.Request(HF_API + repo, headers={"User-Agent": "capri-desktop"})
            try:
                with self.opener(req, timeout=30) as r:
                    listing = [x.get("rfilename", "") for x in json.loads(r.read().decode("utf-8")).get("siblings", [])]
            except (urllib.error.URLError, ValueError, AttributeError) as exc:
                raise RuntimeError(f"couldn't look up the vision model ({getattr(exc, 'reason', exc)})")
        files = pick_vision_files(listing)
        if not files:
            raise RuntimeError("the vision model's files weren't where I expected. Try /getbrain see-fast")
        model, proj = files
        folder = os.path.join(self.folder, "models", which)
        for i, name in enumerate((model, proj)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                self.progress(("Downloading the vision model" if i == 0 else "Downloading its image encoder")
                              + (f" (about {mb} MB in total)..." if i == 0 else "..."))
                download(hf_file_url(repo, name), path, self._pct("vision model" if i == 0 else "image encoder"),
                         self.opener, min_bytes=1_000_000)
        with open(os.path.join(folder, "files.json"), "w", encoding="utf-8") as f:
            json.dump({"model": model, "mmproj": proj, "repo": repo}, f)
        return self.binary(), os.path.join(folder, model)

    def ensure_engine(self, release=None, need_vision=False):
        exe = self.binary()
        if exe and need_vision and not self.check_mmproj(exe):
            self.progress("Your AI engine is too old to see. Updating it...")
            shutil.rmtree(os.path.join(self.folder, "bin"), ignore_errors=True)
            exe = None
        if not exe:
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
        return self.binary()


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


def ollama_vision_model(base=OLLAMA_URL, opener=urllib.request.urlopen):
    """Name of an Ollama model that can see images (llava, qwen2.5vl, moondream, gemma3...), or ''."""
    try:
        with opener(base + "/api/tags", timeout=2) as r:
            models = json.loads(r.read().decode("utf-8")).get("models") or []
        for m in models:
            n = (m.get("name") or "").lower()
            if any(k in n for k in OLLAMA_VISION):
                return m.get("name")
    except Exception:
        pass
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
        self._see_cache = (0.0, False)

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
                 "": "not installed (type /getbrain)"}[w]
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
                mm = self.install.mmproj_path(self.which) if is_vision(self.which) else ""
                argv = self.argv_builder(self.install.binary(), self.install.model_path(self.which), port,
                                         **({"mmproj": mm} if mm else {}))
                flags = CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                try:
                    self.proc = self.popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, creationflags=flags)
                except OSError as exc:
                    raise RuntimeError(f"couldn't start the local AI ({exc})")
                self.base = f"http://127.0.0.1:{port}"
            else:
                raise RuntimeError("No local AI yet. Type /getbrain to install one.")
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

    def can_see(self, max_age=30.0):
        """Is there a LOCAL model that can look at a screenshot? (cached: asked every tick)"""
        at, val = self.__dict__.get("_see_cache", (0.0, False))
        if time.time() - at < max_age:
            return val
        val = self._can_see()
        self._see_cache = (time.time(), val)
        return val

    def _can_see(self):
        w = self.where()
        if w == "builtin":
            return is_vision(self.which)
        if w == "ollama":
            return bool(ollama_vision_model(opener=self.opener))
        if w == "url":
            return os.environ.get("CAPRI_LOCAL_VISION", "") == "1"
        return False

    def see(self, system, media_type, b64, prompt, max_tokens=160):
        """Ask the local vision model about one screenshot. The image never leaves this computer."""
        base = self.start()
        model = self.model_name
        if self.where() == "ollama":
            model = ollama_vision_model(opener=self.opener) or model
        text = post_chat(base, vision_body(system, media_type, b64, prompt, max_tokens, model), self.opener,
                         timeout=180)
        return text

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
