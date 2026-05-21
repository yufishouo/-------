import os
import math
import struct
import wave
import numpy as np
import cv2

# 建立 assets 目錄
os.makedirs('assets', exist_ok=True)

# =====================================================================
# 1. 圖片資產生成器 (Procedural Image Generators)
# =====================================================================
SIZE = 64

def generate_normal_ball():
    """生成普通足球圖像"""
    ball = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cx, cy = SIZE // 2, SIZE // 2
    radius = SIZE // 2 - 2
    
    cv2.circle(ball, (cx, cy), radius, (255, 255, 255, 255), -1)
    
    # 畫中心黑五角星
    pts = []
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        x = int(cx + radius * 0.4 * math.cos(angle))
        y = int(cy + radius * 0.4 * math.sin(angle))
        pts.append([x, y])
    pts = np.array(pts, np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(ball, [pts], (0, 0, 0, 255))
    
    # 連接邊緣線條
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        p1_x = int(cx + radius * 0.4 * math.cos(angle))
        p1_y = int(cy + radius * 0.4 * math.sin(angle))
        p2_x = int(cx + radius * math.cos(angle))
        p2_y = int(cy + radius * math.sin(angle))
        cv2.line(ball, (p1_x, p1_y), (p2_x, p2_y), (0, 0, 0, 255), 2)
        
    cv2.circle(ball, (cx, cy), radius, (0, 0, 0, 255), 2)
    return ball

def generate_gold_ball():
    """生成黃金足球圖像 (高貴黃金漸層 + 金色星光外圈)"""
    gold = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cx, cy = SIZE // 2, SIZE // 2
    radius = SIZE // 2 - 4
    
    # 放射狀金色漸層
    for r in range(radius, 0, -2):
        # 愈接近球心愈亮 (金色 BGR: (0, 215, 255))
        factor = 1.0 - (r / radius)
        b = int(0)
        g = int(140 + 115 * factor)
        r_val = int(200 + 55 * factor)
        cv2.circle(gold, (cx, cy), r, (b, g, r_val, 255), -1)
        
    # 畫暗金色五角星與線條
    pts = []
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        x = int(cx + radius * 0.4 * math.cos(angle))
        y = int(cy + radius * 0.4 * math.sin(angle))
        pts.append([x, y])
    pts = np.array(pts, np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(gold, [pts], (0, 70, 130, 255)) # 暗金色
    
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        p1_x = int(cx + radius * 0.4 * math.cos(angle))
        p1_y = int(cy + radius * 0.4 * math.sin(angle))
        p2_x = int(cx + radius * math.cos(angle))
        p2_y = int(cy + radius * math.sin(angle))
        cv2.line(gold, (p1_x, p1_y), (p2_x, p2_y), (0, 70, 130, 255), 2)
        
    cv2.circle(gold, (cx, cy), radius, (0, 100, 180, 255), 2)
    
    # 繪製外圈閃亮光環 (Alpha Blend)
    glow = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cv2.circle(glow, (cx, cy), radius + 3, (0, 215, 255, 100), 2)
    # 四個對角發光點
    for angle_deg in [0, 90, 180, 270]:
        rad = math.radians(angle_deg)
        sp_x = int(cx + (radius + 2) * math.cos(rad))
        sp_y = int(cy + (radius + 2) * math.sin(rad))
        cv2.circle(glow, (sp_x, sp_y), 3, (150, 255, 255, 200), -1)
        
    # 合併光圈
    mask = glow[:, :, 3] > 0
    gold[mask] = glow[mask]
    return gold

def generate_bomb_ball():
    """生成炸彈球圖像 (暗紅彈體 + 黃黑危險斜條紋 + 發光引信)"""
    bomb = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cx, cy = SIZE // 2, SIZE // 2 + 3
    radius = SIZE // 2 - 8
    
    # 繪製暗紅色彈體
    cv2.circle(bomb, (cx, cy), radius, (0, 0, 120, 255), -1)
    
    # 繪製黃黑斜條紋
    mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    cv2.circle(mask, (cx, cy), radius, 255, -1)
    
    stripes = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    for i in range(-SIZE, SIZE * 2, 12):
        # 繪製斜線多邊形
        pts = np.array([
            [i, 0], [i + 6, 0],
            [i - SIZE + 6, SIZE], [i - SIZE, SIZE]
        ], np.int32)
        cv2.fillPoly(stripes, [pts], (0, 215, 255, 255)) # 亮黃色
        
    # 只保留彈體內部的斜條紋，並套用透明度
    for c in range(3):
        stripes[:, :, c] = cv2.bitwise_and(stripes[:, :, c], mask)
    stripes[:, :, 3] = mask
    
    # 混合底色與條紋
    mask_stripes = stripes[:, :, 3] > 0
    bomb[mask_stripes] = cv2.addWeighted(bomb[mask_stripes], 0.4, stripes[mask_stripes], 0.6, 0)
    
    # 外框
    cv2.circle(bomb, (cx, cy), radius, (0, 0, 0, 255), 2)
    
    # 引信底座與引線
    cv2.rectangle(bomb, (cx - 4, cy - radius - 3), (cx + 4, cy - radius), (100, 100, 100, 255), -1)
    # 畫引信曲線
    fuse = [
        [cx, cy - radius - 3],
        [cx + 5, cy - radius - 10],
        [cx + 2, cy - radius - 15]
    ]
    cv2.polylines(bomb, [np.array(fuse, np.int32)], False, (20, 80, 150, 255), 2)
    # 火花
    cv2.circle(bomb, (cx + 2, cy - radius - 16), 4, (0, 255, 255, 255), -1)
    cv2.circle(bomb, (cx + 2, cy - radius - 16), 2, (255, 255, 255, 255), -1)
    return bomb

def generate_ice_ball():
    """生成冰凍球圖像 (晶瑩剔透冰藍色 + 精緻白色雪花幾何圖案)"""
    ice = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cx, cy = SIZE // 2, SIZE // 2
    radius = SIZE // 2 - 4
    
    # 放射狀冰藍色漸層
    for r in range(radius, 0, -2):
        factor = 1.0 - (r / radius)
        b = int(255)
        g = int(180 + 75 * factor)
        r_val = int(100 + 155 * factor)
        cv2.circle(ice, (cx, cy), r, (b, g, r_val, 255), -1)
        
    # 繪製雪花圖案 (8個對稱臂)
    for i in range(8):
        angle = math.radians(i * 45)
        p2_x = int(cx + radius * 0.8 * math.cos(angle))
        p2_y = int(cy + radius * 0.8 * math.sin(angle))
        # 主幹
        cv2.line(ice, (cx, cy), (p2_x, p2_y), (255, 255, 255, 255), 2)
        
        # 側邊冰晶分支
        sub_angle1 = angle + math.radians(35)
        sub_angle2 = angle - math.radians(35)
        mid_x = int(cx + radius * 0.45 * math.cos(angle))
        mid_y = int(cy + radius * 0.45 * math.sin(angle))
        
        v1_x = int(mid_x + 6 * math.cos(sub_angle1))
        v1_y = int(mid_y + 6 * math.sin(sub_angle1))
        v2_x = int(mid_x + 6 * math.cos(sub_angle2))
        v2_y = int(mid_y + 6 * math.sin(sub_angle2))
        cv2.line(ice, (mid_x, mid_y), (v1_x, v1_y), (255, 255, 255, 255), 1)
        cv2.line(ice, (mid_x, mid_y), (v2_x, v2_y), (255, 255, 255, 255), 1)
        
    cv2.circle(ice, (cx, cy), radius, (255, 230, 180, 255), 2)
    return ice

def generate_heart_ball():
    """生成愛心球圖像 (精準數學心形線 + 粉紅飽和填滿 + 白色發光外框)"""
    heart = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    cx, cy = SIZE // 2, SIZE // 2 - 3
    
    # 使用心形線參數方程式繪製
    pts = []
    for deg in range(360):
        angle = math.radians(deg)
        # 心形公式
        x = 16 * (math.sin(angle) ** 3)
        y = 13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle)
        # 縮放至合適大小
        px = int(cx + x * (SIZE / 38))
        py = int(cy - y * (SIZE / 38))
        pts.append([px, py])
        
    pts = np.array(pts, np.int32).reshape((-1, 1, 2))
    # 填入粉紅/桃紅色
    cv2.fillPoly(heart, [pts], (150, 50, 255, 255))
    # 畫白色發光邊緣
    cv2.polylines(heart, [pts], True, (255, 255, 255, 255), 2)
    # 畫內陰影
    cv2.polylines(heart, [pts], True, (100, 20, 180, 255), 1)
    return heart

# 輸出所有圖像
cv2.imwrite('assets/ball.png', generate_normal_ball())
cv2.imwrite('assets/ball_gold.png', generate_gold_ball())
cv2.imwrite('assets/ball_bomb.png', generate_bomb_ball())
cv2.imwrite('assets/ball_ice.png', generate_ice_ball())
cv2.imwrite('assets/ball_heart.png', generate_heart_ball())
print(">>> [圖片生成] 所有特殊球種 PNG 圖像已成功繪製至 assets/")

# =====================================================================
# 2. 音效資產生成器 (Procedural Audio Synthesizer)
# =====================================================================
SAMPLE_RATE = 44100

def write_wav(filename, data):
    """將 float 陣列轉換為 16-bit PCM 並寫入 WAV 檔案"""
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        
        # 轉換數值並包裝成二進位二位元組
        for val in data:
            # 限制振幅在 [-1.0, 1.0] 之間
            val = max(-1.0, min(1.0, val))
            sample = int(val * 32767.0)
            wav_file.writeframesraw(struct.pack('<h', sample))

def synthesize_hit_normal():
    """普通擊球聲: 快速上升的 Sine 波"""
    duration = 0.15
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 頻率從 600 掃描到 800 Hz
        freq = 600 + 200 * (t / duration)
        val = math.sin(2.0 * math.pi * freq * t)
        # 淡出包絡線
        envelope = 1.0 - (t / duration)
        data.append(val * envelope * 0.4)
    return data

def synthesize_miss():
    """漏接聲: 低沉的 Square 鋸齒波，帶強烈衰減"""
    duration = 0.3
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 頻率從 200 快速下降到 100 Hz
        freq = 200 - 100 * (t / duration)
        # Square 波
        val = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
        # 指數型衰減
        envelope = math.exp(-6 * t)
        data.append(val * envelope * 0.25)
    return data

def synthesize_hit_gold():
    """黃金球聲: 高亢閃亮的魔法鈴聲 (疊加雙 Sine 諧振)"""
    duration = 0.25
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 主頻率 1000 Hz 到 1800 Hz
        freq1 = 1000 + 800 * (t / duration)
        # 泛音頻率 (三倍頻)
        freq2 = freq1 * 1.5
        
        val = 0.7 * math.sin(2.0 * math.pi * freq1 * t) + 0.3 * math.sin(2.0 * math.pi * freq2 * t)
        envelope = (1.0 - (t / duration)) ** 1.5
        data.append(val * envelope * 0.4)
    return data

def synthesize_hit_bomb():
    """炸彈爆炸聲: 低頻 Square 波 + 狂暴白噪音"""
    duration = 0.50
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 頻率從 150 Hz 急速降至 30 Hz
        freq = 150 - 120 * (t / duration)
        
        # 混合低頻方波與白色隨機噪音
        square_wave = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
        noise = np.random.uniform(-1.0, 1.0)
        
        # 前期以爆炸噪音為主，後期以低頻震動為主
        ratio = t / duration
        val = (1.0 - ratio) * noise + ratio * square_wave
        
        # 長衰減包絡線
        envelope = (1.0 - ratio) ** 2
        data.append(val * envelope * 0.5)
    return data

def synthesize_hit_ice():
    """冰凍結晶聲: 急速下降並帶有抖動的高頻 Sine 波"""
    duration = 0.20
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # 頻率從 1400 Hz 掃描至 500 Hz，並加上顫音效果
        vibrato = 1.0 + 0.1 * math.sin(2.0 * math.pi * 50 * t)
        freq = (1400 - 900 * (t / duration)) * vibrato
        
        val = math.sin(2.0 * math.pi * freq * t)
        envelope = math.exp(-8 * t)
        data.append(val * envelope * 0.35)
    return data

def synthesize_hit_heart():
    """愛心治癒聲: 兩段上升的暖和 Sine 雙音階"""
    duration = 0.30
    num_samples = int(SAMPLE_RATE * duration)
    data = []
    # 兩段連續音
    half_samples = num_samples // 2
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        if i < half_samples:
            # 第一段低音上升 (400 -> 600 Hz)
            t_sub = i / SAMPLE_RATE
            dur_sub = half_samples / SAMPLE_RATE
            freq = 400 + 200 * (t_sub / dur_sub)
            val = math.sin(2.0 * math.pi * freq * t_sub)
            envelope = 1.0 - (t_sub / dur_sub)
            data.append(val * envelope * 0.35)
        else:
            # 第二段高音上升 (600 -> 900 Hz)
            t_sub = (i - half_samples) / SAMPLE_RATE
            dur_sub = (num_samples - half_samples) / SAMPLE_RATE
            freq = 600 + 300 * (t_sub / dur_sub)
            val = math.sin(2.0 * math.pi * freq * t_sub)
            envelope = 1.0 - (t_sub / dur_sub)
            data.append(val * envelope * 0.35)
    return data

# 輸出所有合成 WAV 檔案
write_wav('assets/hit.wav', synthesize_hit_normal())
write_wav('assets/miss.wav', synthesize_miss())
write_wav('assets/hit_gold.wav', synthesize_hit_gold())
write_wav('assets/hit_bomb.wav', synthesize_hit_bomb())
write_wav('assets/hit_ice.wav', synthesize_hit_ice())
write_wav('assets/hit_heart.wav', synthesize_hit_heart())
print(">>> [音效生成] 所有升級版 WAV 聲音資產已成功合成至 assets/")
print(">>> [完成] 所有專案資產皆已建置完成，準備升級遊戲本體！")
