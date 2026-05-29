import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = '''            draw_text(frame, "Press '1', '2', or '3' to deploy!", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_GOLD, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key in [ord('1'), ord('2'), ord('3')]:'''
            
replacement1 = '''            draw_text(frame, "Press '1', '2', or '3' to deploy!  |  'ESC' to go Back", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_GOLD, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                game_state = STATE_MENU_MODE
            elif key in [ord('1'), ord('2'), ord('3')]:'''

content = content.replace(target1, replacement1)

target2 = '''            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('b') or key == ord('B'):
                bg_replace = not bg_replace'''
                
replacement2 = '''            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:
                lives = 0
                game_state = STATE_GAMEOVER
                speak('Game Over')
            elif key == ord('b') or key == ord('B'):
                bg_replace = not bg_replace'''

content = content.replace(target2, replacement2)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement done.")
