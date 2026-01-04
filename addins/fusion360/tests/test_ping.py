"""AIDX Ping コマンド直接テスト"""
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
sys.path.insert(0, str(Path(__file__).parent / "client" / "mcp-server" / "src"))

from protocol import AIDXClient, AIDXProtocolError
from config import CMD_PING


async def test_ping():
    """Pingコマンドをテスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        print("Fusion360に接続中...")
        await client.connect()
        print("✓ 接続成功")

        print("\nPingコマンド送信中...")
        import time
        start = time.time()

        response = await client.send_command(CMD_PING, b"")

        elapsed = time.time() - start
        print(f"✓ レスポンス受信 ({elapsed:.3f}秒)")

        print(f"\nレスポンス内容:")
        print(response.decode("utf-8"))

    except AIDXProtocolError as e:
        print(f"✗ プロトコルエラー: Code 0x{e.code:04X}, Message: {e.message}")
        return 1
    except Exception as e:
        print(f"✗ エラー: {type(e).__name__}: {e}")
        return 1
    finally:
        await client.close()
        print("\n接続を閉じました")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_ping())
    sys.exit(exit_code)
