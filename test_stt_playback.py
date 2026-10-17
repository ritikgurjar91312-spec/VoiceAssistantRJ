import time
import wave
import numpy as np
import speech_recognition as sr
from jarvis_core import SoundDeviceMicrophone

print("Testing SoundDeviceMicrophone live recording...")
mic = SoundDeviceMicrophone()
r = sr.Recognizer()

with mic as source:
    print("Adjusting ambient noise...")
    r.adjust_for_ambient_noise(source, duration=0.5)
    print(f"Energy threshold: {r.energy_threshold}")
    print("Please say something (you have 4 seconds)...")
    try:
        audio = r.listen(source, timeout=4, phrase_time_limit=4)
        print("Audio captured! Length in bytes:", len(audio.get_raw_data()))
        
        # Save to test.wav to check quality
        with open("test_mic.wav", "wb") as f:
            f.write(audio.get_wav_data())
        print("Saved test_mic.wav")
        
        # Try recognize_google
        try:
            txt = r.recognize_google(audio, language="en-IN")
            print("Google recognized (en-IN):", txt)
        except Exception as e:
            print("Google recognition error:", e)
    except Exception as e:
        print("Listen error:", e)
