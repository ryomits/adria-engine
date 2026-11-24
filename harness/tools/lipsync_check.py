"""Offline lip-sync check: WAV -> mouth curve -> metrics, plot and representative frames.

Usage:
    uv run --extra tools python tools/lipsync_check.py OUT_DIR a.wav [b.wav ...]
        [--attack-ms 30] [--release-ms 60] [--max-open 0.9] [--gamma 0.6]

For each WAV this writes OUT_DIR/<name>.png (waveform, RMS and mouth curve on one
time axis) and prints the proxy metrics. OUT_DIR/summary.json collects the
parameters, metrics and representative frames (mouth peak / closed / middle),
which tools/render_mouth_frames.sh renders with the three-vrm viewer.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from adria_harness.lipsync import (  # noqa: E402
    LipSyncParams,
    frame_rms,
    mouth_curve,
    normalized_level,
)
from adria_harness.lipsync_eval import (  # noqa: E402
    OPEN_THRESHOLD,
    closed_in_silence,
    flap_rate,
    onset_lags_ms,
    rapid_reversal_rate,
)

TUNABLE = ("attack_ms", "release_ms", "max_open", "gamma", "gate_rms", "gate_level")
PASS = {"max_onset_lag_ms": 50.0, "closed_in_silence": 1.0, "max_flap_rate": 0.5}


def representative_frames(mouth: np.ndarray, fps: int) -> dict[str, dict]:
    peak = int(np.argmax(mouth))
    closed = np.flatnonzero(mouth == 0.0)
    target_mid = mouth[peak] / 2
    mid = int(np.argmin(np.abs(mouth - target_mid) + (mouth == 0.0) * 10))
    frames = {"peak": peak, "middle": mid}
    if len(closed):
        frames["closed"] = int(closed[len(closed) // 2])
    return {k: {"time_sec": i / fps, "mouth": float(mouth[i])} for k, i in frames.items()}


def check(path: Path, out_dir: Path, params: LipSyncParams) -> dict:
    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = audio[:, 0]
    rms = frame_rms(audio, sr, params)
    mouth = np.array(mouth_curve(audio, sr, params).values)
    lags = onset_lags_ms(rms, mouth, params)
    metrics = {
        "onsets": len(lags),
        "median_onset_lag_ms": float(np.median(lags)) if lags else None,
        "max_onset_lag_ms": float(max(lags)) if lags else None,
        "closed_in_silence": closed_in_silence(rms, mouth, params),
        "flap_rate_per_sec": flap_rate(normalized_level(rms, params), mouth, params),
        # Fast moves that follow a large change in the sound; reference only.
        "rapid_reversals_per_sec": rapid_reversal_rate(mouth, params),
    }
    metrics["pass"] = bool(
        (metrics["max_onset_lag_ms"] or 0) <= PASS["max_onset_lag_ms"]
        and metrics["closed_in_silence"] >= PASS["closed_in_silence"]
        and metrics["flap_rate_per_sec"] <= PASS["max_flap_rate"]
    )
    frames = representative_frames(mouth, params.fps)

    t_audio = np.arange(len(audio)) / sr
    t_frames = np.arange(len(mouth)) / params.fps
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(t_audio, audio / (np.abs(audio).max() or 1), color="0.8", lw=0.5, label="waveform")
    ax.plot(t_frames, rms / (rms.max() or 1), color="tab:blue", lw=1, label="RMS (normalized)")
    ax.plot(t_frames, mouth, color="tab:red", lw=1.6, label="mouth open")
    ax.axhline(OPEN_THRESHOLD, color="tab:red", ls=":", lw=0.8)
    for name, f in frames.items():
        ax.axvline(f["time_sec"], color="k", ls="--", lw=0.6)
        ax.text(f["time_sec"], 1.02, name, fontsize=8, ha="center")
    ax.set_xlabel("seconds")
    ax.set_ylim(-1.05, 1.1)
    ax.set_title(f"{path.name}  lag max {metrics['max_onset_lag_ms']} ms  "
                 f"closed {metrics['closed_in_silence']:.2f}  "
                 f"flaps {metrics['flap_rate_per_sec']:.2f}/s")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / f"{path.stem}.png", dpi=110)
    plt.close(fig)
    return {"file": path.name, "metrics": metrics, "frames": frames}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("wavs", type=Path, nargs="+")
    defaults = LipSyncParams()
    for field in TUNABLE:
        flag = f"--{field.replace('_', '-')}"
        ap.add_argument(flag, type=float, default=getattr(defaults, field))
    args = ap.parse_args()
    params = dataclasses.replace(defaults, **{f: getattr(args, f) for f in TUNABLE})
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = [check(p, args.out_dir, params) for p in args.wavs]
    for r in results:
        m = r["metrics"]
        print(f"{r['file']}: onsets={m['onsets']} lag median={m['median_onset_lag_ms']}ms "
              f"max={m['max_onset_lag_ms']}ms closed={m['closed_in_silence']:.2f} "
              f"flaps={m['flap_rate_per_sec']:.2f}/s (rapid {m['rapid_reversals_per_sec']:.2f}/s) "
              f"-> {'PASS' if m['pass'] else 'FAIL'}")
    summary = {"params": dataclasses.asdict(params), "criteria": PASS, "results": results}
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
