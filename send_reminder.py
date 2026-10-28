import os
import json
import requests
from datetime import datetime, timedelta, timezone

# Берем токен и Chat ID из секретов GitHub (которые мы добавили)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Функция для отправки сообщения
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

# Читаем список задач из файла tasks.json
def check_tasks():
    # Если файла нет, создаем пустой список
    if not os.path.exists('tasks.json'):
        return

    with open('tasks.json', 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    # Текущее время в UTC
    now = datetime.now(timezone.utc)
    
    for task in tasks:
        # Пропускаем выполненные задачи
        if task.get('done'):
            continue
            
        # Парсим время задачи (формат: "2026-11-01 15:00")
        task_time = datetime.strptime(task['time'], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        
        # Вычисляем разницу между задачей и текущим временем
        diff = task_time - now
        
        # Если до задачи осталось от 55 до 65 минут, отправляем уведомление
        if timedelta(minutes=55) <= diff <= timedelta(minutes=65):
            # Чтобы не спамить, можно добавить проверку, отправляли ли уже уведомление
            if not task.get('notified'):
                text = f"🔔 Напоминание!\n\nЗадача: {task['title']}\nВремя: {task['time']}"
                send_message(text)
                
                # Отмечаем, что уведомление отправлено
                task['notified'] = True

    # Сохраняем обновленный список (чтобы не отправлять повторно)
    with open('tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check_tasks()
    # Отправляем тестовое сообщение при ручном запуске
    if os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch':
        send_message("✅ Скрипт успешно запущен вручную! Уведомления работают.")
