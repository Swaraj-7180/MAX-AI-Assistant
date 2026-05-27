import json
import os
import re
from datetime import datetime
from typing import Optional
from groq import Groq


BRAIN_FILE = r"D:\MAX_AI\second_brain.json"

# ── AI CLIENT ────────────────────────────────────────
def _get_client():
    return Groq(api_key="Groq api key")


class SecondBrain:
    def __init__(self, say_callback) -> None:
        self.say = say_callback
        self.memories = self._load()
        

    # ── STORAGE ──────────────────────────────────────
    def _load(self) -> list:
        try:
            if os.path.exists(BRAIN_FILE):
                with open(BRAIN_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save(self) -> None:
        try:
            with open(BRAIN_FILE, "w") as f:
                json.dump(self.memories, f, indent=2)
        except Exception:
            pass

    # ── MAIN HANDLER ─────────────────────────────────
    def handle(self, text: str) -> Optional[str]:
        query = text.strip().lower()

        # Remember triggers
        # Remember triggers — more flexible
        remember_match = re.search(
            r"\b(remember|note that|save this|store this|keep in mind|don't forget|log this)\b.+",
        query
        )
        if remember_match:
            content = re.sub(
                r"^(remember|note|save|store|keep in mind|don't forget|log)\s+(that\s+)?",
                "", query
            ).strip()
            if content:
                return self._store_memory(content, text)

        # Recall triggers
        recall_match = re.search(
            r"\b(what did i|do you remember|recall|remind me about|what was|"
            r"when did i|what is my|look up my)\b.+", query
        )
        if recall_match:
            return self._recall_memory(text)

        # Show all
        if re.search(r"\b(show|list|all)\s+(my\s+)?(memories|notes|brain)\b", query):
            return self._show_all()

        # Delete
        delete_match = re.search(r"\b(forget|delete|remove)\b\s+(.+)", query)
        if delete_match:
            return self._delete_memory(delete_match.group(2).strip())

        return None

    # ── STORE ────────────────────────────────────────
    def _store_memory(self, content: str, original: str) -> str:
        # Use AI to extract category and clean content
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Extract and clean this memory for storage. "
                        f"Return JSON only with keys: 'content' (clean version), 'category' "
                        f"(one of: personal, work, deadline, idea, fact, password, other). "
                        f"Memory: '{content}'. "
                        f"Example: {{\"content\": \"Project deadline is May 10\", \"category\": \"deadline\"}}"
                    )
                }],
                max_tokens=100
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            clean_content = parsed.get("content", content)
            category = parsed.get("category", "other")
        except Exception:
            clean_content = content
            category = "other"

        memory = {
            "id": len(self.memories) + 1,
            "content": clean_content,
            "original": original,
            "category": category,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "date_human": datetime.now().strftime("%B %d, %Y at %I:%M %p")
        }
        self.memories.append(memory)
        self._save()
        return f"Got it. Stored in your second brain under {category}."

    # ── RECALL ───────────────────────────────────────
    def _recall_memory(self, query: str) -> str:
        if not self.memories:
            return "Your second brain is empty. Start telling me things to remember."

        # Use AI to find most relevant memory
        try:
            client = _get_client()
            memories_text = "\n".join([
                f"[{m['id']}] ({m['category']}) {m['content']} — saved on {m['date_human']}"
                for m in self.memories
            ])
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{
                    "role": "user",
                    "content": (
                        f"The user is asking: '{query}'\n\n"
                        f"Here are all stored memories:\n{memories_text}\n\n"
                        f"Find the most relevant memory and answer the user's question naturally "
                        f"in 1-2 sentences. If nothing matches say 'I don't have that stored.' "
                        f"Be direct and conversational."
                    )
                }],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception:
            # Fallback — simple keyword search
            query_words = query.lower().split()
            for memory in reversed(self.memories):
                if any(w in memory["content"].lower() for w in query_words):
                    return f"I have this stored: {memory['content']} — saved on {memory['date_human']}."
            return "I don't have anything stored about that."

    # ── SHOW ALL ─────────────────────────────────────
    def _show_all(self) -> str:
        if not self.memories:
            return "Your second brain is empty."
        count = len(self.memories)
        categories = {}
        for m in self.memories:
            categories[m["category"]] = categories.get(m["category"], 0) + 1
        summary = ", ".join([f"{v} {k}" for k,v in categories.items()])
        return f"You have {count} memories stored — {summary}. What do you want to find?"

    # ── DELETE ───────────────────────────────────────
    def _delete_memory(self, keyword: str) -> str:
        before = len(self.memories)
        self.memories = [
            m for m in self.memories
            if keyword.lower() not in m["content"].lower()
        ]
        deleted = before - len(self.memories)
        self._save()
        if deleted:
            return f"Deleted {deleted} memory about {keyword}."
        return f"No memory found about {keyword}."