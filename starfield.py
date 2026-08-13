"""
starfield.py
------------
پس‌زمینه‌ی انیمیشنی سایبرپانک/کهکشانی: گرادیان بنفش-مشکی-فیروزه‌ای
به‌همراه ستاره‌ها و ذرات نورانی معلق که به‌آرامی چشمک می‌زنند و شناور می‌شوند.
سبک، بدون نیاز به هیچ تصویر خارجی (همه چیز با canvas کشیده می‌شود).
"""

import random
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.clock import Clock
from kivy.properties import NumericProperty

NEON_COLORS = [
    (0.53, 0.15, 0.95, 1),   # بنفش نئونی
    (0.10, 0.85, 0.92, 1),   # فیروزه‌ای/سایان
    (0.95, 0.15, 0.55, 1),   # صورتی مگنتا
    (1.00, 1.00, 1.00, 1),   # سفید
]


class Star:
    __slots__ = ("x", "y", "radius", "color", "phase", "speed", "drift")

    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.radius = random.uniform(1, 3.2)
        self.color = random.choice(NEON_COLORS)
        self.phase = random.uniform(0, 6.28)
        self.speed = random.uniform(1.5, 3.0)
        self.drift = random.uniform(-4, 4)


class StarField(Widget):
    n_stars = NumericProperty(140)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stars = []
        self._t = 0
        self.bind(size=self._rebuild, pos=self._rebuild)
        Clock.schedule_once(self._rebuild, 0)
        Clock.schedule_interval(self._animate, 1 / 30)

    def _rebuild(self, *args):
        if self.width <= 0 or self.height <= 0:
            return
        self.stars = [Star(self.width, self.height) for _ in range(int(self.n_stars))]
        self._draw()

    def _animate(self, dt):
        self._t += dt
        if not self.stars:
            return
        for s in self.stars:
            s.y -= s.speed * dt * 12
            s.x += s.drift * dt
            if s.y < -5:
                s.y = self.height + 5
                s.x = random.uniform(0, self.width)
            if s.x < -5:
                s.x = self.width + 5
            elif s.x > self.width + 5:
                s.x = -5
        self._draw()

    def _draw(self):
        import math
        self.canvas.clear()
        with self.canvas:
            # پس‌زمینه‌ی تیره‌ی پایه (فضای عمیق) — بدون ابرهای نبولا،
            # طبق خواسته فقط ذرات معلق باقی می‌مانند
            Color(0.02, 0.01, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)

            for s in self.stars:
                twinkle = 0.5 + 0.5 * math.sin(self._t * s.speed + s.phase)
                r, g, b, a = s.color
                Color(r, g, b, a * (0.25 + 0.75 * twinkle))
                rad = s.radius * (0.7 + 0.6 * twinkle)
                Ellipse(pos=(self.x + s.x - rad, self.y + s.y - rad), size=(rad * 2, rad * 2))
