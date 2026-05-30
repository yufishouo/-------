import cv2
import numpy as np
import pygame
import math
import random
import time
import json
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
        engine.setProperty('rate', 130) # Slower for robotic feel
        engine.setProperty('volume', 1.0)
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            # Try to select the first voice (usually male/default SAPI5)
            engine.setProperty('voice', voices[0].id)
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


# ==========================================
# 遊戲設定
# ==========================================
WINDOW_NAME = 'Virtual Goalkeeper - Ultimate Upgrade'
MAX_LIVES = 3
INITIAL_BALL_SPEED = 5
SPAWN_INTERVAL = 2.0  # seconds
HIGH_SCORE_FILE = 'highscores.json'

# ==========================================
# 極致科幻霓虹配色系統 (Cyberpunk Premium Neon Palette - BGR Format)
# ==========================================
COLOR_NEON_TEAL = (255, 230, 0)      # 主要導航 / 輔助提示 (亮青綠色)
COLOR_NEON_MAGENTA = (200, 50, 255)  # 生命值 / 警告提示 (霓虹粉紫)
COLOR_NEON_GOLD = (0, 195, 255)     # 高分 / 黃金球 / 榮譽稱號 (烈陽金)
COLOR_NEON_BLUE = (255, 220, 100)    # 冰凍 / 技能準備就緒 (冰晶藍)
COLOR_NEON_GREEN = (180, 255, 50)    # 完美分數 / 安全綠色 (螢光綠)
COLOR_DARK_PANEL = (15, 10, 25)      # 磨砂玻璃深色背景 (深幽紫黑)

# ==========================================
# 音效與影像載入 (安全加載與備用機制)
# ==========================================
pygame.mixer.init()

# --- 🎵 BGM 載入與播放 ---
try:
    if os.path.exists('assets/bgm.mp3'):
        pygame.mixer.music.load('assets/bgm.mp3')
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1)
except Exception as e:
    print(f"Warning: Could not load BGM ({e}). Background music will be muted.")

sound_files = {
    'hit': 'assets/hit.wav',
    'miss': 'assets/miss.wav',
    'hit_gold': 'assets/hit_gold.wav',
    'hit_bomb': 'assets/hit_bomb.wav',
    'hit_ice': 'assets/hit_ice.wav',
    'hit_heart': 'assets/hit_heart.wav'
}
sounds = {}
for key, filepath in sound_files.items():
    try:
        sounds[key] = pygame.mixer.Sound(filepath)
    except Exception as e:
        print(f"Warning: Could not load sound '{filepath}'. Sound will be muted.")
        sounds[key] = None

# 七種球種的圖像加載與備用繪製
ball_types = ['normal', 'gold', 'bomb', 'ice', 'heart', 'split', 'homing']
ball_imgs = {}

for bt in ball_types:
    filepath = 'assets/ball.png' if bt == 'normal' else f'assets/ball_{bt}.png'
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        img = np.zeros((64, 64, 4), dtype=np.uint8)
        cx, cy = 32, 32
        if bt == 'normal':
            cv2.circle(img, (cx, cy), 30, (255, 255, 255, 255), -1)
            cv2.circle(img, (cx, cy), 30, (0, 0, 0, 255), 2)
        elif bt == 'gold':
            cv2.circle(img, (cx, cy), 30, (0, 215, 255, 255), -1)
            cv2.circle(img, (cx, cy), 30, (0, 100, 200, 255), 2)
        elif bt == 'bomb':
            cv2.circle(img, (cx, cy), 30, (0, 0, 150, 255), -1)
            cv2.circle(img, (cx, cy), 30, (0, 255, 255, 255), 2)
        elif bt == 'ice':
            cv2.circle(img, (cx, cy), 30, (255, 230, 150, 255), -1)
            cv2.circle(img, (cx, cy), 30, (255, 255, 255, 255), 2)
        elif bt == 'heart':
            cv2.circle(img, (cx, cy), 30, (150, 50, 255, 255), -1)
            cv2.circle(img, (cx, cy), 30, (255, 255, 255, 255), 2)
        elif bt == 'split':
            cv2.circle(img, (cx, cy), 30, (255, 100, 100, 255), -1)
            cv2.circle(img, (cx, cy), 30, (50, 255, 50, 255), 2)
        elif bt == 'homing':
            cv2.circle(img, (cx, cy), 30, (0, 0, 0, 255), -1)
            cv2.circle(img, (cx, cy), 30, (0, 0, 255, 255), 3)
            cv2.line(img, (cx - 30, cy), (cx + 30, cy), (0, 0, 255, 255), 2)
            cv2.line(img, (cx, cy - 30), (cx, cy + 30), (0, 0, 255, 255), 2)
    ball_imgs[bt] = img

BALL_HEIGHT, BALL_WIDTH = ball_imgs['normal'].shape[:2]

# ==========================================
# 載入場景背景圖
# ==========================================
background_img = cv2.imread('football.jpg')
if background_img is None:
    print("Warning: 無法讀取 'football.jpg'。請確認檔案是否存在於同一目錄下。")

# ==========================================
# 電腦視覺 MediaPipe 可選模式設定與偵測
# ==========================================
USE_MEDIAPIPE = False
pose_tracker = None
mp_image_format = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    mp_image_format = mp.ImageFormat.SRGB
    base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=2,  # 啟用雙人追蹤模式
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=True  # 新增：啟用背景去背遮罩
    )
    pose_tracker = vision.PoseLandmarker.create_from_options(options)
    USE_MEDIAPIPE = True
    print(">>> [MediaPipe] 成功載入 Tasks API！已自動啟用雙人骨架追蹤與虛擬化身模式。")
except Exception as e:
    print(f">>> [MediaPipe] 初始化失敗 ({e})。請確認已下載 'pose_landmarker.task' 模型檔案。遊戲將降級為 MOG2 動態偵測模式。")

def update_pose_tracker(num_poses):
    global pose_tracker
    if not USE_MEDIAPIPE:
        return
    try:
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=True
        )
        if pose_tracker:
            pose_tracker.close() # 關閉並釋放原本的資源
        pose_tracker = vision.PoseLandmarker.create_from_options(options)
        print(f">>> [MediaPipe] 追蹤人數已更新為: {num_poses} 人")
    except Exception as e:
        print(f"Error updating MediaPipe tracker: {e}")

# ==========================================
# 高分紀錄與進度儲存 (Save System)
# ==========================================
def load_save_data():
    default_data = {'high_score': 0, 'cyber_coins': 0, 'unlocked_items': [], 'equipped_shield': 'default', 'leaderboard': []}
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if 'high_score' in data and 'cyber_coins' not in data:
                        # 舊版存檔兼容
                        default_data['high_score'] = data.get('high_score', 0)
                    else:
                        default_data.update(data)
                        if 'leaderboard' not in default_data:
                            default_data['leaderboard'] = []
        except Exception:
            pass
    return default_data

def save_data(data):
    try:
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# ==========================================
# 3D 動態霓虹網格背景渲染 (Synthwave Grid)
# ==========================================
_cached_sky = None

def generate_synthwave_grid(w: int, h: int, t: float):
    """
    動態 3D 霓虹網格背景渲染 (Dynamic 3D Synthwave Grid)
    利用透視投影 (Perspective Projection) 原理，即時運算產生向後方無限延伸的流動網格。
    """
    global _cached_sky
    if _cached_sky is None or _cached_sky.shape[:2] != (h, w):
        _cached_sky = np.zeros((h, w, 3), dtype=np.uint8)
        # 預先計算並快取漸層天空，避免每幀執行 360 次 Python for loop
        for y in range(h // 2):
            ratio = y / (h // 2)
            b = int(60 * (1 - ratio) + 20)
            g = int(10 * (1 - ratio))
            r = int(50 * (1 - ratio))
            cv2.line(_cached_sky, (0, y), (w, y), (b, g, r), 1)
            
    grid = _cached_sky.copy()

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
# 影像合成工具函式 (Alpha Blending & Tint)
# ==========================================
def overlay_image_alpha(img, img_overlay, x, y, global_alpha=1.0):
    """將含有透明通道的 img_overlay 合成到 img 上，支援全域透明度 global_alpha"""
    x, y = int(round(x)), int(round(y))
    
    y1, y2 = max(0, y), min(img.shape[0], y + img_overlay.shape[0])
    x1, x2 = max(0, x), min(img.shape[1], x + img_overlay.shape[1])

    oy1 = max(0, -y)
    oy2 = oy1 + (y2 - y1)
    ox1 = max(0, -x)
    ox2 = ox1 + (x2 - x1)

    if oy1 >= img_overlay.shape[0] or ox1 >= img_overlay.shape[1] or y1 >= y2 or x1 >= x2:
        return img  # 移出螢幕外

    # 向量化 Alpha Blending (避免 Python for loop 逐通道計算，提升合成速度)
    alpha_s = (img_overlay[oy1:oy2, ox1:ox2, 3:4] / 255.0) * global_alpha
    alpha_l = 1.0 - alpha_s

    img[y1:y2, x1:x2] = (alpha_s * img_overlay[oy1:oy2, ox1:ox2, :3] + alpha_l * img[y1:y2, x1:x2]).astype(np.uint8)
    return img

# ==========================================
# 圓角與霓虹發光繪製工具 (Rounded Corner & Neon Glow Utilities)
# ==========================================
def draw_rounded_rect(img, pt1, pt2, color, thickness=1, r=12, fill=False):
    """在 OpenCV 圖像上繪製精緻的圓角矩形 (帶有抗鋸齒)"""
    if thickness < 0:
        fill = True
    x1, y1 = pt1
    x2, y2 = pt2
    
    # 確保座標順序
    if x1 > x2: x1, x2 = x2, x1
    if y1 > y2: y1, y2 = y2, y1
        
    w = x2 - x1
    h = y2 - y1
    
    # 縮小圓角半徑如果太大的話
    r = min(r, w // 2, h // 2)
    if r <= 0:
        if fill:
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        else:
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
        return img
    
    if fill:
        # 繪製主矩形塊與圓角填充
        cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
        cv2.circle(img, (x1 + r, y1 + r), r, color, -1, cv2.LINE_AA)
        cv2.circle(img, (x2 - r, y1 + r), r, color, -1, cv2.LINE_AA)
        cv2.circle(img, (x1 + r, y2 - r), r, color, -1, cv2.LINE_AA)
        cv2.circle(img, (x2 - r, y2 - r), r, color, -1, cv2.LINE_AA)
    else:
        # 繪製直線邊緣
        cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness, cv2.LINE_AA)
        
        # 繪製圓角弧線
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness, cv2.LINE_AA)
    return img

def draw_glow_circle(img, cx, cy, r, color, thickness=2, glow_factor=3):
    """在圓形周圍繪製多層半透明的發光光環效果 (Neon Glow)，優化：僅處理 ROI 避免全螢幕記憶體拷貝"""
    h, w = img.shape[:2]
    max_r = r + glow_factor * 4 + thickness + glow_factor * 2
    x1, x2 = max(0, cx - max_r), min(w, cx + max_r)
    y1, y2 = max(0, cy - max_r), min(h, cy + max_r)
    
    if x1 >= x2 or y1 >= y2:
        return
        
    roi = img[y1:y2, x1:x2]
    for i in range(glow_factor, 0, -1):
        alpha = 0.12 * (1.0 - (i / (glow_factor + 1)))
        glow_r = r + i * 4
        overlay_roi = roi.copy()
        cv2.circle(overlay_roi, (cx - x1, cy - y1), glow_r, color, thickness + i * 2, cv2.LINE_AA)
        cv2.addWeighted(overlay_roi, alpha, roi, 1.0 - alpha, 0, roi)
        
    cv2.circle(roi, (cx - x1, cy - y1), r, color, thickness, cv2.LINE_AA)

def draw_heart(img, cx, cy, size, color):
    """在給定座標繪製精美的向量愛心 (抗鋸齒填滿，用於生命值顯示)"""
    r = size // 4
    # 左右兩個半圓
    cv2.circle(img, (cx - r, cy - r), r, color, -1, cv2.LINE_AA)
    cv2.circle(img, (cx + r, cy - r), r, color, -1, cv2.LINE_AA)
    # 下方的倒三角形
    pts = np.array([
        [cx - 2 * r - 1, cy - r // 2],
        [cx + 2 * r + 1, cy - r // 2],
        [cx, cy + r * 2]
    ], np.int32)
    cv2.fillPoly(img, [pts], color)

# ==========================================
# 極致磨砂玻璃面板繪製 (Glassmorphism HUD Panels)
# ==========================================
def draw_glass_panel(img, x1, y1, x2, y2, bg_color=(0, 0, 0), alpha=0.4, border_color=(255, 255, 255), border_thickness=1, blur_value=15, corner_radius=15):
    """在影像上繪製具有真實磨砂模糊效果、半透明、外發光霓虹邊框與雙層玻璃反光邊框的極致控制面板"""
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x1 >= x2 or y1 >= y2:
        return img
    
    sub_img = img[y1:y2, x1:x2].copy()
    
    # 1. 磨砂模糊效果
    if blur_value > 0:
        ksize = blur_value if blur_value % 2 == 1 else blur_value + 1
        sub_img = cv2.GaussianBlur(sub_img, (ksize, ksize), 0)
        
    # 2. 顏色混合 (在子區域中繪製填充的圓角矩形)
    rect = np.zeros_like(sub_img)
    draw_rounded_rect(rect, (0, 0), (x2 - x1, y2 - y1), bg_color, fill=True, r=corner_radius)
    
    # 3. 使用 mask 把圓角外的背景還原，避免圓角外部也變黑
    mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
    draw_rounded_rect(mask, (0, 0), (x2 - x1, y2 - y1), 255, fill=True, r=corner_radius)
    
    # 對 sub_img 與 rect 進行混合
    blended = cv2.addWeighted(rect, alpha, sub_img, 1.0 - alpha, 0)
    
    # 只把圓角內部的部分替換回 img，圓角外部保持原樣
    mask_inv = cv2.bitwise_not(mask)
    img_bg = cv2.bitwise_and(img[y1:y2, x1:x2], img[y1:y2, x1:x2], mask=mask_inv)
    img_fg = cv2.bitwise_and(blended, blended, mask=mask)
    
    img[y1:y2, x1:x2] = cv2.add(img_bg, img_fg)
    
    # 4. 繪製精緻的霓虹圓角雙邊框與外發光效果
    if border_thickness > 0:
        pad = 12
        bx1, bx2 = max(0, x1 - pad), min(w, x2 + pad)
        by1, by2 = max(0, y1 - pad), min(h, y2 + pad)
        
        if bx1 < bx2 and by1 < by2:
            roi_img = img[by1:by2, bx1:bx2]
            
            # A. 外發光投影效果 (Neon Outer Glow)，優化：僅處理 ROI 避免全螢幕拷貝
            glow_overlay = roi_img.copy()
            for i in range(4, 0, -1):
                draw_rounded_rect(glow_overlay, (x1 - bx1 - i, y1 - by1 - i), (x2 - bx1 + i, y2 - by1 + i), border_color, thickness=border_thickness + i * 2, r=corner_radius + i)
            cv2.addWeighted(glow_overlay, 0.12, roi_img, 0.88, 0, roi_img)
            
            # B. 核心主要發光邊框 (Core Neon Border)
            draw_rounded_rect(roi_img, (x1 - bx1, y1 - by1), (x2 - bx1, y2 - by1), border_color, thickness=border_thickness, r=corner_radius)
            
            # C. 內層超細緻白色高光玻璃反光邊框 (Inset White Specular Border)
            specular_overlay = roi_img.copy()
            draw_rounded_rect(specular_overlay, (x1 - bx1 + 1, y1 - by1 + 1), (x2 - bx1 - 1, y2 - by1 - 1), (255, 255, 255), thickness=1, r=max(0, corner_radius - 1))
            cv2.addWeighted(specular_overlay, 0.35, roi_img, 0.65, 0, roi_img)
        
    return img

# ==========================================
# 高質感粒子特效生成器
# ==========================================
def spawn_particles(particles, x, y, color):
    """在給定座標炸出 15-20 個彩色小圓點粒子"""
    for _ in range(random.randint(15, 20)):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        particles.append({
            'x': x + BALL_WIDTH // 2,
            'y': y + BALL_HEIGHT // 2,
            'vx': speed * math.cos(angle),
            'vy': speed * math.sin(angle) - random.uniform(1, 3), # 帶有往上的初速
            'color': color,
            'radius': random.randint(3, 7),
            'life': 1.0,
            'decay': random.uniform(0.02, 0.05)
        })

# ==========================================
# 隨機球體類型挑選
# ==========================================
def get_random_ball_type():
    """根據權重選擇球體"""
    r = random.random()
    if r < 0.50: return 'normal'
    elif r < 0.60: return 'gold'
    elif r < 0.70: return 'bomb'
    elif r < 0.75: return 'ice'
    elif r < 0.80: return 'heart'
    elif r < 0.90: return 'split'
    else: return 'homing'

# ==========================================
# 遊戲狀態與重置函式
# ==========================================
STATE_MENU_MODE = 0
STATE_MENU_DIFF = 1
STATE_PLAYING = 2
STATE_GAMEOVER = 3
STATE_SHOP = 4

def reset_game_state(difficulty: int, high_score: int) -> dict:
    """
    初始化或重置遊戲狀態 (Initialize/Reset Game State)
    根據不同的難度設定給予對應的生命值與初始球速，並重置所有技能冷卻、Boss 狀態與分數。
    
    Args:
        difficulty (int): 遊戲難度 (1=Easy, 2=Normal, 3=Hard)
        high_score (int): 目前的歷史最高分紀錄
        
    Returns:
        dict: 包含所有遊戲變數的初始狀態字典
    """
    # difficulty: 1 (Easy), 2 (Normal), 3 (Hard)
    if difficulty == 1:
        lives = 5
        speed = INITIAL_BALL_SPEED
    elif difficulty == 2:
        lives = 3
        speed = INITIAL_BALL_SPEED
    else: # 3
        lives = 2
        speed = INITIAL_BALL_SPEED + 3

    return {
        'score': 0,
        'lives': lives,
        'balls': [],
        'effects': [],
        'particles': [],
        'ambient_sparks': [],
        'combo': 0,
        'high_score': high_score,
        'current_speed': speed,
        'current_spawn_interval': SPAWN_INTERVAL,
        'last_spawn_time': time.time(),
        'game_state': STATE_PLAYING,
        'ice_timer': 0.0,
        'shake_timer': 0,
        'hit_stop_timer': 0,
        'flash_timer': 0,
        'flash_color': (0, 0, 0),
        'skill_cooldown': 0,
        'shield_timer': 0.0,
        'fever_timer': 0.0,
        'bullet_time_timer': 0.0,
        'shield_cooldown': 0,
        'shockwaves': [],
        'next_boss_score': 300,
        'boss': {'active': False, 'hp': 0, 'max_hp': 0, 'x': 0, 'y': 0, 'vx': 0, 'last_attack': 0, 'dead': False}
    }

# ==========================================
# UI 繪製輔助函式
# ==========================================
def draw_text(img, text, pos, scale, color, thickness=2, center=False):
    """
    繪製文字工具函式 (Draw Text Helper)
    封裝了 OpenCV 的 putText 功能，支援文字置中對齊以及自動加上黑色邊框以提升閱讀性。
    """
    font = cv2.FONT_HERSHEY_DUPLEX
    if center:
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        pos = ((img.shape[1] - text_size[0]) // 2, pos[1])
    # 畫黑色描邊
    cv2.putText(img, text, pos, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    # 畫主要文字
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)

# ==========================================
# 主遊戲迴圈
# ==========================================
def main():
    """
    遊戲主迴圈與核心邏輯 (Main Game Loop & Core Logic)
    負責管理系統資源 (Webcam, 音效)、影像擷取、狀態機切換 (Menu -> Shop -> Playing -> GameOver)、
    以及核心的物理碰撞偵測與畫面渲染更新。
    """
    cap = cv2.VideoCapture(0)
    mp_start_time = time.time()
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # 初始化狀態
    game_state = STATE_MENU_MODE
    game_mode = 1
    game_difficulty = 2
    save_info = load_save_data()
    high_score = save_info.get('high_score', 0)
    cyber_coins = save_info.get('cyber_coins', 0)
    unlocked_items = save_info.get('unlocked_items', [])
    equipped_shield = save_info.get('equipped_shield', 'default')
    leaderboard = save_info.get('leaderboard', [])
    new_record_broken = False
    score_saved = False
    bg_replace = False  # 預設為 False：顯示真實視訊背景，可手動按 'B' 鍵切換虛擬去背

    # 預先計算全螢幕特效遮罩，避免每幀重複計算浪費大量 CPU 資源
    FRAME_H, FRAME_W = 720, 1280
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
    
    # 預先合併這兩層遮罩，將每幀的乘法次數減半
    FINAL_OVERLAY_MASK = (VIGNETTE_MASK_3C * SCANLINES_MASK).astype(np.float32)

    # 初始化這些變數，稍後 reset 時會覆蓋
    score, lives, balls, effects, particles, combo, ambient_sparks, shockwaves = 0, MAX_LIVES, [], [], [], 0, [], []
    menu_particles = []
    last_spawn_time, current_speed, current_spawn_interval, ice_timer = 0, 0, 0, 0.0
    shake_timer, flash_timer, flash_color, skill_cooldown, shield_timer, shield_cooldown, hit_stop_timer = 0, 0, (0, 0, 0), 0, 0.0, 0, 0
    fever_timer, bullet_time_timer = 0.0, 0.0
    glitch_timer = 0
    backSub = None 

    print("Game Started! Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. 影像預處理：水平翻轉 (Mirror)
        frame = cv2.flip(frame, 1)

        # 根據比例進行 16:9 自動裁切，並統一放大至 1280x720，保證全畫面解析度一致且視窗不跳動
        h, w = frame.shape[:2]
        if w / h > 16 / 9:
            # 畫面太寬 (如 21:9)，裁切兩側
            new_w = int(h * 16 / 9)
            crop_x = (w - new_w) // 2
            frame = frame[:, crop_x : w - crop_x]
        else:
            # 畫面太高 (如 4:3)，裁切上下
            new_h = int(w * 9 / 16)
            crop_y = (h - new_h) // 2
            frame = frame[crop_y : h - crop_y, :]
            
        frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
        FRAME_H, FRAME_W = 720, 1280
        
        # 震屏特效實作 (Screen Shake translation matrix)
        if game_state == STATE_PLAYING and shake_timer > 0:
            dx = random.randint(-8, 8)
            dy = random.randint(-8, 8)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, M, (FRAME_W, FRAME_H))
            shake_timer -= 1

        if game_state in (STATE_MENU_MODE, STATE_MENU_DIFF):
            # 1. 畫半透明黑色遮罩讓文字更清楚，使用幽邃的暗紫底色
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (10, 5, 15), -1)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

            # 2. 動態選單背景粒子漂移系統
            if len(menu_particles) < 50:
                menu_particles.append({
                    'x': random.uniform(10, FRAME_W - 10),
                    'y': random.uniform(FRAME_H + 5, FRAME_H + 20), # 從畫面底部外圍緩緩升起
                    'vx': random.uniform(-0.5, 0.5),
                    'vy': random.uniform(-1.5, -0.4),
                    'color': random.choice([COLOR_NEON_TEAL, COLOR_NEON_MAGENTA, COLOR_NEON_GOLD, COLOR_NEON_BLUE]),
                    'radius': random.randint(2, 5),
                    'life': random.uniform(0.7, 1.0)
                })
            
            # 更新並繪製漂移粒子 (在遮罩之後、玻璃面板之前繪製，創造絕佳的空間景深感)
            for p in menu_particles[:]:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['life'] -= 0.003
                if p['y'] < -10 or p['life'] <= 0:
                    menu_particles.remove(p)
                    continue
                
                overlay_pt = frame.copy()
                cv2.circle(overlay_pt, (int(p['x']), int(p['y'])), p['radius'], p['color'], -1, cv2.LINE_AA)
                cv2.addWeighted(overlay_pt, p['life'] * 0.45, frame, 1.0 - p['life'] * 0.45, 0, frame)

        if game_state == STATE_MENU_MODE:
            # 繪製主選單大玻璃面板 (極光青邊框)
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, COLOR_DARK_PANEL, 0.55, COLOR_NEON_TEAL, 2)

            # 主選單標題 (高貴亮麗的烈陽金)
            draw_text(frame, "Virtual Goalkeeper", (0, int(FRAME_H * 0.2)), 1.5, COLOR_NEON_GOLD, 3, center=True)
            draw_text(frame, "Ultimate Edition", (0, int(FRAME_H * 0.28)), 1.0, (255, 255, 255), 2, center=True)
            
            # 顯示目前偵測到的電腦視覺追蹤模式
            cv_text = "Sensing Mode: MediaPipe Skeleton Tracker (Pro)" if USE_MEDIAPIPE else "Sensing Mode: Dynamic Outline Silhouette"
            cv_color = COLOR_NEON_GREEN if USE_MEDIAPIPE else COLOR_NEON_GOLD
            draw_text(frame, cv_text, (0, int(FRAME_H * 0.36)), 0.6, cv_color, 1, center=True)
            
            draw_text(frame, f"ALL-TIME HIGH SCORE: {high_score}", (0, int(FRAME_H * 0.45)), 0.7, (255, 255, 255), 2, center=True)
            
            # --- 🏆 繪製排行榜 ---
            if leaderboard:
                lb_panel_x1, lb_panel_y1 = FRAME_W - 280, 50
                lb_panel_x2, lb_panel_y2 = FRAME_W - 30, 60 + len(leaderboard) * 35 + 50
                frame = draw_glass_panel(frame, lb_panel_x1, lb_panel_y1, lb_panel_x2, lb_panel_y2, COLOR_DARK_PANEL, 0.45, COLOR_NEON_GOLD, 1)
                draw_text(frame, "TOP 5 SCORE", (lb_panel_x1 + 45, lb_panel_y1 + 35), 0.65, COLOR_NEON_GOLD, 2)
                for i, s in enumerate(leaderboard):
                    rank_color = (255, 215, 0) if i == 0 else (192, 192, 192) if i == 1 else (205, 127, 50) if i == 2 else (255, 255, 255)
                    draw_text(frame, f"#{i+1} {s}", (lb_panel_x1 + 30, lb_panel_y1 + 75 + i * 35), 0.6, rank_color, 1)

            draw_text(frame, "Select Game Mode:", (0, int(FRAME_H * 0.56)), 0.8, COLOR_NEON_TEAL, 2, center=True)
            draw_text(frame, "1. Single Player (Classic Arena)", (0, int(FRAME_H * 0.64)), 0.7, (255, 255, 255), 1, center=True)
            draw_text(frame, "2. Multiplayer (Wider Screen Co-op)", (0, int(FRAME_H * 0.71)), 0.7, (255, 255, 255), 1, center=True)
            draw_text(frame, "3. Defend Center (360 Degree Survival)", (0, int(FRAME_H * 0.78)), 0.7, (255, 255, 255), 1, center=True)
            
            # 呼吸霓虹發光提示字
            pulse = int(math.sin(time.time() * 8) * 3)
            draw_text(frame, "Press '1', '2', or '3' to Start!", (0, int(FRAME_H * 0.89) + pulse), 0.7, COLOR_NEON_TEAL, 2, center=True)
            draw_text(frame, "Press 'S' to enter CYBER SHOP", (0, int(FRAME_H * 0.95)), 0.6, COLOR_NEON_MAGENTA, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('1'):
                game_mode = 1
                update_pose_tracker(1)
                game_state = STATE_MENU_DIFF
            elif key == ord('2'):
                game_mode = 2
                update_pose_tracker(2)
                game_state = STATE_MENU_DIFF
            elif key == ord('3'):
                game_mode = 3
                update_pose_tracker(1)
                game_state = STATE_MENU_DIFF
            elif key == ord('s') or key == ord('S'):
                game_state = STATE_SHOP
            elif key == ord('q'):
                break
 
        elif game_state == STATE_MENU_DIFF:
            # 繪製難度選擇大玻璃面板 (烈陽金邊框)
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, COLOR_DARK_PANEL, 0.55, COLOR_NEON_GOLD, 2)

            # 難度選單標題
            draw_text(frame, f"Mode {game_mode} Selected", (0, int(FRAME_H * 0.2)), 1.3, COLOR_NEON_TEAL, 3, center=True)
            draw_text(frame, "Select Difficulty Level:", (0, int(FRAME_H * 0.4)), 1.0, (255, 255, 255), 2, center=True)
            
            # 不同難度高質感配色
            draw_text(frame, "1. Easy (5 Lives, Adaptive Speed)", (0, int(FRAME_H * 0.52)), 0.75, COLOR_NEON_GREEN, 2, center=True)
            draw_text(frame, "2. Normal (3 Lives, High-octane)", (0, int(FRAME_H * 0.62)), 0.75, COLOR_NEON_TEAL, 2, center=True)
            draw_text(frame, "3. Hard (2 Lives, INSANE Tempo)", (0, int(FRAME_H * 0.72)), 0.75, COLOR_NEON_MAGENTA, 2, center=True)
            
            # 呼吸霓虹提示字
            pulse = int(math.sin(time.time() * 8) * 3)
            draw_text(frame, "Press '1', '2', or '3' to deploy!  |  'ESC' to go Back", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_GOLD, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                game_state = STATE_MENU_MODE
            elif key in [ord('1'), ord('2'), ord('3')]:
                if key == ord('1'): game_difficulty = 1
                elif key == ord('2'): game_difficulty = 2
                elif key == ord('3'): game_difficulty = 3
                
                # 初始化遊戲狀態
                save_info = load_save_data()
                high_score = save_info.get('high_score', 0)
                cyber_coins = save_info.get('cyber_coins', 0)
                unlocked_items = save_info.get('unlocked_items', [])
                equipped_shield = save_info.get('equipped_shield', 'default')
                leaderboard = save_info.get('leaderboard', [])
                glitch_timer = 0
                new_record_broken = False
                score_saved = False
                state = reset_game_state(game_difficulty, high_score)
                score = state['score']
                lives = state['lives']
                balls = state['balls']
                effects = state['effects']
                particles = state['particles']
                ambient_sparks = state['ambient_sparks']
                combo = state['combo']
                current_speed = state['current_speed']
                current_spawn_interval = state['current_spawn_interval']
                last_spawn_time = state['last_spawn_time']
                game_state = state['game_state']
                ice_timer = state['ice_timer']
                shake_timer = state['shake_timer']
                hit_stop_timer = state['hit_stop_timer']
                flash_timer = state['flash_timer']
                flash_color = state['flash_color']
                skill_cooldown = state['skill_cooldown']
                shield_timer = state.get('shield_timer', 0.0)
                shield_cooldown = state.get('shield_cooldown', 0)
                fever_timer = state.get('fever_timer', 0.0)
                bullet_time_timer = state.get('bullet_time_timer', 0.0)
                shockwaves = state.get('shockwaves', [])
                next_boss_score = state.get('next_boss_score', 300)
                boss = state.get('boss', {})
                
                # 重新初始化背景相減器以適應新的解析度
                backSub = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
                
            elif key == ord('q'):
                break

        elif game_state == STATE_SHOP:
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, COLOR_DARK_PANEL, 0.65, COLOR_NEON_MAGENTA, 2)
            draw_text(frame, "CYBER SHOP", (0, int(FRAME_H * 0.2)), 1.5, COLOR_NEON_MAGENTA, 3, center=True)
            draw_text(frame, f"CYBER COINS: {cyber_coins}", (0, int(FRAME_H * 0.3)), 1.0, COLOR_NEON_GOLD, 2, center=True)

            items = [
                {'id': 'quantum_purple', 'name': 'Quantum Purple Shield', 'cost': 50, 'color': (255, 50, 150)},
                {'id': 'deep_sea_blue', 'name': 'Deep Sea Blue Shield', 'cost': 50, 'color': (255, 150, 0)}
            ]

            # 繪製商品
            for i, item in enumerate(items):
                y_pos = int(FRAME_H * (0.45 + i * 0.15))
                status = "EQUIPPED" if equipped_shield == item['id'] else "UNLOCKED" if item['id'] in unlocked_items else f"COST: {item['cost']} COINS"
                color = COLOR_NEON_GREEN if equipped_shield == item['id'] else (255, 255, 255) if item['id'] in unlocked_items else (150, 150, 150)
                
                draw_text(frame, f"{i+1}. {item['name']} - {status}", (0, y_pos), 0.8, color, 2, center=True)
            
            draw_text(frame, "Press '1' / '2' to Buy/Equip, '0' for Default, 'Q' to Back", (0, int(FRAME_H * 0.85)), 0.6, COLOR_NEON_TEAL, 1, center=True)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == ord('Q'):
                game_state = STATE_MENU_MODE
            elif key == ord('0'):
                equipped_shield = 'default'
                save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield, 'leaderboard': leaderboard})
            elif key == ord('1') or key == ord('2'):
                idx = int(chr(key)) - 1
                item = items[idx]
                if item['id'] in unlocked_items:
                    equipped_shield = item['id']
                    save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield, 'leaderboard': leaderboard})
                elif cyber_coins >= item['cost']:
                    cyber_coins -= item['cost']
                    unlocked_items.append(item['id'])
                    equipped_shield = item['id']
                    save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield, 'leaderboard': leaderboard})

        elif game_state == STATE_PLAYING:
            if equipped_shield == 'quantum_purple':
                shield_glow_color = (255, 50, 150)
            elif equipped_shield == 'deep_sea_blue':
                shield_glow_color = (255, 150, 0)
            else:
                shield_glow_color = (0, 255, 255)
                
            is_shield_active = (time.time() < shield_timer)
            if skill_cooldown > 0:
                skill_cooldown -= 1
            if shield_cooldown > 0:
                shield_cooldown -= 1

            # 2. 電腦視覺追蹤運算 (MediaPipe 或是 背景相減 Outlines)
            player_points = [] # 用於 MediaPipe 精準圓形碰撞 (x, y, radius)
            player_boxes = []  # 用於背景相減 AABB 碰撞偵測 (x, y, w, h)
            player_hands = []  # 新增：儲存手腕位置用於重力磁吸護盾
            player_heads = []  # 新增：儲存頭部位置用於追蹤球
            area_thresh = 1000 if game_mode == 1 else 2500
            
            if USE_MEDIAPIPE:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp_image_format, data=rgb_frame)
                timestamp_ms = int((time.time() - mp_start_time) * 1000)
                
                # 執行多骨架推論
                pose_results = pose_tracker.detect_for_video(mp_image, timestamp_ms)
                
                # --- 背景替換 (MediaPipe 虛擬攝影棚) ---
                if bg_replace and pose_results and pose_results.segmentation_masks:
                    bg_resized = generate_synthwave_grid(FRAME_W, FRAME_H, time.time())
                    combined_mask = np.zeros((FRAME_H, FRAME_W), dtype=np.float32)
                    for mask in pose_results.segmentation_masks:
                        mask_arr = mask.numpy_view()
                        if mask_arr.shape != (FRAME_H, FRAME_W):
                            mask_arr = cv2.resize(mask_arr, (FRAME_W, FRAME_H))
                        combined_mask = np.maximum(combined_mask, mask_arr)
                    
                    # 邊緣平滑化
                    combined_mask = cv2.GaussianBlur(combined_mask, (5, 5), 0)
                    combined_mask_3c = np.expand_dims(combined_mask, axis=-1)
                    
                    # 混合人體前景與自訂背景
                    frame = (frame * combined_mask_3c + bg_resized * (1 - combined_mask_3c)).astype(np.uint8)
                # ---------------------------------------
 
                if pose_results and pose_results.pose_landmarks:
                    for idx, pose in enumerate(pose_results.pose_landmarks):
                        # 抓取肩膀、手腕，並新增頭部(0)、手肘(13,14)與腳踝(27,28)
                        left_shoulder = pose[11]
                        right_shoulder = pose[12]
                        left_wrist = pose[15]
                        right_wrist = pose[16]
                        nose = pose[0]
                        left_elbow = pose[13]
                        right_elbow = pose[14]
                        left_ankle = pose[27]
                        right_ankle = pose[28]
                        
                        # 映射座標
                        lsx, lsy = int(left_shoulder.x * FRAME_W), int(left_shoulder.y * FRAME_H)
                        rsx, rsy = int(right_shoulder.x * FRAME_W), int(right_shoulder.y * FRAME_H)
                        lwx, lwy = int(left_wrist.x * FRAME_W), int(left_wrist.y * FRAME_H)
                        rwx, rwy = int(right_wrist.x * FRAME_W), int(right_wrist.y * FRAME_H)
                        
                        # 儲存左右手腕位置用於重力磁鐵
                        player_hands.append((lwx, lwy))
                        player_hands.append((rwx, rwy))
                        
                        # 將頭部判定點往上平移 100 像素，從鼻子移至額頭/頭頂區域
                        nx, ny = int(nose.x * FRAME_W), int(nose.y * FRAME_H) - 100
                        player_heads.append((nx, ny))
                        lex, ley = int(left_elbow.x * FRAME_W), int(left_elbow.y * FRAME_H)
                        rex, rey = int(right_elbow.x * FRAME_W), int(right_elbow.y * FRAME_H)
                        lax, lay = int(left_ankle.x * FRAME_W), int(left_ankle.y * FRAME_H)
                        rax, ray = int(right_ankle.x * FRAME_W), int(right_ankle.y * FRAME_H)
                        
                        # 計算身體中心 (以肩膀中心替代)
                        bx, by = (lsx + rsx) // 2, (lsy + rsy) // 2
                        
                        # 顏色區分玩家一與玩家二
                        body_color = (0, 255, 0) if idx == 0 else (200, 150, 0)
                        
                        # --- 數位傀儡 (Digital Puppetry) 繪製與碰撞映射 ---
                        
                        # 1. 身體 Avatar (圓角矩形且內部深色微透明)
                        player_points.append((bx, by, 45)) # 半徑 45 的防守範圍
                        draw_rounded_rect(frame, (bx - 40, by - 55), (bx + 40, by + 55), (body_color[0]//4, body_color[1]//4, body_color[2]//4), -1, r=12)
                        draw_rounded_rect(frame, (bx - 40, by - 55), (bx + 40, by + 55), body_color, 2, r=12)
                        draw_text(frame, f"P{idx+1}", (bx - 15, by - 65), 0.6, body_color, 1)
                        
                        # 2. 左手防守手套 (紅色發光霓虹圓)
                        player_points.append((lwx, lwy, 35))
                        draw_glow_circle(frame, lwx, lwy, 30, (0, 0, 255), 2, glow_factor=3)
                        if is_shield_active:
                            # 繪製強烈吸引黃金引力圈
                            pulse = int(math.sin(time.time() * 15) * 8)
                            draw_glow_circle(frame, lwx, lwy, 45 + pulse, shield_glow_color, 2, glow_factor=4)
                        cv2.circle(frame, (lwx, lwy), 25, (100, 100, 255), -1, cv2.LINE_AA)
                        
                        # 3. 右手防守手套 (藍色發光霓虹圓)
                        player_points.append((rwx, rwy, 35))
                        draw_glow_circle(frame, rwx, rwy, 30, (255, 0, 0), 2, glow_factor=3)
                        if is_shield_active:
                            # 繪製強烈吸引黃金引力圈
                            pulse = int(math.sin(time.time() * 15) * 8)
                            draw_glow_circle(frame, rwx, rwy, 45 + pulse, shield_glow_color, 2, glow_factor=4)
                        cv2.circle(frame, (rwx, rwy), 25, (255, 100, 100), -1, cv2.LINE_AA)
                        
                        # 4. 頭部頂球點 (橘黃色發光霓虹圓)
                        player_points.append((nx, ny, 35))
                        draw_glow_circle(frame, nx, ny, 30, (0, 165, 255), 2, glow_factor=3)
                        cv2.circle(frame, (nx, ny), 25, (100, 200, 255), -1, cv2.LINE_AA)
                        draw_text(frame, "HEAD", (nx - 20, ny - 45), 0.4, (0, 165, 255), 1)
                        
                        # 5. 手肘輔助防守點 (空心發光圓，填補手臂空隙)
                        player_points.append((lex, ley, 25))
                        draw_glow_circle(frame, lex, ley, 22, (0, 0, 255), 1, glow_factor=2)
                        player_points.append((rex, rey, 25))
                        draw_glow_circle(frame, rex, rey, 22, (255, 0, 0), 1, glow_factor=2)
                        
                        # 6. 雙腳踢球點 (青黃色發光圓)
                        player_points.append((lax, lay, 35))
                        draw_glow_circle(frame, lax, lay, 30, (255, 255, 0), 2, glow_factor=3)
                        cv2.circle(frame, (lax, lay), 25, (200, 255, 200), -1, cv2.LINE_AA)
                        
                        player_points.append((rax, ray, 35))
                        draw_glow_circle(frame, rax, ray, 30, (255, 255, 0), 2, glow_factor=3)
                        cv2.circle(frame, (rax, ray), 25, (200, 255, 200), -1, cv2.LINE_AA)

                        # 7. 手勢技能偵測：雙手手腕交叉 (發動全螢幕衝擊波)
                        if skill_cooldown <= 0:
                            wrist_dist = np.hypot(lwx - rwx, lwy - rwy)
                            if wrist_dist < 60:
                                # 觸發清場大絕招
                                balls.clear()
                                flash_timer = 15
                                flash_color = (255, 255, 255)
                                shake_timer = 20
                                score += 50
                                speak('Ultimate Active!')
                                effects.append({'text': f'P{idx+1} ULTIMATE WAVES!', 'x': bx - 100, 'y': by, 'color': (0, 255, 255), 'life': 60, 'vx': 0, 'vy': -1.0})
                                hit_stop_timer = 8
                                skill_cooldown = 300  # 冷卻約 10 秒 (假設 30 FPS)
                                if sounds['hit_bomb']: sounds['hit_bomb'].play()
                                
                                # 產生一個全螢幕衝擊波
                                shockwaves.append({
                                    'cx': bx, 'cy': by,
                                    'r': 10.0, 'max_r': float(max(FRAME_W, FRAME_H) * 1.2),
                                    'color': (255, 255, 0),  # 霓虹青綠色
                                    'thickness': 8,
                                    'life': 1.0,
                                    'speed': 18.0
                                })
                                
                                # 產生大範圍放射粒子特效
                                for _ in range(40):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed_pt = random.uniform(5, 20)
                                    particles.append({
                                        'x': float(bx), 'y': float(by),
                                        'vx': speed_pt * math.cos(angle), 'vy': speed_pt * math.sin(angle),
                                        'color': (0, 255, 255), 'radius': random.randint(3, 8),
                                        'life': 1.0, 'decay': random.uniform(0.01, 0.04)
                                    })
                                    
                        # 新手勢技能：雙手平舉 T-Pose (發動子彈時間)
                        if skill_cooldown <= 0:
                            if abs(lwy - lsy) < 60 and abs(rwy - rsy) < 60 and abs(lwx - rwx) > 300:
                                bullet_time_timer = time.time() + 3.0 # 持續 3 秒
                                skill_cooldown = 450 # 共享冷卻 15 秒
                                speak('Bullet Time!')
                                effects.append({'text': f'P{idx+1} BULLET TIME!', 'x': bx - 100, 'y': by - 80, 'color': (255, 100, 255), 'life': 60, 'vx': 0, 'vy': -1.0})
                                hit_stop_timer = 5
                                if sounds['hit_ice']: sounds['hit_ice'].play()
                                for _ in range(30):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed_pt = random.uniform(3, 8)
                                    particles.append({
                                        'x': float(bx), 'y': float(by),
                                        'vx': speed_pt * math.cos(angle), 'vy': speed_pt * math.sin(angle),
                                        'color': (255, 100, 255), 'radius': random.randint(3, 6),
                                        'life': 1.0, 'decay': random.uniform(0.02, 0.04)
                                    })

                        # 8. 手勢技能偵測：雙手高舉過頭 (發動重力吸附護盾)
                        if shield_cooldown <= 0:
                            if lwy < ny and rwy < ny:
                                shield_timer = time.time() + 3.0 # 持續 3 秒
                                shield_cooldown = 450 # 冷卻約 15 秒 (假設 30 FPS)
                                effects.append({'text': f'P{idx+1} GRAVITY SHIELD ACTIVE!', 'x': bx - 160, 'y': by - 80, 'color': (255, 255, 100), 'life': 60, 'vx': 0, 'vy': -1.0})
                                hit_stop_timer = 5
                                if sounds['hit_ice']: sounds['hit_ice'].play()
                                
                                # 噴發一圈護盾發光粒子
                                for _ in range(25):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed_pt = random.uniform(3, 8)
                                    particles.append({
                                        'x': float(bx), 'y': float(by),
                                        'vx': speed_pt * math.cos(angle), 'vy': speed_pt * math.sin(angle),
                                        'color': (255, 255, 100), 'radius': random.randint(3, 6),
                                        'life': 1.0, 'decay': random.uniform(0.02, 0.04)
                                    })
            else:
                # 傳統 MOG2 背景相減法 + 霓虹邊框繪製
                fgMask = backSub.apply(frame)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
                
                # --- 背景替換 (MOG2 備用模式) ---
                if bg_replace:
                    bg_resized = generate_synthwave_grid(FRAME_W, FRAME_H, time.time())
                    mask_blurred = cv2.GaussianBlur(fgMask, (5, 5), 0) / 255.0
                    mask_3c = np.expand_dims(mask_blurred, axis=-1)
                    frame = (frame * mask_3c + bg_resized * (1 - mask_3c)).astype(np.uint8)
                # --------------------------------

                # 尋找移動區域的輪廓
                contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 繪製霓虹科幻防護罩 Outlines
                neon_overlay = np.zeros_like(frame)
                for contour in contours:
                    if cv2.contourArea(contour) > area_thresh:
                        x, y, w, h = cv2.boundingRect(contour)
                        player_boxes.append((x, y, w, h))
                        # 多重描邊實現科幻霓虹發光力場
                        cv2.drawContours(neon_overlay, [contour], -1, (255, 255, 0), 8, cv2.LINE_AA) # 青色外發光
                        cv2.drawContours(neon_overlay, [contour], -1, (0, 255, 0), 3, cv2.LINE_AA)  # 綠色內發光
                        cv2.drawContours(neon_overlay, [contour], -1, (255, 255, 255), 1, cv2.LINE_AA) # 白色核心
                        
                cv2.addWeighted(frame, 1.0, neon_overlay, 0.7, 0, frame)

            # 實作人體霓虹能量粒子微粒發射 (Contour / Joint sparks emission)
            if not USE_MEDIAPIPE:
                for contour in contours:
                    if cv2.contourArea(contour) > area_thresh:
                        if random.random() < 0.25: # 25% 機率產生
                            pt = random.choice(contour)[0]
                            ambient_sparks.append({
                                'x': float(pt[0]),
                                'y': float(pt[1]),
                                'vx': random.uniform(-1.5, 1.5),
                                'vy': random.uniform(-3, -1),
                                'color': (255, 255, 0), # 青藍色能量微粒
                                'radius': random.randint(1, 3),
                                'life': 1.0,
                                'decay': random.uniform(0.04, 0.08)
                            })
            else:
                for px, py, _ in player_points:
                    if random.random() < 0.04: # 每點 4% 機率產生
                        ambient_sparks.append({
                            'x': float(px),
                            'y': float(py),
                            'vx': random.uniform(-1.0, 1.0),
                            'vy': random.uniform(-2.5, -0.5),
                            'color': (0, 255, 255), # 金黃色能量微粒
                            'radius': random.randint(1, 3),
                            'life': 1.0,
                            'decay': random.uniform(0.04, 0.08)
                        })

            # 若有頓幀 (Hit Stop)，跳過遊戲邏輯更新
            update_physics = True
            if hit_stop_timer > 0:
                hit_stop_timer -= 1
                update_physics = False
                last_spawn_time += (1.0 / 30.0) # 補償暫停的時間避免生成錯亂
                if ice_timer > 0: ice_timer += (1.0 / 30.0)
                if shield_timer > 0: shield_timer += (1.0 / 30.0)
                if bullet_time_timer > 0: bullet_time_timer += (1.0 / 30.0)
                if fever_timer > 0: fever_timer += (1.0 / 30.0)

            # Boss 觸發邏輯
            if score >= next_boss_score and not boss['active'] and not boss['dead']:
                boss['active'] = True
                boss['hp'] = 300
                boss['max_hp'] = 300
                boss['x'] = FRAME_W // 2
                boss['y'] = 120
                boss['vx'] = 4.0 if game_difficulty == 1 else 6.0
                boss['last_attack'] = time.time()
                shake_timer = 20
                flash_timer = 15
                flash_color = (0, 0, 255)
                if sounds['hit_bomb']: sounds['hit_bomb'].play()
                speak('Warning, Boss Approaching')
                effects.append({'text': 'WARNING: BOSS APPROACHING!', 'x': FRAME_W//2 - 200, 'y': FRAME_H//2, 'color': (0, 0, 255), 'life': 90, 'vx': 0, 'vy': -1.0})

            # 檢查並觸發 Fever Mode
            is_fever_active = fever_timer > 0 and time.time() < fever_timer
            if combo >= 20 and not is_fever_active:
                fever_timer = time.time() + 8.0
                is_fever_active = True
                effects.append({'text': 'FEVER MODE!', 'x': FRAME_W//2 - 150, 'y': FRAME_H//2, 'color': (0, 215, 255), 'life': 90, 'vx': 0, 'vy': -1.0})
                if sounds['hit_gold']: sounds['hit_gold'].play()

            # 3. 遊戲邏輯 - 虛擬球隨機生成
            current_time = time.time()
            if update_physics and (current_time - last_spawn_time > current_spawn_interval):
                if is_fever_active:
                    b_type = random.choice(['gold', 'gold', 'heart']) # Fever 期間只會掉落高分球與愛心
                else:
                    b_type = get_random_ball_type()
                
                if game_mode in (1, 2):
                    new_x = random.randint(0, FRAME_W - BALL_WIDTH)
                    balls.append({
                        'x': new_x, 'y': -BALL_HEIGHT, 
                        'dx': 0, 'dy': current_speed, 
                        'type': b_type,
                        'trail': []
                    })
                else:
                    # 模式 3: 球從四面八方出現並朝中心前進
                    edge = random.choice(['top', 'bottom', 'left', 'right'])
                    if edge == 'top':
                        start_x, start_y = random.randint(0, FRAME_W), -BALL_HEIGHT
                    elif edge == 'bottom':
                        start_x, start_y = random.randint(0, FRAME_W), FRAME_H
                    elif edge == 'left':
                        start_x, start_y = -BALL_WIDTH, random.randint(0, FRAME_H)
                    else: # right
                        start_x, start_y = FRAME_W, random.randint(0, FRAME_H)
                    
                    start_cx = start_x + BALL_WIDTH / 2
                    start_cy = start_y + BALL_HEIGHT / 2
                    target_x, target_y = FRAME_W / 2, FRAME_H / 2
                    
                    dist = np.hypot(target_x - start_cx, target_y - start_cy)
                    if dist > 0:
                        dx = (target_x - start_cx) / dist * current_speed
                        dy = (target_y - start_cy) / dist * current_speed
                    else:
                        dx, dy = 0, current_speed
                        
                    balls.append({
                        'x': start_x, 'y': start_y, 
                        'dx': dx, 'dy': dy, 
                        'type': b_type,
                        'trail': []
                    })

                last_spawn_time = current_time
                current_speed += 0.2
                current_spawn_interval = max(0.5, current_spawn_interval - 0.05)

            # 4. 遊戲邏輯 - 物理更新與碰撞偵測
            is_frozen = (time.time() < ice_timer)
            is_shield_active = (time.time() < shield_timer)
            is_bullet_time = (time.time() < bullet_time_timer)
            
            speed_mult = 1.0
            if is_frozen: speed_mult = 0.4
            elif is_bullet_time: speed_mult = 0.2
            
            for ball in balls[:]:
                if not update_physics:
                    break # 頓幀時完全不更新球體的物理與碰撞

                # 追蹤球 (Homing) 物理：逐漸修正 dx, dy 指向最近的玩家頭部
                if ball['type'] == 'homing' and len(player_heads) > 0:
                    ball_cx = ball['x'] + BALL_WIDTH / 2
                    ball_cy = ball['y'] + BALL_HEIGHT / 2
                    nearest_head = min(player_heads, key=lambda h: np.hypot(h[0] - ball_cx, h[1] - ball_cy))
                    hx, hy = nearest_head
                    dist = np.hypot(hx - ball_cx, hy - ball_cy)
                    if dist > 10:
                        speed = np.hypot(ball['dx'], ball['dy'])
                        speed = max(speed, current_speed * 1.2) # 追蹤球稍微快一點
                        target_dx = (hx - ball_cx) / dist * speed
                        target_dy = (hy - ball_cy) / dist * speed
                        ball['dx'] = ball['dx'] * 0.96 + target_dx * 0.04
                        ball['dy'] = ball['dy'] * 0.96 + target_dy * 0.04

                # 重力磁場吸附物理：若護盾啟動，將非炸彈球向最近的手部拉引
                if is_shield_active and ball['type'] != 'bomb' and len(player_hands) > 0:
                    ball_cx = ball['x'] + BALL_WIDTH / 2
                    ball_cy = ball['y'] + BALL_HEIGHT / 2
                    nearest_hand = min(player_hands, key=lambda h: np.hypot(h[0] - ball_cx, h[1] - ball_cy))
                    hx, hy = nearest_hand
                    
                    dx_diff = hx - ball_cx
                    dy_diff = hy - ball_cy
                    dist = np.hypot(dx_diff, dy_diff)
                    if dist > 5:
                        attract_speed = 9.0  # 強力磁吸速度
                        ball['dx'] = (dx_diff / dist) * attract_speed
                        ball['dy'] = (dy_diff / dist) * attract_speed

                # 紀錄拖尾歷史位置
                ball['trail'].append((ball['x'], ball['y']))
                if len(ball['trail']) > 8:
                    ball['trail'].pop(0)
                    
                if ball.get('has_gravity', False):
                    ball['dy'] += 0.3 * speed_mult
                    if ball['x'] < 0:
                        ball['x'] = 0
                        ball['dx'] *= -1
                    elif ball['x'] > FRAME_W - BALL_WIDTH:
                        ball['x'] = FRAME_W - BALL_WIDTH
                        ball['dx'] *= -1

                # 更新位置
                ball['x'] += ball['dx'] * speed_mult
                ball['y'] += ball['dy'] * speed_mult

                # 全局越界清除 (避免球體無限飄移 Memory Leak)
                if ball['x'] < -300 or ball['x'] > FRAME_W + 300 or ball['y'] < -500 or ball['y'] > FRAME_H + 300:
                    balls.remove(ball)
                    continue
                
                if ball.get('deflected', False) and boss['active']:
                    dist = np.hypot(ball['x'] - boss['x'], ball['y'] - boss['y'])
                    if dist < 70:
                        boss['hp'] -= 30
                        shake_timer = 5
                        flash_timer = 3
                        flash_color = (255, 255, 255)
                        spawn_particles(particles, ball['x'], ball['y'], (0, 255, 255))
                        if sounds['hit_bomb']: sounds['hit_bomb'].play()
                        balls.remove(ball)
                        
                        if boss['hp'] <= 0:
                            boss['active'] = False
                            boss['dead'] = False
                            score += 500
                            next_boss_score = score + 300
                            cyber_coins += 50
                            shake_timer = 30
                            flash_timer = 20
                            flash_color = (0, 0, 255)
                            speak('Boss Destroyed, excellent')
                            effects.append({'text': 'BOSS DESTROYED! +500 PTS / +50 COINS', 'x': FRAME_W//2 - 250, 'y': FRAME_H//2, 'color': (0, 255, 255), 'life': 90, 'vx': 0, 'vy': -2.0})
                            for _ in range(3):
                                shockwaves.append({
                                    'cx': boss['x'], 'cy': boss['y'],
                                    'r': 10.0, 'max_r': float(max(FRAME_W, FRAME_H)),
                                    'color': (0, 0, 255),
                                    'thickness': 15,
                                    'life': 1.0,
                                    'speed': random.uniform(15, 25)
                                })
                        continue
                        
                if ball.get('deflected', False) and ball['y'] < -50:
                    balls.remove(ball)
                    continue
                
                # 碰撞偵測
                hit = False
                if USE_MEDIAPIPE:
                    # MediaPipe 模式：精準的「點與圓形」碰撞判定
                    ball_cx = ball['x'] + BALL_WIDTH / 2
                    ball_cy = ball['y'] + BALL_HEIGHT / 2
                    ball_radius = BALL_WIDTH / 2
                    for px, py, pr in player_points:
                        if np.hypot(ball_cx - px, ball_cy - py) < (ball_radius + pr):
                            hit = True
                            break
                else:
                    # 傳統模式：AABB 碰撞框判定
                    for bx, by, bw, bh in player_boxes:
                        if (ball['x'] < bx + bw and ball['x'] + BALL_WIDTH > bx and
                            ball['y'] < by + bh and ball['y'] + BALL_HEIGHT > by):
                            hit = True
                            break
                
                # 碰撞事件處理
                if hit and not ball.get('deflected', False):
                    b_type = ball['type']
                    bx, by = ball['x'], ball['y']
                    
                    # 計算連擊倍率
                    mult = 1
                    if combo >= 20: mult = 5
                    elif combo >= 10: mult = 3
                    elif combo >= 5: mult = 2
                    
                    if b_type == 'normal':
                        pts_earned = 10 * mult
                        score += pts_earned
                        combo += 1
                        msg = random.choice(["NICE!", "GREAT!", "GOOD!"]) if combo > 3 else ""
                        text_str = f'+{pts_earned} {msg}' if msg else f'+{pts_earned}'
                        effects.append({'text': text_str, 'x': bx + random.randint(-15, 15), 'y': by, 'color': (0, 255, 0), 'life': 30, 'vx': random.uniform(-0.5, 0.5), 'vy': -3.0})
                        hit_stop_timer = 2
                        spawn_particles(particles, bx, by, (200, 200, 200)) # 灰色煙霧粒子
                        if sounds['hit']: sounds['hit'].play()
                        
                        if boss['active']:
                            ball['dy'] = -20
                            ball['dx'] = random.uniform(-8, 8)
                            ball['deflected'] = True
                        
                    elif b_type == 'gold':
                        # 黃金球：獲得 3 倍基本分並乘上連擊加成！
                        pts_earned = 30 * mult
                        score += pts_earned
                        combo += 1
                        coins_earned = 5
                        cyber_coins += coins_earned
                        flash_timer = 7 # 耀眼金色閃屏
                        flash_color = (0, 215, 255)
                        effects.append({'text': f'PERFECT! +{pts_earned}', 'x': bx + random.randint(-15, 15), 'y': by, 'color': (0, 215, 255), 'life': 40, 'vx': random.uniform(-1.0, 1.0), 'vy': -4.0})
                        effects.append({'text': f'+{coins_earned} COINS!', 'x': bx + random.randint(-15, 15), 'y': by + 20, 'color': (0, 215, 255), 'life': 40, 'vx': random.uniform(-1.0, 1.0), 'vy': -4.0})
                        hit_stop_timer = 5
                        spawn_particles(particles, bx, by, (0, 215, 255)) # 黃金火花粒子
                        if sounds['hit_gold']: sounds['hit_gold'].play()
                        
                    elif b_type == 'bomb':
                        # 炸彈球：扣 20 分與 1 點生命，中斷連擊！
                        lives -= 1
                        score = max(0, score - 20)
                        combo = 0
                        shake_timer = 12 # 劇烈震屏
                        flash_timer = 8  # 鮮紅閃光
                        flash_color = (0, 0, 255)
                        effects.append({'text': 'BOMB! -20', 'x': bx, 'y': by, 'color': (0, 0, 255), 'life': 45, 'vx': 0, 'vy': -2.0})
                        hit_stop_timer = 3
                        spawn_particles(particles, bx, by, (0, 100, 255)) # 橘紅色爆炸粒子
                        if sounds['hit_bomb']: sounds['hit_bomb'].play()
                        if lives <= 0:
                            game_state = STATE_GAMEOVER
                            glitch_timer = 20
                            speak('Game Over')
                            
                    elif b_type == 'ice':
                        # 冰凍球：獲得 10 分並觸發減速 3 秒
                        score += 10
                        combo += 1
                        ice_timer = time.time() + 3.0
                        flash_timer = 7 # 冰藍色閃屏
                        flash_color = (255, 255, 100)
                        effects.append({'text': 'FREEZE!', 'x': bx, 'y': by, 'color': (255, 255, 100), 'life': 30, 'vx': 0, 'vy': -2.0})
                        hit_stop_timer = 3
                        spawn_particles(particles, bx, by, (255, 255, 100)) # 青藍色冰晶粒子
                        if sounds['hit_ice']: sounds['hit_ice'].play()
                        
                    elif b_type == 'heart':
                        # 愛心球：增加生命值，最高 5 點
                        if lives < 5:
                            lives += 1
                            effects.append({'text': 'LIFE UP!', 'x': bx, 'y': by, 'color': (150, 50, 255), 'life': 35, 'vx': 0, 'vy': -2.0})
                        else:
                            effects.append({'text': 'MAX LIFE!', 'x': bx, 'y': by, 'color': (150, 50, 255), 'life': 35, 'vx': 0, 'vy': -2.0})
                        hit_stop_timer = 2
                        score += 10
                        combo += 1
                        flash_timer = 7 # 粉紅色閃屏
                        flash_color = (150, 50, 255)
                        spawn_particles(particles, bx, by, (150, 50, 255)) # 粉紅色愛心粒子
                        if sounds['hit_heart']: sounds['hit_heart'].play()

                    elif b_type == 'split':
                        score += 5
                        effects.append({'text': 'SPLIT!', 'x': bx, 'y': by, 'color': (50, 255, 50), 'life': 30, 'vx': 0, 'vy': -2.0})
                        hit_stop_timer = 2
                        if sounds['hit']: sounds['hit'].play()
                        balls.append({'x': bx, 'y': by, 'dx': -8, 'dy': -8, 'type': 'normal', 'trail': [], 'has_gravity': True})
                        balls.append({'x': bx, 'y': by, 'dx': 8, 'dy': -8, 'type': 'normal', 'trail': [], 'has_gravity': True})

                    elif b_type == 'homing':
                        pts_earned = 15 * mult
                        score += pts_earned
                        combo += 1
                        effects.append({'text': f'INTERCEPTED! +{pts_earned}', 'x': bx, 'y': by, 'color': (255, 50, 50), 'life': 35, 'vx': 0, 'vy': -3.0})
                        hit_stop_timer = 3
                        spawn_particles(particles, bx, by, (255, 50, 50))
                        if sounds['hit']: sounds['hit'].play()
                        
                    if not ball.get('deflected', False):
                        balls.remove(ball)
                else:
                    # 漏接判定
                    miss = False
                    if game_mode in (1, 2):
                        if ball['y'] > FRAME_H:
                            miss = True
                    else:
                        # 模式 3: 若球接近正中心則漏接
                        cx, cy = ball['x'] + BALL_WIDTH/2, ball['y'] + BALL_HEIGHT/2
                        if np.hypot(cx - FRAME_W/2, cy - FRAME_H/2) < 50:
                            miss = True
                            
                    if miss:
                        # 炸彈球即使漏接也不會扣生命值（因為本來就要閃躲炸彈！）
                        if ball['type'] != 'bomb':
                            lives -= 1
                            combo = 0 # 漏接中斷連擊
                            shake_timer = 8 # 漏接震屏
                            flash_timer = 6 # 漏接紅色警報閃爍
                            flash_color = (0, 0, 255)
                            if sounds['miss']: sounds['miss'].play()
                            if lives <= 0:
                                game_state = STATE_GAMEOVER
                                glitch_timer = 20
                                speak('Game Over')
                        balls.remove(ball)

            # 5. 畫面渲染
            # --- Boss Update & Render ---
            if boss['active']:
                if update_physics:
                    boss['x'] += boss['vx']
                    if boss['x'] < 100 or boss['x'] > FRAME_W - 100:
                        boss['vx'] *= -1
                    
                    if time.time() - boss['last_attack'] > 2.0:
                        boss['last_attack'] = time.time()
                        balls.append({
                            'x': boss['x'], 'y': boss['y'] + 50, 
                            'dx': random.choice([-3, -1, 1, 3]), 'dy': current_speed * 1.2, 
                            'type': 'bomb',
                            'trail': []
                        })
                
                draw_glow_circle(frame, int(boss['x']), int(boss['y']), 60, (0, 0, 255), 4, glow_factor=5)
                cv2.circle(frame, (int(boss['x']), int(boss['y'])), 50, (30, 30, 30), -1, cv2.LINE_AA)
                pulse_boss = int(math.sin(time.time() * 10) * 10)
                cv2.circle(frame, (int(boss['x']), int(boss['y'])), 30 + pulse_boss, (0, 0, 255), -1, cv2.LINE_AA)
                draw_text(frame, "CORE", (int(boss['x']) - 25, int(boss['y']) - 70), 0.5, (0, 0, 255), 1)
                
                hp_ratio = boss['hp'] / boss['max_hp']
                hp_w = 200
                draw_rounded_rect(frame, (int(boss['x']) - hp_w//2, int(boss['y']) - 90), (int(boss['x']) + hp_w//2, int(boss['y']) - 80), (50, 50, 50), fill=True, r=4)
                if hp_ratio > 0:
                    draw_rounded_rect(frame, (int(boss['x']) - hp_w//2, int(boss['y']) - 90), (int(boss['x']) - hp_w//2 + int(hp_w * hp_ratio), int(boss['y']) - 80), (0, 0, 255), fill=True, r=4)

            # 模式 3 中心防守渲染 (炫目的科技感雷達掃描線)
            if game_mode == 3:
                cx, cy = int(FRAME_W//2), int(FRAME_H//2)
                pulse = int(math.sin(time.time() * 8) * 8)
                cv2.circle(frame, (cx, cy), 50 + pulse, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 35 - pulse//2, (0, 165, 255), 2, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 15, (0, 0, 255), -1, cv2.LINE_AA)
                cv2.line(frame, (cx - 60, cy), (cx + 60, cy), (0, 255, 255), 1, cv2.LINE_AA)
                cv2.line(frame, (cx, cy - 60), (cx, cy + 60), (0, 255, 255), 1, cv2.LINE_AA)
                
                # 旋轉雷達掃描線 (Rotating radar sweep line)
                sweep_angle = time.time() * 4.0
                sx = int(cx + (50 + pulse) * math.cos(sweep_angle))
                sy = int(cy + (50 + pulse) * math.sin(sweep_angle))
                cv2.line(frame, (cx, cy), (sx, sy), (0, 255, 255), 1, cv2.LINE_AA)

            # 繪製球體拖尾 (高質感霓虹動態殘影)
            for ball in balls:
                if len(ball['trail']) > 1:
                    pts = np.array([[(tx + BALL_WIDTH/2, ty + BALL_HEIGHT/2)] for tx, ty in ball['trail']], np.int32)
                    trail_color = (255, 255, 255)
                    if ball['type'] == 'gold': trail_color = (0, 215, 255)
                    elif ball['type'] == 'bomb': trail_color = (0, 0, 255)
                    elif ball['type'] == 'ice': trail_color = (255, 255, 100)
                    elif ball['type'] == 'heart': trail_color = (150, 50, 255)
                    elif ball['type'] == 'normal': trail_color = (0, 255, 255)
                    elif ball['type'] == 'split': trail_color = (50, 255, 50)
                    elif ball['type'] == 'homing': trail_color = (0, 0, 255)
                    # 繪製發光連線
                    cv2.polylines(frame, [pts], False, trail_color, 4, cv2.LINE_AA)
                    cv2.polylines(frame, [pts], False, (255, 255, 255), 1, cv2.LINE_AA)

                for idx, (tx, ty) in enumerate(ball['trail'][:-1]):
                    # 越久以前的座標越透明
                    alpha_factor = (idx + 1) / len(ball['trail']) * 0.5
                    frame = overlay_image_alpha(frame, ball_imgs[ball['type']], tx, ty, alpha_factor)
                
                # 繪製主球體
                frame = overlay_image_alpha(frame, ball_imgs[ball['type']], ball['x'], ball['y'])

            # 繪製粒子物理運動 (格擋爆炸特效)
            for p in particles[:]:
                if update_physics:
                    p['x'] += p['vx']
                    p['y'] += p['vy']
                    p['vy'] += 0.15  # 地心引力加速度
                    p['life'] -= p['decay']
                
                if p['life'] <= 0:
                    particles.remove(p)
                else:
                    r = int(p['radius'] * p['life'])
                    if r > 0:
                        cv2.circle(frame, (int(p['x']), int(p['y'])), r, p['color'], -1, cv2.LINE_AA)

            # 繪製發射出的環境能量微粒
            for s in ambient_sparks[:]:
                if update_physics:
                    s['x'] += s['vx']
                    s['y'] += s['vy']
                    s['life'] -= s['decay']
                if s['life'] <= 0:
                    ambient_sparks.remove(s)
                else:
                    r = int(s['radius'] * s['life'])
                    if r > 0:
                        cv2.circle(frame, (int(s['x']), int(s['y'])), r, s['color'], -1, cv2.LINE_AA)

            # 繪製並更新全螢幕大絕招擴散衝擊波 (Shockwave Rings)
            for sw in shockwaves[:]:
                if update_physics:
                    sw['r'] += sw['speed']
                    # 隨著擴散生命值 decay
                    sw['life'] = max(0.0, 1.0 - (sw['r'] / sw['max_r']))
                if sw['life'] <= 0 or sw['r'] >= sw['max_r']:
                    shockwaves.remove(sw)
                else:
                    thickness = int(max(1, sw['thickness'] * sw['life']))
                    # 用透明融合繪製發光的衝擊波外圈
                    overlay = frame.copy()
                    cv2.circle(overlay, (int(sw['cx']), int(sw['cy'])), int(sw['r']), sw['color'], thickness + 4, cv2.LINE_AA)
                    cv2.addWeighted(overlay, sw['life'] * 0.4, frame, 1.0 - sw['life'] * 0.4, 0, frame)
                    cv2.circle(frame, (int(sw['cx']), int(sw['cy'])), int(sw['r']), (255, 255, 255), max(1, thickness // 2), cv2.LINE_AA)

            # Combo 高連擊特殊能量火花特效 (Combo Spark Trail)
            if combo >= 5:
                # 隨機在底部邊緣產生上升粒子，數量隨 combo 增加
                spawn_count = min(3, combo // 5)
                for _ in range(spawn_count):
                    if random.random() < 0.3:
                        ambient_sparks.append({
                            'x': float(random.randint(50, FRAME_W - 50)),
                            'y': float(FRAME_H - 10),
                            'vx': random.uniform(-1.0, 1.0),
                            'vy': random.uniform(-6.0, -3.0) - (combo * 0.1), # combo 越高衝得越快
                            'color': (0, 165, 255) if random.random() < 0.5 else (0, 215, 255), # 橘金/金黃色火花
                            'radius': random.randint(2, 4),
                            'life': 1.0,
                            'decay': random.uniform(0.02, 0.04)
                        })

            # 繪製飄浮分數與文字特效 (物理飄浮與淡出)
            for effect in effects[:]:
                vx = effect.get('vx', 0)
                vy = effect.get('vy', -2.0)
                
                if 'max_life' not in effect:
                    effect['max_life'] = effect['life']
                
                if update_physics:
                    effect['x'] += vx
                    effect['y'] += vy
                    effect['vy'] = min(0.5, effect['vy'] + 0.1)  # 模擬空氣阻力，減速向上漂浮
                    effect['life'] -= 1
                
                # 使用 life 計算縮放以實現「Pop (彈出)」效果 (真實彈跳與淡出曲線)
                scale = 1.0
                max_life = effect['max_life']
                
                life_ratio = effect['life'] / max_life if max_life > 0 else 0
                if life_ratio > 0.8:
                    # 剛出現時從 1.5 快速縮小回 1.0 (真實 Pop)
                    pop_factor = (life_ratio - 0.8) * 5.0 # 0.0 到 1.0
                    scale = 1.0 + pop_factor * 0.5 
                
                # 消失前淡出縮小
                if life_ratio < 0.2:
                    scale = max(0.1, life_ratio * 5.0)
                
                draw_text(frame, effect['text'], (int(effect['x']), int(effect['y'])), scale, effect['color'], 2)
                if effect['life'] <= 0:
                    effects.remove(effect)

            # 冰凍邊框特效 overlay
            if is_frozen:
                cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), (255, 200, 100), 8) # 藍色凍結框
                draw_text(frame, "TIME FROZEN", (0, 90), 0.7, (255, 255, 100), 2, center=True)

            if is_bullet_time:
                cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), (255, 100, 255), 12)
                draw_text(frame, "BULLET TIME", (0, 120), 0.9, (255, 100, 255), 3, center=True)

            if is_fever_active:
                pulse_f = int(math.sin(time.time() * 20) * 5)
                cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), (0, 215, 255), 8 + pulse_f)
                draw_text(frame, "FEVER MODE", (0, 150), 1.0, (0, 215, 255), 3, center=True)

            # 重力磁吸護盾文字提示 overlay
            if is_shield_active:
                pulse = int(math.sin(time.time() * 12) * 3)
                draw_text(frame, "GRAVITY SHIELD ACTIVE", (0, 95 + pulse), 0.65, shield_glow_color, 2, center=True)

            # 閃光護盾邊框特效 (Vignette Flash Effect)
            if flash_timer > 0:
                border_thick = int(24 * (flash_timer / 7))
                if border_thick > 0:
                    cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), flash_color, border_thick)
                flash_timer -= 1

            # 磨砂玻璃左上 HUD 面板 (Score, High Score & Skill)
            # 將面板高度擴展至 220 以放置三條極緻技能進度條
            panel_y2 = 220 if USE_MEDIAPIPE else 125
            frame = draw_glass_panel(frame, 15, 15, 295, panel_y2, COLOR_DARK_PANEL, 0.55, COLOR_NEON_TEAL, 1)
            draw_text(frame, f"Score: {score}", (30, 48), 0.7, (255, 255, 255), 2)
            # 即時更新突破紀錄的視覺反饋
            display_high_score = int(max(score, high_score))
            draw_text(frame, f"HI Score: {display_high_score}", (30, 80), 0.55, COLOR_NEON_GOLD, 1)
            
            # 顯示技能冷卻圓環 (Arc Progress)
            if USE_MEDIAPIPE:
                # 1. 大絕招
                ulti_ratio = max(0.0, skill_cooldown / 300.0)
                ulti_color = COLOR_NEON_BLUE if ulti_ratio == 0 else (100, 100, 100)
                
                # 2. 護盾
                shield_ratio = max(0.0, shield_cooldown / 450.0)
                shield_color = COLOR_NEON_GOLD if shield_ratio == 0 else (100, 100, 100)
                
                # 3. 子彈時間
                bullet_ratio = max(0.0, skill_cooldown / 450.0)
                bullet_color = (255, 100, 255) if bullet_ratio == 0 else (100, 100, 100)
                
                skills = [
                    ("ULTI", ulti_ratio, ulti_color, 65, skill_cooldown),
                    ("SHIELD", shield_ratio, shield_color, 155, shield_cooldown),
                    ("BULLET", bullet_ratio, bullet_color, 245, skill_cooldown)
                ]
                
                draw_text(frame, "SKILL COOLDOWNS", (30, 105), 0.45, (255, 255, 255), 1)
                
                for name, ratio, color, cx, raw_cd in skills:
                    cy = 155
                    radius = 28
                    # 繪製底圈
                    cv2.circle(frame, (cx, cy), radius, (40, 40, 40), 5, cv2.LINE_AA)
                    # 繪製進度弧線
                    if ratio < 1.0:
                        end_angle = -90 + (1.0 - ratio) * 360
                        cv2.ellipse(frame, (cx, cy), (radius, radius), 0, -90, end_angle, color, 5, cv2.LINE_AA)
                    if ratio == 0:
                        pulse = int(math.sin(time.time() * 10) * 3)
                        cv2.circle(frame, (cx, cy), radius + pulse, color, 1, cv2.LINE_AA)
                        draw_glow_circle(frame, cx, cy, radius, color, 2, glow_factor=2)
                    
                    # 顯示文字
                    text_scale = 0.4
                    draw_text(frame, name, (cx - 18, cy + 50), text_scale, color, 1)
                    if ratio > 0:
                        cd_time = raw_cd // 30 + 1
                        draw_text(frame, str(cd_time), (cx - 5, cy + 5), 0.5, (255, 255, 255), 1)
                    else:
                        draw_text(frame, "RDY", (cx - 15, cy + 5), 0.4, (255, 255, 255), 1)

            # 顯示生命值 HUD 面板 ( procedural 愛心繪製取代文字 )
            panel_w = 95 + lives * 32
            panel_x1 = FRAME_W - panel_w - 15
            lives_color = COLOR_NEON_MAGENTA if lives == 1 and (int(time.time() * 5) % 2 == 0) else COLOR_NEON_TEAL
            
            frame = draw_glass_panel(frame, panel_x1, 15, FRAME_W - 15, 62, COLOR_DARK_PANEL, 0.55, lives_color, 1)
            draw_text(frame, "LIVES", (panel_x1 + 15, 47), 0.55, (255, 255, 255), 1)
            
            # 依生命值繪製動態跳動與發光的向量愛心
            for i in range(lives):
                hx = panel_x1 + 80 + i * 32
                hy = 36
                # 若僅剩一命，愛心會劇烈抖動
                vibrate = random.randint(-1, 1) if lives == 1 else 0
                pulse_sz = int(math.sin(time.time() * 8 + i) * 2)
                draw_heart(frame, hx + vibrate, hy + vibrate, 20 + pulse_sz, COLOR_NEON_MAGENTA)

            # 顯示 Combo 連擊磨砂玻璃面板 (有呼吸燈抖動特效)
            if combo >= 3:
                base_scale = 0.8
                anim_speed = 12
                combo_color = (0, 215, 255)
                
                mult = 1
                if combo >= 20: 
                    mult = 5
                    base_scale = 1.3
                    anim_speed = 25
                    combo_color = COLOR_NEON_MAGENTA
                elif combo >= 10: 
                    mult = 3
                    base_scale = 1.0
                    anim_speed = 18
                    combo_color = COLOR_NEON_GOLD
                elif combo >= 5: 
                    mult = 2
                
                pulse_scale = base_scale + (0.15 * mult) * math.sin(time.time() * anim_speed)
                shake_x = int(math.sin(time.time() * 30) * mult * 2) if combo >= 10 else 0
                shake_y = int(math.cos(time.time() * 25) * mult * 2) if combo >= 10 else 0
                
                combo_text = f"{combo} COMBO!"
                combo_thickness = 3 + (mult // 2)
                combo_size = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_DUPLEX, pulse_scale, combo_thickness)[0]
                
                cx1 = (FRAME_W - combo_size[0]) // 2 - 30 + shake_x
                cx2 = (FRAME_W + combo_size[0]) // 2 + 30 + shake_x
                cy1 = 80 + shake_y
                cy2 = 145 + shake_y
                
                if mult > 1:
                    cy2 = 185 + shake_y # 面板增高以容納乘數
                    
                frame = draw_glass_panel(frame, cx1, cy1, cx2, cy2, (20, 30, 20), 0.6, combo_color, 2)
                draw_text(frame, combo_text, (cx1 + 30, 120 + shake_y), pulse_scale, combo_color, combo_thickness)
                if mult > 1:
                    draw_text(frame, f"{mult}X SCORE MULTIPLIER", (0, 168 + shake_y), 0.5, (255, 255, 255), 1, center=True)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == 27: # ESC key to surrender/exit to menu
                lives = 0 # Force game over logic to run safely on next frame, or just change state
                game_state = STATE_GAMEOVER
                glitch_timer = 20
                speak('Game Over')
            elif key == ord('b') or key == ord('B'):
                bg_replace = not bg_replace

        elif game_state == STATE_GAMEOVER:
            # 判斷是否打破歷史高分紀錄並儲存
            if not score_saved:
                if score > high_score:
                    high_score = score
                    new_record_broken = True
                
                # 排行榜邏輯
                if score > 0:
                    leaderboard.append(score)
                    leaderboard.sort(reverse=True)
                    leaderboard = leaderboard[:5] # 保持前 5 名
                
                # 儲存進度 (包含分數與代幣與排行榜)
                save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield, 'leaderboard': leaderboard})
                score_saved = True

            # 畫半透明黑色遮罩，使用幽邃的暗紫底色
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (15, 10, 20), -1)
            cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

            # 根據分數決定戰績等級 (Cyberpunk Achievement Rankings)
            if score >= 500:
                rank_str, rank_desc, rank_color = "SS", "GODLIKE GOALKEEPER", COLOR_NEON_GOLD
            elif score >= 300:
                rank_str, rank_desc, rank_color = "S", "WORLD-CLASS KEEPER", COLOR_NEON_BLUE
            elif score >= 150:
                rank_str, rank_desc, rank_color = "A", "IMPERVIOUS WALL", COLOR_NEON_GREEN
            elif score >= 50:
                rank_str, rank_desc, rank_color = "B", "RISING STAR", COLOR_NEON_TEAL
            else:
                rank_str, rank_desc, rank_color = "C", "ROOKIE APPRENTICE", COLOR_NEON_MAGENTA

            # 邊框色彩：破紀錄為高貴金色，否則為魔幻粉紅
            panel_border = COLOR_NEON_GOLD if new_record_broken else COLOR_NEON_MAGENTA
            
            # 繪製遊戲結束大玻璃面板
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, COLOR_DARK_PANEL, 0.6, panel_border, 2)

            # GAME OVER 標題
            draw_text(frame, "GAME OVER", (0, int(FRAME_H * 0.18)), 1.8, COLOR_NEON_MAGENTA, 4, center=True)
            
            # 破紀錄高光特效
            if new_record_broken:
                pulse = int(math.sin(time.time() * 12) * 4)
                draw_text(frame, "★ NEW ALL-TIME HIGH SCORE ★", (0, int(FRAME_H * 0.26) + pulse), 0.8, COLOR_NEON_GOLD, 2, center=True)
            
            # 顯示得分資訊
            draw_text(frame, f"Final Score: {score}", (0, int(FRAME_H * 0.35)), 0.9, (255, 255, 255), 2, center=True)

            # --- 榮譽評級面板 (玻璃子面板) ---
            sub_x1, sub_x2 = FRAME_W // 2 - 220, FRAME_W // 2 + 220
            sub_y1, sub_y2 = int(FRAME_H * 0.42), int(FRAME_H * 0.77)
            frame = draw_glass_panel(frame, sub_x1, sub_y1, sub_x2, sub_y2, (10, 10, 15), 0.45, rank_color, 1, corner_radius=10)
            
            # 繪製大型發光評級字元與動態縮放
            pulse_scale = 2.4 + 0.12 * math.sin(time.time() * 8)
            draw_text(frame, rank_str, (0, int(FRAME_H * 0.63)), pulse_scale, rank_color, 6, center=True)
            draw_text(frame, rank_desc, (0, int(FRAME_H * 0.71)), 0.65, rank_color, 2, center=True)

            # 操作按鍵提示 (動態浮游效果)
            pulse = int(math.sin(time.time() * 8) * 2)
            draw_text(frame, "Press 'r' to Restart  |  'q' to Exit", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_TEAL, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                game_state = STATE_MENU_MODE

        # ------------------------------------------
        # 最終畫面後製 (Post-Processing)
        # ------------------------------------------
        # 套用 CRT 掃描線與四角暗角特效，增強 Cyberpunk 沉浸感 (使用預先計算的 Mask 與 OpenCV 加速)
        frame = cv2.multiply(frame.astype(np.float32), FINAL_OVERLAY_MASK).astype(np.uint8)

        # 🎬 死亡雜訊 Glitch 渲染
        if glitch_timer > 0:
            glitch_timer -= 1
            # 隨機切割畫面並偏移
            num_slices = random.randint(5, 15)
            for _ in range(num_slices):
                y_start = random.randint(0, FRAME_H - 10)
                slice_h = random.randint(5, 40)
                y_end = min(FRAME_H, y_start + slice_h)
                x_offset = random.randint(-40, 40)
                
                if x_offset > 0:
                    frame[y_start:y_end, x_offset:] = frame[y_start:y_end, :-x_offset].copy()
                    frame[y_start:y_end, :x_offset] = 0
                elif x_offset < 0:
                    x_offset = abs(x_offset)
                    frame[y_start:y_end, :-x_offset] = frame[y_start:y_end, x_offset:].copy()
                    frame[y_start:y_end, -x_offset:] = 0
            
            # 隨機加上色彩濾鏡
            color_shift = random.randint(0, 2)
            frame[:, :, color_shift] = cv2.add(frame[:, :, color_shift], 50)

        # 顯示最終畫面
        cv2.imshow(WINDOW_NAME, frame)

    # 離開遊戲前，若有突破高分則進行安全存檔
    if score > 0 and not score_saved:
        leaderboard.append(score)
        leaderboard.sort(reverse=True)
        leaderboard = leaderboard[:5]
    save_data({'high_score': max(score, high_score), 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield, 'leaderboard': leaderboard})
    print(">>> [System] Data saved on exit.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
