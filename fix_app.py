import sys
with open('app.py', 'r') as f:
    code = f.read()

import re

# 1. Add animate_pulse before toggle_listening
animate_pulse_code = '''
    def animate_pulse(self):
        if self.is_processing:
            if self.pulse_state:
                self.avatar_display.configure(border_width=2, border_color="#00ffff")
            else:
                self.avatar_display.configure(border_width=0)
            self.pulse_state = not self.pulse_state
        else:
            self.avatar_display.configure(border_width=0)
        self.after(500, self.animate_pulse)

    def toggle_listening(self):'''
code = code.replace('    def toggle_listening(self):', animate_pulse_code, 1)

# 2. Rewrite toggle_listening up to change_voice
pattern = r'    def toggle_listening\(self\):.*?    def change_voice\(self, choice\):'
new_toggle_listening = '''    def toggle_listening(self):
        if self.is_listening:
            self.is_listening = False
            self.mic_btn.configure(fg_color="transparent", text="MIC [OFF]", text_color="#00aaff")
            if not self.is_processing:
                self.title("J.A.R.V.I.S - Advanced Interface")
            return
            
        self.is_listening = True
        self.mic_btn.configure(fg_color="#005555", text="MIC [ON]", text_color="#ffffff")
        self.title("J.A.R.V.I.S - Listening for Commands...")
        
        def _listen_loop():
            try:
                import threading
                import time
                with self.core.voice.get_microphone() as source:
                    self.core.voice.recognizer.adjust_for_ambient_noise(source, duration=1)
                    while self.is_listening:
                        if self.is_processing:
                            time.sleep(0.5)
                            continue
                            
                        self.after(0, lambda: self.title("J.A.R.V.I.S - Listening..."))
                        text = self.core.voice.listen_with_mic(source, timeout=10, phrase_time_limit=15, pause_threshold=1.0)
                        if not self.is_listening: break
                        if text:
                            self.after(0, self.process_request, text)
                            self.is_listening = False
                            self.after(0, lambda: self.mic_btn.configure(fg_color="transparent", text="MIC [OFF]", text_color=self.text_color))
                            break
            except Exception as e:
                print("Voice Loop Error:", e)
                            
        import threading
        threading.Thread(target=_listen_loop, daemon=True).start()

    def change_voice(self, choice):'''
code = re.sub(pattern, new_toggle_listening, code, flags=re.DOTALL)

# 3. Remove change_voice and toggle_gesture entirely down to show_image_preview
pattern2 = r'    def change_voice\(self, choice\):.*?    def show_image_preview\(self, img_b64\):'
new_end = '''    def show_image_preview(self, img_b64):'''
code = re.sub(pattern2, new_end, code, flags=re.DOTALL)

with open('app.py', 'w') as f:
    f.write(code)
print('Replacement complete.')
