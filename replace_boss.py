import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Boss Spawning Logic
target1 = '''            # 檢查並觸發 Fever Mode'''
replacement1 = '''            # Boss 觸發邏輯
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
                effects.append({'text': 'WARNING: BOSS APPROACHING!', 'x': FRAME_W//2 - 200, 'y': FRAME_H//2, 'color': (0, 0, 255), 'life': 90, 'vx': 0, 'vy': -1.0})

            # 檢查並觸發 Fever Mode'''
content = content.replace(target1, replacement1)

# 2. Boss Update & Render
target2 = '''            # 5. 畫面渲染'''
replacement2 = '''            # 5. 畫面渲染
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
'''
content = content.replace(target2, replacement2)

# 3. Boss Collision logic in physics
target3 = '''                # 更新位置
                ball['x'] += ball['dx'] * speed_mult
                ball['y'] += ball['dy'] * speed_mult'''
replacement3 = '''                # 更新位置
                ball['x'] += ball['dx'] * speed_mult
                ball['y'] += ball['dy'] * speed_mult
                
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
                            boss['dead'] = True
                            next_boss_score += 300
                            score += 500
                            cyber_coins += 50
                            shake_timer = 30
                            flash_timer = 20
                            flash_color = (0, 0, 255)
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
                    continue'''
content = content.replace(target3, replacement3)

# 4. Ball Deflection logic in hit handling
target4 = '''                    if b_type == 'normal':
                        pts_earned = 10 * mult
                        score += pts_earned
                        combo += 1
                        msg = random.choice(["NICE!", "GREAT!", "GOOD!"]) if combo > 3 else ""
                        text_str = f'+{pts_earned} {msg}' if msg else f'+{pts_earned}'
                        effects.append({'text': text_str, 'x': bx + random.randint(-15, 15), 'y': by, 'color': (0, 255, 0), 'life': 30, 'vx': random.uniform(-0.5, 0.5), 'vy': -3.0})
                        hit_stop_timer = 2
                        spawn_particles(particles, bx, by, (200, 200, 200)) # 灰色煙霧粒子
                        if sounds['hit']: sounds['hit'].play()'''
replacement4 = '''                    if b_type == 'normal':
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
                            ball['deflected'] = True'''
content = content.replace(target4, replacement4)

# 5. Prevent removing deflected balls
target5 = '''                    balls.remove(ball)
                else:
                    # 漏接判定'''
replacement5 = '''                    if not ball.get('deflected', False):
                        balls.remove(ball)
                else:
                    # 漏接判定'''
content = content.replace(target5, replacement5)


with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Boss modifications complete.')
