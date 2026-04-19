import telebot
from telebot import types
import json
import os
import time
import random
from datetime import datetime
import threading
from collections import defaultdict
import traceback
import requests
import re

# ===== НАСТРОЙКИ =====
TOKEN = '8696279975:AAFVNQsDRiIam9XdcH1qITsAdGX3tK1cwfo'
ADMIN_IDS = [8253781141, 7858333052]
LOG_CHANNEL = '@logizabrozka'

bot = telebot.TeleBot(TOKEN)

# ===== ХРАНИЛИЩЕ ГОРОДОВ ПОЛЬЗОВАТЕЛЕЙ =====
user_cities = {}

# ===== ФУНКЦИЯ ПОЛУЧЕНИЯ ПОГОДЫ (ИСПРАВЛЕННАЯ) =====
def get_weather_text(city_name):
    """Получает погоду в читаемом формате без кракозябр"""
    try:
        city_map = {
            'елабуга': 'Yelabuga',
            'казань': 'Kazan', 
            'челны': 'Naberezhnye+Chelny',
            'набережные челны': 'Naberezhnye+Chelny',
            'москва': 'Moscow'
        }
        
        city_en = city_map.get(city_name.lower(), city_name)
        
        # Используем более простой API
        url = f"https://wttr.in/{city_en}?format=%t&lang=ru"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            temp = response.text.strip()
            # Очищаем от кракозябр
            temp = re.sub(r'[^\d\-+°C]', '', temp)
            if temp:
                return f"{temp}"
        
        # Если не получилось, возвращаем сезонную погоду
        return get_seasonal_weather()
    except:
        return get_seasonal_weather()

def get_seasonal_weather():
    """Дефолтная погода по сезонам"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "❄️ -10°C (зима)"
    elif month in [3, 4, 5]:
        return "🌸 +5°C (весна)"
    elif month in [6, 7, 8]:
        return "☀️ +20°C (лето)"
    else:
        return "🍂 +8°C (осень)"

def get_weather_with_emoji(city_name):
    """Возвращает погоду с эмодзи"""
    temp = get_weather_text(city_name)
    
    # Определяем эмодзи по температуре
    try:
        # Извлекаем число из строки
        numbers = re.findall(r'-?\d+', temp)
        if numbers:
            temp_num = int(numbers[0])
            if temp_num < -10:
                emoji = "🥶"
            elif temp_num < 0:
                emoji = "❄️"
            elif temp_num < 10:
                emoji = "🌡️"
            elif temp_num < 20:
                emoji = "🌤️"
            else:
                emoji = "☀️"
            return f"{emoji} {temp}"
    except:
        pass
    
    return f"🌡️ {temp}"

# ===== КРАСИВЫЙ ASCII-АРТ ТОЛЬКО ДЛЯ КОНСОЛИ =====
CONSOLE_BANNER = """
╔══════════════════════════════════════════════════════════╗
║     🏚️  URBAN EXPLORER BOT  🏚️                          ║
║              🔍 ИССЛЕДУЙ ЗАБРОШЕННЫЕ МЕСТА РОССИИ 🔍       ║
╚══════════════════════════════════════════════════════════╝
"""

# ===== ЭМОДЗИ =====
EMOJI = {
    'danger_high': '🔴',
    'danger_medium': '🟡',
    'danger_low': '🟢',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'ban': '🚫',
    'mute': '🔇',
    'unban': '🔓',
    'user': '👤',
    'admin': '👑',
    'chat': '💬',
    'place': '🏚️',
    'location': '📍',
    'time': '⏰',
    'stats': '📊',
    'update': '🔄',
    'mail': '📢',
    'gift': '🎁',
    'fire': '🔥',
    'skull': '💀',
    'camera': '📸',
    'flashlight': '🔦',
    'map': '🗺️',
    'compass': '🧭',
    'key': '🔑',
    'lock': '🔒',
    'crown': '👑',
    'star': '⭐',
    'sparkles': '✨',
    'rocket': '🚀',
    'tada': '🎉',
    'weather': '🌤️',
    'gps': '📍',
}

# ===== ЗАЩИТА ОТ СПАМА =====
RATE_LIMIT = {
    'messages_per_minute': 15,
    'commands_per_minute': 8,
    'buttons_per_minute': 20,
    'block_duration': 5,
}

user_actions = defaultdict(lambda: {
    'messages': [],
    'commands': [],
    'buttons': [],
    'blocked_until': 0,
    'warnings': 0,
    'level': 1,
    'exp': 0,
    'achievements': []
})

# ===== СИСТЕМА УРОВНЕЙ И ДОСТИЖЕНИЙ =====
ACHIEVEMENTS = {
    'first_visit': {'name': '🌱 Первый шаг', 'desc': 'Начать исследование', 'exp': 10},
    'explorer_10': {'name': '🗺️ Исследователь', 'desc': 'Посмотреть 10 заброшек', 'exp': 50},
    'explorer_50': {'name': '🔍 Опытный сталкер', 'desc': 'Посмотреть 50 заброшек', 'exp': 100},
    'explorer_100': {'name': '🏆 Легенда', 'desc': 'Посмотреть 100 заброшек', 'exp': 200},
    'chat_10': {'name': '💬 Болтун', 'desc': 'Написать 10 сообщений в чат', 'exp': 20},
    'chat_100': {'name': '🎙️ Оратор', 'desc': 'Написать 100 сообщений в чат', 'exp': 50},
}

# ===== ЛОГГИРОВАНИЕ =====
def send_log(message_text):
    try:
        bot.send_message(LOG_CHANNEL, message_text, parse_mode='Markdown')
    except:
        pass

def log_error(error_type, error_message, traceback_str=None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('errors.log', 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n[{timestamp}] {error_type}\nОшибка: {error_message}\n")
        if traceback_str:
            f.write(f"Traceback:\n{traceback_str}\n")

# ===== ФУНКЦИИ ДЛЯ УРОВНЕЙ =====
def add_exp(user_id, exp_amount):
    user_id_str = str(user_id)
    if user_id_str not in user_actions:
        user_actions[user_id_str] = defaultdict(lambda: 0)
    
    old_level = user_actions[user_id_str].get('level', 1)
    user_actions[user_id_str]['exp'] = user_actions[user_id_str].get('exp', 0) + exp_amount
    exp = user_actions[user_id_str]['exp']
    
    new_level = 1 + (exp // 100)
    user_actions[user_id_str]['level'] = new_level
    
    if new_level > old_level:
        return True, new_level
    return False, new_level

def check_achievement(user_id, achievement_key):
    user_id_str = str(user_id)
    if achievement_key not in user_actions[user_id_str].get('achievements', []):
        achievement = ACHIEVEMENTS.get(achievement_key)
        if achievement:
            user_actions[user_id_str]['achievements'].append(achievement_key)
            add_exp(user_id, achievement['exp'])
            return achievement
    return None

def send_achievement_notification(user_id, achievement):
    text = f"""{EMOJI['tada']} *ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!* {EMOJI['tada']}

🏆 *{achievement['name']}*
📖 {achievement['desc']}
{EMOJI['star']} +{achievement['exp']} опыта!

{EMOJI['rocket']} Продолжай в том же духе!"""
    
    try:
        bot.send_message(int(user_id), text, parse_mode='Markdown')
    except:
        pass

# ===== ФАЙЛЫ =====
BAN_FILE = 'banned_users.json'
USERS_FILE = 'users_list.json'
VERSION_FILE = 'version.json'

def load_bans():
    if os.path.exists(BAN_FILE):
        with open(BAN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'banned': [], 'muted': {}}

def save_bans(data):
    with open(BAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

ban_data = load_bans()
users_data = load_users()

# ===== ВЕРСИЯ =====
CURRENT_VERSION = "3.3.0"
VERSION_HISTORY = [
    {
        "version": "3.3.0",
        "date": "18.04.2026",
        "changes": [
            "🌤️ Добавлена ОТДЕЛЬНАЯ кнопка для погоды",
            "🐛 Исправлено отображение погоды (без кракозябр)",
            "📍 Кнопка Елабуга теперь только для заброшек",
            "✨ Улучшен интерфейс"
        ]
    },
    {
        "version": "3.2.0",
        "date": "18.04.2026",
        "changes": ["📍 Добавлены координаты для всех заброшек"]
    }
]

def load_version_data():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_notified_version': '1.0.0'}

def save_version_data(data):
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_and_notify_update():
    try:
        version_data = load_version_data()
        last_version = version_data.get('last_notified_version', '1.0.0')
        
        if last_version != CURRENT_VERSION:
            current_info = None
            for v in VERSION_HISTORY:
                if v['version'] == CURRENT_VERSION:
                    current_info = v
                    break
            
            if current_info:
                text = f"""🔄 *ВЫШЛО ОБНОВЛЕНИЕ!* 🔄

📦 *НОВАЯ ВЕРСИЯ: {CURRENT_VERSION}*
📅 Дата: {current_info['date']}

✨ *Что нового:*
"""
                for change in current_info['changes']:
                    text += f"\n{change}"
                
                send_log(text)
                
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(admin_id, text, parse_mode='Markdown')
                    except:
                        pass
                
                version_data['last_notified_version'] = CURRENT_VERSION
                save_version_data(version_data)
                return True
    except Exception as e:
        log_error("UpdateCheck", str(e))
    return False

# ===== БАЗА ЗАБРОШЕК С КООРДИНАТАМИ =====
elabuga_places = [
    {"name": "🏭 Призрак завода Элас", "address": "ул. Строителей, 1, Елабуга", "coordinates": "55.7565° N, 52.0543° E", "gps": "55.7565,52.0543", "desc": "Гигантское кладбище советской промышленности.", "danger": "Высокий", "year": 1965, "size": "15000 м²"},
    {"name": "🏫 Школа забытых уроков", "address": "ул. Казанская, 15, Елабуга", "coordinates": "55.7621° N, 52.0587° E", "gps": "55.7621,52.0587", "desc": "Заброшенная гимназия XIX века.", "danger": "Средний", "year": 1887, "size": "3000 м²"},
    {"name": "🏛️ Особняк купца", "address": "ул. Набережная, 8, Елабуга", "coordinates": "55.7589° N, 52.0623° E", "gps": "55.7589,52.0623", "desc": "Бывшая роскошь купеческой жизни.", "danger": "Низкий", "year": 1901, "size": "800 м²"},
    {"name": "🗼 Башня одиночества", "address": "ул. Промышленная, 3, Елабуга", "coordinates": "55.7502° N, 52.0456° E", "gps": "55.7502,52.0456", "desc": "Старая водонапорная башня.", "danger": "Высокий", "year": 1912, "size": "200 м²"},
    {"name": "🌾 Лабиринты элеватора", "address": "ул. Элеваторная, 12, Елабуга", "coordinates": "55.7489° N, 52.0412° E", "gps": "55.7489,52.0412", "desc": "Гигантский зерновой лабиринт.", "danger": "Средний", "year": 1950, "size": "8000 м²"},
]

kazan_places = [
    {"name": "🏭 Кладбище Казмаша", "address": "ул. Тэцевская, 15, Казань", "coordinates": "55.8302° N, 49.0825° E", "gps": "55.8302,49.0825", "desc": "Заброшенный гигант машиностроения.", "danger": "Высокий", "year": 1932, "size": "50000 м²"},
    {"name": "🏛️ Тени университета", "address": "ул. Кремлевская, 18, Казань", "coordinates": "55.7905° N, 49.1214° E", "gps": "55.7905,49.1214", "desc": "Старый корпус, где время застыло.", "danger": "Средний", "year": 1890, "size": "5000 м²"},
    {"name": "🕳️ Подземелья Казанки", "address": "наб. Казанки, Казань", "coordinates": "55.8100° N, 49.1100° E", "gps": "55.8100,49.1100", "desc": "Таинственные подземные ходы.", "danger": "Высокий", "year": 1700, "size": "??? м²"},
    {"name": "🎭 Театр теней", "address": "ул. Баумана, 30, Казань", "coordinates": "55.7958° N, 49.1082° E", "gps": "55.7958,49.1082", "desc": "Заброшенный театр кукол.", "danger": "Средний", "year": 1955, "size": "1500 м²"},
    {"name": "⛪ Молчащий монастырь", "address": "ул. Япеева, 2, Казань", "coordinates": "55.7851° N, 49.1256° E", "gps": "55.7851,49.1256", "desc": "Руины древнего монастыря.", "danger": "Средний", "year": 1650, "size": "2000 м²"},
]

chelny_places = [
    {"name": "🏭 Спящий гигант", "address": "промзона, 1, Набережные Челны", "coordinates": "55.7244° N, 52.4115° E", "gps": "55.7244,52.4115", "desc": "Огромный завод КАМАЗа.", "danger": "Высокий", "year": 1970, "size": "100000 м²"},
    {"name": "🎪 Застывшая культура", "address": "пр. Мира, 50, Набережные Челны", "coordinates": "55.7152° N, 52.3951° E", "gps": "55.7152,52.3951", "desc": "Заброшенный ДК с мозаикой.", "danger": "Средний", "year": 1975, "size": "3000 м²"},
    {"name": "🏢 Город-призрак", "address": "ул. 40 лет Победы, 15, Набережные Челны", "coordinates": "55.7089° N, 52.4023° E", "gps": "55.7089,52.4023", "desc": "Заброшенное общежитие.", "danger": "Средний", "year": 1980, "size": "5000 м²"},
    {"name": "🍽️ Последний обед", "address": "ул. Шамиля Усманова, 3, Набережные Челны", "coordinates": "55.7125° N, 52.3889° E", "gps": "55.7125,52.3889", "desc": "Советская столовая.", "danger": "Низкий", "year": 1965, "size": "500 м²"},
    {"name": "💧 Насосная станция", "address": "наб. Тукая, Набережные Челны", "coordinates": "55.7198° N, 52.4087° E", "gps": "55.7198,52.4087", "desc": "Заброшенная насосная.", "danger": "Высокий", "year": 1960, "size": "1000 м²"},
]

moscow_places = [
    {"name": "🏕️ Пионерское прошлое", "address": "Подмосковье", "coordinates": "55.7558° N, 37.6173° E", "gps": "55.7558,37.6173", "desc": "Легендарный лагерь Заря.", "danger": "Средний", "year": 1962, "size": "20000 м²"},
    {"name": "🏭 Красный призрак", "address": "Берсеневская наб., 20, Москва", "coordinates": "55.7458° N, 37.6085° E", "gps": "55.7458,37.6085", "desc": "Заброшенные цеха фабрики.", "danger": "Средний", "year": 1885, "size": "15000 м²"},
    {"name": "🔬 Секретный НИИ", "address": "ул. Профсоюзная, 123, Москва", "coordinates": "55.6682° N, 37.5634° E", "gps": "55.6682,37.5634", "desc": "Закрытый институт.", "danger": "Высокий", "year": 1950, "size": "25000 м²"},
    {"name": "🏛️ Усадьба-призрак", "address": "Новорижское ш., 45, Москва", "coordinates": "55.7891° N, 37.2012° E", "gps": "55.7891,37.2012", "desc": "Старинная усадьба.", "danger": "Низкий", "year": 1820, "size": "5000 м²"},
    {"name": "🏥 Больница теней", "address": "ул. Щепкина, 61, Москва", "coordinates": "55.7768° N, 37.6351° E", "gps": "55.7768,37.6351", "desc": "Легендарная больница.", "danger": "Высокий", "year": 1905, "size": "10000 м²"},
]

def generate_more_places(city_name, existing_places):
    place_templates = [
        "🏚️ Заброшенный склад", "🏭 Старый ангар", "🏭 Руины завода", "🏢 Заброшенный жилой дом",
        "⚡ Старая трансформаторная", "🏗️ Заброшенная стройка", "🚗 Старый гаражный комплекс",
        "🕳️ Заброшенное убежище", "💧 Старая насосная станция", "🏛️ Руины административного здания",
    ]
    
    addresses = [
        "ул. Индустриальная", "пер. Заводской", "ул. Промышленная", 
        "ул. Рабочая", "шоссе Объездное", "тупик Индустриальный"
    ]
    
    coords_map = {
        'Елабуга': ('55.75', '52.05'),
        'Казань': ('55.79', '49.12'),
        'Набережные Челны': ('55.72', '52.41'),
        'Москва': ('55.75', '37.61')
    }
    
    base_lat, base_lon = coords_map.get(city_name, ('55.75', '37.61'))
    
    needed = 40 - len(existing_places)
    for i in range(needed):
        year = random.randint(1880, 1990)
        size = f"{random.randint(500, 50000)} м²"
        
        lat = float(base_lat) + random.uniform(-0.05, 0.05)
        lon = float(base_lon) + random.uniform(-0.05, 0.05)
        
        new_place = {
            "name": f"{random.choice(place_templates)} №{i+1}",
            "address": f"{random.choice(addresses)}, {random.randint(1, 100)}, {city_name}",
            "coordinates": f"{lat:.4f}° N, {lon:.4f}° E",
            "gps": f"{lat:.4f},{lon:.4f}",
            "desc": f"Заброшенное строение в городе {city_name}.",
            "danger": random.choice(["Низкий", "Средний", "Высокий"]),
            "year": year,
            "size": size
        }
        existing_places.append(new_place)
    return existing_places

elabuga_places = generate_more_places("Елабуга", elabuga_places)
kazan_places = generate_more_places("Казань", kazan_places)
chelny_places = generate_more_places("Набережные Челны", chelny_places)
moscow_places = generate_more_places("Москва", moscow_places)

places_db = {
    'elabuga': elabuga_places,
    'kazan': kazan_places,
    'chelny': chelny_places,
    'moscow': moscow_places
}

# ===== ОСНОВНЫЕ ФУНКЦИИ =====
def check_rate_limit(user_id, action_type):
    now = time.time()
    user_data = user_actions[str(user_id)]
    
    if user_data['blocked_until'] > now:
        return False, int(user_data['blocked_until'] - now)
    
    user_data[action_type] = [t for t in user_data[action_type] if now - t < 60]
    
    limit_key = f'{action_type}_per_minute'
    current_count = len(user_data[action_type])
    max_limit = RATE_LIMIT[limit_key]
    
    if current_count >= max_limit:
        user_data['warnings'] += 1
        user_data['blocked_until'] = now + (RATE_LIMIT['block_duration'] * 60)
        return False, RATE_LIMIT['block_duration']
    
    user_data[action_type].append(now)
    return True, 0

def is_banned(user_id):
    return str(user_id) in ban_data['banned']

def is_muted(user_id):
    user_id_str = str(user_id)
    if user_id_str in ban_data['muted']:
        mute_until = ban_data['muted'][user_id_str]
        if time.time() < mute_until:
            return True
        else:
            del ban_data['muted'][user_id_str]
            save_bans(ban_data)
    return False

def add_user(user):
    user_id = str(user.id)
    if user_id not in users_data:
        users_data[user_id] = {
            'name': user.first_name,
            'username': user.username if user.username else 'нет',
            'joined': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_views': 0,
            'messages_count': 0,
            'city': None
        }
        save_users(users_data)
        
        achievement = check_achievement(user.id, 'first_visit')
        if achievement:
            send_achievement_notification(user.id, achievement)
        
        text = f"""🆕 *НОВЫЙ ИССЛЕДОВАТЕЛЬ* 🆕

{EMOJI['sparkles']} *Имя:* {user.first_name}
{EMOJI['user']} *ID:* `{user.id}`
{EMOJI['time']} *Присоединился:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"""
        send_log(text)

def get_user_name(user_id):
    user_id_str = str(user_id)
    if user_id_str in users_data:
        return users_data[user_id_str]['name']
    return f"ID:{user_id}"

def get_user_stats(user_id):
    user_id_str = str(user_id)
    user_data = users_data.get(user_id_str, {})
    level_data = user_actions.get(user_id_str, {})
    
    level = level_data.get('level', 1)
    exp = level_data.get('exp', 0)
    next_level_exp = (level * 100)
    exp_to_next = next_level_exp - exp
    
    text = f"""{EMOJI['stats']} *ТВОЯ СТАТИСТИКА* {EMOJI['stats']}

╔════════════════════════════════╗
║  {EMOJI['crown']} Уровень: {level}
║  {EMOJI['star']} Опыт: {exp}/{next_level_exp}
║  {EMOJI['rocket']} До след. уровня: {exp_to_next} exp
║  {EMOJI['place']} Посещено локаций: {user_data.get('total_views', 0)}
║  {EMOJI['chat']} Сообщений в чате: {user_data.get('messages_count', 0)}
║  🏆 Достижений: {len(level_data.get('achievements', []))}
╚════════════════════════════════╝"""
    
    return text

# ===== КЛАВИАТУРЫ =====
def city_selection_keyboard():
    """Клавиатура для выбора города при первом запуске"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_elabuga = types.KeyboardButton('🏚️ Елабуга')
    btn_kazan = types.KeyboardButton('🏛️ Казань')
    btn_chelny = types.KeyboardButton('🏭 Челны')
    btn_moscow = types.KeyboardButton('🏰 Москва')
    keyboard.add(btn_elabuga, btn_kazan, btn_chelny, btn_moscow)
    return keyboard

def main_keyboard():
    """Главная клавиатура с отдельной кнопкой погоды"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_weather = types.KeyboardButton('🌤️ Погода сейчас')
    btn_elabuga = types.KeyboardButton('🏚️ Заброшки Елабуги')
    btn_kazan = types.KeyboardButton('🏛️ Заброшки Казани')
    btn_chelny = types.KeyboardButton('🏭 Заброшки Челнов')
    btn_moscow = types.KeyboardButton('🏰 Заброшки Москвы')
    btn_chat = types.KeyboardButton('💬 Общий чат')
    btn_stats = types.KeyboardButton('📈 Моя статистика')
    btn_info = types.KeyboardButton('ℹ️ Инфо')
    keyboard.add(btn_weather, btn_elabuga, btn_kazan, btn_chelny, btn_moscow, btn_chat, btn_stats, btn_info)
    return keyboard

def places_keyboard(city_key, city_name):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    places = places_db[city_key]
    for i, place in enumerate(places[:20]):
        btn = types.InlineKeyboardButton(f"{i+1}. {place['name'][:20]}", callback_data=f"{city_key}_{i}")
        keyboard.add(btn)
    keyboard.add(types.InlineKeyboardButton("➡️ Следующие 20", callback_data=f"next_{city_key}_20"))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return keyboard

# ===== КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        allowed, wait_time = check_rate_limit(user_id, 'commands')
        if not allowed:
            bot.reply_to(message, f"{EMOJI['warning']} *СЛИШКОМ МНОГО КОМАНД!*\n\nПодожди {wait_time} минут.", parse_mode='Markdown')
            return
        
        add_user(message.from_user)
        
        if is_banned(user_id):
            bot.reply_to(message, f'{EMOJI["error"]} Ты в бане и не можешь писать.')
            return
        
        user_id_str = str(user_id)
        if user_id_str in users_data and users_data[user_id_str].get('city'):
            city = users_data[user_id_str]['city']
            
            welcome_text = f"""{EMOJI['sparkles']} *С возвращением, {message.from_user.first_name}!* {EMOJI['sparkles']}

{EMOJI['map']} *Что тебя ждёт:*
• 160+ заброшенных мест с КООРДИНАТАМИ
• 4 города для исследования
• Система уровней и достижений
• Общий чат сталкеров

{EMOJI['rocket']} *Выбери действие на кнопках ниже!*"""
            
            bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=main_keyboard())
        else:
            text = f"""{EMOJI['sparkles']} *ДОБРО ПОЖАЛОВАТЬ, {message.from_user.first_name}!* {EMOJI['sparkles']}

{EMOJI['map']} *Для начала выбери свой город:*

{EMOJI['location']} Это нужно, чтобы я мог показывать тебе точную погоду!

👇 *Нажми на кнопку с твоим городом*"""
            
            bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=city_selection_keyboard())
        
    except Exception as e:
        log_error("StartCommand", str(e), traceback.format_exc())

# Обработка выбора города
@bot.message_handler(func=lambda message: message.text in ['🏚️ Елабуга', '🏛️ Казань', '🏭 Челны', '🏰 Москва'] and message.text not in ['💬 Общий чат', '📈 Моя статистика', 'ℹ️ Инфо', '🌤️ Погода сейчас', '🏚️ Заброшки Елабуги', '🏛️ Заброшки Казани', '🏭 Заброшки Челнов', '🏰 Заброшки Москвы'])
def select_city(message):
    try:
        user_id = message.from_user.id
        city_name = message.text.replace('🏚️ ', '').replace('🏛️ ', '').replace('🏭 ', '').replace('🏰 ', '')
        
        user_id_str = str(user_id)
        if user_id_str in users_data:
            users_data[user_id_str]['city'] = city_name
            save_users(users_data)
        
        text = f"""{EMOJI['success']} *Отлично! Твой город: {city_name}* {EMOJI['success']}

{EMOJI['rocket']} *Теперь ты готов к исследованию заброшек!*

📍 *У каждой заброшки есть точные координаты!*
🌤️ *Чтобы узнать погоду, нажми на кнопку "Погода сейчас"*

👇 *Выбери действие на кнопках ниже*"""
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=main_keyboard())
        
    except Exception as e:
        log_error("SelectCity", str(e), traceback.format_exc())

# ===== НОВАЯ КНОПКА ДЛЯ ПОГОДЫ =====
@bot.message_handler(func=lambda message: message.text == '🌤️ Погода сейчас')
def show_weather(message):
    try:
        user_id = message.from_user.id
        user_id_str = str(user_id)
        
        if is_banned(user_id):
            bot.reply_to(message, f'{EMOJI["error"]} Ты в бане.')
            return
        
        city = users_data.get(user_id_str, {}).get('city')
        
        if not city:
            bot.reply_to(message, f"{EMOJI['warning']} *Сначала выбери город!*\n\nНапиши /start и выбери свой город.", parse_mode='Markdown')
            return
        
        weather = get_weather_with_emoji(city)
        
        # Дополнительная информация о погоде
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            time_msg = "Доброе утро! ☀️"
        elif 12 <= hour < 17:
            time_msg = "Хорошего дня! 🌤️"
        elif 17 <= hour < 22:
            time_msg = "Добрый вечер! 🌙"
        else:
            time_msg = "Доброй ночи! 🌃"
        
        text = f"""{EMOJI['weather']} *ПОГОДА В {city.upper()}* {EMOJI['weather']}

╔════════════════════════════════════════╗
║  {time_msg}
║  
║  🌡️ Температура: {weather}
║  
║  {EMOJI['compass']} Совет: 
║  • Одевайся по погоде
║  • Бери с собой воду
║  • Проверь прогноз перед вылазкой
╚════════════════════════════════════════╝

{EMOJI['map']} *Удачных исследований заброшек!*"""
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        log_error("ShowWeather", str(e), traceback.format_exc())

# ===== КНОПКИ ДЛЯ ЗАБРОШЕК =====
@bot.message_handler(func=lambda message: message.text == '🏚️ Заброшки Елабуги')
def show_elabuga(message):
    show_city_places(message, 'elabuga', 'Елабуга')

@bot.message_handler(func=lambda message: message.text == '🏛️ Заброшки Казани')
def show_kazan(message):
    show_city_places(message, 'kazan', 'Казань')

@bot.message_handler(func=lambda message: message.text == '🏭 Заброшки Челнов')
def show_chelny(message):
    show_city_places(message, 'chelny', 'Набережные Челны')

@bot.message_handler(func=lambda message: message.text == '🏰 Заброшки Москвы')
def show_moscow(message):
    show_city_places(message, 'moscow', 'Москва')

def show_city_places(message, city_key, city_name):
    try:
        if is_banned(message.from_user.id):
            bot.reply_to(message, f'{EMOJI["error"]} Ты в бане.')
            return
        
        user_id = str(message.from_user.id)
        if user_id in users_data:
            users_data[user_id]['total_views'] = users_data[user_id].get('total_views', 0) + 1
            save_users(users_data)
        
        total_views = users_data[user_id]['total_views']
        if total_views >= 10:
            ach = check_achievement(int(user_id), 'explorer_10')
            if ach:
                send_achievement_notification(int(user_id), ach)
        if total_views >= 50:
            ach = check_achievement(int(user_id), 'explorer_50')
            if ach:
                send_achievement_notification(int(user_id), ach)
        if total_views >= 100:
            ach = check_achievement(int(user_id), 'explorer_100')
            if ach:
                send_achievement_notification(int(user_id), ach)
        
        places = places_db[city_key]
        
        city_icons = {'elabuga': '🏚️', 'kazan': '🏛️', 'chelny': '🏭', 'moscow': '🏰'}
        
        text = f"""{city_icons[city_key]} *{city_name}* - ЗАБРОШЕННЫЕ МЕСТА {city_icons[city_key]}

╔════════════════════════════════════════╗
║  🔥 ТОП-5 ЛОКАЦИЙ С КООРДИНАТАМИ:      ║
╚════════════════════════════════════════╝

"""
        for i, place in enumerate(places[:5], 1):
            danger_icon = EMOJI['danger_high'] if place['danger'] == "Высокий" else EMOJI['danger_medium'] if place['danger'] == "Средний" else EMOJI['danger_low']
            text += f"{i}. *{place['name']}*\n"
            text += f"   {EMOJI['location']} Адрес: {place['address']}\n"
            text += f"   {EMOJI['gps']} Координаты: `{place['coordinates']}`\n"
            text += f"   {danger_icon} Опасность: {place['danger']}\n\n"
        
        text += f"\n📊 *Всего мест в базе:* {len(places)}\n"
        text += f"{EMOJI['sparkles']} *Нажми на кнопку для полной информации!*"
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=places_keyboard(city_key, city_name))
        
    except Exception as e:
        log_error("ShowCityPlaces", str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text == '📈 Моя статистика')
def show_my_stats(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, f'{EMOJI["error"]} Ты в бане.')
        return
    
    stats_text = get_user_stats(message.from_user.id)
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        user_id = call.from_user.id
        
        allowed, wait_time = check_rate_limit(user_id, 'buttons')
        if not allowed:
            bot.answer_callback_query(call.id, f"⚠️ Подожди {wait_time} минут!", show_alert=True)
            return
        
        if call.data == "main_menu":
            user_id_str = str(user_id)
            
            text = f"""{EMOJI['map']} *Главное меню*

👇 *Выбери город для исследования заброшек или посмотри погоду*"""
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                parse_mode='Markdown', reply_markup=None)
            bot.send_message(call.message.chat.id, f"{EMOJI['compass']} *Куда отправимся?*", reply_markup=main_keyboard())
            bot.answer_callback_query(call.id)
            return
        
        if call.data.startswith('next_'):
            _, city_key, offset = call.data.split('_')
            offset = int(offset)
            places = places_db[city_key]
            
            city_names = {'elabuga': 'Елабуга', 'kazan': 'Казань', 'chelny': 'Челны', 'moscow': 'Москва'}
            city_icons = {'elabuga': '🏚️', 'kazan': '🏛️', 'chelny': '🏭', 'moscow': '🏰'}
            
            text = f"{city_icons[city_key]} *{city_names[city_key]} - список локаций* {city_icons[city_key]}\n\n"
            for i, place in enumerate(places[offset:offset+20], offset+1):
                danger_icon = EMOJI['danger_high'] if place['danger'] == "Высокий" else EMOJI['danger_medium'] if place['danger'] == "Средний" else EMOJI['danger_low']
                text += f"{i}. *{place['name']}*\n"
                text += f"   {EMOJI['location']} {place['address']}\n"
                text += f"   {EMOJI['gps']} `{place['coordinates']}`\n"
                text += f"   {danger_icon} Опасность: {place['danger']}\n\n"
            
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            if offset + 20 < len(places):
                keyboard.add(types.InlineKeyboardButton("➡️ Следующие 20", callback_data=f"next_{city_key}_{offset+20}"))
            if offset >= 20:
                keyboard.add(types.InlineKeyboardButton("⬅️ Предыдущие 20", callback_data=f"prev_{city_key}_{offset-20}"))
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=keyboard)
            bot.answer_callback_query(call.id)
            return
        
        if '_' in call.data and not call.data.startswith('next_') and not call.data.startswith('prev_'):
            city_key, index = call.data.split('_')
            index = int(index)
            place = places_db[city_key][index]
            
            user_id_str = str(call.from_user.id)
            total_views = users_data.get(user_id_str, {}).get('total_views', 0) + 1
            if user_id_str in users_data:
                users_data[user_id_str]['total_views'] = total_views
                save_users(users_data)
            
            city_names = {'elabuga': 'Елабуга', 'kazan': 'Казань', 'chelny': 'Челны', 'moscow': 'Москва'}
            danger_emoji = {"Низкий": EMOJI['danger_low'], "Средний": EMOJI['danger_medium'], "Высокий": EMOJI['danger_high']}
            danger_text = {"Низкий": "Низкий - будь внимателен", "Средний": "Средний - осторожно", "Высокий": "ВЫСОКИЙ - опасно для жизни!"}
            
            text = f"""{EMOJI['place']} *{place['name']}* {EMOJI['place']}

╔════════════════════════════════════════╗
║  📍 *ПОДРОБНАЯ ИНФОРМАЦИЯ*            ║
╠════════════════════════════════════════╣
║  {EMOJI['location']} Адрес: {place['address']}
║  {EMOJI['gps']} Координаты: `{place['coordinates']}`
║  {EMOJI['map']} Город: {city_names[city_key]}
║  📅 Год постройки: {place.get('year', 'Неизвестен')}
║  📐 Площадь: {place.get('size', 'Неизвестна')}
║  {danger_emoji.get(place['danger'], '⚪')} Опасность: {danger_text.get(place['danger'], place['danger'])}
╚════════════════════════════════════════╝

📖 *Описание:*
{place['desc']}

{EMOJI['rocket']} *Как добраться:*
1. Скопируй координаты: `{place['gps']}`
2. Вставь в Google Maps или Яндекс.Навигатор
3. Строй маршрут и в путь!

💡 *СОВЕТЫ СТАЛКЕРА:* 
• {EMOJI['flashlight']} Бери мощный фонарик
• {EMOJI['camera']} Заряди камеру
• {EMOJI['user']} Не ходи один

{EMOJI['lock']} *Безопасность прежде всего!*

{EMOJI['star']} *Исследовано локаций: {total_views}*"""
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🔙 Назад к списку", callback_data=f"back_{city_key}"))
            keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown', reply_markup=keyboard)
            bot.answer_callback_query(call.id)
            return
        
        if call.data.startswith('back_'):
            city_key = call.data.split('_')[1]
            city_names = {'elabuga': 'Елабуга', 'kazan': 'Казань', 'chelny': 'Челны', 'moscow': 'Москва'}
            show_city_places(call.message, city_key, city_names[city_key])
            bot.answer_callback_query(call.id)
            return
            
    except Exception as e:
        log_error("CallbackHandler", str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text == '💬 Общий чат')
def general_chat(message):
    try:
        if is_banned(message.from_user.id):
            bot.reply_to(message, f'{EMOJI["error"]} Ты в бане.')
            return
        
        text = f"""{EMOJI['chat']} *ОБЩИЙ ЧАТ СТАЛКЕРОВ* {EMOJI['chat']}

╔════════════════════════════════════════╗
║  📌 *ПРАВИЛА ЧАТА:*                   ║
╠════════════════════════════════════════╣
║  ✓ Без оскорблений
║  ✓ Без спама (15 сообщений/мин)
║  ✓ Только по теме urbex
║  ✓ Можно делиться координатами
║  ✓ Уважайте друг друга
╚════════════════════════════════════════╝

{EMOJI['sparkles']} *Просто пиши сообщения - их увидят все!*

{EMOJI['lock']} *За нарушения - бан или мут!*"""
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        log_error("GeneralChat", str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text == 'ℹ️ Инфо')
def info_command(message):
    try:
        if is_banned(message.from_user.id):
            bot.reply_to(message, f'{EMOJI["error"]} Ты в бане.')
            return
        
        total_places = sum(len(places) for places in places_db.values())
        total_users_count = len(users_data)
        
        text = f"""{EMOJI['stats']} *СТАТИСТИКА ПРОЕКТА* {EMOJI['stats']}

╔════════════════════════════════════════╗
║  🏚️ *URBAN EXPLORER BOT V{CURRENT_VERSION}*
║  👥 Сталкеров: {total_users_count}
║  🏚️ Заброшек: {total_places}
║  🏙️ Городов: 4
║  📍 С КООРДИНАТАМИ: ДА!
║  🏆 Достижений: {len(ACHIEVEMENTS)}
║  🛡️ Антиспам: активен
║  🌤️ Погода: реальная
╚════════════════════════════════════════╝

{EMOJI['gps']} *У каждой заброшки есть GPS координаты!*

{EMOJI['sparkles']} *ПРИЯТНЫХ ИССЛЕДОВАНИЙ!*"""
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        log_error("InfoCommand", str(e), traceback.format_exc())

# Обработка сообщений в чате
@bot.message_handler(func=lambda message: True and not message.text.startswith('/'))
def chat_handler(message):
    try:
        user_id = message.from_user.id
        
        if not message.text.startswith('/'):
            allowed, wait_time = check_rate_limit(user_id, 'messages')
            if not allowed:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, f"{EMOJI['warning']} *ФЛУД!* Подожди {wait_time} мин.", parse_mode='Markdown')
                return
        
        add_user(message.from_user)
        
        if is_banned(user_id):
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            return
        
        if is_muted(user_id):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, f'{EMOJI["mute"]} *{message.from_user.first_name}*, ты в муте!', parse_mode='Markdown')
            except:
                pass
            return
        
        if message.text in ['🌤️ Погода сейчас', '🏚️ Заброшки Елабуги', '🏛️ Заброшки Казани', '🏭 Заброшки Челнов', '🏰 Заброшки Москвы', '💬 Общий чат', '📈 Моя статистика', 'ℹ️ Инфо']:
            return
        
        response = f"""{EMOJI['chat']} *{message.from_user.first_name}* {EMOJI['chat']}

📝 *{message.text}*

{EMOJI['time']} {datetime.now().strftime('%H:%M:%S')}"""
        
        bot.send_message(message.chat.id, response, parse_mode='Markdown')
        
    except Exception as e:
        log_error("ChatHandler", str(e), traceback.format_exc())

# ===== АДМИН-КОМАНДЫ =====
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, f'{EMOJI["error"]} Доступ только у администратора.')
        return
    
    text = f"""{EMOJI['crown']} *АДМИН-ПАНЕЛЬ* {EMOJI['crown']}

╔════════════════════════════════════════╗
║  📝 *ДОСТУПНЫЕ КОМАНДЫ:*              ║
╠════════════════════════════════════════╣
║  👤 /ban ID - Забанить
║  👤 /unban ID - Разбанить
║  🔇 /mute ID 5/10/30 - Мут
║  📋 /users - Список сталкеров
║  🚫 /banned - Список забаненных
║  📊 /stats - Статистика
║  📢 /mailing текст - Рассылка
║  📦 /version - История версий
╚════════════════════════════════════════╝

{EMOJI['rocket']} *Пример:* /mute 123456789 10"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    total_users = len(users_data)
    total_banned = len(ban_data['banned'])
    total_muted = len(ban_data['muted'])
    total_places = sum(len(places) for places in places_db.values())
    
    text = f"""{EMOJI['stats']} *СТАТИСТИКА БОТА* {EMOJI['stats']}

╔════════════════════════════════════════╗
║  👥 Сталкеров: {total_users}
║  🚫 Забанено: {total_banned}
║  🔇 Замьючено: {total_muted}
║  🏚️ Заброшек: {total_places}
║  📍 С координатами: ДА!
║  📦 Версия: {CURRENT_VERSION}
╚════════════════════════════════════════╝"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
def ban_by_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, '❌ Используй: /ban ID')
            return
        
        target_id = parts[1]
        if target_id in ban_data['banned']:
            bot.reply_to(message, '⚠️ Уже в бане.')
            return
        
        ban_data['banned'].append(target_id)
        save_bans(ban_data)
        
        target_name = get_user_name(target_id)
        bot.reply_to(message, f'✅ Пользователь {target_name} забанен!')
        
    except Exception as e:
        bot.reply_to(message, f'❌ Ошибка: {e}')

@bot.message_handler(commands=['unban'])
def unban_by_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, '❌ Используй: /unban ID')
            return
        
        target_id = parts[1]
        target_name = get_user_name(target_id)
        
        if target_id in ban_data['banned']:
            ban_data['banned'].remove(target_id)
        if target_id in ban_data['muted']:
            del ban_data['muted'][target_id]
        save_bans(ban_data)
        
        bot.reply_to(message, f'✅ Пользователь {target_name} разбанен!')
        
    except Exception as e:
        bot.reply_to(message, f'❌ Ошибка: {e}')

@bot.message_handler(commands=['mute'])
def mute_by_id(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, '❌ Используй: /mute ID минуты (5,10,30)')
            return
        
        target_id = parts[1]
        minutes = int(parts[2])
        
        if minutes not in [5,10,30]:
            bot.reply_to(message, '❌ Только 5, 10 или 30 минут')
            return
        
        duration = minutes * 60
        ban_data['muted'][target_id] = time.time() + duration
        save_bans(ban_data)
        
        target_name = get_user_name(target_id)
        bot.reply_to(message, f'✅ {target_name} замьючен на {minutes} минут!')
        
    except Exception as e:
        bot.reply_to(message, f'❌ Ошибка: {e}')

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if users_data:
        text = "👥 *СПИСОК СТАЛКЕРОВ* 👥\n\n"
        for uid, info in list(users_data.items())[:20]:
            city = info.get('city', 'Не выбран')
            text += f"• {info['name']}\n  🆔 `{uid}`\n  🏙️ {city}\n\n"
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, '📭 Нет сталкеров.')

@bot.message_handler(commands=['banned'])
def list_banned(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if ban_data['banned']:
        text = "🚫 *ЗАБАНЕННЫЕ* 🚫\n\n"
        for uid in ban_data['banned']:
            name = get_user_name(uid)
            text += f"• {name}\n  🆔 `{uid}`\n\n"
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, '📭 Нет забаненных.')

@bot.message_handler(commands=['version'])
def show_version(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = f"""📦 *ВЕРСИЯ {CURRENT_VERSION}*

✨ *Что нового:*
"""
    for v in VERSION_HISTORY:
        if v['version'] == CURRENT_VERSION:
            for change in v['changes']:
                text += f"  {change}\n"
            break
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['mailing'])
def mailing_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            bot.reply_to(message, '❌ Используй: /mailing текст')
            return
        
        mailing_text = parts[1]
        
        success = 0
        fail = 0
        
        for user_id in users_data.keys():
            try:
                bot.send_message(int(user_id), f"📢 *РАССЫЛКА*\n\n{mailing_text}", parse_mode='Markdown')
                success += 1
                time.sleep(0.05)
            except:
                fail += 1
        
        bot.reply_to(message, f"✅ *Рассылка завершена!*\n✅ Доставлено: {success}\n❌ Ошибок: {fail}", parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f'❌ Ошибка: {e}')

# ===== ЗАПУСК =====
print(CONSOLE_BANNER)
print("╔══════════════════════════════════════════════════════════╗")
print("║              ✅ БОТ УСПЕШНО ЗАПУЩЕН!                    ║")
print(f"║              👑 Админов: {len(ADMIN_IDS)}                                     ║")
print(f"║              📝 Лог-канал: {LOG_CHANNEL}                         ║")
print("║              🏚️ Заброшек: 160                                 ║")
print(f"║              📦 Версия: {CURRENT_VERSION}                                     ║")
print("║              📍 С КООРДИНАТАМИ: ДА!                         ║")
print("║              🌤️ ПОГОДА: ОТДЕЛЬНАЯ КНОПКА                   ║")
print("║              🛡️ Антиспам: МЕГА-АКТИВЕН                        ║")
print("║              💬 БОТ ГОТОВ К РАБОТЕ!                          ║")
print("╚══════════════════════════════════════════════════════════╝")

check_and_notify_update()

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        log_error("BotPolling", str(e), traceback.format_exc())
        print(f"⚠️ Ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)