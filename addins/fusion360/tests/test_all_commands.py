"""AIDX 全コマンド統合テスト"""
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
from config import (
    CMD_PING,
    CMD_SCREENSHOT,
    CMD_GET_OBJECTS,
    CMD_IMPORT_FILE,
    CMD_MODIFY
)
import time


class TestRunner:
    """テストランナー"""

    def __init__(self):
        self.client = AIDXClient(host="127.0.0.1", port=8109)
        self.test_results = []

    async def connect(self):
        """Fusion360に接続"""
        print("=" * 60)
        print("AIDX 全コマンド統合テスト")
        print("=" * 60)
        print("\nFusion360に接続中...")
        await self.client.connect()
        print("✓ 接続成功\n")

    async def close(self):
        """接続を閉じる"""
        await self.client.close()

    async def run_test(self, test_name: str, test_func):
        """テストを実行"""
        print(f"\n{'=' * 60}")
        print(f"テスト: {test_name}")
        print("=" * 60)

        start_time = time.time()
        try:
            await test_func()
            elapsed = time.time() - start_time
            self.test_results.append({
                "name": test_name,
                "status": "✓ 成功",
                "time": elapsed
            })
            print(f"\n✓ {test_name} 成功 ({elapsed:.3f}秒)")
        except Exception as e:
            elapsed = time.time() - start_time
            self.test_results.append({
                "name": test_name,
                "status": f"✗ 失敗: {e}",
                "time": elapsed
            })
            print(f"\n✗ {test_name} 失敗 ({elapsed:.3f}秒)")
            print(f"  エラー: {type(e).__name__}: {e}")

    async def test_ping(self):
        """Pingコマンドテスト"""
        response = await self.client.send_command(CMD_PING, b"")
        result = json.loads(response.decode("utf-8"))
        print(f"Ping応答: {result}")

        if result.get("status") != "pong":
            raise ValueError(f"期待しない応答: {result}")

    async def test_screenshot(self):
        """Screenshotコマンドテスト"""
        response = await self.client.send_command(CMD_SCREENSHOT, b"")
        print(f"画像サイズ: {len(response):,} バイト ({len(response) / 1024:.1f} KB)")

        # PNG/JPGヘッダ確認
        if response[:8] == b'\x89PNG\r\n\x1a\n':
            print("画像フォーマット: PNG")
        elif response[:2] == b'\xff\xd8':
            print("画像フォーマット: JPEG")
        else:
            raise ValueError(f"不明な画像フォーマット (先頭バイト: {response[:4].hex()})")

        # 画像を保存
        output_path = Path(__file__).parent / "test_screenshot.png"
        with open(output_path, "wb") as f:
            f.write(response)
        print(f"保存先: {output_path}")

    async def test_get_objects(self):
        """GetObjectsコマンドテスト"""
        request = {"filter": {}}
        payload = json.dumps(request).encode("utf-8")
        response = await self.client.send_command(CMD_GET_OBJECTS, payload)

        result = json.loads(response.decode("utf-8"))
        objects = result.get("objects", [])

        print(f"取得したオブジェクト数: {len(objects)}")

        if "error" in result:
            print(f"警告: {result['error']}")

        # 最初のオブジェクトの詳細表示
        if objects:
            obj = objects[0]
            print(f"\n最初のオブジェクト:")
            print(f"  名前: {obj.get('name', '無名')}")
            print(f"  タイプ: {obj.get('type', 'unknown')}")
            print(f"  ID: {obj.get('id', 'N/A')}")

            volume_mm3 = obj.get('volume_mm3', 0)
            if volume_mm3 > 0:
                print(f"  体積: {volume_mm3:,.1f} mm³")

        # JSONを保存
        output_path = Path(__file__).parent / "test_get_objects.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n詳細情報を保存: {output_path}")

    async def test_import_file(self):
        """ImportFileコマンドテスト（オプション）"""
        # テスト用STEPファイルのパスを指定
        test_file = Path(__file__).parent / "test_data" / "sample.step"

        if not test_file.exists():
            print(f"警告: テストファイルが見つかりません: {test_file}")
            print("このテストをスキップします。")
            return

        request = {
            "path": str(test_file),
            "pos": [100, 100, 0],  # mm単位
            "rot": [0, 0, 45]      # 度数法
        }
        payload = json.dumps(request).encode("utf-8")
        response = await self.client.send_command(CMD_IMPORT_FILE, payload)

        result = json.loads(response.decode("utf-8"))
        print(f"インポート結果: {result}")

        if not result.get("success"):
            raise ValueError(f"インポート失敗: {result.get('error')}")

        print(f"インポートされたオブジェクトID: {result.get('id')}")

    async def test_modify(self):
        """Modifyコマンドテスト（オプション）"""
        # まず GetObjects でオブジェクトIDを取得
        request = {"filter": {}}
        payload = json.dumps(request).encode("utf-8")
        response = await self.client.send_command(CMD_GET_OBJECTS, payload)

        result = json.loads(response.decode("utf-8"))
        objects = result.get("objects", [])

        if not objects:
            print("警告: 変形対象のオブジェクトがありません。")
            print("このテストをスキップします。")
            return

        # 最初のオブジェクトに対して変換行列を適用（単位行列 = 変化なし）
        target_id = objects[0].get('id')
        if not target_id:
            print("警告: オブジェクトIDが取得できません。")
            return

        # 単位行列（4x4、行優先順）
        identity_matrix = [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]

        modify_request = {
            "id": target_id,
            "matrix": identity_matrix
        }
        modify_payload = json.dumps(modify_request).encode("utf-8")
        modify_response = await self.client.send_command(CMD_MODIFY, modify_payload)

        modify_result = json.loads(modify_response.decode("utf-8"))
        print(f"変形結果: {modify_result}")

        if not modify_result.get("success"):
            raise ValueError(f"変形失敗: {modify_result.get('error')}")

    def print_summary(self):
        """テスト結果サマリーを表示"""
        print(f"\n{'=' * 60}")
        print("テスト結果サマリー")
        print("=" * 60)

        for result in self.test_results:
            status_icon = "✓" if "成功" in result["status"] else "✗"
            print(f"{status_icon} {result['name']}: {result['status']} ({result['time']:.3f}秒)")

        # 成功率計算
        success_count = sum(1 for r in self.test_results if "成功" in r["status"])
        total_count = len(self.test_results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        print(f"\n成功率: {success_count}/{total_count} ({success_rate:.1f}%)")


async def main():
    """メイン関数"""
    runner = TestRunner()

    try:
        # 接続
        await runner.connect()

        # 各テストを実行
        await runner.run_test("Ping", runner.test_ping)
        await runner.run_test("Screenshot", runner.test_screenshot)
        await runner.run_test("GetObjects", runner.test_get_objects)
        await runner.run_test("ImportFile (オプション)", runner.test_import_file)
        await runner.run_test("Modify (オプション)", runner.test_modify)

        # サマリー表示
        runner.print_summary()

        # 接続を閉じる
        await runner.close()
        print("\n接続を閉じました")

    except AIDXProtocolError as e:
        print(f"\n✗ プロトコルエラー:")
        print(f"  ErrorCode: 0x{e.code:04X}")
        print(f"  Message: {e}")
        await runner.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        await runner.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
