"""AIDX CreateObject と DeleteObject コマンド統合テスト"""
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

from protocol import AIDXClient, AIDXProtocolError
from config import CMD_CREATE_OBJECT, CMD_DELETE_OBJECT, CMD_GET_OBJECTS
import time


async def test_create_and_delete():
    """CreateObjectとDeleteObjectの統合テスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)
    created_ids = []

    try:
        print("=" * 60)
        print("CreateObject & DeleteObject 統合テスト")
        print("=" * 60)

        print("\nFusion360に接続中...")
        await client.connect()
        print("✓ 接続成功\n")

        # テストケース1: Box作成
        print("=" * 60)
        print("[1] Box作成テスト")
        print("=" * 60)
        box_request = {
            "type": "box",
            "params": {
                "width": 100,   # mm
                "height": 50,
                "length": 80
            },
            "position": [50, 50, 0],
            "rotation": [0, 0, 45]
        }

        print(f"リクエスト: {json.dumps(box_request, indent=2, ensure_ascii=False)}")
        start_time = time.time()

        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(box_request).encode("utf-8")
        )

        elapsed = time.time() - start_time
        result = json.loads(response.decode("utf-8"))

        print(f"✓ Box作成完了 ({elapsed:.3f}秒)")
        print(f"  ID: {result.get('id')}")
        print(f"  Type: {result.get('type')}")

        if result.get("success"):
            created_ids.append(("box", result["id"]))
        else:
            print(f"  エラー: {result.get('error')}")

        # テストケース2: Cylinder作成
        print(f"\n{'=' * 60}")
        print("[2] Cylinder作成テスト")
        print("=" * 60)
        cylinder_request = {
            "type": "cylinder",
            "params": {
                "radius": 25,
                "height": 100
            },
            "position": [150, 50, 0],
            "rotation": [0, 0, 0]
        }

        print(f"リクエスト: {json.dumps(cylinder_request, indent=2, ensure_ascii=False)}")
        start_time = time.time()

        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(cylinder_request).encode("utf-8")
        )

        elapsed = time.time() - start_time
        result = json.loads(response.decode("utf-8"))

        print(f"✓ Cylinder作成完了 ({elapsed:.3f}秒)")
        print(f"  ID: {result.get('id')}")

        if result.get("success"):
            created_ids.append(("cylinder", result["id"]))
        else:
            print(f"  エラー: {result.get('error')}")

        # テストケース3: Sphere作成
        print(f"\n{'=' * 60}")
        print("[3] Sphere作成テスト")
        print("=" * 60)
        sphere_request = {
            "type": "sphere",
            "params": {
                "radius": 40
            },
            "position": [250, 50, 0],
            "rotation": [0, 0, 0]
        }

        print(f"リクエスト: {json.dumps(sphere_request, indent=2, ensure_ascii=False)}")
        start_time = time.time()

        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(sphere_request).encode("utf-8")
        )

        elapsed = time.time() - start_time
        result = json.loads(response.decode("utf-8"))

        print(f"✓ Sphere作成完了 ({elapsed:.3f}秒)")
        print(f"  ID: {result.get('id')}")

        if result.get("success"):
            created_ids.append(("sphere", result["id"]))
        else:
            print(f"  エラー: {result.get('error')}")

        # テストケース4: Torus作成
        print(f"\n{'=' * 60}")
        print("[4] Torus作成テスト")
        print("=" * 60)
        torus_request = {
            "type": "torus",
            "params": {
                "majorRadius": 50,
                "minorRadius": 15
            },
            "position": [350, 50, 0],
            "rotation": [90, 0, 0]
        }

        print(f"リクエスト: {json.dumps(torus_request, indent=2, ensure_ascii=False)}")
        start_time = time.time()

        response = await client.send_command(
            CMD_CREATE_OBJECT,
            json.dumps(torus_request).encode("utf-8")
        )

        elapsed = time.time() - start_time
        result = json.loads(response.decode("utf-8"))

        print(f"✓ Torus作成完了 ({elapsed:.3f}秒)")
        print(f"  ID: {result.get('id')}")

        if result.get("success"):
            created_ids.append(("torus", result["id"]))
        else:
            print(f"  エラー: {result.get('error')}")

        # GetObjectsで確認
        print(f"\n{'=' * 60}")
        print("[5] GetObjectsで作成されたオブジェクト確認")
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
            print(f"  [{i}] {obj.get('name', '無名')} (ID: {obj.get('id')})")

        # 削除テスト
        print(f"\n{'=' * 60}")
        print("[6] DeleteObjectテスト")
        print("=" * 60)

        for shape_type, object_id in created_ids:
            print(f"\n削除中: {shape_type} (ID: {object_id[:20]}...)")

            delete_request = {
                "id": object_id,
                "type": "BRepBody"
            }

            start_time = time.time()
            response = await client.send_command(
                CMD_DELETE_OBJECT,
                json.dumps(delete_request).encode("utf-8")
            )

            elapsed = time.time() - start_time
            result = json.loads(response.decode("utf-8"))

            if result.get("success"):
                print(f"  ✓ 削除成功 ({elapsed:.3f}秒)")
            else:
                print(f"  ✗ 削除失敗: {result.get('error')}")

        # 最終確認
        print(f"\n{'=' * 60}")
        print("[7] 削除後の確認")
        print("=" * 60)

        response = await client.send_command(
            CMD_GET_OBJECTS,
            json.dumps(get_request).encode("utf-8")
        )

        result = json.loads(response.decode("utf-8"))
        objects = result.get("objects", [])

        print(f"シーン内のオブジェクト数: {len(objects)}")
        if objects:
            print("残っているオブジェクト:")
            for i, obj in enumerate(objects, 1):
                print(f"  [{i}] {obj.get('name', '無名')}")
        else:
            print("すべてのオブジェクトが削除されました")

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
    asyncio.run(test_create_and_delete())
