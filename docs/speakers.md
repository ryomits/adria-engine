# Speaker identification

Each utterance is matched against enrolled voiceprints, in parallel with speech recognition, to choose the persona. It is a convenience, **not authentication**: anything uncertain falls back to the child persona.

- Model: SpeechBrain ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`), on the CPU, about 30 ms per utterance. Downloaded by `setup.sh`; offline at runtime.
- Voiceprints: one 192-dimensional unit vector per person in `ADRIA_HOME/voiceprints/<id>.npy` (owner-only, ignored by Git in both repositories). No audio is kept.
- Decision: the best cosine similarity must be at least `threshold` **and** ahead of the second best by `margin`. Utterances shorter than `min_audio_sec` are unknown.
- Routing: `[speakers.map]` maps speaker ids to personas. Unknown, too short, ambiguous, enrolled-but-unmapped: `[personas] default` (the child persona).

## Enrolling

```bash
source scripts/_env.sh
adria enroll papa                  # speak naturally for ~20 s (several sentences)
adria enroll mama
adria enroll kid                   # recommended: the child, too
adria speakers                     # who is enrolled and which persona each gets
```

```toml
# ADRIA_HOME/config.toml
[speakers.map]
papa = "parent"
mama = "parent"
kid = "child"
```

`enroll` prints how consistent the recording was and how close the new voice is to the others. A pair above the threshold will be confused; enroll again in a quieter place, or accept that the pair falls back to the child persona. Enrolling the child too is recommended: the child's voice then clearly matches the child instead of being close to a parent.

`adria enroll NAME --wav a.wav b.wav` enrolls from files; `adria forget NAME` deletes a voiceprint. New enrollments take effect on the next utterance without a restart.

## Re-enrolling (children's voices change)

A child's voice changes as they grow. Re-enroll when the child is often answered by the wrong persona or the scores drop:

1. `adria identify` some recent recordings, or watch the `you (kid 0.xx -> child)` lines in the Terminal. Re-enroll when the child's scores approach the threshold.
2. `adria enroll kid` again (it overwrites the old voiceprint).
3. Check `adria speakers` and the similarity printed by `enroll`.

Rough guide: every 6 months for a preschooler, and whenever a parent notices misrouting.

## Choosing the threshold

The default is set to err towards the child persona. A stranger or the TV routed to a parent persona is the error that must not happen; a parent sometimes answered by the child persona is acceptable.

`tools/speaker_check.py` sweeps the threshold over a set of clips (`<speaker>_enroll_<n>.wav`, `<speaker>_test_<n>.wav`) and reports correct identifications, **unsafe** routings, and fail-safe misses.

### Results with synthetic voices (2026-11-25)

Real family recordings were not available, so seven speakers were synthesized with Irodori-TTS voice design (`tools/make_speaker_clips.py`): papa, mama and kid enrolled (~24 s each); aunt (similar to mama), a news announcer, an anime girl and a grandfather never enrolled. 4 test sentences per speaker, different from the enrollment text.

| Threshold | Correct (of 12) | Unsafe | Fail-safe misses |
|---|---|---|---|
| 0.55 | 12 | 5 | 0 |
| 0.60 | 11 | 1 | 1 |
| 0.65 | 9 | 1 | 2 |
| **0.70** | 9 | **0** | 2 |
| 0.75 | 7 | 0 | 3 |

- Enrolled speakers scored 0.59–0.89 against themselves; cross-scores between them were ≤ 0.38.
- Strangers of the same sex scored high against an enrolled voice: grandfather up to 0.66 and announcer up to 0.60 against papa, aunt up to 0.56 against mama. The anime voice matched kid (0.46–0.78), which routes to the child persona anyway.
- The default `threshold = 0.70`, `margin = 0.1` gave no unsafe routing, with a small safety gap (0.66 vs 0.70).

These are synthetic voices from one TTS model, so the numbers only show the method works. **Calibrate with the real family**: enroll, record a few sentences of each person and of the TV, and run `tools/speaker_check.py` (or `adria identify`). Raise the threshold if any stranger reaches it.
