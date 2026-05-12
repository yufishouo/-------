import cv2
import numpy as np
import pygame
import math
import random
import time

# ==========================================
# 遊戲設定
# ==========================================
WINDOW_NAME = 'Virtual Goalkeeper'
MAX_LIVES = 3
INITIAL_BALL_SPEED = 5
SPAWN_INTERVAL = 2.0  # seconds

# ==========================================
# 音效與影像載入
# ==========================================
# Initialize Pygame Mixer
pygame.mixer.init()

try:
    hit_sound = pygame.mixer.Sound('assets/hit.wav')
    miss_sound = pygame.mixer.Sound('assets/miss.wav')
except Exception as e:
    print("Warning: Could not load sound files. Run setup_assets.py first.")
    hit_sound, miss_sound = None, None

# Load Ball Image
ball_img = cv2.imread('assets/ball.png', cv2.IMREAD_UNCHANGED)
if ball_img is None:
    print("Warning: Could not load ball.png. Creating a placeholder.")
    ball_img = np.zeros((64, 64, 4), dtype=np.uint8)
    cv2.circle(ball_img, (32, 32), 30, (255, 255, 255, 255), -1)
    cv2.circle(ball_img, (32, 32), 30, (0, 0, 0, 255), 2)

BALL_HEIGHT, BALL_WIDTH = ball_img.shape[:2]

# ==========================================
# 影像合成工具函式 (Alpha Blending)
# ==========================================
def overlay_image_alpha(img, img_overlay, x, y):
    """Overlay img_overlay on top of img at the position (x, y)."""
    x, y = int(round(x)), int(round(y))
    
    # Image ranges
    y1, y2 = max(0, y), min(img.shape[0], y + img_overlay.shape[0])
    x1, x2 = max(0, x), min(img.shape[1], x + img_overlay.shape[1])

    # Offset within the overlay image
    oy1 = max(0, -y)
    oy2 = oy1 + (y2 - y1)
    ox1 = max(0, -x)
    ox2 = ox1 + (x2 - x1)

    if oy1 >= img_overlay.shape[0] or ox1 >= img_overlay.shape[1] or y1 >= y2 or x1 >= x2:
        return img  # Outside screen

    alpha_s = img_overlay[oy1:oy2, ox1:ox2, 3] / 255.0
    alpha_l = 1.0 - alpha_s

    for c in range(0, 3):
        img[y1:y2, x1:x2, c] = (
            alpha_s * img_overlay[oy1:oy2, ox1:ox2, c] +
            alpha_l * img[y1:y2, x1:x2, c]
        )
    return img

# ==========================================
# 遊戲狀態與重置函式
# ==========================================
STATE_MENU_MODE = 0
STATE_MENU_DIFF = 1
STATE_PLAYING = 2
STATE_GAMEOVER = 3

def reset_game_state(difficulty):
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
        'current_speed': speed,
        'current_spawn_interval': SPAWN_INTERVAL,
        'last_spawn_time': time.time(),
        'game_state': STATE_PLAYING
    }

# ==========================================
# UI 繪製輔助函式
# ==========================================
def draw_text(img, text, pos, scale, color, thickness=2, center=False):
    font = cv2.FONT_HERSHEY_DUPLEX
    if center:
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        pos = ((img.shape[1] - text_size[0]) // 2, pos[1])
    # 畫黑色外框
    cv2.putText(img, text, pos, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    # 畫主要文字
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)

# ==========================================
# 主遊戲迴圈
# ==========================================
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # 初始化狀態
    game_state = STATE_MENU_MODE
    game_mode = 1
    game_difficulty = 2

    # 初始化這些變數，稍後 reset 時會覆蓋
    score, lives, balls, effects = 0, MAX_LIVES, [], []
    last_spawn_time, current_speed, current_spawn_interval = 0, 0, 0
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
            # 選單畫面變大 (1.8倍)
            frame = cv2.resize(frame, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_LINEAR)
        elif game_state in (STATE_PLAYING, STATE_GAMEOVER):
            if game_mode == 2:
                # 多人遊戲：為了橫向廣又不拉長人體，將上下裁切後再等比放大
                # 例如裁掉上下各 1/8，再放大 2.0 倍
                h, w = frame.shape[:2]
                crop_y = int(h * 0.125)
                frame = frame[crop_y : h - crop_y, :]
                frame = cv2.resize(frame, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
            elif game_mode == 3:
                # 中心防守：稍微放大，不超出螢幕 (1.8倍)
                frame = cv2.resize(frame, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_LINEAR)
        
        FRAME_H, FRAME_W = frame.shape[:2]

        if game_state == STATE_MENU_MODE:
            # 畫半透明黑色遮罩讓文字更清楚
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            # 主選單: 選擇模式
            draw_text(frame, "Virtual Goalkeeper", (0, int(FRAME_H * 0.2)), 1.5, (50, 255, 50), 3, center=True)
            draw_text(frame, "Select Game Mode:", (0, int(FRAME_H * 0.4)), 1.0, (255, 255, 255), 2, center=True)
            draw_text(frame, "1. Single Player (Classic)", (0, int(FRAME_H * 0.5)), 0.8, (255, 255, 255), 2, center=True)
            draw_text(frame, "2. Multiplayer (Wider Screen)", (0, int(FRAME_H * 0.6)), 0.8, (255, 255, 255), 2, center=True)
            draw_text(frame, "3. Defend Center (360 Degree)", (0, int(FRAME_H * 0.7)), 0.8, (255, 255, 255), 2, center=True)
            draw_text(frame, "Instructions: Move your body to block balls!", (0, int(FRAME_H * 0.9)), 0.7, (0, 255, 255), 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('1'):
                game_mode = 1
                game_state = STATE_MENU_DIFF
            elif key == ord('2'):
                game_mode = 2
                game_state = STATE_MENU_DIFF
            elif key == ord('3'):
                game_mode = 3
                game_state = STATE_MENU_DIFF
            elif key == ord('q'):
                break

        elif game_state == STATE_MENU_DIFF:
            # 畫半透明黑色遮罩
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            # 難度選單
            draw_text(frame, f"Mode {game_mode} Selected", (0, int(FRAME_H * 0.2)), 1.5, (0, 255, 255), 3, center=True)
            draw_text(frame, "Select Difficulty:", (0, int(FRAME_H * 0.4)), 1.0, (255, 255, 255), 2, center=True)
            draw_text(frame, "1. Easy (5 Lives, Normal Speed)", (0, int(FRAME_H * 0.5)), 0.8, (50, 255, 50), 2, center=True)
            draw_text(frame, "2. Normal (3 Lives, Normal Speed)", (0, int(FRAME_H * 0.6)), 0.8, (0, 255, 255), 2, center=True)
            draw_text(frame, "3. Hard (2 Lives, High Speed)", (0, int(FRAME_H * 0.7)), 0.8, (50, 50, 255), 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key in [ord('1'), ord('2'), ord('3')]:
                if key == ord('1'): game_difficulty = 1
                elif key == ord('2'): game_difficulty = 2
                elif key == ord('3'): game_difficulty = 3
                
                # 初始化遊戲狀態
                state = reset_game_state(game_difficulty)
                score, lives, balls, effects = state['score'], state['lives'], state['balls'], state['effects']
                current_speed, current_spawn_interval = state['current_speed'], state['current_spawn_interval']
                last_spawn_time, game_state = state['last_spawn_time'], state['game_state']
                
                # 重新初始化背景相減器以適應新的解析度
                backSub = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50, detectShadows=False)
                
            elif key == ord('q'):
                break

        elif game_state == STATE_PLAYING:
            # 2. 動態偵測
            fgMask = backSub.apply(frame)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel)
            
            # 尋找移動區域的輪廓
            contours, _ = cv2.findContours(fgMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            player_boxes = []
            for contour in contours:
                # 模式 2 和 3 畫面放大 1.5~2 倍，面積閥值可以適當提高
                area_thresh = 1000 if game_mode == 1 else 2500
                if cv2.contourArea(contour) > area_thresh:
                    x, y, w, h = cv2.boundingRect(contour)
                    player_boxes.append((x, y, w, h))

            # 3. 遊戲邏輯 - 虛擬球生成
            current_time = time.time()
            if current_time - last_spawn_time > current_spawn_interval:
                if game_mode in (1, 2):
                    new_x = random.randint(0, FRAME_W - BALL_WIDTH)
                    balls.append({'x': new_x, 'y': -BALL_HEIGHT, 'dx': 0, 'dy': current_speed})
                else:
                    # 模式 3: 球從四面八方出現
                    edge = random.choice(['top', 'bottom', 'left', 'right'])
                    if edge == 'top':
                        start_x, start_y = random.randint(0, FRAME_W), -BALL_HEIGHT
                    elif edge == 'bottom':
                        start_x, start_y = random.randint(0, FRAME_W), FRAME_H
                    elif edge == 'left':
                        start_x, start_y = -BALL_WIDTH, random.randint(0, FRAME_H)
                    else: # right
                        start_x, start_y = FRAME_W, random.randint(0, FRAME_H)
                    
                    # 計算球心坐標，讓球心精準對齊畫面正中心
                    start_cx = start_x + BALL_WIDTH / 2
                    start_cy = start_y + BALL_HEIGHT / 2
                    target_x, target_y = FRAME_W / 2, FRAME_H / 2
                    
                    dist = np.hypot(target_x - start_cx, target_y - start_cy)
                    # 避免除以 0
                    if dist > 0:
                        dx = (target_x - start_cx) / dist * current_speed
                        dy = (target_y - start_cy) / dist * current_speed
                    else:
                        dx, dy = 0, current_speed
                        
                    balls.append({'x': start_x, 'y': start_y, 'dx': dx, 'dy': dy})

                last_spawn_time = current_time
                current_speed += 0.2
                current_spawn_interval = max(0.5, current_spawn_interval - 0.05)

            # 4. 遊戲邏輯 - 更新球與碰撞偵測
            for ball in balls[:]:
                ball['x'] += ball['dx']
                ball['y'] += ball['dy']
                
                # 碰撞偵測 (AABB)
                hit = False
                for bx, by, bw, bh in player_boxes:
                    if (ball['x'] < bx + bw and ball['x'] + BALL_WIDTH > bx and
                        ball['y'] < by + bh and ball['y'] + BALL_HEIGHT > by):
                        hit = True
                        break
                
                if hit:
                    # 成功格擋
                    score += 10
                    effects.append({'text': '+10', 'x': ball['x'], 'y': ball['y'], 'life': 30})
                    balls.remove(ball)
                    if hit_sound: hit_sound.play()
                else:
                    # 漏接判定
                    miss = False
                    if game_mode in (1, 2):
                        if ball['y'] > FRAME_H:
                            miss = True
                    else:
                        # 模式 3: 若球接近正中心 (半徑 50 的圓內，對應視覺外圈) 則視為漏接
                        cx, cy = ball['x'] + BALL_WIDTH/2, ball['y'] + BALL_HEIGHT/2
                        if np.hypot(cx - FRAME_W/2, cy - FRAME_H/2) < 50:
                            miss = True
                            
                    if miss:
                        lives -= 1
                        balls.remove(ball)
                        if miss_sound: miss_sound.play()
                        if lives <= 0:
                            game_state = STATE_GAMEOVER

            # 5. 畫面渲染
            if game_mode == 3:
                # 標示中心防守區域 (變得好看一點，加入脈動效果)
                cx, cy = int(FRAME_W//2), int(FRAME_H//2)
                pulse = int(math.sin(time.time() * 8) * 8)
                
                # 外圈
                cv2.circle(frame, (cx, cy), 50 + pulse, (0, 255, 255), 2, cv2.LINE_AA)
                # 內圈
                cv2.circle(frame, (cx, cy), 35 - pulse//2, (0, 165, 255), 2, cv2.LINE_AA)
                # 核心
                cv2.circle(frame, (cx, cy), 15, (0, 0, 255), -1, cv2.LINE_AA)
                # 十字準心
                cv2.line(frame, (cx - 60, cy), (cx + 60, cy), (0, 255, 255), 1, cv2.LINE_AA)
                cv2.line(frame, (cx, cy - 60), (cx, cy + 60), (0, 255, 255), 1, cv2.LINE_AA)

            for ball in balls:
                frame = overlay_image_alpha(frame, ball_img, ball['x'], ball['y'])

            # 渲染特效 (如 +10 分字樣)
            for effect in effects[:]:
                draw_text(frame, effect['text'], (int(effect['x']), int(effect['y'])), 1.0, (50, 255, 255), 2)
                effect['y'] -= 2 # 往上飄移
                effect['life'] -= 1
                if effect['life'] <= 0:
                    effects.remove(effect)

            # UI 顯示
            draw_text(frame, f"Score: {score}", (20, 40), 1.0, (255, 255, 255), 2)
            # Lives on top right
            lives_text = f"Lives: {lives}"
            lives_size = cv2.getTextSize(lives_text, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)[0]
            draw_text(frame, lives_text, (FRAME_W - lives_size[0] - 20, 40), 1.0, (50, 50, 255), 2)

            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break

        elif game_state == STATE_GAMEOVER:
            # 畫半透明黑色遮罩
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            draw_text(frame, "GAME OVER", (0, FRAME_H//2 - 20), 2.0, (50, 50, 255), 4, center=True)
            draw_text(frame, f"Final Score: {score}", (0, FRAME_H//2 + 50), 1.2, (255, 255, 255), 3, center=True)
            draw_text(frame, "Press 'r' to Menu or 'q' to Quit", (0, FRAME_H//2 + 100), 0.8, (0, 255, 255), 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                game_state = STATE_MENU_MODE

        # 顯示畫面
        cv2.imshow(WINDOW_NAME, frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()

