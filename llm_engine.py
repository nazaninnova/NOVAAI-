"""
llm_engine.py
-------------
لایه‌ی ارتباط با مدل زبانی آفلاین (GGUF) با استفاده از llama-cpp-python.
این ماژول کاملاً مستقل از رابط کاربری Kivy است تا بشه بعداً موتور رو عوض کرد.

نکته‌ی مهم نصب:
    pip install llama-cpp-python
یک مدل GGUF (مثلاً Qwen3-0.6B-Q4_K_M.gguf)
را دانلود کرده و مسیرش را در MODEL_PATH قرار دهید. مدل باید داخل assets/models
کنار اپ کپی شود تا نسخه‌ی نهایی واقعاً آفلاین باشد.
"""

import os
import threading

MODEL_PATH = os.path.join(os.path.dirname(__file__), "assets", "models", "model.gguf")

# پرامپت‌های سیستمی برای هر «حالت» از اپ
SYSTEM_PROMPTS = {
    "story": (
        "تو یک سناریونویس خلاق و باتجربه هستی. داستان‌ها، شخصیت‌ها و دیالوگ‌های "
        "جذاب و منسجم می‌نویسی. وقتی کاربر ایده‌ای می‌دهد، آن را با جزئیات ادبی "
        "و ساختار درست (شروع، کشمکش، پایان) گسترش بده."
    ),
    "science": (
        "تو یک معلم دقیق ریاضی، فیزیک و شیمی هستی. مسائل را قدم‌به‌قدم و با "
        "استدلال روشن حل می‌کنی، فرمول‌ها را می‌نویسی و در پایان جواب نهایی را "
        "به‌صورت خلاصه مشخص می‌کنی."
    ),
    "companion": (
        "تو یک همراه احساسی گرم، صبور و بدون قضاوت هستی. با همدلی گوش می‌دهی، "
        "احساسات کاربر را تأیید می‌کنی و در صورت نیاز به آرامش و دیدگاه سالم "
        "کمک می‌کنی. توصیه‌ی پزشکی یا روان‌پزشکی قطعی نمی‌دهی."
    ),
    "general": (
        "تو یک دستیار هوش مصنوعی دانا و صادق هستی که به هر سوالی با دقت، "
        "شفافیت و لحنی دوستانه پاسخ می‌دهی."
    ),
    "memory_extract": (
        "با دقت به این مکالمه نگاه کن و فقط نکات مهم و پایدار درباره‌ی "
        "کاربر را که ارزش به‌خاطر سپردن برای مکالمات آینده دارند (مثل "
        "اسم، علایق، شغل، اهداف، ترجیحات) در چند خط کوتاه فارسی و به‌صورت "
        "فهرست بنویس. اگر نکته‌ی مهم جدیدی نبود، فقط بنویس: هیچ."
    ),
}


def get_engine(model_path: str = MODEL_PATH):
    """
    فکتوری موتور: روی دسکتاپ مستقیم از llama-cpp-python استفاده می‌کند،
    روی اندروید سرور نیتیو محلی را اجرا و به آن وصل می‌شود (llm_engine_android.py).
    """
    from kivy.utils import platform
    if platform == "android":
        from llm_engine_android import AndroidLLMEngine
        return AndroidLLMEngine(model_path=model_path)
    return LLMEngine(model_path=model_path)


class LLMEngine:
    """رَپِر بالای llama-cpp-python برای بارگذاری و تولید پاسخ به‌صورت آفلاین."""

    def __init__(self, model_path: str = MODEL_PATH, n_ctx: int = 4096):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.llm = None
        self._lock = threading.Lock()
        self.load_error = None

    def load(self):
        """مدل را در حافظه بارگذاری می‌کند. این تابع را در یک ترد جدا صدا بزنید."""
        try:
            from llama_cpp import Llama
        except ImportError:
            self.load_error = (
                "کتابخانه‌ی llama-cpp-python نصب نیست.\n"
                "دستور نصب: pip install llama-cpp-python"
            )
            return False

        if not os.path.exists(self.model_path):
            self.load_error = (
                f"فایل مدل پیدا نشد:\n{self.model_path}\n"
                "یک فایل GGUF (مدل پیش‌فرض Qwen3-0.6B-Q4_K_M.gguf) دانلود و "
                "در این مسیر قرار دهید."
            )
            return False

        try:
            with self._lock:
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    n_threads=max(2, os.cpu_count() or 4),
                    verbose=False,
                )
            return True
        except Exception as exc:  # noqa: BLE001
            self.load_error = f"خطا در بارگذاری مدل: {exc}"
            return False

    def is_ready(self):
        return self.llm is not None

    def generate(self, user_text: str, mode: str = "general", history=None,
                 max_tokens: int = 512, temperature: float = 0.7, memory: str = "", username: str = ""):
        """
        پاسخ مدل را برمی‌گرداند (blocking - باید در ترد جدا صدا زده شود).
        history: لیستی از دیکشنری‌های {'role': 'user'/'assistant', 'content': ...}
        memory: خلاصه‌ی حافظه‌ی بلندمدت کاربر (نکاتی که قبلاً درباره‌اش
                فهمیده‌ایم)، اگر موجود باشد به system prompt اضافه می‌شود.
        """
        if self.llm is None:
            return "⚠️ مدل هنوز بارگذاری نشده است."

        system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
        if username:
            system_prompt += f"\n\nنام کاربر فعلی: {username}\nکاربر را با همین نام صدا بزن، مگر اینکه خودش نام دیگری بخواهد."
        if memory:
            system_prompt += (
                "\n\nنکاتی که از مکالمات قبلی با این کاربر به خاطر داری:\n" + memory
            )
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])  # فقط چند پیام آخر برای کنترل حافظه
        messages.append({"role": "user", "content": user_text})

        with self._lock:
            try:
                try:
                    result = self.llm.create_chat_completion(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        chat_template_kwargs={"enable_thinking": False},
                    )
                except TypeError:
                    # Compatibility fallback for older llama-cpp-python versions
                    # that do not expose chat_template_kwargs.
                    result = self.llm.create_chat_completion(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                content = result["choices"][0]["message"].get("content", "").strip()
                if not content:
                    return "⚠️ مدل پاسخی تولید نکرد."
                return content
            except Exception as exc:  # noqa: BLE001
                return f"⚠️ خطا در تولید پاسخ: {exc}"
