"""オブジェクト変形コマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class ModifyCommand(AIDXCommand):
    """既存オブジェクトの変形・移動"""

    COMMAND_ID = 0x0400

    def execute(self, payload: bytes) -> bytes:
        """
        オブジェクト変形

        Args:
            payload: JSON形式 {"id": "オブジェクトID", "matrix": [16要素の4x4行列]}

        Returns:
            JSON形式 {"success": true} または {"success": false, "error": "エラーメッセージ"}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            object_id = request["id"]
            matrix_values = request["matrix"]

            if len(matrix_values) != 16:
                raise ValueError("Matrix must have 16 elements (4x4)")

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # オブジェクト検索
            entity = design.findEntityByToken(object_id)
            if not entity:
                raise RuntimeError(f"Object not found: {object_id}")

            # Occurrenceかどうか確認
            if isinstance(entity[0], adsk.fusion.Occurrence):
                occurrence = entity[0]

                # 4x4行列を作成
                transform = self._create_matrix_from_values(matrix_values)

                # 変換適用
                occurrence.transform = transform

                response = {"success": True}
            else:
                raise RuntimeError(f"Entity is not an Occurrence: {type(entity[0])}")

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")

    def _create_matrix_from_values(self, values: list[float]) -> adsk.core.Matrix3D:
        """
        16要素の配列から4x4変換行列を作成

        Args:
            values: 16要素の配列（行優先順）

        Returns:
            Matrix3D
        """
        matrix = adsk.core.Matrix3D.create()

        # Matrix3Dのデータ配列に設定（Fusion APIは列優先）
        # 入力は行優先なので転置が必要
        matrix_data = [
            values[0], values[4], values[8], values[12],   # 列1
            values[1], values[5], values[9], values[13],   # 列2
            values[2], values[6], values[10], values[14],  # 列3
            values[3], values[7], values[11], values[15]   # 列4
        ]

        matrix.setWithArray(matrix_data)

        return matrix
