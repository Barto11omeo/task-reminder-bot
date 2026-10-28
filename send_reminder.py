import os
import json
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def load_tasks():
    if os.path.exists('tasks.json'):
        with open('tasks.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open('tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def format_tasks_list(tasks):
    if not tasks:
        return "📭 Список задач пуст."
    
    sorted_tasks = sorted(tasks, key=lambda x: datetime.strptime(x['time'], "%Y-%m-%d %H:%M"))
    
    msg = "📋 Ваши задачи:\n\n"
    for i, t in enumerate(sorted_tasks, 1):
        status = "✅" if t.get('done') else "⏳"
        dt = datetime.strptime(t['time'], "%Y-%m-%d %H:%M")
        display_time = dt.strftime("%d.%m %H:%M")
        msg += f"{i}. {status} {t['title']} — {display_time}\n"
    return msg

def clean_old_tasks(tasks):
    """Удаляет задачи, время которых уже прошло"""
    now = datetime.now(timezone.utc)
    moscow_tz = ZoneInfo("Europe/Moscow")
    cleaned = []
    for task in tasks:
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=moscow_tz).astimezone(timezone.utc)
        if task_time >= now:
            cleaned.append(task)
        else:
            print(f"Удалена прошедшая задача: {task['title']}")
    return cleaned

def check_telegram_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()
    
    if not response.get('ok'):
        return

    updates = response.get('result', [])
    print(f"Найдено сообщений: {len(updates)}")
    
    tasks = load_tasks()
    
    # Сначала чистим старые задачи!
    tasks = clean_old_tasks(tasks)
    save_tasks(tasks)

    last_update_id = 0

    for update in updates:
        last_update_id = update['update_id']
        message = update.get('message', {})
        text = message.get('text', '')
        
        if text == '/tasks':
            send_message(format_tasks_list(tasks))
            
        elif text.startswith('/delete'):
            try:
                index = int(text.split(' ')[1]) - 1
                sorted_tasks = sorted(tasks, key=lambda x: datetime.strptime(x['time'], "%Y-%m-%d %H:%M"))
                
                if 0 <= index < len(sorted_tasks):
                    task_to_remove = sorted_tasks[index]
                    tasks.remove(task_to_remove)
                    save_tasks(tasks) # Сохраняем сразу!
                    send_message(f"🗑 Задача «{task_to_remove['title']}» удалена.\n\n" + format_tasks_list(tasks))
                else:
                    send_message("❌ Задачи с таким номером не существует.")
            except Exception:
                send_message("❌ Ошибка. Формат: /delete НОМЕР")
                
        elif text.startswith('/add'):
            try:
                parts = text[4:].strip().rsplit(' ', 2)
                title = parts[0]
                date_str = parts[1]
                time_str = parts[2]
                
                day, month = date_str.split('.')
                hour, minute = time_str.split('.')
                task_time = f"2026-{month}-{day} {hour}:{minute}"
                datetime.strptime(task_time, "%Y-%m-%d %H:%M")
                
                tasks.append({
                    "title": title,
                    "time": task_time,
                    "done": False,
                    "notified": False
                })
                save_tasks(tasks) # Сохраняем сразу!
                send_message(f"✅ Задача «{title}» добавлена.\n\n" + format_tasks_list(tasks))
            except Exception:
                send_message("❌ Ошибка формата. Пример: /add Купить хлеб 29.10 18.00")

    # Запоминаем, что прочитали эти сообщения (защита от повторного чтения)
    if last_update_id > 0:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}")

def check_reminders():
    tasks = load_tasks()
    if not tasks:
        return

    now = datetime.now(timezone.utc)
    moscow_tz = ZoneInfo("Europe/Moscow")
    updated = False
    
    for task in tasks:
        if task.get('done') or task.get('notified'):
            continue
            
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=moscow_tz).astimezone(timezone.utc)
        diff = task_time - now
        
        if timedelta(minutes=45) <= diff <= timedelta(minutes=75):
            text = f"🔔 Напоминание!\n\nЗадача: {task['title']}\nВремя: {task['time']}"
            send_message(text)
            task['notified'] = True
            updated = True

    if updated:
        save_tasks(tasks)

if __name__ == "__main__":
    check_telegram_commands()
    check_reminders()
