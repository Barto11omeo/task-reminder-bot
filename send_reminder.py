import os
import json
import requests
from datetime import datetime, timedelta, timezone

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
            # Формат: /add Купить хлеб 2026-12-31 18:00
            try:
                parts = text[4:].strip().rsplit(' ', 2)
                title = parts[0]
                date_str = parts[1]
                time_str = parts[2]
                
                task_time = f"{date_str} {time_str}"
                # Проверяем, правильный ли формат времени
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
        
    # Запоминаем, что мы прочитали эти сообщения, чтобы не добавлять их дважды
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
            
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        diff = task_time - now
        
        # Если до задачи осталось от 55 до 65 минут
        if timedelta(minutes=55) <= diff <= timedelta(minutes=65):
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
    
    # Если запускаем вручную, отправим тестовое сообщение
    if os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        send_message("✅ Бот обновлен! Теперь я умею принимать команды.")
