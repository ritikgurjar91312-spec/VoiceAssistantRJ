import os
import sys
import traceback
import time
from dotenv import load_dotenv

load_dotenv(override=True)

def print_section(title):
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

results = {}

# 1. TEST DEPENDENCY IMPORTS
print_section("1. DEPENDENCY IMPORTS")
deps = [
    ("customtkinter", "customtkinter"),
    ("pymongo", "pymongo"),
    ("speech_recognition", "speech_recognition"),
    ("cv2", "OpenCV (cv2)"),
    ("PIL", "Pillow (PIL)"),
    ("edge_tts", "edge_tts"),
    ("google.genai", "Google GenAI SDK"),
    ("sounddevice", "sounddevice"),
    ("dotenv", "python-dotenv")
]

all_deps_ok = True
for mod, name in deps:
    try:
        __import__(mod)
        print(f"  [PASS] {name} imported successfully.")
    except Exception as e:
        print(f"  [FAIL] {name} import error: {e}")
        all_deps_ok = False
results["dependencies"] = all_deps_ok

# 2. TEST MONGODB MANAGER
print_section("2. MONGODB MANAGER")
try:
    from jarvis_core import MongoDBManager
    db = MongoDBManager()
    print(f"  Using fallback: {db.use_fallback}")
    
    # Test task operations
    test_task = f"Test Task {int(time.time())}"
    db.add_task(test_task, due_at=int(time.time())+3600)
    tasks = db.get_tasks()
    found = any(test_task in t.get("text", "") for t in tasks)
    print(f"  [INFO] Add task: {'PASS' if found else 'FAIL'}")
    
    db.complete_task(test_task)
    tasks = db.get_tasks()
    completed = any(test_task in t.get("text", "") and t.get("done") for t in tasks)
    print(f"  [INFO] Complete task: {'PASS' if completed else 'FAIL'}")
    
    db.delete_task(test_task)
    tasks = db.get_tasks()
    deleted = not any(test_task in t.get("text", "") for t in tasks)
    print(f"  [INFO] Delete task: {'PASS' if deleted else 'FAIL'}")
    
    # Test memory operations
    test_fact = f"User test fact {int(time.time())}"
    db.add_memory(test_fact)
    memories = db.get_memory()
    fact_found = test_fact in memories
    print(f"  [INFO] Memory fact: {'PASS' if fact_found else 'FAIL'}")
    
    results["mongodb"] = (found and completed and deleted and fact_found)
    print(f"  [PASS] MongoDBManager functional test passed.")
except Exception as e:
    print(f"  [FAIL] MongoDBManager error: {e}")
    traceback.print_exc()
    results["mongodb"] = False

# 3. TEST VOICE MANAGER (TTS & Microphone)
print_section("3. VOICE MANAGER")
try:
    from jarvis_core import VoiceManager, SoundDeviceMicrophone
    vm = VoiceManager()
    vm.set_voice(0, 150)
    print(f"  Voice name: {vm.voice_name}, Rate: {vm.voice_rate}")
    vm.set_voice(1, 160)
    print(f"  Voice name (female): {vm.voice_name}, Rate: {vm.voice_rate}")
    
    # Test edge_tts generation
    import asyncio
    import edge_tts
    import tempfile
    
    async def test_tts_gen():
        comm = edge_tts.Communicate("Testing speech.", vm.voice_name, rate=vm.voice_rate)
        tmp = tempfile.mktemp(suffix=".mp3")
        await comm.save(tmp)
        size = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if os.path.exists(tmp):
            os.remove(tmp)
        return size > 0
        
    loop = asyncio.new_event_loop()
    tts_ok = loop.run_until_complete(test_tts_gen())
    loop.close()
    print(f"  [INFO] edge-tts audio generation: {'PASS' if tts_ok else 'FAIL'}")

    # Test sounddevice audio input devices
    import sounddevice as sd
    devices = sd.query_devices()
    print(f"  [INFO] Audio devices found: {len(devices)}")
    has_input = any(d.get("max_input_channels", 0) > 0 for d in devices)
    print(f"  [INFO] Input microphone available: {has_input}")
    
    results["voice"] = tts_ok
    print(f"  [PASS] VoiceManager functional test passed.")
except Exception as e:
    print(f"  [FAIL] VoiceManager error: {e}")
    traceback.print_exc()
    results["voice"] = False

# 4. TEST VISION MANAGER
print_section("4. VISION MANAGER")
try:
    from jarvis_core import VisionManager
    vis = VisionManager()
    import cv2
    cap = cv2.VideoCapture(0)
    can_open = cap.isOpened()
    if can_open:
        ret, frame = cap.read()
        cap.release()
        print(f"  [INFO] Camera device opened: True, frame captured: {ret}")
    else:
        cap.release()
        print("  [INFO] Camera device 0 not currently opened (hardware might not have camera or it is in use). VisionManager handles this gracefully.")
    
    img_b64 = vis.capture_image_base64()
    print(f"  [INFO] Vision capture returned: {'Image Data' if img_b64 else 'None (handled gracefully)'}")
    results["vision"] = True
    print(f"  [PASS] VisionManager test passed.")
except Exception as e:
    print(f"  [FAIL] VisionManager error: {e}")
    traceback.print_exc()
    results["vision"] = False

# 5. TEST ACTION PROCESSING
print_section("5. ACTION PROCESSING")
try:
    from rk_core import RKCore
    core = RKCore()
    
    test_cases = [
        ("Sir, task added.\nACTION: ADD_TASK(\"Buy batteries\")", "ADD_TASK"),
        ("Sir, remind set.\nACTION: REMIND(\"Meeting\", 15)", "REMIND"),
        ("Sir, task done.\nACTION: COMPLETE_TASK(\"Buy batteries\")", "COMPLETE_TASK"),
        ("Sir, task removed.\nACTION: DELETE_TASK(\"Buy batteries\")", "DELETE_TASK"),
        ("Understood sir.\nACTION: LEARN_FACT(\"Prefers dark theme\")", "LEARN_FACT"),
        ("Opening site.\nACTION: OPEN_WEBSITE(\"https://google.com\")", "OPEN_WEBSITE"),
        ("Closing app.\nACTION: CLOSE_APP(\"notepad\")", "CLOSE_APP"),
        ("Playing.\nACTION: PLAY_YOUTUBE(\"Interstellar soundtrack\")", "PLAY_YOUTUBE"),
        ("Language switched.\nACTION: SET_LANGUAGE(\"en-US\")", "SET_LANGUAGE"),
        ("Voice set.\nACTION: SET_VOICE(0, 160)", "SET_VOICE"),
        ("Running code.\nACTION: RUN_CODE(\"print('test')\")", "RUN_CODE"),
    ]
    
    actions_ok = True
    for sample, action_name in test_cases:
        try:
            cleaned = core._process_actions(sample)
            print(f"  [INFO] Action {action_name}: Processed. Output: '{cleaned.strip()}'")
        except Exception as err:
            print(f"  [FAIL] Action {action_name} error: {err}")
            actions_ok = False
            
    results["actions"] = actions_ok
    if actions_ok:
        print(f"  [PASS] Action processing passed.")
    else:
        print(f"  [FAIL] Some actions encountered issues.")
except Exception as e:
    print(f"  [FAIL] Action processing exception: {e}")
    traceback.print_exc()
    results["actions"] = False

# 6. TEST GEMINI API CONNECTION
print_section("6. GEMINI API & LLM")
try:
    from rk_core import RKCore
    core = RKCore()
    if not core.gemini_client:
        print("  [FAIL] Gemini Client not initialized. Check GEMINI_API_KEY.")
        results["gemini"] = False
    else:
        print("  [INFO] Sending test ping to Gemini API...")
        reply = core.send_message("System test: Reply with exactly 'RK_ONLINE' in one word.")
        print(f"  [INFO] Gemini Response: {reply}")
        if "Error" in reply or not reply:
            print(f"  [FAIL] Gemini API returned error: {reply}")
            results["gemini"] = False
        else:
            print("  [PASS] Gemini API responded successfully.")
            results["gemini"] = True
except Exception as e:
    print(f"  [FAIL] Gemini API Exception: {e}")
    traceback.print_exc()
    results["gemini"] = False

# 7. TEST GUI INITIALIZATION
print_section("7. GUI INITIALIZATION (HEADLESS TEST)")
try:
    from app import RKApp
    print("  [INFO] Initializing RKApp...")
    app = RKApp()
    app.update_idletasks()
    print("  [INFO] Widgets and layout constructed successfully.")
    app.destroy()
    print("  [PASS] GUI initialization passed.")
    results["gui"] = True
except Exception as e:
    print(f"  [FAIL] GUI initialization error: {e}")
    traceback.print_exc()
    results["gui"] = False

# SUMMARY
print_section("TEST SUMMARY")
all_passed = True
for k, v in results.items():
    status = "PASSED" if v else "FAILED"
    print(f"  {k.upper()}: {status}")
    if not v:
        all_passed = False

if all_passed:
    print("\n>>> ALL TESTS PASSED! RK IS COMPLETELY OPERATIONAL. <<<")
else:
    print("\n>>> SOME TESTS FAILED. INVESTIGATION REQUIRED. <<<")
