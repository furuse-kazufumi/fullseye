# 規制実行記録の保証境界 / Regulated execution-record assurance boundary

`ValidationProfile` と `AuditSink` は、CPU・BLAS スレッド数・入力／出力ハッシュ・実行環境・ソフトウェア provenance を固定し、成功、失敗、取消を canonical JSONL の hash chain として保存します。規制実行は、git の source provenance または検証済み wheel `RECORD` を取得できず、BLAS の上限を実際に適用できず、あるいは耐久化 `AuditSink` へ追記できない場合、出力を返さず失敗します。

`ValidationProfile` and `AuditSink` fix CPU execution, BLAS threads, input/output hashes, execution environment, and software provenance, then save success, failure, and cancellation as a canonical-JSONL hash chain. A regulated execution fails without returning an output if it cannot obtain git-source provenance or a verified wheel `RECORD`, actually apply the BLAS ceiling, or append to the durable `AuditSink`.

## 限界 / Limitations

この hash chain とローカル `fsync` だけでは、監査証跡の真正性を保証しません。攻撃者が監査ログと同じ書込み可能な場所にある checkpoint を置換できる場合、連鎖と checkpoint を再生成できます。規制証跡としての真正性には、checkpoint の独立保管に加え、次段で導入する電子署名、WORM 保管、または外部 attestation が必要です。

The hash chain and local `fsync` alone do not establish audit-trail authenticity. An attacker able to replace a log and its co-located checkpoint can regenerate both the chain and checkpoint. Regulatory-trail authenticity requires independently retained checkpoints together with the next-stage control: electronic signatures, WORM storage, or external attestation.
