import telebot
import json
import os
import sys
import subprocess

API_TOKEN = '8643931610:AAE-eKzjdyFMDcOMtURgLQpIdrx3s6crQ4c'
OWNER_ID = 8121720867
bot = telebot.TeleBot(API_TOKEN)

DATA_FILE = "bot_data.json"
FILE_NAME = sys.argv[0]

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"admins": {}, "commands": {}, "auto_reply": ""}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()
user_state = {}

def is_owner(user_id):
    return user_id == OWNER_ID

# --- نظام فحص وتعديل الكود ---

@bot.message_handler(commands=['editcode'])
def edit_code(message):
    if not is_owner(message.from_user.id): return
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        code = f.read()
    with open("current_code.txt", "w", encoding="utf-8") as tmp:
        tmp.write(code)
    with open("current_code.txt", "rb") as doc:
        bot.send_document(message.chat.id, doc, caption="انسخ الكود، عدله، ثم أرسله بعد ضغط /save")

@bot.message_handler(commands=['save'])
def save_new_code(message):
    if not is_owner(message.from_user.id): return
    msg = bot.reply_to(message, "أرسل الكود الجديد كاملاً كرسالة نصية لفحصه:")
    bot.register_next_step_handler(msg, check_and_apply)

def check_and_apply(message):
    new_code = message.text
    temp_file = "temp_test.py"
    
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(new_code)
    
    # محاولة فحص الكود برمجياً قبل تشغيله
    try:
        # استخدام compile للتأكد من عدم وجود أخطاء Syntax
        compile(new_code, temp_file, 'exec')
        
        # إذا نجح الفحص، نقوم بتبديل الملفات
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write(new_code)
        
        bot.send_message(message.chat.id, "✅ الكود سليم برمجياً وتم حفظه. اضغط /restartbot لتطبيقه.")
        if os.path.exists(temp_file): os.remove(temp_file)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في الكود الجديد! لن يتم الحفظ.\n\nنوع الخطأ:\n{str(e)}")
        if os.path.exists(temp_file): os.remove(temp_file)

@bot.message_handler(commands=['restartbot'])
def restart_bot(message):
    if not is_owner(message.from_user.id): return
    bot.send_message(message.chat.id, "♻️ جاري إعادة التشغيل...")
    os.execv(sys.executable, ['python'] + sys.argv)

# --- الأوامر الأساسية ---

@bot.message_handler(commands=['rsala'])
def set_auto_reply(message):
    if not (is_owner(message.from_user.id) or str(message.from_user.id) in db.get("admins", {})): return
    msg = bot.reply_to(message, "أرسل الرد العام (أو 'تعطيل'):")
    bot.register_next_step_handler(msg, save_auto_reply)

def save_auto_reply(message):
    db["auto_reply"] = "" if message.text == "تعطيل" else message.text
    save_data(db)
    bot.send_message(message.chat.id, "✅ تم التحديث.")

@bot.message_handler(commands=['new'])
def new_cmd(message):
    if not (is_owner(message.from_user.id) or str(message.from_user.id) in db.get("admins", {})): return
    msg = bot.reply_to(message, "اكتب الكلمة المفتاحية:")
    user_state[message.chat.id] = {'step': 1}
    bot.register_next_step_handler(msg, step_1)

def step_1(message):
    user_state[message.chat.id]['key'] = message.text
    msg = bot.send_message(message.chat.id, "اكتب الرد المطلوب:")
    bot.register_next_step_handler(msg, step_2)

def step_2(message):
    key = user_state[message.chat.id]['key']
    db["commands"][key] = {"text": message.text, "type": "all"}
    save_data(db)
    bot.send_message(message.chat.id, "✅ تم الحفظ.")
    del user_state[message.chat.id]

def handle_logic(message):
    if db.get("auto_reply") and not message.text.startswith('/'):
        try: bot.send_message(message.chat.id, db["auto_reply"])
        except: pass
    if message.text in db["commands"]:
        cmd = db["commands"][message.text]
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, cmd["text"])
        except: pass

@bot.message_handler(func=lambda m: True)
def p_m(m): handle_logic(m)

@bot.channel_post_handler(func=lambda m: True)
def c_m(m): handle_logic(m)

print("-------- تم تشغيل البوت بنجاح -----------")
bot.polling(non_stop=True)
