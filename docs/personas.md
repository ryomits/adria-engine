# Personas and memory

The LLM itself has no persona. For every request the harness picks a persona (from the speaker; see [speakers.md](speakers.md)), reads its file, and sends it as the system prompt together with that persona's memory. Nothing is baked into an Ollama Modelfile, so editing a file changes the next reply without a restart or rebuild.

## Persona files: `ADRIA_HOME/personas/<name>.md`

A Markdown body (the system prompt) with an optional TOML front matter for the other layers:

```markdown
+++
[voice]                      # handed to the TTS with every line
reference = "adria"          # voices/adria.wav; "none" = caption only; omitted = [tts] voice
caption = "明るくやさしい声。"   # Irodori voice description; omitted = [tts] caption

[reply]                      # enforced by the harness, not only asked of the LLM
max_sentences = 3
max_chars = 90

[memory]
user_label = "子ども"         # how the other side is named in summaries
focus = ["すきなもの", "保育園の友達の名前", "続いている ごっこ遊び の設定", "約束したこと"]
+++
# あなたについて
...
# 約束ごと
...
# 会話の例
...
```

- Prefer concrete example conversations over abstract descriptions of character.
- The reply limit is enforced while streaming: after `max_sentences` sentences (or before going past `max_chars`, always keeping the first sentence) the harness stops reading and closes the stream, so Ollama stops generating. Only what was spoken goes into the history.
- Names are lowercase letters, digits, `-` and `_`. `[personas] default` in `config.toml` names the fallback persona; it must be the child one.
- Dummy samples: `persona-templates/child.example.md`, `parent.example.md`. Real texts (with family names) belong only in the private repository.

## Sessions

A session is a run of turns with one persona. It ends when:

- another persona is selected (a different speaker),
- nobody has spoken for `[memory] idle_end_sec` (default 5 minutes), or
- the harness exits (Ctrl-C, `stop.sh`, closing the Terminal window).

Short-term history lives only in memory and never crosses personas: a new persona always starts with an empty history.

## Memory: `ADRIA_HOME/memory/<persona>.md`

When a session ends, the LLM summarizes it once (never per turn) and the summary is appended to that persona's file. The next session of the same persona gets the file in its system prompt.

- The summary runs in the background, only while nobody is talking (Ollama handles one request at a time). At exit, pending summaries are saved before the process ends; `stop.sh` waits for that (up to 2 minutes) before unloading the LLM. A crash loses the summary of the current session.
- **Grounding check.** The LLM must return each memo with the user's own words as evidence (`{"items": [{"memo", "evidence"}]}`). Memos whose evidence does not appear in what the *user* said are dropped. Without this, the model filled every requested topic with invented names and games, even for a conversation that was only "bye".
- Above `[memory] max_chars` (default 2000) the file is merged by the LLM into one shorter summary. If the merge is empty or not shorter, the file is kept as is.
- Personas never share memory: the file name is the persona name. Parents' remarks go to `parent.md` and are not visible to the child persona.
- Memory files are tracked in the private repository. Edit or delete entries freely; the next request reads the file again.

Known limits:

- Speech recognition errors end up in memory as heard (e.g. a friend's name misheard).
- The grounding check stops invented facts but not a wrong paraphrase of a real remark.
- An unknown voice (TV, visitor) talks to the child persona, so its words can become part of the child's session and its summary.

## Full transcripts: `ADRIA_HOME/conversation-logs/`

For parents to look back on: one JSON line per turn (time, persona, speaker and score, what was heard, what was replied) in a file per day, owner-only permissions.

- Deleted after `[memory] transcript_retention_days` (7) days, checked at startup, hourly, and on each write.
- Write-only for the harness: no code reads it back, so it cannot reach the LLM. Long-term memory comes only from the summaries.
- Not tracked by Git. No audio is stored anywhere.
