import os
import re
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class CommandResult:
    matched: bool
    response: str = ""


class CommandHandler:
    APP_MAP = {
        "chrome":           r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "edge":             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "firefox":          r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "notepad":          "notepad",
        "calculator":       "calc",
        "calc":             "calc",
        "paint":            "mspaint",
        "explorer":         "explorer",
        "settings":         "ms-settings:",
        "task manager":     "taskmgr",
        "cmd":              "cmd",
        "powershell":       "powershell",
        "terminal":         "wt",
        "vscode":           r"C:\Users\Swaraj Shinde\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "vs code":          r"C:\Users\Swaraj Shinde\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "code":             r"C:\Users\Swaraj Shinde\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "cursor":           r"C:\Users\Swaraj Shinde\AppData\Local\Programs\cursor\Cursor.exe",
        "spotify":          r"C:\Users\Swaraj Shinde\AppData\Roaming\Spotify\Spotify.exe",
        "whatsapp":         "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
        "discord":          r"C:\Users\Swaraj Shinde\AppData\Local\Discord\Update.exe",
        "anaconda":         r"C:\Users\Swaraj Shinde\anaconda3\Scripts\anaconda-navigator.exe",
        "ollama":           r"C:\Users\Swaraj Shinde\AppData\Local\Programs\Ollama\ollama app.exe",
        "tradingview":      "shell:AppsFolder\\31178TradingViewInc.TradingView_q4jpyh43s5mv6!TradingView.Desktop",
        "trading view":     "shell:AppsFolder\\31178TradingViewInc.TradingView_q4jpyh43s5mv6!TradingView.Desktop",
        "youtube":          "https://www.youtube.com",
        "gmail":            "https://mail.google.com",
        "github":           "https://www.github.com",
        "linkedin":         "https://www.linkedin.com",
        "instagram":        "https://www.instagram.com",
        "chatgpt":          "https://chat.openai.com",
        "chat gpt":         "https://chat.openai.com",
        "claude":           "https://claude.ai",
        "claude ai":        "https://claude.ai",
        "hotstar":          "https://www.jiohotstar.com",
        "jio hotstar":      "https://www.jiohotstar.com",
        "jiohotstar":       "https://www.jiohotstar.com",
        "whatsapp web":     "https://web.whatsapp.com",
        "news":             "https://news-app-dmoy.onrender.com"
    }

    # ✅ Both singular and plural folder names
    FOLDER_MAP = {
        "desktop":      os.path.expanduser("~\\Desktop"),
        "download":     os.path.expanduser("~\\Downloads"),
        "downloads":    os.path.expanduser("~\\Downloads"),
        "document":     os.path.expanduser("~\\Documents"),
        "documents":    os.path.expanduser("~\\Documents"),
        "picture":      os.path.expanduser("~\\Pictures"),
        "pictures":     os.path.expanduser("~\\Pictures"),
        "music":        os.path.expanduser("~\\Music"),
        "video":        os.path.expanduser("~\\Videos"),
        "videos":       os.path.expanduser("~\\Videos"),
    }

    CLOSE_TRIGGERS  = ["close", "kill", "exit", "quit", "terminate"]
    PLAY_TRIGGERS   = ["play", "put on", "stream"]
    VOLUME_UP       = ["volume up", "increase volume", "louder", "turn up", "raise volume"]
    VOLUME_DOWN     = ["volume down", "decrease volume", "quieter", "turn down", "lower volume"]
    SHUTDOWN        = ["shutdown", "shut down", "power off", "turn off computer", "turn off pc"]
    RESTART         = ["restart", "reboot", "restart computer", "restart pc"]
    LOCK            = ["lock screen", "lock computer", "lock pc", "lock the screen"]
    SLEEP           = ["sleep mode", "put to sleep", "go to sleep"]
    MESSAGING_TRIGGERS = ["send", "message to", "text to", "whatsapp to",
                          "send message", "send whatsapp", "ping"]

    def handle(self, text: str) -> CommandResult:
        query = text.strip().lower()
        query = re.sub(r"^max\s+", "", query).strip()

        if not query:
            return CommandResult(matched=False)

        # Skip messaging
        if any(t in query for t in self.MESSAGING_TRIGGERS):
            return CommandResult(matched=False)

        # Combined commands
        if " and " in query:
            parts = query.split(" and ", 1)
            results = []
            for part in parts:
                result = self._route(part.strip())
                if result.matched and result.response:
                    results.append(result.response)
            if results:
                return CommandResult(matched=True, response=". ".join(results))

        return self._route(query)

    def _route(self, query: str) -> CommandResult:
        # Volume
        if any(t in query for t in self.VOLUME_UP):
            return self._volume("up")
        if any(t in query for t in self.VOLUME_DOWN):
            return self._volume("down")
        if re.search(r"\bunmute\b", query):
            return self._volume("unmute")
        if re.search(r"\bmute\b", query):
            return self._volume("mute")

        # Power
        if any(t in query for t in self.SHUTDOWN):
            return self._power("shutdown")
        if any(t in query for t in self.RESTART):
            return self._power("restart")
        if any(t in query for t in self.LOCK):
            return self._power("lock")
        if any(t in query for t in self.SLEEP):
            return self._power("sleep")

        # Close
        close_match = re.match(r"^(close|kill|exit|quit|terminate)\s+(.+)", query)
        if close_match:
            return self._close_app(close_match.group(2).strip())

        # ✅ Search — ALWAYS goes to Google, never file manager
        search_match = re.match(r"^(search|search for|google|look up)\s+(.+)", query)
        if search_match:
            return self._google_search(search_match.group(2).strip())

        # Play YouTube
        play_match = re.match(r"^(play|put on|stream)\s+(.+)", query)
        if play_match:
            return self._play_youtube(play_match.group(2).strip())

        # ✅ Folder open — check BEFORE app open
        open_folder_match = re.match(
            r"^(?:open|go to|show me|navigate to|take me to)\s+(?:my\s+)?(.+)", query)
        if open_folder_match:
            target = open_folder_match.group(1).strip()
            # Strip "folder" suffix
            target = re.sub(r"\s*(folder|directory)$", "", target).strip()
            folder_result = self._open_folder(target)
            if folder_result.matched:
                return folder_result
            # Not a folder — try as app
            return self._open_app(target)

        # Direct app name match
        for app_key in sorted(self.APP_MAP.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(app_key)}\b", query):
                if app_key == "whatsapp" and any(
                        t in query for t in ["send", "message", "text", "msg"]):
                    return CommandResult(matched=False)
                return self._open_app(app_key)

        return CommandResult(matched=False)

    def _open_app(self, app_name: str) -> CommandResult:
        app_key = app_name.strip().lower()
        target = self.APP_MAP.get(app_key)

        if not target:
            # Partial match
            for key, val in sorted(self.APP_MAP.items(), key=lambda x: len(x[0]), reverse=True):
                if app_key in key or key in app_key:
                    target = val
                    app_key = key
                    break

        if not target:
            return CommandResult(matched=False)

        try:
            if target.startswith("http"):
                webbrowser.open(target)
            elif target.startswith("ms-"):
                os.startfile(target)
            elif target.startswith("shell:"):
                subprocess.Popen(["explorer", target])
            elif os.path.isabs(target):
                if os.path.exists(target):
                    subprocess.Popen([target], shell=False)
                else:
                    return CommandResult(matched=True,
                        response=f"Can't find {app_key}. Check the path.")
            else:
                subprocess.Popen(target, shell=True)
            return CommandResult(matched=True, response=f"Opening {app_key}.")
        except Exception:
            return CommandResult(matched=True, response=f"Couldn't open {app_key}.")

    def _close_app(self, app_name: str) -> CommandResult:
        name_map = {
            "chrome": "chrome.exe", "edge": "msedge.exe",
            "notepad": "notepad.exe", "vscode": "code.exe",
            "vs code": "code.exe", "spotify": "spotify.exe",
            "discord": "discord.exe", "whatsapp": "whatsapp.exe",
            "calculator": "calculator.exe", "paint": "mspaint.exe",
        }
        exe = name_map.get(app_name.lower(), app_name + ".exe")
        try:
            subprocess.Popen(["taskkill", "/f", "/im", exe],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return CommandResult(matched=True, response=f"Closing {app_name}.")
        except Exception:
            return CommandResult(matched=True, response=f"Couldn't close {app_name}.")

    def _open_folder(self, folder_name: str) -> CommandResult:
        key = folder_name.strip().lower()
        path = self.FOLDER_MAP.get(key)
        if not path:
            return CommandResult(matched=False)
        try:
            os.startfile(path)
            return CommandResult(matched=True, response=f"Opening {key}.")
        except Exception:
            return CommandResult(matched=True, response=f"Couldn't open {key}.")

    def _volume(self, action: str) -> CommandResult:
        key_map = {"mute": "[char]173", "unmute": "[char]173",
                   "up": "[char]175", "down": "[char]174"}
        char = key_map.get(action)
        if not char:
            return CommandResult(matched=True, response="Volume command not recognized.")
        try:
            repeat = 5 if action in ("up", "down") else 1
            for _ in range(repeat):
                subprocess.Popen(
                    ["powershell", "-c",
                     f"$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys({char})"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            label = {"mute": "Muted", "unmute": "Unmuted",
                     "up": "Volume increased", "down": "Volume decreased"}
            return CommandResult(matched=True, response=f"{label[action]}.")
        except Exception:
            return CommandResult(matched=True, response="Couldn't control volume.")

    def _power(self, action: str) -> CommandResult:
        try:
            if action == "shutdown":
                self._delayed_run(["shutdown", "/s", "/t", "5"])
            elif action == "restart":
                self._delayed_run(["shutdown", "/r", "/t", "5"])
            elif action == "lock":
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
                return CommandResult(matched=True, response="Screen locked.")
            elif action == "sleep":
                subprocess.Popen(
                    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                return CommandResult(matched=True, response="Going to sleep.")
            return CommandResult(matched=True, response=f"{action.capitalize()} initiated.")
        except Exception:
            return CommandResult(matched=True, response=f"Couldn't {action} system.")

    def _delayed_run(self, command: list) -> None:
        def run():
            import time
            time.sleep(2)
            subprocess.Popen(command)
        threading.Thread(target=run, daemon=True).start()

    def _google_search(self, term: str) -> CommandResult:
        if not term:
            return CommandResult(matched=True, response="Say what to search.")
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(term)}")
        return CommandResult(matched=True, response=f"Searching for {term}.")

    def _play_youtube(self, term: str) -> CommandResult:
        if not term:
            return CommandResult(matched=True, response="Say what to play.")
        try:
            import pywhatkit
            pywhatkit.playonyt(term)
            return CommandResult(matched=True, response=f"Playing {term}.")
        except Exception:
            webbrowser.open(
                f"https://www.youtube.com/results?search_query={quote_plus(term)}")
            return CommandResult(matched=True, response=f"Opening YouTube for {term}.")