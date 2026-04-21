def prompt_for_kind(kind: str, caption: str = '') -> str:
    caption = (caption or '').strip()
    prompts = {
        'image': 'حلل هذه الصورة بدقة واستخرج النصوص والعناصر المهمة بالعربية.',
        'audio': 'حلل هذا الملف الصوتي. فرّغه إن أمكن ثم لخّصه بالعربية.',
        'video': 'حلل هذا الفيديو. لخّص أهم ما فيه بالعربية.',
        'document': 'حلل هذا الملف واستخرج أهم المعلومات بالعربية.',
    }
    base = prompts.get(kind, 'حلل هذا المحتوى بالعربية.')
    return f'{base}\n\nتعليمات المستخدم: {caption}' if caption else base


def welcome_text() -> str:
    return (
        'أهلاً بك في AI Bot Hub\\n\\n'
        'الأوضاع:\\n'
        '• /mode_text\\n• /mode_image\\n• /mode_audio\\n• /mode_video\\n• /mode_code\\n\\n'
        'أوامر إضافية:\\n• /help\\n• /status\\n• /clear\\n• /dashboard'
    )


def help_text() -> str:
    return (
        'هذا بوت Python Webhook مهيأ لRailway ومصمم ليكون مستقراً وقابلاً للتوسعة.\\n'
        'يدعم أكثر من مزود ذكاء عبر AI_PROVIDER.'
    )
