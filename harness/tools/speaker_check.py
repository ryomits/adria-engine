"""Check speaker identification on a set of clips and sweep the decision threshold.

Usage:
    uv run python tools/speaker_check.py CLIP_DIR --enrolled papa mama kid \\
        [--map papa=parent mama=parent kid=child] [--default child]

CLIP_DIR holds <speaker>_enroll_<n>.wav and <speaker>_test_<n>.wav (for example
from tools/make_speaker_clips.py). Enrolled speakers are registered from their
enroll clips; every test clip is then identified. Speakers that are not
enrolled play the role of the TV or a visitor.

Reported per threshold:
- correct: enrolled speakers recognized as themselves
- unsafe: clips that would get a persona other than the default although they
  should not (a stranger or the TV routed to a parent persona, or an enrolled
  speaker routed to someone else's persona). This must be zero.
- fail-safe misses: clips that should get a non-default persona but fall back
  to the default. Acceptable (the speaker just talks to the child persona).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adria_harness.main import read_wav_16k  # noqa: E402
from adria_harness.speaker import (  # noqa: E402
    EcapaEmbedder,
    enroll_voiceprint,
    match_voiceprint,
    persona_for,
)

CLIP_RE = re.compile(r"^(?P<speaker>[a-z0-9_-]+?)_(?P<kind>enroll|test)_\d+\.wav$")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", type=Path)
    ap.add_argument("--enrolled", nargs="+", required=True)
    ap.add_argument("--map", nargs="*", default=[], help="speaker=persona")
    ap.add_argument("--default", default="child")
    ap.add_argument("--margin", type=float, default=0.1)
    ap.add_argument("--model-dir", type=Path, default=Path.home() / ".cache" / "adria-ecapa")
    args = ap.parse_args()
    mapping = dict(m.split("=", 1) for m in args.map)

    clips: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for path in sorted(args.clips.glob("*.wav")):
        m = CLIP_RE.match(path.name)
        if m:
            clips[m["speaker"]][m["kind"]].append(path)

    embed = EcapaEmbedder(args.model_dir)
    prints = {}
    for name in args.enrolled:
        segments = [read_wav_16k(p) for p in clips[name]["enroll"]]
        prints[name] = enroll_voiceprint(segments, embed, min_total_sec=5)
        print(f"enrolled {name}: {sum(len(s) for s in segments) / 16000:.1f}s")

    names = sorted(prints)
    print("\nvoiceprint similarity between enrolled speakers")
    for a in names:
        print(f"  {a:8s} " + " ".join(f"{float(np.dot(prints[a], prints[b])):6.2f}"
                                       for b in names))

    tests = []  # (true speaker, embedding)
    for speaker, kinds in sorted(clips.items()):
        for p in kinds["test"]:
            tests.append((speaker, p.name, embed(read_wav_16k(p))))

    print("\nscores of test clips (best enrolled match)")
    for speaker, name, e in tests:
        scores = {n: float(np.dot(e, prints[n])) for n in names}
        best = max(scores, key=scores.get)
        role = "enrolled" if speaker in prints else "stranger"
        print(f"  {name:22s} {role:8s} " + " ".join(f"{n}={s:.2f}" for n, s in scores.items())
              + f"  -> {best}")

    print(f"\nthreshold sweep (margin {args.margin})")
    print("  threshold  correct  unsafe  fail-safe misses")
    for threshold in np.arange(0.30, 0.81, 0.05):
        correct = unsafe = misses = enrolled = 0
        for speaker, _, e in tests:
            match = match_voiceprint(e, prints, threshold, args.margin)
            want = persona_for_speaker(speaker, prints, mapping, args.default)
            got = persona_for(match, mapping, args.default)
            if speaker in prints:
                enrolled += 1
                correct += match.speaker == speaker
            if got != want:
                if got == args.default:
                    misses += 1
                else:
                    unsafe += 1
        print(f"  {threshold:9.2f}  {correct:3d}/{enrolled:<3d}  {unsafe:6d}  {misses:16d}")


def persona_for_speaker(speaker, prints, mapping, default):
    return mapping.get(speaker, default) if speaker in prints else default


if __name__ == "__main__":
    main()
