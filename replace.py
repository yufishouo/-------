import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. PLAYING state shield color setup
target1 = '''        elif game_state == STATE_PLAYING:
            is_shield_active = (time.time() < shield_timer)'''
replacement1 = '''        elif game_state == STATE_PLAYING:
            if equipped_shield == 'quantum_purple':
                shield_glow_color = (255, 50, 150)
            elif equipped_shield == 'deep_sea_blue':
                shield_glow_color = (255, 150, 0)
            else:
                shield_glow_color = (0, 255, 255)
                
            is_shield_active = (time.time() < shield_timer)'''
content = content.replace(target1, replacement1)

# 2. Replace the hardcoded (0, 255, 255) in the left/right hand gravity shield with shield_glow_color
target2 = '''draw_glow_circle(frame, lwx, lwy, 45 + pulse, (0, 255, 255), 2, glow_factor=4)'''
replacement2 = '''draw_glow_circle(frame, lwx, lwy, 45 + pulse, shield_glow_color, 2, glow_factor=4)'''
content = content.replace(target2, replacement2)

target3 = '''draw_glow_circle(frame, rwx, rwy, 45 + pulse, (0, 255, 255), 2, glow_factor=4)'''
replacement3 = '''draw_glow_circle(frame, rwx, rwy, 45 + pulse, shield_glow_color, 2, glow_factor=4)'''
content = content.replace(target3, replacement3)

target4 = '''draw_text(frame, "GRAVITY SHIELD ACTIVE", (0, 95 + pulse), 0.65, (0, 255, 255), 2, center=True)'''
replacement4 = '''draw_text(frame, "GRAVITY SHIELD ACTIVE", (0, 95 + pulse), 0.65, shield_glow_color, 2, center=True)'''
content = content.replace(target4, replacement4)

# 3. Add cyber coins to gold ball collision
target5 = '''                    elif b_type == 'gold':
                        # 黃金球：獲得 3 倍基本分並乘上連擊加成！
                        pts_earned = 30 * mult
                        score += pts_earned
                        combo += 1
                        flash_timer = 7 # 耀眼金色閃屏
                        flash_color = (0, 215, 255)
                        effects.append({'text': f'PERFECT! +{pts_earned}', 'x': bx + random.randint(-15, 15), 'y': by, 'color': (0, 215, 255), 'life': 40, 'vx': random.uniform(-1.0, 1.0), 'vy': -4.0})'''
replacement5 = '''                    elif b_type == 'gold':
                        # 黃金球：獲得 3 倍基本分並乘上連擊加成！
                        pts_earned = 30 * mult
                        score += pts_earned
                        combo += 1
                        coins_earned = 5
                        cyber_coins += coins_earned
                        flash_timer = 7 # 耀眼金色閃屏
                        flash_color = (0, 215, 255)
                        effects.append({'text': f'PERFECT! +{pts_earned}', 'x': bx + random.randint(-15, 15), 'y': by, 'color': (0, 215, 255), 'life': 40, 'vx': random.uniform(-1.0, 1.0), 'vy': -4.0})
                        effects.append({'text': f'+{coins_earned} COINS!', 'x': bx + random.randint(-15, 15), 'y': by + 20, 'color': (0, 215, 255), 'life': 40, 'vx': random.uniform(-1.0, 1.0), 'vy': -4.0})'''
content = content.replace(target5, replacement5)

# 4. Save cyber coins on game over
target6 = '''        elif game_state == STATE_GAMEOVER:
            # 判斷是否打破歷史高分紀錄並儲存
            if score > high_score:
                high_score = score
                save_high_score(high_score)
                new_record_broken = True'''
replacement6 = '''        elif game_state == STATE_GAMEOVER:
            # 判斷是否打破歷史高分紀錄並儲存
            if score > high_score:
                high_score = score
                new_record_broken = True
            
            # 儲存進度 (包含分數與代幣)
            save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield})'''
content = content.replace(target6, replacement6)

# Final exit save adjustment
target7 = '''    if score > high_score:
        save_high_score(score)'''
replacement7 = '''    if score > high_score:
        save_data({'high_score': score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield})'''
content = content.replace(target7, replacement7)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Modifications complete.')
