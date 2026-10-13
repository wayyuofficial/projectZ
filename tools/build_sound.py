# -*- coding: utf-8 -*-
"""효과음·배경음악을 게임 파일 안에 넣는다 (지시 #178 녹음 권총 · #180 스킬로 만든 효과음 19·배경음악).

게임은 파일 하나여야 하고(c6) 통신을 안 한다(c3) — 그래서 소리 파일을 data URI(base64) 로
`game/index.html` 의 `const SND_SAMPLES = {...};` 한 줄에 박는다. 원본은 `source/sound/` 그대로 둔다.

다듬기: 모노 · 끝 꼬리 자르기(-48dB 아래, 30ms 페이드) · 표본율 낮춤(표 SOUNDS) · 최고값 -1dBFS · 16비트 WAV.
쓰는 법: python tools/build_sound.py            (표 SOUNDS 의 소리를 전부 다시 넣는다)
결과 확인용 WAV: source/sound/build/<이름>.wav
"""
import io, os, re, sys, wave, base64
import numpy as np
from scipy.signal import resample_poly

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")
TAIL_DB = -48.0
FADE_S = 0.03

# 게임 안 이름 → (원본 파일, 출력 표본율). 효과음은 game-sound 스킬(D:/bgmcreator/soundgen.py)로 만든 것 — 레시피는 source/sound/sfx/.soundgen/ (지시 #180)
# 권총은 사람이 넣은 녹음(지시 #178). 합성 권총(sfx_pistol.wav)도 만들어 두었다 — 바꾸려면 이 줄만 바꾼다.
SFX_SR = 22050   # 효과음은 22kHz 로 — 게임 파일 상한(c27 5MB) 안에 19개를 넣으려고
SOUNDS = {
    "pistol": ("source/sound/sfx_pistol_real.wav", 32000),
    # 지시 #197 — 총기는 사람이 넣은 녹음으로(source/sound/sfx_*.wav). 합성 v2 는 source/sound/sfx/ 에 남아 있다(이 줄만 바꾸면 돌아간다)
    "rifle": ("source/sound/sfx_rifle.wav", SFX_SR),
    "rifle_1": ("source/sound/sfx_rifle_01.wav", SFX_SR),
    "rifle_2": ("source/sound/sfx_rifle_02.wav", SFX_SR),
    "rifle_3": ("source/sound/sfx_rifle_03.wav", SFX_SR),
    "mg": ("source/sound/sfx_machinegun.wav", SFX_SR),
    "mg_1": ("source/sound/sfx_machinegun_01.wav", SFX_SR),
    "mg_2": ("source/sound/sfx_machinegun_02.wav", SFX_SR),
    "mg_3": ("source/sound/sfx_machinegun_03.wav", SFX_SR),
    "shotgun": ("source/sound/sfx_shotgun.wav", SFX_SR),
    "flame": ("source/sound/sfx_flamethrower.wav", SFX_SR),
    "bolt": ("source/sound/sfx_crossbow.wav", SFX_SR),
    "boom": ("source/sound/sfx_grenade_launch.wav", SFX_SR),
    "explode": ("source/sound/sfx_grenade_explode.wav", SFX_SR),
    "saw": ("source/sound/sfx_chainsaw.wav", SFX_SR),
    "rail": ("source/sound/sfx_railgun.wav", SFX_SR),
    "kill": ("source/sound/sfx/sfx_kill.wav", SFX_SR),
    "boss_in": ("source/sound/sfx/sfx_boss_in.wav", SFX_SR),
    "boss_kill": ("source/sound/sfx/sfx_boss_kill.wav", SFX_SR),
    "zone": ("source/sound/sfx/sfx_zone.wav", SFX_SR),
    "death": ("source/sound/sfx/sfx_death.wav", SFX_SR),
    "gacha": ("source/sound/sfx/sfx_gacha.wav", SFX_SR),
    "gacha_shine": ("source/sound/sfx/sfx_gacha_shine.wav", SFX_SR),
    "buy": ("source/sound/sfx/sfx_buy.wav", SFX_SR),
    "skill": ("source/sound/sfx/sfx_skill.wav", SFX_SR),
    "tap": ("source/sound/sfx/sfx_tap.wav", SFX_SR),
}


def load(path):
    w = wave.open(path, "rb")
    ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64) / (1 << 23)
    elif sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128) / 128
    else:
        raise SystemExit("지원 안 하는 샘플 폭: %d 바이트" % sw)
    return x.reshape(-1, ch).mean(axis=1), sr


def shape(x, sr, out_sr):
    win = int(sr * 0.01)
    rms = np.array([np.sqrt((x[i:i + win] ** 2).mean() + 1e-12) for i in range(0, len(x), win)])
    loud = np.where(20 * np.log10(rms) > TAIL_DB)[0]
    end = min(len(x), (loud[-1] + 1) * win) if len(loud) else len(x)
    x = x[:end].copy()
    f = min(len(x), int(sr * FADE_S))
    x[-f:] *= np.linspace(1, 0, f)
    g = np.gcd(out_sr, sr)
    y = resample_poly(x, out_sr // g, sr // g)
    y *= 10 ** (-1 / 20) / max(1e-9, np.abs(y).max())
    return y


def to_wav(y, out_sr):
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(out_sr)
    w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
    w.close()
    return buf.getvalue()


# 배경음악(지시 #180) — 스테레오를 모노로, 24kHz, OGG Vorbis(압축 0.7 ≈ 48kbps). WAV 로는 34초에 5.9MB 라 게임 파일 상한(c27)을 넘는다.
BGM = ("source/sound/bgm/bgm_ai_apocalypse.wav", 24000, 0.7)   # 지시 #182 — AI 작곡(구글 Lyria 3.5, aimusic.py) 32마디 루프. 이전: 합성 bgm_apocalypse.wav(#181) · bgm_combat_v1_peaceful.wav(#180)


def build_bgm():
    import soundfile as sf
    rel, out_sr, q = BGM
    x, sr = sf.read(os.path.join(ROOT, rel))
    m = x.mean(axis=1) if x.ndim == 2 else x
    g = np.gcd(out_sr, sr)
    y = resample_poly(m, out_sr // g, sr // g).astype(np.float32)   # 루프 곡이라 꼬리를 자르지 않는다
    out = os.path.join(ROOT, "source", "sound", "build", "bgm.ogg")
    # libsndfile 1.2 의 Vorbis 인코더는 윈도우에서 큰 덩어리를 한 번에 쓰면 스택이 넘쳐 죽는다(2026-10-08) — 4096 프레임씩
    with sf.SoundFile(out, "w", out_sr, 1, format="OGG", subtype="VORBIS", compression_level=q) as f:
        for i in range(0, len(y), 4096):
            f.write(y[i:i + 4096])
    data = io.open(out, "rb").read()
    # M26 (지시 #191) — 배경음악은 게임 파일 밖 game/snd/bgm-<해시>.ogg 로(게임은 오디오 요소로 튼다). 옛 bgm-*.ogg 는 지운다
    import hashlib, glob
    name = "bgm-%s.ogg" % hashlib.sha256(data).hexdigest()[:10]
    sdir = os.path.join(ROOT, "game", "snd"); os.makedirs(sdir, exist_ok=True)
    for old in glob.glob(os.path.join(sdir, "bgm-*.ogg")):
        if os.path.basename(old) != name:
            os.remove(old)
    io.open(os.path.join(sdir, name), "wb").write(data)
    print("bgm: %s → %.2f초 · %dHz · OGG %d 바이트 → game/snd/%s" % (rel, len(y) / out_sr, out_sr, len(data), name))
    return "const SND_BGM = 'snd/%s';" % name


def main():
    parts = []
    os.makedirs(os.path.join(ROOT, "source", "sound", "build"), exist_ok=True)
    total = 0
    for name, (rel, out_sr) in SOUNDS.items():
        x, sr = load(os.path.join(ROOT, rel))
        y = shape(x, sr, out_sr)
        data = to_wav(y, out_sr)
        io.open(os.path.join(ROOT, "source", "sound", "build", name + ".wav"), "wb").write(data)
        parts.append("%s: 'data:audio/wav;base64,%s'" % (name, base64.b64encode(data).decode("ascii")))
        total += len(parts[-1])
        print("%s: %s → %.2f초 · %dHz · %d 바이트(base64 %d)" % (name, rel, len(y) / out_sr, out_sr, len(data), len(parts[-1])))
    print("합 base64 %d 바이트" % total)
    line = "const SND_SAMPLES = { %s };" % ", ".join(parts)
    t = io.open(GAME, encoding="utf-8").read()
    n = len(re.findall(r"^const SND_SAMPLES = \{.*\};$", t, flags=re.M))
    if n != 1:
        raise SystemExit("game/index.html 에 'const SND_SAMPLES = {...};' 줄이 %d 개다 — 하나여야 한다" % n)
    t = re.sub(r"^const SND_SAMPLES = \{.*\};$", lambda m: line, t, flags=re.M)
    bl = build_bgm()
    if len(re.findall(r"^const SND_BGM = '.*';$", t, flags=re.M)) != 1:
        raise SystemExit("game/index.html 에 'const SND_BGM = ...;' 줄이 하나여야 한다")
    t = re.sub(r"^const SND_BGM = '.*';$", lambda m: bl, t, flags=re.M)
    io.open(GAME, "w", encoding="utf-8", newline="").write(t)
    print("game/index.html 에 넣었다")


if __name__ == "__main__":
    main()
