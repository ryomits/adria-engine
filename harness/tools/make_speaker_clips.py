"""Synthesize test speakers with Irodori-TTS for checking speaker identification.

Usage:
    uv run python tools/make_speaker_clips.py OUT_DIR

Each speaker is a voice-design caption. A short caption-only line is saved as
that speaker's reference voice, and every clip is then synthesized from that
reference, so all clips of one speaker share a timbre (like one person).
Writes OUT_DIR/<speaker>_enroll_<n>.wav and OUT_DIR/<speaker>_test_<n>.wav.
Synthetic voices only approximate real family members; see docs/speakers.md.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adria_harness.config import load_config  # noqa: E402
from adria_harness.tts import IrodoriTTS  # noqa: E402

SPEAKERS = {
    # Enrolled family members (stand-ins)
    "papa": "落ち着いた低い声の30代の男性。ゆっくり話す。",
    "mama": "やわらかく明るい声の30代の女性。",
    "kid": "4歳くらいの幼い女の子の声。舌足らずで元気な話し方。",
    # Never enrolled: must fall back to the child persona
    "aunt": "やさしい声の40代の女性。",
    "news": "ニュースを読む男性アナウンサー。はっきりした話し方。",
    "anime": "アニメの元気な少女キャラクターの声。高い声。",
    "grandpa": "しわがれた声の70代の男性。",
}

ENROLL = [
    "きょうは、いいてんきですね。",
    "あさごはんに、パンとたまごをたべました。",
    "こうえんまで、あるいて十分くらいです。",
    "あしたは、あめがふるかもしれません。",
    "でんしゃにのって、おでかけしました。",
    "このほんは、とてもおもしろかったです。",
    "よるは、はやめにねようとおもいます。",
]

TEST = [
    "ねえ、きいてきいて。",
    "おなかすいたなあ、なにたべようかな。",
    "さっき、ねこがまどのそとにいたよ。",
    "きょうのよるごはんは、カレーがいいな。",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--speakers", nargs="*", default=list(SPEAKERS))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    voices = args.out / "voices"
    voices.mkdir(exist_ok=True)
    cfg = load_config()
    tts_cfg = dataclasses.replace(cfg.tts, seed=args.seed, voice="none")
    tts = IrodoriTTS(tts_cfg, voices, args.out)
    try:
        for name in args.speakers:
            caption = SPEAKERS[name]
            ref = tts.synthesize("こんにちは。きょうは、なにをしてあそびましょうか。",
                                 voice="none", caption=caption)
            (voices / f"test-{name}.wav").write_bytes(ref)
            for kind, lines in (("enroll", ENROLL), ("test", TEST)):
                for i, text in enumerate(lines):
                    wav = tts.synthesize(text, voice=f"test-{name}", caption=caption)
                    (args.out / f"{name}_{kind}_{i}.wav").write_bytes(wav)
            print(f"{name}: done")
    finally:
        tts.shutdown()


if __name__ == "__main__":
    main()
