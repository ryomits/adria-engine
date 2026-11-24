# adria-engine

Mac 上で完全ローカルに動く、子ども向けのお話し相手キャラクター「ADRIA」の仕組み部分。

マイク → 音声認識（Whisper / MLX）→ ローカル LLM（Ollama）→ 音声合成（Irodori-TTS）→ 再生

- `harness/` 対話管理、STT・TTS・LLM の配管
- `app/` 表示アプリ（未実装）
- `persona-templates/` 設定・ペルソナの書式とダミーのサンプル
- `scripts/` セットアップ・起動・停止
- `docs/` セットアップ手順（`setup.md`）、実測記録（`measurements.md`）

個人の中身（ペルソナ、設定、参照音声）はこのリポジトリに置かず、非公開の `adria-home` を `ADRIA_HOME` で指定して読み込む。
