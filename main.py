import asyncio
import sys
import re
import threading
import time 
import sys
import psutil
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
def is_already_running():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == current_pid:
                continue
            if proc.info['name'] == 'python.exe':
                cmdline = proc.info['cmdline'] or []
                if any('main.py' in c for c in cmdline):
                    return True
        except Exception:
            pass
    return False

if is_already_running():
    print("[MAX] Already running. Exiting duplicate instance.")
    sys.exit(0)

from ai_brain import AIBrain
from commands import CommandHandler
from gui import MaxGUI
from memory import MemoryStore
from speech_to_text import SpeechToText
from text_to_speech import TextToSpeech

WAKE_WORD = "hey max"


class MaxAssistant:

    def __init__(self) -> None:
        self.gui = MaxGUI()
        self.stt = SpeechToText()
        self.tts = TextToSpeech(voice="en-IN-NeerjaNeural")
        self.memory = MemoryStore()
        self.commands = CommandHandler()
        self.brain = AIBrain()

        from productivity import ProductivityManager
        self.productivity = ProductivityManager(say_callback=self._say)
        from messaging import MessagingHandler
        self.messaging = MessagingHandler(say_callback=self._say)
        from second_brain import SecondBrain
        self.brain2 = SecondBrain(say_callback=self._say)
        from dev_tools import DevTools
        self.dev = DevTools(say_callback=self._say)
        from file_manager import FileManager
        self.file_manager = FileManager(say_callback=self._say)

    def run(self) -> None:
        self.gui.root.bind('<Alt-q>', lambda event: self._activate_by_hotkey())
        print("[MAX] Ready. Listening always...")
        listener = threading.Thread(target=self._listen_loop, daemon=True)
        listener.start()
        self.gui.run()

    def _activate_by_hotkey(self) -> None:
        self.gui.enqueue_message("MAX", "Activated via Alt+Q")
        self._say("Yes?")

    def _set_status(self, value: str) -> None:
        self.gui.enqueue_status(value)

    def _say(self, text: str) -> None:
        cleaned = TextToSpeech.clean_text(text)
        self.gui.enqueue_message("MAX", cleaned)
        self.tts.speak_async(cleaned)

    def _listen_loop(self) -> None:
        consecutive_errors = 0

        while True:
            try:
                # Wait for TTS to finish — max 8 seconds then open mic anyway
                wait_start = time.time()
                while self.tts.is_speaking():
                    time.sleep(0.1)
                    if time.time() - wait_start > 8:
                        break

                time.sleep(0.2)  # small buffer after speech ends

                self._set_status("Listening...")
                heard = self.stt.listen_once(timeout=5, phrase_time_limit=10)
                self._set_status("Idle")

                if not heard:
                    consecutive_errors = 0
                    continue

                user_text = heard.strip()
                if len(user_text) < 2:
                    continue

                text_low = user_text.lower()
                consecutive_errors = 0

                print(f"[MAX] Heard: '{user_text}'")

                # If MAX is still speaking when user talks — interrupt it
                if self.tts.is_speaking():
                    self.tts.clear_queue()

                # Just "hey max" alone — acknowledge
                if WAKE_WORD in text_low and len(text_low.replace(WAKE_WORD, "").strip()) == 0:
                    self.gui.enqueue_message("You", user_text)
                    self._say("Yes?")
                    continue

                self.gui.enqueue_message("You", user_text)

                threading.Thread(
                    target=self._handle_command,
                    args=(user_text, text_low),
                    daemon=True
                ).start()

            except Exception as e:
                consecutive_errors += 1
                print(f"[MAX] Listen error: {e}")
                if consecutive_errors >= 5:
                    print("[MAX] Restarting mic...")
                    try:
                        self.stt = SpeechToText()
                        consecutive_errors = 0
                    except Exception:
                        time.sleep(2)
                time.sleep(0.3)

    def _handle_command(self, user_text: str, text_low: str) -> None:
        try:
            # Stop command
            if re.search(r"\b(hey max stop|stop max|goodbye max|shutdown max)\b", text_low):
                self._say("Goodbye Boss. Shutting down.")
                time.sleep(2)
                import os
                os.kill(os.getpid(), 9)
                return

            if self._handle_memory(user_text, text_low):
                print("[MAX] Handled by: memory")
                return

            productivity_reply = self.productivity.handle(user_text)
            if productivity_reply:
                print("[MAX] Handled by: productivity")
                self._say(productivity_reply)
                return

            messaging_reply = self.messaging.handle(user_text)
            if messaging_reply:
                print("[MAX] Handled by: messaging")
                self._say(messaging_reply)
                return

            brain_reply = self.brain2.handle(user_text)
            if brain_reply:
                print("[MAX] Handled by: second brain")
                self._say(brain_reply)
                return

            dev_reply = self.dev.handle(user_text)
            if dev_reply:
                print("[MAX] Handled by: dev tools")
                self._say(dev_reply)
                return

            file_reply = self.file_manager.handle(user_text)
            if file_reply:
                print("[MAX] Handled by: file manager")
                self._say(file_reply)
                return

            command_result = self.commands.handle(user_text)
            if command_result.matched:
                print("[MAX] Handled by: commands")
                if command_result.response:
                    self._say(command_result.response)
                return

            print("[MAX] Handled by: AI brain")
            self._set_status("Thinking...")
            detailed = bool(re.search(r"\b(explain more|in detail|details)\b", text_low))
            try:
                reply = self.brain.get_reply(user_text=user_text, detailed=detailed)
            except Exception:
                reply = "I couldn't reach the AI service right now."
            self._set_status("Idle")
            self._say(reply)

        except Exception as e:
            import traceback
            print(f"[MAX] Handler error:\n{traceback.format_exc()}")

    def _handle_memory(self, user_text: str, text_low: str) -> bool:
        name_match = re.search(
            r"\bmy name is\s+([a-zA-Z][a-zA-Z\s'-]{0,40})", user_text, re.I)
        if name_match:
            name = name_match.group(1).strip()
            self.memory.set_user_name(name)
            self._say(f"Got it, I'll call you {name.title()}.")
            return True

        if re.search(r"\bwhat is my name\b", text_low):
            saved_name = self.memory.get_user_name()
            if saved_name:
                self._say(f"Your name is {saved_name}.")
            else:
                self._say("You haven't told me your name yet.")
            return True

        if re.search(r"\b(i live in|i'm from|i am from|my home is in|i live at|i stay in)\s+(.+)", user_text, re.I):
            location_match = re.search(
                r"\b(?:i live in|i'm from|i am from|my home is in|i live at|i stay in)\s+(.+)",
                user_text, re.I)
            if location_match:
                location = location_match.group(1).strip().rstrip('.')
                self.memory.set_home_location(location)
                self._say(f"Got it, I will remember that you live in {location}.")
                return True

        if re.search(r"\b(where do i live|what is my home|where is my home|where am i from)\b", text_low):
            home_location = self.memory.get_home_location()
            if home_location:
                self._say(f"You live in {home_location}.")
            else:
                self._say("I don't know where you live yet. Tell me by saying something like 'I live in Pune'.")
            return True

        if re.search(r"\bremember that\b", text_low):
            remember_match = re.search(r"\bremember that\s+(.+?)\s+is\s+(.+)", user_text, re.I)
            if remember_match:
                fact_key = remember_match.group(1).strip().lower()
                fact_value = remember_match.group(2).strip().rstrip('.')
                self.memory.set_fact(fact_key, fact_value)
                self._say(f"Okay, I'll remember that {fact_key} is {fact_value}.")
                return True

        if re.search(r"\bwhat is my\s+(.+)\b", text_low):
            question_match = re.search(r"\bwhat is my\s+(.+)\b", text_low)
            if question_match:
                fact_key = question_match.group(1).strip().lower()
                if fact_key in {"name", "home", "location", "place", "city", "hometown"}:
                    if fact_key == "name":
                        saved_name = self.memory.get_user_name()
                        if saved_name:
                            self._say(f"Your name is {saved_name}.")
                        else:
                            self._say("I don't know your name yet.")
                        return True
                    home_location = self.memory.get_home_location()
                    if home_location:
                        self._say(f"Your {fact_key} is {home_location}.")
                    else:
                        self._say("I don't know that yet. Tell me by saying where you live.")
                    return True
                stored = self.memory.get_fact(fact_key)
                if stored:
                    self._say(f"Your {fact_key} is {stored}.")
                    return True

        if re.search(r"\b(who are you|introduce yourself)\b", text_low):
            self._say("I'm MAX — your AI desktop assistant. Smarter than your average tool.")
            return True

        if re.search(r"\b(forget everything|clear history|reset conversation|start over)\b", text_low):
            self.brain.clear_history()
            self._say("Done. Fresh start.")
            return True

        if re.search(r"\bgood morning\b", text_low):
            threading.Thread(target=self._morning_briefing, daemon=True).start()
            return True

        if re.search(r"\bdaddy.?s home\b", text_low):
            threading.Thread(target=self._daddy_home, daemon=True).start()
            return True

        return False

    def _morning_briefing(self) -> None:
        import subprocess
        self._say("Good morning Boss! Starting your briefing.")
        time.sleep(2)

        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        edge   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

        self._say("Checking weather.")
        subprocess.Popen(["taskkill", "/f", "/im", "chrome.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        subprocess.Popen([
            chrome, "--new-window",
            "--window-size=960,520", "--window-position=0,0",
            "https://www.google.com/search?q=weather+in+pimpri+chinchwad+pune"
        ])
        time.sleep(7)

        self._say("Loading news.")
        subprocess.Popen([edge, "--new-window", "https://news-app-dmoy.onrender.com"])
        time.sleep(15)

        self._say("Opening TradingView.")
        subprocess.Popen(["explorer",
            "shell:AppsFolder\\"
            "31178TradingViewInc.TradingView_q4jpyh43s5mv6!TradingView.Desktop"])
        time.sleep(3)
        self._say("Briefing ready. Have a productive day Boss!")

    def _daddy_home(self) -> None:
        import subprocess
        import random
        intros = [
            "Let's break it.",
            "Time to build something great.",
            "Locked in. Let's go.",
            "No distractions. Just work.",
            "Focus mode activated.",
        ]
        self._say(random.choice(intros))
        time.sleep(1)

        vscode = (r"C:\Users\Swaraj Shinde\AppData\Local"
                  r"\Programs\Microsoft VS Code\Code.exe")
        subprocess.Popen([vscode])
        time.sleep(3)
        subprocess.Popen([
            "powershell", "-c",
            "$wshell = New-Object -ComObject wscript.shell; "
            "$wshell.AppActivate('Visual Studio Code'); "
            "Start-Sleep -Milliseconds 500; $wshell.SendKeys('%{F10}')"
        ])
        time.sleep(2)
        subprocess.Popen(["explorer", "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude"])


if __name__ == "__main__":
    assistant = MaxAssistant()
    while True:
        try:
            assistant.run()
            break
        except Exception as e:
            import traceback
            print(f"[MAX] CRASH:\n{traceback.format_exc()}")
            try:
                assistant.gui.shutdown()
            except Exception:
                pass
            print("[MAX] Restarting in 3 seconds...")
            time.sleep(3)