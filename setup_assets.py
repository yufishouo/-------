import os
import math
import struct
import wave
import numpy as np
import cv2

# Ensure assets directory exists
os.makedirs('assets', exist_ok=True)

# 1. Generate Ball Image (a simple black and white soccer ball representation)
size = 64
# Create a transparent background
ball = np.zeros((size, size, 4), dtype=np.uint8)

# Draw white circle
center = (size // 2, size // 2)
radius = size // 2 - 2
cv2.circle(ball, center, radius, (255, 255, 255, 255), -1)

# Draw black pentagon in the center
pts = []
for i in range(5):
    angle = math.radians(i * 72 - 90)
    x = int(center[0] + radius * 0.4 * math.cos(angle))
    y = int(center[1] + radius * 0.4 * math.sin(angle))
    pts.append([x, y])
pts = np.array(pts, np.int32)
pts = pts.reshape((-1, 1, 2))
cv2.fillPoly(ball, [pts], (0, 0, 0, 255))

# Draw lines to the edges
for i in range(5):
    angle = math.radians(i * 72 - 90)
    p1_x = int(center[0] + radius * 0.4 * math.cos(angle))
    p1_y = int(center[1] + radius * 0.4 * math.sin(angle))
    p2_x = int(center[0] + radius * math.cos(angle))
    p2_y = int(center[1] + radius * math.sin(angle))
    cv2.line(ball, (p1_x, p1_y), (p2_x, p2_y), (0, 0, 0, 255), 2)

# Outline
cv2.circle(ball, center, radius, (0, 0, 0, 255), 2)

cv2.imwrite('assets/ball.png', ball)
print("Created assets/ball.png")

# 2. Generate Sound Effects
def generate_wav(filename, frequency_start, frequency_end, duration_ms, wave_type='sine'):
    sample_rate = 44100
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Linear frequency sweep
            freq = frequency_start + (frequency_end - frequency_start) * (t / (duration_ms / 1000.0))
            
            if wave_type == 'sine':
                value = math.sin(2.0 * math.pi * freq * t)
            elif wave_type == 'square':
                value = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            elif wave_type == 'noise':
                value = np.random.uniform(-1, 1)
                
            # Envelope (fade out)
            envelope = 1.0 - (t / (duration_ms / 1000.0))
            
            # Convert to 16-bit integer
            sample = int(value * envelope * 32767.0 * 0.5) # 0.5 volume
            wav_file.writeframesraw(struct.pack('<h', sample))
            
    print(f"Created {filename}")

# Hit sound: high pitch 'ping' (sine wave sweep up slightly)
generate_wav('assets/hit.wav', 600, 800, 150, 'sine')

# Miss sound: low pitch 'buzz' (square wave sweep down)
generate_wav('assets/miss.wav', 200, 100, 300, 'square')

print("All assets generated.")
