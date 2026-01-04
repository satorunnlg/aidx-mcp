"""AIDX Combine & Fillet コマンドテスト"""
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
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "client" / "mcp-server" / "src"))

from protocol import AIDXClient, AIDXProtocolError
from config import CMD_CREATE_OBJECT, CMD_COMBINE, CMD_FILLET, CMD_GET_OBJECTS
import time


async def test_combine_and_fillet():
    """Combine & Filletテスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        print("=" * 60)
        print("Combine & Fillet 統合テスト")
        print("=" * 60)

        print("\nFusion360に接続中...")
        await client.connect()
        print("✓ 接続成功\n")

        # テストケース1: 2つのボックスを作成
        print("=" * 60)
        print("[1] ボックス2つ作成")
        print("=" * 60)

        box1_request = {
            "type": "box",
            "params": {"width": 100, "height": 100, "length": 100},
            "position": [0, 0, 0],
            "rotation": [0, 0, 0]
        }

        print("Box1作成中...")
        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(box1_request).encode("utf-8")
        )
        box1_result = json.loads(response.decode("utf-8"))
        print(f"✓ Box1作成完了: {box1_result.get('id')[:30]}...")

        box2_request = {
            "type": "box",
            "params": {"width": 60, "height": 60, "length": 60},
            "position": [70, 0, 0],
            "rotation": [0, 0, 45]
        }

        print("Box2作成中...")
        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(box2_request).encode("utf-8")
        )
        box2_result = json.loads(response.decode("utf-8"))
        print(f"✓ Box2作成完了: {box2_result.get('id')[:30]}...")

        # テストケース2: Combine - Join（結合）
        print(f"\n{'=' * 60}")
        print("[2] Combine - Join（結合）")
        print("=" * 60)

        combine_request = {
            "target_body_id": box1_result["id"],
            "tool_body_ids": [box2_result["id"]],
            "operation": "join",
            "keep_tools": False
        }

        print("結合実行中...")
        start_time = time.time()
        response = await client.send_command(
            CMD_COMBINE,
            json.dumps(combine_request).encode("utf-8")
        )
        elapsed = time.time() - start_time
        combine_result = json.loads(response.decode("utf-8"))

        if combine_result.get("success"):
            print(f"✓ 結合成功 ({elapsed:.3f}秒)")
            print(f"  Result Body ID: {combine_result.get('result_body_id')[:30]}...")
            combined_body_id = combine_result["result_body_id"]
        else:
            print(f"✗ 結合失敗: {combine_result.get('error')}")
            await client.close()
            return

        # テストケース3: GetObjectsで確認
        print(f"\n{'=' * 60}")
        print("[3] 結合後のオブジェクト確認")
        print("=" * 60)

        get_request = {"filter": {}}
        response = await client.send_command(
            CMD_GET_OBJECTS,
            json.dumps(get_request).encode("utf-8")
        )

        result = json.loads(response.decode("utf-8"))
        objects = result.get("objects", [])

        print(f"シーン内のオブジェクト数: {len(objects)}")
        for i, obj in enumerate(objects, 1):
            print(f"  [{i}] {obj.get('name', '無名')}")

        # テストケース4: エッジ検索とフィレット
        print(f"\n{'=' * 60}")
        print("[4] エッジ検索（手動指定が必要）")
        print("=" * 60)
        print("注: エッジIDの自動取得は複雑なため、手動テストが推奨されます")
        print("Fusion360 GUI でエッジを選択してentityTokenを取得してください")

        await client.close()
        print(f"\n{'=' * 60}")
        print("テスト完了")
        print("=" * 60)

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
    asyncio.run(test_combine_and_fillet())
