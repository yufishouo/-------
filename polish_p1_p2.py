import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update TTS properties for a deeper, slower robotic voice
target_tts = '''def tts_worker():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)'''

replacement_tts = '''def tts_worker():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 130) # Slower for robotic feel
        engine.setProperty('volume', 1.0)
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            # Try to select the first voice (usually male/default SAPI5)
            engine.setProperty('voice', voices[0].id)'''

content = content.replace(target_tts, replacement_tts)

# 2. Add Precomputed Post-Processing Masks
target_globals = '''# ==========================================
# 遊戲參數設定 (Game Settings)
# =========================================='''

replacement_globals = '''import numpy as np

# ==========================================
# 遊戲參數設定 (Game Settings)
# =========================================='''

if 'import numpy as np' not in content[:500]:
    content = content.replace(target_globals, replacement_globals)

target_masks = '''# ==========================================
# 工具函式 (Utility Functions)
# =========================================='''

replacement_masks = '''# ==========================================
# 視覺特效預先計算 (Precomputed Visual Effects)
# ==========================================
# 產生暗角 (Vignette) 與掃描線 (Scanlines) 的 Mask，為了效能預先算好
_x = np.arange(FRAME_W) - FRAME_W / 2
_y = np.arange(FRAME_H) - FRAME_H / 2
_X, _Y = np.meshgrid(_x, _y)
_dist = np.hypot(_X, _Y)
_max_dist = np.hypot(FRAME_W / 2, FRAME_H / 2)
VIGNETTE_MASK = 1.0 - 0.45 * (_dist / _max_dist) ** 2.2
VIGNETTE_MASK_3C = np.stack((VIGNETTE_MASK,) * 3, axis=-1).astype(np.float32)

SCANLINES_MASK = np.ones((FRAME_H, FRAME_W, 3), dtype=np.float32)
SCANLINES_MASK[::3, :, :] = 0.88
SCANLINES_MASK[1::3, :, :] = 0.95

# ==========================================
# 工具函式 (Utility Functions)
# =========================================='''

content = content.replace(target_masks, replacement_masks)

# 3. Apply Post-Processing at the end of the frame
target_render = '''        # 顯示最終畫面
        cv2.imshow(WINDOW_NAME, frame)'''

replacement_render = '''        # ------------------------------------------
        # 最終畫面後製 (Post-Processing)
        # ------------------------------------------
        # 套用 CRT 掃描線與四角暗角特效，增強 Cyberpunk 沉浸感
        frame = (frame * VIGNETTE_MASK_3C * SCANLINES_MASK).astype(np.uint8)

        # 顯示最終畫面
        cv2.imshow(WINDOW_NAME, frame)'''

content = content.replace(target_render, replacement_render)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Phase 1 and 2 polish complete.")
