"""オブジェクト情報取得コマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class GetObjectsCommand(AIDXCommand):
    """CAD内のオブジェクト情報を取得"""

    COMMAND_ID = 0x0300

    def execute(self, payload: bytes) -> bytes:
        """
        オブジェクト情報取得

        Args:
            payload: JSON形式 {"filter": {...}} (フィルタ条件、現在は未使用)

        Returns:
            JSON形式 {"objects": [...]} (Fusion 360固有のフォーマット)
        """
        try:
            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # オブジェクト情報収集
            objects = []

            # BRepBodyの情報を取得
            for body in root_comp.bRepBodies:
                obj_info = self._extract_body_info(body)
                objects.append(obj_info)

            # レスポンス
            response = {
                "objects": objects
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラー時は空配列を返す
            response = {
                "objects": [],
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")

    def _extract_body_info(self, body: adsk.fusion.BRepBody) -> dict:
        """
        BRepBodyの情報を抽出

        Args:
            body: BRepBody

        Returns:
            オブジェクト情報（辞書）
        """
        # バウンディングボックス（cm → mm変換）
        bbox = body.boundingBox
        bbox_min_mm = [bbox.minPoint.x * 10, bbox.minPoint.y * 10, bbox.minPoint.z * 10]
        bbox_max_mm = [bbox.maxPoint.x * 10, bbox.maxPoint.y * 10, bbox.maxPoint.z * 10]

        # 体積（cm³ → mm³変換）
        volume_mm3 = body.volume * 1000 if body.volume else 0

        # 質量プロパティ
        mass_kg = 0
        material_name = "None"
        if body.material:
            material_name = body.material.name

        # 物理プロパティ取得
        phys_props = body.getPhysicalProperties()
        if phys_props:
            mass_kg = phys_props.mass

        return {
            "type": "BRepBody",
            "id": body.entityToken,
            "name": body.name,
            "isVisible": body.isVisible,
            "isSolid": body.isSolid,
            "volume_mm3": volume_mm3,
            "mass_kg": mass_kg,
            "material": material_name,
            "boundingBox": {
                "min": bbox_min_mm,
                "max": bbox_max_mm
            }
        }
