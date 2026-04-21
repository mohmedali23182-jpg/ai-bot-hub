# AI Bot Hub

بوت Python Webhook منظم وموسع، يعمل على Railway، ويدعم مزودات ذكاء متعددة.

## المزايا
- Webhook حقيقي بدل polling
- Background task لمعالجة التحديثات بسرعة بدون تعليق endpoint
- Retry للتحميلات والطلبات الخارجية
- Dashboard + healthz + metrics
- Provider architecture:
  - `gemini`
  - `openai_compatible` (مثل OpenAI / Groq / OpenRouter / Together إذا كان endpoint متوافقاً)
- تخزين سياق وإحصاءات بـ SQLite
- أوضاع: نص، صور، صوت، فيديو، كود

## متغيرات البيئة الأساسية
- `TELEGRAM_BOT_TOKEN`
- `BASE_URL`
- `TELEGRAM_WEBHOOK_SECRET`
- `DASHBOARD_PASSWORD`
- `AI_PROVIDER`
- `AI_API_KEY`

## أمثلة المزودات
### Gemini
```env
AI_PROVIDER=gemini
AI_API_KEY=YOUR_GEMINI_KEY
AI_MODEL_TEXT=gemini-2.5-flash
AI_MODEL_VISION=gemini-2.5-flash
AI_MODEL_AUDIO=gemini-2.5-flash
AI_MODEL_VIDEO=gemini-2.5-flash
AI_MODEL_CODE=gemini-2.5-flash
```

### OpenAI-compatible
```env
AI_PROVIDER=openai_compatible
AI_API_KEY=YOUR_PROVIDER_KEY
OPENAI_COMPAT_BASE_URL=https://api.openai.com/v1
AI_MODEL_TEXT=gpt-4.1-mini
AI_MODEL_VISION=gpt-4.1-mini
AI_MODEL_AUDIO=gpt-4.1-mini
AI_MODEL_VIDEO=gpt-4.1-mini
AI_MODEL_CODE=gpt-4.1-mini
```

## التشغيل المحلي
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## النشر على Railway
1. ارفع المشروع إلى GitHub.
2. اختر Deploy from GitHub repo.
3. أضف المتغيرات في Variables.
4. ولّد دومين وضعه في `BASE_URL`.
5. افتح `/` ثم ثبت الويب هوك.

## ملفات المشروع
- `app/config.py`
- `app/providers/`
- `app/services/telegram.py`
- `app/services/handlers.py`
- `app/web/routes.py`
- `app/main.py`
