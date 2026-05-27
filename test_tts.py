# save as test_tts.py
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from text_to_speech import TextToSpeech
tts = TextToSpeech(voice="en-IN-NeerjaNeural")
tts.speak_async("Hello I am MAX. Testing voice output.")
import time
time.sleep(5)
