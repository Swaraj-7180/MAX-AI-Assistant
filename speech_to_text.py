import speech_recognition as sr
import threading
import time


class SpeechToText:
    def __init__(self, energy_threshold: int = 300, pause_threshold: float = 1.2) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold

        # ✅ Longer pause — waits more before cutting off speech
        self.recognizer.pause_threshold = 1.2
        self.recognizer.non_speaking_duration = 0.8

        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5  # ✅ Lower ratio — less aggressive cutoff
        self.recognizer.operation_timeout = 15

        self._lock = threading.Lock()
        self.microphone = sr.Microphone()
        self._last_heard = ""
        self._last_heard_time = 0.0

        print("[MAX] Calibrating mic — please be silent...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)

        # ✅ Floor — never drop below 100
        if self.recognizer.energy_threshold < 100:
            self.recognizer.energy_threshold = 100

        print(f"[MAX] Mic calibrated. Energy threshold: {self.recognizer.energy_threshold:.1f}")

    def _enforce_floor(self) -> None:
        if self.recognizer.energy_threshold < 100:
            self.recognizer.energy_threshold = 100

    def listen_once(self, timeout: float = 5, phrase_time_limit: float = 12) -> str | None:
        self._enforce_floor()
        with self._lock:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_time_limit  # ✅ 12s — full sentence time
                    )
                try:
                    # ✅ Use en-US for better accuracy — Google STT is more accurate in en-US
                    # en-IN causes more mishearing of commands like "Believer", "downloads"
                    text = self.recognizer.recognize_google(audio, language="en-US")

                    if not text or len(text.strip()) < 2:
                        return None

                    text = text.strip()

                    # ✅ Duplicate suppression — ignore same phrase within 3 seconds
                    now = time.time()
                    if text.lower() == self._last_heard.lower() and (now - self._last_heard_time) < 3:
                        print(f"[MAX] Duplicate ignored: '{text}'")
                        return None

                    self._last_heard = text
                    self._last_heard_time = now
                    return text

                except sr.UnknownValueError:
                    return None
                except sr.RequestError as e:
                    print(f"[STT] Google API error: {e}")
                    return None

            except sr.WaitTimeoutError:
                return None
            except OSError:
                try:
                    self.microphone = sr.Microphone()
                except Exception:
                    pass
                return None
            except Exception as e:
                print(f"[STT] Error: {e}")
                return None