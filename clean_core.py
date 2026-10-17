import sys
with open('jarvis_core.py', 'r') as f:
    code = f.read()

import re

# Remove GestureManager class
pattern1 = r'class GestureManager:.*?return None\n\n'
code = re.sub(pattern1, '', code, flags=re.DOTALL)

# Remove self.gesture = GestureManager()
pattern2 = r'        self.gesture = GestureManager\(\)\n'
code = code.replace(pattern2, '')

with open('jarvis_core.py', 'w') as f:
    f.write(code)
print('Cleaned jarvis_core.py')
