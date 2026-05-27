import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional


TASKS_FILE = r"D:\MAX_AI\tasks.json"
REMINDERS_FILE = r"D:\MAX_AI\reminders.json"


class ProductivityManager:
    def __init__(self, say_callback) -> None:
        self.say = say_callback  # MAX's _say method
        self.tasks = self._load(TASKS_FILE, default=[])
        self.reminders = self._load(REMINDERS_FILE, default=[])
        self._start_reminder_thread()

    # ── DATA ─────────────────────────────────────────────
    def _load(self, path: str, default) -> list:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save(self, path: str, data) -> None:
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ── TASK MANAGEMENT ──────────────────────────────────
    def add_task(self, task: str) -> str:
        entry = {
            "id": len(self.tasks) + 1,
            "task": task.strip(),
            "done": False,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.tasks.append(entry)
        self._save(TASKS_FILE, self.tasks)
        return f"Task added: {task.strip()}."

    def show_tasks(self) -> str:
        pending = [t for t in self.tasks if not t["done"]]
        if not pending:
            return "No pending tasks. You're either very productive or very avoidant."
        task_list = ", ".join([f"{t['id']}. {t['task']}" for t in pending])
        return f"You have {len(pending)} pending task{'s' if len(pending) > 1 else ''}: {task_list}."

    def complete_task(self, keyword: str) -> str:
        keyword = keyword.lower().strip()
        for task in self.tasks:
            if keyword in task["task"].lower() and not task["done"]:
                task["done"] = True
                self._save(TASKS_FILE, self.tasks)
                return f"Marked '{task['task']}' as done. One less thing to ignore."
        return f"No pending task matching '{keyword}' found."

    def clear_tasks(self) -> str:
        self.tasks = []
        self._save(TASKS_FILE, self.tasks)
        return "All tasks cleared. Fresh start."

    # ── REMINDERS ────────────────────────────────────────
    def add_reminder(self, text: str, time_str: str) -> str:
        reminder_time = self._parse_time(time_str)
        if not reminder_time:
            return "I couldn't understand that time. Try something like '6 PM' or '14:30'."

        entry = {
            "text": text.strip(),
            "time": reminder_time.strftime("%Y-%m-%d %H:%M"),
            "triggered": False
        }
        self.reminders.append(entry)
        self._save(REMINDERS_FILE, self.reminders)
        return f"Got it, I'll remind you to {text.strip()} at {reminder_time.strftime('%I:%M %p')}."

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        time_str = time_str.strip().lower()
        now = datetime.now()

        # Handle "in X minutes/hours"
        in_match = re.search(r"in\s+(\d+)\s+(minute|hour)s?", time_str)
        if in_match:
            amount = int(in_match.group(1))
            unit = in_match.group(2)
            if unit == "minute":
                return now + timedelta(minutes=amount)
            elif unit == "hour":
                return now + timedelta(hours=amount)

        # Handle "X pm/am" or "X:XX pm/am"
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)

            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0

            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time < now:
                reminder_time += timedelta(days=1)
            return reminder_time

        return None

    def _start_reminder_thread(self) -> None:
        def check_reminders():
            while True:
                now = datetime.now()
                for reminder in self.reminders:
                    if reminder["triggered"]:
                        continue
                    reminder_time = datetime.strptime(reminder["time"], "%Y-%m-%d %H:%M")
                    if now >= reminder_time:
                        reminder["triggered"] = True
                        self._save(REMINDERS_FILE, self.reminders)
                        self.say(f"Reminder: {reminder['text']}")
                time.sleep(30)  # check every 30 seconds

        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()

    # ── DAILY PLAN ───────────────────────────────────────
    def plan_day(self) -> str:
        pending = [t for t in self.tasks if not t["done"]]
        now = datetime.now()
        hour = now.hour

        if hour < 12:
            greeting = "Good morning! Here's a solid plan"
        elif hour < 17:
            greeting = "Afternoon already! Here's how to salvage the day"
        else:
            greeting = "Evening mode. Here's a light plan"

        if pending:
            top_tasks = pending[:3]
            task_names = ", ".join([t["task"] for t in top_tasks])
            return (
                f"{greeting}: Start with {task_names}. "
                f"Work in 25-minute blocks with 5-minute breaks. "
                f"You have {len(pending)} task{'s' if len(pending) > 1 else ''} pending — let's get moving."
            )
        return (
            f"{greeting}: No pending tasks — either plan new goals or take a well-earned break. "
            "Either way, stay intentional."
        )

    # ── SMART SUGGESTIONS ────────────────────────────────
    def smart_suggest(self, text: str) -> Optional[str]:
        text_low = text.lower()
        pending = [t for t in self.tasks if not t["done"]]

        if any(w in text_low for w in ["bored", "nothing to do", "free"]):
            if pending:
                return f"You've got {len(pending)} pending task{'s' if len(pending) > 1 else ''}. Pick one and knock it out."
            return "No tasks pending. Add something worth doing or take a real break — not a phone break."

        if any(w in text_low for w in ["lazy", "unmotivated", "tired", "don't feel like"]):
            return "Start with something small — momentum builds fast. Pick the easiest task and begin."

        if any(w in text_low for w in ["stressed", "overwhelmed", "too much"]):
            return "Take a 5-minute break, then tackle one task at a time. You don't eat everything at once."

        if any(w in text_low for w in ["procrastinating", "distracted", "can't focus"]):
            return "Set a 25-minute timer, close distractions, and pick one task. That's all."

        return None

    # ── MAIN HANDLER ─────────────────────────────────────
    def handle(self, text: str) -> Optional[str]:
        query = text.strip().lower()

        # Add task
        match = re.search(r"\b(add task|create task|new task)\s+(.+)", query)
        if match:
            return self.add_task(match.group(2).strip())

        # Show tasks
        if re.search(r"\b(show|list|what are)\b.*(task|todo|to do)", query):
            return self.show_tasks()

        # Complete task
        match = re.search(r"\b(mark|complete|finish|done|finished)\s+(.+?)\s*(as done|as complete|complete|done)?\s*$", query)
        if match:
            return self.complete_task(match.group(2).strip())

        # Clear tasks
        if re.search(r"\b(clear|delete|remove)\s+(all\s+)?tasks\b", query):
            return self.clear_tasks()

        # Set reminder
        match = re.search(r"\bremind me to\s+(.+?)\s+at\s+(.+)", query)
        if match:
            return self.add_reminder(match.group(1).strip(), match.group(2).strip())

        match = re.search(r"\bremind me to\s+(.+?)\s+in\s+(.+)", query)
        if match:
            return self.add_reminder(match.group(1).strip(), "in " + match.group(2).strip())

        # Plan day
        if re.search(r"\b(plan my day|daily plan|what should i do|schedule my day)\b", query):
            return self.plan_day()

        # Smart suggestions
        suggestion = self.smart_suggest(query)
        if suggestion:
            return suggestion

        return None