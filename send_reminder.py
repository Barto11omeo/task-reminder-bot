import os
import json
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Берем токен и Chat ID из секретов GitHub
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def check_telegram_commands():
    # Получаем последние сообщения от бота
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()
    
    if not response.get('ok'):
        return

    updates = response.get('result', [])
    print(f"Бот проснулся. Найдено сообщений: {len(updates)}")
    last_update_id = 0
    
    # Загружаем текущие задачи
    if os.path.exists('tasks.json'):
        with open('tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
    else:
        tasks = []

    for update in updates:
        last_update_id = update['update_id']
        message = update.get('message', {})
        text = message.get('text', '')
            
        # Если пришла команда /add
        if text.startswith('/add'):
            try:
                parts = text[4:].strip().rsplit(' ', 2)
                title = parts[0]
                date_str = parts[1]
                time_str = parts[2]
                
                task_time = f"{date_str} {time_str}"
                datetime.strptime(task_time, "%Y-%m-%d %H:%M")
                
                tasks.append({
                    "title": title,
                    "time": task_time,
                    "done": False,
                    "notified": False
                })
                send_message(f"✅ Задача добавлена: {title} на {task_time}")
            except Exception:
                send_message("❌ Ошибка. Формат: /add Название ГГГГ-ММ-ДД ЧЧ:ММ\nПример: /add Купить хлеб 2026-12-31 18:00")

    # Сохраняем обновленный список задач
    with open('tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
        
    # Запоминаем, что мы прочитали эти сообщения
    if last_update_id > 0:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}")

def check_reminders():
    if not os.path.exists('tasks.json'):
        return

    with open('tasks.json', 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    now = datetime.now(timezone.utc)
    updated = False
    
    for task in tasks:
        if task.get('done') or task.get('notified'):
            continue
            
        moscow_tz = ZoneInfo("Europe/Moscow")
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=moscow_tz).astimezone(timezone.utc)
        diff = task_time - now
        
        if timedelta(minutes=45) <= diff <= timedelta(minutes=75):
            text = f"🔔 Напоминание!\n\nЗадача: {task['title']}\nВремя: {task['time']}"
            send_message(text)
            task['notified'] = True
            updated = True

    if updated:
        with open('tasks.json', 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check_telegram_commands()
    check_reminders()
    
