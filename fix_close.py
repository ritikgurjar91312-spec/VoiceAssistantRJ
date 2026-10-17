import sys
import re

with open('jarvis_core.py', 'r') as f:
    code = f.read()

# 1. Update system prompt
new_prompt_addition = '''Agar user kisi website ya app ko open karne ko kahe (jaise Google, Chrome, etc.):
ACTION: OPEN_WEBSITE("url")

Agar user kisi app ya process ko close karne ko kahe:
ACTION: CLOSE_APP("app_name")'''

code = code.replace(
    'Agar user kisi website ya app ko open karne ko kahe (jaise Google, Chrome, etc.):\nACTION: OPEN_WEBSITE("url")', 
    new_prompt_addition
)

# 2. Fix RUN_CODE regex
old_run_code = r"code_matches = re.finditer(r'ACTION:\s*RUN_CODE\s*\(\s*[\"\']([\s\S]*?)[\"\']\s*\)', raw_text, re.IGNORECASE)"
new_run_code = r"code_matches = re.finditer(r'ACTION:\s*RUN_CODE\s*\(\s*([\"\'`])([\s\S]*?)\1\s*\)', raw_text, re.IGNORECASE)"
code = code.replace(old_run_code, new_run_code)

old_code_to_run = "code_to_run = m.group(1).replace('\\\\n', '\\n')"
new_code_to_run = "code_to_run = m.group(2).replace('\\\\n', '\\n')"
code = code.replace(old_code_to_run, new_code_to_run)

# 3. Add CLOSE_APP handler
old_open_website = r"m = re.match(r'^ACTION:\s*OPEN_WEBSITE\s*\(\s*[\"\']?(.+?)[\"\']?\s*\)', t, re.IGNORECASE)"
new_close_app = '''m = re.match(r'^ACTION:\s*CLOSE_APP\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)
            if m:
                app_name = m.group(1).lower()
                import os
                if "chrome" in app_name or "browser" in app_name or "website" in app_name:
                    os.system("taskkill /f /im chrome.exe")
                elif "notepad" in app_name:
                    os.system("taskkill /f /im notepad.exe")
                else:
                    os.system(f"taskkill /f /im {app_name}.exe")
                continue
                
            m = re.match(r'^ACTION:\s*OPEN_WEBSITE\s*\(\s*["\']?(.+?)["\']?\s*\)', t, re.IGNORECASE)'''
code = code.replace(old_open_website, new_close_app)

with open('jarvis_core.py', 'w') as f:
    f.write(code)

print("Updates applied")
