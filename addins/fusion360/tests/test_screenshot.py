"""AIDX Screenshot コマンドテスト"""
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
from config import CMD_SCREENSHOT
import time


async def test_screenshot():
    """Screenshotコマンドをテスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        print("Fusion360に接続中...")
        await client.connect()
        print("✓ 接続成功\n")

        print("Screenshotコマンド送信中...")
        start_time = time.time()

        # スクリーンショット取得
        response = await client.send_command(CMD_SCREENSHOT, b"")

        elapsed = time.time() - start_time
        print(f"✓ レスポンス受信 ({elapsed:.3f}秒)\n")

        # レスポンス情報
        print(f"画像サイズ: {len(response):,} バイト ({len(response) / 1024:.1f} KB)")

        # PNG/JPGヘッダ確認
        if response[:8] == b'\x89PNG\r\n\x1a\n':
            print("画像フォーマット: PNG")
        elif response[:2] == b'\xff\xd8':
            print("画像フォーマット: JPEG")
        else:
            print(f"画像フォーマット: 不明 (先頭バイト: {response[:4].hex()})")

        # 画像を保存
        output_path = Path(__file__).parent / "screenshot_test.png"
        with open(output_path, "wb") as f:
            f.write(response)
        print(f"\n保存先: {output_path}")

        await client.close()
        print("\n接続を閉じました")

    except AIDXProtocolError as e:
        print(f"\n✗ プロトコルエラー:")
        print(f"  ErrorCode: 0x{e.code:04X}")
        print(f"  Message: {e}")
        await client.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_screenshot())
