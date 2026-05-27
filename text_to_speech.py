import queue
import re
import tempfile
import threading
import asyncio
from pathlib import Path

import edge_tts
import pygame


class TextToSpeech:

    def __init__(
        self,
        voice: str = "en-IN-NeerjaNeural",
        rate: str = "+8%",
        volume: str = "+0%",
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self._speak_queue: queue.Queue[str] = queue.Queue()

        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        print("[TTS] Ready.")

    def is_speaking(self) -> bool:
        return pygame.mixer.music.get_busy()

    def clear_queue(self) -> None:
        """Drain any queued speech — call this to interrupt MAX mid-sentence."""
        try:
            while True:
                self._speak_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    @staticmethod
    def clean_text(text: str) -> str:
        cleaned = re.sub(r"^(assistant|user)\s*:\s*", "", text.strip(), flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def speak_async(self, text: str) -> None:
        cleaned = self.clean_text(text)
        if cleaned:
            # ✅ Clear any pending queued speech so new reply plays immediately
            self.clear_queue()
            self._speak_queue.put(cleaned)
            print(f"[TTS] Queued: '{cleaned[:50]}'")

    async def _synthesize(self, text: str, out_file: Path) -> None:
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
        )
        await communicate.save(str(out_file))

    def _worker_loop(self) -> None:
        while True:
            text = None
            tmp_path = None
            try:
                text = self._speak_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".mp3") as tmp:
                    tmp_path = Path(tmp.name)

                print(f"[TTS] Synthesizing: '{text[:40]}'")

                future = asyncio.run_coroutine_threadsafe(
                    self._synthesize(text=text, out_file=tmp_path),
                    self._loop
                )

                try:
                    future.result(timeout=20)
                except asyncio.TimeoutError:
                    print("[TTS] Synthesis timed out — skipping")
                    continue
                except Exception as e:
                    print(f"[TTS] Synthesis error: {e}")
                    continue

                if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                    print("[TTS] Empty audio file — skipping")
                    continue

                print("[TTS] Playing audio...")
                pygame.mixer.music.load(str(tmp_path))
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    threading.Event().wait(0.05)

                threading.Event().wait(0.2)
                print("[TTS] Done.")

            except Exception as e:
                print(f"[TTS ERROR] {e}")
            finally:
                try:
                    if tmp_path and tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass