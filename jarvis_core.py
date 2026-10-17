import os
import time
import base64
import speech_recognition as sr
import cv2
import webbrowser
import edge_tts
import asyncio
import tempfile
import ctypes
from pymongo import MongoClient
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

class MongoDBManager:
    def __init__(self):
        uri = os.environ.get("MONGODB_URI", "")
        self.client = None
        self.db = None
        self.fallback_tasks = []
        self.fallback_memory = []
        self.use_fallback = False
        
        if uri:
            # Configure dnspython with resilient public DNS servers to prevent timeouts on systems with custom/NextDNS servers
            try:
                import dns.resolver
                res = dns.resolver.Resolver(configure=False)
                res.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4', '1.0.0.1']
                res.timeout = 5.0
                res.lifetime = 10.0
                dns.resolver.default_resolver = res
            except Exception:
                pass

            try:
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
                self.client.server_info() # trigger exception if cannot connect
                self.db = self.client.rk_db
                print("MongoDB Atlas connected successfully.")
            except Exception as e:
                # If SRV lookup timed out or failed and cluster host is ritik.yw4fow7.mongodb.net, fallback to direct replica set
                connected_fallback = False
                if "ritik.yw4fow7.mongodb.net" in uri and uri.startswith("mongodb+srv://") and "@" in uri:
                    try:
                        auth_part = uri.split("://", 1)[1].split("@", 1)[0]
                        direct_uri = f"mongodb://{auth_part}@ac-wweuykx-shard-00-00.yw4fow7.mongodb.net:27017,ac-wweuykx-shard-00-01.yw4fow7.mongodb.net:27017,ac-wweuykx-shard-00-02.yw4fow7.mongodb.net:27017/?ssl=true&replicaSet=atlas-qs48bo-shard-0&authSource=admin&retryWrites=true&w=majority"
                        self.client = MongoClient(direct_uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
                        self.client.server_info()
                        self.db = self.client.rk_db
                        print("MongoDB Atlas connected successfully (via direct replica set fallback).")
                        connected_fallback = True
                    except Exception:
                        pass
                
                if not connected_fallback:
                    print(f"MongoDB connection failed: {e}. Using in-memory fallback.")
                    self.use_fallback = True
        else:
            print("No MONGODB_URI found in .env. Using in-memory fallback.")
            self.use_fallback = True

    def get_tasks(self):
        if self.use_fallback: return self.fallback_tasks
        return list(self.db.tasks.find({}, {"_id": 0}))

    def add_task(self, task_text, due_at=None):
        if self.use_fallback:
            self.fallback_tasks.append({"text": task_text, "done": False, "due_at": due_at})
            return
        task = {"text": task_text, "done": False, "due_at": due_at}
        self.db.tasks.insert_one(task)

    def complete_task(self, task_text):
        if self.use_fallback:
            for t in self.fallback_tasks:
                if task_text.lower() in t["text"].lower():
                    t["done"] = True
            return
        self.db.tasks.update_many({"text": {"$regex": task_text, "$options": "i"}}, {"$set": {"done": True}})

    def delete_task(self, task_text):
        if self.use_fallback:
            self.fallback_tasks = [t for t in self.fallback_tasks if task_text.lower() not in t["text"].lower()]
            return
        self.db.tasks.delete_many({"text": {"$regex": task_text, "$options": "i"}})

    def get_memory(self):
        if self.use_fallback: return self.fallback_memory
        return [m["fact"] for m in self.db.memory.find({}, {"_id": 0})]

    def add_memory(self, fact):
        if self.use_fallback:
            self.fallback_memory.append(fact)
            return
        self.db.memory.insert_one({"fact": fact})


class SoundDeviceMicrophone(sr.AudioSource):
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2
        self.stream_obj = None
        self._stream_wrapper = None
        self.q = None

    def __enter__(self):
        import sounddevice as sd
        import queue
        self.q = queue.Queue(maxsize=80)
        
        def callback(indata, frames, time, status):
            data = bytes(indata)
            try:
                self.q.put_nowait(data)
            except queue.Full:
                # Discard stale chunk so audio stays completely real-time
                try:
                    self.q.get_nowait()
                except Exception:
                    pass
                try:
                    self.q.put_nowait(data)
                except Exception:
                    pass
                    
        self.stream_obj = sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.CHUNK,
            channels=1,
            dtype='int16',
            callback=callback
        )
        self.stream_obj.start()

        class _Stream:
            def __init__(self, q):
                self.q = q
            def read(self, size):
                try:
                    return self.q.get(timeout=3)
                except Exception:
                    return b'\x00' * 1024

        self._stream_wrapper = _Stream(self.q)
        return self

    def clear_buffer(self):
        """Discards any accumulated audio so recognition starts in true real-time"""
        if self.q is not None:
            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except Exception:
                    break

    def __exit__(self, exc_type, exc_value, traceback):
        if self.stream_obj:
            try:
                self.stream_obj.stop()
                self.stream_obj.close()
            except Exception:
                pass

    @property
    def stream(self):
        return self._stream_wrapper

class VoiceManager:
    VOICE_MAP = {
        0: "hi-IN-MadhurNeural",            # Human Male (Hindi/Hinglish/English) - natural, warm, conversational
        1: "hi-IN-SwaraNeural",             # Human Female (Hindi/Hinglish/English) - sweet, polite, natural
        2: "en-US-ChristopherNeural",       # Jarvis Male (Deep, clear, cinematic AI)
        3: "en-IN-NeerjaExpressiveNeural",  # Expressive Female (Indian English)
        4: "en-US-AndrewMultilingualNeural" # Multilingual Male (Global English)
    }

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 240
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.5
        self.recognizer.non_speaking_duration = 0.4
        self.stt_language = "en-IN"
        self.voice_name = "hi-IN-MadhurNeural" # Ultra-realistic, natural human Indian male voice
        self.voice_rate = "+0%"
        self.voice_pitch = "+0Hz"
        self.is_speaking = False
        self.on_speech_start = None
        self.on_speech_stop = None
        self._pygame_ready = False
        self._init_audio_engine()

    def _init_audio_engine(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
            self._pygame_ready = True
        except Exception as e:
            print("[AUDIO] Pygame mixer init notice:", e)
            self._pygame_ready = False

    def _play_audio_file(self, file_path):
        """Ultra-low-latency, crystal-clear audio playback engine with multiple layers of fallback"""
        if not file_path or not os.path.exists(file_path):
            return False

        # Layer 1: Pygame Mixer (Direct low-latency hardware playback)
        if self._pygame_ready:
            try:
                import pygame
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.is_speaking:
                    time.sleep(0.03)
                try: pygame.mixer.music.unload()
                except Exception: pass
                return True
            except Exception as e:
                print("[AUDIO] Pygame playback error, attempting fallback:", e)

        # Layer 2: Windows PresentationCore MediaPlayer (Native Windows Media Foundation)
        try:
            import subprocess
            p_abs = os.path.abspath(file_path)
            ps_script = (
                f'Add-Type -AssemblyName presentationCore; '
                f'$m = New-Object System.Windows.Media.MediaPlayer; '
                f'$m.Open("{p_abs}"); $m.Play(); '
                f'while ($m.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 20 }}; '
                f'Start-Sleep -Milliseconds ([int]$m.NaturalDuration.TimeSpan.TotalMilliseconds + 50); '
                f'$m.Close()'
            )
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                           capture_output=True, timeout=30)
            return True
        except Exception as e:
            print("[AUDIO] PowerShell MediaPlayer fallback error:", e)

        # Layer 3: Legacy MCI
        try:
            alias = f"myaudio_{os.getpid()}_{int(time.time()*1000)%10000}"
            ctypes.windll.winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias {alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)
            return True
        except Exception as e:
            print("[AUDIO] MCI error:", e)
            return False

    def _clean_for_speech(self, text):
        import re
        if not text:
            return ""
        # Remove ACTION tags completely
        text = re.sub(r'ACTION:\s*[A-Z_]+\s*\(.*?\)', '', text, flags=re.IGNORECASE)
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove markdown headers and emphasis
        text = re.sub(r'[*_~#]+', '', text)
        # Remove bullet dashes
        text = re.sub(r'(?m)^[\s\-*•]+\s*', '', text)
        # Remove emojis and unusual unicode symbols
        text = re.sub(r'[^\w\s.,?!;:/\-\'\"]', '', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def set_voice(self, voice_index, rate=150):
        try:
            v_idx = int(voice_index)
            if v_idx in self.VOICE_MAP:
                self.voice_name = self.VOICE_MAP[v_idx]
            elif v_idx == 1:
                self.voice_name = "hi-IN-SwaraNeural"
            elif v_idx == 2:
                self.voice_name = "en-US-ChristopherNeural"
            else:
                self.voice_name = "hi-IN-MadhurNeural"
                
            # rate: 150 is normal (0%)
            diff = int(rate) - 150
            if diff >= 0:
                self.voice_rate = f"+{diff}%"
            else:
                self.voice_rate = f"{diff}%"
        except Exception as e:
            print(f"Error setting voice: {e}")

    def play_wake_prompt(self):
        """Plays the pre-cached 'Kya command hai boss?' instantly from disk with zero network delay."""
        self.is_speaking = True
        if callable(self.on_speech_start):
            try: self.on_speech_start()
            except Exception: pass

        try:
            is_female = ("Swara" in self.voice_name or "Neerja" in self.voice_name)
            filename = "wake_prompt_female.mp3" if is_female else "wake_prompt_male.mp3"
            full_path = os.path.abspath(filename)
            
            played = False
            if os.path.exists(full_path):
                played = self._play_audio_file(full_path)
            
            if not played:
                self.speak("Kya command hai boss?")
        except Exception as e:
            print("Prompt playback error:", e)
            try:
                self.speak("Kya command hai boss?")
            except Exception:
                pass
        finally:
            self.is_speaking = False
            if callable(self.on_speech_stop):
                try: self.on_speech_stop()
                except Exception: pass

    def speak(self, text):
        import re
        import threading
        import queue
        
        clean_text = self._clean_for_speech(text)
        if not clean_text:
            return

        self.is_speaking = True
        if callable(self.on_speech_start):
            try: self.on_speech_start()
            except Exception: pass

        has_played = False
        try:
            # Natural prosody chunking:
            # For short to moderate responses (<= 250 chars, almost all AI conversational responses),
            # synthesize the entire text in one single go!
            # Edge-TTS neural model delivers ultra-smooth human breathing, realistic cadence, and tone modulation.
            if len(clean_text) <= 250:
                chunks = [clean_text]
            else:
                # For longer responses, break naturally at full sentence endings
                raw_sentences = re.split(r'(?<=[.!?\n])\s+', clean_text)
                chunks = []
                cur = ""
                for s in raw_sentences:
                    s = s.strip()
                    if not s: continue
                    if len(cur) + len(s) < 200:
                        cur = f"{cur} {s}".strip()
                    else:
                        if cur: chunks.append(cur)
                        cur = s
                if cur: chunks.append(cur)

            q = queue.Queue()

            async def _generate_audio(sentence, index):
                communicate = edge_tts.Communicate(sentence, self.voice_name, rate=self.voice_rate, pitch=self.voice_pitch)
                temp_file = tempfile.mktemp(suffix=f"_tts_{index}.mp3")
                await communicate.save(temp_file)
                return temp_file

            def producer():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                for i, sentence in enumerate(chunks):
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
                ok = self._play_audio_file(file_to_play)
                if ok:
                    has_played = True
                try:
                    os.remove(file_to_play)
                except Exception:
                    pass

            if not has_played:
                # Offline fallback using pyttsx3 only if edge-tts failed completely
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 160)
                    engine.say(clean_text)
                    engine.runAndWait()
                except Exception as ex:
                    print("pyttsx3 fallback error:", ex)
        finally:
            self.is_speaking = False
            if callable(self.on_speech_stop):
                try: self.on_speech_stop()
                except Exception: pass

    def listen(self, timeout=5):
        try:
            with SoundDeviceMicrophone() as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
                text = self.recognizer.recognize_google(audio, language=self.stt_language)
                return text
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except Exception as e:
            print(f"Microphone error: {e}")
            return ""

    def get_microphone(self):
        return SoundDeviceMicrophone()

    def listen_with_mic(self, source, timeout=3, phrase_time_limit=6, pause_threshold=0.5):
        try:
            self.recognizer.pause_threshold = pause_threshold
            self.recognizer.non_speaking_duration = 0.4
            
            # Keep threshold locked to high sensitivity so it never drifts to deafness
            self.recognizer.dynamic_energy_threshold = False
            if self.recognizer.energy_threshold < 180 or self.recognizer.energy_threshold > 500:
                self.recognizer.energy_threshold = 240

            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            # Direct recognition with en-IN (captures English, Hinglish, and common Hindi phrases)
            text = self.recognizer.recognize_google(audio, language=self.stt_language)
            if text:
                print(f"[VOICE HEARD]: {text}")
                return text.lower()
            return ""
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except sr.RequestError as e:
            print("Google STT Request Error:", e)
            return ""
        except Exception as e:
            print("Microphone listen error:", e)
            return ""


class VisionManager:
    def __init__(self):
        pass

    def capture_image_base64(self):
        # 0 is usually the built-in webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        
        # Read a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return None
        
        # Convert to jpeg
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return None
            
        # Convert to base64
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        return img_b64

class RKCore:
    def __init__(self):
        self.db = MongoDBManager()
        self.voice = VoiceManager()
        self.vision = VisionManager()
        
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            self.gemini_client = genai.Client(api_key=api_key)
        else:
            self.gemini_client = None
            
        self.chat_history = []
        
        self.system_prompt = """Tum RK ho — ek tez, wafadar, thoda witty personal AI assistant. 
Respond in the exact language the user speaks to you in. If they speak Hindi or Hinglish, reply in Hindi/Hinglish. If they speak English, reply in English. If they command you to speak a specific language, switch to it automatically. Keep answers brief and professional.

Agar user task add/complete/delete karne ko kahe, to apne normal jawab ke bilkul END mein, ek nayi line par, in exact formats mein action likho (multiple ho sakte hain):
ACTION: ADD_TASK("task text")
ACTION: COMPLETE_TASK("matching task text")
ACTION: DELETE_TASK("matching task text")
ACTION: REMIND("task text", minutes_from_now)

Agar user kisi website ya app ko open karne ko kahe (jaise Google, Chrome, etc.):
ACTION: OPEN_WEBSITE("url")

Agar user kisi app, website, browser ya YouTube ko close karne ko kahe (jaise "close youtube", "youtube band karo", "close chrome"):
ACTION: CLOSE_APP("chrome")

Agar user kisi specific gaane ya video ko YouTube par chalane (play karne) ko kahe:
ACTION: PLAY_YOUTUBE("song or video name")

Agar user aawaz ya language badalne ko kahe:
ACTION: SET_LANGUAGE("language_code") 
(Example: en-IN, hi-IN, en-US)
ACTION: SET_VOICE(voice_index, rate)
(Example voice_index: 0 for Human Male (Madhur), 1 for Human Female (Swara), 2 for Jarvis English (Christopher). rate: 150 is normal)

Agar user apne baare mein koi fact batae to:
ACTION: LEARN_FACT("fact text")

Agar user koi code likhne ya autonomous background task run karne ko kahe, to python code likho:
ACTION: RUN_CODE("print('hello world')")

Jawab SHORT rakho. ACTION lines hamesha bilkul last mein.
"""

    def _process_actions(self, raw_text):
        import re
        import threading
        import subprocess

        # Process RUN_CODE separately since it can be multi-line
        code_matches = re.finditer(r'ACTION:\s*RUN_CODE\s*\(\s*(?:("""|\'\'\'|["\'`]))([\s\S]*?)\1\s*\)', raw_text, re.IGNORECASE)
        for m in code_matches:
            code_to_run = m.group(2).replace('\\n', '\n')
            def run_bg(c):
                try:
                    with open("background_job.py", "w", encoding='utf-8') as f:
                        f.write(c)
                    subprocess.Popen(["python", "background_job.py"])
                except Exception as e:
                    print("Error running background code:", e)
            threading.Thread(target=run_bg, args=(code_to_run,), daemon=True).start()
            
        raw_text = re.sub(r'ACTION:\s*RUN_CODE\s*\(\s*(?:("""|\'\'\'|["\'`]))[\s\S]*?\1\s*\)', '', raw_text, flags=re.IGNORECASE)

        lines = raw_text.split('\n')
        kept = []
        for line in lines:
            t = line.strip()
            
            import re
            m = re.match(r'^ACTION:\s*ADD_TASK\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                self.db.add_task(m.group(1))
                continue
                
            m = re.match(r'^ACTION:\s*REMIND\s*\(\s*["\']?(.+?)["\']?\s*,\s*(\d+)\s*\)', t, re.IGNORECASE)
            if m:
                # Store due_at as unix timestamp
                due_at = int(time.time()) + int(m.group(2)) * 60
                self.db.add_task(m.group(1), due_at=due_at)
                continue
                
            m = re.match(r'^ACTION:\s*COMPLETE_TASK\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                self.db.complete_task(m.group(1))
                continue
                
            m = re.match(r'^ACTION:\s*DELETE_TASK\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                self.db.delete_task(m.group(1))
                continue
                
            m = re.match(r'^ACTION:\s*LEARN_FACT\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                self.db.add_memory(m.group(1))
                continue
                
            m = re.match(r'^ACTION:\s*CLOSE_APP\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                app_name = m.group(1).lower().strip()
                import os
                if any(k in app_name for k in ["chrome", "browser", "website", "youtube", "tab", "edge", "video", "yt"]):
                    os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
                    os.system("taskkill /f /im msedge.exe /t >nul 2>&1")
                    os.system("taskkill /f /im brave.exe /t >nul 2>&1")
                elif "notepad" in app_name:
                    os.system("taskkill /f /im notepad.exe /t >nul 2>&1")
                else:
                    if not app_name.endswith(".exe"):
                        app_name += ".exe"
                    os.system(f"taskkill /f /im {app_name} /t >nul 2>&1")
                continue

            m = re.match(r'^ACTION:\s*OPEN_WEBSITE\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                url = m.group(1)
                if not url.startswith('http'):
                    url = 'https://' + url
                webbrowser.open(url)
                continue
                
            m = re.match(r'^ACTION:\s*PLAY_YOUTUBE\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                import urllib.request
                import urllib.parse
                query = urllib.parse.quote(m.group(1))
                try:
                    html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + query)
                    video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html.read().decode())
                    if video_ids:
                        webbrowser.open("https://www.youtube.com/watch?v=" + video_ids[0])
                    else:
                        webbrowser.open("https://www.youtube.com/results?search_query=" + query)
                except Exception as e:
                    webbrowser.open("https://www.youtube.com/results?search_query=" + query)
                continue
                
            m = re.match(r'^ACTION:\s*SET_LANGUAGE\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                self.voice.stt_language = m.group(1)
                continue
                
            m = re.match(r'^ACTION:\s*SET_VOICE\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', t, re.IGNORECASE)
            if m:
                self.voice.set_voice(int(m.group(1)), int(m.group(2)))
                continue
                
            if t.upper().startswith("ACTION:"):
                continue
                
            kept.append(line)
            
        return "\n".join(kept).strip()

    def send_message(self, text, image_b64=None):
        if not self.gemini_client:
            return "GEMINI_API_KEY is missing. Check .env file."
            
        # Get active context
        tasks = self.db.get_tasks()
        active_tasks = [t['text'] for t in tasks if not t.get('done')]
        memory = self.db.get_memory()
        
        context = f"Current active tasks: {', '.join(active_tasks) if active_tasks else '(none)'}\n"
        context += f"User facts: {', '.join(memory) if memory else '(none)'}\n"
        
        full_system = self.system_prompt + "\n" + context

        # Note: Gemini uses different history format, but for simple integration, we can combine context.
        # It's better to use chat sessions if we want native history, but here we just pass the text.
        
        prompt = full_system + "\n\nChat History:\n"
        for m in self.chat_history:
            prompt += f"{m['role'].capitalize()}: {m['content']}\n"
            
        prompt += f"\nUser: {text}"
        
        contents = [prompt]
        if image_b64:
            try:
                from google.genai import types
                image_bytes = base64.b64decode(image_b64)
                contents = [
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
                ]
            except Exception as e:
                print("Image encoding error:", e)

        try:
            from google.genai import types
            models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite', 'gemini-3.8-flash']
            raw_text = None
            last_err = None
            for mod in models_to_try:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=mod,
                        contents=contents,
                        config=types.GenerateContentConfig(automatic_function_calling={"disable": True})
                    )
                    raw_text = response.text
                    if raw_text:
                        break
                except Exception as e:
                    last_err = e
                    continue

            if not raw_text:
                if last_err:
                    return f"Error communicating with Gemini API: {last_err}"
                return "No response received from Gemini."
            
            clean_text = self._process_actions(raw_text)
            
            # Update history
            self.chat_history.append({"role": "user", "content": text})
            # Storing clean_text so actions aren't repeated in context
            self.chat_history.append({"role": "model", "content": clean_text})
            
            # Keep history trimmed
            if len(self.chat_history) > 16:
                self.chat_history = self.chat_history[-16:]
                
            return clean_text
            
        except Exception as e:
            print(e)
            return f"Error communicating with Gemini API: {e}"

# Backward compatibility alias
JarvisCore = RKCore

