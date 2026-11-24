# セットアップと起動

すべての推論（LLM・音声合成・音声認識）は Mac の中だけで行う。ネットワークを使うのは初回のセットアップ（依存とモデルの取得）だけ。

## 前提

- Apple Silicon の Mac（メモリ 48GB 以上を推奨）
- [uv](https://docs.astral.sh/uv/)、[Ollama](https://ollama.com/)（`brew install uv ollama`）
- 2 つのリポジトリを並べて配置する

```
<任意の場所>/
  adria-engine/   公開：仕組み（このリポジトリ）
  adria-home/     非公開：ペルソナ・設定・参照音声
```

`adria-home` を別の場所に置く場合は、環境変数 `ADRIA_HOME` でその場所を指定する。

## 1. 非公開側の用意

```bash
cp adria-engine/persona-templates/config.example.toml adria-home/config.toml
cp adria-engine/persona-templates/child.example.md adria-home/personas/child.md
```

`config.toml` の `[tts] server_dir` に、Irodori-TTS-Server を置いた場所を書く。

```bash
git clone https://github.com/Aratako/Irodori-TTS-Server.git <好きな場所>
```

## 2. 依存とモデルの取得（ネットワークを使う唯一の手順）

```bash
adria-engine/scripts/setup.sh
```

取得するもの： LLM（Ollama）、Whisper（MLX）、Irodori-TTS とコーデック。初回の TTS 取得には十数分かかることがある。

## 3. 声の固定（任意だが推奨）

キャプションだけで声を作ると、行ごとに声色が揺れる。参照音声を 1 本作って固定する。

```bash
source adria-engine/scripts/_env.sh
adria make-voice adria   # adria-home/voices/adria.wav を作る（Git には入らない）
```

`config.toml` の `[tts] voice = "adria"` にする。

## 4. 起動と停止

- 起動： `scripts/start.command` を Finder でダブルクリック（または `scripts/start.sh`）
  - 初回だけ、ターミナルへのマイク使用許可のダイアログが出る
- 停止： ターミナルで Ctrl-C。または `scripts/stop.sh`（TTS サーバも止め、LLM もアンロードする）

## 動作確認用コマンド

```bash
source adria-engine/scripts/_env.sh
adria chat                 # 文字で話しかけ、返事は音声
adria say "こんにちは。"     # 1 行だけ読み上げる
adria e2e a.wav b.wav      # WAV を発話とみなして全経路を通し、遅延を表示（--mute で無音）
```

## ファイル連携（表示アプリとの境界）

実行時のファイルは `ADRIA_HOME/runtime/` に置かれる（Git 管理外）。

| ファイル | 内容 |
|---|---|
| `queue.jsonl` | 再生キュー。1 行 1 JSON。書き込みは `.part` に書いてからリネームする |
| `now_playing` | 再生中の行（`x_` キー、`audio_path`、`started_at`、`duration` を含む）、または `{"playing": false}` |
| `state` | `idle` / `listening` / `thinking` / `speaking` |
| `audio/current.wav` | 再生中の音声（口パク解析用） |
| `metrics.jsonl` | 遅延計測。タイムスタンプのみで、会話本文は含まない |

対話 JSON の `x_` で始まるキー（表情など）は表示側向けの情報で、TTS には渡さない。
