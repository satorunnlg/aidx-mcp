"""押し出しコマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class ExtrudeCommand(AIDXCommand):
    """面やプロファイルを押し出し"""

    COMMAND_ID = 0x0702

    def execute(self, payload: bytes) -> bytes:
        """
        押し出し実行

        Args:
            payload: JSON形式 {
                "profile_ids": ["プロファイルまたは面のentityToken", ...],
                "distance": 押し出し距離 (mm),
                "operation": "new" | "join" | "cut" | "intersect",
                "direction": "positive" | "negative" | "symmetric",  # デフォルト: positive
                "taper_angle": テーパー角度 (度),  # オプション、デフォルト: 0
            }

        Returns:
            JSON形式 {"success": true, "feature_id": "...", "bodies": [...]} または
                     {"success": false, "error": "..."}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            profile_ids = request["profile_ids"]
            distance_mm = request["distance"]
            operation = request["operation"]
            direction = request.get("direction", "positive")
            taper_angle_deg = request.get("taper_angle", 0)

            # mm → cm 変換
            distance_cm = distance_mm / 10.0

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # プロファイル/面検索
            profiles = adsk.core.ObjectCollection.create()
            for profile_id in profile_ids:
                entity = design.findEntityByToken(profile_id)
                if not entity:
                    raise RuntimeError(f"Profile/Face not found: {profile_id}")

                # ProfileまたはBRepFaceを追加
                if isinstance(entity[0], adsk.fusion.Profile):
                    profiles.add(entity[0])
                elif isinstance(entity[0], adsk.fusion.BRepFace):
                    profiles.add(entity[0])
                else:
                    raise RuntimeError(f"Invalid entity type: {type(entity[0])}")

            # ExtrudeFeature作成
            extrude_features = root_comp.features.extrudeFeatures
            extrude_input = extrude_features.createInput(profiles, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            # 操作タイプ設定
            if operation == "new":
                extrude_input.operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            elif operation == "join":
                extrude_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            elif operation == "cut":
                extrude_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            elif operation == "intersect":
                extrude_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # 距離と方向設定
            if direction == "symmetric":
                distance_value = adsk.core.ValueInput.createByReal(distance_cm / 2.0)
                extrude_input.setSymmetricExtent(distance_value, True)
            else:
                distance_value = adsk.core.ValueInput.createByReal(distance_cm)
                is_positive = (direction != "negative")
                extrude_input.setDistanceExtent(is_positive, distance_value)

            # テーパー角度設定
            if taper_angle_deg != 0:
                import math
                taper_angle_rad = math.radians(taper_angle_deg)
                extrude_input.taperAngle = adsk.core.ValueInput.createByReal(taper_angle_rad)

            # 実行
            extrude_feature = extrude_features.add(extrude_input)

            # 結果ボディ取得
            body_ids = []
            if extrude_feature.bodies:
                for i in range(extrude_feature.bodies.count):
                    body_ids.append(extrude_feature.bodies.item(i).entityToken)

            # 成功レスポンス
            response = {
                "success": True,
                "feature_id": extrude_feature.entityToken,
                "bodies": body_ids
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")
