# AIDX-MCP

**AIDX (AI Design eXchange)** は、CADソフトウェアとAIエージェント（LLM/MCPサーバー）間の通信を最適化するための独自バイナリプロトコルおよびアドインの総称です。

## 概要

従来のJSON-RPC等のテキストベース通信を廃し、バイナリフレームによるストリーム通信を採用することで、大規模な図面データや高解像度画像のリアルタイム転送を可能にします。

```
LLM (Claude)
    ↕ stdio (JSON-RPC 2.0)
MCP Server (Python)
    ↕ TCP/IP (AIDX Protocol - バイナリ)
CAD Addin (Fusion 360 / AutoCAD)
```

## プロジェクト構成

```
aidx-mcp/
├── addins/          # CADアドイン（サーバー側）
│   ├── fusion360/   # Fusion 360用アドイン (Python)
│   └── autocad/     # AutoCAD用アドイン (C#)
├── client/          # MCPクライアント
│   ├── mcp-server/  # 本番用MCPサーバー (Python + venv)
│   └── test-client/ # テスト用クライアント
└── docs/            # ドキュメント
```

## クイックスタート

### 1. CADアドインのインストール

#### Fusion 360

**方法1: デプロイスクリプトを使用（推奨）**

```powershell
# リポジトリルートから実行
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1
```

オプション:
- `-Clean`: 既存のアドインを削除してクリーンデプロイ
- `-Force`: 確認なしで実行

**方法2: 手動コピー**

1. `addins/fusion360/AIDX` フォルダを Fusion 360 のアドインディレクトリにコピー:
   ```
   Windows: %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
   macOS: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
   ```

2. Fusion 360を起動

3. **ユーティリティ** > **アドイン** を選択

4. **アドイン** タブで `AIDX` を選択し、**実行** をクリック

5. "AIDX Addin started. 7 commands loaded." のメッセージを確認

詳細は [addins/fusion360/README.md](addins/fusion360/README.md) を参照。

#### AutoCAD

AutoCADアドインは現在未実装です（設計は完了）。

### 2. MCPサーバーのセットアップ

```bash
cd client/mcp-server
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. MCPサーバーの起動

#### スタンドアロン実行

```bash
cd src
python main.py
```

起動ログ:
```
Connecting to fusion360 at 127.0.0.1:8109... (attempt 1/10)
Successfully connected to fusion360!
```

#### Claude Desktopとの統合

Claude Desktopの設定ファイル（`claude_desktop_config.json`）に以下を追加:

```json
{
  "mcpServers": {
    "aidx-fusion360": {
      "command": "絶対パス/client/mcp-server/venv/Scripts/python.exe",
      "args": ["絶対パス/client/mcp-server/src/main.py"],
      "env": {
        "AIDX_CAD_TYPE": "fusion360",
        "AIDX_PORT": "8109"
      }
    }
  }
}
```

詳細は [client/mcp-server/README.md](client/mcp-server/README.md) を参照。

### 4. 動作確認

#### テストクライアントで確認

```bash
cd client/test-client/src
python test_protocol.py
```

期待される出力:
```
✓ Connected to 127.0.0.1:8109
[Test 1] Screenshot
  ✓ Received 12345 bytes (PNG image)
  ✓ Valid PNG header
...
```

詳細は [client/test-client/README.md](client/test-client/README.md) を参照。

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `AIDX_CAD_TYPE` | `fusion360` | 接続先CAD (`fusion360` / `autocad`) |
| `AIDX_PORT` | `8109` | TCPポート番号 |

## 開発

### デバッグ

VSCodeで `.vscode/launch.json` に定義されたデバッグ設定を使用：

- **AIDX MCP Server (venv)**: MCPサーバーをデバッグ
- **AIDX Test Client**: テストクライアントをデバッグ（未実装）
- **AutoCAD AIDX Addin (Attach)**: AutoCADプロセスにアタッチ（未実装）

### プロジェクト進捗

- ✅ **Fusion 360アドイン**: 完全実装（プラグイン方式、分割送受信対応）
- ✅ **MCPサーバー**: 完全実装（分割送受信、エラーハンドリング、接続リトライ）
- ✅ **テストクライアント**: 完全実装（基本テスト、分割送受信テスト）
- ⏳ **AutoCADアドイン**: 未実装（設計は完了）

## ドキュメント

詳細な設計書・マニュアルは以下を参照：

### 設計書
- **[DESIGN.md](DESIGN.md)**: プロトコル仕様、実装詳細、アーキテクチャ

### コンポーネント別ドキュメント
- **[addins/fusion360/README.md](addins/fusion360/README.md)**: Fusion 360アドイン（インストール、使用方法、新規コマンド追加）
- **[client/mcp-server/README.md](client/mcp-server/README.md)**: MCPサーバー（Claude Desktop設定、トラブルシューティング）
- **[client/test-client/README.md](client/test-client/README.md)**: テストクライアント（テストシナリオ、使用方法）

### プロジェクト管理
- **CLAUDE.md**: プロジェクトルール（gitignoreに追加済み）
- **TODO.md**: 進捗管理（gitignoreに追加済み）

## ライセンス

TBD

## 貢献

TBD