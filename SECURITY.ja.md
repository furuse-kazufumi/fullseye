# セキュリティポリシー

**言語:** [English](SECURITY.md) · [日本語](SECURITY.ja.md)

## サポート対象の版

セキュリティ修正は、PyPIで公開している最新のマイナーリリース系列だけに提供します。古い系列を使っている場合は、セキュリティ修正を依頼する前に更新してください。

## 脆弱性の報告方法

GitHubのPrivate vulnerability reportingを使ってください。リポジトリの**Security**タブから**Report a vulnerability**を選ぶか、[非公開のアドバイザリーフォーム](https://github.com/furuse-kazufumi/fullseye/security/advisories/new)を開きます。

脆弱性の詳細を公開Issueに書かないでください。非公開報告のボタンが使えない場合は、非公開の連絡手段を求めることだけを書いた公開Issueを作成してください。そのIssueには、技術的な詳細、再現手順、ログ、攻撃用データを含めないでください。

報告には次の情報を含めてください。

- 影響を受けるFullseyeの版
- OSとPythonの版
- Python API、CLI、MCPサーバー、Studioなど、影響を受ける入口
- 最小の再現手順
- 想定するセキュリティ上の影響

## 対応目標

以下は最善を尽くすための目標であり、保証ではありません。Fullseyeは、余暇で保守している小規模なプロジェクトです。

- 7日以内に受領を連絡します。
- 14日以内に初期評価を行います。
- 確認できた問題は、90日以内を目標に修正または緩和策の計画を示します。
- GitHub Security Advisoryを使って、公開時期を調整します。

## 対象範囲

このリポジトリが保つ次のセキュリティ境界を対象とします。

- `python -m fullseye.mcp`で起動するMCPサーバー
- デスクトップGUIのFullseye Studio
- 画像・ラスター、ボリューム・医用画像、メッシュ・点群の読み込み、およびXML、JSON、パイプライン、定義ファイルを読むコード

たとえば、細工した入力ファイルによるコード実行やパストラバーサル、パーサーによる無制限なメモリ・CPU消費、MCP要求による文書化済みのパス・プロセス・ネットワーク・時間・メモリ・出力制限からの逸脱が該当します。

## 対象外

- 利用者が自分で書いて実行するPythonコードは、Fullseyeのセキュリティ境界の外です。Studioから実行するPythonも含みます(Python Editorはサブプロセスで、Program欄がPythonを実行する時はStudioのプロセスの中で実行します)。このコードは利用者自身の権限で動きます。ただし、利用者が求めていないのにコードが実行される場合(ファイルやプロジェクトを開いただけで実行される、Studioが求める確認を経ずに実行される、など)は対象です。
- optionalな第三者依存パッケージ自体の脆弱性は、そのパッケージの上流へ報告してください。ただし、Fullseyeが宣言する下限によって既知の脆弱性がある版を導入できる場合は、Fullseyeにも報告してください。
- セキュリティ上の影響がなく、数値結果が誤っているだけの問題は、[通常のバグトラッカー](https://github.com/furuse-kazufumi/fullseye/issues)へ報告してください。

## 関連文書

- [MCPサーバーの境界、資源上限、fail-closedの動作](docs/MCP.md)
- [対応ファイル形式の棚卸し](docs/FILE_FORMATS.md)
- [堅牢化で見つけた問題と再発防止の門](docs/HARDENING.md)
- [依存関係監査のallowlist](docs/security/pip_audit_allowlist.json)
- [CycloneDX SBOM](docs/sbom/fullseye.cdx.json)。`py -3.11 tools/gen_sbom.py`で再生成します。
