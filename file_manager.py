import os
import re
import shutil
import threading
from datetime import datetime
from typing import Optional


# Known apps — skip these so commands.py handles them
KNOWN_APPS = {
    "chrome", "edge", "firefox", "notepad", "calculator", "calc",
    "paint", "explorer", "settings", "task manager", "cmd", "powershell",
    "terminal", "vscode", "vs code", "code", "cursor", "spotify",
    "whatsapp", "discord", "anaconda", "ollama", "tradingview",
    "trading view", "youtube", "gmail", "github", "linkedin",
    "instagram", "chatgpt", "chat gpt", "claude", "claude ai",
    "hotstar", "jio hotstar", "jiohotstar", "whatsapp web",
    "word", "excel", "powerpoint", "vlc", "telegram", "opera",
}

# ✅ Junk folders to skip during file search
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", "venv", "env",
    "site-packages", "AppData", "Windows", "System32",
    "Lib", "lib", "Include", "Scripts", "dist-info",
    "dist", "build", ".idea", ".vscode",
}


class FileManager:
    def __init__(self, say_callback) -> None:
        self.say = say_callback

        self.CATEGORIES = {
            "Images":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
            "Videos":      [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
            "Audio":       [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
            "Documents":   [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md"],
            "Sheets":      [".xls", ".xlsx", ".csv", ".ods"],
            "Slides":      [".ppt", ".pptx", ".odp"],
            "Code":        [".py", ".js", ".html", ".css", ".cpp", ".c", ".java",
                           ".ts", ".json", ".xml", ".yaml", ".yml", ".sql", ".php"],
            "Archives":    [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
            "Executables": [".exe", ".msi", ".bat", ".sh"],
        }

        # ✅ Only search user folders — not deep system/project dirs
        self.SEARCH_ROOTS = [
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Downloads"),
            os.path.expanduser("~\\Pictures"),
            os.path.expanduser("~\\Videos"),
            os.path.expanduser("~\\Music"),
        ]

    def handle(self, text: str) -> Optional[str]:
        query = text.strip().lower()

        # ✅ Skip known apps — let commands.py handle them
        for app in KNOWN_APPS:
            if re.search(rf"\b(open|launch|start)\s+{re.escape(app)}\b", query):
                return None

        # Organize folder
        if re.search(r"\b(organize|sort|clean up|tidy)\s+(my\s+)?(downloads|desktop|documents)\b", query):
            folder_match = re.search(r"\b(downloads|desktop|documents)\b", query)
            folder = folder_match.group(1) if folder_match else "downloads"
            threading.Thread(target=self._organize_folder, args=(folder,), daemon=True).start()
            return f"Organizing your {folder} folder. I'll let you know when done."

        # Find all files of a type
        type_match = re.search(r"\bfind\s+all\s+(.+?)\s+files?\b", query)
        if type_match:
            file_type = type_match.group(1).strip()
            threading.Thread(target=self._find_by_type, args=(file_type,), daemon=True).start()
            return f"Searching for all {file_type} files."

        # ✅ ONLY "find", "locate", "where is" trigger file search
        # "search" is REMOVED — that goes to Google via commands.py
        find_match = re.search(r"\b(find|locate|where is)\s+(?:my\s+)?(.+)", query)
        if find_match:
            filename = find_match.group(2).strip()
            # Clean noise words
            filename = re.sub(r"\b(file|document|folder|my|the|a|an|resume|cv)\b", "", filename).strip()
            # ✅ Only search if filename is meaningful (3+ chars)
            if len(filename) >= 3:
                threading.Thread(target=self._find_file, args=(filename,), daemon=True).start()
                return f"Searching for {filename} on your PC."

        return None

    def _find_file(self, filename: str) -> None:
        filename_lower = filename.lower().strip()
        found = []

        for root in self.SEARCH_ROOTS:
            if not os.path.exists(root):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    # ✅ Skip junk directories
                    dirnames[:] = [
                        d for d in dirnames
                        if d not in SKIP_DIRS and not d.startswith(".")
                    ]
                    for fname in filenames:
                        fname_lower = fname.lower()
                        # ✅ Only match actual user files — skip .py .dll .pima etc system files
                        ext = os.path.splitext(fname_lower)[1]
                        if ext in {".py", ".dll", ".pima", ".pimx", ".sig", ".pyd",
                                   ".so", ".c", ".h", ".hpp", ".obj", ".lib", ".exp"}:
                            continue
                        if filename_lower in fname_lower:
                            found.append(os.path.join(dirpath, fname))
                        if len(found) >= 5:
                            break
                    if len(found) >= 5:
                        break
            except PermissionError:
                continue

        if not found:
            self.say(f"Couldn't find {filename} in your common folders.")
            return

        if len(found) == 1:
            self.say(f"Found {os.path.basename(found[0])}. Opening it now.")
            os.startfile(found[0])
        else:
            best = found[0]
            self.say(f"Found {len(found)} matches. Opening the best one — {os.path.basename(best)}.")
            os.startfile(best)
            print("[MAX] All matches found:")
            for f in found:
                print(f"  → {f}")

    def _find_by_type(self, file_type: str) -> None:
        type_map = {
            "python": ".py", "pdf": ".pdf", "image": ".jpg",
            "photo": ".jpg", "video": ".mp4", "audio": ".mp3",
            "music": ".mp3", "word": ".docx", "excel": ".xlsx",
            "powerpoint": ".pptx", "zip": ".zip", "text": ".txt",
            "javascript": ".js", "html": ".html", "css": ".css",
        }

        ext = type_map.get(file_type.lower(), f".{file_type.lower()}")
        found = []

        for root in self.SEARCH_ROOTS:
            if not os.path.exists(root):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                    for fname in filenames:
                        if fname.lower().endswith(ext):
                            found.append(os.path.join(dirpath, fname))
                        if len(found) >= 20:
                            break
                    if len(found) >= 20:
                        break
            except PermissionError:
                continue

        if not found:
            self.say(f"No {file_type} files found in your common folders.")
            return

        print(f"\n[MAX] Found {len(found)} {file_type} files:")
        for f in found:
            print(f"  → {f}")

        folder = os.path.dirname(found[0])
        self.say(f"Found {len(found)} {file_type} files. Opening the folder.")
        os.startfile(folder)

    def _organize_folder(self, folder_name: str) -> None:
        folder_paths = {
            "downloads": os.path.expanduser("~\\Downloads"),
            "desktop":   os.path.expanduser("~\\Desktop"),
            "documents": os.path.expanduser("~\\Documents"),
        }

        folder_path = folder_paths.get(folder_name)
        if not folder_path or not os.path.exists(folder_path):
            self.say(f"Couldn't find the {folder_name} folder.")
            return

        moved = 0
        skipped = 0

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isdir(file_path) or filename.startswith("."):
                continue

            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            category = "Others"
            for cat, extensions in self.CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break

            dest_folder = os.path.join(folder_path, category)
            os.makedirs(dest_folder, exist_ok=True)
            dest_path = os.path.join(dest_folder, filename)

            if os.path.exists(dest_path):
                name, extension = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%H%M%S")
                dest_path = os.path.join(dest_folder, f"{name}_{timestamp}{extension}")

            try:
                shutil.move(file_path, dest_path)
                moved += 1
            except PermissionError:
                skipped += 1
            except Exception:
                pass

        if moved == 0:
            self.say(f"Your {folder_name} is already clean or has no files to organize.")
        else:
            self.say(f"Done! Organized {moved} files in your {folder_name}.")