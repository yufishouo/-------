import sys

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Boss respawn logic
target1 = '''                        if boss['hp'] <= 0:
                            boss['active'] = False
                            boss['dead'] = True
                            next_boss_score += 300
                            score += 500'''
replacement1 = '''                        if boss['hp'] <= 0:
                            boss['active'] = False
                            boss['dead'] = False
                            score += 500
                            next_boss_score = score + 300'''
content = content.replace(target1, replacement1)

# Fix 2: Prevent multiple hits on deflected balls
target2 = '''                # 碰撞事件處理
                if hit:
                    b_type = ball['type']'''
replacement2 = '''                # 碰撞事件處理
                if hit and not ball.get('deflected', False):
                    b_type = ball['type']'''
content = content.replace(target2, replacement2)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Bugs fixed.')
