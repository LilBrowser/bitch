import asyncio
import os
import re
from telethon import TelegramClient, events, errors

# ==========================================
# НАСТРОЙКИ
# ==========================================
API_ID = 94575
API_HASH = "a3406de8d171bb422bb6ddf3bbd800e2"

# Сессия-слушатель (твой основной аккаунт)
LISTENER_SESSION = 'my_new_session' 

# Куда присылать отчеты
MY_MAIN_ID = 'me' 

# Канал для мониторинга
TARGET_CHANNEL = '@Matrix_grup'

# ==========================================

os.chdir(os.path.dirname(os.path.abspath(__file__)))

listener_client = TelegramClient(LISTENER_SESSION, API_ID, API_HASH)

# Глобальные переменные для хранения состояния
current_phone = None
current_hash = None
usa_client = None

@listener_client.on(events.NewMessage(chats=TARGET_CHANNEL))
async def monitor_handler(event):
    global current_phone, current_hash, usa_client
    msg_text = event.message.message or ""
    if not msg_text:
        return

    # 1. ЛОВИМ НОМЕРА США (+1)
    us_numbers = re.findall(r'\+1\d{10,14}', msg_text)
    if us_numbers:
        # Если уже был номер в работе, сбрасываем его
        if usa_client:
            await usa_client.disconnect()
            usa_client = None
            
        current_phone = us_numbers[0]
        print(f"📱 Пойман номер: {current_phone}. Запрашиваем СМС...")
        
        await listener_client.send_message(MY_MAIN_ID, f"📱 **Пойман номер:**\n`{current_phone}`\n📨 Отправляю запрос на СМС...")
        
        # Создаем клиент для нового аккаунта
        usa_client = TelegramClient('usa', API_ID, API_HASH)
        await usa_client.connect()
        
        try:
            # 🔥 САМОЕ ВАЖНОЕ: Запрашиваем код, чтобы СМС пришла на телефон
            sent_code = await usa_client.send_code_request(current_phone)
            # Запоминаем хэш, он нужен для входа!
            current_hash = sent_code.phone_code_hash 
            
            print(f"📨 Запрос отправлен. Ждем код в канале...")
            await listener_client.send_message(MY_MAIN_ID, f"✅ Запрос отправлен! Ждем код в канале...")
            
        except Exception as e:
            print(f"❌ Ошибка запроса кода: {e}")
            await listener_client.send_message(MY_MAIN_ID, f"❌ Ошибка при запросе СМС: {e}")
            current_phone = None
            current_hash = None
            await usa_client.disconnect()
            usa_client = None

    # 2. ЛОВИМ КОД
    code_match = re.search(r'Ваш код[:\s]*(\d{4,6})', msg_text, re.IGNORECASE)
    
    if code_match and current_phone and current_hash and usa_client:
        code = code_match.group(1)
        print(f"🔑 Пойман код: {code} для номера {current_phone}")
        
        await listener_client.send_message(MY_MAIN_ID, f"⏳ **Пробую войти в {current_phone} с кодом {code}...**")

        try:
            # Входим, используя сохраненный хэш
            await usa_client.sign_in(
                phone=current_phone, 
                code=code, 
                phone_code_hash=current_hash
            )
            
            # Если всё ок
            await listener_client.send_message(MY_MAIN_ID, f"✅ **УСПЕХ!**\nАккаунт `{current_phone}` сохранен в файл `usa.session`!")
            await usa_client.disconnect()
            
        except errors.SessionPasswordNeededError:
            await listener_client.send_message(MY_MAIN_ID, f"🔐 **ВНИМАНИЕ!**\nАккаунт `{current_phone}` требует облачный пароль (2FA).")
            await usa_client.disconnect()
        except errors.PhoneCodeExpiredError:
            await listener_client.send_message(MY_MAIN_ID, f"⏰ **ОШИБКА:** Код для `{current_phone}` истек.")
            await usa_client.disconnect()
        except errors.PhoneCodeInvalidError:
            await listener_client.send_message(MY_MAIN_ID, f"❌ **ОШИБКА:** Неверный код для `{current_phone}`.")
            await usa_client.disconnect()
        except Exception as e:
            await listener_client.send_message(MY_MAIN_ID, f"❌ **Ошибка при входе:** {e}")
            await usa_client.disconnect()

        # Сбрасываем данные после попытки
        current_phone = None
        current_hash = None
        usa_client = None

async def main():
    print("⏳ Запуск радара...")
    await listener_client.start()
    me = await listener_client.get_me()
    print(f"✅ Радар работает под аккаунтом: {me.first_name}")
    print(f"👀 Ждем номера и коды в {TARGET_CHANNEL}...")
    await listener_client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Остановлено.")