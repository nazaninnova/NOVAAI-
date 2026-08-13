"""Persistent, resumable downloader for the external GGUF model."""
import os
import time
import threading
import requests

DEFAULT_MODEL_ID = "qwen3-0.6b-q4-k-m"
DEFAULT_MODEL_FILENAME = "qwen3-0.6b-q4-k-m.gguf"
DEFAULT_MODEL_URL = (
    "https://huggingface.co/smarttasks/Qwen3-0.6B-GGUF/resolve/main/"
    "Qwen3-0.6B-Q4_K_M.gguf"
)
DEFAULT_MODEL_SHA256 = "3479875d3e4c726f7a20b2181f5e1536aefe9925f284f9ae9997a39a7e0d8dc9"
CONNECT_TIMEOUT = 20
READ_TIMEOUT = 90
MAX_RETRIES = 8
RETRY_BACKOFF_SECONDS = 4


def _human_size(n):
    if n is None:
        return "? MB"
    return f"{n / (1024 ** 2):.1f} MB"


def _human_error(exc):
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "اتصال برقرار نشد. اینترنت یا فیلترشکن را بررسی کن."
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "دانلود کند یا ناپایدار شد؛ از همان‌جا ادامه می‌دهیم."
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "اتصال اولیه timeout شد؛ دوباره تلاش می‌کنیم."
    return f"{type(exc).__name__}: {exc}"


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def download_model(dest_path, url=DEFAULT_MODEL_URL, expected_sha256=DEFAULT_MODEL_SHA256,
                   on_progress=None, on_done=None, on_error=None, on_status=None):
    """Download in background. Resume uses HTTP Range and a .part file.

    on_progress(fraction, downloaded_bytes, total_bytes, speed_bytes_sec)
    """
    def _run():
        tmp_path = dest_path + ".part"
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resume_from = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
                headers = {"Range": f"bytes={resume_from}-"} if resume_from else {}
                with requests.get(url, stream=True, headers=headers,
                                  timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                  allow_redirects=True) as r:
                    # If Range is ignored, safely restart rather than corrupting the model.
                    if resume_from and r.status_code == 200:
                        resume_from = 0
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                    r.raise_for_status()
                    content_length = r.headers.get("content-length")
                    total = int(content_length) + resume_from if content_length else None
                    downloaded = resume_from
                    started = time.time()
                    mode = "ab" if resume_from else "wb"

                    if on_status:
                        on_status(f"شروع دانلود Qwen3-0.6B — { _human_size(downloaded) } دریافت شده")

                    with open(tmp_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=1024 * 512):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed = max(time.time() - started, 0.001)
                            speed = max(0, downloaded - resume_from) / elapsed
                            fraction = (downloaded / total) if total else None
                            if on_progress:
                                on_progress(fraction, downloaded, total, speed)

                if expected_sha256:
                    actual = _sha256(tmp_path)
                    if actual != expected_sha256.lower():
                        raise ValueError(
                            "اعتبارسنجی SHA-256 مدل ناموفق بود؛ فایل دانلودشده سالم نیست."
                        )
                os.replace(tmp_path, dest_path)
                if on_done:
                    on_done()
                return
            except Exception as exc:
                last_error = exc
                if on_status:
                    on_status(f"{_human_error(exc)} — تلاش {attempt} از {MAX_RETRIES}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        if on_error:
            on_error(_human_error(last_error) if last_error else "خطای نامشخص")

    threading.Thread(target=_run, daemon=True).start()
