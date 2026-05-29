import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Refactoring: Add docstrings and type hints
target_reset = 'def reset_game_state(difficulty, high_score):'
replacement_reset = '''def reset_game_state(difficulty: int, high_score: int) -> dict:
    """
    初始化或重置遊戲狀態 (Initialize/Reset Game State)
    根據不同的難度設定給予對應的生命值與初始球速，並重置所有技能冷卻、Boss 狀態與分數。
    
    Args:
        difficulty (int): 遊戲難度 (1=Easy, 2=Normal, 3=Hard)
        high_score (int): 目前的歷史最高分紀錄
        
    Returns:
        dict: 包含所有遊戲變數的初始狀態字典
    """'''
content = content.replace(target_reset, replacement_reset)

target_main = 'def main():'
replacement_main = '''def main():
    """
    遊戲主迴圈與核心邏輯 (Main Game Loop & Core Logic)
    負責管理系統資源 (Webcam, 音效)、影像擷取、狀態機切換 (Menu -> Shop -> Playing -> GameOver)、
    以及核心的物理碰撞偵測與畫面渲染更新。
    """'''
content = content.replace(target_main, replacement_main)

target_draw_text = 'def draw_text(img, text, pos, scale, color, thickness=2, center=False):'
replacement_draw_text = '''def draw_text(img, text, pos, scale, color, thickness=2, center=False):
    """
    繪製文字工具函式 (Draw Text Helper)
    封裝了 OpenCV 的 putText 功能，支援文字置中對齊以及自動加上黑色邊框以提升閱讀性。
    """'''
content = content.replace(target_draw_text, replacement_draw_text)

target_glass = 'def draw_glass_panel(img, x1, y1, x2, y2, color, alpha, border_color=(255,255,255), border_thickness=1, corner_radius=15):'
replacement_glass = '''def draw_glass_panel(img, x1, y1, x2, y2, color, alpha, border_color=(255,255,255), border_thickness=1, corner_radius=15):
    """
    繪製毛玻璃特效面板 (Draw Glassmorphism Panel)
    用來產生具備半透明與圓角邊框的高質感 UI 面板，適用於商店與選單介面。
    """'''
content = content.replace(target_glass, replacement_glass)

target_synth = 'def generate_synthwave_grid(w, h, t):'
replacement_synth = '''def generate_synthwave_grid(w: int, h: int, t: float):
    """
    動態 3D 霓虹網格背景渲染 (Dynamic 3D Synthwave Grid)
    利用透視投影 (Perspective Projection) 原理，即時運算產生向後方無限延伸的流動網格。
    """'''
content = content.replace(target_synth, replacement_synth)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Phase 3 polish complete.")
