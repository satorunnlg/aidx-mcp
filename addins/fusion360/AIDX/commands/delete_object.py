"""オブジェクト削除コマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class DeleteObjectCommand(AIDXCommand):
    """オブジェクトを削除"""

    COMMAND_ID = 0x0600

    def execute(self, payload: bytes) -> bytes:
        """
        オブジェクト削除

        Args:
            payload: JSON形式 {
                "id": "entityToken",
                "type": "BRepBody" | "Occurrence" | "Sketch"
            }

        Returns:
            JSON形式 {"success": true, "deleted": "entityToken"}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            object_id = request["id"]
            object_type = request.get("type", "BRepBody")

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # オブジェクト検索
            entity = design.findEntityByToken(object_id)
            if not entity:
                raise RuntimeError(f"Object not found: {object_id}")

            # タイプに応じて削除
            deleted_id = None

            if object_type == "BRepBody" and isinstance(entity[0], adsk.fusion.BRepBody):
                body: adsk.fusion.BRepBody = entity[0]
                # BRepBodyを削除（deleteMe()を使用）
                body.deleteMe()
                deleted_id = object_id

            elif object_type == "Occurrence" and isinstance(entity[0], adsk.fusion.Occurrence):
                occurrence: adsk.fusion.Occurrence = entity[0]
                # Occurrenceを削除
                occurrence.deleteMe()
                deleted_id = object_id

            elif object_type == "Sketch" and isinstance(entity[0], adsk.fusion.Sketch):
                sketch: adsk.fusion.Sketch = entity[0]
                # Sketchを削除
                sketch.deleteMe()
                deleted_id = object_id

            else:
                raise RuntimeError(
                    f"Type mismatch or unsupported type: "
                    f"expected {object_type}, got {type(entity[0]).__name__}"
                )

            # 成功レスポンス
            response = {
                "success": True,
                "deleted": deleted_id
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")
