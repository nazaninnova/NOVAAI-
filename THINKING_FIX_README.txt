NovaAI thinking fix
===================

Changes:
1) Qwen3 is requested in non-thinking mode via chat_template_kwargs={"enable_thinking": False}.
2) A compatibility fallback is included for older llama-cpp-python versions.
3) Background generation exceptions are caught so the UI cannot remain stuck on 'در حال فکر کردن...'.
4) The current username is passed into the model context.

Run:
    python main.py
