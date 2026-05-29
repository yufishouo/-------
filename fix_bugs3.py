with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # 1. Fix speak('Game Over') indentation inside hit_bomb
    if 'speak(\'Game Over\')' in line and 'lives <= 0' in lines[i-2]:
        # Inside hit_bomb logic
        new_lines.append('                                speak(\'Game Over\')\n')
    # 2. Fix speak('Game Over') indentation inside miss
    elif 'speak(\'Game Over\')' in line and 'lives <= 0' in lines[i-2]:
        # Inside miss logic
        new_lines.append('                                speak(\'Game Over\')\n')
    # Or just fix ANY speak('Game Over') that has 28 spaces instead of 32
    elif "speak('Game Over')" in line and line.startswith('                            speak'):
        new_lines.append('                                speak(\'Game Over\')\n')
    # 3. Fix exit save logic at the bottom of the script
    elif "if score > high_score:" in line and "save_data" in lines[i+1]:
        # Skip the if condition and just save unconditionally
        # We will write the save_data in the next line handler
        pass
    elif "save_data({'high_score': score" in line and "if score > high_score:" in lines[i-1]:
        # Replace the conditional save with unconditional save
        new_lines.append("    save_data({'high_score': max(score, high_score), 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield})\n")
    elif "print(f\">>>" in line and "s" in line and "if score > high_score:" in lines[i-2]:
        # Also remove the indentation of the print statement
        new_lines.append('    print(">>> [System] Data saved on exit.")\n')
    else:
        new_lines.append(line)

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Now, also add a save trigger directly into the shop when an item is bought or equipped.
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
target_shop = '''                    if item['id'] in unlocked_items:
                        equipped_shield = item['id']
                    elif cyber_coins >= item['price']:
                        cyber_coins -= item['price']
                        unlocked_items.append(item['id'])
                        equipped_shield = item['id']'''
                        
replacement_shop = '''                    if item['id'] in unlocked_items:
                        equipped_shield = item['id']
                        save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield})
                    elif cyber_coins >= item['price']:
                        cyber_coins -= item['price']
                        unlocked_items.append(item['id'])
                        equipped_shield = item['id']
                        save_data({'high_score': high_score, 'cyber_coins': cyber_coins, 'unlocked_items': unlocked_items, 'equipped_shield': equipped_shield})'''

content = content.replace(target_shop, replacement_shop)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Bug fixes applied.")
