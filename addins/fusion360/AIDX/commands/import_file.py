"""ファイルインポートコマンド実装"""
import adsk.core
import adsk.fusion
import json
from .base import AIDXCommand


class ImportFileCommand(AIDXCommand):
    """STEP等の外部ファイルをインポート"""

    COMMAND_ID = 0x0200

    def execute(self, payload: bytes) -> bytes:
        """
        ファイルインポート

        Args:
            payload: JSON形式 {"path": "...", "pos": [x, y, z], "rot": [rx, ry, rz]}
                - path: ファイルパス
                - pos: 配置座標 [x, y, z] (mm単位)
                - rot: 回転角度 [x, y, z] (度数法)

        Returns:
            JSON形式 {"success": true, "id": "オブジェクトID"} または {"success": false, "error": "エラーメッセージ"}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            file_path = request["path"]
            pos_mm = request.get("pos", [0, 0, 0])
            rot_deg = request.get("rot", [0, 0, 0])

            # mm → cm 変換（Fusion 360の内部単位）
            pos_cm = [x / 10.0 for x in pos_mm]

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # インポート実行
            import_manager = app.importManager
            import_options = import_manager.createSTEPImportOptions(file_path)

            # インポート（新しいコンポーネントとして）
            import_manager.importToTarget(import_options, root_comp)

            # インポートされた最後のOccurrenceを取得
            if root_comp.occurrences.count == 0:
                raise RuntimeError("Import succeeded but no occurrence created")

            occurrence = root_comp.occurrences.item(root_comp.occurrences.count - 1)

            # 変換行列の作成
            transform = self._create_transform_matrix(pos_cm, rot_deg)

            # 変換適用
            occurrence.transform = transform

            # 成功レスポンス
            response = {
                "success": True,
                "id": occurrence.entityToken
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")

    def _create_transform_matrix(self, pos_cm: list[float], rot_deg: list[float]) -> adsk.core.Matrix3D:
        """
        変換行列を作成

        Args:
            pos_cm: 位置 [x, y, z] (cm)
            rot_deg: 回転 [rx, ry, rz] (度)

        Returns:
            変換行列
        """
        import math

        # 単位行列
        matrix = adsk.core.Matrix3D.create()

        # 回転（度 → ラジアン）
        rx = math.radians(rot_deg[0])
        ry = math.radians(rot_deg[1])
        rz = math.radians(rot_deg[2])

        # X軸回転
        if rx != 0:
            rot_x = adsk.core.Matrix3D.create()
            rot_x.setToRotation(rx, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Point3D.create(0, 0, 0))
            matrix.transformBy(rot_x)

        # Y軸回転
        if ry != 0:
            rot_y = adsk.core.Matrix3D.create()
            rot_y.setToRotation(ry, adsk.core.Vector3D.create(0, 1, 0), adsk.core.Point3D.create(0, 0, 0))
            matrix.transformBy(rot_y)

        # Z軸回転
        if rz != 0:
            rot_z = adsk.core.Matrix3D.create()
            rot_z.setToRotation(rz, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create(0, 0, 0))
            matrix.transformBy(rot_z)

        # 移動
        translation = adsk.core.Vector3D.create(pos_cm[0], pos_cm[1], pos_cm[2])
        matrix.translation = translation

        return matrix
