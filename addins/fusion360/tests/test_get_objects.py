"""AIDX GetObjects コマンドテスト"""
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
from config import CMD_GET_OBJECTS
import time


async def test_get_objects():
    """GetObjectsコマンドをテスト"""
    client = AIDXClient(host="127.0.0.1", port=8109)

    try:
        print("Fusion360に接続中...")
        await client.connect()
        print("✓ 接続成功\n")

        print("GetObjectsコマンド送信中...")
        start_time = time.time()

        # オブジェクト情報取得（フィルタは空）
        request = {"filter": {}}
        payload = json.dumps(request).encode("utf-8")

        response = await client.send_command(CMD_GET_OBJECTS, payload)

        elapsed = time.time() - start_time
        print(f"✓ レスポンス受信 ({elapsed:.3f}秒)\n")

        # レスポンス解析
        result = json.loads(response.decode("utf-8"))

        # オブジェクト数
        objects = result.get("objects", [])
        print(f"取得したオブジェクト数: {len(objects)}")

        # エラー確認
        if "error" in result:
            print(f"警告: {result['error']}")

        # 各オブジェクトの情報表示
        if objects:
            print("\nオブジェクト詳細:")
            for i, obj in enumerate(objects, 1):
                print(f"\n[{i}] {obj.get('name', '無名')}")
                print(f"  タイプ: {obj.get('type', 'unknown')}")
                print(f"  ID: {obj.get('id', 'N/A')}")
                print(f"  表示: {'表示中' if obj.get('isVisible') else '非表示'}")
                print(f"  ソリッド: {'はい' if obj.get('isSolid') else 'いいえ'}")

                # 体積
                volume_mm3 = obj.get('volume_mm3', 0)
                if volume_mm3 > 0:
                    print(f"  体積: {volume_mm3:,.1f} mm³ ({volume_mm3 / 1000:.1f} cm³)")

                # 質量
                mass_kg = obj.get('mass_kg', 0)
                if mass_kg > 0:
                    print(f"  質量: {mass_kg:.3f} kg")

                # マテリアル
                material = obj.get('material')
                if material and material != 'None':
                    print(f"  マテリアル: {material}")

                # バウンディングボックス
                bbox = obj.get('boundingBox')
                if bbox:
                    bbox_min = bbox.get('min', [0, 0, 0])
                    bbox_max = bbox.get('max', [0, 0, 0])
                    size_x = bbox_max[0] - bbox_min[0]
                    size_y = bbox_max[1] - bbox_min[1]
                    size_z = bbox_max[2] - bbox_min[2]
                    print(f"  サイズ: {size_x:.1f} × {size_y:.1f} × {size_z:.1f} mm")
        else:
            print("\nシーンにオブジェクトがありません。")

        # JSONをファイルに保存
        output_path = Path(__file__).parent / "get_objects_result.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n詳細情報を保存: {output_path}")

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
    asyncio.run(test_get_objects())
