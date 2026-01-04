# AIDX MCP Server

AIDXプロトコルを使用してCAD（Fusion 360 / AutoCAD）と通信するMCPサーバーです。Claude DesktopなどのMCPクライアントから使用できます。

## 機能

- **screenshot**: CADビューポートのスクリーンショット取得
- **import_file**: STEP等の外部ファイルをCADにインポート
- **get_objects**: CAD内のオブジェクト情報を取得
- **modify**: 既存オブジェクトの変形・移動

## 前提条件

- Python 3.10以上
- Fusion 360またはAutoCADのAIDXアドインが起動していること

## セットアップ

### 1. 仮想環境の作成

```bash
cd client/mcp-server
python -m venv venv
```

### 2. 仮想環境の有効化

**Windows**:
```bash
venv\Scripts\activate
```

**macOS/Linux**:
```bash
source venv/bin/activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

必要なパッケージ:
- `mcp>=0.1.0`: Anthropic公式MCPサーバーSDK
- `pydantic>=2.0.0`: データバリデーション

## 使用方法

### スタンドアロン実行

```bash
cd src
python main.py
```

起動時のログ:
```
Connecting to fusion360 at 127.0.0.1:8109... (attempt 1/10)
Successfully connected to fusion360!
```

### Claude Desktopとの統合

Claude Desktopの設定ファイル（`claude_desktop_config.json`）に以下を追加:

**Windows**:
```json
{
  "mcpServers": {
    "aidx-fusion360": {
      "command": "C:\\Users\\YourName\\github\\aidx-mcp\\client\\mcp-server\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\YourName\\github\\aidx-mcp\\client\\mcp-server\\src\\main.py"],
      "env": {
        "AIDX_CAD_TYPE": "fusion360",
        "AIDX_PORT": "8109"
      }
    }
  }
}
```

**macOS/Linux**:
```json
{
  "mcpServers": {
    "aidx-fusion360": {
      "command": "/Users/yourname/github/aidx-mcp/client/mcp-server/venv/bin/python",
      "args": ["/Users/yourname/github/aidx-mcp/client/mcp-server/src/main.py"],
      "env": {
        "AIDX_CAD_TYPE": "fusion360",
        "AIDX_PORT": "8109"
      }
    }
  }
}
```

**設定ファイルの場所**:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### AutoCAD用の設定

AutoCADを使用する場合は、`AIDX_CAD_TYPE`と`AIDX_PORT`を変更:

```json
{
  "mcpServers": {
    "aidx-autocad": {
      "command": "...",
      "args": ["..."],
      "env": {
        "AIDX_CAD_TYPE": "autocad",
        "AIDX_PORT": "8110"
      }
    }
  }
}
```

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `AIDX_CAD_TYPE` | `fusion360` | 接続先CAD (`fusion360` または `autocad`) |
| `AIDX_PORT` | `8109` (Fusion 360)<br>`8110` (AutoCAD) | TCPポート番号 |

## MCPツール仕様

### screenshot

CADビューポートのスクリーンショットを取得します。

**入力**: なし

**出力**: PNG画像（base64エンコード）

**使用例（Claude）**:
```
現在のCADビューポートのスクリーンショットを撮影してください
```

---

### import_file

STEP等の外部ファイルをCADにインポートします。

**入力**:
```json
{
  "path": "ファイルパス",
  "pos": [x, y, z],  // 配置座標 (mm) - オプション
  "rot": [rx, ry, rz]  // 回転角度 (度) - オプション
}
```

**出力**:
```json
{
  "success": true,
  "id": "オブジェクトID"
}
```

**使用例（Claude）**:
```
/path/to/part.stepファイルを座標(100, 200, 50)にインポートしてください
```

---

### get_objects

CAD内のオブジェクト情報を取得します。

**入力**:
```json
{
  "filter": {}  // フィルタ条件（CAD依存、オプション）
}
```

**出力** (Fusion 360):
```json
{
  "objects": [
    {
      "type": "BRepBody",
      "id": "...",
      "name": "Body1",
      "isVisible": true,
      "isSolid": true,
      "volume_mm3": 250000.0,
      "mass_kg": 2.0,
      "material": "Steel",
      "boundingBox": {
        "min": [0, 0, 0],
        "max": [100, 100, 100]
      }
    }
  ]
}
```

**注意**: レスポンス形式はCADによって異なります。AutoCADでは`layer`や`color`などのプロパティが含まれます。

**使用例（Claude）**:
```
CAD内の全オブジェクトの情報を取得してください
```

---

### modify

既存オブジェクトの変形・移動を行います。

**入力**:
```json
{
  "id": "オブジェクトID",
  "matrix": [m11, m12, m13, m14, m21, m22, m23, m24, ...]  // 4x4変換行列（16要素）
}
```

**出力**:
```json
{
  "success": true
}
```

**使用例（Claude）**:
```
オブジェクトID "xyz123" を(50, 0, 0)に移動してください
```

## トラブルシューティング

### 接続エラー

```
ERROR: Failed to connect to fusion360 at 127.0.0.1:8109.
Please ensure the CAD addin is running.
```

**原因**: CADアドインが起動していない

**解決策**:
1. Fusion 360/AutoCADを起動
2. アドインマネージャーでAIDXアドインを実行
3. "AIDX Addin started. X commands loaded." のメッセージを確認
4. MCPサーバーを再起動

---

### ポート番号エラー

```
Connection failed: [WinError 10061] ...
```

**原因**: ポート番号が間違っている

**解決策**:

環境変数を確認:
- Fusion 360: `AIDX_PORT=8109`
- AutoCAD: `AIDX_PORT=8110`

ポートが使用中の場合、別のポートに変更:
```bash
# Windows
set AIDX_PORT=8120
python src/main.py

# macOS/Linux
export AIDX_PORT=8120
python src/main.py
```

---

### Claude Desktopで認識されない

**原因**: 設定ファイルのパスが間違っている

**解決策**:

1. 絶対パスを使用:
   ```json
   "command": "C:\\Users\\YourName\\..."  // 相対パスは使用不可
   ```

2. バックスラッシュをエスケープ（Windows）:
   ```json
   "C:\\Users\\..."  // 正しい
   "C:\Users\..."    // 間違い
   ```

3. Claude Desktopを再起動

4. ログを確認:
   - **Windows**: `%APPDATA%\Claude\logs\`
   - **macOS**: `~/Library/Logs/Claude/`

---

### ツール実行時のエラー

```
Error: Not connected to CAD. Please ensure Fusion 360/AutoCAD addin is running.
```

**原因**: MCPサーバー起動後にCADアドインが停止した

**解決策**:
1. CADアドインを再起動
2. MCPサーバーを再起動（Claude Desktopの場合はClaude Desktopを再起動）

---

### プロトコルエラー

```
AIDX Protocol Error (Code 0x1001): Unknown command: 0x0500
```

**原因**: CADアドインに実装されていないコマンドIDが使用された

**解決策**:
- 標準コマンド（0x0100, 0x0200, 0x0300, 0x0400）のみ使用
- カスタムコマンドを使用する場合は、CADアドイン側に実装が必要

---

## 開発

### デバッグ実行

VSCodeで `.vscode/launch.json` の設定を使用:

```json
{
  "name": "AIDX MCP Server (venv)",
  "type": "python",
  "request": "launch",
  "module": "main",
  "cwd": "${workspaceFolder}/client/mcp-server/src",
  "python": "${workspaceFolder}/client/mcp-server/venv/Scripts/python.exe",
  "env": {
    "AIDX_CAD_TYPE": "fusion360",
    "AIDX_PORT": "8109"
  },
  "console": "integratedTerminal"
}
```

### プロトコルテスト

MCPサーバーを介さずにプロトコルをテストする場合は、テストクライアントを使用:

```bash
cd ../test-client/src
python test_protocol.py
```

詳細は[test-client/README.md](../test-client/README.md)を参照。

---

## 技術仕様

### アーキテクチャ

```
Claude Desktop
    ↕ stdio (JSON-RPC 2.0)
MCP Server (Python)
    ↕ TCP/IP (AIDX Protocol - バイナリ)
CAD Addin (Fusion 360 / AutoCAD)
```

### プロトコル

- **Magic**: `0x41494458` (AIDX)
- **Port**: `8109` (Fusion 360) / `8110` (AutoCAD)
- **Endian**: Little Endian
- **Chunking**: 64KB単位（自動分割送受信）

### 分割送受信

64KBを超えるデータは自動的に分割送受信されます:

- **送信**: リクエストペイロードが64KB超過時、プロトコル層が自動分割
- **受信**: レスポンスが複数チャンクの場合、自動で再構築
- **透過性**: ツール実装者は分割処理を意識する必要なし

### エラーハンドリング

すべてのエラーはMCP標準フォーマットで返却:

```json
{
  "content": [{
    "type": "text",
    "text": "エラーメッセージ"
  }],
  "isError": true
}
```

### 接続リトライ

CAD起動待ちのため、接続リトライ機能を実装:

- **最大試行回数**: 10回
- **リトライ間隔**: 3秒
- **タイムアウト**: 各チャンク受信30秒

---

## ライセンス

TBD

## 関連ドキュメント

- [../../DESIGN.md](../../DESIGN.md): 詳細設計仕様書
- [../../README.md](../../README.md): プロジェクト概要
- [../test-client/README.md](../test-client/README.md): テストクライアント
- [../../addins/fusion360/README.md](../../addins/fusion360/README.md): Fusion 360アドイン
