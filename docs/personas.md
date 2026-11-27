# Persona and memory

The LLM itself has no persona. For every request the harness reads `ADRIA_HOME/persona.md` and sends it as the system prompt together with the long-term memory. Nothing is baked into an Ollama Modelfile, so editing the file changes the next reply without a restart or rebuild.

There is one persona. Everyone who talks to ADRIA talks to it.

## The persona file: `ADRIA_HOME/persona.md`

A Markdown body (the system prompt) with an optional TOML front matter:

```markdown
+++
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
- The voice is set in `config.toml` (`[tts] voice` and `caption`), not in the persona.
- Dummy sample: `persona-templates/persona.example.md`. The real text (with family names) belongs only in the private repository.

## Sessions

A session is a run of turns. It ends when:

- nobody has spoken for `[conversation] idle_timeout_min` minutes (default 5), or
- the harness exits (quitting the display app, Ctrl-C, `stop.sh`, closing the Terminal window).

Ending a conversation with a click on the character does not end the session: a new click within the timeout continues it with the same short-term history. Short-term history lives only in memory.

## Memory: `ADRIA_HOME/memory/summary.md`

When a session ends, the LLM summarizes it once (never per turn) and the summary is appended to the file. The next request gets the file in its system prompt.

- The summary runs in the background, only while nobody is talking (Ollama handles one request at a time). At exit, pending summaries are saved before the process ends; `stop.sh` waits for that (up to 2 minutes) before unloading the LLM. A crash loses the summary of the current session.
- **Grounding check.** The LLM must return each memo with the user's own words as evidence (`{"items": [{"memo", "evidence"}]}`). Memos whose evidence does not appear in what the *user* said are dropped. Without this, the model filled every requested topic with invented names and games, even for a conversation that was only "bye".
- Above `[memory] max_chars` (default 2000) the file is merged by the LLM into one shorter summary. If the merge is empty or not shorter, the file is kept as is.
- The file is tracked in the private repository. Edit or delete entries freely; the next request reads the file again.

Known limits:

- Speech recognition errors end up in memory as heard (e.g. a friend's name misheard).
- The grounding check stops invented facts but not a wrong paraphrase of a real remark.
- Anyone who speaks during a conversation (a parent, the TV) becomes part of the session and its summary.

## Full transcripts: `ADRIA_HOME/conversation-logs/`

For parents to look back on: one JSON line per turn (time, what was heard, what was replied) in a file per day, owner-only permissions.

- Deleted after `[memory] transcript_retention_days` (7) days, checked at startup, hourly, and on each write.
- Write-only for the harness: no code reads it back, so it cannot reach the LLM. Long-term memory comes only from the summaries.
- Not tracked by Git. No audio is stored anywhere.
