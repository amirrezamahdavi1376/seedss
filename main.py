import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# توکن ربات و کلید OpenAI رو از متغیر محیطی می‌گیریم
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# آدرس پایه API تلگرام
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

# یه دیکشنری ساده برای نگهداری پروژه‌ها (بعداً می‌تونی به دیتابیس منتقل کنی)
PROJECTS = {
    'طراحی': 'یک لوگو برای کافی‌شاپی به نام "صبح" طراحی کن. رنگ‌های ملایم و قهوه‌ای مد نظر صاحب کاره.',
    'برنامه‌نویسی': 'یک تابع پایتون بنویس که اعداد زوج یک لیست را برگرداند.',
    'ترجمه': 'متن زیر را به انگلیسی روان ترجمه کن: "ایران کشوری با تاریخ و فرهنگ غنی است."'
}

def send_message(chat_id, text):
    """ارسال پیام به کاربر"""
    url = f'{TELEGRAM_API_URL}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    requests.post(url, json=payload)

def get_ai_feedback(project_description, user_answer):
    """گرفتن بازخورد از OpenAI"""
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    prompt = f"""You are a professional freelance mentor. The user was given this project: "{project_description}". They submitted this response: "{user_answer}". Give constructive feedback in Persian (formal but friendly). Include:
- Positive points
- Suggestions for improvement
- A score out of 100
Keep it concise but helpful."""
    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7,
        'max_tokens': 500
    }
    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"متأسفانه خطایی رخ داد: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    """مسیری که تلگرام آپدیت‌ها رو بهش می‌فرسته"""
    update = request.get_json()
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '')

        # اگه کاربر /start زد
        if text == '/start':
            welcome_msg = "به ربات مربی فریلنسری خوش اومدی!\n"
            welcome_msg += "یکی از مهارت‌ها رو انتخاب کن:\n"
            welcome_msg += "طراحی\nبرنامه‌نویسی\nترجمه"
            send_message(chat_id, welcome_msg)
            return 'OK'

        # بررسی اینکه آیا کاربر یکی از مهارت‌ها رو انتخاب کرده
        if text in PROJECTS:
            # پروژه رو براش بفرست
            project = PROJECTS[text]
            send_message(chat_id, f"پروژه {text}:\n\n{project}\n\nپاسخت رو ارسال کن.")
            # اینجا می‌تونیم وضعیت کاربر رو ذخیره کنیم که منتظر پاسخش هستیم. برای سادگی، فعلاً از حافظه ساده استفاده می‌کنیم.
            # ما از یه دیکشنری گلوبال استفاده می‌کنیم (با احتیاط!)
            if not hasattr(app, 'user_projects'):
                app.user_projects = {}
            app.user_projects[chat_id] = {'skill': text, 'project': project}
            return 'OK'

        # اگر کاربر در حال ارسال پاسخ به یه پروژه باشه
        if hasattr(app, 'user_projects') and chat_id in app.user_projects:
            skill = app.user_projects[chat_id]['skill']
            project = app.user_projects[chat_id]['project']
            user_answer = text

            # گرفتن بازخورد از هوش مصنوعی
            feedback = get_ai_feedback(project, user_answer)
            send_message(chat_id, f"بازخورد منتور:\n\n{feedback}")

            # پاک کردن وضعیت کاربر
            del app.user_projects[chat_id]

            # پیشنهاد پروژه جدید
            send_message(chat_id, "می‌تونی پروژه بعدی رو انتخاب کنی:\nطراحی\nبرنامه‌نویسی\nترجمه")
            return 'OK'

        # در غیر این صورت، پیام نامفهوم
        send_message(chat_id, "دستور نامفهوم. لطفاً یکی از گزینه‌ها رو انتخاب کن یا /start بزن.")
    return 'OK'

@app.route('/')
def index():
    return "ربات فعال است!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))