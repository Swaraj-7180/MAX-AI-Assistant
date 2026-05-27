from datetime import datetime, timedelta
import pywhatkit

send_time = datetime.now() + timedelta(minutes=1)
print(f"Sending at {send_time.hour}:{send_time.minute:02d}")
pywhatkit.sendwhatmsg("+919881632692", "hi", send_time.hour, send_time.minute, wait_time=20, tab_close=True)