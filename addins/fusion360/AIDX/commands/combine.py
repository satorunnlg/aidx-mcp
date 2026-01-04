"""結合演算コマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class CombineCommand(AIDXCommand):
    """ブール演算（Union/Subtract/Intersect）"""

    COMMAND_ID = 0x0703

    def execute(self, payload: bytes) -> bytes:
        """
        結合演算実行

        Args:
            payload: JSON形式 {
                "target_body_id": "対象ボディのentityToken",
                "tool_body_ids": ["ツールボディのentityToken", ...],
                "operation": "join" | "cut" | "intersect",
                "keep_tools": false  # ツールボディを保持するか
            }

        Returns:
            JSON形式 {"success": true, "result_body_id": "..."} または
                     {"success": false, "error": "..."}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            target_body_id = request["target_body_id"]
            tool_body_ids = request["tool_body_ids"]
            operation = request["operation"]
            keep_tools = request.get("keep_tools", False)

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # 対象ボディ検索
            target_entity = design.findEntityByToken(target_body_id)
            if not target_entity or not isinstance(target_entity[0], adsk.fusion.BRepBody):
                raise RuntimeError(f"Target body not found: {target_body_id}")
            target_body = target_entity[0]

            # ツールボディ検索
            tool_bodies = adsk.core.ObjectCollection.create()
            for tool_id in tool_body_ids:
                tool_entity = design.findEntityByToken(tool_id)
                if not tool_entity or not isinstance(tool_entity[0], adsk.fusion.BRepBody):
                    raise RuntimeError(f"Tool body not found: {tool_id}")
                tool_bodies.add(tool_entity[0])

            # 操作タイプ変換
            if operation == "join":
                op_type = adsk.fusion.FeatureOperations.JoinFeatureOperation
            elif operation == "cut":
                op_type = adsk.fusion.FeatureOperations.CutFeatureOperation
            elif operation == "intersect":
                op_type = adsk.fusion.FeatureOperations.IntersectFeatureOperation
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # CombineFeature作成
            combine_features = root_comp.features.combineFeatures
            combine_input = combine_features.createInput(target_body, tool_bodies)
            combine_input.operation = op_type
            combine_input.isKeepToolBodies = keep_tools

            # 実行
            combine_feature = combine_features.add(combine_input)

            # 結果ボディ取得
            result_bodies = combine_feature.bodies
            if result_bodies.count > 0:
                result_body_id = result_bodies.item(0).entityToken
            else:
                result_body_id = target_body.entityToken

            # 成功レスポンス
            response = {
                "success": True,
                "result_body_id": result_body_id
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")
