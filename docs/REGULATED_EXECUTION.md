# 規制実行記録の保証境界 / Regulated execution-record assurance boundary

`ValidationProfile` と `AuditSink` は、CPU・BLAS スレッド数・入力／出力ハッシュ・実行環境・ソフトウェア provenance を固定し、成功、失敗、取消を canonical JSONL の hash chain として保存します。規制実行は、git の source provenance または検証済み wheel `RECORD` を取得できず、BLAS の上限を実際に適用できず、あるいは耐久化 `AuditSink` へ追記できない場合、出力を返さず失敗します。

`ValidationProfile` and `AuditSink` fix CPU execution, BLAS threads, input/output hashes, execution environment, and software provenance, then save success, failure, and cancellation as a canonical-JSONL hash chain. A regulated execution fails without returning an output if it cannot obtain git-source provenance or a verified wheel `RECORD`, actually apply the BLAS ceiling, or append to the durable `AuditSink`.

## 限界 / Limitations

この hash chain とローカル `fsync` だけでは、監査証跡の真正性を保証しません。攻撃者が監査ログと同じ書込み可能な場所にある checkpoint を置換できる場合、連鎖と checkpoint を再生成できます。規制証跡としての真正性には、checkpoint の独立保管に加え、次段で導入する電子署名、WORM 保管、または外部 attestation が必要です。

The hash chain and local `fsync` alone do not establish audit-trail authenticity. An attacker able to replace a log and its co-located checkpoint can regenerate both the chain and checkpoint. Regulatory-trail authenticity requires independently retained checkpoints together with the next-stage control: electronic signatures, WORM storage, or external attestation.

## 検証環境の限界 / Verification-environment limits

2026-11-24 のローカル Python 3.11 環境では、`py -3.11 -m pytest --collect-only -q -p no:cacheprovider` が 29,910 件を収集した後、`tests/test_fileio_scientific.py` の収集中に停止しました。ローカルの Astropy が `numpy.lib.array_utils` を import しようとしましたが、その NumPy 環境には同モジュールがありませんでした。この依存関係の不整合があるため、このローカル環境では全 pytest の合格を確認していません。CI selector は always-run 一覧から `tests/test_execution_record.py` と `tests/test_fsthreads.py` を常に test matrix へ含め、full run は全件を確認します。

In the local Python 3.11 environment on 2026-11-24, `py -3.11 -m pytest --collect-only -q -p no:cacheprovider` collected 29,910 tests and then stopped while collecting `tests/test_fileio_scientific.py`. The local Astropy installation tried to import `numpy.lib.array_utils`, which was absent from that NumPy environment. Because of this dependency mismatch, a passing full pytest run has not been established locally. The CI selector always includes `tests/test_execution_record.py` and `tests/test_fsthreads.py` in the test matrix through its always-run list; full runs check the whole suite.

制御文字検査の `scan_ctrl.py` はリポジトリ外の読み取り専用ツールであり、リポジトリへ取り込まず、CI からも実行しません。そのため、変更差分に対する同ツールのローカル実行と結果の記録が必要です。

The control-character checker `scan_ctrl.py` is a read-only tool kept outside this repository. It is neither vendored nor run by CI, so the changed diff must be checked locally with that tool and the result recorded.
