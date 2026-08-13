"""
farsi_widgets.py
-----------------
PersianTextField: یک فیلد ورودی تک‌خطی که از صفر (نه به‌عنوان زیرکلاس
TextInput) برای فارسی/راست‌به‌چپ نوشته شده است.

چرا از صفر؟ چون منطق داخلی TextInput در Kivy برای متن راست‌به‌چپ درست
کار نمی‌کند: نه حروف را می‌چسباند و نه موقعیت مکان‌نما را هنگام
کلیک/ویرایش وسط متن درست محاسبه می‌کند (چندین بار امتحان و تأیید شد).
اینجا خودمان کیبورد را می‌گیریم، رشته‌ی منطقی (واقعی) متن را نگه
می‌داریم، و موقعیت مکان‌نما/کلیک را با یک فرمول ساده‌ی راست‌به‌چپ
حساب می‌کنیم؛ نمایش گرافیکی خود حروف را همچنان به Label استاندارد
Kivy (که رندر فونت را درست انجام می‌دهد) می‌سپاریم.
"""

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.properties import StringProperty
from kivy.clock import Clock

from farsi import rtl

FA_FONT = "assets/fonts/Vazirmatn-Regular.ttf"
_PAD = 12


class PersianTextField(Widget):
    text = StringProperty("")
    hint_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor_index = 0
        self._focused = False
        self._cursor_visible = True
        self._keyboard = None

        with self.canvas.before:
            Color(0.08, 0.04, 0.16, 0.9)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

        self._label = Label(
            markup=False,
            color=(0.90, 0.98, 1, 1),
            font_size="16sp",
            font_name=FA_FONT,
            halign="right",
            valign="middle",
        )
        self.add_widget(self._label)

        self.register_event_type("on_text_validate")

        self.bind(pos=self._sync, size=self._sync)
        self.bind(text=self._refresh, hint_text=self._refresh)

        Clock.schedule_interval(self._blink, 0.5)
        self._sync()

    # ---------- هندسه و رسم ----------

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._label.pos = self.pos
        self._label.size = self.size
        self._label.text_size = (self.width - _PAD * 2, None)
        self._refresh()

    def _measure(self, s):
        if not s:
            return 0
        cl = CoreLabel(text=s, font_name=FA_FONT, font_size=16)
        cl.refresh()
        return cl.texture.size[0] if cl.texture else 0

    def _visual_text(self):
        return rtl(self.text) if self.text else ""

    def _refresh(self, *a):
        if self.text:
            self._label.text = self._visual_text()
            self._label.color = (0.90, 0.98, 1, 1)
        elif self.hint_text and not self._focused:
            self._label.text = rtl(self.hint_text)
            self._label.color = (0.5, 0.55, 0.65, 1)
        else:
            self._label.text = ""
        self._draw_cursor()

    def _draw_cursor(self):
        self.canvas.after.clear()
        if not (self._focused and self._cursor_visible):
            return
        n = len(self.text)
        i = max(0, min(self._cursor_index, n))
        visual = self._visual_text()
        prefix_len = n - i
        prefix = visual[:prefix_len] if visual else ""
        prefix_w = self._measure(prefix)
        total_w = self._measure(visual)
        right_edge = self.right - _PAD
        text_left = right_edge - total_w
        cursor_x = text_left + prefix_w
        cursor_x = max(self.x + _PAD, min(cursor_x, self.right - _PAD))
        with self.canvas.after:
            Color(0.10, 0.9, 0.9, 1)
            Line(points=[cursor_x, self.y + 8, cursor_x, self.top - 8], width=1.4)

    def _blink(self, dt):
        self._cursor_visible = (not self._cursor_visible) if self._focused else True
        self._draw_cursor()

    # ---------- فوکوس، کلیک و کیبورد ----------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._focus(True)
            self._cursor_index = self._index_from_x(touch.x)
            self._refresh()
            return True
        elif self._focused:
            self._focus(False)
        return super().on_touch_down(touch)

    def _index_from_x(self, x):
        n = len(self.text)
        if n == 0:
            return 0
        visual = self._visual_text()
        total_w = self._measure(visual)
        text_left = (self.right - _PAD) - total_w
        offset = x - text_left
        if offset <= 0:
            prefix_len = 0
        elif offset >= total_w:
            prefix_len = len(visual)
        else:
            prefix_len = len(visual)
            for k in range(1, len(visual) + 1):
                if self._measure(visual[:k]) >= offset:
                    prefix_len = k
                    break
        return max(0, n - prefix_len)

    def _focus(self, value):
        self._focused = value
        if value:
            self._keyboard = Window.request_keyboard(self._keyboard_closed, self, "text")
            if self._keyboard:
                self._keyboard.bind(on_key_down=self._on_key_down)
            Window.bind(on_textinput=self._on_textinput)
        else:
            if self._keyboard:
                self._keyboard.unbind(on_key_down=self._on_key_down)
                self._keyboard.release()
                self._keyboard = None
            Window.unbind(on_textinput=self._on_textinput)
        self._refresh()

    def _keyboard_closed(self):
        self._focus(False)

    def _on_textinput(self, window, text):
        if not text:
            return
        i = self._cursor_index
        self.text = self.text[:i] + text + self.text[i:]
        self._cursor_index = i + len(text)

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        n = len(self.text)
        if key == "backspace":
            if self._cursor_index > 0:
                i = self._cursor_index
                self.text = self.text[: i - 1] + self.text[i:]
                self._cursor_index = i - 1
        elif key == "delete":
            i = self._cursor_index
            if i < n:
                self.text = self.text[:i] + self.text[i + 1:]
        elif key == "left":
            self._cursor_index = max(0, self._cursor_index - 1)
            self._refresh()
        elif key == "right":
            self._cursor_index = min(n, self._cursor_index + 1)
            self._refresh()
        elif key == "home":
            self._cursor_index = 0
            self._refresh()
        elif key == "end":
            self._cursor_index = n
            self._refresh()
        elif key == "enter":
            self.dispatch("on_text_validate")
        else:
            return False
        return True

    def on_text_validate(self, *args):
        pass
