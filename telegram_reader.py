import asyncio
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Any

# Сторонние библиотеки
from telethon import TelegramClient
from telethon.tl.functions.messages import GetPeerDialogsRequest
from dotenv import load_dotenv

# 1. Загружаем секреты из файла .env (если он есть)
load_dotenv()

# Проверяем, что ключи загрузились
API_ID: str | None = os.getenv("TG_API_ID")
API_HASH: str | None = os.getenv("TG_API_HASH")
GMAIL_USER: str | None = os.getenv("GMAIL_USER")
GMAIL_PASS: str | None = os.getenv("GMAIL_PASS")
TO_EMAIL: str | None = os.getenv("TO_EMAIL")

if not all([API_ID, API_HASH, GMAIL_USER, GMAIL_PASS]):
    print("❌ Ошибка: Не найдены ключи в .env или переменных окружения!")
    exit(1)

# 2. Загружаем конфиг с каналами
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config: dict[str, Any] = json.load(f)
        TARGETS: list[str] = config.get("channels", [])
        LIMIT: int = config.get("message_limit_per_channel", 10)
        SUBJECT_PREFIX: str = config.get("email_subject_prefix", "Telegram Digest")
        SHOW_UNREAD_COUNT: bool = config.get("show_unread_count", True)
        MARK_AS_READ_AFTER_FETCH: bool = config.get(
            "mark_as_read_after_fetch", False
        )
        ONLY_UNREAD: bool = config.get("only_unread", False)
        # ОБРАБОТКА ИНСТРУКЦИЙ (СПИСОК -> СТРОКА)
        raw_instructions = config.get("ai_instructions", [])
        if isinstance(raw_instructions, list):
            # Соединяем строки через перенос (\n)
            AI_INSTRUCTIONS = "\n".join(raw_instructions)
        else:
            # Если вдруг там просто строка
            AI_INSTRUCTIONS = str(raw_instructions)
except FileNotFoundError:
    print("❌ Ошибка: Не найден файл config.json")
    exit(1)


async def main() -> None:
    # Файл сессии будет называться anon.session и будет игнорироваться гитом
    async with TelegramClient("anon", int(API_ID), API_HASH) as client:

        print("🔍 Начинаю сбор сообщений...")
        # «Сегодня» = полночь по локальной дате (в UTC для сравнения с message.date)
        local_midnight = datetime.now().astimezone().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today: datetime = local_midnight.astimezone(timezone.utc)

        full_body: list[str] = []
        total_count: int = 0

        for target in TARGETS:
            try:
                # Пытаемся получить канал/чат
                entity = await client.get_entity(target)
                title: str = entity.title if hasattr(entity, "title") else str(target)

                print(f"Сканирую: {title}...")

                # Диалог: непрочитанные и граница прочитанного (для only_unread)
                unread_count: int | None = None
                read_inbox_max_id: int = 0  # сообщения с id > этого считаются непрочитанными
                if SHOW_UNREAD_COUNT or ONLY_UNREAD:
                    try:
                        peer = await client.get_input_entity(entity)
                        result = await client(GetPeerDialogsRequest(peers=[peer]))
                        if result.dialogs:
                            dialog = result.dialogs[0]
                            if SHOW_UNREAD_COUNT:
                                unread_count = getattr(dialog, "unread_count", 0) or 0
                            if ONLY_UNREAD:
                                read_inbox_max_id = getattr(
                                    dialog, "read_inbox_max_id", 0
                                ) or 0
                    except Exception:
                        pass

                msgs: list[str] = []
                max_read_id: int | None = None
                async for message in client.iter_messages(
                    entity, limit=50
                ):
                    # Только за сегодня, с текстом; при only_unread — только id > read_inbox_max_id
                    if not (message.date > today and message.text):
                        continue
                    if ONLY_UNREAD and message.id <= read_inbox_max_id:
                        continue
                    # Запоминаем id самого нового сообщения (iter идёт от новых к старым)
                    if max_read_id is None:
                        max_read_id = message.id

                    time_str: str = message.date.astimezone().strftime("%H:%M")
                    sender_name: str = ""
                    if message.sender and hasattr(message.sender, "first_name"):
                        sender_name = f"{message.sender.first_name}: "
                    msgs.append(f"[{time_str}] {sender_name}{message.text}")

                    if len(msgs) >= LIMIT:
                        break

                if msgs:
                    msgs.reverse()
                    header: str = f"=== Начало канала: {title} ==="
                    if unread_count is not None:
                        header += f" (непрочитанных в диалоге: {unread_count})"
                    header += "\n"
                    block = header + "\n\n".join(msgs)
                    full_body.append(block)
                    total_count += len(msgs)

                # Пометить канал/чат прочитанным до последнего собранного сообщения
                if MARK_AS_READ_AFTER_FETCH and max_read_id is not None:
                    try:
                        await client.send_read_acknowledge(entity, max_id=max_read_id)
                        print(f"   ✓ Отмечено прочитанным до id={max_read_id}")
                    except Exception as e:
                        print(f"   ⚠ Не удалось отметить прочитанным: {e}")

            except ValueError:
                print(f"⚠️ Не нашел канал: {target}")
            except Exception as e:
                print(f"❌ Ошибка с {target}: {e}")

        if not full_body:
            print("📭 Новых сообщений за сегодня нет.")
            return

        # Сборка письма
        date_str: str = datetime.now().strftime("%d.%m.%Y")
        time_str: str = datetime.now().strftime("%H:%M")
        subject: str = f"{SUBJECT_PREFIX} [{date_str} {time_str}]"

        system_prompt = (
                f"\n\n--- ИНСТРУКЦИЯ ДЛЯ AI (GEMINI) ---\n"
                f"{AI_INSTRUCTIONS}\n\n"
                f"-----------------------------------\n\n"
                f"--- НАЧАЛО ДАННЫХ ({date_str} - {time_str}) ---\n"
            )

        final_content: str = system_prompt + "\n\n".join(full_body)
        print(final_content)
        # Отправка
        msg: MIMEMultipart = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(final_content, "plain"))

        # Таймаут 60 сек; многие мобильные операторы блокируют SMTP (587/465)
        smtp_timeout: int = 60
        try:
            print("📧 Отправляю письмо...")
            try:
                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=smtp_timeout)
                server.starttls()
            except (OSError, TimeoutError):
                # Пробуем порт 465 (SMTPS), если 587 заблокирован оператором
                print("   Порт 587 недоступен, пробую 465...")
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=smtp_timeout)
            print("Успешно подключились к SMTP")
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
            server.quit()
            print("✅ Успешно! Письмо отправлено.")
        except Exception as e:
            print(f"❌ Ошибка отправки почты: {e}")
            print("   Подсказка: с мобильного интернета/хотспота оператор часто блокирует SMTP. Попробуйте с Wi‑Fi.")


if __name__ == "__main__":
    asyncio.run(main())
