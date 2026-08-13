# Nova AI — دستیار هوش مصنوعی آفلاین (Kivy)

اپی با تم سایبرپانک/کهکشانی، ستاره‌های متحرک، و ۴ حالت گفتگو:
داستان‌نویسی، حل مسائل علمی، همراه احساسی، و پاسخ‌گویی عمومی.
موتور آن یک مدل زبانی کوچک به‌صورت **کاملاً آفلاین** (فرمت GGUF از طریق
llama-cpp-python) است.

## ساختار پروژه
```
ai_companion/
├── main.py          # اپ اصلی Kivy
├── llm_engine.py     # لایه‌ی ارتباط با مدل GGUF
├── starfield.py       # پس‌زمینه‌ی ستاره‌های متحرک
├── theme.kv           # استایل سایبرپانک
├── requirements.txt
├── buildozer.spec      # تنظیمات بیلد اندروید
└── assets/models/       # اینجا فایل .gguf را قرار دهید
```

## ۰) رفع مشکل فونت/متن فارسی (مهم — قبل از هرچیز)

اگر متن فارسی به‌صورت مربع‌های خالی یا حروف جدا و برعکس نمایش داده می‌شود،
دو کار لازم است:

**۱. نصب کتابخانه‌های شکل‌دهی متن راست‌به‌چپ:**
```bash
pip install arabic-reshaper python-bidi
```
(این‌ها به `requirements.txt` اضافه شده‌اند.)

**۲. دانلود یک فونت فارسی و قرار دادنش در پروژه:**
فونت پیشنهادی، رایگان و متن‌باز: **Vazirmatn**
- از اینجا دانلود کنید: https://github.com/rastikerdar/vazirmatn/releases
  (فایل `Vazirmatn-Regular.ttf` را از پوشه‌ی فونت‌ها بردارید)
- آن را دقیقاً در این مسیر قرار دهید:
```
ai_companion/assets/fonts/Vazirmatn-Regular.ttf
```
پوشه‌ی `assets/fonts` را اگر وجود ندارد بسازید. کد از قبل تنظیم شده تا
این فونت را برای همه‌ی متن‌ها (عنوان، حباب‌های چت، دکمه‌ها، اسپینر) استفاده کند.

**۳. حل تایپ به‌هم‌ریخته (این‌بار کامل):**
باکس ارسال پیام حالا از یک ویجت سفارشی به اسم `PersianTextInput`
(داخل `farsi_widgets.py`) استفاده می‌کند که حین تایپ، حروف فارسی را
به‌صورت زنده می‌چسباند. متنی که واقعاً ذخیره و به هوش مصنوعی ارسال
می‌شود همیشه صحیح است؛ تنها ریزنکته‌ی احتمالی این است که روی جمله‌های
خیلی طولانی، خط چشمک‌زن مکان‌نما ممکن است چند پیکسل با گلیف واقعی
هم‌تراز نباشد (چون عرض گلیف چسبیده کمی با حالت جدا فرق دارد) — این فقط
ظاهری‌ست و کارکرد را خراب نمی‌کند.

> این override به متد داخلی `_create_line_label` در `TextInput` تکیه
> دارد که ممکن است بین نسخه‌های مختلف Kivy کمی فرق کند. نسخه‌ی پین‌شده
> در `requirements.txt` (۲.۳.۱) تست شده در نظر گرفته شده؛ اگر با نسخه‌ی
> دیگری از Kivy اجرا کردید و ارور گرفتید، متنش رو برام بفرستید.



## ۱) اجرا روی ویندوز / لینوکس / مک (توسعه و تست)

```bash
python -m venv venv
venv\Scripts\activate        # ویندوز
pip install -r requirements.txt
```

مدل پیش‌فرض که اپ خودش دانلود می‌کند: **Qwen2.5-7B-Instruct** (حدود ۴.۷
گیگابایت، به‌مراتب باهوش‌تر و فارسی روان‌تر از نسخه‌های کوچک‌تر — برای
اجرای روان به حداقل ۸ گیگابایت رم نیاز دارد). اگر می‌خواهید مدل دیگری
امتحان کنید:
- `Qwen2.5-3B-Instruct-Q4_K_M.gguf` (سبک‌تر، برای سیستم‌های ضعیف‌تر)
- `Phi-4-mini-Q4_K_M.gguf` (استدلال قوی‌تر برای ریاضی/فیزیک)

فایل را در `App.user_data_dir/models/qwen3-0.6b-q4-k-m.gguf` قرار دهید، سپس:
```bash
python main.py
```

## ۲) ساخت فایل اجرایی ویندوز (.exe)

```bash
pyinstaller --onefile --windowed --name NovaAI ^
  --add-data "theme.kv;." --add-data "assets;assets" main.py
```
خروجی در پوشه‌ی `dist/` قرار می‌گیرد. (روی لینوکس/مک از `:` به‌جای `;` استفاده کنید.)

## ۳) ساخت APK اندروید — مهم‌ترین بخش

Buildozer فقط روی **لینوکس** (یا WSL) کار می‌کند:
```bash
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config
pip install buildozer cython
```

### گام ۱: کراس‌کامپایل llama-server با NDK (فقط یک‌بار لازم است)

چون `llama-cpp-python` پکیج/recipe رسمی برای اندروید ندارد، به‌جایش فقط
باینری `llama-server` را کامپایل می‌کنیم (خود llama.cpp، بدون بایندینگ پایتون)
و آن را به‌عنوان یک کتابخانه‌ی نیتیو داخل APK جا می‌دهیم. اپ در زمان اجرا
این باینری را اجرا کرده و از طریق HTTP روی `127.0.0.1` باهاش صحبت می‌کند —
یعنی هیچ داده‌ای از گوشی خارج نمی‌شود و کاملاً آفلاین می‌ماند.

```bash
> ⚠️ لینک‌های دانلود مستقیم NDK هر از گاهی توسط گوگل عوض/حذف می‌شن. اگه
> این لینک هم در آینده کار نکرد، آخرین نسخه‌ی LTS رو از
> https://developer.android.com/ndk/downloads بردارید و به‌جای `r27d`
> همه‌جا (اینجا و در `buildozer.spec`) شماره‌ی نسخه‌ی جدید رو بذارید.

```bash
# دانلود مستقیم:
# wget https://dl.google.com/android/repository/android-ndk-r27d-linux.zip
# unzip android-ndk-r27d-linux.zip
export ANDROID_NDK=/path/to/android-ndk-r27d

git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# بیلد برای arm64-v8a (اکثر گوشی‌های جدید)
cmake -B build-arm64 \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-arm64 --target llama-server -j$(nproc)

# بیلد برای armeabi-v7a (گوشی‌های قدیمی‌تر، اختیاری)
cmake -B build-armv7 \
  -DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=armeabi-v7a -DANDROID_PLATFORM=android-24 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-armv7 --target llama-server -j$(nproc)
```

### گام ۲: قرار دادن باینری‌ها در پروژه

خروجی‌ها را با نام `libllama_server.so` (نام باید با `lib` شروع و با
`.so` تمام شود تا اندروید اجازه‌ی اجرا بدهد) در این مسیرها کپی کنید:
```bash
mkdir -p ai_companion/libs/arm64-v8a ai_companion/libs/armeabi-v7a
cp llama.cpp/build-arm64/bin/llama-server ai_companion/libs/arm64-v8a/libllama_server.so
cp llama.cpp/build-armv7/bin/llama-server ai_companion/libs/armeabi-v7a/libllama_server.so
```
این مسیرها از قبل در `buildozer.spec` با `android.add_libs_*` رجیستر شده‌اند.

### گام ۳: بیلد نهایی
```bash
cd ai_companion
buildozer android debug
```
خروجی APK در `bin/` ساخته می‌شود. اپ در اولین اجرا مدل GGUF را (طبق
`model_downloader.py`) یک‌بار دانلود می‌کند و از آن به بعد کاملاً آفلاین
کار می‌کند — همان الگویی که اپ‌های شناخته‌شده‌ای مثل PocketPal AI و
MLC Chat استفاده می‌کنند.

> نکته: کد `llm_engine_android.py` مسیر باینری را با `pyjnius` از
> `nativeLibraryDir` اپ پیدا می‌کند، آن را اجرا و صبر می‌کند تا سرور
> آماده شود، سپس درخواست‌های چت را با فرمت OpenAI-compatible
> (`/v1/chat/completions`) به آن می‌فرستد — دقیقاً همان API که
> `llama_engine.py` روی دسکتاپ تولید می‌کند، پس منطق `main.py` بدون
> تغییر روی هر دو پلتفرم کار می‌کند.

## ۴) انتشار در کافه‌بازار و مایکت
- ثبت‌نام به‌عنوان توسعه‌گر در [Cafe Bazaar](https://developers.cafebazaar.ir)
  و [Myket](https://developer.myket.ir)
- APK امضاشده (`buildozer android release` + `jarsigner`/`apksigner`) آماده کنید.
- آیکون، اسکرین‌شات، توضیحات فارسی و سیاست حریم خصوصی (چون داده‌ی
  کاربر لوکال است، همین را در توضیحات بنویسید که مزیت رقابتی است).
- هر دو مارکت اپ رایگان یا پولی را قبول می‌کنند؛ چک کردن قوانین محتوای
  حساس (مشاور احساسی) در پالیسی هر مارکت پیش از انتشار توصیه می‌شود.

## نکات مهم درباره‌ی «مشاور احساسی»
چون این حالت با سلامت روانی کاربران سروکار دارد، پیشنهاد می‌کنم:
- در همان صفحه‌ی اول اپ تذکر بدهید که این یک هوش مصنوعی است، نه جایگزین
  روان‌شناس یا روان‌پزشک.
- برای موقعیت‌های بحرانی (افکار خودآزاری و مشابه)، شماره‌های اورژانس/خط
  بحران کشور خودتان را در پرامپت سیستمی یا یک صفحه‌ی جداگانه قرار دهید.


## مدل موبایل
مدل پیش‌فرض این نسخه Qwen3-0.6B Q4_K_M است و داخل APK قرار نمی‌گیرد. لینک و SHA-256 در `config/model_config.json` نگهداری می‌شود. مدل در storage پایدار اپ ذخیره می‌شود و با ویرایش کد یا انتشار APK جدید دوباره دانلود نمی‌شود. دانلود Resume دارد و رابط کاربری مقدار MB، درصد و سرعت را نمایش می‌دهد.

برای تغییر مدل، فقط `config/model_config.json` را تغییر بده و برای جلوگیری از استفاده‌ی اشتباهی از مدل قدیمی، `filename` را نسخه‌دار نگه دار.
