"""
farsi.py
--------
Kivy به‌صورت پیش‌فرض حروف فارسی/عربی را به‌هم نمی‌چسباند (shaping) و
جهت راست‌به‌چپ را هم رعایت نمی‌کند. این ماژول متن فارسی را قبل از
نمایش، «آماده‌ی نمایش» می‌کند.

نصب لازم:
    pip install arabic-reshaper python-bidi
"""

import arabic_reshaper
from bidi.algorithm import get_display
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window

_FA_FONT = "assets/fonts/Vazirmatn-Regular.ttf"
# حباب چت size_hint_x=0.82 داره و padding افقی‌اش 14*2 و Label هم
# text_size = self.width - 10 داره (نگاه کن به ChatBubble در theme.kv).
_BUBBLE_SIZE_HINT_X = 0.82
_BUBBLE_HORIZONTAL_SLACK = 14 * 2 + 10

_reshaper_config = arabic_reshaper.config_for_true_type_font(
    None, arabic_reshaper.ENABLE_ALL_LIGATURES
) if False else None  # تنظیم پیش‌فرض کافی است

_reshaper = arabic_reshaper.ArabicReshaper()


def rtl(text: str) -> str:
    """متن فارسی را برای نمایش صحیح در Label/Button آماده می‌کند.

    هر خط را جداگانه پردازش می‌کنیم چون اجرای bidi روی کل یک متن
    چندخطی/چندپاراگرافی یکجا، ترتیب خط‌ها و پاراگراف‌ها را به‌هم می‌ریزد.
    """
    if not text:
        return text
    try:
        lines = text.split("\n")
        processed = []
        for line in lines:
            if line.strip():
                reshaped = _reshaper.reshape(line)
                processed.append(get_display(reshaped))
            else:
                processed.append(line)
        return "\n".join(processed)
    except Exception:  # noqa: BLE001
        return text


def _text_width_px(s: str, font_size: int = 15) -> float:
    if not s:
        return 0
    cl = CoreLabel(text=s, font_name=_FA_FONT, font_size=font_size)
    cl.refresh()
    return cl.texture.size[0] if cl.texture else 0


def wrap_rtl(text: str, max_width: float = None) -> str:
    """مخصوص متن‌های طولانی (مثل جواب هوش مصنوعی) که قرار است داخل یک
    Label با عرض محدود نمایش داده شوند.

    مشکل: اگر بگذاریم خود Kivy متن را به‌صورت خودکار بشکند، این کار را
    روی متنِ از قبل بازآرایی‌شده (bidi) انجام می‌دهد و چون Label فرض
    می‌کند متن چپ‌به‌راست است، نقطه‌ی شکستن خط را اشتباه انتخاب می‌کند و
    ترتیب کلمات بهم می‌ریزد (همان مشکلی که با آن مواجه شدید).

    راه‌حل: خودمان، قبل از بازآرایی، پاراگراف را بر اساس عرض واقعیِ
    پیکسلیِ حباب چت (نه یک تعداد کاراکتر ثابت) به خط‌های کوتاه‌تر
    می‌شکنیم؛ سپس هر خطِ از قبل شکسته‌شده را rtl می‌کنیم. اینطوری تا
    جایی که کلمات واقعاً در عرض حباب جا می‌شوند همان یک خط می‌مانند، و
    فقط وقتی از عرض واقعی حباب بیشتر شد می‌شکنند.
    """
    if not text:
        return text
    if max_width is None:
        max_width = Window.width * _BUBBLE_SIZE_HINT_X - _BUBBLE_HORIZONTAL_SLACK
    paragraphs = text.split("\n")
    out_lines = []
    for para in paragraphs:
        if not para.strip():
            out_lines.append("")
            continue
        words = para.split(" ")
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if _text_width_px(candidate) > max_width and current:
                out_lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            out_lines.append(current)
    return rtl("\n".join(out_lines))
