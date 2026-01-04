# AIDX Fusion 360 アドイン

Fusion 360用のAIDXプロトコルサーバーアドインです。

## インストール

1. `AIDX` フォルダを Fusion 360 のアドインディレクトリにコピー:
   ```
   Windows: %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
   macOS: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
   ```

2. Fusion 360を起動

3. **ユーティリティ** > **アドイン** を選択

4. **アドイン** タブで `AIDX` を選択し、**実行** をクリック

## 使用方法

### アドインの起動

アドインを実行すると、localhost:8109でTCPサーバーが起動します。メッセージボックスに「AIDX Addin started. X commands loaded.」と表示されれば成功です。

### MCPサーバーからの接続

MCPサーバー（`client/mcp-server`）を起動すると、自動的にこのアドインに接続されます。

```bash
cd client/mcp-server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd src
python main.py
```

### 利用可能なコマンド

| コマンドID | 機能 | 説明 |
|-----------|------|------|
| 0x0100 | Screenshot | ビューポートのスクリーンショットをPNG形式で取得 |
| 0x0200 | ImportFile | STEP等のファイルをインポート（位置・回転指定可能） |
| 0x0300 | GetObjects | BRepBodyの情報を取得（体積、質量、バウンディングボックス等） |
| 0x0400 | Modify | Occurrenceの変形・移動（4x4変換行列） |

## 新しいコマンドの追加

プラグイン方式により、メインコードを変更せずにコマンドを追加できます。

### 手順

1. `commands/` ディレクトリに新しいPythonファイルを作成（例: `my_command.py`）

2. `AIDXCommand` を継承したクラスを定義:

```python
from .base import AIDXCommand
import adsk.core

class MyCommand(AIDXCommand):
    COMMAND_ID = 0x0500  # 独自のコマンドID

    def execute(self, payload: bytes) -> bytes:
        # コマンド処理
        # payload: リクエストデータ（完全なバイナリ、分割受信済み）
        # 戻り値: レスポンスデータ（64KB超過時は自動で分割送信）

        return b"response data"
```

3. アドインを再起動

自動的にコマンドが検出・登録されます。

## トラブルシューティング

### アドインが起動しない

- Fusion 360のバージョンが古い可能性があります（Python 3.9以降が必要）
- **ツール** > **スクリプトとアドイン** > **デバッグ** でエラーログを確認

### MCPサーバーと接続できない

- ポート8109が他のプロセスで使用されていないか確認:
  ```bash
  netstat -an | findstr 8109
  ```
- ファイアウォールでポート8109がブロックされていないか確認

### コマンドが登録されない

- `commands/` ディレクトリ内のファイル名が正しいか確認（`.py`拡張子）
- クラスが `AIDXCommand` を継承しているか確認
- `COMMAND_ID` が定義されているか確認
- コマンドIDが他のコマンドと重複していないか確認

## 技術仕様

### 単位系

| プロパティ | AIDX プロトコル | Fusion 360 内部 | 変換 |
|-----------|---------------|---------------|------|
| 位置座標 | mm | cm | `pos_cm = pos_mm / 10` |
| 体積 | mm³ | cm³ | `volume_mm3 = volume_cm3 * 1000` |
| 回転角度 | 度 | ラジアン | `rad = deg * π / 180` |

### プロトコル

詳細は `../../DESIGN.md` を参照してください。

- **Magic**: `0x41494458` (AIDX)
- **Port**: `8109`
- **Endian**: Little Endian
- **Chunking**: 64KB単位（自動分割送受信）

## ライセンス

TBD
