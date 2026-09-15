<!-- copilot の聞き取り(採点対象外)。transcript から最終回答だけを切り出し、ローカル絶対パスは相対に置換。検証済み注記は docs/RAG_EVAL.md -->

- **1. 役立つ場面／役立たない場面**
  - 役立つ: (a) ユーザーが検査画像を渡し「欠陥の有無・寸法」を聞く場合。`image → region → feature` の型連鎖と worked example を検索できる（`docs/ops/INDEX.md:47-52`、`docs/OP_CATALOG.md:5-12`）。
  - 役立つ: (b) ステレオ画像・点群から深度、姿勢、地形、把持候補を組み立てる場合。3-D op 群と実行例がある（`docs/ops/INDEX.md:10-11`）。
  - 役立つ: (c) Claude Code から、未知の op を検索→ノート確認→サンプル実行まで行う場合。MCP は 918 op を 8 tool に集約している（`docs/MCP.md:31-46`）。
  - 使わない: 自然画像の「これは何か」という認識・分類。古典手法で、学習済み検出器・セグメンタは含まれない（`docs/INTEGRATION.md:101-102`）。
  - 使わない: 単純な文字列処理、一般的なコード修正、画像を実際に目視できない環境での最終判定。

- **2. この環境で詰まる点**
  - 私の実行環境は Windows で、利用できる主な操作は `rg`、ファイル閲覧、PowerShell、`gh`。Linux 前提のシェル例はそのまま使えず、`py -3.11`、PowerShell の環境変数構文への読み替えが要る（`docs/MCP.md:17-28`）。
  - 今回、`docs/AI_RAG_GUIDE.md` は約389 KBで一括閲覧が拒否され、部分検索に切り替えた。約1,943枚のノート（`docs/AI_RAG_GUIDE.md:55`）は、毎回多数ファイルを開くとコンテキストと呼び出し回数を圧迫する。
  - PowerShellで行番号抽出を試した際は permission denied になり、実行検証へ進めなかった。MCP登録用の Claude クライアントもこのセッションにはなく、`claude mcp add` は実行確認できない。
  - MCP は wheel だけでは動かず checkout と `docs/OP_INDEX.json` が必要（`docs/MCP.md:12-15`、`docs/INTEGRATION.md:75-76`）。

- **3. 正しさの確認**
  - 可能性はある。ノートの worked example、ground truth、テスト、MCP の stdio 往復テスト、小図確認が用意されている（`docs/MCP.md:89`、`docs/ops/INDEX.md:52`）。
  - ただし現在は実行権限と画像表示経路を確認できず、私自身は例を実行・図を目視できなかった。実行可能な Python 環境、依存関係、画像表示または数値比較の出力が必要。

- **4. 一番使いやすい入口**
  - **MCP**。私の仕事は対話中に検索・説明・実行を連続して行うことなので、8 tool、ハンドル、統計、strict エラーが最も直接的（`docs/MCP.md:41-46、50、68-70`）。ただし登録不能な現環境では、次点は `rg` で引ける op ノート。

- **5. 課題への影響**
  - 軽くなる: 幻覚（ノート、registry fingerprint、ground truth）、長文の読み落とし（family→guide→op の段階検索）、ツール失敗の隠蔽（strict／degraded ledger）。RAG は外部ベクタDB不要（`docs/AI_RAG_GUIDE.md:5-7`）。
  - 悪化する: コンテキスト量と検索コスト（巨大な生コーパス）、環境差（wheel に知識層なし、Windows/Linux差）、古さ（Tier 2 のクラスタは再取込しないと陳腐化、`docs/AI_RAG_GUIDE.md:71`）。また「妥当」と判定されても、物理的な正しさを保証するものではない。

- **6. 推薦**
  - 推薦: 検査・計測、古典画像処理、3-D／ロボティクス、再現可能な実験を行う Python 利用者、または MCP を登録できる Claude 利用者。
  - 非推薦: 学習モデル中心の認識業務、pip install だけで MCP の知識層まで欲しい利用者、GUI・GPU・追加依存を導入できない最小実行環境。

- **7. 作者への要望（1つ）**
  - **op ノートと `OP_INDEX.json` を含む MCP 対応 wheel を提供し、`fullseye.mcp` を checkout なしで起動可能にしてほしい。** 現在の最大の導入障壁である（`docs/MCP.md:12-15`）。
