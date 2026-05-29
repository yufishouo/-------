import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Modify STATE_MENU_DIFF UI and logic
target_diff = '''            # IlOiܦr
            pulse = int(math.sin(time.time() * 8) * 3)
            draw_text(frame, "Press '1', '2', or '3' to deploy!", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_GOLD, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key in [ord('1'), ord('2'), ord('3')]:'''

replacement_diff = '''            # IlOiܦr
            pulse = int(math.sin(time.time() * 8) * 3)
            draw_text(frame, "Press '1', '2', or '3' to deploy!  |  'ESC' to go Back", (0, int(FRAME_H * 0.88) + pulse), 0.7, COLOR_NEON_GOLD, 2, center=True)
            
            key = cv2.waitKey(30) & 0xFF
            if key == 27: # ESC
                game_state = STATE_MENU_MODE
            elif key in [ord('1'), ord('2'), ord('3')]:'''

content = content.replace(target_diff, replacement_diff)

# 2. Modify STATE_PLAYING to allow ESC to end game gracefully
target_playing = '''            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('b') or key == ord('B'):'''

replacement_playing = '''            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == 27: # ESC key to surrender/exit to menu
                lives = 0 # Force game over logic to run safely on next frame, or just change state
                game_state = STATE_GAMEOVER
                speak('Game Over')
            elif key == ord('b') or key == ord('B'):'''

content = content.replace(target_playing, replacement_playing)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added back and exit buttons.')
