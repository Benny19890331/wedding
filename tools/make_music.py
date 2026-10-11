# 用程式合成背景音樂：帕海貝爾《D 大調卡農》音樂盒版
# 樂曲是 1680 年代的作品（公有領域），聲音完全由這支程式產生，沒有版權問題。
# 用法：python tools/make_music.py   → assets/audio/canon-musicbox.mp3
import math, os, struct, subprocess, wave
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SR = 44100
BEAT = 60 / 63            # 一拍的秒數
NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440 * 2 ** ((NOTE[n] + (o - 4) * 12 - 9) / 12)


def pluck(freq, dur, vol=1.0):
    """音樂盒的一個音：敲一下之後慢慢消失，帶一點金屬泛音"""
    t = np.arange(int(SR * dur)) / SR
    tau = 0.55 + 220 / freq * 0.5                 # 低音餘韻長、高音短
    env = np.exp(-t / tau) * (1 - np.exp(-t / 0.002))
    s = (np.sin(2 * math.pi * freq * t)
         + 0.42 * np.sin(2 * math.pi * freq * 2.0 * t) * np.exp(-t / (tau * 0.5))
         + 0.18 * np.sin(2 * math.pi * freq * 3.01 * t) * np.exp(-t / (tau * 0.3))
         + 0.10 * np.sin(2 * math.pi * freq * 5.4 * t) * np.exp(-t / 0.08))
    return s * env * vol


# 一輪 8 個和弦，每個和弦 2 拍：D A Bm F#m G D G A
CHORDS = [('D3', ['D4', 'F#4', 'A4']), ('A2', ['C#4', 'E4', 'A4']), ('B2', ['B3', 'D4', 'F#4']), ('F#2', ['A3', 'C#4', 'F#4']),
          ('G2', ['B3', 'D4', 'G4']), ('D3', ['A3', 'D4', 'F#4']), ('G2', ['B3', 'D4', 'G4']), ('A2', ['C#4', 'E4', 'A4'])]
LINE1 = ['F#5', 'E5', 'D5', 'C#5', 'B4', 'A4', 'B4', 'C#5']                                   # 每個和弦一個長音
LINE2 = ['D5', 'C#5', 'B4', 'A4', 'G4', 'F#4', 'G4', 'E4']
LINE3 = ['D5', 'F#5', 'A5', 'G5', 'F#5', 'D5', 'F#5', 'E5', 'D5', 'B4', 'D5', 'A5', 'G5', 'B5', 'A5', 'G5']   # 每拍一個音
LINE4 = ['F#5', 'D5', 'E5', 'C#5', 'D5', 'B4', 'C#5', 'A4', 'B4', 'G4', 'A4', 'F#4', 'G4', 'E4', 'F#4', 'E4',
         'D5', 'F#5', 'A5', 'A5', 'B5', 'G5', 'A5', 'F#5', 'D5', 'D6', 'D6', 'C#6', 'D6', 'B5', 'C#6', 'A5']   # 每半拍一個音

CYCLE = 16 * BEAT
# 每一輪要彈哪些聲部：(琶音, 旋律, 音量)
PLAN = [(True, None), (True, 'L1'), (True, 'L2+L1'), (True, 'L3'), (True, 'L4'), (True, 'L3+L1'), (True, 'L1')]
total = CYCLE * len(PLAN) + 4.0
buf = np.zeros(int(SR * total))


def add(name, start, dur, vol):
    s = pluck(hz(name), dur, vol)
    i = int(start * SR)
    buf[i:i + len(s)] += s[:len(buf) - i]


for c, (arp, mel) in enumerate(PLAN):
    t0 = c * CYCLE
    for k, (bass, tri) in enumerate(CHORDS):
        ts = t0 + k * 2 * BEAT
        add(bass, ts, 3.2, 0.55)
        add(bass[:-1] + str(int(bass[-1]) + 1), ts, 3.0, 0.22)
        if arp:
            for j, n in enumerate([tri[0], tri[1], tri[2], tri[1]]):       # 分解和弦
                add(n, ts + j * BEAT / 2, 1.6, 0.26)
    if not mel:
        continue
    if 'L1' in mel:
        for k, n in enumerate(LINE1): add(n, t0 + k * 2 * BEAT, 3.0, 0.62 if mel == 'L1' else 0.34)
    if 'L2' in mel:
        for k, n in enumerate(LINE2): add(n, t0 + k * 2 * BEAT, 3.0, 0.5)
    if 'L3' in mel:
        for k, n in enumerate(LINE3): add(n, t0 + k * BEAT, 2.0, 0.55)
    if 'L4' in mel:
        for k, n in enumerate(LINE4): add(n, t0 + k * BEAT / 2, 1.4, 0.5)

# 結尾停在 D 和弦
tend = CYCLE * len(PLAN)
for n, v in (('D3', 0.6), ('A3', 0.3), ('D4', 0.35), ('F#4', 0.35), ('A4', 0.35), ('D5', 0.6)):
    add(n, tend, 4.0, v)

# 簡單的空間感：兩道回聲，左右聲道略有不同
def echo(x, delay, gain):
    y = x.copy(); d = int(delay * SR)
    y[d:] += x[:-d] * gain
    return y

left = echo(echo(buf, 0.23, 0.22), 0.41, 0.12)
right = echo(echo(buf, 0.29, 0.22), 0.37, 0.12)
peak = max(np.abs(left).max(), np.abs(right).max())
left, right = left / peak * 0.82, right / peak * 0.82
fade = int(SR * 2.5)                                # 頭尾淡入淡出，循環播放時比較自然
ramp = np.linspace(0, 1, fade)
for ch in (left, right):
    ch[:int(SR * 0.05)] *= np.linspace(0, 1, int(SR * 0.05)); ch[-fade:] *= ramp[::-1]

out_dir = os.path.join(ROOT, 'assets', 'audio')
os.makedirs(out_dir, exist_ok=True)
wav = os.path.join(ROOT, 'work', 'canon-musicbox.wav')
pcm = (np.stack([left, right], axis=1) * 32767).astype('<i2')
with wave.open(wav, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
mp3 = os.path.join(out_dir, 'canon-musicbox.mp3')
subprocess.run([r'D:/VideoDedup/bin/ffmpeg.exe', '-v', 'error', '-y', '-i', wav, '-codec:a', 'libmp3lame', '-b:a', '112k', mp3], check=True)
os.remove(wav)
print('seconds', round(total, 1), 'size KB', os.path.getsize(mp3) // 1024)
