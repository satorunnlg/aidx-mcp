"""シャンファーコマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class ChamferCommand(AIDXCommand):
    """エッジにシャンファー（面取り）を適用"""

    COMMAND_ID = 0x0701

    def execute(self, payload: bytes) -> bytes:
        """
        シャンファー実行

        Args:
            payload: JSON形式 {
                "edge_ids": ["エッジのentityToken", ...],
                "distance": 距離 (mm),  # 等距離面取り
                または
                "distance1": 距離1 (mm),  # 2距離面取り
                "distance2": 距離2 (mm),
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
            body_id = request.get("body_id")

            # mm → cm 変換
            if "distance" in request:
                # 等距離面取り
                distance_cm = request["distance"] / 10.0
                distance1_cm = distance_cm
                distance2_cm = distance_cm
            else:
                # 2距離面取り
                distance1_cm = request["distance1"] / 10.0
                distance2_cm = request["distance2"] / 10.0

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

            # ChamferFeature作成
            chamfer_features = root_comp.features.chamferFeatures
            chamfer_input = chamfer_features.createInput(edges, True)

            # 距離設定
            chamfer_input.setToTwoDistances(
                adsk.core.ValueInput.createByReal(distance1_cm),
                adsk.core.ValueInput.createByReal(distance2_cm)
            )

            # 実行
            chamfer_feature = chamfer_features.add(chamfer_input)

            # 成功レスポンス
            response = {
                "success": True,
                "feature_id": chamfer_feature.entityToken
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")
