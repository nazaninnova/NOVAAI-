[app]
title = Nova AI
package.name = novaai
package.domain = org.nazaninova
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json,ttf
version = 1.0
requirements = python3,kivy,requests,pyjnius,plyer
orientation = portrait
fullscreen = 0

android.permissions = INTERNET, CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.allow_backup = True

# Native llama-server must be supplied before the Android build.
android.add_libs_arm64_v8a = libs/arm64-v8a/libllama_server.so

[buildozer]
log_level = 2
warn_on_root = 1
