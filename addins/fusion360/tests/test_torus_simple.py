"""AIDX Torusシンプルテスト"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Windowsコンソールでの文字化け防止
if sys.platform == "win32":
    os.system("chcp 65001 >nul")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent / "client" / "mcp-server" / "src"))

from protocol import AIDXClient
from config import CMD_CREATE_OBJECT, CMD_DELETE_OBJECT, CMD_GET_OBJECTS


async def test_torus_variations():
    """Torusパラメータのバリエーションテスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        print("Fusion360に接続中...")
        await client.connect()
        print("✓ 接続成功\n")

        # テストケース: より大きなmajorRadius
        test_cases = [
            {"majorRadius": 100, "minorRadius": 10, "desc": "大きなTorus (R=100, r=10)"},
            {"majorRadius": 50, "minorRadius": 10, "desc": "中サイズTorus (R=50, r=10)"},
            {"majorRadius": 30, "minorRadius": 5, "desc": "小サイズTorus (R=30, r=5)"},
        ]

        for i, params in enumerate(test_cases):
            print(f"[{i+1}] {params['desc']}")

            torus_request = {
                "type": "torus",
                "params": {
                    "majorRadius": params["majorRadius"],
                    "minorRadius": params["minorRadius"]
                },
                "position": [i * 150, 0, 0],
                "rotation": [0, 0, 0]
            }

            print(f"  リクエスト: majorRadius={params['majorRadius']}mm, minorRadius={params['minorRadius']}mm")

            response = await client.send_command(
                CMD_CREATE_OBJECT,
                json.dumps(torus_request).encode("utf-8")
            )

            result = json.loads(response.decode("utf-8"))

            if result.get("success"):
                print(f"  ✓ 成功: ID={result.get('id')[:30]}...")
            else:
                print(f"  ✗ 失敗: {result.get('error')}")

            print()

        await client.close()
        print("テスト完了")

    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_torus_variations())
