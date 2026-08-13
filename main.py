"""
main.py
-------
اپ Nova AI: دستیار هوش مصنوعی آفلاین با تم سایبرپانک/کهکشانی
ساخته‌شده با Kivy. برای اجرا:
    pip install kivy llama-cpp-python
    python main.py
"""

import os
import time
import threading

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import mainthread, Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.utils import platform

from llm_engine import get_engine
from model_downloader import download_model, DEFAULT_MODEL_URL
from farsi import rtl, wrap_rtl
import profile_manager

try:
    from plyer import filechooser as plyer_filechooser
except Exception:  # noqa: BLE001
    plyer_filechooser = None

try:
    from plyer import camera as plyer_camera
except Exception:  # noqa: BLE001
    plyer_camera = None

Builder.load_file("theme.kv")

FA_FONT_PATH = "assets/fonts/Vazirmatn-Regular.ttf"

_MODE_LABELS = ["عمومی", "داستان‌نویسی", "علمی", "همراه احساسی"]
_MODE_KEYS = ["general", "story", "science", "companion"]
MODE_MAP = {rtl(label): key for label, key in zip(_MODE_LABELS, _MODE_KEYS)}

MEMORY_EVERY_N_EXCHANGES = 3  # هر چند تبادل پیام، یک‌بار خلاصه‌ی حافظه به‌روزرسانی شود


class SplashScreen(Screen):
    """صفحه‌ی اسپلش: لوگوی اپ را چند ثانیه نشان می‌دهد."""

    def on_enter(self, *args):
        Clock.schedule_once(self._go_next, 2.2)

    def _go_next(self, *args):
        self.manager.current = "profile"


class ProfileScreen(Screen):
    """صفحه‌ی انتخاب/ساخت پروفایل محلی (معادل ورود/ثبت‌نام، بدون سرور)."""

    def on_pre_enter(self, *args):
        self.refresh_profiles()

    def refresh_profiles(self):
        box = self.ids.profiles_box
        box.clear_widgets()
        profiles = profile_manager.list_profiles()
        if not profiles:
            lbl = Factory.NeonLabel()
            lbl.text = rtl("هنوز پروفایلی نساختی؛ یه اسم جدید وارد کن و بزن شروع.")
            lbl.size_hint_y = None
            lbl.height = "30sp"
            lbl.font_size = "13sp"
            box.add_widget(lbl)
            return
        for name in profiles:
            btn = Factory.NeonButton()
            btn.text = rtl(name)
            btn.size_hint_y = None
            btn.height = "46sp"
            btn.bind(on_release=lambda inst, n=name: self.go_to_chat(n))
            box.add_widget(btn)

    def create_or_continue(self):
        name = self.ids.new_profile_input.text.strip()
        if not name:
            return
        self.ids.new_profile_input.text = ""
        self.go_to_chat(name)

    def go_to_chat(self, username):
        app = App.get_running_app()
        chat_screen = app.root.get_screen("chat")
        chat_screen.set_profile(username)
        app.root.current = "chat"


class RootScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # مسیر ذخیره‌ی مدل: یک پوشه‌ی ثابت در خانه‌ی کاربر، مستقل از پروفایل
        # کاربر و مستقل از اسم کلاس اپ (برای اینکه با تغییرات بعدی، مدل
        # دوباره دانلود نشود)
        data_dir = os.path.join(os.path.expanduser("~"), ".nova_ai_offline")
        self.model_path = os.path.join(data_dir, "model.gguf")

        self.engine = get_engine(model_path=self.model_path)
        self.history = []
        self.username = None
        self._exchange_count = 0

        self._loading = True
        self._model_ready = False
        self._model_error = None

        if os.path.exists(self.model_path):
            threading.Thread(target=self._load_model, daemon=True).start()
        else:
            threading.Thread(target=self._start_download, daemon=True).start()

    # ---------- مدیریت پروفایل ----------

    def set_profile(self, username):
        self.username = username
        self.history = profile_manager.load_history(username)
        self.ids.chat_box.clear_widgets()

        if self.history:
            for msg in self.history:
                self._add_bubble(msg["content"], is_user=(msg["role"] == "user"))
        else:
            self._add_bubble(f"سلام {username}! من Nova AI هستم ✦", is_user=False)

        if self._model_error:
            self._add_bubble(
                "⚠️ نتونستم مدل رو بارگذاری کنم. جزئیات خطا بالای نوار پیام نشون داده شده.",
                is_user=False,
            )
        elif self._loading:
            self._add_bubble("در حال بارگذاری مدل هوش مصنوعی...", is_user=False)
        elif self._model_ready and not self.history:
            self._add_bubble("آماده‌ام! هر سوالی داری بپرس ✨", is_user=False)

    # ---------- دانلود و بارگذاری مدل ----------

    def _start_download(self):
        download_model(
            self.model_path,
            url=DEFAULT_MODEL_URL,
            on_progress=self._on_download_progress,
            on_status=self._on_download_status,
            on_done=self._on_download_done,
            on_error=self._on_download_error,
        )

    @mainthread
    def _on_download_progress(self, fraction):
        self.ids.status_label.text = rtl(f"در حال دانلود مدل... {int(fraction * 100)}٪")
        self.ids.status_label.color = (0.10, 0.9, 0.9, 1)

    @mainthread
    def _on_download_status(self, message):
        # پیام‌های میانی مثل «تلاش دوباره...» وقتی اتصال قطع/کند میشه ولی
        # هنوز تلاش برای دانلود ادامه داره (retry خودکار).
        self.ids.status_label.text = rtl(message)
        self.ids.status_label.color = (1, 0.75, 0.2, 1)

    @mainthread
    def _on_download_done(self):
        self.ids.status_label.text = ""
        if self.username:
            self._add_bubble("دانلود تموم شد ✦ دارم مدل رو بارگذاری می‌کنم...", is_user=False)
        threading.Thread(target=self._load_model, daemon=True).start()

    @mainthread
    def _on_download_error(self, err):
        self._loading = False
        self._model_error = str(err)
        self.ids.status_label.text = rtl(f"خطا در دانلود مدل: {err}")
        self.ids.status_label.color = (1, 0.4, 0.5, 1)
        if self.username:
            self._add_bubble(
                f"⚠️ دانلود مدل بعد از چند بار تلاش ناموفق بود:\n{err}\n"
                "اگه از فیلترشکن استفاده می‌کنی روشنش کن، یا بعداً دوباره اپ رو باز کن "
                "(دانلود از همون‌جا که مونده ادامه پیدا می‌کنه).",
                is_user=False,
            )

    def _load_model(self):
        ok = self.engine.load()
        self._on_model_loaded(ok)

    @mainthread
    def _on_model_loaded(self, ok):
        self._loading = False
        if ok:
            self._model_ready = True
            if self.username and not self.history:
                self._add_bubble("آماده‌ام! هر سوالی داری بپرس ✨", is_user=False)
        else:
            self._model_error = self.engine.load_error or "خطای نامشخص در بارگذاری مدل"
            self.ids.status_label.text = rtl(self._model_error)
            if self.username:
                self._add_bubble(
                    "⚠️ نتونستم مدل رو بارگذاری کنم. جزئیات خطا بالای نوار پیام نشون داده شده.",
                    is_user=False,
                )

    # ---------- گفتگو ----------

    def open_upload_menu(self):
        """یک پنجره‌ی کوچک با دو گزینه‌ی «عکس از گالری» و «دوربین» باز می‌کند."""
        box = BoxLayout(orientation="vertical", spacing=12, padding=16)

        gallery_btn = Factory.NeonButton()
        gallery_btn.text = rtl("انتخاب عکس")
        gallery_btn.size_hint_y = None
        gallery_btn.height = "50sp"

        camera_btn = Factory.NeonButton()
        camera_btn.text = rtl("گرفتن عکس با دوربین")
        camera_btn.size_hint_y = None
        camera_btn.height = "50sp"

        box.add_widget(gallery_btn)
        box.add_widget(camera_btn)

        popup = Popup(
            title=rtl("چه‌جوری می‌خوای عکس اضافه کنی؟"),
            title_font=FA_FONT_PATH,
            content=box,
            size_hint=(0.8, 0.4),
        )

        def _pick_gallery(*_):
            popup.dismiss()
            self.open_image_picker()

        def _pick_camera(*_):
            popup.dismiss()
            self.open_camera()

        gallery_btn.bind(on_release=_pick_gallery)
        camera_btn.bind(on_release=_pick_camera)
        popup.open()

    def open_image_picker(self):
        """با plyer، انتخاب‌گر بومی همون پلتفرم رو باز می‌کند (گالری اندروید،
        اکسپلورر ویندوز، Finder مک). اگر plyer نصب نبود، به یک انتخاب‌گر
        ساده‌ی داخلی Kivy برمی‌گردد."""
        if plyer_filechooser is not None:
            try:
                plyer_filechooser.open_file(
                    on_selection=self._on_file_selected,
                    filters=[["Images", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.webp"]],
                )
                return
            except Exception:  # noqa: BLE001
                pass
        self._open_fallback_picker()

    @mainthread
    def _on_file_selected(self, selection):
        if not selection:
            return
        self._add_image_bubble(selection[0], is_user=True)
        self.history.append({"role": "user", "content": "[کاربر یک عکس پیوست کرد]"})

    def _open_fallback_picker(self):
        """انتخاب‌گر جایگزین، فقط برای وقتی که plyer در دسترس نیست."""
        chooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"])
        box = BoxLayout(orientation="vertical", spacing=8)
        box.add_widget(chooser)
        pick_btn = Factory.NeonButton()
        pick_btn.text = rtl("انتخاب این عکس")
        pick_btn.size_hint_y = None
        pick_btn.height = "44sp"
        box.add_widget(pick_btn)

        popup = Popup(
            title=rtl("انتخاب عکس"),
            title_font=FA_FONT_PATH,
            content=box,
            size_hint=(0.9, 0.9),
        )

        def _choose(*_):
            if chooser.selection:
                self._add_image_bubble(chooser.selection[0], is_user=True)
                self.history.append({"role": "user", "content": "[کاربر یک عکس پیوست کرد]"})
            popup.dismiss()

        pick_btn.bind(on_release=_choose)
        popup.open()

    def open_camera(self):
        """گرفتن عکس با دوربین دستگاه (روی اندروید: دوربین گوشی؛ روی
        دسکتاپ اگر وبکم/دوربین در دسترس و پشتیبانی‌شده باشد)."""
        if plyer_camera is None:
            self._add_bubble("⚠️ دوربین روی این دستگاه در دسترس نیست.", is_user=False)
            return

        out_dir = os.path.join(os.path.expanduser("~"), ".nova_ai_offline", "camera")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"photo_{int(time.time())}.jpg")

        try:
            plyer_camera.take_picture(filename=path, on_complete=self._on_camera_done)
        except NotImplementedError:
            self._add_bubble("⚠️ دوربین روی این دستگاه پشتیبانی نمی‌شه.", is_user=False)
        except Exception as exc:  # noqa: BLE001
            self._add_bubble(f"⚠️ خطا در باز کردن دوربین: {exc}", is_user=False)

    @mainthread
    def _on_camera_done(self, path):
        if path and os.path.exists(path):
            self._add_image_bubble(path, is_user=True)
            self.history.append({"role": "user", "content": "[کاربر یک عکس گرفت]"})

    def send_message(self):
        text = self.ids.msg_input.text.strip()
        if not text:
            return
        self.ids.msg_input.text = ""
        self._add_bubble(text, is_user=True)

        if self._loading:
            self._add_bubble("⏳ صبر کن، مدل هنوز داره بارگذاری می‌شه...", is_user=False)
            return
        if not self.engine.is_ready():
            self._add_bubble("⚠️ مدل بارگذاری نشده. نصب و مسیر مدل رو بررسی کن.", is_user=False)
            return

        mode_label = self.ids.mode_spinner.text
        mode = MODE_MAP.get(mode_label, "general")
        self.history.append({"role": "user", "content": text})

        thinking_bubble = self._add_bubble("در حال فکر کردن...", is_user=False)
        threading.Thread(
            target=self._generate_reply, args=(text, mode, thinking_bubble), daemon=True
        ).start()

    def _generate_reply(self, text, mode, thinking_bubble):
        try:
            memory = profile_manager.load_memory(self.username) if self.username else ""
            reply = self.engine.generate(
                text,
                mode=mode,
                history=self.history,
                memory=memory,
                username=self.username,
            )
            if not reply or not reply.strip():
                reply = "⚠️ مدل پاسخ خالی برگرداند."
        except Exception as exc:  # noqa: BLE001
            reply = f"⚠️ خطا در تولید پاسخ: {exc}"

        self.history.append({"role": "assistant", "content": reply})
        self._update_bubble(thinking_bubble, reply)

        if self.username:
            profile_manager.save_history(self.username, self.history)
            self._exchange_count += 1
            if self._exchange_count % MEMORY_EVERY_N_EXCHANGES == 0:
                threading.Thread(target=self._update_memory, daemon=True).start()

    def _update_memory(self):
        """چند خط آخر مکالمه را می‌گیرد و خلاصه‌ی نکات مهم را در حافظه‌ی
        بلندمدت کاربر ذخیره می‌کند. این کار بی‌صدا در پس‌زمینه انجام می‌شود."""
        recent = self.history[-6:]
        summary = self.engine.generate(
            "خلاصه‌ی نکات مهم رو بنویس.", mode="memory_extract", history=recent
        )
        if summary and "هیچ" not in summary.strip()[:10]:
            profile_manager.append_memory(self.username, summary)

    def _add_image_bubble(self, image_path, is_user):
        bubble = Factory.ImageBubble()
        bubble.image_source = image_path
        bubble.is_user = is_user
        bubble.size_hint_x = 0.72
        bubble.pos_hint = {"right": 1} if is_user else {"x": 0}
        self.ids.chat_box.add_widget(bubble)
        self._scroll_to_bottom()
        return bubble

    def _add_bubble(self, text, is_user):
        bubble = Factory.ChatBubble()
        bubble.text = wrap_rtl(text)
        bubble.is_user = is_user
        bubble.size_hint_x = 0.82
        bubble.pos_hint = {"right": 1} if is_user else {"x": 0}
        self.ids.chat_box.add_widget(bubble)
        self._scroll_to_bottom()
        return bubble

    @mainthread
    def _update_bubble(self, bubble, text):
        bubble.text = wrap_rtl(text)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        self.ids.scroll.scroll_y = 0


class NovaAIApp(App):
    def build(self):
        Window.clearcolor = (0.02, 0.01, 0.05, 1)
        self.icon = "assets/images/logo.png"
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(RootScreen(name="chat"))
        sm.current = "splash"
        return sm


if __name__ == "__main__":
    NovaAIApp().run()
