import cv2
import numpy as np
import pygame
import math
import random
import time
import json
import os

# ==========================================
# 遊戲設定
# ==========================================
WINDOW_NAME = 'Virtual Goalkeeper - Ultimate Upgrade'
MAX_LIVES = 3
INITIAL_BALL_SPEED = 5
SPAWN_INTERVAL = 2.0  # seconds
HIGH_SCORE_FILE = 'highscores.json'

# ==========================================
# 音效與影像載入 (安全加載與備用機制)
# ==========================================
pygame.mixer.init()

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

# 五種球種的圖像加載與備用繪製
ball_types = ['normal', 'gold', 'bomb', 'ice', 'heart']
ball_imgs = {}

for bt in ball_types:
    filepath = 'assets/ball.png' if bt == 'normal' else f'assets/ball_{bt}.png'
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Warning: Could not load {filepath}. Generating fallback visual.")
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
# 高分紀錄儲存與讀取 (Leaderboard)
# ==========================================
def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('high_score', 0)
        except Exception:
            pass
    return 0

def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump({'high_score': score}, f)
    except Exception:
        pass

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

    alpha_s = (img_overlay[oy1:oy2, ox1:ox2, 3] / 255.0) * global_alpha
    alpha_l = 1.0 - alpha_s

    for c in range(0, 3):
        img[y1:y2, x1:x2, c] = (
            alpha_s * img_overlay[oy1:oy2, ox1:ox2, c] +
            alpha_l * img[y1:y2, x1:x2, c]
        )
    return img

# ==========================================
# 極致磨砂玻璃面板繪製 (Glassmorphism HUD Panels)
# ==========================================
def draw_glass_panel(img, x1, y1, x2, y2, bg_color=(0, 0, 0), alpha=0.4, border_color=(255, 255, 255), border_thickness=1):
    """在影像上繪製半透明且帶有發光霓虹邊框的質感控制面板"""
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x1 >= x2 or y1 >= y2:
        return img
    
    sub_img = img[y1:y2, x1:x2]
    rect = np.zeros_like(sub_img)
    cv2.rectangle(rect, (0, 0), (x2 - x1, y2 - y1), bg_color, -1)
    
    # 磨砂混合
    img[y1:y2, x1:x2] = cv2.addWeighted(rect, alpha, sub_img, 1.0 - alpha, 0)
    
    # 繪製精緻的單像素或霓虹外框
    if border_thickness > 0:
        cv2.rectangle(img, (x1, y1), (x2, y2), border_color, border_thickness, cv2.LINE_AA)
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
    """根據權重選擇球體 (普通:70%, 黃金:10%, 炸彈:10%, 冰凍:5%, 愛心:5%)"""
    r = random.random()
    if r < 0.70:
        return 'normal'
    elif r < 0.80:
        return 'gold'
    elif r < 0.90:
        return 'bomb'
    elif r < 0.95:
        return 'ice'
    else:
        return 'heart'

# ==========================================
# 遊戲狀態與重置函式
# ==========================================
STATE_MENU_MODE = 0
STATE_MENU_DIFF = 1
STATE_PLAYING = 2
STATE_GAMEOVER = 3

def reset_game_state(difficulty, high_score):
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
        'flash_timer': 0,
        'flash_color': (0, 0, 0)
    }

# ==========================================
# UI 繪製輔助函式
# ==========================================
def draw_text(img, text, pos, scale, color, thickness=2, center=False):
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
    cap = cv2.VideoCapture(0)
    mp_start_time = time.time()
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # 初始化狀態
    game_state = STATE_MENU_MODE
    game_mode = 1
    game_difficulty = 2
    high_score = load_high_score()
    new_record_broken = False

    # 初始化這些變數，稍後 reset 時會覆蓋
    score, lives, balls, effects, particles, combo, ambient_sparks = 0, MAX_LIVES, [], [], [], 0, []
    last_spawn_time, current_speed, current_spawn_interval, ice_timer = 0, 0, 0, 0.0
    shake_timer, flash_timer, flash_color = 0, 0, (0, 0, 0)
    backSub = None 

    print("Game Started! Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. 影像預處理：水平翻轉 (Mirror)
        frame = cv2.flip(frame, 1)

        # 根據模式決定是否放大畫面
        if game_state in (STATE_MENU_MODE, STATE_MENU_DIFF):
            frame = cv2.resize(frame, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_LINEAR)
        elif game_state in (STATE_PLAYING, STATE_GAMEOVER):
            if game_mode == 2:
                # 多人遊戲：上下裁切後再等比放大
                h, w = frame.shape[:2]
                crop_y = int(h * 0.125)
                frame = frame[crop_y : h - crop_y, :]
                frame = cv2.resize(frame, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
            elif game_mode == 3:
                # 中心防守：1.8倍
                frame = cv2.resize(frame, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_LINEAR)
        
        FRAME_H, FRAME_W = frame.shape[:2]

        # 震屏特效實作 (Screen Shake translation matrix)
        if game_state == STATE_PLAYING and shake_timer > 0:
            dx = random.randint(-8, 8)
            dy = random.randint(-8, 8)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame = cv2.warpAffine(frame, M, (FRAME_W, FRAME_H))
            shake_timer -= 1

        if game_state == STATE_MENU_MODE:
            # 畫半透明黑色遮罩讓文字更清楚
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            # 繪製主選單大玻璃面板
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, (15, 10, 25), 0.5, (0, 215, 255), 2)

            # 主選單文字
            draw_text(frame, "Virtual Goalkeeper", (0, int(FRAME_H * 0.2)), 1.5, (0, 215, 255), 3, center=True)
            draw_text(frame, "Ultimate Edition", (0, int(FRAME_H * 0.28)), 1.0, (255, 255, 255), 2, center=True)
            
            # 顯示目前偵測到的 CV 追蹤模式
            cv_text = "Sensing Mode: MediaPipe skeleton" if USE_MEDIAPIPE else "Sensing Mode: High-spec Background outlines"
            cv_color = (0, 255, 0) if USE_MEDIAPIPE else (255, 255, 0)
            draw_text(frame, cv_text, (0, int(FRAME_H * 0.36)), 0.6, cv_color, 1, center=True)
            
            draw_text(frame, f"ALL-TIME HIGH SCORE: {high_score}", (0, int(FRAME_H * 0.45)), 0.7, (255, 255, 255), 2, center=True)
            
            draw_text(frame, "Select Game Mode:", (0, int(FRAME_H * 0.56)), 0.8, (0, 255, 255), 2, center=True)
            draw_text(frame, "1. Single Player (Classic)", (0, int(FRAME_H * 0.64)), 0.7, (255, 255, 255), 1, center=True)
            draw_text(frame, "2. Multiplayer (Wider Screen)", (0, int(FRAME_H * 0.71)), 0.7, (255, 255, 255), 1, center=True)
            draw_text(frame, "3. Defend Center (360 Degree)", (0, int(FRAME_H * 0.78)), 0.7, (255, 255, 255), 1, center=True)
            draw_text(frame, "Press '1', '2', or '3' to Start!", (0, int(FRAME_H * 0.89)), 0.7, (0, 215, 255), 2, center=True)
            
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
            elif key == ord('q'):
                break

        elif game_state == STATE_MENU_DIFF:
            # 畫半透明黑色遮罩
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            # 繪製難度選擇玻璃面板
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, (25, 15, 10), 0.5, (0, 215, 255), 2)

            # 難度選單文字
            draw_text(frame, f"Mode {game_mode} Selected", (0, int(FRAME_H * 0.2)), 1.3, (0, 215, 255), 3, center=True)
            draw_text(frame, "Select Difficulty:", (0, int(FRAME_H * 0.4)), 1.0, (255, 255, 255), 2, center=True)
            draw_text(frame, "1. Easy (5 Lives, Normal Speed)", (0, int(FRAME_H * 0.52)), 0.75, (50, 255, 50), 2, center=True)
            draw_text(frame, "2. Normal (3 Lives, Normal Speed)", (0, int(FRAME_H * 0.62)), 0.75, (0, 255, 255), 2, center=True)
            draw_text(frame, "3. Hard (2 Lives, High Speed)", (0, int(FRAME_H * 0.72)), 0.75, (50, 50, 255), 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key in [ord('1'), ord('2'), ord('3')]:
                if key == ord('1'): game_difficulty = 1
                elif key == ord('2'): game_difficulty = 2
                elif key == ord('3'): game_difficulty = 3
                
                # 初始化遊戲狀態
                high_score = load_high_score()
                new_record_broken = False
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
                flash_timer = state['flash_timer']
                flash_color = state['flash_color']
                
                # 重新初始化背景相減器以適應新的解析度
                backSub = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
                
            elif key == ord('q'):
                break

        elif game_state == STATE_PLAYING:
            # 2. 電腦視覺追蹤運算 (MediaPipe 或是 背景相減 Outlines)
            player_points = [] # 用於 MediaPipe 精準圓形碰撞 (x, y, radius)
            player_boxes = []  # 用於背景相減 AABB 碰撞偵測 (x, y, w, h)
            area_thresh = 1000 if game_mode == 1 else 2500
            
            if USE_MEDIAPIPE:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp_image_format, data=rgb_frame)
                timestamp_ms = int((time.time() - mp_start_time) * 1000)
                
                # 執行多骨架推論
                pose_results = pose_tracker.detect_for_video(mp_image, timestamp_ms)
                
                # --- 背景替換 (MediaPipe 虛擬攝影棚) ---
                if background_img is not None and pose_results and pose_results.segmentation_masks:
                    bg_resized = cv2.resize(background_img, (FRAME_W, FRAME_H))
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
                        nx, ny = int(nose.x * FRAME_W), int(nose.y * FRAME_H)
                        lex, ley = int(left_elbow.x * FRAME_W), int(left_elbow.y * FRAME_H)
                        rex, rey = int(right_elbow.x * FRAME_W), int(right_elbow.y * FRAME_H)
                        lax, lay = int(left_ankle.x * FRAME_W), int(left_ankle.y * FRAME_H)
                        rax, ray = int(right_ankle.x * FRAME_W), int(right_ankle.y * FRAME_H)
                        
                        # 計算身體中心 (以肩膀中心替代)
                        bx, by = (lsx + rsx) // 2, (lsy + rsy) // 2
                        
                        # 顏色區分玩家一與玩家二
                        body_color = (0, 255, 0) if idx == 0 else (200, 150, 0)
                        
                        # --- 數位傀儡 (Digital Puppetry) 繪製與碰撞映射 ---
                        
                        # 1. 身體 Avatar (矩形)
                        player_points.append((bx, by, 45)) # 半徑 45 的防守範圍
                        cv2.rectangle(frame, (bx - 40, by - 50), (bx + 40, by + 50), body_color, 2, cv2.LINE_AA)
                        cv2.rectangle(frame, (bx - 40, by - 50), (bx + 40, by + 50), (0, 50, 0), -1)
                        draw_text(frame, f"P{idx+1}", (bx - 15, by - 60), 0.6, body_color, 1)
                        
                        # 2. 左手防守手套 (紅色系)
                        player_points.append((lwx, lwy, 35))
                        cv2.circle(frame, (lwx, lwy), 35, (0, 0, 255), 2, cv2.LINE_AA)
                        cv2.circle(frame, (lwx, lwy), 30, (0, 0, 150), -1)
                        
                        # 3. 右手防守手套 (藍色系)
                        player_points.append((rwx, rwy, 35))
                        cv2.circle(frame, (rwx, rwy), 35, (255, 0, 0), 2, cv2.LINE_AA)
                        cv2.circle(frame, (rwx, rwy), 30, (150, 0, 0), -1)
                        
                        # 4. 頭部頂球點 (橘黃色)
                        player_points.append((nx, ny, 35))
                        cv2.circle(frame, (nx, ny), 35, (0, 165, 255), 2, cv2.LINE_AA)
                        cv2.circle(frame, (nx, ny), 30, (0, 100, 200), -1)
                        draw_text(frame, "HEAD", (nx - 20, ny - 45), 0.4, (0, 165, 255), 1)

                        # 5. 手肘輔助防守點 (空心圓，填補手臂空隙)
                        player_points.append((lex, ley, 25))
                        cv2.circle(frame, (lex, ley), 25, (0, 0, 255), 2, cv2.LINE_AA)
                        player_points.append((rex, rey, 25))
                        cv2.circle(frame, (rex, rey), 25, (255, 0, 0), 2, cv2.LINE_AA)

                        # 6. 雙腳踢球點 (青色系)
                        player_points.append((lax, lay, 35))
                        cv2.circle(frame, (lax, lay), 35, (255, 255, 0), 2, cv2.LINE_AA)
                        cv2.circle(frame, (lax, lay), 30, (150, 150, 0), -1)
                        player_points.append((rax, ray, 35))
                        cv2.circle(frame, (rax, ray), 35, (255, 255, 0), 2, cv2.LINE_AA)
                        cv2.circle(frame, (rax, ray), 30, (150, 150, 0), -1)
            else:
                # 傳統 MOG2 背景相減法 + 霓虹邊框繪製
                fgMask = backSub.apply(frame)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
                
                # --- 背景替換 (MOG2 備用模式) ---
                if background_img is not None:
                    bg_resized = cv2.resize(background_img, (FRAME_W, FRAME_H))
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

            # 3. 遊戲邏輯 - 虛擬球隨機生成
            current_time = time.time()
            if current_time - last_spawn_time > current_spawn_interval:
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
            speed_mult = 0.4 if is_frozen else 1.0  # 冰凍時間減速 60%
            
            for ball in balls[:]:
                # 紀錄拖尾歷史位置
                ball['trail'].append((ball['x'], ball['y']))
                if len(ball['trail']) > 5:
                    ball['trail'].pop(0)
                    
                # 更新位置
                ball['x'] += ball['dx'] * speed_mult
                ball['y'] += ball['dy'] * speed_mult
                
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
                if hit:
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
                        effects.append({'text': f'+{pts_earned}', 'x': bx, 'y': by, 'color': (0, 255, 0), 'life': 30})
                        spawn_particles(particles, bx, by, (200, 200, 200)) # 灰色煙霧粒子
                        if sounds['hit']: sounds['hit'].play()
                        
                    elif b_type == 'gold':
                        # 黃金球：獲得 3 倍基本分並乘上連擊加成！
                        pts_earned = 30 * mult
                        score += pts_earned
                        combo += 1
                        flash_timer = 7 # 耀眼金色閃屏
                        flash_color = (0, 215, 255)
                        effects.append({'text': f'GOLD! +{pts_earned}', 'x': bx, 'y': by, 'color': (0, 215, 255), 'life': 30})
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
                        effects.append({'text': 'BOMB! -20', 'x': bx, 'y': by, 'color': (0, 0, 255), 'life': 45})
                        spawn_particles(particles, bx, by, (0, 100, 255)) # 橘紅色爆炸粒子
                        if sounds['hit_bomb']: sounds['hit_bomb'].play()
                        if lives <= 0:
                            game_state = STATE_GAMEOVER
                            
                    elif b_type == 'ice':
                        # 冰凍球：獲得 10 分並觸發減速 3 秒
                        score += 10
                        combo += 1
                        ice_timer = time.time() + 3.0
                        flash_timer = 7 # 冰藍色閃屏
                        flash_color = (255, 255, 100)
                        effects.append({'text': 'FREEZE!', 'x': bx, 'y': by, 'color': (255, 255, 100), 'life': 30})
                        spawn_particles(particles, bx, by, (255, 255, 100)) # 青藍色冰晶粒子
                        if sounds['hit_ice']: sounds['hit_ice'].play()
                        
                    elif b_type == 'heart':
                        # 愛心球：增加生命值，最高 5 點
                        if lives < 5:
                            lives += 1
                            effects.append({'text': 'LIFE UP!', 'x': bx, 'y': by, 'color': (150, 50, 255), 'life': 35})
                        else:
                            effects.append({'text': 'MAX LIFE!', 'x': bx, 'y': by, 'color': (150, 50, 255), 'life': 35})
                        score += 10
                        combo += 1
                        flash_timer = 7 # 粉紅色閃屏
                        flash_color = (150, 50, 255)
                        spawn_particles(particles, bx, by, (150, 50, 255)) # 粉紅色愛心粒子
                        if sounds['hit_heart']: sounds['hit_heart'].play()
                        
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
                        balls.remove(ball)

            # 5. 畫面渲染
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

            # 繪製球體拖尾 (運動模糊)
            for ball in balls:
                for idx, (tx, ty) in enumerate(ball['trail'][:-1]):
                    # 越久以前的座標越透明
                    alpha_factor = (idx + 1) / len(ball['trail']) * 0.4
                    frame = overlay_image_alpha(frame, ball_imgs[ball['type']], tx, ty, alpha_factor)
                
                # 繪製主球體
                frame = overlay_image_alpha(frame, ball_imgs[ball['type']], ball['x'], ball['y'])

            # 繪製粒子物理運動 (格擋爆炸特效)
            for p in particles[:]:
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
                s['x'] += s['vx']
                s['y'] += s['vy']
                s['life'] -= s['decay']
                if s['life'] <= 0:
                    ambient_sparks.remove(s)
                else:
                    r = int(s['radius'] * s['life'])
                    if r > 0:
                        cv2.circle(frame, (int(s['x']), int(s['y'])), r, s['color'], -1, cv2.LINE_AA)

            # 繪製飄浮分數與文字特效
            for effect in effects[:]:
                draw_text(frame, effect['text'], (int(effect['x']), int(effect['y'])), 0.8, effect['color'], 2)
                effect['y'] -= 2  # 特效文字飄移
                effect['life'] -= 1
                if effect['life'] <= 0:
                    effects.remove(effect)

            # 冰凍邊框特效 overlay
            if is_frozen:
                cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), (255, 200, 100), 8) # 藍色凍結框
                draw_text(frame, "TIME FROZEN", (0, 90), 0.7, (255, 255, 100), 2, center=True)

            # 閃光護盾邊框特效 (Vignette Flash Effect)
            if flash_timer > 0:
                border_thick = int(24 * (flash_timer / 7))
                if border_thick > 0:
                    cv2.rectangle(frame, (0, 0), (FRAME_W, FRAME_H), flash_color, border_thick)
                flash_timer -= 1

            # 磨砂玻璃左上 HUD 面板 (Score & High Score)
            frame = draw_glass_panel(frame, 15, 15, 210, 95, (30, 20, 20), 0.5, (0, 215, 255), 1)
            # 磨砂玻璃左上 HUD 面板 (Score, High Score & Skill)
            frame = draw_glass_panel(frame, 15, 15, 280, 125, (30, 20, 20), 0.5, (0, 215, 255), 1)
            draw_text(frame, f"Score: {score}", (30, 48), 0.7, (255, 255, 255), 2)
            draw_text(frame, f"HI Score: {high_score}", (30, 80), 0.55, (0, 215, 255), 1)
            
            # 顯示技能冷卻狀態
            if USE_MEDIAPIPE:
                if skill_cooldown <= 0:
                    draw_text(frame, "SKILL: READY (Cross Wrists)", (30, 110), 0.45, (0, 255, 0), 1)
                else:
                    draw_text(frame, f"SKILL: CD {skill_cooldown // 30}s", (30, 110), 0.45, (100, 100, 100), 1)

            # 顯示生命值 HUD 面板
            lives_color = (0, 0, 255) if lives == 1 and (int(time.time() * 5) % 2 == 0) else (50, 50, 255)
            lives_text = f"Lives: {lives}"
            lives_size = cv2.getTextSize(lives_text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)[0]
            panel_x1 = FRAME_W - lives_size[0] - 35
            
            frame = draw_glass_panel(frame, panel_x1, 15, FRAME_W - 15, 60, (20, 20, 30), 0.5, lives_color, 1)
            draw_text(frame, lives_text, (panel_x1 + 10, 46), 0.7, lives_color, 2)

            # 顯示 Combo 連擊磨砂玻璃面板 (有呼吸燈抖動特效)
            if combo >= 3:
                pulse_scale = 0.8 + 0.12 * math.sin(time.time() * 12)
                combo_text = f"{combo} COMBO!"
                combo_thickness = 3
                combo_size = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_DUPLEX, pulse_scale, combo_thickness)[0]
                
                cx1 = (FRAME_W - combo_size[0]) // 2 - 20
                cx2 = (FRAME_W + combo_size[0]) // 2 + 20
                cy1 = 80
                cy2 = 145
                
                mult = 1
                if combo >= 20: mult = 5
                elif combo >= 10: mult = 3
                elif combo >= 5: mult = 2
                
                if mult > 1:
                    cy2 = 175 # 面板增高以容納乘數
                    
                frame = draw_glass_panel(frame, cx1, cy1, cx2, cy2, (20, 30, 20), 0.6, (0, 215, 255), 1)
                draw_text(frame, combo_text, (cx1 + 20, 120), pulse_scale, (0, 215, 255), combo_thickness)
                if mult > 1:
                    draw_text(frame, f"{mult}X SCORE MULTIPLIER", (0, 158), 0.45, (0, 255, 255), 1, center=True)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break

        elif game_state == STATE_GAMEOVER:
            # 判斷是否打破歷史高分紀錄並儲存
            if score > high_score:
                high_score = score
                save_high_score(high_score)
                new_record_broken = True

            # 畫半透明黑色遮罩
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            # 繪製遊戲結束大玻璃面板
            frame = draw_glass_panel(frame, 50, 40, FRAME_W - 50, FRAME_H - 40, (10, 10, 20), 0.6, (50, 50, 255), 2)

            draw_text(frame, "GAME OVER", (0, FRAME_H//2 - 50), 2.0, (50, 50, 255), 4, center=True)
            
            # 榮耀冠軍字樣
            if new_record_broken:
                pulse = int(math.sin(time.time() * 10) * 5)
                draw_text(frame, "NEW HIGH SCORE!", (0, FRAME_H//2 + 15), 1.2, (0, 215, 255), 3, center=True)
            
            draw_text(frame, f"Final Score: {score}", (0, FRAME_H//2 + 70), 1.0, (255, 255, 255), 2, center=True)
            draw_text(frame, "Press 'r' to Menu or 'q' to Quit", (0, FRAME_H//2 + 120), 0.8, (0, 255, 255), 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                game_state = STATE_MENU_MODE

        # 顯示最終畫面
        cv2.imshow(WINDOW_NAME, frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
