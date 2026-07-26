from random import randint
import telebot
import uuid
import json
import time
from datetime import datetime, timedelta
import requests
from telebot import types
from urllib.parse import quote
import threading
from typing import Dict, Optional
import sqlite3
import testt
import logging
import paramiko
import os
from dotenv import load_dotenv
from typing import Optional, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Загружаем переменные из .env
load_dotenv()


# ======= 👆НЕОБХОДИМЫЕ БИБЛИОТЕКИ👆 =======


# ======= НАСТРОЙКА ЛОГОВ ДЛЯ ПОДРОБНОЙ КОНСОЛИ =======

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========

# Настройки бота
TOKEN1 = os.getenv("TOKEN1")
TOKEN2 = os.getenv("TOKEN2")
my_id = os.getenv("my_id")
# ========== НАСТРОЙКИ КАНАЛА ==========
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
CHANNEL_URL = os.getenv("CHANNEL_URL")
SUPPORT_URL = os.getenv("SUPPORT_URL")

# ========== НАСТРОЙКИ MARZBAN ==========
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_DOMEN = os.getenv("MARZBAN_DOMEN")
USERNAME = os.getenv("MARZBAN_USERNAME")
PASSWORD = os.getenv("MARZBAN_PASSWORD")

REMNAWAVE_URL = os.getenv("REMNAWAVE_URL")
REMNAWAVE_API_TOKEN = os.getenv("REMNAWAVE_API_TOKEN")


# ========== НАСТРОЙКИ 3X-UI ==========
PANEL_URL = os.getenv("PANEL_URL")
USERNAME1 = os.getenv("XUI_USERNAME")
PASSWORD1 = os.getenv("XUI_PASSWORD")

# ========== НАСТРОЙКИ VLESS ==========
REALITY_PUBLIC_KEY = os.getenv("REALITY_PUBLIC_KEY")
SERVER_IP2 = os.getenv("SERVER_IP2")
SERVER_DOMEN2 = os.getenv("SERVER_DOMEN2")
DEFAULT_PORT2 = int(os.getenv("DEFAULT_PORT2"))
DEFAULT_SNI = os.getenv("DEFAULT_SNI")
COUNTRY_PHOTO = os.getenv("COUNTRY_PHOTO")
SERVER_IP = os.getenv("SERVER_IP")
SERVER_DOMEN = os.getenv("SERVER_DOMEN")
DEFAULT_PORT = int(os.getenv("DEFAULT_PORT"))

# ========== НАСТРОЙКИ SSH ==========
SERVER = {
    "hostname": os.getenv("SSH_HOST"),
    "port": int(os.getenv("SSH_PORT")),
    "username": os.getenv("SSH_USERNAME"),
    "password": os.getenv("SSH_PASSWORD")
}

CONFIG_PATH = os.getenv("CONFIG_PATH")

bot = telebot.TeleBot(TOKEN2)


# ========== КЛАСС ПРОВЕРКИ ПОДПИСКИ НА КАНАЛ ==========

class ChannelChecker:
    """Проверка подписки пользователя на Telegram канал"""

    @staticmethod
    def check_subscription(user_id: int) -> bool:
        """
        Проверяет, подписан ли пользователь на канал

        Args:
            user_id: ID пользователя Telegram

        Returns:
            bool: True если подписан, False если нет
        """
        try:
            member = bot.get_chat_member(
                chat_id=f"@{CHANNEL_USERNAME}",
                user_id=user_id
            )

            allowed_statuses = ['creator', 'administrator', 'member']
            is_subscribed = member.status in allowed_statuses

            logger.info(f"Проверка подписки user_id={user_id}: статус={member.status}, подписан={is_subscribed}")

            return is_subscribed

        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")

            if "chat not found" in str(e).lower():
                logger.warning("Канал не найден! Проверьте CHANNEL_USERNAME")
                return False

            if "bot is not a member" in str(e).lower():
                logger.warning("Бот не является участником канала!")
                return True

            return False

    @staticmethod
    def get_subscribe_keyboard() -> types.InlineKeyboardMarkup:
        """
        Создаёт клавиатуру для подписки на канал

        Returns:
            InlineKeyboardMarkup с кнопками
        """
        # ========== КЛАВИАТУРА ДЛЯ ПРОВЕРКИ ПОДПИСКИ ==========
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        btn_subscribe = types.InlineKeyboardButton(
            text="📢 ПОДПИСАТЬСЯ НА КАНАЛ",
            url=CHANNEL_URL
        )
        btn_check = types.InlineKeyboardButton(
            text="✅ ПРОВЕРИТЬ ПОДПИСКУ",
            callback_data="check_channel_subscription"
        )
        keyboard.add(btn_subscribe, btn_check)

        return keyboard

# ========== БАЗЫ ДАННЫХ ДЛЯ ПОДПИСОК ==========

# Хранилище данных
users_db = {}
temp_data = {}
subscription_plans = {}
active_subscriptions = {}

# ========== НАСТРОЙКИ ПОДПИСКИ ==========
class SubscriptionManager:
    """Менеджер подписок и временных протоколов"""

    def __init__(self):
        # Предустановленные тарифные планы
        self.plans = {
            "trial": {
                "name": "🔥 Пробный",
                "duration_days": 3,
                "limit_gb": 0,
                "price": 0,
                "auto_start": True  # Сразу активируется
            },
            "premium": {
                "name": "💎 Стандарт",
                "duration_days": 30,
                "limit_gb": 50,
                "price": 69,
                "auto_start": True
            },
            "premium_plus": {
                "name": "⭐️ Премиум",
                "duration_days": 30,
                "limit_gb": 0,
                "price": 69,
                "auto_start": True
            }
        }

        # Запускаем планировщик проверки подписок
        self.start_scheduler()

    def start_scheduler(self):
        """Запуск фонового планировщика"""

        def check_expired_subscriptions():
            while True:
                self._check_all_sub_by_message48()
                self._check_all_sub_by_message48_free()
                self._check_all_sub_by_message24()
                self._check_all_sub_by_message24_free()
                self._check_all_subscriptions()
                self._check_all_subscriptions_free()

                time.sleep(3600)  # Проверка каждый час

        thread = threading.Thread(target=check_expired_subscriptions, daemon=True)
        thread.start()

    def get_uuid_from_db1(self, user_id):
        """Получение UUID пользователя по ID"""
        conn = sqlite3.connect('itproger1.sql')
        cursor = conn.cursor()

        try:
            # Выполняем запрос
            cursor.execute(f"SELECT user_uuid1 FROM users WHERE user_id1 = {user_id}")
            el = cursor.fetchone()  # ВАЖНО: может быть None!

            # ОТЛАДКА: посмотрим что вернулось
            print(f"DEBUG: el = {el}")  # Покажет (None, 'my_id', 'a255b039-8e6a-4b88-907b-97a7dfc9ac8f')
            print(f"DEBUG: type(el) = {type(el)}")  # Покажет <class 'tuple'> или <class 'NoneType'>
            print(f"DEBUG: el is None = {el is None}")  # False если данные есть

            if el is None:
                print(f"❌ Пользователь с ID  не найден")
                return None

            # Проверяем количество полей в результате
            print(f"DEBUG: len(el) = {len(el)}")  # Покажет сколько полей
            print(f"DEBUG: el = {el}")  # Посмотрим всю структуру
                # Безопасное извлечение UUID
            uuid_raw = el[0]

            cursor.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
            # Преобразуем в строку и очищаем
            if uuid_raw is not None:
                uuid_1 = str(uuid_raw).replace("'", "").replace("(", "").replace(")", "").strip()
                print(f"✅ UUID извлечен: {uuid_1}")
                return uuid_1
            else:
                print("⚠️  UUID в базе данных равен None")
                return None

        except sqlite3.Error as e:
            print(f"❌ Ошибка базы данных: {e}")
            return None
        finally:
            conn.close()

    # def get_uuid_from_db2(self, user_id):
    #
    #     """Получение UUID пользователя по ID"""
    #     conn = sqlite3.connect('itproger3.sql')
    #     cursor = conn.cursor()
    #
    #     try:
    #         # Выполняем запрос
    #         cursor.execute(f"SELECT user_names1 FROM users WHERE user_id1 = {user_id}")
    #         el = cursor.fetchone()  # ВАЖНО: может быть None!
    #
    #         # ОТЛАДКА: посмотрим что вернулось
    #         print(f"DEBUG: el = {el}")  # Покажет (None, 'my_id', 'a255b039-8e6a-4b88-907b-97a7dfc9ac8f')
    #         print(f"DEBUG: type(el) = {type(el)}")  # Покажет <class 'tuple'> или <class 'NoneType'>
    #         print(f"DEBUG: el is None = {el is None}")  # False если данные есть
    #
    #         if el is None:
    #             print(f"❌ Пользователь с ID  не найден")
    #             return None
    #
    #         # Проверяем количество полей в результате
    #         print(f"DEBUG: len(el) = {len(el)}")  # Покажет сколько полей
    #         print(f"DEBUG: el = {el}")  # Посмотрим всю структуру
    #
    #         # Ваш код для извлечения UUID
    #         # el[0] = первое поле (возможно id)
    #         # el[1] = второе поле (возможно telegram_id или что-то другое)
    #         # el[2] = третье поле (возможно UUID)
    #
    #
    #             # Безопасное извлечение UUID
    #         uuid_raw = el[0]
    #         cursor.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
    #         # Преобразуем в строку и очищаем
    #         if uuid_raw is not None:
    #             uuid_1 = str(uuid_raw).replace("'", "").replace("(", "").replace(")", "").strip()
    #             print(f"✅ UUID извлечен: {uuid_1}")
    #             return uuid_1
    #         else:
    #             print("⚠️  UUID в базе данных равен None")
    #             return None
    #
    #     except sqlite3.Error as e:
    #         print(f"❌ Ошибка базы данных: {e}")
    #         return None
    #     finally:
    #         conn.close()

    def _check_all_subscriptions(self):
        """Проверка всех подписок на истечение срока"""
        current_time = datetime.now()
        expired_users = []

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "premium":
                if current_time >= datetime.fromisoformat(sub_data['expires_at']):
                    # Подписка истекла
                    a = self.deactivate_subscription(user_id)
                    expired_users.append(user_id)
                    if a:
                        bot.send_message(my_id, f"⚠️ Закончилась подписка у ПРЕМИУМ пользователя\n"
                                                f"ID: <code>{user_id}</code>",
                                         parse_mode="HTML")




        if expired_users:
            print(f"⚠️ Истекли подписки у пользователей: {expired_users}")

    def _check_all_subscriptions_free(self):
        """Проверка всех подписок на истечение срока"""
        current_time = datetime.now()
        expired_users = []

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "trial":
                if current_time >= datetime.fromisoformat(sub_data['expires_at']):
                    # Подписка истекла
                    self.deactivate_subscription_free(user_id)
                    expired_users.append(user_id)
                    #============================#
                    uuid1 = self.get_uuid_from_db1(user_id)
                    if uuid1:
                        print(f"Найден UUID: {uuid1} {user_id}")
                    else:
                        print("UUID не найден")

                    #       Запускаем удаление      #
                    #===============================#


                    print("\n✅ Операция завершена успешно!")
                    bot.send_message(chat_id=my_id,
                                         text=f"✅Пользователь удалён из конфигурации (itproger1). Временный тариф закончился🤷‍♂️\n\nUUID: <code>{uuid1}</code>\nID: <code>{user_id}</code>",
                                         parse_mode="HTML"
                        )
                    # else:
                    #     bot.send_message(chat_id=my_id,
                    #                      text=f"❌Пользователя не удалось удалить из конфигурации. Необходимо сделать это самостоятельно в 3X-UI или Marzban панели\n\nUUID1: <code>{uuid1}</code>\nID: <code>{user_id}</code>",
                    #                      parse_mode="HTML"
                    #     )
                    #     print("\n❌ Не удалось удалить пользователя")




        if expired_users:
            print(f"⚠️ Истекли подписки у пользователей: {expired_users}")

    def _check_all_sub_by_message48(self):

        new_time = datetime.now() + timedelta(hours=48)

        """Проверка всех подписок для уведомления"""
        expired_users = []

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "premium":
                if new_time >= datetime.fromisoformat(sub_data['expires_at']):
                    try:
                        conn1 = sqlite3.connect('messagePRO.sql')
                        cur1 = conn1.cursor()
                        cur1.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {user_id}")
                        data = cur1.fetchone()
                        print('извлечение -', data)
                        if data is not None:
                            cur1.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                            data1 = cur1.fetchone()
                            print('удаление -', data1)
                            conn1.commit()
                            conn1.close()  # ВАЖНО: закрываем соединение
                            # 2. Добавляем в itprogMES.sql
                            conn2 = sqlite3.connect('itprogMES_pro.sql')
                            cur2 = conn2.cursor()
                            # Создаём таблицу если нет
                            cur2.execute('''
                                                        CREATE TABLE IF NOT EXISTS users (
                                                            user_id1 TEXT PRIMARY KEY,
                                                            user_names1 TEXT
                                                        )
                                                    ''')
                            stats = "True"
                            cur2.execute("INSERT OR REPLACE INTO users (user_id1, user_names1) VALUES (?, ?)",
                                         (user_id, stats))
                            conn2.commit()
                            conn2.close()
                            kek = types.InlineKeyboardMarkup()
                            kek.add(types.InlineKeyboardButton(text="💎ПРОДЛИТЬ ПОДПИСКУ",
                                                               callback_data="continue_sub"))
                            bot.send_message(chat_id=user_id,
                                             text=
                                             "❗️ Ваша подписка истекает через 48 часов.\n"
                                             "Не забудьте продлить её по кнопке ниже 👇\n\n"
                                             "Поддержка - @MESA_VPN_support",
                                             reply_markup=kek)
                            bot.send_message(my_id, f"Уведомление ПРЕМИУМ 48 часов отправлено пользователю {user_id}")
                        else:
                            bot.send_message(my_id, f"Не удалось отправить уведомление для {user_id}")

                    except:
                        print("Не удалось отправить сообщение")


        if expired_users:
            print(f"⚠️ Истекли подписки у пользователей: {expired_users}")

    def _check_all_sub_by_message24(self):

        new_time = datetime.now() + timedelta(hours=24)

        """Проверка всех подписок для уведомления"""
        expired_users = []

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "premium":
                if new_time >= datetime.fromisoformat(sub_data['expires_at']):
                    try:
                        # Подключаемся к itprogMES.sql и удаляем пользователя
                        conn = sqlite3.connect('itprogMES_pro.sql')
                        cur = conn.cursor()
                        cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {user_id}")
                        data = cur.fetchone()

                        if data is not None:
                            cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                            conn.commit()

                            conn.close()  # ВАЖНО: закрываем соединение

                            kek = types.InlineKeyboardMarkup()
                            kek.add(types.InlineKeyboardButton(text="💎ПРОДЛИТЬ ПОДПИСКУ",
                                                               callback_data="continue_sub"))
                            bot.send_message(chat_id=user_id,
                                             text=
                                             "❗️ Ваша подписка истекает через 24 часа.\n"
                                             "Не забудьте продлить её по кнопке ниже 👇\n\n"
                                             "Поддержка - @MESA_VPN_support",
                                             reply_markup=kek)
                            bot.send_message(my_id, f"Уведомление ПРЕМИУМ 24 часа отправлено пользователю {user_id}")
                        else:
                            bot.send_message(my_id, "Уведомление не может быть отправлено. Пользователя нет в itprogerMES_pro")
                    except:
                        # conn = sqlite3.connect('itprogMES_pro.sql')
                        # cur = conn.cursor()
                        # cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                        # conn.commit()
                        # conn.close()  # ВАЖНО: закрываем соединение
                        print("Не удалось отправить уведомление")


        if expired_users:
            print(f"⚠️ Истекли подписки у пользователей: {expired_users}")

    def _check_all_sub_by_message48_free(self):
        """Триал: уведомление за 48 часов (только 1 раз, НЕ УДАЛЯЕМ из актуальной БД)"""

        new_time = datetime.now() + timedelta(hours=48)

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "trial":
                if new_time >= datetime.fromisoformat(sub_data['expires_at']):
                    try:
                        # 1. Проверяем и удаляем из message.sql если есть
                        conn1 = sqlite3.connect('message.sql')
                        cur1 = conn1.cursor()
                        cur1.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {user_id}")
                        data = cur1.fetchone()
                        print('извлечение -', data)
                        if data is not None:
                            cur1.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                            data1 = cur1.fetchone()
                            print('удаление -', data1)
                            conn1.commit()
                            conn1.close()  # ВАЖНО: закрываем соединение
                            # 2. Добавляем в itprogMES.sql
                            conn2 = sqlite3.connect('itprogMES_free.sql')
                            cur2 = conn2.cursor()
                            # Создаём таблицу если нет
                            cur2.execute('''
                                CREATE TABLE IF NOT EXISTS users (
                                    user_id1 TEXT PRIMARY KEY,
                                    user_names1 TEXT
                                )
                            ''')
                            stats = "True"
                            cur2.execute("INSERT OR REPLACE INTO users (user_id1, user_names1) VALUES (?, ?)",
                                         (user_id, stats))
                            conn2.commit()
                            conn2.close()  # ВАЖНО: закрываем соединение
                            # 3. Отправляем уведомление
                            kek = types.InlineKeyboardMarkup()
                            kek.add(
                                types.InlineKeyboardButton(text="💎КУПИТЬ ПОДПИСКУ", callback_data="activate_premium_now"))
                            bot.send_message(
                                chat_id=user_id,
                                text="❗️ Ваша пробная подписка истекает через 48 часов.\n"
                                     "Приобретите премиум подписку по кнопке ниже 👇\n\n"
                                     "Поддержка - @MESA_VPN_support",
                                reply_markup=kek
                            )
                            bot.send_message(my_id, f"✅ Уведомление TRIAL 48 часов отправлено пользователю {user_id}")

                    except Exception as e:
                        bot.send_message(my_id, f"❌ Не удалось отправить уведомление TRIAL 48ч для {user_id}: {e}")

    def _check_all_sub_by_message24_free(self):
        """Триал: уведомление за 24 часа и удаление из БД"""

        new_time = datetime.now() + timedelta(hours=24)

        for user_id, sub_data in active_subscriptions.items():
            if sub_data['status'] == 'active' and sub_data['expires_at'] and sub_data['plan_id'] == "trial":
                if new_time >= datetime.fromisoformat(sub_data['expires_at']):
                    try:
                        # Подключаемся к itprogMES.sql и удаляем пользователя
                        conn = sqlite3.connect('itprogMES_free.sql')
                        cur = conn.cursor()
                        cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {user_id}")
                        data = cur.fetchone()

                        if data is not None:
                            cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                            conn.commit()

                            conn.close()  # ВАЖНО: закрываем соединение

                            # Отправляем уведомление
                            kek = types.InlineKeyboardMarkup()
                            kek.add(
                                types.InlineKeyboardButton(text="💎КУПИТЬ ПОДПИСКУ", callback_data="activate_premium_now"))
                            bot.send_message(
                                chat_id=user_id,
                                text="❗️ Ваша пробная подписка истекает через 24 часа.\n"
                                     "Не забудьте оплатить подписку, чтобы не потерять доступ.\n\n"
                                     "Поддержка - @MESA_VPN_support",
                                reply_markup=kek
                            )
                            bot.send_message(my_id, f"✅ Уведомление TRIAL 24 часа отправлено пользователю {user_id}")

                    except Exception as e:
                        bot.send_message(my_id, f"❌ Не удалось отправить уведомление TRIAL 24ч для {user_id}: {e}")

    def create_subscription(self, user_id: int, plan_id: str,
                            start_immediately: bool = None) -> Dict:
        """
        Создать подписку для пользователя

        Args:
            user_id: ID пользователя Telegram
            plan_id: ID тарифного плана
            start_immediately: Начать сразу или при первом использовании
                              (если None - используется настройка плана)

        Returns:
            Dict: Данные подписки
        """
        if plan_id not in self.plans:
            raise ValueError(f"План {plan_id} не найден")

        plan = self.plans[plan_id]

        # Определяем когда начинать подписку
        if start_immediately is None:
            start_immediately = plan.get('auto_start', True)

        if start_immediately:
            start_date = datetime.now()
            expires_at = start_date + timedelta(days=plan['duration_days'])
            status = 'active'
        else:
            start_date = None
            expires_at = None
            status = 'pending'  # Ожидает активации при первом использовании

        subscription = {
            'user_id': user_id,
            'plan_id': plan_id,
            'plan_name': plan['name'],
            'duration_days': plan['duration_days'],
            'limit_gb': 0,
            'start_date': start_date.isoformat() if start_date else None,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'auto_start': start_immediately,
            'used_traffic': 0  # В будущем можно добавить отслеживание трафика
        }

        active_subscriptions[user_id] = subscription

        # Сохраняем в файл (в реальном проекте - в БД)
        self._save_subscriptions()

        return subscription

    def activate_subscription(self, user_id: int) -> bool:
        """
        Активировать подписку (начать отсчет срока)

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность активации
        """
        if user_id not in active_subscriptions:
            return False

        sub = active_subscriptions[user_id]

        if sub['status'] == 'active':
            return True  # Уже активна

        if sub['status'] == 'pending':
            # Активируем подписку
            start_date = datetime.now()
            expires_at = start_date + timedelta(days=sub['duration_days'])

            sub['status'] = 'active'
            sub['start_date'] = start_date.isoformat()
            sub['expires_at'] = expires_at.isoformat()

            active_subscriptions[user_id] = sub
            self._save_subscriptions()

            # Уведомляем пользователя
            try:
                bot.send_message(
                    user_id,
                    f"✅ Ваша подписка '{sub['plan_name']}' активирована!\n"
                    f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}"
                )
            except:
                pass

            return True

        return False

    def deactivate_subscription(self, user_id: int) -> bool:
        """
        Деактивировать подписку

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность деактивации
        """
        if user_id not in active_subscriptions:
            return False

        sub = active_subscriptions[user_id]
        sub['status'] = 'expired'
        sub['duration_days'] = "30"
        active_subscriptions[user_id] = sub

        # Уведомляем пользователя
        try:
            kek = types.InlineKeyboardMarkup()
            kek.add(types.InlineKeyboardButton(text="💎ПРОДЛИТЬ ПОДПИСКУ", callback_data="continue_sub"))
            bot.send_message(
                user_id,
                "⚠️ Ваша подписка истекла!\n"
                "Для продолжения использования услуг VPN-сервиса оформите 💎 Премиум подписку по кнопке ниже.\n\nПоддержка - @MESA_VPN_support",
                reply_markup=kek
            )
        except:
            pass

        self._save_subscriptions()
        return True

    def deactivate_subscription_free(self, user_id: int) -> bool:
        """
        Деактивировать подписку

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность деактивации
        """
        if user_id not in active_subscriptions:
            return False

        sub = active_subscriptions[user_id]
        sub['status'] = 'expired'
        sub['duration_days'] = "3"
        active_subscriptions[user_id] = sub

        # Уведомляем пользователя
        try:
            kek = types.InlineKeyboardMarkup()
            kek.add(types.InlineKeyboardButton(text="💎КУПИТЬ ПОДПИСКУ", callback_data="activate_premium_now"))
            bot.send_message(
                user_id,
                "⚠️ Ваша подписка истекла!\n"
                "Для продолжения использования услуг VPN-сервиса оформите 💎 Премиум подписку по кнопке ниже.\n\nПоддержка - @MESA_VPN_support",
                reply_markup=kek
            )
        except:
            pass

        self._save_subscriptions()
        return True

    def continue_subscription(self, user_id: int) -> bool:
        sub = active_subscriptions[user_id]
        start_date = datetime.now()
        expires_at = start_date + timedelta(days=30)

        sub['plan_id'] = "premium"
        sub['status'] = 'active'
        sub['start_date'] = start_date.isoformat()
        sub['expires_at'] = expires_at.isoformat()
        sub['created_at'] = start_date.isoformat()
        sub['auto_start'] = True
        sub['duration_days'] = 30

        active_subscriptions[user_id] = sub

        self._save_subscriptions()

    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """
        Получить информацию о подписке пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Optional[Dict]: Данные подписки или None
        """
        return active_subscriptions.get(user_id)

    def check_access(self, user_id: int) -> bool:
        """
        Проверить доступ пользователя к VPN

        Args:
            user_id: ID пользователя

        Returns:
            bool: Есть ли доступ
        """
        if user_id not in active_subscriptions:
            return False

        sub = active_subscriptions[user_id]

        if sub['status'] != 'active':
            return False

        # Проверяем срок действия
        if sub['expires_at']:
            expires_date = datetime.fromisoformat(sub['expires_at'])
            if datetime.now() > expires_date:
                self.deactivate_subscription(user_id)
                return False

        return True

    def get_remaining_days(self, user_id: int) -> int:
        """
        Получить количество оставшихся дней подписки

        Args:
            user_id: ID пользователя

        Returns:
            int: Оставшиеся дни
        """
        sub = self.get_user_subscription(user_id)

        if not sub or sub['status'] != 'active' or not sub['expires_at']:
            return 0

        expires_date = datetime.fromisoformat(sub['expires_at'])
        remaining = (expires_date - datetime.now()).days

        return max(0, remaining)

    def _save_subscriptions(self):
        """Сохранить подписки в файл"""
        try:
            with open('subscriptions.json', 'w', encoding='utf-8') as f:
                # Преобразуем datetime в строки
                data_to_save = {}
                for user_id, sub in active_subscriptions.items():
                    data_to_save[user_id] = sub

                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения подписок: {e}")

    def _load_subscriptions(self):
        """Загрузить подписки из файла"""
        try:
            with open('subscriptions.json', 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Преобразуем строки обратно в нужный формат
                for user_id, sub in loaded.items():
                    active_subscriptions[int(user_id)] = sub
        except FileNotFoundError:
            print("Файл подписок не найден, создаем новый")
        except Exception as e:
            print(f"Ошибка загрузки подписок: {e}")

    def create_user_3x_ui(self, user_id: int, limit_gb: int, user_uuid: int) -> int:
        session = requests.Session()
        login_data = {
            "username": USERNAME1,
            "password": PASSWORD1
        }
        session.post(f"{PANEL_URL}/login", data=login_data)

        # ID вашего инбаунда на порту 443 (узнать в панели)
        INBOUND_ID = 2  # Замените на ваш ID

        # Генерация нового UUID
        new_uuid = user_uuid

        # Данные нового пользователя
        client_data = {
            "id": new_uuid,
            "flow": "xtls-rprx-vision",
            "email": f"user_{new_uuid[:8]}",
            "limitIp": 0,
            "totalGB": 0,  # 0 = безлимит
            "expiryTime": limit_gb,  # 0 = вечный
            "enable": True,
            "tgId": user_id,
            "subId": ""
        }

        # Добавление пользователя в инбаунд
        response = session.post(
            f"{PANEL_URL}/panel/api/inbounds/addClient",
            json={
                "id": INBOUND_ID,
                "settings": json.dumps({"clients": [client_data]})
            }
        )

        if response.status_code == 200:
            print(f"✅ Пользователь добавлен. UUID: {new_uuid}")
            print(f"Ссылка: vless://{new_uuid}@ваш-сервер:443?flow=xtls-rprx-vision&...")
        else:
            print(f"❌ Ошибка: {response.text}")

# ========== НАСТРОЙКИ ВПН и 3X-UI ПАНЕЛИ ==========
class VPNManager:
    """Расширенный менеджер VPN с поддержкой подписок"""

    def __init__(self, subscription_manager: SubscriptionManager):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.sub_manager = subscription_manager
        self._squads_cache = None
        self._cache_time = 0
        self._cache_ttl = 300

    def get_token(self):
        """Получение токена доступа"""
        url = f"{MARZBAN_URL}/api/admin/token"
        try:
            resp = requests.post(url, data={"username": USERNAME, "password": PASSWORD}, verify=False, timeout=10)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if not token:
                raise Exception("Token not in response")
            return token
        except Exception as e:
            print(f"❌ Ошибка получения токена: {e}")
            raise

    def get_hosts(self, token):
        """Получение списка хостов и их ID"""
        url = f"{MARZBAN_URL}/api/hosts"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Marzban возвращает словарь, где ключ - имя хоста, значение - список хостов
            hosts = []
            if isinstance(data, dict):
                for host_name, host_list in data.items():
                    if isinstance(host_list, list):
                        for host in host_list:
                            host['name'] = host_name
                            hosts.append(host)
            elif isinstance(data, list):
                hosts = data

            return hosts
        except Exception as e:
            print(f"❌ Ошибка получения хостов: {e}")
            return []

    def create_user_vless_small(self, token, user_uuid, username, expire_days=3, data_limit_gb=0):
        """Создание пользователя VLESS и VMess с одинаковым UUID"""
        url = f"{MARZBAN_URL}/api/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Получаем ID хоста VLESS REALITY
        hosts = self.get_hosts(token)
        host_id = None
        for host in hosts:
            if host.get('name') == 'VLESS REALITY' or host.get('remark') == 'VLESS REALITY':
                host_id = host.get('id')
                break

        if not host_id and hosts:
            # Если не нашли VLESS REALITY, берём первый попавшийся хост
            host_id = hosts[0].get('id')
            print(f"⚠️ VLESS REALITY не найден, используем хост: {hosts[0].get('name', 'unknown')}")

        expire = int(time.time() + expire_days * 86400) if expire_days > 0 else 0
        data_limit = data_limit_gb * 1073741824 if data_limit_gb > 0 else 0

        payload = {
            "username": username,
            "status": "active",
            "proxies": {
                "vless": {
                    "id": user_uuid,
                    "flow": "xtls-rprx-vision",
                    "encryption": "none"
                },
                "vmess": {
                    "id": user_uuid,
                    "alterId": 0,
                    "security": "auto"
                }
            },
            "inbounds": {
                "vless": ["VLESS REALITY"],
                "vmess": ["VMess"]
            },
            "expire": expire,
            "data_limit": data_limit
        }

        # Добавляем host_id если нашли
        if host_id:
            payload["hosts_ids"] = [host_id]

        print(f"📤 Отправка запроса на создание пользователя {username}...")
        print(f"🔑 UUID: {user_uuid} (общий для VLESS и VMess)")

        try:
            resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
            print(f"📊 Статус: {resp.status_code}")

            if resp.status_code == 401:
                print("❌ Ошибка авторизации. Проверьте логин и пароль")
                return None

            if resp.status_code == 409:
                print(f"❌ Пользователь {username} уже существует")
                return None

            if resp.status_code == 422:
                print(f"❌ Ошибка валидации: {resp.text}")
                return None

            response_data = resp.json() if resp.text else {}
            print(f"📝 Ответ: {json.dumps(response_data, indent=2, ensure_ascii=False) if response_data else 'empty'}")

            if resp.status_code == 200 or resp.status_code == 201:
                return response_data
            else:
                print(f"❌ Ошибка: HTTP {resp.status_code}")
                return None

        except requests.exceptions.Timeout:
            print("❌ Таймаут при создании пользователя")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def create_user_vless(self, token, user_uuid, username, expire_days=3, data_limit_gb=0):
        """Создание пользователя VLESS и VMess с одинаковым UUID"""
        url = f"{MARZBAN_URL}/api/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Получаем ID хоста VLESS REALITY
        hosts = self.get_hosts(token)
        host_id = None
        for host in hosts:
            if host.get('name') == 'VLESS REALITY' or host.get('remark') == 'VLESS REALITY':
                host_id = host.get('id')
                break

        if not host_id and hosts:
            # Если не нашли VLESS REALITY, берём первый попавшийся хост
            host_id = hosts[0].get('id')
            print(f"⚠️ VLESS REALITY не найден, используем хост: {hosts[0].get('name', 'unknown')}")

        expire = int(time.time() + expire_days * 86400) if expire_days > 0 else 0
        data_limit = data_limit_gb * 1073741824 if data_limit_gb > 0 else 0

        payload = {
            "username": username,
            "status": "active",
            "proxies": {
                "vless": {
                    "id": user_uuid,
                    "flow": "xtls-rprx-vision",
                    "encryption": "none"
                },
                "vmess": {
                    "id": user_uuid,
                    "alterId": 0,
                    "security": "auto"
                }
            },
            "inbounds": {
                "vless": ["VLESS REALITY", "VLESS FINLAND XHTTP", "VLESS SplitHTTP", "VLESS GERMANY", "VMESS WS TLS", "VLESS UNIVERSAL"],
                "vmess": ["VMess"]
            },
            "expire": expire,
            "data_limit": data_limit
        }

        # Добавляем host_id если нашли
        if host_id:
            payload["hosts_ids"] = [host_id]

        print(f"📤 Отправка запроса на создание пользователя {username}...")
        print(f"🔑 UUID: {user_uuid} (общий для VLESS и VMess)")

        try:
            resp = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
            print(f"📊 Статус: {resp.status_code}")

            if resp.status_code == 401:
                print("❌ Ошибка авторизации. Проверьте логин и пароль")
                return None

            if resp.status_code == 409:
                print(f"❌ Пользователь {username} уже существует")
                return None

            if resp.status_code == 422:
                print(f"❌ Ошибка валидации: {resp.text}")
                return None

            response_data = resp.json() if resp.text else {}
            print(f"📝 Ответ: {json.dumps(response_data, indent=2, ensure_ascii=False) if response_data else 'empty'}")

            if resp.status_code == 200 or resp.status_code == 201:
                return response_data
            else:
                print(f"❌ Ошибка: HTTP {resp.status_code}")
                return None

        except requests.exceptions.Timeout:
            print("❌ Таймаут при создании пользователя")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def add_user(self, user_id: int, email: str) -> Dict:
        """
        Добавить пользователя с учетом его подписки

        Args:
            user_id: ID пользователя Telegram
            email: Email пользователя

        Returns:
            Dict: Результат операции
        """
        # Проверяем подписку
        if not self.sub_manager.check_access(user_id):
            return {
                "success": False,
                "error": "Нет активной подписки"
            }

        sub = self.sub_manager.get_user_subscription(user_id)

        # Если подписка в статусе pending, активируем ее
        if sub and sub['status'] == 'pending':
            self.sub_manager.activate_subscription(user_id)
            sub = self.sub_manager.get_user_subscription(user_id)

        # Генерируем UUID
        user_uuid = str(uuid.uuid4())

        # Добавляем в X-UI
        limit_gb = 0
        token = self.get_token()

        # Показываем список хостов
        hosts = self.get_hosts(token)

        # Создаём пользователя
        user = self.create_user_vless(
            token=token,
            user_uuid=user_uuid,
            username=email.replace("🇳🇱", ""),
            expire_days=3,
            data_limit_gb=15
        )

        if user:
            username = user.get('username')

            # Берём подписку прямо из ответа
            subscription_url = user.get('subscription_url')
            if subscription_url:
                full_sub_link = f"{MARZBAN_DOMEN}{subscription_url}"
        else:
            print("\n❌ Ошибка создания пользователя")

        # Генерируем ссылку
        # vless_link = self.generate_vless_link(user_uuid, email, limit_gb)

        # Сохраняем пользователя
        users_db[user_id] = {
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 10,
            "vless_link": full_sub_link,
            "created_at": datetime.now().isoformat(),
            "subscription_id": sub['plan_id'] if sub else None
        }
        conn = sqlite3.connect('itproger5.sql')
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50), user_sub1 varchar(50), user_stats varchar(50))')
        conn.commit()
        user_stats = 0
        cur.execute("INSERT INTO users (user_id1, user_names1, user_sub1, user_stats) VALUES (?, ?, ?, ?)",
                    (user_id, user_uuid, full_sub_link, user_stats))
        conn.commit()

        return {
            "success": True,
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 10,
            "vless_link": full_sub_link,
            "subscription": sub
        }

    # def add_user(self, user_id: int, email: str) -> Dict:
    #     """
    #     Добавить пользователя с учетом его подписки
    #
    #     Args:
    #         user_id: ID пользователя Telegram
    #         email: Email пользователя
    #
    #     Returns:
    #         Dict: Результат операции
    #     """
    #     # Проверяем подписку
    #     if not self.sub_manager.check_access(user_id):
    #         return {
    #             "success": False,
    #             "error": "Нет активной подписки"
    #         }
    #
    #     sub = self.sub_manager.get_user_subscription(user_id)
    #
    #     # Если подписка в статусе pending, активируем ее
    #     if sub and sub['status'] == 'pending':
    #         self.sub_manager.activate_subscription(user_id)
    #         sub = self.sub_manager.get_user_subscription(user_id)
    #
    #     # Генерируем UUID
    #     user_uuid = str(uuid.uuid4())
    #
    #     # Добавляем в X-UI
    #     limit_gb = 0
    #     success = self._add_to_xui(email, user_uuid, limit_gb, expiry_days=3)
    #
    #     if not success:
    #         return {
    #             "success": False,
    #             "error": "Ошибка добавления в X-UI"
    #         }
    #
    #     # Генерируем ссылку
    #     vless_link = self.generate_vless_link(user_uuid, email, limit_gb)
    #
    #     # Сохраняем пользователя
    #     users_db[user_id] = {
    #         "email": email,
    #         "uuid": user_uuid,
    #         "limit_gb": 0,
    #         "vless_link": vless_link,
    #         "created_at": datetime.now().isoformat(),
    #         "subscription_id": sub['plan_id'] if sub else None
    #     }
    #
    #     return {
    #         "success": True,
    #         "email": email,
    #         "uuid": user_uuid,
    #         "limit_gb": 0,
    #         "vless_link": vless_link,
    #         "subscription": sub
    #     }

    def add_userPRO(self, user_id: int, email: str) -> Dict:
        """
        Добавить пользователя с учетом его подписки

        Args:
            user_id: ID пользователя Telegram
            email: Email пользователя

        Returns:
            Dict: Результат операции
        """
        # Проверяем подписку
        if not self.sub_manager.check_access(user_id):
            return {
                "success": False,
                "error": "Нет активной подписки"
            }

        sub = self.sub_manager.get_user_subscription(user_id)

        # Если подписка в статусе pending, активируем ее
        if sub and sub['status'] == 'pending':
            self.sub_manager.activate_subscription(user_id)
            sub = self.sub_manager.get_user_subscription(user_id)

        # Генерируем UUID
        user_uuid = str(uuid.uuid4())

        token = self.get_token()

        # Создаём пользователя
        user = self.create_user_vless(
            token=token,
            user_uuid=user_uuid,
            username=email.replace("🇳🇱", ""),
            expire_days=30,
            data_limit_gb=0
        )

        if user:
            username = user.get('username')

            # Берём подписку прямо из ответа
            subscription_url = user.get('subscription_url')
            if subscription_url:
                full_sub_link = f"{MARZBAN_DOMEN}{subscription_url}"
        else:
            print("\n❌ Ошибка создания пользователя")

        # Генерируем ссылку
        # vless_link = self.generate_vless_link(user_uuid, email, limit_gb)

        # Сохраняем пользователя
        users_db[user_id] = {
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 0,
            "vless_link": full_sub_link,
            "created_at": datetime.now().isoformat(),
            "subscription_id": sub['plan_id'] if sub else None
        }
        conn = sqlite3.connect('itproger5.sql')
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50), user_sub1 varchar(50), user_stats varchar(50))')
        conn.commit()
        user_stats = 1
        cur.execute("INSERT INTO users (user_id1, user_names1, user_sub1, user_stats) VALUES (?, ?, ?, ?)",
                    (user_id, user_uuid, full_sub_link, user_stats))
        conn.commit()
        conn = sqlite3.connect('itproger4.sql')
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users(
                                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                    user_id1 VARCHAR(50) UNIQUE NOT NULL,
                                                    user_names1 VARCHAR(50) NOT NULL,
                                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                                )''')
        conn.commit()
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id, user_uuid))
        conn.commit()

        return {
            "success": True,
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 0,
            "vless_link": full_sub_link,
            "subscription": sub
        }

    def add_userTEST(self, user_id: int, email: str) -> Dict:
        """
                Добавить пользователя с учетом его подписки

                Args:
                    user_id: ID пользователя Telegram
                    email: Email пользователя

                Returns:
                    Dict: Результат операции
                """

        # Генерируем UUID
        user_uuid = str(uuid.uuid4())

        token = self.get_token()

        # Создаём пользователя
        user = self.create_user_vless(
            token=token,
            user_uuid=user_uuid,
            username=email.replace("🇳🇱", ""),
            expire_days=30,
            data_limit_gb=0
        )

        if user:
            username = user.get('username')

            # Берём подписку прямо из ответа
            subscription_url = user.get('subscription_url')
            if subscription_url:
                full_sub_link = f"{MARZBAN_DOMEN}{subscription_url}"
        else:
            print("\n❌ Ошибка создания пользователя")

        # Генерируем ссылку
        # vless_link = self.generate_vless_link(user_uuid, email, limit_gb)

        # Сохраняем пользователя
        users_db[user_id] = {
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 0,
            "vless_link": full_sub_link,
            "created_at": datetime.now().isoformat()
        }
        conn = sqlite3.connect('itproger5.sql')
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50), user_sub1 varchar(50), user_stats varchar(50))')
        conn.commit()
        user_stats = 1
        cur.execute("INSERT INTO users (user_id1, user_names1, user_sub1, user_stats) VALUES (?, ?, ?, ?)",
                    (user_id, user_uuid, full_sub_link, user_stats))
        conn.commit()
        conn = sqlite3.connect('itproger4.sql')
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users(
                                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                            user_id1 VARCHAR(50) UNIQUE NOT NULL,
                                                            user_names1 VARCHAR(50) NOT NULL,
                                                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                                        )''')
        conn.commit()
        cur.execute(
            "INSERT OR IGNORE INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id, user_uuid))
        conn.commit()

        return {
            "success": True,
            "email": email,
            "uuid": user_uuid,
            "limit_gb": 0,
            "vless_link": full_sub_link
        }

    # def _add_to_xui(self, email: str, user_uuid: str, limit_gb: int, expiry_days: int = 0) -> bool:
    #     """Добавить пользователя в X-UI
    #     Args:
    #         email: Email пользователя
    #         user_uuid: UUID пользователя
    #         limit_gb: Лимит трафика в ГБ
    #         expiry_days: Время жизни ссылки в днях (0 = никогда не истекает)
    #     """
    #     try:
    #         # Авторизация
    #         auth_response = self.session.post(
    #             f"{XUI_HOST}/login",
    #             json={"username": XUI_USERNAME, "password": XUI_PASSWORD},
    #             timeout=10
    #         )
    #         if auth_response.status_code != 200:
    #             return False
    #         # Получаем инбаунды
    #         inbounds_response = self.session.get(f"{XUI_HOST}/panel/api/inbounds/list")
    #         if inbounds_response.status_code != 200:
    #             return False
    #         inbounds = inbounds_response.json()
    #         if not inbounds.get('obj'):
    #             return False
    #         inbound_id = 2
    #         # vless://bd0424fe-ebca-45b6-8ade-a0a5ceaf2ff2@144.31.247.61:443?type=tcp&encryption=none&security=reality&pbk=PIvLjG-jBC1C1WNU-qSpCgZwDuNqrN8_9xU7nhotaS0&fp=chrome&sni=www.nvidia.com&sid=f64fd5fb036fed&spx=%2F&flow=xtls-rprx-vision#PRO-7351725
    #         # vless://9d6da848-561f-4867-9d98-4c8467c0cf10@144.31.247.61:433?type=tcp&encryption=none&security=reality&pbk=PIvLjG-jBC1C1WNU-qSpCgZwDuNqrN8_9xU7nhotaS0&fp=chrome&sni=www.nvidia.com&sid=f64fd5fb036fed&spx=%2F&flow=xtls-rprx-vision#PRO-8384977
    #         # Рассчитываем время окончания
    #         current_time = int(time.time())
    #         if expiry_days > 0:
    #             expiry_time = (current_time + expiry_days * 86400) * 1000  # в миллисекундах
    #         else:
    #             expiry_time = 0  # 0 = никогда не истекает
    #         client_settings = {
    #             "clients": [{
    #                 "id": user_uuid,
    #                 "email": email,
    #                 "flow": "xtls-rprx-vision",
    #                 "limitIp": 1,
    #                 "totalGB": limit_gb,
    #                 "expiryTime": expiry_time,
    #                 "total_connection": 1,  # Время истечения в миллисекундах
    #                 "enable": True,
    #                 "tgId": "",
    #                 "subId": "",
    #                 # НОВЫЕ ПОЛЯ ДЛЯ ОТСЛЕЖИВАНИЯ С НАЧАЛА ИСПОЛЬЗОВАНИЯ
    #                 "startTime": current_time * 1000,  # Текущее время в миллисекундах
    #                 "createdAt": datetime.now().isoformat(),  # Дата создания в ISO формате
    #                 "expiryDate": (datetime.now() + timedelta(
    #                     days=expiry_days)).isoformat() if expiry_days > 0 else "never",
    #                 "daysFromStart": 0,  # Дней с начала использования
    #                 "lastResetTime": 0,  # Время последнего сброса
    #                 "usageFromStart": {  # Детальная статистика с начала
    #                     "totalUpload": 0,
    #                     "totalDownload": 0,
    #                     "peakUsageDay": 0,
    #                     "averageDailyUsage": 0
    #                 },
    #                 "settings": {
    #                     "trackFromStart": True,  # Включить отслеживание с начала
    #                     "autoResetDays": 3,  # Автосброс через N дней (0 = отключено)
    #                     "notifyOnMilestone": True,  # Уведомлять о вехах (7, 30, 90 дней)
    #                     "notifyOnExpiry": True,  # Уведомлять об истечении срока
    #                     "expiryWarningDays": [3, 1, 0],  # Дни до истечения для предупреждений
    #                     "usageHistory": []  # История использования по дням
    #                 }
    #             }],
    #             "decryption": "none",
    #             "fallbacks": []
    #         }
    #         # Добавляем клиента
    #         add_response = self.session.post(
    #             f"{XUI_HOST}/panel/api/inbounds/addClient",
    #             json={
    #                 "id": inbound_id,
    #                 "settings": json.dumps(client_settings, ensure_ascii=False)
    #             }
    #         )
    #         return add_response.status_code == 200
    #     except Exception as e:
    #         print(f"X-UI error: {e}")
    #         return False
    #
    # def _add_to_xui2(self, email: str, user_uuid: str, limit_gb: int, expiry_days: int = 0) -> bool:
    #     """Добавить пользователя в X-UI
    #     Args:
    #         email: Email пользователя
    #         user_uuid: UUID пользователя
    #         limit_gb: Лимит трафика в ГБ
    #         expiry_days: Время жизни ссылки в днях (0 = никогда не истекает)
    #     """
    #     try:
    #         # Авторизация
    #         auth_response = self.session.post(
    #             f"{XUI_HOST2}/login",
    #             json={"username": XUI_USERNAME2, "password": XUI_PASSWORD2},
    #             timeout=10
    #         )
    #         if auth_response.status_code != 200:
    #             return False
    #         # Получаем инбаунды
    #         inbounds_response = self.session.get(f"{XUI_HOST2}/panel/api/inbounds/list")
    #         if inbounds_response.status_code != 200:
    #             return False
    #         inbounds = inbounds_response.json()
    #         if not inbounds.get('obj'):
    #             return False
    #         inbound_id = 2
    #         # Рассчитываем время окончания
    #         current_time = int(time.time())
    #         if expiry_days > 0:
    #             expiry_time = (current_time + expiry_days * 86400) * 1000  # в миллисекундах
    #         else:
    #             expiry_time = 0  # 0 = никогда не истекает
    #         client_settings = {
    #             "clients": [{
    #                 "id": user_uuid,
    #                 "email": email,
    #                 "flow": "xtls-rprx-vision",
    #                 "limitIp": 1,
    #                 "totalGB": limit_gb,
    #                 "expiryTime": expiry_time,
    #                 "total_connection": 1,  # Время истечения в миллисекундах
    #                 "enable": True,
    #                 "tgId": "",
    #                 "subId": "",
    #                 # НОВЫЕ ПОЛЯ ДЛЯ ОТСЛЕЖИВАНИЯ С НАЧАЛА ИСПОЛЬЗОВАНИЯ
    #                 "startTime": current_time * 1000,  # Текущее время в миллисекундах
    #                 "createdAt": datetime.now().isoformat(),  # Дата создания в ISO формате
    #                 "expiryDate": (datetime.now() + timedelta(
    #                     days=expiry_days)).isoformat() if expiry_days > 0 else "never",
    #                 "daysFromStart": 0,  # Дней с начала использования
    #                 "lastResetTime": 0,  # Время последнего сброса
    #                 "usageFromStart": {  # Детальная статистика с начала
    #                     "totalUpload": 0,
    #                     "totalDownload": 0,
    #                     "peakUsageDay": 0,
    #                     "averageDailyUsage": 0
    #                 },
    #                 "settings": {
    #                     "trackFromStart": True,  # Включить отслеживание с начала
    #                     "autoResetDays": 3,  # Автосброс через N дней (0 = отключено)
    #                     "notifyOnMilestone": True,  # Уведомлять о вехах (7, 30, 90 дней)
    #                     "notifyOnExpiry": True,  # Уведомлять об истечении срока
    #                     "expiryWarningDays": [3, 1, 0],  # Дни до истечения для предупреждений
    #                     "usageHistory": []  # История использования по дням
    #                 }
    #             }],
    #             "decryption": "none",
    #             "fallbacks": []
    #         }
    #         # Добавляем клиента
    #         add_response = self.session.post(
    #             f"{XUI_HOST2}/panel/api/inbounds/addClient",
    #             json={
    #                 "id": inbound_id,
    #                 "settings": json.dumps(client_settings, ensure_ascii=False)
    #             }
    #         )
    #         return add_response.status_code == 200
    #     except Exception as e:
    #         print(f"X-UI error: {e}")
    #         return False

    def renew_expired_subscription_marzban(self, user_uuid, user_id, email):
        """
        Добавить пользователя с учетом его подписки
        Args:
            user_id: ID пользователя Telegram
            email: Email пользователя

        Returns:
            Dict: Результат операции
        """
        try:
            res1 = testt.delete_user_by_uuid_from_marzban(user_uuid)
            if res1:
                token = self.get_token()

                # Создаём пользователя
                user = self.create_user_vless(
                    token=token,
                    user_uuid=user_uuid,
                    username=email.replace("🇳🇱", ""),
                    expire_days=30,
                    data_limit_gb=0
                )

                if user:
                    username = user.get('username')

                    # Берём подписку прямо из ответа
                    subscription_url = user.get('subscription_url')
                    if subscription_url:
                        full_sub_link = f"{MARZBAN_DOMEN}{subscription_url}"
                else:
                    print("\n❌ Ошибка создания пользователя")

                # Генерируем ссылку
                # vless_link = self.generate_vless_link(user_uuid, email, limit_gb)

                # Сохраняем пользователя
                users_db[user_id] = {
                    "email": email,
                    "uuid": user_uuid,
                    "limit_gb": 0,
                    "vless_link": full_sub_link,
                    "created_at": datetime.now().isoformat()
                }

                return {
                    "success": True,
                    "email": email,
                    "uuid": user_uuid,
                    "limit_gb": 0,
                    "vless_link": full_sub_link
                }
            else:
                bot.send_message(my_id, "Не удалось удалить пользователя из Marzban")
        except:
            bot.send_message(my_id, "Произошла ошибка при обновлении подписки для пользователя")

    def generate_vless_link(self, user_uuid: str, email: str, limit_gb: int) -> str:
        """Генерация vless ссылки"""
        #short_id = hashlib.md5(f"{email}_{time.time()}".encode()).hexdigest()[:13]

        params = {
            "type": "tcp",
            "encryption": "none",
            "security": "reality",
            "pbk": REALITY_PUBLIC_KEY,
            "fp": "chrome",
            "sni": DEFAULT_SNI,
            "sid": "8f9a32a6a0",
            "spx": "%2F".replace("%252F", "%2F"),
            "flow": "xtls-rprx-vision"
        }

        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={quote(str(value))}")
        query_string = "&".join(query_parts)

        vless_link = f"vless://{user_uuid}@{SERVER_DOMEN2}:{DEFAULT_PORT2}?{query_string.replace('%252F', '%2F')}#{email.replace('@', '%40')}"

        return vless_link

    def generate_qr_code_url(self, vless_link: str) -> str:
        """Генерация URL QR-кода"""
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={quote(vless_link)}"

    def get_all_internal_squads(self):
        """Получает список всех внутренних сквадов"""
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Accept": "application/json"
        }

        try:
            response = requests.get(
                f"{REMNAWAVE_URL}/api/internal-squads",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Если ответ вложен в "response"
                if "response" in data:
                    data = data["response"]

                # Если есть поле "internalSquads" — берём его
                if "internalSquads" in data:
                    squads = data["internalSquads"]
                else:
                    squads = data

                print(f"✅ Найдено {len(squads)} внутренних сквадов")
                return squads
            else:
                print(f"⚠️ Не удалось получить сквады: {response.text}")
                return []

        except Exception as e:
            print(f"❌ Ошибка получения сквадов: {e}")
            return []

    def create_user_and_get_link(
            self,
            username: str,
            expire_days: int = 30,
            data_limit_gb: int = 0,
            plan_type: str = "standart",  # 👈 НОВЫЙ ПАРАМЕТР
            verbose: bool = True,
            hwid_limit: int = 1,
            tg_id: int = 0
    ) -> Optional[Dict]:
        """
        Создаёт пользователя, добавляет в нужные сквады и возвращает ссылку
        """

        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # ===== 1. СОЗДАЁМ ПОЛЬЗОВАТЕЛЯ =====
        user_uuid = str(uuid.uuid4())
        expire_at = (datetime.now() + timedelta(days=expire_days)).isoformat() + "Z"

        payload = {
            "username": username,
            "uuid": user_uuid,
            "telegramId": tg_id,
            "status": "ACTIVE",
            "expireAt": expire_at,
            "dataLimit": data_limit_gb * 1073741824 if data_limit_gb > 0 else 0,
            "hwidDeviceLimit": hwid_limit,
            "proxies": {
                "vless": {
                    "id": user_uuid,
                    "flow": "xtls-rprx-vision",
                    "encryption": "none"
                }
            },
            "inbounds": {
                "vless": ["VLESS REALITY"]
            }
        }

        try:
            create_response = requests.post(
                f"{REMNAWAVE_URL}/api/users",
                headers=headers,
                json=payload,
                timeout=30
            )

            if create_response.status_code not in [200, 201, 202]:
                print(f"❌ Ошибка создания: {create_response.text}")
                return None

            data = create_response.json()
            if "response" in data:
                data = data["response"]

            short_uuid = data.get("shortUuid")
            subscription_url = data.get("subscriptionUrl")

            if verbose:
                print("=" * 60)
                print("✅ Пользователь создан!")
                print("=" * 60)
                print(f"  👤 Имя: {username}")
                print(f"  🔑 UUID: {user_uuid}")
                print(f"  📌 shortUuid: {short_uuid}")
                print(f"  🔗 Ссылка: {subscription_url}")
                print(f"  📂 План: {plan_type}")

            # ===== 2. ДОБАВЛЯЕМ В НУЖНЫЕ СКВАДЫ =====
            squads_to_add = self.get_squads_by_plan(plan_type)
            added_count = 0

            if squads_to_add:
                print(f"\n📂 Добавление в сквады для плана '{plan_type}'...")
                for squad_uuid in squads_to_add:
                    if self.add_user_to_squad(user_uuid, squad_uuid):
                        added_count += 1
                        print(f"  ✅ Добавлен в сквад")
                    else:
                        print(f"  ⚠️ Ошибка добавления в сквад")
            else:
                print(f"⚠️ Нет сквадов для плана '{plan_type}'")

            print(f"\n✅ Добавлен в {added_count} сквадов")

            # ===== 3. ПОЛУЧАЕМ ЗАШИФРОВАННУЮ ССЫЛКУ =====
            crypt4_link = None
            if short_uuid:
                raw_response = requests.get(
                    f"{REMNAWAVE_URL}/api/subscriptions/by-short-uuid/{short_uuid}/raw",
                    headers=headers,
                    timeout=30
                )

                if raw_response.status_code == 200:
                    raw_data = raw_response.text.strip()
                    if raw_data.startswith(("happ://crypt4/", "happ://routing/add/")):
                        crypt4_link = raw_data

            if verbose:
                print("=" * 60)

            return {
                "uuid": user_uuid,
                "short_uuid": short_uuid,
                "subscription_url": subscription_url,
                "crypt4_link": crypt4_link,
                "username": username,
                "expire_at": expire_at,
                "plan_type": plan_type,
                "squads_added": added_count
            }

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    def add_user_to_squad(self, user_uuid: str, squad_uuid: str) -> bool:
        """Добавляет пользователя во внутренний сквад"""
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "userUuids": [user_uuid]
        }

        try:
            response = requests.post(
                f"{REMNAWAVE_URL}/api/internal-squads/{squad_uuid}/bulk-actions/add-users",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201, 204]:
                return True
            else:
                print(f"  ⚠️ Ошибка добавления в сквад {squad_uuid[:8]}: {response.text}")
                return False

        except Exception as e:
            print(f"  ❌ Ошибка добавления в сквад: {e}")
            return False
    # ========== ПОЛУЧЕНИЕ СКВАДОВ ПО ПЛАНУ ==========
    def get_squads_by_plan(self, plan_type: str) -> list:
        """Возвращает список UUID сквадов в зависимости от типа подписки"""
        plan_squads = {
            "standart": ["Norm", "Standart"],
            "premium": ["Standart", "Norm", "Auto"],
            "maximum": ["Standart", "Norm", "Auto"],
            "fast_start": ["Norm"]
        }

        squad_names = plan_squads.get(plan_type, [])
        if not squad_names:
            print(f"⚠️ Неизвестный тип подписки: {plan_type}")
            return []

        all_squads = self.get_all_internal_squads()
        target_squads = []

        for squad in all_squads:
            squad_name = squad.get("name", "")
            if squad_name in squad_names:
                squad_uuid = squad.get("uuid")
                if squad_uuid:
                    target_squads.append(squad_uuid)

        print(f"📂 Для плана '{plan_type}' найдено {len(target_squads)} сквадов: {squad_names}")
        return target_squads

    def extend_user_subscription(
            self,
            user_uuid: str,
            extra_days: int = 30,
            hwid_limit: int = None,
            verbose: bool = True
    ) -> Optional[Dict]:
        """
        Продлевает подписку пользователя и изменяет лимит устройств

        Args:
            user_uuid: UUID пользователя в Remnawave
            extra_days: Количество дней для продления (по умолчанию 30)
            hwid_limit: Новый лимит устройств (если None — не меняется)
            verbose: Выводить ли логи

        Returns:
            Dict: Обновлённые данные пользователя или None при ошибке
        """
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # 1. Получаем текущие данные пользователя
            get_response = requests.get(
                f"{REMNAWAVE_URL}/api/users/{user_uuid}",
                headers=headers,
                timeout=30
            )

            if get_response.status_code != 200:
                print(f"❌ Пользователь с UUID {user_uuid} не найден")
                return None

            data = get_response.json()
            if "response" in data:
                data = data["response"]

            # 2. Извлекаем текущую дату истечения
            current_expire = data.get("expireAt")
            current_hwid_limit = data.get("hwidDeviceLimit")

            # 3. Рассчитываем новую дату
            if current_expire:
                try:
                    current_date = datetime.fromisoformat(current_expire.replace('Z', '+00:00'))
                    new_expire = current_date + timedelta(days=extra_days)
                except Exception as e:
                    print(f"⚠️ Ошибка парсинга даты: {e}")
                    new_expire = datetime.now() + timedelta(days=extra_days)
            else:
                new_expire = datetime.now() + timedelta(days=extra_days)

            new_expire_str = new_expire.isoformat().replace('+00:00', 'Z')

            # 4. Формируем payload для обновления
            payload = {
                "uuid": user_uuid,
                "expireAt": new_expire_str
            }

            # Если указан новый лимит устройств — добавляем
            if hwid_limit is not None:
                payload["hwidDeviceLimit"] = hwid_limit

            # 5. Отправляем запрос на обновление
            patch_response = requests.patch(
                f"{REMNAWAVE_URL}/api/users",
                headers=headers,
                json=payload,
                timeout=30
            )

            if patch_response.status_code not in [200, 201, 202]:
                print(f"❌ Ошибка обновления: {patch_response.text}")
                return None

            result = patch_response.json()
            if "response" in result:
                result = result["response"]

            # 6. Выводим результат
            if verbose:
                print("=" * 60)
                print("✅ Подписка обновлена!")
                print("=" * 60)
                print(f"  👤 UUID: {user_uuid}")
                print(f"  📅 Было: {current_expire}")
                print(f"  📅 Стало: {new_expire_str}")
                print(f"  📆 Добавлено дней: {extra_days}")
                if hwid_limit is not None:
                    print(f"  📱 Лимит устройств: {hwid_limit} (было: {current_hwid_limit})")
                print("=" * 60)

            return {
                "uuid": user_uuid,
                "old_expire": current_expire,
                "new_expire": new_expire_str,
                "extra_days": extra_days,
                "old_hwid_limit": current_hwid_limit,
                "new_hwid_limit": hwid_limit if hwid_limit is not None else current_hwid_limit
            }

        except Exception as e:
            print(f"❌ Ошибка обновления подписки: {e}")
            return None

    def delete_user_by_uuid(self, user_uuid: str, verbose: bool = True) -> bool:
        """
        Удаляет пользователя из Remnawave по UUID
        """
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Accept": "application/json"
        }

        try:
            # 1. Проверяем, существует ли пользователь
            get_response = requests.get(
                f"{REMNAWAVE_URL}/api/users/{user_uuid}",
                headers=headers,
                timeout=30
            )

            if get_response.status_code != 200:
                print(f"❌ Пользователь с UUID {user_uuid} не найден")
                return False

            # 2. Удаляем пользователя
            delete_response = requests.delete(
                f"{REMNAWAVE_URL}/api/users/{user_uuid}",
                headers=headers,
                timeout=30
            )

            if delete_response.status_code in [200, 201, 202, 204]:
                if verbose:
                    print("=" * 60)
                    print("✅ Пользователь удалён!")
                    print("=" * 60)
                    print(f"  🔑 UUID: {user_uuid}")
                    print("=" * 60)
                return True
            else:
                print(f"❌ Ошибка удаления: {delete_response.text}")
                return False

        except Exception as e:
            print(f"❌ Ошибка удаления пользователя: {e}")
            return False

    def delete_user_by_telegram_id(
            self,
            telegram_id: int,
            verbose: bool = True
    ) -> bool:
        """
        Удаляет пользователя из Remnawave по Telegram ID

        Args:
            telegram_id: Telegram ID пользователя
            verbose: Выводить ли логи

        Returns:
            bool: True если удалено успешно
        """
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Accept": "application/json"
        }

        try:
            # 1. Получаем пользователя по Telegram ID
            response = requests.get(
                f"{REMNAWAVE_URL}/api/users/by-telegram-id/{telegram_id}",
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
                return False

            data = response.json()
            if "response" in data:
                data = data["response"]

            if isinstance(data, list):
                if not data:
                    print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
                    return False
                user_data = data[0]
            else:
                user_data = data

            user_uuid = user_data.get("uuid")
            if not user_uuid:
                print(f"❌ UUID пользователя {telegram_id} не найден")
                return False

            # 2. Удаляем пользователя
            return self.delete_user_by_uuid(user_uuid, verbose)

        except Exception as e:
            print(f"❌ Ошибка удаления пользователя: {e}")
            return False

    def get_user_hwid_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """
        Получает данные пользователя по Telegram ID
        Возвращает: {
            "user_uuid": str,
            "devices": list,
            "total_devices": int,
            "subscription_days": int,  # Количество полных дней до истечения
            "expire_at": str,
            "tarif": str
        }
        """
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Accept": "application/json"
        }

        try:
            # 1. Получаем пользователя по Telegram ID
            response = requests.get(
                f"{REMNAWAVE_URL}/api/users/by-telegram-id/{telegram_id}",
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                print(f"⚠️ Пользователь с Telegram ID {telegram_id} не найден")
                return None

            data = response.json()
            if "response" in data:
                data = data["response"]

            if isinstance(data, list):
                if not data:
                    return None
                user_data = data[0]
            else:
                user_data = data

            user_uuid = user_data.get("uuid")
            if not user_uuid:
                print("⚠️ UUID пользователя не найден")
                return None

            # ========== ПОЛУЧАЕМ ИНФОРМАЦИЮ О ПОДПИСКЕ ==========
            subscription_days = 0
            expire_at = None
            tarif = "unknown"

            # Пробуем получить данные о подписке из user_data
            if "expire_at" in user_data and user_data["expire_at"]:
                expire_at = user_data["expire_at"]
                try:
                    # Вычисляем количество дней до истечения
                    expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
                    now = datetime.now().astimezone()

                    # ========== ИСПРАВЛЕНО: правильный расчет дней ==========
                    delta = expire_date - now

                    # Вариант 1: Округление вниз (полные дни)
                    subscription_days = delta.days

                    # Вариант 2: Округление вверх (если есть часы/минуты, добавляем день)
                    # subscription_days = delta.days + (1 if delta.seconds > 0 else 0)

                    # Вариант 3: Округление до ближайшего целого
                    # subscription_days = int(round(delta.total_seconds() / 86400))

                    # Если подписка уже истекла
                    if subscription_days < 0:
                        subscription_days = 0

                except Exception as e:
                    print(f"⚠️ Ошибка расчета дней: {e}")
                    subscription_days = 0

            # Получаем тариф
            if "plan_type" in user_data:
                tarif = user_data["plan_type"]
            elif "plan" in user_data:
                tarif = user_data["plan"]
            elif "tarif" in user_data:
                tarif = user_data["tarif"]

            # 2. Получаем HWID устройства по UUID пользователя
            hwid_response = requests.get(
                f"{REMNAWAVE_URL}/api/hwid/devices/{user_uuid}",
                headers=headers,
                timeout=30
            )

            if hwid_response.status_code != 200:
                print(f"⚠️ HWID для пользователя {user_uuid} не найден")
                return {
                    "user_uuid": user_uuid,
                    "devices": [],
                    "total_devices": 0,
                    "subscription_days": subscription_days,
                    "expire_at": expire_at,
                    "tarif": tarif
                }

            hwid_data = hwid_response.json()

            if "response" in hwid_data:
                hwid_data = hwid_data["response"]

            # Извлекаем список устройств
            devices = []
            if isinstance(hwid_data, dict):
                if "devices" in hwid_data:
                    devices = hwid_data["devices"]
                elif "items" in hwid_data:
                    devices = hwid_data["items"]
                elif "data" in hwid_data:
                    devices = hwid_data["data"]
                elif hwid_data.get("hwid"):
                    devices = [hwid_data]
            elif isinstance(hwid_data, list):
                devices = hwid_data

            # Форматируем каждое устройство
            formatted_devices = []
            for device in devices:
                formatted_devices.append({
                    "hwid": device.get("hwid", "Неизвестно"),
                    "platform": device.get("platform", "Неизвестно"),
                    "os_version": device.get("osVersion", "Неизвестно"),
                    "device_model": device.get("deviceModel", "Неизвестно"),
                    "user_agent": device.get("userAgent", "Неизвестно"),
                    "request_ip": device.get("requestIp", "Неизвестно"),
                    "created_at": device.get("createdAt", "Неизвестно"),
                    "updated_at": device.get("updatedAt", "Неизвестно"),
                    "user_id": device.get("userId", "Неизвестно"),
                    "device_name": f"{device.get('platform', '')} {device.get('deviceModel', '')}".strip() or "Неизвестно"
                })

            return {
                "user_uuid": user_uuid,
                "devices": formatted_devices,
                "total_devices": len(formatted_devices),
                "subscription_days": subscription_days,
                "expire_at": expire_at,
                "tarif": tarif
            }

        except Exception as e:
            print(f"❌ Ошибка получения данных пользователя: {e}")
            return None

    def get_subscription_status(self, telegram_id: int) -> Dict:
        """
        Получает статус подписки пользователя
        """

        # Получаем базовые данные пользователя
        user_data = self.get_user_hwid_by_telegram_id(telegram_id)

        if not user_data:
            return {
                "status": "not_found",
                "status_text": "❌ Пользователь не найден",
                "subscription_days": 0,
                "expire_at": None,
                "tarif": "unknown",
                "total_devices": 0,
                "user_uuid": None
            }

        # ========== ДЕЛАЕМ ДОПОЛНИТЕЛЬНЫЙ ЗАПРОС ДЛЯ ПОЛУЧЕНИЯ EXPIRE_AT ==========
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Accept": "application/json"
        }

        user_uuid = user_data.get("user_uuid")
        subscription_days = 0
        expire_at = None
        tarif = user_data.get("tarif", "unknown")

        try:
            # Получаем полную информацию о пользователе по UUID
            response = requests.get(
                f"{REMNAWAVE_URL}/api/users/{user_uuid}",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if "response" in data:
                    data = data["response"]

                # Извлекаем expire_at
                if "expire_at" in data and data["expire_at"]:
                    expire_at = data["expire_at"]

                    # Вычисляем количество дней
                    try:
                        expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
                        now = datetime.now().astimezone()
                        delta = expire_date - now
                        subscription_days = delta.days if delta.days > 0 else 0
                    except Exception as e:
                        print(f"⚠️ Ошибка расчета дней: {e}")
                        subscription_days = 0

                # Обновляем тариф
                if "plan_type" in data:
                    tarif = data["plan_type"]
                elif "plan" in data:
                    tarif = data["plan"]

        except Exception as e:
            print(f"⚠️ Ошибка получения данных пользователя: {e}")

        # ========== ОПРЕДЕЛЯЕМ СТАТУС ==========
        total_devices = user_data.get("total_devices", 0)

        if expire_at is None:
            status = "inactive"
            status_text = "⚪ Подписка не активирована"
        elif subscription_days <= 0:
            status = "expired"
            status_text = "🔴 Подписка истекла"
        else:
            if subscription_days <= 3:
                status_text = f"🟡 Скоро истекает ({subscription_days} дн.)"
            elif subscription_days <= 7:
                status_text = f"🟡 Истекает через {subscription_days} дней"
            else:
                status_text = f"🟢 Активна ({subscription_days} дней)"
            status = "active"

        return {
            "status": status,
            "status_text": status_text,
            "subscription_days": subscription_days,
            "expire_at": expire_at,
            "tarif": tarif,
            "total_devices": total_devices,
            "user_uuid": user_uuid
        }

    def check_subscription_status(self, telegram_id: int) -> str:
        """
        Упрощенная проверка статуса подписки

        Returns: "active", "expired", "inactive", "not_found"
        """
        result = self.get_subscription_status(telegram_id)
        return result["status"]

    def _check_all_subscriptions(self):
        """Проверка всех подписок на истечение срока"""
        current_time = datetime.now()
        expired_users = []
        expiring_soon_users = []

        conn = sqlite3.connect('mesa_all.sql')
        cur = conn.cursor()

        try:
            # Получаем всех пользователей с активной подпиской
            # ========== ВАРИАНТ 1: ПРАВИЛЬНОЕ ИЗВЛЕЧЕНИЕ ==========
            cur.execute('SELECT user_id FROM users')
            users = cur.fetchall()

            for user in users:
                user_id = user[0]  # Просто берем первый элемент кортежа
                status_info = vpn_manager.get_subscription_status(user_id)
                print(status_info)

            # ========== ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ ОБ ИСТЕКАЮЩЕЙ ПОДПИСКЕ ==========
            if expiring_soon_users:
                print(f"🟡 Найдено {len(expiring_soon_users)} пользователей с истекающей подпиской")

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="tarifes"))
                keyboard.add(types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL))

                message_text = """
    ⚠️ <b>ВНИМАНИЕ! Ваша подписка скоро истечет!</b>

    📅 Ваша подписка заканчивается через <b>{days_left} дня(ей)</b> - {expire_date}.

    Чтобы не потерять доступ к VPN, пожалуйста, продлите подписку заранее!

    🔹 <b>Как продлить:</b>
    1️⃣ Нажмите кнопку «Продлить подписку»
    2️⃣ Выберите удобный тариф
    3️⃣ Оплатите и продолжайте пользоваться!

    🔄 Нажмите кнопку ниже, чтобы продлить подписку прямо сейчас!
    """

                for user in expiring_soon_users:
                    user_id = user['user_id']
                    days_left = user['days_left']
                    expire_date = user['expire_date'].strftime('%d.%m.%Y')

                    try:
                        bot.send_message(
                            user_id,
                            message_text.format(
                                days_left=days_left,
                                expire_date=expire_date
                            ),
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        print(f"✅ Уведомление отправлено пользователю {user_id} (осталось {days_left} дн.)")
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

            cur.close()
            conn.close()

        except Exception as e:
            print(f"❌ Ошибка при проверке подписок: {e}")
            cur.close()
            conn.close()
            return

        # ========== ВЫВОД СТАТИСТИКИ ==========
        print(f"\n📊 СТАТИСТИКА ПРОВЕРКИ ПОДПИСОК:")
        print(f"🟢 Активных подписок: {len(users) - len(expired_users)}")
        print(f"🔴 Истекших (статус изменен на inactive): {len(expired_users)}")
        print(f"🟡 Истекают через 2 дня: {len(expiring_soon_users)}")

        return expired_users

def connect_ssh():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(**SERVER)
    return client

# ========== ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ==========
def add_user(email, uuid):
    client = connect_ssh()
    new_uuid = uuid

    stdin, stdout, stderr = client.exec_command(f"cat {CONFIG_PATH}")
    config = json.loads(stdout.read().decode())

    added_count = 0

    # Добавление в inbound
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless":
            if "clients" not in inbound["settings"]:
                inbound["settings"]["clients"] = []
            existing = [c for c in inbound["settings"]["clients"] if c.get("email") == email]
            if not existing:
                inbound["settings"]["clients"].append({
                    "id": new_uuid,
                    "email": email,
                    "flow": "xtls-rprx-vision"
                })
                added_count += 1
                print(f"✅ Добавлен в inbound: {inbound.get('tag', 'unnamed')}")

    # Добавление в outbound
    # for outbound in config.get("outbounds", []):
    #     if outbound.get("protocol") == "vless":
    #         if "vnext" in outbound["settings"]:
    #             for vnext in outbound["settings"]["vnext"]:
    #                 if "users" not in vnext:
    #                     vnext["users"] = []
    #                 existing = [u for u in vnext["users"] if u.get("email") == email]
    #                 if not existing:
    #                     vnext["users"].append({
    #                         "id": new_uuid,
    #                         "encryption": "none",
    #                         "flow": "xtls-rprx-vision"
    #                     })
    #                     added_count += 1
    #                     print(f"✅ Добавлен в outbound: {outbound.get('tag', 'unnamed')}")

    if added_count > 0:
        new_config = json.dumps(config, indent=2)
        client.exec_command(f"cat > {CONFIG_PATH} <<'EOF'\n{new_config}\nEOF")
        client.exec_command("systemctl restart xray")
        print(f"\n🔄 Xray перезапущен")
    else:
        print("\n❌ Не найден inbound/outbound с протоколом vless")

    client.close()
    return new_uuid, added_count

# ========== УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО UUID ==========
def remove_user_by_uuid(uuid_to_remove):
    client = connect_ssh()

    stdin, stdout, stderr = client.exec_command(f"cat {CONFIG_PATH}")
    config = json.loads(stdout.read().decode())

    removed_count = 0
    removed_email = None

    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless" and "clients" in inbound["settings"]:
            for c in inbound["settings"]["clients"]:
                if c.get("id") == uuid_to_remove:
                    removed_email = c.get("email")
            original_len = len(inbound["settings"]["clients"])
            inbound["settings"]["clients"] = [c for c in inbound["settings"]["clients"] if
                                              c.get("id") != uuid_to_remove]
            if len(inbound["settings"]["clients"]) < original_len:
                removed_count += 1
                print(f"✅ Удален из inbound: {inbound.get('tag', 'unnamed')}")

    for outbound in config.get("outbounds", []):
        if outbound.get("protocol") == "vless" and "vnext" in outbound["settings"]:
            for vnext in outbound["settings"]["vnext"]:
                if "users" in vnext:
                    for u in vnext["users"]:
                        if u.get("id") == uuid_to_remove:
                            removed_email = u.get("email")
                    original_len = len(vnext["users"])
                    vnext["users"] = [u for u in vnext["users"] if u.get("id") != uuid_to_remove]
                    if len(vnext["users"]) < original_len:
                        removed_count += 1
                        print(f"✅ Удален из outbound: {outbound.get('tag', 'unnamed')}")

    if removed_count > 0:
        new_config = json.dumps(config, indent=2)
        client.exec_command(f"cat > {CONFIG_PATH} <<'EOF'\n{new_config}\nEOF")
        client.exec_command("systemctl restart xray")
        print(f"\n🔄 Xray перезапущен")
        print(f"\n✅ Удален: {removed_email if removed_email else uuid_to_remove}")
    else:
        print(f"\n❌ UUID {uuid_to_remove} не найден")

    client.close()
    return removed_count

# ========== УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ПО EMAIL ==========
def remove_user_by_email(email):
    client = connect_ssh()

    stdin, stdout, stderr = client.exec_command(f"cat {CONFIG_PATH}")
    config = json.loads(stdout.read().decode())

    removed_count = 0
    removed_uuid = None

    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless" and "clients" in inbound["settings"]:
            for c in inbound["settings"]["clients"]:
                if c.get("email") == email:
                    removed_uuid = c.get("id")
            original_len = len(inbound["settings"]["clients"])
            inbound["settings"]["clients"] = [c for c in inbound["settings"]["clients"] if c.get("email") != email]
            if len(inbound["settings"]["clients"]) < original_len:
                removed_count += 1
                print(f"✅ Удален из inbound: {inbound.get('tag', 'unnamed')}")

    for outbound in config.get("outbounds", []):
        if outbound.get("protocol") == "vless" and "vnext" in outbound["settings"]:
            for vnext in outbound["settings"]["vnext"]:
                if "users" in vnext:
                    for u in vnext["users"]:
                        if u.get("email") == email:
                            removed_uuid = u.get("id")
                    original_len = len(vnext["users"])
                    vnext["users"] = [u for u in vnext["users"] if u.get("email") != email]
                    if len(vnext["users"]) < original_len:
                        removed_count += 1
                        print(f"✅ Удален из outbound: {outbound.get('tag', 'unnamed')}")

    if removed_count > 0:
        new_config = json.dumps(config, indent=2)
        client.exec_command(f"cat > {CONFIG_PATH} <<'EOF'\n{new_config}\nEOF")
        client.exec_command("systemctl restart xray")
        print(f"\n🔄 Xray перезапущен")
        print(f"\n✅ Удален: {email} (UUID: {removed_uuid})")
    else:
        print(f"\n❌ Пользователь {email} не найден")

    client.close()
    return removed_count

# ========== ПОКАЗАТЬ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ ==========
def list_users():
    client = connect_ssh()
    stdin, stdout, stderr = client.exec_command(f"cat {CONFIG_PATH}")
    config = json.loads(stdout.read().decode())

    users = {}
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless" and "clients" in inbound["settings"]:
            for c in inbound["settings"]["clients"]:
                if c.get("id") and c.get("email"):
                    users[c.get("id")] = c.get("email")

    print("\n" + "=" * 60)
    print("📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    if users:
        for uid, email in users.items():
            print(f"📧 {email:<30} -> 🔑 {uid}")
        print("-" * 60)
        print(f"Всего: {len(users)} пользователей")
    else:
        print("❌ Нет пользователей")
    print("=" * 60 + "\n")

    client.close()
    return users


def safe_send(chat_id, text, max_retries=3):
    for i in range(max_retries):
        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            return True
        except Exception as e:
            print(f"⚠️ Попытка {i + 1}: {e}")
            time.sleep(2)
    return False

def safe_send3(chat_id, text=None, photo=None, parse_mode="HTML", max_retries=3):
    for i in range(max_retries):
        try:
            if photo:
                bot.send_photo(chat_id=chat_id, photo=photo, caption=text, parse_mode=parse_mode)
            else:
                bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            print(f"⚠️ Попытка {i+1} отправки failed: {e}")
            time.sleep(2)
    return False

# Инициализация менеджеров
subscription_manager = SubscriptionManager()
vpn_manager = VPNManager(subscription_manager)

# Загружаем сохраненные подписки
subscription_manager._load_subscriptions()

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start']) # Главное меню
def start_command(message):
    user_id = message.from_user.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # ========== ПОДПИСКА ПОДТВЕРЖДЕНА - ПОКАЗЫВАЕМ ГЛАВНОЕ МЕНЮ ==========
    keyboard = types.InlineKeyboardMarkup()
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
    conn.commit()
    people_id = message.chat.id
    cur.execute(f"SELECT user_id FROM users WHERE user_id = {people_id}")
    data = cur.fetchone()
    if data is None:
        keyboard.add(types.InlineKeyboardButton(text="🔥 Пробный период", callback_data="activ1"))
    keyboard.add(types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe"))
    keyboard.add(types.InlineKeyboardButton(text="📊 Тарифы", callback_data="tarifes"))
    keyboard.add(types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL),
                 types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil"))
    # keyboard.add(types.InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral"))

    photo = open("./start_mes.png", "rb")
    welcome_text = f"""
Главное меню

🔔 Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a> чтобы быть в курсе новостей и акций.

Выберите действие:
    """
    bot.send_photo(
        message.chat.id,
        caption=welcome_text,
        photo=photo,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    """Команда /start с проверкой подписки на канал"""

    user = message.from_user

    # Сохраняем пользователя в БД
    conn = sqlite3.connect('itprogerSTART.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
    conn.commit()

    user_id1 = message.chat.id
    user_names1 = message.chat.username
    us = message.from_user.first_name
    user_us = f"{us}, {message.from_user.last_name}"
    people_id = message.chat.id

    cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {people_id}")
    data = cur.fetchone()

    if data is None:
        cur.execute("INSERT INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id1, user_names1))
        conn.commit()
        bot.send_message(chat_id=my_id, text=f"Пользователь с ID: <code>{user_id1}</code>\n"
                                                  f"USER: @{user_names1}\n"
                                                  f"NAME: {user_us}\n\n"
                                                  f"Использовал команду /start и был занесён в базу (itprogerSTART)",
                         parse_mode="HTML")
    cur.close()
    conn.close()

    # ========== ПРОВЕРКА ПОДПИСКИ НА КАНАЛ ==========

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def referral_callback(call):
    user_id = call.from_user.id
    bot_username = bot.get_me().username

    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()

    # Получаем статистику из таблицы рефералов
    cur.execute("SELECT referral_count, bonus_days FROM referrals WHERE user_id = ?", (user_id,))
    stats = cur.fetchone()

    if not stats:
        # Если пользователя нет в таблице рефералов, добавляем
        cur.execute(
            "INSERT INTO referrals (user_id, referrer_id, referral_count, bonus_days) VALUES (?, ?, ?, ?)",
            (user_id, None, 0, 0)
        )
        conn.commit()
        cur.execute("SELECT referral_count, bonus_days FROM referrals WHERE user_id = ?", (user_id,))
        stats = cur.fetchone()

    # Получаем историю приглашений
    cur.execute(
        "SELECT new_user_id, bonus_days, created_at FROM referral_history WHERE referrer_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )
    history = cur.fetchall()

    cur.close()
    conn.close()

    # Генерируем реферальную ссылку
    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    # Формируем текст с историей
    history_text = ""
    if history:
        history_text = "\n\n📋 <b>Последние приглашения:</b>\n"
        for idx, (new_user_id, bonus, created_at) in enumerate(history, 1):
            history_text += f"{idx}. Пользователь ID: {new_user_id} (+{bonus} дней) - {created_at[:10]}\n"
    else:
        history_text = "\n\n📋 У вас пока нет приглашенных друзей."

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_referral"))
    # keyboard.add(types.InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="referral_leaderboard"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="alpha"))

    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>+3 дня</b> подписки за каждого!\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"👤 Приглашено друзей: <b>{stats[0]}</b>\n"
        f"🎁 Бонусных дней получено: <b>{stats[1]}</b>\n"
        f"{history_text}\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"💡 Просто отправьте эту ссылку другу — и он получит пробный период, а вы бонусные дни!",
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "copy_referral")
def copy_referral_callback(call):
    user_id = call.from_user.id
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    bot.send_message(
        call.message.chat.id,
        f"🔗 <b>Ваша реферальная ссылка:</b>\n\n"
        f"<code>{referral_link}</code>\n\n"
        f"📱 Нажмите на ссылку, чтобы скопировать, или отправьте её друзьям!",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "referral_leaderboard")
def referral_leaderboard_callback(call):
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()

    # Топ-10 пользователей по количеству приглашений
    cur.execute('''
        SELECT user_id, referral_count, bonus_days 
        FROM referrals 
        WHERE referral_count > 0 
        ORDER BY referral_count DESC, bonus_days DESC 
        LIMIT 10
    ''')

    top_users = cur.fetchall()
    cur.close()
    conn.close()

    if not top_users:
        leaderboard_text = "📊 Пока никто не пригласил друзей. Будьте первым! 🏆"
    else:
        leaderboard_text = "🏆 <b>Таблица лидеров</b>\n\n"
        for idx, (user_id, count, bonus) in enumerate(top_users, 1):
            # Пытаемся получить username пользователя
            try:
                chat = bot.get_chat(user_id)
                name = chat.username if chat.username else f"ID: {user_id}"
            except:
                name = f"ID: {user_id}"

            leaderboard_text += f"{idx}. @{name} — {count} приглашений (+{bonus} дней)\n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="🔙 Назад", callback_data="referral"))

    bot.send_message(
        call.message.chat.id,
        leaderboard_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
# @bot.message_handler(commands=['subscribe'])
# def show_plans_command1(message):
#     """Показать тарифные планы"""
#     user_id = message.chat.id
#     is_subscribed = ChannelChecker.check_subscription(user_id)
#
#     if not is_subscribed:
#         # Пользователь НЕ подписан - просим подписаться
#         keyboard = types.InlineKeyboardMarkup()
#         keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
#         keyboard.add(
#             types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))
#
#         bot.send_message(
#             message.chat.id,
#             f"🔒 <b>Требуется подписка на канал!</b>\n\n"
#             f"<b>Как получить доступ:</b>\n"
#             f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
#             f"2️⃣ Подпишитесь на канал\n"
#             f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
#             parse_mode="HTML",
#             reply_markup=keyboard
#         )
#         return
#     plans = subscription_manager.plans
#
#     text = '''
# 📄 Доступные тарифные планы:
#
# Выберите понравившийся тариф
# '''
#     keyboard = types.InlineKeyboardMarkup(row_width=2)
#     keyboard.add(
#         types.InlineKeyboardButton("🔥 Пробный", callback_data="plan_trial"),
#         types.InlineKeyboardButton("💎 Премиум", callback_data="activate_premium_now")
#     )
#
#     bot.send_message(
#         message.chat.id,
#         text,
#         reply_markup=keyboard,
#         parse_mode="HTML"
#     )

# @bot.message_handler(commands=['newvpn'])
# def process_vpn_email_step(message):
#     user_id = message.chat.id
#     is_subscribed = ChannelChecker.check_subscription(user_id)
#
#     if not is_subscribed:
#         # Пользователь НЕ подписан - просим подписаться
#         keyboard = types.InlineKeyboardMarkup()
#         keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
#         keyboard.add(
#             types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))
#
#         bot.send_message(
#             message.chat.id,
#             f"🔒 <b>Требуется подписка на канал!</b>\n\n"
#             f"<b>Как получить доступ:</b>\n"
#             f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
#             f"2️⃣ Подпишитесь на канал\n"
#             f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
#             parse_mode="HTML",
#             reply_markup=keyboard
#         )
#         return
#     conn = sqlite3.connect('itproger1.sql')
#     cur = conn.cursor()
#     cur.execute(
#         'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_uuid1 varchar(50))')
#     conn.commit()
#     user_id1 = message.chat.id
#     people_id = message.chat.id
#     cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {people_id}")
#     data = cur.fetchone()
#
#     if data is None:
#
#         """Обработка email для VPN"""
#
#         email = f'{COUNTRY_PHOTO}FREE_{user_id1}-{randint(1, 9999999)}'
#         emailxray = email.replace(f"{COUNTRY_PHOTO}", "")
#
#         plan_id = "trial"
#         subscription = subscription_manager.create_subscription(user_id1, plan_id)
#
#         # Создаем VPN аккаунт
#         bot.edit_message_text(
#             chat_id=message.chat.id,
#             message_id=message.message_id,
#             text="⏳ Создаю аккаунт...")
#
#         time.sleep(2)
#
#         result = vpn_manager.add_user(user_id1, email)
#
#         mark = types.InlineKeyboardMarkup()
#         btn1 = types.InlineKeyboardButton(text="🔎 Сгенерировать QR-код", callback_data="QR_codee")
#         mark.add(btn1)
#         if result["success"]:
#
#             photo1 = open("./photo_happ.jpg", "rb")
#
#             # Формируем ответ
#             limit_text = "∞ GB"
#
#             response_text = f"""
#     📋 Информация:
#
#     • Тариф: 🔥 Пробный
#     • Трафик: {limit_text}
#     • Осталось дней: 3
#
#     <b>Инструкция по подключению:</b>
#
#     1️⃣ <b>ШАГ 1</b>
#     Нажмите на кнопку <a href="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru">Скачать приложение</a> для того, чтобы скачать <b>HAPP</b> на устройство.
#     2️⃣ <b>ШАГ 2</b>
#     👇Скопируйте ссылку ниже, нажав на неё👇
#     🔗 Ссылка на подключение:
#     <pre>{result['vless_link']}</pre>
#
#     Перейдите в <b>HAPP</b> и нажмите “Из буфера”. Наша ссылка отобразится на главном экране.
#     3️⃣ <b>ШАГ 3</b>
#     Нажмите по кнопке включения сверху в приложении.
#     4️⃣ <b>ШАГ 4</b>
#     Разрешите добавление конфигурации.
#     """
#
#             bot.send_photo(
#                 message.chat.id,
#                 caption=response_text,
#                 photo=photo1,
#                 parse_mode="HTML",
#                 reply_markup=mark
#             )
#             uuuid1 = result["uuid"]
#
#             new_uuid, count = add_user(emailxray, uuuid1)
#             print(f"\n✅ Пользователь добавлен!")
#             print(f"📧 Email: {email}")
#             print(f"🔑 UUID: {new_uuid}")
#             print(f"📊 Добавлен в {count} мест")
#             user_uuid1 = result["uuid"]
#             cur.execute("INSERT INTO users (user_id1, user_uuid1) VALUES ('%s', '%s')" % (user_id1, user_uuid1))
#             conn.commit()
#             bot.send_message(chat_id=my_id,
#                              text=f"Пользователь использовал кнопку АКТИВИРОВАТЬ и был занесён в базу (itproger1, 3X-UI)\nID: <code>{user_id1}</code>\nUUID: <code>{user_uuid1}</code>",
#                              parse_mode="HTML")
#             conn = sqlite3.connect('message.sql')
#             cur = conn.cursor()
#             cur.execute(
#                 'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
#             conn.commit()
#             stats = "True"
#             cur.execute("INSERT INTO users (user_id1, user_names1) VALUES (?, ?)", (user_id1, stats))
#             conn.commit()
#             conn = sqlite3.connect('itprogMES_free.sql')
#             cur.execute(
#                 'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
#             conn.commit()
#
#         else:
#             bot.send_message(
#                 message.chat.id,
#                 f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\nВведите /newvpn для активации",
#                 parse_mode="HTML"
#             )
#
#     else:
#         markup = types.InlineKeyboardMarkup()
#         btn1 = types.InlineKeyboardButton(text="⚙️Обнулить статус", callback_data="reset_stat")
#         markup.add(btn1)
#         bot.send_message(message.chat.id,
#                          "У вас уже есть ссылка для подключения",
#                          reply_markup=markup
#                          )
#
#     cur.close()
#     conn.close()
#
#     time.sleep(3600)
#     bot.send_message(message.chat.id,
#                      "Всё получилось ❓\n\nЕсли хочешь - помогу с настройкой\n\n📞Поддержка - @MESA_VPN_support")
@bot.callback_query_handler(func=lambda call: call.data == "alpha") # Главное меню
def start_command(call):
    """Команда /start с проверкой подписки на канал"""
    user_id = call.message.from_user.id
    user = call.message.from_user

    # Сохраняем пользователя в БД
    conn = sqlite3.connect('itprogerSTART.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
    conn.commit()

    user_id1 = call.message.chat.id
    user_names1 = call.message.chat.username
    us = call.message.from_user.first_name
    user_us = f"{us}, {call.message.from_user.last_name}"
    people_id = call.message.chat.id

    cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {people_id}")
    data = cur.fetchone()

    if data is None:
        cur.execute("INSERT INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id1, user_names1))
        conn.commit()
        bot.send_message(chat_id=my_id, text=f"Пользователь с ID: <code>{user_id1}</code>\n"
                                                  f"USER: @{user_names1}\n"
                                                  f"NAME: {user_us}\n\n"
                                                  f"Использовал команду /start и был занесён в базу (itprogerSTART)",
                         parse_mode="HTML")
    cur.close()
    conn.close()

    # ========== ПРОВЕРКА ПОДПИСКИ НА КАНАЛ ==========
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на канал\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # ========== ПОДПИСКА ПОДТВЕРЖДЕНА - ПОКАЗЫВАЕМ ГЛАВНОЕ МЕНЮ ==========
    keyboard = types.InlineKeyboardMarkup()
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
    conn.commit()
    people_id = call.message.chat.id
    cur.execute(f"SELECT user_id FROM users WHERE user_id = {people_id}")
    data = cur.fetchone()
    if data is None:
        keyboard.add(types.InlineKeyboardButton(text="🔥 Пробный период", callback_data="activ1"))
    keyboard.add(types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe"))
    keyboard.add(types.InlineKeyboardButton(text="📊 Тарифы", callback_data="tarifes"))
    keyboard.add(types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL), types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil"))
    # keyboard.add(types.InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referral"))

    photo = open("./start_mes.png", "rb")
    welcome_text = f"""
Главное меню

🔔 Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a> чтобы быть в курсе новостей и акций.

Выберите действие:
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.message_handler(commands=['otziv']) # Оставить отзыв
def otziv(message):
    user_id = message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на канал\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return
    args = message.text.split()
    user_id = message.chat.id

    if len(args) > 1:
        bot.send_message(message.chat.id, f"Отзыв принят, спасибо ❤️\n\n"
                                          f"Поддержка - @MESA_VPN_support")

        _otziv_ = message.text.replace("/otziv ", "")
        bot.send_message(chat_id=my_id,
                         text=  f"Новый отзыв!\n"
                                f"<blockquote>{str(_otziv_)}</blockquote>"
                                f"Чтобы ответить - <code>/admin_send {user_id}</code>",
                         parse_mode="HTML"
        )
        try:
            conn = sqlite3.connect('otziv.sql')
            cur = conn.cursor()
            cur.execute(
                'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), message_id varchar(50))')
            conn.commit()
            cur.execute("INSERT INTO users (user_id, message_id) VALUES ('%s', '%s')" % (user_id, _otziv_))
            conn.commit()
        except:
            bot.send_message(chat_id=my_id, text="Ошибка при внесении отзыва в otziv.sql")
    else:
        bot.send_message(message.chat.id, "Введите отзыв после команды: /otziv ...\n\n")

# @bot.message_handler(commands=['myvless'])
# def myvless(message):
#     try:
#         people_id = message.chat.id
#
#         # ===== ПОДКЛЮЧЕНИЕ К ПЕРВОЙ БАЗЕ (бесплатные ключи) =====
#         conn1 = sqlite3.connect('itproger1.sql')
#         cur1 = conn1.cursor()
#         cur1.execute(f"SELECT user_uuid1 FROM users WHERE user_id1 = {people_id}")
#         result1 = cur1.fetchone()  # Получаем результат
#         conn1.close()
#
#         # ===== ПОДКЛЮЧЕНИЕ КО ВТОРОЙ БАЗЕ (платные ключи) =====
#         conn2 = sqlite3.connect('itproger4.sql')
#         cur2 = conn2.cursor()
#         cur2.execute(f"SELECT user_names1 FROM users WHERE user_id1 = {people_id}")
#         result2 = cur2.fetchone()  # Получаем результат
#         conn2.close()
#
#         # Извлекаем данные (если есть)
#         data = result1[0] if result1 else None
#         data1 = result2[0] if result2 else None
#
#         print(f"DEBUG: user_id={people_id}, free_key={data}, paid_key={data1}")  # Для отладки
#
#         # ===== ЛОГИКА ОТВЕТА =====
#         if data is None and data1 is None:
#             # Нет ни бесплатного, ни платного ключа
#             bot.send_message(message.chat.id, "❌ У вас нет активной ссылки для подключения")
#
#         elif data is not None and data1 is not None:
#             # Есть оба ключа
#             total1 = f"vless://{data}@{SERVER_DOMEN}:8443?type=tcp&encryption=none&security=reality&pbk=NU12JRsVwScafn-bYgUHrIC_55-EPoJ00ZaixUVE_GQ&fp=chrome&sni=www.tesla.com&sid=8f9a32a6a0&spx=%2F&flow=xtls-rprx-vision#{COUNTRY_PHOTO}FREE_{message.chat.id}"
#             total2 = f"vless://{data1}@{SERVER_DOMEN}:8443?type=tcp&encryption=none&security=reality&pbk=NU12JRsVwScafn-bYgUHrIC_55-EPoJ00ZaixUVE_GQ&fp=chrome&sni=www.tesla.com&sid=8f9a32a6a0&spx=%2F&flow=xtls-rprx-vision#{COUNTRY_PHOTO}PRO_{message.chat.id}"
#
#             bot.send_message(
#                 message.chat.id,
#                 "🔎 Ваши ссылки для подключения:\n\n"
#                 f"🎁 Бесплатный ключ:\n<pre>{total1}</pre>\n\n"
#                 f"💎 Платный ключ:\n<pre>{total2}</pre>",
#                 parse_mode='HTML'
#             )
#
#         elif data is not None and data1 is None:
#             # Только бесплатный ключ
#             total1 = f"vless://{data}@{SERVER_DOMEN}:8443?type=tcp&encryption=none&security=reality&pbk=NU12JRsVwScafn-bYgUHrIC_55-EPoJ00ZaixUVE_GQ&fp=chrome&sni=www.tesla.com&sid=8f9a32a6a0&spx=%2F&flow=xtls-rprx-vision#{COUNTRY_PHOTO}FREE_{message.chat.id}"
#
#             bot.send_message(
#                 message.chat.id,
#                 "🔎 Ваша ссылка для подключения:\n\n"
#                 f"🎁 Бесплатный ключ:\n<pre>{total1}</pre>",
#                 parse_mode='HTML'
#             )
#
#         elif data is None and data1 is not None:
#             # Только платный ключ
#             total2 = f"vless://{data1}@{SERVER_DOMEN}:8443?type=tcp&encryption=none&security=reality&pbk=NU12JRsVwScafn-bYgUHrIC_55-EPoJ00ZaixUVE_GQ&fp=chrome&sni=www.tesla.com&sid=8f9a32a6a0&spx=%2F&flow=xtls-rprx-vision#{COUNTRY_PHOTO}PRO_{message.chat.id}"
#
#             bot.send_message(
#                 message.chat.id,
#                 "🔎 Ваша ссылка для подключения:\n\n"
#                 f"💎 Платный ключ:\n<pre>{total2}</pre>",
#                 parse_mode='HTML'
#             )
#
#     except Exception as e:
#         print(f"Ошибка в myvless: {e}")
#         bot.send_message(message.chat.id, "❌ Произошла ошибка при получении ваших ключей.")

@bot.callback_query_handler(func=lambda call: call.data == "profil") # Профиль пользователя
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="alpha"))
    response_text = f"""
👤 Профиль

• ID пользователя: <code>{user_id}</code>
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "tarifes") # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="⚡️ Быстрый старт", callback_data="fast_start"))
    keyboard.add(types.InlineKeyboardButton(text="💥 Стандарт", callback_data="standart"))
    keyboard.add(types.InlineKeyboardButton(text="💎 Премиум", callback_data="premium"))
    keyboard.add(types.InlineKeyboardButton(text="📈 Максимум", callback_data="maximum"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="alpha"))

    response_text = f"""
📊 Тарифы

Выберите подходящий тариф:
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "fast_start") # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="⭐️ 3 устр. | 70 ₽ | 1 мес. ⭐️", callback_data="fast:3:70:1"))
    keyboard.add(types.InlineKeyboardButton(text="4 устр. | 120 ₽ | 2 мес.", callback_data="fast:4:120:2"))
    keyboard.add(types.InlineKeyboardButton(text="5 устр. | 340 ₽ | 6 мес.", callback_data="fast:5:340:6"))
    keyboard.add(types.InlineKeyboardButton(text="6 устр. | 670 ₽ | 1 год", callback_data="fast:6:670:12"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))


    response_text = f"""
📊 Тариф: ⚡️ Быстрый старт

Что входит в тариф?

— Высокая скорость 
— <b>Безлимитный трафик</b>
— Более 10 стран в 1 подписке

Обход белых списков:
❌ Отсутствует

Автовыбор страны с обходом:
❌ Отсутствует
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "standart") # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="5 устр. | 120 ₽ | 1 мес.", callback_data="standart:5:120:1"))
    keyboard.add(types.InlineKeyboardButton(text="6 устр. | 200 ₽ | 2 мес.", callback_data="standart:6:300:2"))
    keyboard.add(types.InlineKeyboardButton(text="7 устр. | 500 ₽ | 6 мес.", callback_data="standart:7:500:6"))
    keyboard.add(types.InlineKeyboardButton(text="8 устр. | 800 ₽ | 1 год", callback_data="standart:8:800:12"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))


    response_text = f"""
📊 Тариф: 💥 Стандарт

Что входит в тариф?

— Высокая скорость 
— <b>Безлимитный трафик</b>
— Более 10 стран в 1 подписке

Обход белых списков:
✅ Есть

Автовыбор страны с обходом:
❌ Отсутствует


"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "premium") # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="⭐️ 7 устр. | 150 ₽ | 1 мес. ⭐️", callback_data="premium:7:150:1"))
    keyboard.add(types.InlineKeyboardButton(text="8 устр. | 250 ₽ | 2 мес.", callback_data="premium:8:250:2"))
    keyboard.add(types.InlineKeyboardButton(text="9 устр. | 600 ₽ | 6 мес.", callback_data="premium:9:600:6"))
    keyboard.add(types.InlineKeyboardButton(text="10 устр. | 1000 ₽ | 1 год", callback_data="premium:10:1000:12"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))


    response_text = f"""
📊 Тариф: 💎 Премиум

Что входит в тариф?

— Высокая скорость 
— <b>Безлимитный трафик</b>
— Более 10 стран в 1 подписке

Обход белых списков:
✅ Есть

Автовыбор страны с обходом:
✅ Есть


"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "maximum") # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="10 устр. | 200 ₽ | 1 мес.", callback_data="maximum:10:200:1"))
    keyboard.add(types.InlineKeyboardButton(text="12 устр. | 350 ₽ | 2 мес.", callback_data="maximum:12:350:2"))
    keyboard.add(types.InlineKeyboardButton(text="14 устр. | 800 ₽ | 6 мес.", callback_data="maximum:14:800:6"))
    keyboard.add(types.InlineKeyboardButton(text="15 устр. | 1400 ₽ | 1 год", callback_data="maximum:15:1400:12"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))

    response_text = f"""
📊 Тариф: 📈 Максимум 

Что входит в тариф?

— Высокая скорость 
— <b>Безлимитный трафик</b>
— Более 10 стран в 1 подписке

Обход белых списков:
✅ Есть

Автовыбор страны с обходом:
✅ Есть


"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("fast:")) # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)
    # Получаем данные из callback
    res = call.data.replace("fast:", "")
    res = res.split(":")

    # Или если нужно присвоить переменным
    hwids = int(res[0])
    money = int(res[1])
    times = int(res[2])

    # Выводим по аргументам
    print(f"Аргумент 1: {hwids}")
    print(f"Аргумент 2: {money}")
    print(f"Аргумент 3: {times}")

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="✅ Оплатить", callback_data=f"f:{user_id}:{hwids}:{money}:{times}"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="fast_start"))
    if times == 1:
        times = f"{times} месяц"
    else:
        times = f"{times} месяцев"
    response_text = f"""
⚡️ Быстрый старт

Макс. количество устройств: {hwids}
Цена: {money}
Срок подписки: {times}
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("standart:")) # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)
    # Получаем данные из callback
    res = call.data.replace("standart:", "")
    res = res.split(":")

    # Или если нужно присвоить переменным
    hwids = int(res[0])
    money = int(res[1])
    times = int(res[2])

    # Выводим по аргументам
    print(f"Аргумент 1: {hwids}")
    print(f"Аргумент 2: {money}")
    print(f"Аргумент 3: {times}")

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="✅ Оплатить", callback_data=f"s:{user_id}:{hwids}:{money}:{times}"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="standart"))
    if times == 1:
        times = f"{times} месяц"
    else:
        times = f"{times} месяцев"
    response_text = f"""
💥 Стандарт

Макс. количество устройств: {hwids}
Цена: {money}
Срок подписки: {times}
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("premium:")) # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)
    # Получаем данные из callback
    res = call.data.replace("premium:", "")
    res = res.split(":")

    # Или если нужно присвоить переменным
    hwids = int(res[0])
    money = int(res[1])
    times = int(res[2])

    # Выводим по аргументам
    print(f"Аргумент 1: {hwids}")
    print(f"Аргумент 2: {money}")
    print(f"Аргумент 3: {times}")

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="✅ Оплатить", callback_data=f"p:{user_id}:{hwids}:{money}:{times}"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="premium"))
    if times == 1:
        times = f"{times} месяц"
    else:
        times = f"{times} месяцев"
    response_text = f"""
💎 Премиум 

Макс. количество устройств: {hwids}
Цена: {money}
Срок подписки: {times}
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("maximum:")) # Тарифы
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)
    # Получаем данные из callback
    res = call.data.replace("maximum:", "")
    res = res.split(":")



    # Или если нужно присвоить переменным
    hwids = int(res[0])  # 10
    money = int(res[1])  # 200
    times = int(res[2])  # 15

    # Выводим по аргументам
    print(f"Аргумент 1: {hwids}")  # 10
    print(f"Аргумент 2: {money}")  # 200
    print(f"Аргумент 3: {times}")  # 15

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="✅ Оплатить", callback_data=f"m:{user_id}:{hwids}:{money}:{times}"))
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="maximum"))
    if times == 1:
        times = f"{times} месяц"
    else:
        times = f"{times} месяцев"
    response_text = f"""
📈 Максимум 

Макс. количество устройств: {hwids}
Цена: {money}
Срок подписки: {times}
"""
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        caption=response_text,
        message_id=call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("my_hwid")) # Устройства в подписке
def my_subscription_command(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return
    hwid_info = vpn_manager.get_user_hwid_by_telegram_id(user_id)

    if not hwid_info:
        bot.send_message(user_id, "❌ Не удалось получить информацию об устройствах")
        return

    devices = hwid_info.get("devices", [])
    user_uuid = hwid_info.get("user_uuid")

    if not devices:
        mark = types.InlineKeyboardMarkup(row_width=1)
        mark.add(
            types.InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="my_hwid"
            )
        )
        mark.add(
            types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="subscribe"
            )
        )
        try:
            # Пытаемся отредактировать
            a = bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"🔑 <b>Ваш UUID:</b> <code>{user_uuid}</code>\n\n"
                     f"📱 <b>Устройства не найдены</b>\n"
                     f"Подключитесь к VPN, чтобы устройство появилось в списке.",
                reply_markup=mark,
                parse_mode="HTML"
            )
        except Exception as e:
            # Если ошибка "message is not modified" — игнорируем
            if "message is not modified" in str(e):
                bot.answer_callback_query(call.id, "✅ Успешно обновлено")
            else:
                # Если ошибка другая — показываем
                print(f"❌ Ошибка: {e}")
                bot.answer_callback_query(call.id, "⚠️ Ошибка обновления")
        return

    # ========== ОСНОВНОЙ ТЕКСТ ==========
    text = f"🔑 <b>Ваш UUID:</b> <code>{user_uuid}</code>\n\n"
    text += f"📱 <b>Найдено устройств:</b> {len(devices)}\n\n"
    text += f"👇 <b>Нажмите на устройство для подробной информации:</b>"

    # ========== СОЗДАЁМ КНОПКИ ДЛЯ УСТРОЙСТВ ==========
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    for i, device in enumerate(devices, 1):
        # Название кнопки: модель устройства или "Устройство N"
        device_model = device.get('device_model', 'Неизвестно')
        platform = device.get('platform', '')

        if device_model != 'Неизвестно' and platform:
            button_text = f"{i}. {platform} {device_model}"
        elif device_model != 'Неизвестно':
            button_text = f"{i}. {device_model}"
        else:
            button_text = f"{i}. Устройство"

        # Сохраняем индекс устройства для callback
        keyboard.add(
            types.InlineKeyboardButton(
                text=button_text,
                callback_data=f"device_info_{i - 1}"  # передаём индекс устройства
            )
        )
    keyboard.add(
        types.InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="my_hwid"
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="subscribe"
        )
    )

    try:
        # Пытаемся отредактировать
        a = bot.edit_message_caption(
            chat_id=user_id,
            message_id=call.message.message_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        # Если ошибка "message is not modified" — игнорируем
        if "message is not modified" in str(e):
            bot.answer_callback_query(call.id, "✅ Успешно обновлено")
        else:
            # Если ошибка другая — показываем
            print(f"❌ Ошибка: {e}")
            bot.answer_callback_query(call.id, "⚠️ Ошибка обновления")

@bot.callback_query_handler(func=lambda call: call.data.startswith("device_info_")) # Подробная информация об устройстве
def show_device_info(call):
    user_id = call.from_user.id

    # Получаем индекс устройства из callback
    device_index = int(call.data.replace("device_info_", ""))

    # Получаем данные об устройствах
    hwid_info = vpn_manager.get_user_hwid_by_telegram_id(user_id)

    if not hwid_info:
        bot.answer_callback_query(call.id, "❌ Ошибка получения данных")
        return

    devices = hwid_info.get("devices", [])
    user_uuid = hwid_info.get("user_uuid")

    if device_index >= len(devices):
        bot.answer_callback_query(call.id, "❌ Устройство не найдено")
        return

    device = devices[device_index]
    hwid = device.get('hwid', 'Неизвестно')
    device_model = device.get('device_model', 'Неизвестно')

    # ========== ФОРМИРУЕМ ПОДРОБНУЮ ИНФОРМАЦИЮ ОБ УСТРОЙСТВЕ ==========
    text = f"📱 <b>Детальная информация об устройстве</b>\n\n"
    text += f"🔑 <b>Ваш UUID:</b> <code>{user_uuid}</code>\n\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"🔐 <b>HWID:</b> <code>{hwid}</code>\n"
    text += f"💬 <b>Модель:</b> {device_model}\n"
    text += f"📁 <b>Платформа:</b> {device.get('platform', 'Неизвестно')}\n"
    text += f"🗂 <b>Версия ОС:</b> {device.get('os_version', 'Неизвестно')}\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"

    if device.get('user_agent') and device.get('user_agent') != 'Неизвестно':
        text += f"🌐 <b>User Agent:</b>\n<code>{device.get('user_agent')}</code>\n\n"

    if device.get('request_ip') and device.get('request_ip') != 'Неизвестно':
        text += f"🌍 <b>IP адрес:</b> {device.get('request_ip')}\n"

    if device.get('created_at') and device.get('created_at') != 'Неизвестно':
        created = device.get('created_at')
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            created = dt.strftime('%d.%m.%Y %H:%M:%S')
        except:
            pass
        text += f"📅 <b>Подключено:</b> {created}\n"

    if device.get('updated_at') and device.get('updated_at') != 'Неизвестно':
        updated = device.get('updated_at')
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            updated = dt.strftime('%d.%m.%Y %H:%M:%S')
        except:
            pass
        text += f"🔄 <b>Обновлено:</b> {updated}\n"

    # ========== КЛАВИАТУРА ==========

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            text=f"🗑️ Удалить устройство ({device_model})",
            callback_data=f"delete_device_{hwid}"
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text="⬅️ Назад к устройствам",
            callback_data="my_hwid"
        )
    )
    # Редактируем сообщение, показывая детали устройства
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    bot.answer_callback_query(call.id)

# ========== ОБРАБОТЧИК УДАЛЕНИЯ УСТРОЙСТВА ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_device_")) # Предупредительное сообщение об удалении устройства
def delete_device(call):
    user_id = call.from_user.id

    # Получаем HWID из callback
    hwid = call.data.replace("delete_device_", "")

    # Подтверждение удаления
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"confirm_delete_{hwid}"
        ),
        types.InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="my_hwid"
        )
    )

    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=f"⚠️ <b>Вы уверены, что хотите удалить устройство?</b>\n\n"
                f"🔐 HWID: <code>{hwid}</code>\n\n"
                f"После удаления устройство потеряет доступ к VPN.",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    bot.answer_callback_query(call.id)

def delete_user_device_by_hwid(user_id: int, hwid: str) -> bool:
    """
    Удаляет устройство пользователя по HWID через API

    Args:
        user_id: Telegram ID пользователя
        hwid: HWID устройства

    Returns:
        bool: True если удалено успешно
    """
    try:
        headers = {
            "Authorization": f"Bearer {REMNAWAVE_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # 1. Получаем UUID пользователя по Telegram ID
        response = requests.get(
            f"{REMNAWAVE_URL}/api/users/by-telegram-id/{user_id}",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ Пользователь с Telegram ID {user_id} не найден")
            return False

        data = response.json()
        if "response" in data:
            data = data["response"]

        user_data = data[0] if isinstance(data, list) else data
        user_uuid = user_data.get("uuid")

        if not user_uuid:
            print(f"❌ UUID пользователя {user_id} не найден")
            return False

        # 2. Удаляем устройство
        payload = {
            "userUuid": user_uuid,
            "hwid": hwid
        }

        delete_response = requests.post(
            f"{REMNAWAVE_URL}/api/hwid/devices/delete",
            headers=headers,
            json=payload,
            timeout=30
        )

        if delete_response.status_code in [200, 201, 204]:
            print(f"✅ Устройство {hwid} удалено!")
            return True
        else:
            print(f"❌ Ошибка удаления: {delete_response.text}")
            return False

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

# ========== ОБРАБОТЧИК В БОТЕ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_")) # Окончательное удаление устройства
def confirm_delete_device(call):
    user_id = call.from_user.id
    hwid = call.data.replace("confirm_delete_", "")

    bot.answer_callback_query(call.id, "🗑️ Удаляю устройство...")

    # Удаляем устройство
    success = delete_user_device_by_hwid(user_id, hwid)

    if success:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"✅ <b>Устройство успешно удалено!</b>\n\n"
                    f"🔐 HWID: <code>{hwid}</code>",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    text="📱 Обновить список устройств",
                    callback_data="my_hwid"
                )
            )
        )
    else:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"❌ <b>Не удалось удалить устройство</b>\n\n"
                    f"🔐 HWID: <code>{hwid}</code>\n\n"
                    f"Попробуйте позже или обратитесь в поддержку.\n\n"
                    f"📞 @MESA_VPN_support",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="my_hwid"
                )
            )
        )


# ========== ОБРАБОТЧИК КНОПКИ "НАЗАД" ==========
# @bot.callback_query_handler(func=lambda call: call.data == "back_to_devices")
# def back_to_devices(call):
#     user_id = call.from_user.id
#
#     # Просто вызываем функцию myhwid для этого пользователя
#     # Создаём фейковое сообщение
#     class FakeMessage:
#         def __init__(self, chat_id):
#             self.chat = type('obj', (object,), {'id': chat_id})()
#             self.from_user = type('obj', (object,), {'id': chat_id})()
#
#     fake_msg = FakeMessage(user_id)
#     get_my_hwid(fake_msg)
#
#     bot.answer_callback_query(call.id)
@bot.callback_query_handler(func=lambda call: call.data == "subscribe") # Управление подпиской
def subscribe(call):
    """Информация о подписке"""
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return
    #sub = subscription_manager.get_user_subscription(user_id)
    #
    # if not sub:
    #     bot.send_message(
    #         call.message.chat.id,
    #         "❌ У вас нет активной подписки!\n"
    #         "Выберите тариф:",
    #
    #         parse_mode="HTML"
    #     )
    #     return
    #
    # # Форматируем даты
    # if sub['start_date']:
    #     start_date = datetime.fromisoformat(sub['start_date']).strftime('%d.%m.%Y')
    # else:
    #     start_date = "—"
    #
    # if sub['expires_at']:
    #     expires_date = datetime.fromisoformat(sub['expires_at']).strftime('%d.%m.%Y')
    # else:
    #     expires_date = "—"
    #
    # # Статус
    # status_icons = {
    #     'active': '✅ Активна',
    #     'pending': '⏱ Ожидает активации',
    #     'expired': '❌ Истекла'
    # }
    # status_text = status_icons.get(sub['status'], sub['status'])
    #
    # # Оставшиеся дни
    # remaining_days = subscription_manager.get_remaining_days(user_id)
    #
    # # Трафик
    # limit_text = "Безлимит GB "
    # res = sub['duration_days']
    # if int(res) == 30:
    #     res = f"{res} дней"
    # else:
    #     res = f"{res} дня"
    #
    # stat = ""
    # keyboard = types.InlineKeyboardMarkup()
    # if sub['status'] == 'expired' and sub['plan_id'] == 'premium':
    #     stat = "👇 Для продления нажмите на кнопку ниже 👇"
    #     keyboard.add(
    #         types.InlineKeyboardButton("🔁 Продлить подписку", callback_data="continue_sub")
    #     )
    # elif sub['status'] == 'expired' and sub['plan_id'] == 'trial':
    #     stat = ("💎 Для покупки подписки"
    #             "👇 нажмите на кнопку ниже 👇")
    #     keyboard.add(
    #         types.InlineKeyboardButton("💎 Купить подписку", callback_data="activate_premium_now")
    #     )
    keyboard = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="⬅️ Назад", callback_data="alpha")
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
    conn.commit()
    people_id = call.message.chat.id
    cur.execute(f"SELECT user_sub FROM users WHERE user_id = {people_id}")
    sub = cur.fetchone()
    photo = open("./start_mes.png", "rb")
    hwid_info = vpn_manager.get_user_hwid_by_telegram_id(user_id)
    print(hwid_info)
    user_uuid = ""
    if hwid_info:
        user_uuid = f'Ваш идентификатор: <code>{hwid_info.get("user_uuid")}</code>\n'
        if sub is None:
            sub = ""
        else:
            sub = str(sub).replace("'", "").replace(")", "").replace("(", "").replace(",", "")
            btn3 = types.InlineKeyboardButton(text="🔑 Подключить в Happ", url=sub)
            sub = (f'🔗 Ссылка на подключение:\n'
                   f'<code>{sub}</code>\n')
            btn2 = types.InlineKeyboardButton(text="🔎 Сгенерировать QR-код", callback_data="QR_codee")
            btn4 = types.InlineKeyboardButton(text="📱 Мои устройства", callback_data="my_hwid")
            keyboard.add(btn2)
            keyboard.add(btn3)
            keyboard.add(btn4)

        cur.execute("SELECT status_profil FROM users WHERE user_id = ?", (people_id,))
        result = cur.fetchone()

        if result is None:
            status_profil = ""  # Пользователь не найден
        else:
            status_profil = str(result[0]).strip()  # Берём первое поле

        if status_profil == "free":
            status_profil = "📊 Тариф: 🔥 Пробный период\n"
        elif status_profil == "fast_start":
            status_profil = "📊 Тариф: ⚡️ Быстрый старт\n"
        elif status_profil == "standart":
            status_profil = "📊 Тариф: 💥 Стандарт\n"
        elif status_profil == "premium":
            status_profil = "📊 Тариф: 💎 Премиум\n"
        elif status_profil == "maximum":
            status_profil = "📊 Тариф: 📈 Максимум\n"
        else:
            status_profil = ""  # Если значение неизвестно
        cur.execute("SELECT days FROM users WHERE user_id = ?", (people_id,))
        days = cur.fetchone()
        if result is None:
            days = ""
        else:
            days = int(str(days).replace("'", "").replace(")", "").replace("(", "").replace(",", ""))
            if days % 10 == 2 or days % 10 == 3 or days % 10 == 4:
                days = f"⏳ Срок подписки: {days} дня"
            else:
                days = f"⏳ Срок подписки: {days} дней"
        keyboard.add(btn1)
        response_text = f"""
⚙️ Управление подпиской

{sub}
{status_profil}
{days}
"""
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            caption=response_text,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        cur.close()
        conn.close()
    else:
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="alpha"))
        response_text = f"""
⚙️ Управление подпиской

Ваша подписка: ✖️ Отсутствует
    """
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            caption=response_text,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data == "extend_sub")
def extend_subscription(call):
    user_id = call.from_user.id

    # Получаем UUID пользователя из БД или Remnawave
    hwid_info = vpn_manager.get_user_hwid_by_telegram_id(user_id)
    if not hwid_info:
        bot.send_message(user_id, "❌ Не удалось найти ваш аккаунт")
        return

    user_uuid = hwid_info.get("user_uuid")

    # Продлеваем на 30 дней
    result = vpn_manager.extend_user_subscription(
        user_uuid=user_uuid,
        extra_days=30
    )

    if result:
        bot.send_message(
            user_id,
            f"✅ <b>Подписка продлена!</b>\n\n"
            f"📅 Новая дата истечения:\n<code>{result['new_expire']}</code>\n\n"
            f"📆 Добавлено дней: {result['extra_days']}",
            parse_mode="HTML"
        )
    else:
        bot.send_message(user_id, "❌ Не удалось продлить подписку")

@bot.callback_query_handler(func=lambda call: call.data == "check_channel_subscription") # Проверка подписки на тг-канал
def check_channel_callback(call):
    """Обработчик кнопки проверки подписки на канал"""
    user_id = call.from_user.id

    bot.answer_callback_query(call.id, "🔍 Проверяю подписку...")

    is_subscribed = ChannelChecker.check_subscription(user_id)

    if is_subscribed:
        # Подписка подтверждена - показываем главное меню
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔗 Пробный период", callback_data="plan_trial"))
        keyboard.add(types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe"))
        keyboard.add(types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL),
                     types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil"))
        photo = open("./start_mes.png", "rb")
        welcome_text = f"""
Главное меню

🔔 Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a> чтобы быть в курсе новостей и акций.

Выберите действие:
"""
        bot.send_photo(
            call.message.chat.id,
            caption=welcome_text,
            photo=photo,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        bot.answer_callback_query(
            call.id,
            "✅ Подписка подтверждена! Добро пожаловать!",
            show_alert=True
        )

    else:
        # Всё ещё не подписан
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))
        photo = open("./No_sub.png", "rb")

        bot.send_photo(
            call.message.chat.id,
            caption="❌ Вы ещё не подписались на канал!",
            photo=photo,
            reply_markup=keyboard
        )

        # Обновляем сообщение
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🔒 <b>Подписка не подтверждена!</b>\n\n"
                     f"Для получения доступа к MESA VPN необходимо подписаться на канал:\n\n"
                     f"📢 <b>@{CHANNEL_USERNAME}</b>\n\n"
                     f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
                     f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
                     f"3️⃣ Нажмите <b>«Проверить подписку»</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.debug(f"Сообщение не изменилось: {e}")

# @bot.callback_query_handler(func=lambda call: call.data.startswith('plan_')) # Сообщение перед активацией
# def process_plan_selection(call):
#     """Обработка выбора тарифного плана"""
#     markup = types.InlineKeyboardMarkup()
#     markup.add(types.InlineKeyboardButton(text="АКТИВИРОВАТЬ", callback_data="activ1"))
#
#     kek = types.InlineKeyboardMarkup()
#     kek.add(types.InlineKeyboardButton(text="💎 КУПИТЬ ПРЕМИУМ", callback_data="activate_premium_now"))
#     user_id = call.from_user.id
#     plan_id = call.data.split('_')[1]
#     conn = sqlite3.connect('itproger1.sql')
#     cur = conn.cursor()
#     cur.execute(
#         'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_uuid1 varchar(50))')
#     conn.commit()
#     user_id1 = call.message.chat.id
#     people_id = call.message.chat.id
#     cur.execute(f"SELECT user_id1 FROM users WHERE user_id1 = {people_id}")
#     data = cur.fetchone()
#
#     if data is None:
#
#         if plan_id not in subscription_manager.plans:
#             bot.answer_callback_query(call.id, "❌ План не найден")
#             return
#
#         plan = subscription_manager.plans[plan_id]
#
#         # Для пробного плана сразу создаем
#         if plan_id == 'trial':
#             success_text = f"""
# ✅ Пробная подписка формируется!
#
# 📄 Тариф: {plan['name']}
# 📅 Срок: {plan['duration_days']} дней
# 📊 Трафик: ∞ GB
# ⏱ Активация: Сразу
#
# 👇 Для активации нажмите на кнопку
#             """
#
#             bot.send_message(
#                 chat_id=call.message.chat.id,
#                 text=success_text,
#                 parse_mode="HTML",
#                 reply_markup=markup
#             )
#
#             return
#
#         # Для платных планов предлагаем выбор времени активации
#         keyboard = types.InlineKeyboardMarkup(row_width=2)
#         keyboard.add(
#             types.InlineKeyboardButton("✅ Начать сразу", callback_data=f"activate_{plan_id}_now")
#             # types.InlineKeyboardButton("⏱ При первом использовании", callback_data=f"activate_{plan_id}_later")
#         )
#         keyboard.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_plan"))
#         bot.send_message(
#             chat_id=call.message.chat.id,
#             text=(
#                 f"Выбран план: {plan['name']}\n"
#                 f"Цена: {plan['price']} руб\n\n"
#                 f"Выберите когда начать подписку:"
#             ),
#             reply_markup=keyboard,
#             parse_mode="HTML"
#         )
#         conn.close()
#         cur.close()
#
#     else:
#         text = """
# Вы уже создавали пробную подписку.
#
# Для продолжения использования VPN - оформите подписку.
# """
#         bot.send_message(
#             chat_id=user_id,
#             text=text, reply_markup=kek)
@bot.callback_query_handler(func=lambda call: call.data.startswith('activate_')) # Доп. Сообщение к платной подписке
def process_activation_choice(call):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Оплатить", callback_data="paying_69")
    markup.add(btn1)
    """Обработка выбора времени активации"""
    _, plan_id, when = call.data.split('_')

    plan = subscription_manager.plans[plan_id]

    # В реальном боте здесь была бы интеграция с платежной системой
    # Для демо просто создаем подписку

    result_text = f"""
📋 Детали:

• План: {plan['name']}
• Срок: {plan['duration_days']} дней
• Трафик: ∞ GB

Цена: 69 рублей
    """

    bot.send_message(
        chat_id=call.message.chat.id,
        text=result_text,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "activ1") # Активация подписки VPN (пробник)
def activ_1(call):
    user_id = call.message.chat.id
    is_subscribed = ChannelChecker.check_subscription(user_id)

    if not is_subscribed:
        # Пользователь НЕ подписан - просим подписаться
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
        keyboard.add(
            types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

        bot.send_message(
            call.message.chat.id,
            f"🔒 <b>Требуется подписка на канал!</b>\n\n"
            f"<b>Как получить доступ:</b>\n"
            f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
            f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
            f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
    conn.commit()
    user_id1 = call.message.chat.id
    people_id = call.message.chat.id
    cur.execute(f"SELECT user_id FROM users WHERE user_id = {people_id}")
    data = cur.fetchone()

    if data is None:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="⏳ Создаю подписку..."
        )
        result = vpn_manager.create_user_and_get_link(
            username=f"user_{user_id1}",
            tg_id=user_id1,
            expire_days=3,
            plan_type="fast_start"  # 👈 Добавляем план
        )
        if result:
            HAPP_URL = f"{result['subscription_url']}"
            mark = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton(text="🔎 Сгенерировать QR-код", callback_data="QR_codee")
            btn2 = types.InlineKeyboardButton(text="🔑 Подключить в Happ", url=HAPP_URL)
            btn5 = types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe")
            btn3 = types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)
            btn4 = types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil")
            mark.add(btn1)
            mark.add(btn2)
            mark.add(btn5)
            mark.add(btn3, btn4)


            photo1 = open("./start_mes.png", "rb")

            response_text = f"""
📋 Информация о подписке:

Срок подписки: 3 дня

🔗 Ссылка на подключение:
<code>{result['subscription_url']}</code>

Выберите действие: 
"""

            bot.send_photo(
                call.message.chat.id,
                caption=response_text,
                photo=photo1,
                parse_mode="HTML",
                reply_markup=mark
            )
            user_sub = result['subscription_url']
            start_date = datetime.now().isoformat()
            status_profil = "free"
            days = 3
            cur.execute("INSERT INTO users (user_id, user_sub, time_start, status_profil, days) VALUES ('%s', '%s', '%s', '%s', '%s')" % (user_id1, user_sub, start_date, status_profil, days))
            conn.commit()
            bot.send_message(chat_id=my_id,
                             text=f"Пользователь использовал кнопку АКТИВИРОВАТЬ и был занесён в базу (mesa_all.sql)\nID: <code>{user_id1}</code>\nSUB: <code>{user_sub}</code>",
                             parse_mode="HTML")
            conn = sqlite3.connect('message.sql')
            cur = conn.cursor()
            cur.execute(
                'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
            conn.commit()
            stats = "True"
            cur.execute("INSERT INTO users (user_id1, user_names1) VALUES (?, ?)", (user_id1, stats))
            conn.commit()
            conn = sqlite3.connect('itprogMES_free.sql')
            cur.execute(
                'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
            conn.commit()

        else:
            bot.send_message(
                call.message.chat.id,
                f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\nВведите /newvpn для активации",
                parse_mode="HTML"
            )

    else:
        bot.send_message(user_id, "У вас уже есть активная подписка")
    #     check = vpn_manager.get_user_hwid_by_telegram_id(user_id)
    #     if check:
    #         user_uuid = check.get("user_uuid")
    #         result = vpn_manager.extend_user_subscription(
    #             user_uuid=user_uuid,
    #             extra_days=3,
    #             hwid_limit=check['total_devices']
    #         )
    #         if result:
    #             dt = datetime.fromisoformat(result['new_expire'].replace('Z', '+00:00'))
    #             formatted = dt.strftime("%d/%m/%y")
    #             board = types.InlineKeyboardMarkup()
    #             board.add(types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe"))
    #             bot.send_message(
    #                 user_id,
    #                 f"✅ <b>Ваша подписка успешно продлена!</b>\n\n"
    #                 f"📅 Дата окончания подписки: {formatted}\n"
    #                 f"📆 Добавлено дней: 3\n",
    #                 reply_markup=board,
    #                 parse_mode="HTML"
    #             )
    #
    #             # ========== ИСПРАВЛЕНО: используем ? вместо %s ==========
    #             conn = sqlite3.connect('mesa_all.sql', timeout=10)
    #             cur = conn.cursor()
    #             cur.execute('''
    #                             CREATE TABLE IF NOT EXISTS users(
    #                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
    #                                 user_id TEXT UNIQUE,
    #                                 user_sub TEXT,
    #                                 time_start TEXT,
    #                                 status_profil TEXT,
    #                                 days TEXT
    #                             )
    #                         ''')
    #             conn.commit()
    #             cur.execute(f"SELECT status_profil FROM users WHERE user_id = {people_id}")
    #             data = cur.fetchone()
    #             start_date = datetime.now().strftime("%d/%m/%y")
    #             status_profil = data
    #             days = int(check['subscription_days']) + 3
    #
    #             # ===== ИСПРАВЛЕНО: используем ? вместо %s =====
    #             cur.execute(
    #                 "REPLACE INTO users (user_id, time_start, days) VALUES (?, ?, ?)",
    #                 (str(user_id), start_date, str(days))
    #             )
    #             conn.commit()
    #             cur.close()
    #             conn.close()

    cur.close()
    conn.close()

    time.sleep(3600)
    bot.send_message(call.message.chat.id,
                     "Всё получилось ❓\n\nЕсли хочешь - помогу с настройкой\n\n📞Поддержка - @MESA_VPN_support")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_plan") # Отмена плана
def cancel_plan_callback(call):
    """Отмена выбора плана"""
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ Выбор плана отменен"
    )

@bot.callback_query_handler(func=lambda call: call.data == "paying_69") # Оплата 69 рублей
def pay(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Я оплатил(-а)", callback_data="i`m_pay"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Ваш заказ будет принят на обработку в течении 5-10 минут после оплаты\n\n"
             "Реквизиты для оплаты\n\n"
             "🔒Т-банк\n"
             "<code>2200 7019 6828 2019</code>\n👆\n"
             "<tg-spoiler>Кликни на номер карты и она скопируется😋</tg-spoiler>",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "i`m_pay") # Конечная оплата 69 рублей
def I_pay(call):
    user_uuid = str(uuid.uuid4())
    conn = sqlite3.connect('itproger2.sql')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id1 VARCHAR(50) UNIQUE NOT NULL,
                user_names1 VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
    conn.commit()

    # 2. Получаем данные
    user_id1 = call.message.chat.id
    user_names1 = user_uuid  # Предполагаем, что user_uuid определен выше
    people_id = call.message.chat.id

    # 3. Проверяем, существует ли пользователь (БЕЗОПАСНО)
    cur.execute("SELECT user_id1 FROM users WHERE user_id1 = ?", (people_id,))
    data = cur.fetchone()

    if data is None:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔎Ваш заказ успешно создан\n\n"
                 "Как только мы проверим платёж - бот отправит вам индивидуальную ссылку на подключение\n\n"
                 "Реквизиты для оплаты\n\n"
                 "🔒Т-банк\n"
                 "<code>2200 7019 6828 2019</code>\n👆\n"
                 "Сумма платежа: 69 рублей\n"
                 f"📋Код заказа: <code>{user_uuid}</code>",
            parse_mode="HTML"
        )
        cur.execute("INSERT OR IGNORE INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id1, user_names1))
        conn.commit()
        cur.execute('SELECT * FROM users')
        conn.commit()
        users = cur.fetchall()
        infoALL = ''
        infoSOLO = ''

        for el in users:
            infoALL += (f"🔑ID: <code>{el[1]}</code> \n"
                        f"Сумма заказа: 69р.\n"
                        f"Номер заказа: <code>{el[2]}</code>\n\n"
                        )
            infoSOLO = (f"🔑ID: <code>{el[1]}</code> \n"
                        f"Сумма заказа: 69р.\n"
                        f"Номер заказа: <code>{el[2]}</code>\n\n"
                        )
        bot.send_message(chat_id=my_id, text=f"Список заказов: \n\n{infoALL}", parse_mode="HTML")
        bot.send_message(chat_id=my_id, text=f"Новый заказ: \n\n{infoSOLO}", parse_mode="HTML",
                         reply_markup=payment_check_keyboard(user_id1))
        cur.close()
        conn.close()
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы уже оформляли заказ, ожидайте ответа от команды.\n\nПоддержка - @MESA_VPN_support"
        )

@bot.callback_query_handler(func=lambda call: call.data == "continue_sub") # Конечная оплата 69 рублей (продление)
def I_payPRO(call):
    user_uuid = str(uuid.uuid4())
    conn = sqlite3.connect('itproger2.sql')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id1 VARCHAR(50) UNIQUE NOT NULL,
                user_names1 VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
    conn.commit()

    # 2. Получаем данные
    user_id1 = call.message.chat.id
    user_names1 = user_uuid  # Предполагаем, что user_uuid определен выше
    people_id = call.message.chat.id

    # 3. Проверяем, существует ли пользователь (БЕЗОПАСНО)
    cur.execute("SELECT user_id1 FROM users WHERE user_id1 = ?", (people_id,))
    data = cur.fetchone()

    if data is None:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔎Ваш заказ успешно создан\n\n"
                 "Как только мы проверим платёж - бот отправит вам сообщение об результате оплаты\n\n"
                 "Реквизиты для оплаты\n\n"
                 "🔒Т-банк\n"
                 "<code>2200 7019 6828 2019</code>\n👆\n"
                 "Сумма платежа: 69 рублей\n"
                 f"📋Код заказа: <code>{user_uuid}</code>",
            parse_mode="HTML"
        )
        cur.execute("INSERT INTO users (user_id1, user_names1) VALUES ('%s', '%s')" % (user_id1, user_names1))
        conn.commit()
        cur.execute('SELECT * FROM users')
        conn.commit()
        users = cur.fetchall()
        infoALL = ''
        infoSOLO = ''

        for el in users:
            infoALL += (f"🔑ID: <code>{el[1]}</code> \n"
                        f"Сумма заказа: 69р.\n"
                        f"Номер заказа: <code>{el[2]}</code>\n\n"
                        )
            infoSOLO = (f"🔑ID: <code>{el[1]}</code> \n"
                        f"Сумма заказа: 69р.\n"
                        f"Номер заказа: <code>{el[2]}</code>\n\n"
                        )
        bot.send_message(chat_id=my_id, text=f"Список заказов на продление подписки: \n\n{infoALL}", parse_mode="HTML")
        bot.send_message(chat_id=my_id, text=f"Новый заказ на продление подписки: \n\n{infoSOLO}", parse_mode="HTML",
                         reply_markup=payment_check_keyboardPRO(user_id1))
        cur.close()
        conn.close()
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы уже оформляли заказ, ожидайте ответа от команды.\n\nПоддержка - @MESA_VPN_support"
        )

def payment_check_keyboard(user_id1):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton(
        text="✅ Платёж проверен",
        callback_data=f"success:{user_id1}"
    )

    btn2 = types.InlineKeyboardButton(
        text="❌ Платёж не удался",
        callback_data=f"failed:{user_id1}"
    )

    markup.add(btn1, btn2)
    return markup

def payment_check_keyboardPRO(user_id1):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton(
        text="✅ Платёж проверен",
        callback_data=f"success_con:{user_id1}"
    )

    btn2 = types.InlineKeyboardButton(
        text="❌ Платёж не удался",
        callback_data=f"failed_con:{user_id1}"
    )

    markup.add(btn1, btn2)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("success:")) # Подтверждение оплаты от пользователя
def success_payment(call):
    try:
        # 1. Парсим callback
        _, user_id = call.data.split(":")
        user_id = int(user_id)

        is_subscribed = ChannelChecker.check_subscription(user_id)

        if not is_subscribed:
            # Пользователь НЕ подписан - просим подписаться
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ НА КАНАЛ", url=CHANNEL_URL))
            keyboard.add(
                types.InlineKeyboardButton(text="✅ ПРОВЕРИТЬ ПОДПИСКУ", callback_data="check_channel_subscription"))

            bot.send_message(
                call.message.chat.id,
                f"🔒 <b>Требуется подписка на канал!</b>\n\n"
                f"<b>Как получить доступ:</b>\n"
                f"1️⃣ Нажмите <b>«Подписаться на канал»</b>\n"
                f"2️⃣ Подпишитесь на <a href='https://t.me/MenlikProxyVPN'>наш канал</a>\n"
                f"3️⃣ Вернитесь в бот и нажмите <b>«Проверить подписку»</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
        conn = sqlite3.connect('mesa_all.sql')
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
        conn.commit()
        cur.execute(f"SELECT user_id FROM users WHERE user_id = {user_id}")
        data = cur.fetchone()
        photo = open("./sub_mes.png", "rb")

        if data is None:
            bot.send_message(
                chat_id=user_id,
                text="⏳ Создаю подписку..."
            )
            cur.execute(f"SELECT time_start FROM users WHERE user_id = {user_id}")
            result = vpn_manager.create_user_and_get_link(
                username=f"user_{user_id}",
                expire_days=3,
                data_limit_gb=0,
                add_to_all_squads=True,
                verbose=True,
                tg_id=user_id
            )
            if result:
                HAPP_URL = f"{result['subscription_url']}"
                mark = types.InlineKeyboardMarkup()
                btn1 = types.InlineKeyboardButton(text="🔎 Сгенерировать QR-код", callback_data="QR_codee")
                btn2 = types.InlineKeyboardButton(text="🔑 Подключить в Happ", url=HAPP_URL)
                btn5 = types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe")
                btn3 = types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)
                btn4 = types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil")
                mark.add(btn1)
                mark.add(btn2)
                mark.add(btn5)
                mark.add(btn3, btn4)

                photo1 = open("./start_mes.png", "rb")

                response_text = f"""
        📋 Информация о подписке:

        Срок подписки: 3 дня

        🔗 Ссылка на подключение:
        <code>{result['subscription_url']}</code>

        Выберите действие: 
        """

                bot.send_photo(
                    call.message.chat.id,
                    caption=response_text,
                    photo=photo1,
                    parse_mode="HTML",
                    reply_markup=mark
                )
                user_sub = result['subscription_url']
                start_date = datetime.now().isoformat()
                status_profil = "free"
                days = 3
                cur.execute(
                    "INSERT INTO users (user_id, user_sub, time_start, status_profil, days) VALUES ('%s', '%s', '%s', '%s', '%s')" % (
                    user_id, user_sub, start_date, status_profil, days))
                conn.commit()
                bot.send_message(chat_id=my_id,
                                 text=f"Пользователь получил ПРЕМИУМ и был занесён в базу (mesa_all.sql)\nID: <code>{user_id}</code>\nSUB: <code>{user_sub}</code>",
                                 parse_mode="HTML")
                conn = sqlite3.connect('message.sql')
                cur = conn.cursor()
                cur.execute(
                    'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
                conn.commit()
                stats = "True"
                cur.execute("INSERT INTO users (user_id1, user_names1) VALUES (?, ?)", (user_id, stats))
                conn.commit()
                conn = sqlite3.connect('itprogMES_free.sql')
                cur.execute(
                    'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
                conn.commit()

            else:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\nВведите /newvpn для активации",
                    parse_mode="HTML"
                )

        else:
            markup = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton(text="⚙️ Главное меню", callback_data="alpha")
            markup.add(btn1)
            bot.send_message(call.message.chat.id,
                             "У вас уже есть активная подписка.\n",
                             reply_markup=markup
                             )

        cur.close()
        conn.close()

        time.sleep(3600)
        bot.send_message(call.message.chat.id,
                         "Всё получилось ❓\n\nЕсли хочешь - помогу с настройкой\n\n📞Поддержка - @MESA_VPN_support")
    except:
        print("---")

@bot.callback_query_handler(func=lambda call: call.data.startswith("success_con:")) # Подтверждение оплаты от пользователя (продление)
def success_paymentPRO(call):
    try:
        # 1. Парсим callback
        mark = types.InlineKeyboardMarkup()
        mark.add(types.InlineKeyboardButton(text="🔁 Повторить попытку", callback_data="continue_sub"))
        _, user_id = call.data.split(":")
        user_id = int(user_id)

        bot.delete_message(call.message.chat.id, call.message.id)
        conn = sqlite3.connect('itproger4.sql')
        cur = conn.cursor()
        cur.execute(f"SELECT user_names1 FROM users WHERE user_id1 = {user_id}")
        conn.commit()
        users = cur.fetchall()
        user_uuid = str(users).replace("'", "").replace(")", "").replace("(", "").replace('"', '').replace(",", "").replace("[", "").replace("]", "")
        try:
            email = f"PRO_{user_id}"
            s1 = vpn_manager.renew_expired_subscription(user_uuid)
            s3 = vpn_manager.renew_expired_subscription_marzban(user_uuid, user_id, email)
            if s1 or s3:
                subscription_manager.continue_subscription(user_id)
                bot.send_message(user_id, f"Ваша подписка успешно продлена на 30 дней.\n\n"
                                        f"Поддержка - @MESA_VPN_support")
                bot.send_message(my_id,
                                 f"Подписка ВКЛЮЧЕНА для пользователя \nID: <code>{user_id}</code>\nUUID: <code>{user_uuid}</code>",
                                 parse_mode="HTML")

                conn = sqlite3.connect('itproger2.sql')
                cur = conn.cursor()
                cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                cur.fetchone()
                conn.commit()
                conn = sqlite3.connect('messagePRO.sql')
                cur = conn.cursor()
                cur.execute(
                    'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
                conn.commit()
                stats = "True"
                cur.execute("INSERT INTO users (user_id1, user_names1) VALUES (?, ?)", (user_id, stats))
                conn.commit()
                conn = sqlite3.connect('itprogMES_pro.sql')
                cur.execute(
                    'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
                conn.commit()
                cur.close()
                conn.close()
            else:
                s3 = vpn_manager.renew_expired_subscription_marzban(user_uuid, user_id, email)
                if s3:
                    subscription_manager.continue_subscription(user_id)
                    bot.send_message(user_id, f"Ваша подписка успешно продлена на 30 дней.\n\n"
                                              f"Поддержка - @MESA_VPN_support")
                    bot.send_message(my_id,
                                     f"Подписка ВКЛЮЧЕНА для пользователя \nID: <code>{user_id}</code>\nUUID: <code>{user_uuid}</code>",
                                     parse_mode="HTML")

                    conn = sqlite3.connect('itproger2.sql')
                    cur = conn.cursor()
                    cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                    cur.fetchone()
                    conn.commit()

                    conn = sqlite3.connect('message.sql')
                    cur = conn.cursor()
                    cur.execute(
                        'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id1 varchar(50), user_names1 varchar(50))')
                    conn.commit()
                    stats = "True"
                    cur.execute("INSERT INTO users (user_id1, user_names1) VALUES (?, ?)", (user_id, stats))
                    conn.commit()
                    cur.close()
                    conn.close()
                else:
                    bot.send_message(user_id, "Не удалось продлить подписку. Администратор уведомлён", reply_markup=mark)
                    bot.send_message(my_id, f"Не удалось продлить подписку для пользователя <code>{user_id}</code>", parse_mode="HTML")
                    conn = sqlite3.connect('itproger2.sql')
                    cur = conn.cursor()
                    cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
                    cur.fetchone()
                    conn.commit()
                    cur.close()
                    conn.close()

        except:
            bot.send_message(my_id, f"Не удалось ВКЛЮЧИТЬ подписку для пользователя <code>{user_id}</code>", parse_mode="HTML")
    except:
        _, user_id = call.data.split(":")
        user_id = int(user_id)
        bot.send_message(my_id, f"Не удалось ВКЛЮЧИТЬ подписку для этого пользователя <code>{user_id}</code>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("failed:")) # Отклонение оплаты от пользователя
def fail(call):
    _, user_id = call.data.split(":")
    user_id = int(user_id)
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.send_message(chat_id=my_id,
                     text="Успешно!\nСсылка не будет отправлена"
                     )
    mark = types.InlineKeyboardMarkup()
    mark.add(types.InlineKeyboardButton(text="🔁 Повторить попытку", callback_data="activate_premium_now"))
    conn = sqlite3.connect('itproger2.sql')
    cur = conn.cursor()
    cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
    bot.send_message(chat_id=user_id,
                     text="❌ Ваш платеж не удался.\nВы снова можете создавать заказы\n\nПоддержка - @MESA_VPN_support",
                     reply_markup=mark)

    cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("failed_con:")) # Отклонение оплаты от пользователя (продление)
def failPRO(call):
    _, user_id = call.data.split(":")
    user_id = int(user_id)
    bot.delete_message(call.message.chat.id, call.message.id)
    mark = types.InlineKeyboardMarkup()
    mark.add(types.InlineKeyboardButton(text="🔁 Повторить попытку", callback_data="continue_sub"))
    bot.send_message(chat_id=my_id,
                     text="Успешно!\nСсылка не будет отправлена"
                     )
    conn = sqlite3.connect('itproger2.sql')
    cur = conn.cursor()
    cur.execute(f"DELETE FROM users WHERE user_id1 = {user_id}")
    bot.send_message(chat_id=user_id,
                     text="❌ Ваш платеж не удался.\nВы снова можете создавать заказы\n\nПоддержка - @MESA_VPN_support",
                     reply_markup=mark)

    cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call : call.data == "QR_codee") # Генерация бесплатных QR-кодов
def QR_cod(call):
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    people_id = call.message.chat.id
    cur.execute("SELECT user_sub FROM users WHERE user_id = ?", (people_id,))
    data = cur.fetchone()
    user_uuid = str(data).replace("'", "").replace(")", "").replace("(", "").replace('"', '').replace(",",
                                                                                                       "").replace(
        "[", "").replace("]", "")
    qr_url = vpn_manager.generate_qr_code_url(str(user_uuid))
    print(user_uuid)
    if qr_url:
        # Отправляем QR-код
        bot.send_photo(
            call.message.chat.id,
            photo=qr_url,
            caption="📱 QR-код для подключения"
        )
        conn.commit()
    else:
        bot.send_message(people_id, "Не удалось сгенерировать QR-код")
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call : call.data == "QR_codee2") # Генерация платных QR-кодов
def QR_cod2(call):
    conn = sqlite3.connect('mesa_all.sql')
    cur = conn.cursor()
    people_id = call.message.chat.id
    user_stats = "pro"
    cur.execute("SELECT user_sub FROM users WHERE user_id = ? AND status_profil = ?", (people_id, user_stats))
    data = cur.fetchone()
    user_uuid = str(data).replace("'", "").replace(")", "").replace("(", "").replace('"', '').replace(",",
                                                                                                      "").replace(
        "[", "").replace("]", "")
    qr_url = vpn_manager.generate_qr_code_url(str(user_uuid))
    print(user_uuid)
    if qr_url:
        # Отправляем QR-код
        bot.send_photo(
            call.message.chat.id,
            photo=qr_url,
            caption="📱 QR-код для подключения"
        )
        conn.commit()
    else:
        bot.send_message(people_id, "Не удалось сгенерировать QR-код")
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call : call.data == "reset_stat") # Сброс статуса получения подписки
def reset_stats(call):
    us_id = call.message.chat.id
    for id1 in ADMIN_IDS:
        if id1 == us_id:
            bot.delete_message(call.message.chat.id, call.message.id)
            conn = sqlite3.connect('itproger1.sql')
            cur = conn.cursor()
            cur.execute(
                f"DELETE FROM users WHERE user_id1 = {us_id}"
            )
            cur.fetchone()
            conn.commit()

            bot.send_message(
                call.message.chat.id,
                "🔑 Статус успешно обнулён, используйте /newvpn для создания нового VPN"
            )
        else:
            bot.delete_message(call.message.chat.id, call.message.id)
            bot.send_message(call.message.chat.id,
                "❌ Нет прав"
            )

def QR_code(text):
    qr_url = vpn_manager.generate_qr_code_url(str(text))
    if qr_url:
        return qr_url

@bot.callback_query_handler(func=lambda call: call.data.startswith("f:"))
def success_payment(call):
    try:
        # 1. Парсим callback
        res = call.data.replace("f:", "")
        res = res.split(":")

        user_id = int(res[0])
        hwids = int(res[1])
        money = int(res[2])
        times = int(res[3])

        print(f"Аргумент 1: {user_id}")
        print(f"Аргумент 2: {hwids}")
        print(f"Аргумент 3: {money}")
        print(f"Аргумент 4: {times}")
        conn = sqlite3.connect('mesa_all.sql', timeout=10)
        cur = conn.cursor()

        cur.execute(
            'CREATE TABLE IF NOT EXISTS tickets('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'user_id TEXT, user_sub TEXT, time_start TEXT, '
            'status_profil TEXT, days TEXT)'
        )
        cur.execute(f"SELECT user_id FROM tickets WHERE user_id = {user_id}")
        data = cur.fetchone()
        if data is None:
            photo1 = open("./start_mes.png", "rb")

            response_text = f"""
📄 Ваш заказ успешно создан

Тариф: ⚡️ Быстрый старт
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Реквизиты для оплаты:

Номер карты: <code>2200 7019 6828 2019</code>
Банк: Т-Банк
"""

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=response_text,
                parse_mode="HTML"
            )

            # 2. Работа с БД (ПРАВИЛЬНЫЙ ПОРЯДОК)
            status_profil = "fast_start"
            user_sub = "Нет"
            start_date = datetime.now().isoformat()
            cur.execute(
                "INSERT INTO tickets (user_id, user_sub, time_start, status_profil, days) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), user_sub, start_date, status_profil, str(times))
            )
            conn.commit()
            # ✅ ПРАВИЛЬНЫЙ ПОРЯДОК: сначала cursor, потом connection
            cur.close()
            conn.close()

            # 3. Отправляем админу
            text = f"""
📄 Новый заказ

ID: <code>{user_id}</code>
Тариф: ⚡️ Быстрый старт
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Выберите действие:
"""
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(
                    text="✅ Успешно",
                    callback_data=f"y:{user_id}:{hwids}:{money}:{times}:f"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"n:{user_id}:{hwids}:{money}:{times}:f"
                )
            )

            bot.send_photo(
                my_id,
                photo=photo1,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            photo1.close()
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))
            bot.edit_message_caption(
                chat_id=user_id,
                message_id=call.message.message_id,
                caption="Вы уже <b>оформляли</b> заказ. \nОжидайте ответа от команды",
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(my_id, f"❌ Ошибка при создании заказа: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("s:"))
def success_payment(call):
    try:
        # 1. Парсим callback
        res = call.data.replace("s:", "")
        res = res.split(":")

        user_id = int(res[0])
        hwids = int(res[1])
        money = int(res[2])
        times = int(res[3])

        print(f"Аргумент 1: {user_id}")
        print(f"Аргумент 2: {hwids}")
        print(f"Аргумент 3: {money}")
        print(f"Аргумент 4: {times}")
        conn = sqlite3.connect('mesa_all.sql', timeout=10)
        cur = conn.cursor()

        cur.execute(
            'CREATE TABLE IF NOT EXISTS tickets('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'user_id TEXT, user_sub TEXT, time_start TEXT, '
            'status_profil TEXT, days TEXT)'
        )
        cur.execute(f"SELECT user_id FROM tickets WHERE user_id = {user_id}")
        data = cur.fetchone()
        if data is None:
            photo1 = open("./start_mes.png", "rb")

            response_text = f"""
📄 Ваш заказ успешно создан

Тариф: 💥 Стандарт
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Реквизиты для оплаты:

Номер карты: <code>2200 7019 6828 2019</code>
Банк: Т-Банк
"""

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=response_text,
                parse_mode="HTML"
            )

            # 2. Работа с БД (ПРАВИЛЬНЫЙ ПОРЯДОК)
            status_profil = "standart"
            user_sub = "Нет"
            start_date = datetime.now().isoformat()
            cur.execute(
                "INSERT INTO tickets (user_id, user_sub, time_start, status_profil, days) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), user_sub, start_date, status_profil, str(times))
            )
            conn.commit()
            # ✅ ПРАВИЛЬНЫЙ ПОРЯДОК: сначала cursor, потом connection
            cur.close()
            conn.close()

            # 3. Отправляем админу
            text = f"""
📄 Новый заказ

ID: <code>{user_id}</code>
Тариф: 💥 Стандарт
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Выберите действие:
"""
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(
                    text="✅ Успешно",
                    callback_data=f"y:{user_id}:{hwids}:{money}:{times}:s"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"n:{user_id}:{hwids}:{money}:{times}:s"
                )
            )

            bot.send_photo(
                my_id,
                photo=photo1,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            photo1.close()
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))
            bot.edit_message_caption(
                chat_id=user_id,
                message_id=call.message.message_id,
                caption="Вы уже <b>оформляли</b> заказ. \nОжидайте ответа от команды",
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(my_id, f"❌ Ошибка при создании заказа: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("p:"))
def success_payment(call):
    try:
        # 1. Парсим callback
        res = call.data.replace("p:", "")
        res = res.split(":")

        user_id = int(res[0])
        hwids = int(res[1])
        money = int(res[2])
        times = int(res[3])

        print(f"Аргумент 1: {user_id}")
        print(f"Аргумент 2: {hwids}")
        print(f"Аргумент 3: {money}")
        print(f"Аргумент 4: {times}")
        conn = sqlite3.connect('mesa_all.sql', timeout=10)
        cur = conn.cursor()

        cur.execute(
            'CREATE TABLE IF NOT EXISTS tickets('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'user_id TEXT, user_sub TEXT, time_start TEXT, '
            'status_profil TEXT, days TEXT)'
        )
        cur.execute(f"SELECT user_id FROM tickets WHERE user_id = {user_id}")
        data = cur.fetchone()
        if data is None:
            photo1 = open("./start_mes.png", "rb")

            response_text = f"""
📄 Ваш заказ успешно создан

Тариф: 💎 Премиум
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Реквизиты для оплаты:

Номер карты: <code>2200 7019 6828 2019</code>
Банк: Т-Банк
"""

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=response_text,
                parse_mode="HTML"
            )

            # 2. Работа с БД (ПРАВИЛЬНЫЙ ПОРЯДОК)
            status_profil = "premium"
            user_sub = "Нет"
            start_date = datetime.now().isoformat()
            cur.execute(
                "INSERT INTO tickets (user_id, user_sub, time_start, status_profil, days) VALUES (?, ?, ?, ?, ?)",
                (str(user_id), user_sub, start_date, status_profil, str(times))
            )
            conn.commit()
            # ✅ ПРАВИЛЬНЫЙ ПОРЯДОК: сначала cursor, потом connection
            cur.close()
            conn.close()

            # 3. Отправляем админу
            text = f"""
📄 Новый заказ

ID: <code>{user_id}</code>
Тариф: 💎 Премиум
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Выберите действие:
"""
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(
                    text="✅ Успешно",
                    callback_data=f"y:{user_id}:{hwids}:{money}:{times}:p"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"n:{user_id}:{hwids}:{money}:{times}:p"
                )
            )

            bot.send_photo(
                my_id,
                photo=photo1,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            photo1.close()
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="tarifes"))
            bot.edit_message_caption(
                chat_id=user_id,
                message_id=call.message.message_id,
                caption="Вы уже <b>оформляли</b> заказ. \nОжидайте ответа от команды",
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(my_id, f"❌ Ошибка при создании заказа: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("m:"))
def success_payment(call):
    try:
        # 1. Парсим callback
        res = call.data.replace("m:", "")
        res = res.split(":")

        user_id = int(res[0])
        hwids = int(res[1])
        money = int(res[2])
        times = int(res[3])

        print(f"Аргумент 1: {user_id}")
        print(f"Аргумент 2: {hwids}")
        print(f"Аргумент 3: {money}")
        print(f"Аргумент 4: {times}")

        photo1 = open("./start_mes.png", "rb")

        response_text = f"""
📄 Ваш заказ успешно создан

Тариф: 📈 Максимум
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Реквизиты для оплаты:

Номер карты: <code>2200 7019 6828 2019</code>
Банк: Т-Банк
"""

        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=response_text,
            parse_mode="HTML"
        )

        # 2. Работа с БД (ПРАВИЛЬНЫЙ ПОРЯДОК)
        conn = sqlite3.connect('mesa_all.sql', timeout=10)
        cur = conn.cursor()

        cur.execute(
            'CREATE TABLE IF NOT EXISTS tickets('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'user_id TEXT, user_sub TEXT, time_start TEXT, '
            'status_profil TEXT, days TEXT)'
        )

        status_profil = "maximum"
        user_sub = "Нет"
        start_date = datetime.now().isoformat()

        cur.execute(
            "INSERT INTO tickets (user_id, user_sub, time_start, status_profil, days) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), user_sub, start_date, status_profil, str(times))
        )
        conn.commit()

        # ✅ ПРАВИЛЬНЫЙ ПОРЯДОК: сначала cursor, потом connection
        cur.close()
        conn.close()

        # 3. Отправляем админу
        text = f"""
📄 Новый заказ

ID: <code>{user_id}</code>
Тариф: 📈 Максимум
Срок оплаты: 15 минут
Цена заказа: {money} ₽

Выберите действие:
"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(
                text="✅ Успешно",
                callback_data=f"y:{user_id}:{hwids}:{money}:{times}:m"
            ),
            types.InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"n:{user_id}:{hwids}:{money}:{times}:m"
            )
        )

        bot.send_photo(
            my_id,
            photo=photo1,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        photo1.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(my_id, f"❌ Ошибка при создании заказа: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("y:"))
def success_payment(call):
    try:
        # 1. Сразу отвечаем на callback, чтобы Telegram не ждал
        bot.answer_callback_query(call.id, "⏳ Обрабатываю оплату...")

        # 2. Парсим callback
        res = call.data.replace("y:", "").split(":")

        user_id = int(res[0])
        hwids = int(res[1])
        money = int(res[2])
        times = int(res[3])
        tarif_code = res[4] if len(res) > 4 else "s"

        # 3. Определяем тариф
        tarif_map = {
            "f": "fast_start",
            "s": "standart",
            "p": "premium",
            "m": "maximum"
        }
        tarif = tarif_map.get(tarif_code, "standart")

        print(f"✅ Оплата подтверждена: user={user_id}, tarif={tarif}, hwids={hwids}, money={money}, days={times * 30}")

        # 4. Проверяем существование пользователя в БД
        try:
            conn = sqlite3.connect('mesa_all.sql', timeout=10)
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE user_id = ?", (str(user_id),))
            data = cur.fetchone()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка БД: {e}")
            data = None

        # 5. Если пользователь существует — продлеваем
        if data is not None:
            check = vpn_manager.get_user_hwid_by_telegram_id(user_id)
            if check:
                user_uuid = check.get("user_uuid")
                result = vpn_manager.extend_user_subscription(
                    user_uuid=user_uuid,
                    extra_days=times * 30,
                    hwid_limit=hwids
                )
                if result:
                    dt = datetime.fromisoformat(result['new_expire'].replace('Z', '+00:00'))
                    formatted = dt.strftime("%d/%m/%y")
                    board = types.InlineKeyboardMarkup()
                    board.add(types.InlineKeyboardButton(text="⚙️ Управление подпиской", callback_data="subscribe"))
                    bot.send_message(
                        user_id,
                        f"✅ <b>Ваша подписка успешно продлена!</b>\n\n"
                        f"📅 Дата окончания подписки: {formatted}\n"
                        f"📆 Добавлено дней: {times * 30}\n"
                        f"📱 Лимит устройств: {hwids}",
                        reply_markup=board,
                        parse_mode="HTML"
                    )

                    # ========== ИСПРАВЛЕНО: используем ? вместо %s ==========
                    conn = sqlite3.connect('mesa_all.sql', timeout=10)
                    cur = conn.cursor()
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS users(
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            user_id TEXT UNIQUE, 
                            user_sub TEXT, 
                            time_start TEXT, 
                            status_profil TEXT, 
                            days TEXT
                        )
                    ''')
                    conn.commit()

                    res = vpn_manager.get_user_hwid_by_telegram_id(user_id)
                    if res:
                        # ===== ИСПРАВЛЕНО: используем ? вместо %s =====
                        start_date = datetime.now().isoformat()
                        status_profil = tarif
                        days = res['subscription_days']
                        cur.execute(
                            "UPDATE users SET time_start = ?, status_profil = ?, days = ? WHERE user_id = ?",
                            (start_date, status_profil, str(days), str(user_id))
                        )
                        conn.commit()
                        cur.close()
                        conn.close()

                    # Удаляем заказ из tickets
                    try:
                        conn = sqlite3.connect('mesa_all.sql', timeout=10)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM tickets WHERE user_id = ?", (str(user_id),))
                        conn.commit()
                        cur.close()
                        conn.close()
                    except Exception as e:
                        try:
                            conn = sqlite3.connect('mesa_all.sql', timeout=10)
                            cur = conn.cursor()
                            cur.execute("DELETE FROM tickets WHERE user_id = ?", (str(user_id),))
                            conn.commit()
                            cur.close()
                            conn.close()
                        except:
                            print(f"⚠️ Ошибка удаления из tickets: {e}")

                    bot.send_message(my_id, f"✅ Подписка продлена до {formatted}\n👤 ID: {user_id}")
                    bot.answer_callback_query(call.id, "✅ Подписка продлена!")
                    return
                else:
                    bot.send_message(user_id, "❌ Не удалось продлить подписку. Обратитесь в поддержку.")
                    bot.answer_callback_query(call.id, "❌ Ошибка продления")
                    return

        # 6. Если пользователь новый — создаём
        result = vpn_manager.create_user_and_get_link(
            username=f"user_{user_id}",
            tg_id=user_id,
            expire_days=times * 30,
            plan_type=tarif,
            data_limit_gb=0,
            hwid_limit=hwids
        )

        dt = datetime.fromisoformat(result['expire_at'].replace('Z', '+00:00'))
        formatted = dt.strftime("%d/%m/%y")
        bot.send_message(
            user_id,
            f"✅ <b>Ваша подписка активирована!</b>\n\n"
            f"📅 Дата окончания: {formatted}\n"
            f"📆 Добавлено дней: {times * 30}\n"
            f"📱 Лимит устройств: {hwids}\n\n"
            f"🔗 Ссылка для подключения:\n<code>{result['subscription_url']}</code>",
            parse_mode="HTML"
        )

        # ========== ИСПРАВЛЕНО: используем ? вместо %s ==========
        conn = sqlite3.connect('mesa_all.sql', timeout=10)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id TEXT UNIQUE, 
                user_sub TEXT, 
                time_start TEXT, 
                status_profil TEXT, 
                days TEXT
            )
        ''')
        conn.commit()

        start_date = datetime.now().isoformat()
        status_profil = tarif
        days = times * 30
        user_sub = result['subscription_url']

        # ===== ИСПРАВЛЕНО: используем ? вместо %s =====
        cur.execute(
            "INSERT INTO users (user_id, user_sub, time_start, status_profil, days) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), user_sub, start_date, status_profil, str(days))
        )
        conn.commit()
        cur.close()
        conn.close()

        # Удаляем заказ из tickets
        try:
            conn = sqlite3.connect('mesa_all.sql', timeout=10)
            cur = conn.cursor()
            cur.execute("DELETE FROM tickets WHERE user_id = ?", (str(user_id),))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка удаления из tickets: {e}")

        bot.send_message(my_id, f"✅ Новая подписка создана до {formatted}\n👤 ID: {user_id}")
        bot.answer_callback_query(call.id, "✅ Подписка активирована!")

    except Exception as e:
        print(f"❌ Ошибка в success_payment: {e}")
        try:
            bot.send_message(my_id, f"❌ Ошибка при обработке оплаты: {e}")
            bot.answer_callback_query(call.id, "⚠️ Ошибка обработки")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("n:")) # Отклонение оплаты от пользователя
def success_payment(call):
     # 1. Парсим callback
     res = call.data.replace("n:", "")
     res = res.split(":")

     # Или если нужно присвоить переменным
     user_id = int(res[0])
     hwids = int(res[1])  # 10
     money = int(res[2])  # 200
     times = int(res[3])  # 15

     # Выводим по аргументам
     print(f"Аргумент 1: {user_id}")  # 10
     print(f"Аргумент 2: {hwids}")  # 10
     print(f"Аргумент 3: {money}")  # 200
     print(f"Аргумент 4: {times}")  # 15

     conn = sqlite3.connect('tickets.sql')
     cur = conn.cursor()
     cur.execute(
         'CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, user_id varchar(50), user_sub varchar(50), time_start varchar(50), status_profil varchar(50), days varchar(50))')
     mark = types.InlineKeyboardMarkup()
     mark.add(types.InlineKeyboardButton(text="Главное меню", callback_data="alpha"))
     mark.add(types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL))
     cur.execute(f"DELETE FROM users WHERE user_id = {user_id}")
     conn.commit()
     cur.close()
     conn.close()
     bot.edit_message_caption(chat_id=my_id, message_id=call.message.message_id, caption="Оплата отклонена. Подписка не будет отправлена")
     with open("./start_mes.png", "rb") as photo:
         bot.send_photo(
             chat_id=user_id,
             photo=photo,
             caption="🚫 Ваш заказ был отклонён модератором.\n\n"
                     "<b>Комментарий:</b>\n"
                     "<blockquote>Оплата не прошла, просьба повторить заказ или написать в поддержку</blockquote>\n\n"
                     "С уважением, команда MESA.",
             reply_markup=mark,
             parse_mode="HTML"
         )

#============= КОМАНДЫ ДЛЯ АДМИНОВ ==============
@bot.message_handler(commands=['admin_com']) # Команды админа
def admin_com(message):
    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    bot.send_message(chat_id=my_id, text="Команды для админов:\n\n"
                                              "/admin_com - команды для админов\n"
                                              "/admin_stats - просмотр статистики\n"
                                              "/admin_delete - удаление пользователя по UUID\n"
                                              "/admin_add - добавление пользователя по ID в 3X-UI панель и подписки\n"
                                              "/admin_send - можно написать любому пользователю сообщение\n"
                                              "/admin_send_ALL - отправка сообщения всем пользователям"
    )

@bot.message_handler(commands=['admin_stats']) # Статистика бота
def admin_stats_command(message):
    """Статистика для админа"""
    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return

    # Статистика подписок
    active = sum(1 for s in active_subscriptions.values() if s['status'] == 'active')
    pending = sum(1 for s in active_subscriptions.values() if s['status'] == 'pending')
    expired = sum(1 for s in active_subscriptions.values() if s['status'] == 'expired')

    # Распределение по планам
    plan_stats = {}
    for sub in active_subscriptions.values():
        plan = sub['plan_id']
        plan_stats[plan] = plan_stats.get(plan, 0) + 1

    plan_text = ""
    for plan_id, count in plan_stats.items():
        plan_name = subscription_manager.plans.get(plan_id, {}).get('name', plan_id)
        plan_text += f"• {plan_name}: {count}\n"

    try:
        conn = sqlite3.connect('otziv.sql')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        mes = ''
        #for el in users:
            #mes += (f"⭐️ Отзыв: {str(el[2])}\n"
                    #f"🔑 ID: <code>{int(el[1])}</code>\n\n")
        for i, r in enumerate(users, 1):
            #print(f"{i}. {r['title']}")
            mes += (f"{i}. Отзыв: {str(r[2])}\n"
                    f"🔑 ID: <code>{int(r[1])}</code>\n")
    except:
        mes = "🚫 Отсутствуют"
    stats_text = f"""
📊 Статистика подписок:

👥 Всего подписок: {len(active_subscriptions)}
✅ Активных: {active}
⏱ Ожидающих: {pending}
❌ Истекших: {expired}
👤 ПОДПИСОК В ЭТОЙ СЕССИИ: {len(users_db)}

📈 По планам:
{plan_text}
📄 Список всех отзывов:

{mes}
        """
    bot.send_message(message.chat.id, stats_text, parse_mode="HTML")

@bot.message_handler(commands=['admin_delete']) # Удаление подписки пользователя
def delete_admin_uuid(message):
    user_id = message.chat.id

    if user_id not in ADMIN_IDS:
        safe_send(user_id, "❌ Нет прав")
        return

    args = message.text.split()

    if len(args) < 2:
        safe_send(message.chat.id, "❌ Укажите UUID после команды:\n/admin_delete UUID")
        return

    user_uuid = args[1]

    safe_send(my_id, f"🔍 Начинаю удаление пользователя {user_uuid}...")

    # Marzban
    try:
        a = vpn_manager.delete_user_by_telegram_id(user_uuid)
        if a:
            bot.send_message(my_id, "✅ Пользователь успешно удалён из REMNAWAVE")
    except:
        bot.send_message(my_id, "Ошибка удаления пользователя из REMNAWAVE")
# @bot.message_handler(commands=['admin_delete_id'])
# def delete_admin_id(message):
#     user_id = message.from_user.id
#
#     if user_id not in ADMIN_IDS:
#         bot.send_message(message.chat.id, "❌ Нет прав")
#         return
#     # Простейший вариант
#     args = message.text.split()
#
#     if len(args) > 1:
#         user_uuid = args[1]
#         res = testt.delete_user_by_uuid(user_uuid)
#         if res:
#             bot.send_message(chat_id=my_id, text="Пользователь удалён из 3X-UI")
#         else:
#             bot.send_message(chat_id=my_id, text="Не удалось найти пользователя")
#     else:
#         bot.send_message(message.chat.id, "Укажите UUID после команды")
@bot.message_handler(commands=['admin_add']) # Добавление ТЕСТ подписки на 3 дня
def add_admin(message):
    user_id = message.from_user.id
    created_uuid = None
    created_email = None

    # ✅ Отладка
    print(f"🔍 user_id: {user_id}, ADMIN_IDS: {ADMIN_IDS}, тип: {type(ADMIN_IDS)}")

    # ✅ Проверка прав с защитой от ошибок
    if not isinstance(ADMIN_IDS, list):
        bot.send_message(message.chat.id, "❌ Ошибка конфигурации: ADMIN_IDS должен быть списком")
        return

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return

    args = message.text.split()

    if len(args) < 2:
        bot.send_message(message.chat.id, f"❌ Укажите ID пользователя после команды:\n/admin_add {my_id}")
        return

    target_user_id = args[1]

    try:
        if target_user_id == "778":
            # ТЕСТОВЫЙ пользователь
            bot.send_message(message.chat.id, "🧪 Добавляю ТЕСТ пользователя...")

            result = vpn_manager.create_user_and_get_link(
                username=f"test_{randint(1, 99999999999999)}",
                expire_days=3,
                data_limit_gb=0,
                add_to_all_squads=True,
                verbose=True
            )
            if result:
                HAPP_URL = f"{result['subscription_url']}"
                mark = types.InlineKeyboardMarkup()
                btn1 = types.InlineKeyboardButton(text="🔎 Сгенерировать QR-код", callback_data="QR_codee")
                btn2 = types.InlineKeyboardButton(text="🔑 Подключить в Happ", url=HAPP_URL)
                btn3 = types.InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)
                btn4 = types.InlineKeyboardButton(text="👤 Профиль", callback_data="profil")
                mark.add(btn1)
                mark.add(btn2)
                mark.add(btn3, btn4)

                photo1 = open("./start_mes.png", "rb")

                response_text = f"""
📋 Информация о подписке:

Срок подписки: 3 дня

🔗 Ссылка на подключение:
<code>{result['subscription_url']}</code>

Выберите действие: 
"""
                bot.send_photo(
                    message.chat.id,
                    caption=response_text,
                    photo=photo1,
                    parse_mode="HTML",
                    reply_markup=mark
                )

        else:
            # ОБЫЧНЫЙ пользователь
            bot.send_message(message.chat.id, f"👤 Добавляю пользователя {target_user_id}...")

            plan_id = "premium"
            subscription_manager.create_subscription(target_user_id, plan_id)
            time.sleep(3)

            email = f"MESA_VPN_by_ADMIN_{target_user_id}"
            result = vpn_manager.add_userPRO(target_user_id, email)

            if not result or "uuid" not in result:
                raise Exception("Ошибка создания пользователя")

            created_uuid = result["uuid"]

            limit_text = "∞ GB"

            response_text = f"""
📋 Информация о подписке:

• Тариф: 💎 Премиум
• Трафик: {limit_text}
• Срок: 30 дней

<b>📱 Инструкция по подключению:</b>

1️⃣ <b>ШАГ 1</b>
Скачайте приложение <b>HAPP</b> по ссылке:
<a href="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru">Google Play</a>

2️⃣ <b>ШАГ 2</b>
👇 Скопируйте ссылку ниже 👇

<pre>{result['vless_link']}</pre>

3️⃣ <b>ШАГ 3</b>
Откройте <b>HAPP</b> → нажмите <b>"Из буфера"</b>

4️⃣ <b>ШАГ 4</b>
Нажмите кнопку включения для подключения
            """

            try:
                with open("./photo_happ.jpg", "rb") as photo:
                    bot.send_photo(target_user_id, caption=response_text, photo=photo, parse_mode="HTML")
            except Exception as e:
                bot.send_message(target_user_id, text=response_text, parse_mode="HTML")
                print(f"⚠️ Не удалось отправить фото: {e}")

            bot.send_message(my_id,
                             f"✅ Пользователь добавлен!\n"
                             f"🆔 ID: <code>{target_user_id}</code>\n"
                             f"🔑 UUID: <code>{created_uuid}</code>\n",
                             parse_mode="HTML"
                             )

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Ошибка при добавлении пользователя: {error_msg}")

        bot.send_message(my_id, f"❌ Ошибка при добавлении пользователя {target_user_id}: {error_msg[:100]}")

        # Откат: удаляем пользователя, если был создан
        if created_uuid:
            bot.send_message(my_id, f"🔄 Выполняю откат: удаление пользователя {created_uuid[:8]}...")
            try:
                # Удаляем из Remnawave
                vpn_manager.delete_user(created_uuid)
                bot.send_message(my_id, "✅ Откат выполнен, пользователь удалён")
            except Exception as rollback_error:
                bot.send_message(my_id, f"⚠️ Ошибка при откате: {rollback_error}")
        else:
            bot.send_message(my_id, "ℹ️ Пользователь не был создан, откат не требуется")

@bot.message_handler(commands=['admin_send']) # Отправка любого сообщения пользователю
def admin_send(message):
    args = message.text.split()

    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return

    if len(args) > 1:
        try:
            user = args[1]
            message1 = message.text.replace(f"{user}", "").replace("/admin_send ", "")
            print(message1)
            bot.send_message(chat_id=user, text=message1)
            bot.send_message(chat_id=my_id,
                             text=f"✅ Сообщение отправлено пользователю <code>{user}</code>",
                             parse_mode="HTML")
        except:
            bot.send_message(message.chat.id, "Не удалось отправить сообщение. Ошибка")

    else:
        bot.send_message(message.chat.id, "Введите в таком порядке: /admin_send user_id text")

@bot.message_handler(commands=['admin_send_ALL']) # Отправка любого сообщения для всех пользователей
def admin_send_ALL(message):
    args = message.text.split()

    user_id = message.from_user.id

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return

    if len(args) > 1:
        try:
            conn = sqlite3.connect('itprogerSTART.sql')
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM users")
            data = cur.fetchall()
            message1 = message.text.replace("/admin_send_ALL ", "")

            for el in data:
                bot.send_message(chat_id=el[1],
                                 text=message1)

            bot.send_message(my_id, "Сообщение отправленно всем пользователям")
        except:
            bot.send_message(my_id, "Не удалось отправить сообщение всем пользователям")
    else:
        bot.send_message(my_id, "Укажите сообщение после команды")

@bot.message_handler(commands=['admin_xray']) # Статистика Xray на VPS
def admin_xray(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return

    bot.send_message(my_id, "⏳ Загружаю список пользователей...")

    import paramiko
    import json

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(**SERVER)

    stdin, stdout, stderr = client.exec_command("cat /usr/local/etc/xray/config.json")
    output = stdout.read().decode()

    try:
        config = json.loads(output)
        users = {}

        # Собираем всех пользователей из всех inbound'ов
        for inbound in config.get("inbounds", []):
            if inbound.get("protocol") == "vless" and "clients" in inbound.get("settings", {}):
                for client_data in inbound["settings"]["clients"]:
                    if client_data.get("id") and client_data.get("email"):
                        users[client_data["id"]] = client_data["email"]

        if users:
            text = "📋 <b>Список пользователей в Xray:</b>\n\n"
            for i, (uid, email) in enumerate(users.items(), 1):
                text += f"{i}. 📧 <b>{email}</b>\n"
                text += f"   🔑 <code>{uid}</code>\n\n"

            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    bot.send_message(my_id, part, parse_mode="HTML")
            else:
                bot.send_message(my_id, text, parse_mode="HTML")

            bot.send_message(my_id, f"📊 <b>Всего пользователей:</b> {len(users)}", parse_mode="HTML")
        else:
            bot.send_message(my_id, "❌ Нет пользователей в xray")

    except json.JSONDecodeError as e:
        bot.send_message(my_id, f"❌ Ошибка парсинга JSON: {e}")
        bot.send_message(my_id, f"<pre>{output[:500]}</pre>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(my_id, f"❌ Ошибка: {str(e)[:200]}")

    client.close()

@bot.message_handler(commands=['test']) # Статистика Xray на VPS
def test(message):
    user_id = message.chat.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Нет прав")
        return
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Тест", callback_data="extend_sub"))
    bot.send_message(user_id, 'Выбери', reply_markup=keyboard)

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("🤖 VPN Subscription Bot запускается...")
    print(f"📊 Загружено подписок: {len(active_subscriptions)}")
    #
    # # КРИТИЧНО: Удаляем вебхук и очищаем все обновления
    # try:
    #     # Удаляем вебхук
    a = bot.remove_webhook()
    if a:
        bot.send_message(my_id, "✅ Webhook удален")
    #
    #     # Очищаем очередь обновлений
    #     updates = bot.get_updates(offset=-1, timeout=1)
    #     if updates:
    #         last_update_id = updates[-1].update_id
    #         bot.get_updates(offset=last_update_id + 1)
    #         print(f"✅ Очищено {len(updates)} обновлений")
    #
    vpn_manager._check_all_subscriptions()
    bot.send_message(
            chat_id=my_id,
            text=f"🚀 Бот успешно запущен\n📊 Загружено подписок: {len(active_subscriptions)}")
    bot.infinity_polling()
    #     )
    #     bot.polling(
    #         none_stop=True,  # Не останавливаться при ошибках
    #         interval=1,  # Интервал между запросами
    #         long_polling_timeout=30,  # Длинный polling
    #         allowed_updates=["message", "callback_query"]  # Разрешаем только нужные типы
    #     )
    #
    # except Exception as e:
    #     print(f"⚠️ Ошибка очистки: {e}")
    #     bot.polling(
    #         none_stop=True,  # Не останавливаться при ошибках
    #         interval=1,  # Интервал между запросами
    #         long_polling_timeout=30,  # Длинный polling
    #         allowed_updates=["message", "callback_query"]  # Разрешаем только нужные типы
    #     )





