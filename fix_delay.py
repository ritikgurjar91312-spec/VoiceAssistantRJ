import sys
import re

# 1. Update app.py
with open('app.py', 'r') as f:
    app_code = f.read()

app_code = app_code.replace(
    'text = self.core.voice.listen_with_mic(source, timeout=10, phrase_time_limit=15, pause_threshold=1.0)',
    'text = self.core.voice.listen_with_mic(source, timeout=10, phrase_time_limit=15, pause_threshold=0.5)'
)

with open('app.py', 'w') as f:
    f.write(app_code)

# 2. Update jarvis_core.py
with open('jarvis_core.py', 'r') as f:
    core_code = f.read()

speak_pattern = r'    def speak\(self, text\):.*?    def listen\(self, timeout=5\):'

new_speak = '''    def speak(self, text):
        import re
        import threading
        import queue
        
        sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if s.strip()]
        if not sentences:
            return

        q = queue.Queue()

        async def _generate_audio(sentence, index):
            communicate = edge_tts.Communicate(sentence, self.voice_name, rate=self.voice_rate)
            temp_file = tempfile.mktemp(suffix=f"_{index}.mp3")
            await communicate.save(temp_file)
            return temp_file

        def producer():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for i, sentence in enumerate(sentences):
                try:
                    f = loop.run_until_complete(_generate_audio(sentence, i))
                    q.put(f)
                except Exception as e:
                    print(f"TTS Gen Error: {e}")
            q.put(None)
            loop.close()

        threading.Thread(target=producer, daemon=True).start()

        while True:
            file_to_play = q.get()
            if file_to_play is None:
                break
            try:
                ctypes.windll.winmm.mciSendStringW(f'open "{file_to_play}" type mpegvideo alias myaudio', None, 0, None)
                ctypes.windll.winmm.mciSendStringW('play myaudio wait', None, 0, None)
                ctypes.windll.winmm.mciSendStringW('close myaudio', None, 0, None)
                os.remove(file_to_play)
            except Exception as e:
                pass

    def listen(self, timeout=5):'''

core_code = re.sub(speak_pattern, new_speak, core_code, flags=re.DOTALL)

with open('jarvis_core.py', 'w') as f:
    f.write(core_code)

print("Delay fixes applied")
