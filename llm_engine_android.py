"""
llm_engine_android.py
----------------------
روی اندروید به‌جای استفاده مستقیم از llama-cpp-python (که برایش recipe
رسمی وجود ندارد)، یک باینری از پیش کامپایل‌شده‌ی llama-server را که در
لایه‌ی کتابخانه‌های نیتیو اپ جاسازی شده اجرا می‌کنیم و از طریق HTTP روی
127.0.0.1 با آن صحبت می‌کنیم. کاملاً آفلاین است چون هیچ داده‌ای از
دستگاه خارج نمی‌شود.

پیش‌نیاز: باینری llama-server با نام libllama_server.so در
buildozer.spec از طریق android.add_libs_* اضافه شده باشد (توضیح در README).
"""

import os
import subprocess
import time
import threading

import requests

from llm_engine import SYSTEM_PROMPTS  # پرامپت‌های سیستمی مشترک

SERVER_PORT = 8080
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
NATIVE_LIB_NAME = "libllama_server.so"


def _get_native_lib_dir():
    """مسیر پوشه‌ی کتابخانه‌های نیتیو اپ روی اندروید را برمی‌گرداند."""
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    context = PythonActivity.mActivity
    return context.getApplicationInfo().nativeLibraryDir


class AndroidLLMEngine:
    def __init__(self, model_path: str, n_ctx: int = 2048):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.process = None
        self.load_error = None
        self._ready = False

    def load(self):
        """باینری سرور را پیدا و اجرا می‌کند، سپس منتظر می‌ماند تا آماده شود."""
        try:
            lib_dir = _get_native_lib_dir()
        except Exception as exc:  # noqa: BLE001
            self.load_error = f"نتوانستم مسیر کتابخانه‌ی نیتیو را پیدا کنم: {exc}"
            return False

        server_bin = os.path.join(lib_dir, NATIVE_LIB_NAME)
        if not os.path.exists(server_bin):
            self.load_error = (
                f"باینری سرور پیدا نشد:\n{server_bin}\n"
                "مطمئن شو libllama_server.so در buildozer.spec اضافه شده."
            )
            return False

        if not os.path.exists(self.model_path):
            self.load_error = f"فایل مدل پیدا نشد:\n{self.model_path}"
            return False

        try:
            self.process = subprocess.Popen(
                [
                    server_bin,
                    "-m", self.model_path,
                    "-c", str(self.n_ctx),
                    "--port", str(SERVER_PORT),
                    "--host", "127.0.0.1",
                    "-ngl", "0",  # روی اکثر گوشی‌ها فقط CPU در دسترس است
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:  # noqa: BLE001
            self.load_error = f"اجرای سرور شکست خورد: {exc}"
            return False

        # صبر برای آماده شدن سرور (حداکثر ۶۰ ثانیه، مدل‌های بزرگ‌تر کندتر لود می‌شوند)
        for _ in range(60):
            try:
                r = requests.get(f"{SERVER_URL}/health", timeout=2)
                if r.status_code == 200:
                    self._ready = True
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)

        self.load_error = "سرور در زمان مقرر آماده نشد."
        return False

    def is_ready(self):
        return self._ready

    def generate(self, user_text, mode="general", history=None,
                 max_tokens=512, temperature=0.7, memory=""):
        if not self._ready:
            return "⚠️ سرور مدل هنوز آماده نیست."

        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
        if username:
            system_prompt += f"\n\nنام کاربر فعلی: {username}\nکاربر را با همین نام صدا بزن، مگر اینکه خودش نام دیگری بخواهد."
        if memory:
            system_prompt += (
                "\n\nنکاتی که از مکالمات قبلی با این کاربر به خاطر داری:\n" + memory
            )
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_text})

        try:
            r = requests.post(
                f"{SERVER_URL}/v1/chat/completions",
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            return f"⚠️ خطا در ارتباط با سرور محلی: {exc}"

    def shutdown(self):
        if self.process:
            self.process.terminate()
