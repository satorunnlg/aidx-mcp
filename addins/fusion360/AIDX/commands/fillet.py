"""フィレットコマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class FilletCommand(AIDXCommand):
    """エッジにフィレット（丸め）を適用"""

    COMMAND_ID = 0x0700

    def execute(self, payload: bytes) -> bytes:
        """
        フィレット実行

        Args:
            payload: JSON形式 {
                "edge_ids": ["エッジのentityToken", ...],
                "radius": 半径 (mm),
                "body_id": "対象ボディのentityToken（オプション）"
            }

        Returns:
            JSON形式 {"success": true, "feature_id": "..."} または
                     {"success": false, "error": "..."}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            edge_ids = request["edge_ids"]
            radius_mm = request["radius"]
            body_id = request.get("body_id")

            # mm → cm 変換
            radius_cm = radius_mm / 10.0

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # エッジ検索
            edges = adsk.core.ObjectCollection.create()
            for edge_id in edge_ids:
                edge_entity = design.findEntityByToken(edge_id)
                if not edge_entity or not isinstance(edge_entity[0], adsk.fusion.BRepEdge):
                    raise RuntimeError(f"Edge not found: {edge_id}")
                edges.add(edge_entity[0])

            # FilletFeature作成
            fillet_features = root_comp.features.filletFeatures
            fillet_input = fillet_features.createInput()
            fillet_input.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(radius_cm), True)

            # 実行
            fillet_feature = fillet_features.add(fillet_input)

            # 成功レスポンス
            response = {
                "success": True,
                "feature_id": fillet_feature.entityToken
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")
