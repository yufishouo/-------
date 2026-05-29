import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports and TTS setup
imports = '''import json
import os
import threading
import queue
import pyttsx3

# ==========================================
# 語音播報系統 (TTS)
# ==========================================
tts_queue = queue.Queue()

def tts_worker():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
    except Exception as e:
        print(f"TTS Engine Init Error: {e}")
        return

    while True:
        text = tts_queue.get()
        if text is None:
            break
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
        tts_queue.task_done()

tts_thread = threading.Thread(target=tts_worker, daemon=True)
tts_thread.start()

def speak(text):
    tts_queue.put(text)
'''
content = content.replace('import json\nimport os', imports)

# 2. Synthwave Grid Function
grid_func = '''# ==========================================
# 3D 動態霓虹網格背景渲染 (Synthwave Grid)
# ==========================================
def generate_synthwave_grid(w, h, t):
    grid = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 畫漸層天空 (深紫藍)
    for y in range(h // 2):
        ratio = y / (h // 2)
        b = int(60 * (1 - ratio) + 20)
        g = int(10 * (1 - ratio))
        r = int(50 * (1 - ratio))
        cv2.line(grid, (0, y), (w, y), (b, g, r), 1)

    horizon_y = h // 2
    # 地平線發光
    cv2.line(grid, (0, horizon_y-1), (w, horizon_y-1), (255, 100, 255), 1)
    cv2.line(grid, (0, horizon_y), (w, horizon_y), (255, 255, 255), 2)
    cv2.line(grid, (0, horizon_y+1), (w, horizon_y+1), (255, 100, 255), 1)

    # 3D 網格 - 垂直線 (輻射狀)
    num_v_lines = 22
    center_x = w // 2
    for i in range(-num_v_lines, num_v_lines + 1):
        x_bottom = center_x + i * 180
        cv2.line(grid, (center_x, horizon_y), (x_bottom, h), (255, 0, 200), 2, cv2.LINE_AA)

    # 3D 網格 - 水平線 (透視移動)
    speed = 2.0
    num_h_lines = 15
    for i in range(num_h_lines):
        z = (i + (t * speed) % 1.0) / num_h_lines
        y = horizon_y + int((h - horizon_y) * (z ** 2.5))
        thickness = max(1, int(3 * z))
        color = (255, 0, int(100 + 155 * z))
        cv2.line(grid, (0, y), (w, y), color, thickness, cv2.LINE_AA)
        
    return grid

# ==========================================
# 影像合成工具函式'''
content = content.replace('# ==========================================\n# 影像合成工具函式', grid_func)

# 3. Replace background logic for MediaPipe
target_bg_mp = '''                # --- 背景替換 (MediaPipe 虛擬攝影棚) ---
                if bg_replace and background_img is not None and pose_results and pose_results.segmentation_masks:
                    bg_resized = cv2.resize(background_img, (FRAME_W, FRAME_H))'''
replace_bg_mp = '''                # --- 背景替換 (MediaPipe 虛擬攝影棚) ---
                if bg_replace and pose_results and pose_results.segmentation_masks:
                    bg_resized = generate_synthwave_grid(FRAME_W, FRAME_H, time.time())'''
content = content.replace(target_bg_mp, replace_bg_mp)

# 4. Replace background logic for MOG2
target_bg_mog = '''                # --- 背景替換 (MOG2 備用模式) ---
                if bg_replace and background_img is not None:
                    bg_resized = cv2.resize(background_img, (FRAME_W, FRAME_H))'''
replace_bg_mog = '''                # --- 背景替換 (MOG2 備用模式) ---
                if bg_replace:
                    bg_resized = generate_synthwave_grid(FRAME_W, FRAME_H, time.time())'''
content = content.replace(target_bg_mog, replace_bg_mog)

# 5. Insert voice calls
# Ultimate
content = content.replace("effects.append({'text': f'P{idx+1} ULTIMATE WAVES!'", "speak('Ultimate Active!')\n                                effects.append({'text': f'P{idx+1} ULTIMATE WAVES!'")
# Bullet Time
content = content.replace("effects.append({'text': f'P{idx+1} BULLET TIME!'", "speak('Bullet Time!')\n                                effects.append({'text': f'P{idx+1} BULLET TIME!'")
# Boss
content = content.replace("effects.append({'text': 'WARNING: BOSS APPROACHING!'", "speak('Warning, Boss Approaching')\n                effects.append({'text': 'WARNING: BOSS APPROACHING!'")
# Boss Destroyed
content = content.replace("effects.append({'text': 'BOSS DESTROYED!", "speak('Boss Destroyed, excellent')\n                            effects.append({'text': 'BOSS DESTROYED!")
# Game Over
content = content.replace("draw_text(frame, \"GAME OVER\", (0, int(FRAME_H * 0.18)), 1.8, COLOR_NEON_MAGENTA, 4, center=True)", "if flash_timer == 0: speak('Game Over') # Use flash_timer as a simple run-once flag, wait, better just put it where game_state transitions to GAMEOVER.\ndraw_text(frame, \"GAME OVER\", (0, int(FRAME_H * 0.18)), 1.8, COLOR_NEON_MAGENTA, 4, center=True)")
# Wait, replacing GAME OVER text is bad because it draws every frame. It will speak "Game Over" 30 times a second.
# Let's put it where `game_state = STATE_GAMEOVER`.
content = content.replace("game_state = STATE_GAMEOVER", "game_state = STATE_GAMEOVER\n                                speak('Game Over')")
# Note: there are two places for game_state = STATE_GAMEOVER. Both will be replaced! Perfect.

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Modifications for Proposal 4 complete.')
