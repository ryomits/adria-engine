# Lip sync: method and offline check

## Method

The harness computes a mouth-openness curve once per line (`adria_harness/lipsync.py`) and puts it in `now_playing` (`mouth: {fps, values}`). The display only samples it by elapsed time since `started_at`. The offline tools use the same function, so what is checked offline is what the character does.

1. Short-time RMS: 20 ms window centred on each 10 ms frame (100 fps)
2. Normalize to the line's loud parts (95th percentile, floor 0.02) and clip to 0..1
3. Perceptual curve: `level ** 0.6`
4. Noise gate: RMS < 0.01 or normalized level < 0.1 → 0
5. Attack / release smoothing (separate time constants); once nearly closed in silence, snap to fully closed
6. Clip to the maximum opening

`started_at` includes the output device latency reported by the audio stream, so the mouth starts when the sound is heard. On Bluetooth headphones this was 171 ms. Without it the mouth would lead the sound by that much.

## Parameters

| Parameter | Initial | Tuned | Why |
|---|---|---|---|
| attack_ms | 30 | 30 | |
| release_ms | 80 | **60** | the mouth stayed open into pauses |
| snap_below | 0.02 | **0.05** | same; closing took ~310 ms, now ~170 ms |
| gamma | 0.6 | 0.6 | |
| gate_rms / gate_level | 0.01 / 0.1 | 0.01 / 0.1 | |
| max_open | 0.9 | 0.9 | |

## Proxy metrics and pass criteria

These are proxies. The final judgement of naturalness is made on the Mac by a person.

| Metric | Definition | Pass |
|---|---|---|
| Onset lag | From when a syllable becomes audible (normalized level ≥ 0.3 after a quiet stretch) until the mouth is visibly open (≥ 0.3) | max ≤ 50 ms |
| Closed in silence | Share of silent frames, more than 250 ms after speech, with the mouth fully closed | 1.00 |
| Flapping | Open/close reversals less than 50 ms apart, swing > 0.08, where the sound level changed by less than 0.2 | ≤ 0.5 / s |
| Rapid reversals (reference) | The same fast reversals including ones that follow a large level change (consonants) | — |

The first version of the metrics measured onset lag from the noise gate and counted every fast reversal. That flagged soft consonants that fade in (lag 130 ms from near-silence, although the mouth followed the audible sound) and dips that track real consonants (level 0.85 → 0.32) as failures. The definitions were changed to match the criteria: no visible delay against the audible sound, and no flapping on *small* volume changes.

## Results (2026-11-25, tuned parameters)

Test clips (local only, not in Git). All were synthesized with Irodori-TTS v4-Small, 16 steps:

- `tts_16_0`–`tts_16_3`: the character voice (voice design, seed 42). Texts: こんにちは！ / いちご、おいしいよね。 / きょうは、こうえんで、なにしてあそんだの？ / すべりだいと、ぶらんこ、どっちがすき？
- `u1`–`u6`: a young child's voice (voice design, seed 7, 24 steps): the six user turns of the voice-loop test

| Clip | Onsets | Lag median / max | Closed in silence | Flapping | Rapid reversals | Result |
|---|---|---|---|---|---|---|
| tts_16_0 | 3 | 0 / 0 ms | 1.00 | 0.00 /s | 0.00 /s | pass |
| tts_16_1 | 5 | 0 / 10 ms | 1.00 | 0.00 /s | 0.00 /s | pass |
| tts_16_2 | 8 | 0 / 10 ms | 1.00 | 0.00 /s | 0.00 /s | pass |
| tts_16_3 | 8 | 0 / 10 ms | 1.00 | 0.21 /s | 0.85 /s | pass |
| u1 | 2 | 5 / 10 ms | 1.00 | 0.00 /s | 0.00 /s | pass |
| u2 | 6 | 0 / 0 ms | 1.00 | 0.39 /s | 0.39 /s | pass |
| u3 | 5 | 0 / 20 ms | 1.00 | 0.38 /s | 0.77 /s | pass |
| u4 | 5 | 0 / 10 ms | 1.00 | 0.00 /s | 0.00 /s | pass |
| u5 | 7 | 0 / 0 ms | 1.00 | 0.00 /s | 0.37 /s | pass |
| u6 | 4 | 0 / 10 ms | 1.00 | 0.00 /s | 0.00 /s | pass |

With the initial parameters, closed-in-silence dropped to 0.79. Lag and flapping were unchanged.

The 20 ms RMS window is centred, so the curve may lead the sound by up to 10 ms. This is in line with real speech, where the lips move slightly before the sound.

Representative frames (provisional model, `tts_16_3`): closed (t = 2.75 s, 0.00), middle (1.37 s, 0.45), peak (1.02 s, 0.90). The mouth shape matched each state.

## Running the check

```bash
cd harness
uv run --extra tools python tools/lipsync_check.py OUT a.wav b.wav      # plots, metrics, summary.json
(cd ../app/web && npx vite) &                                           # viewer for the frames
uv run python tools/render_mouth_frames.py OUT/summary.json --vrm avatars/your-model.vrm
```

Parameters can be overridden on the command line (`--attack-ms`, `--release-ms`, `--max-open`, `--gamma`, `--gate-rms`, `--gate-level`). Copy the chosen values into `LipSyncParams` and record them here.

## Remaining for the Mac

- Whether the mouth looks natural with the real voice and model
- Whether the output latency estimate matches perception on each device (speakers vs. Bluetooth)
- The first ≤ 50 ms of each line can be missed (polling interval). The curve is sampled by absolute time, so the mouth catches up within one poll
