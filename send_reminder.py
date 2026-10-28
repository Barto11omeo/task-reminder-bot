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

def format_tasks_list(tasks):
    """Функция для красивого вывода списка задач (сортирует по времени)"""
    if not tasks:
        return "📭 Список задач пуст."
    
    # Сортируем задачи по времени (от ближайших к дальним)
    sorted_tasks = sorted(tasks, key=lambda x: datetime.strptime(x['time'], "%Y-%m-%d %H:%M"))
    
    msg = "📋 Ваши задачи:\n\n"
    for i, t in enumerate(sorted_tasks, 1):
        status = "✅" if t.get('done') else "⏳"
        # Переводим время обратно в формат ДД.ММ ЧЧ:ММ для удобства
        dt = datetime.strptime(t['time'], "%Y-%m-%d %H:%M")
        display_time = dt.strftime("%d.%m %H:%M")
        msg += f"{i}. {status} {t['title']} — {display_time}\n"
    return msg

def check_telegram_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()
    
    if not response.get('ok'):
        return

    updates = response.get('result', [])
    print(f"Бот проснулся. Найдено сообщений: {len(updates)}")
    last_update_id = 0
    
    if os.path.exists('tasks.json'):
        with open('tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
    else:
        tasks = []

    for update in updates:
        last_update_id = update['update_id']
        message = update.get('message', {})
        text = message.get('text', '')
        
        # 1. Команда /tasks
        if text == '/tasks':
            send_message(format_tasks_list(tasks))
            continue 
            
        # 2. Команда /delete (например, /delete 1)
        if text.startswith('/delete'):
            try:
                index = int(text.split(' ')[1]) - 1
                sorted_tasks = sorted(tasks, key=lambda x: datetime.strptime(x['time'], "%Y-%m-%d %H:%M"))
                
                if 0 <= index < len(sorted_tasks):
                    task_to_remove = sorted_tasks[index]
                    tasks.remove(task_to_remove)
                    send_message(f"🗑 Задача «{task_to_remove['title']}» удалена.\n\n" + format_tasks_list(tasks))
                else:
                    send_message("❌ Задачи с таким номером не существует.")
            except Exception:
                send_message("❌ Ошибка. Формат: /delete НОМЕР\nПример: /delete 1")
            continue
            
        # 3. Команда /add (формат: /add Название ДД.ММ ЧЧ.ММ)
        if text.startswith('/add'):
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
                
                send_message(f"✅ Задача «{title}» добавлена.\n\n" + format_tasks_list(tasks))
                
            except Exception:
                send_message("❌ Ошибка формата. Пример: /add Купить хлеб 29.10 18.00")

    # Сохраняем обновленный список задач
    with open('tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
        
    if last_update_id > 0:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}")

def check_reminders():
    """Проверяет напоминания и удаляет прошедшие задачи"""
    if not os.path.exists('tasks.json'):
        return

    with open('tasks.json', 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    now = datetime.now(timezone.utc)
    updated = False
    cleaned_tasks = []
    
    for task in tasks:
        moscow_tz = ZoneInfo("Europe/Moscow")
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=moscow_tz).astimezone(timezone.utc)
        
        # АВТОУДАЛЕНИЕ: Если задача уже прошла, не добавляем её в новый список
        if task_time < now:
            print(f"Удалена прошедшая задача: {task['title']}")
            updated = True
            continue
            
        # Оставляем задачу в списке
        cleaned_tasks.append(task)
        
        # ОТПРАВКА НАПОМИНАНИЯ (если еще не отправляли)
        if not task.get('done') and not task.get('notified'):
            diff = task_time - now
            if timedelta(minutes=45) <= diff <= timedelta(minutes=75):
                text = f"🔔 Напоминание!\n\nЗадача: {task['title']}\nВремя: {task['time']}"
                send_message(text)
                task['notified'] = True
                updated = True

    # Если были изменения (удалили или отправили напоминание) - сохраняем
    if updated:
        with open('tasks.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned_tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check_telegram_commands()
    check_reminders()
