"""Record every Listening part of a test with Kokoro. Usage: python3 gen_audio.py t01"""
import json, sys, os, subprocess, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
TTS = "/tmp/claude-0/-home-claude/ff8f22aa-a13a-5d01-b9c1-17a141a07c47/scratchpad/tts"
k = Kokoro(f"{TTS}/kokoro.onnx", f"{TTS}/voices.bin")
slug = sys.argv[1]
parts = json.load(open(f"build/{slug}.script.json"))
src = __import__(slug).TEST["listening"]["parts"]
out = f"build/audio/{slug}"; os.makedirs(out, exist_ok=True)
meta = []
for pi, (p, sp) in enumerate(zip(parts, src)):
    voices = {"N": "bm_george", **{s: v["voice"] for s, v in sp["speakers"].items()}}
    speed = 1.0 if pi == 3 else 0.95
    sr = 24000; chunks = [np.zeros(int(sr * 0.8), np.float32)]; t = 0.8; marks = []; prev = None
    for l in p["script"]:
        if "pause" in l:
            chunks.append(np.zeros(int(sr * l["pause"]), np.float32)); t += l["pause"]; continue
        gap = (0.75 if prev != l["s"] else 0.4) if prev else 0
        if gap: chunks.append(np.zeros(int(sr * gap), np.float32)); t += gap
        a, sr = k.create(l["t"], voice=voices[l["s"]], speed=0.92 if l["s"] == "N" else speed, lang="en-gb")
        a = a.astype(np.float32); a = a / max(1e-6, np.abs(a).max()) * 0.89
        marks.append({"s": l["s"], "t": round(t, 2), "e": round(t + len(a) / sr, 2)}); chunks.append(a); t += len(a) / sr; prev = l["s"]
    chunks.append(np.zeros(int(sr * 0.8), np.float32)); t += 0.8
    wav = f"{out}/part{pi+1}.wav"; sf.write(wav, np.concatenate(chunks), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5", "-ac", "1", "-b:a", "80k", f"{out}/part{pi+1}.mp3"], check=True)
    os.remove(wav)
    meta.append({"dur": round(t, 2), "marks": marks}); print(slug, p["label"], round(t, 1), "s", flush=True)
json.dump(meta, open(f"{out}/meta.json", "w"))
print("total", round(sum(m["dur"] for m in meta) / 60, 1), "min")
