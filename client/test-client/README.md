# AIDX テストクライアント

AIDXプロトコルの動作確認用テストクライアントです。MCPサーバーを介さずに、CADアドインに直接接続してプロトコルをテストします。

## 前提条件

- Python 3.10以上
- Fusion 360アドインまたはAutoCADアドインが起動していること

## セットアップ

仮想環境は不要です（標準ライブラリのみ使用）。

```bash
cd client/test-client/src
```

## 使用方法

### 基本プロトコルテスト

各コマンド（Screenshot、ImportFile、GetObjects、Modify）の基本動作をテストします。

```bash
python test_protocol.py [host] [port]
```

**引数**:
- `host`: CADアドインのホスト（デフォルト: `127.0.0.1`）
- `port`: CADアドインのポート（デフォルト: `8109`）

**例**:
```bash
# Fusion 360 (デフォルトポート 8109)
python test_protocol.py

# AutoCAD (ポート 8110)
python test_protocol.py 127.0.0.1 8110
```

**出力例**:
```
============================================================
AIDX Protocol Test Client
============================================================
✓ Connected to 127.0.0.1:8109

[Test 1] Screenshot
  → Sent: CommandID=0x0100, Seq=0, PayloadSize=0
  ← Recv: CommandID=0x0100, Seq=0, PayloadSize=12345, TotalSize=12345, Flags=0x0000
  ✓ Received 12345 bytes (PNG image)
  ✓ Valid PNG header

[Test 2] ImportFile
  → Sent: CommandID=0x0200, Seq=1, PayloadSize=78
  ← Recv: CommandID=0x0200, Seq=1, PayloadSize=56, TotalSize=56, Flags=0x0000
  Result: {
      "success": false,
      "error": "File not found: /path/to/test.step"
  }
  ✓ Import failed (expected, file doesn't exist)

[Test 3] GetObjects
  → Sent: CommandID=0x0300, Seq=2, PayloadSize=2
  ← Recv: CommandID=0x0300, Seq=2, PayloadSize=456, TotalSize=456, Flags=0x0000
  Found 3 objects
    Object 1: type=BRepBody, name=Body1
    Object 2: type=BRepBody, name=Body2
    Object 3: type=BRepBody, name=Body3
  ✓ GetObjects succeeded

[Test 4] Invalid Command ID
  → Sent: CommandID=0x9999, Seq=3, PayloadSize=0
  ← Recv: CommandID=0xFFFF, Seq=3, PayloadSize=123, TotalSize=123, Flags=0x0000
  ✓ Received expected error: AIDX Error: Code=0x1001, Message=Unknown command: 0x9999

============================================================
All tests completed!
============================================================
✓ Disconnected
```

---

### 分割送受信テスト

64KB超過時の分割送受信機能をテストします。

```bash
python test_chunking.py [host] [port]
```

**引数**:
- `host`: CADアドインのホスト（デフォルト: `127.0.0.1`）
- `port`: CADアドインのポート（デフォルト: `8109`）

**出力例**:
```
============================================================
AIDX Chunking Test Client
============================================================
Chunk Size: 65536 bytes (64KB)

✓ Connected to 127.0.0.1:8109

[Test 1] Small Payload (< 64KB)
  Sending chunked command: CommandID=0x0F00, Seq=0, TotalSize=1024
    → Chunk 1: START, Size=1024, Offset=0
  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): ...

[Test 2] Medium Payload (128KB = 2 chunks)
  Sending chunked command: CommandID=0x0F00, Seq=1, TotalSize=131072
    → Chunk 1: START, Size=65536, Offset=0
    → Chunk 2: END, Size=65536, Offset=65536
  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): ...

[Test 3] Large Payload (320KB = 5 chunks)
  Sending chunked command: CommandID=0x0F00, Seq=2, TotalSize=327680
    → Chunk 1: START, Size=65536, Offset=0
    → Chunk 2: MIDDLE, Size=65536, Offset=65536
    → Chunk 3: MIDDLE, Size=65536, Offset=131072
    → Chunk 4: MIDDLE, Size=65536, Offset=196608
    → Chunk 5: END, Size=65536, Offset=262144
  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): ...

[Test 4] Boundary Payload (exactly 64KB)
  Sending chunked command: CommandID=0x0F00, Seq=3, TotalSize=65536
    → Chunk 1: START, Size=65536, Offset=0
  ⚠ Empty response (may not be implemented in CAD)

============================================================
Chunking tests completed!
Note: Some tests may fail if CMD_TEST_LARGE (0x0F00)
      is not implemented in the CAD addin.
============================================================
✓ Disconnected
```

**注意**: 分割送受信テストは、CADアドイン側で専用のテストコマンド（CommandID `0x0F00`）を実装していない場合、エラーになります。ただし、Screenshotコマンド（`0x0100`）が大きな画像を返す場合、分割受信の動作を確認できます。

---

## テストシナリオ

### test_protocol.py

| テスト | コマンドID | 内容 | 期待結果 |
|--------|-----------|------|---------|
| Screenshot | 0x0100 | スクリーンショット取得 | PNGバイナリ受信 |
| ImportFile | 0x0200 | 存在しないファイルのインポート | エラーレスポンス（ファイル未検出） |
| GetObjects | 0x0300 | オブジェクト一覧取得 | JSONレスポンス |
| Invalid Command | 0x9999 | 無効なコマンドID | エラーレスポンス（0xFFFF） |

### test_chunking.py

| テスト | ペイロードサイズ | チャンク数 | 内容 |
|--------|----------------|-----------|------|
| Small Payload | 1KB | 1（単一パケット） | 小さいデータの送信 |
| Medium Payload | 128KB | 2 | 2チャンクに分割 |
| Large Payload | 320KB | 5 | 5チャンクに分割 |
| Boundary Payload | 64KB（境界） | 1（単一パケット） | 境界サイズの扱い確認 |

---

## トラブルシューティング

### 接続エラー

```
ConnectionRefusedError: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。
```

**原因**: CADアドインが起動していない

**解決策**:
1. Fusion 360/AutoCADを起動
2. アドインマネージャーでAIDXアドインを実行
3. "AIDX Addin started. X commands loaded." のメッセージを確認

---

### ポート番号エラー

```
OSError: [WinError 10061] ...
```

**原因**: ポート番号が間違っている

**解決策**:
- Fusion 360: ポート `8109`（デフォルト）
- AutoCAD: ポート `8110`（環境変数 `AIDX_PORT` で変更可能）

```bash
# AutoCAD用
python test_protocol.py 127.0.0.1 8110
```

---

### 分割受信テストが失敗する

```
✗ Failed: AIDX Error: Code=0x1001, Message=Unknown command: 0x0F00
```

**原因**: テスト用コマンド（0x0F00）がCADアドインに実装されていない

**解決策**: これは正常な動作です。分割受信の実際の動作を確認したい場合は、以下のいずれかを実施:

1. **Screenshotコマンドで確認**: 大きなビューポートでスクリーンショットを取得すると、64KB超過時の分割受信が発生する可能性があります

2. **テスト用コマンドを実装**: CADアドイン側に以下のコマンドを追加（オプション）:
   ```python
   # commands/test_large.py
   class TestLargeCommand(AIDXCommand):
       COMMAND_ID = 0x0F00

       def execute(self, payload: bytes) -> bytes:
           # 受信したデータをそのまま返す（エコーバック）
           return payload
   ```

---

## 技術仕様

### プロトコル定数

- **Magic**: `0x41494458` (AIDX)
- **Chunk Size**: `65536` bytes (64KB)
- **Endian**: Little Endian

### Flags ビットフィールド（bit 0-1: ChunkState）

| 値 | 定数 | 説明 |
|----|------|------|
| 0x0000 | FLAG_SINGLE | 単一パケット |
| 0x0001 | FLAG_START | 分割開始 |
| 0x0002 | FLAG_MIDDLE | 分割中間 |
| 0x0003 | FLAG_END | 分割終了 |

---

## ライセンス

TBD
