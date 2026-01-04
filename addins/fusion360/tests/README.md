# AIDX Fusion360 Tests

Fusion360アドイン用の統合テストスクリプト集です。

## 前提条件

- Fusion360が起動していること
- AIDXアドインが実行中であること
- Pythonクライアント環境がセットアップされていること

## テストファイル

| ファイル | 説明 | コマンドID |
|---------|------|-----------|
| [test_ping.py](test_ping.py) | 接続確認テスト | 0x0001 |
| [test_screenshot.py](test_screenshot.py) | スクリーンショット取得テスト | 0x0100 |
| [test_get_objects.py](test_get_objects.py) | オブジェクト一覧取得テスト | 0x0300 |
| [test_create_delete.py](test_create_delete.py) | オブジェクト作成・削除統合テスト | 0x0500, 0x0600 |
| [test_torus_simple.py](test_torus_simple.py) | Torusパラメータバリエーションテスト | 0x0500 |
| [test_all_commands.py](test_all_commands.py) | 全コマンド統合テスト | 全コマンド |

## 実行方法

### 個別テスト実行

リポジトリルートから:

```bash
python addins/fusion360/tests/test_ping.py
```

### 全コマンドテスト実行

```bash
python addins/fusion360/tests/test_all_commands.py
```

期待される出力:
```
============================================================
AIDX All Commands Test
============================================================

Connecting to Fusion360...
✓ Connected

============================================================
[1] Ping Test
============================================================
✓ Success (0.026s)

============================================================
[2] Screenshot Test
============================================================
✓ Success (0.195s)
  Size: 139,623 bytes
  Chunks: 3

...

Success Rate: 5/5 (100.0%)
```

### CreateObject & DeleteObject統合テスト

```bash
python addins/fusion360/tests/test_create_delete.py
```

このテストでは以下を実行します:
1. Box, Cylinder, Sphere, Torusの作成
2. GetObjectsで作成確認
3. 全オブジェクトの削除
4. GetObjectsで削除確認

## トラブルシューティング

### 接続エラー

```
ConnectionRefusedError: [WinError 10061]
```

**原因**: Fusion360のAIDXアドインが起動していない

**対処**:
1. Fusion360を起動
2. ユーティリティ > アドイン > AIDX > 実行

### タイムアウトエラー

```
TimeoutError: recv timeout
```

**原因**: コマンド実行に時間がかかりすぎている

**対処**:
- Fusion360で重い処理をしていないか確認
- `config.py`の`RECV_TIMEOUT`を増やす

### プロトコルエラー

```
AIDXProtocolError: 0x1000 - Parse error
```

**原因**: リクエストペイロードが不正

**対処**:
- テストコードのJSONペイロードを確認
- DESIGN.mdのプロトコル仕様を参照

## 開発者向け

### 新しいテストの追加

1. `test_*.py`という名前でファイル作成
2. `AIDXClient`を使用して接続・コマンド送信
3. レスポンスを検証
4. このREADMEに追加

テンプレート:

```python
"""AIDX [コマンド名] テスト"""
import asyncio
import sys
import os
from pathlib import Path

# Windowsコンソールでの文字化け防止
if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "client" / "mcp-server" / "src"))

from protocol import AIDXClient
from config import CMD_YOUR_COMMAND


async def test_your_command():
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        await client.connect()
        # テストロジック
        await client.close()
    except Exception as e:
        print(f"Error: {e}")
        await client.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_your_command())
```
