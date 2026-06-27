import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# --- НАСТРОЙКИ БОТА ---
TOKEN = '8611296615:AAEVVzrSfFHizjPkgRgPXFf0AQMxh7-_HQU'
ADMIN_ID = 913324178
# ----------------------

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask (сервер для связи с сайтом-рулеткой)
app = Flask(__name__)
CORS(app)

# Инициализация Telegram бота
tg_app = Application.builder().token(TOKEN).build()

# Глобальная переменная для хранения подкрутки админа
forced_prize_setting = None

# Ссылка на твой сайт (мы заменим её на настоящую после деплоя на Render)
WEBAPP_URL = "https://poisongift.onrender.com"

# --- БЛОК TELEGRAM БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start отправляет кнопку для открытия рулетки"""
    keyboard = [
        [InlineKeyboardButton(text="🎰 КРУТИТЬ РУЛЕТКУ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Привет! Нажми на кнопку ниже, чтобы открыть крипто-рулетку и испытать свою удачу!",
        reply_markup=reply_markup
    )

tg_app.add_handler(CommandHandler("start", start))

# --- БЛОК FLASK СЕРВЕРА ---

@app.route('/get_spin',methods=['GET'])
def get_spin():
    """Сайт спрашивает у бота, какой приз выдать игроку"""
    global forced_prize_setting
    user_id = int(request.args.get('user_id', 0))
    
    # Если админ настроил подкрутку, отдаем её и сбрасываем настройку
    if forced_prize_setting:
        prize = forced_prize_setting
        forced_prize_setting = None  # Сбрасываем после одного использования
        return jsonify({"forced_prize": prize})
    
    return jsonify({"forced_prize": None})

@app.route('/set_admin_settings', methods=['POST'])
def set_admin_settings():
    """Админка сайта отправляет команду на подкрутку"""
    global forced_prize_setting
    data = request.json
    admin_id = int(data.get('admin_id', 0))
    
    if admin_id != ADMIN_ID:
        return jsonify({"error": "Unauthorized"}), 403
        
    forced_prize_setting = data.get('next_prize') # Получаем выбранный админом приз
    return jsonify({"status": "success"})

@app.route('/result', methods=['POST'])
def result():
    """Сайт сообщает боту результат прокрутки, а бот отправляет юзеру сообщение и картинку"""
    data = request.json
    user_id = int(data.get('user_id', 0))
    username = data.get('username', 'Игрок')
    prize = data.get('prize', '')
    
    # Логика отправки картинок в зависимости от приза
    # Картинки должны лежать в той же папке на GitHub
    try:
        if "СУПЕР-ПРИЗ" in prize:
            caption = f"🎉 Поздравляем, @{username}! Вы выиграли СУПЕР-ПРИЗ!"
            photo_path = "we_open.png"  # Название твоей картинки для победы
        elif "пусто" in prize.lower() or "мимо" in prize.lower():
            caption = f"😔 Эх, @{username}, в этот раз не повезло. Попробуйте снова!"
            photo_path = "durovfarm.png" # Название твоей картинки для проигрыша
        else:
            caption = f"🎁 @{username}, ваш результат: {prize}!"
            photo_path = "durovfarm.png"

        # Отправляем сообщение пользователю через бота в фоновом режиме
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                loop.run_until_complete(tg_app.bot.send_photo(chat_id=user_id, photo=photo, caption=caption))
        else:
            loop.run_until_complete(tg_app.bot.send_message(chat_id=user_id, text=caption))
            
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")

    return jsonify({"status": "ok"})

@app.route('/')
def index():
    return "Бот работает!"

if __name__ == '__main__':
    # Запуск Flask сервера (Render сам назначит порт)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
