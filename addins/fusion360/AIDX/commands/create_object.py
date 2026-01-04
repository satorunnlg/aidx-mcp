"""オブジェクト作成コマンド実装"""
import adsk.core
import adsk.fusion
import json
import math
from .base import AIDXCommand


class CreateObjectCommand(AIDXCommand):
    """プリミティブ形状を作成"""

    COMMAND_ID = 0x0500

    def execute(self, payload: bytes) -> bytes:
        """
        オブジェクト作成

        Args:
            payload: JSON形式 {
                "type": "box" | "cylinder" | "sphere" | "torus",
                "params": {...},
                "position": [x, y, z],  # mm
                "rotation": [rx, ry, rz]  # 度
            }

        Returns:
            JSON形式 {"success": true, "id": "...", "type": "BRepBody"}
        """
        try:
            # ペイロード解析
            request = json.loads(payload.decode("utf-8"))
            shape_type = request["type"]
            params = request["params"]
            pos_mm = request.get("position", [0, 0, 0])
            rot_deg = request.get("rotation", [0, 0, 0])

            # mm → cm 変換
            pos_cm = [x / 10.0 for x in pos_mm]

            # Fusion 360 API取得
            app = adsk.core.Application.get()
            design: adsk.fusion.Design = app.activeProduct
            root_comp = design.rootComponent

            # 形状タイプに応じて作成
            if shape_type == "box":
                body = self._create_box(root_comp, params, pos_cm, rot_deg)
            elif shape_type == "cylinder":
                body = self._create_cylinder(root_comp, params, pos_cm, rot_deg)
            elif shape_type == "sphere":
                body = self._create_sphere(root_comp, params, pos_cm, rot_deg)
            elif shape_type == "torus":
                body = self._create_torus(root_comp, params, pos_cm, rot_deg)
            else:
                raise ValueError(f"Unknown shape type: {shape_type}")

            # 成功レスポンス
            response = {
                "success": True,
                "id": body.entityToken,
                "type": "BRepBody"
            }

            return json.dumps(response).encode("utf-8")

        except Exception as e:
            # エラーレスポンス
            response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(response).encode("utf-8")

    def _create_box(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        ボックスを作成（TemporaryBRepManager使用）

        Args:
            component: コンポーネント
            params: {"width": mm, "height": mm, "length": mm}
            pos_cm: 位置 (cm)
            rot_deg: 回転 (度)

        Returns:
            作成されたBRepBody
        """
        # mm → cm 変換
        width_cm = params["width"] / 10.0
        height_cm = params["height"] / 10.0
        length_cm = params["length"] / 10.0

        # 一時BRepマネージャーでボックス作成
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()

        # 原点中心のボックスを作成（OrientedBoundingBox3Dを使用）
        center = adsk.core.Point3D.create(0, 0, 0)
        length_dir = adsk.core.Vector3D.create(1, 0, 0)
        width_dir = adsk.core.Vector3D.create(0, 1, 0)

        oriented_box = adsk.core.OrientedBoundingBox3D.create(
            center,
            length_dir,
            width_dir,
            width_cm,
            length_cm,
            height_cm
        )

        temp_body = temp_brep_mgr.createBox(oriented_box)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        temp_brep_mgr.transform(temp_body, transform)

        # BaseFeatureを使用してコンポーネントに追加
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        component.bRepBodies.add(temp_body, base_feature)
        base_feature.finishEdit()

        # finishEdit後に実際のBRepBodyを取得（最後に追加されたもの）
        body = component.bRepBodies.item(component.bRepBodies.count - 1)

        return body

    def _create_cylinder(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        円柱を作成（TemporaryBRepManager使用）

        Args:
            component: コンポーネント
            params: {"radius": mm, "height": mm}
            pos_cm: 位置 (cm)
            rot_deg: 回転 (度)

        Returns:
            作成されたBRepBody
        """
        # mm → cm 変換
        radius_cm = params["radius"] / 10.0
        height_cm = params["height"] / 10.0

        # 一時BRepマネージャーで円柱作成
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()

        # Z軸を中心軸として円柱作成（中心が原点）
        # createCylinderOrCone(point1, radius1, point2, radius2)
        point1 = adsk.core.Point3D.create(0, 0, -height_cm / 2)
        point2 = adsk.core.Point3D.create(0, 0, height_cm / 2)

        temp_body = temp_brep_mgr.createCylinderOrCone(
            point1,
            radius_cm,
            point2,
            radius_cm
        )

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        temp_brep_mgr.transform(temp_body, transform)

        # BaseFeatureを使用してコンポーネントに追加
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        component.bRepBodies.add(temp_body, base_feature)
        base_feature.finishEdit()

        # finishEdit後に実際のBRepBodyを取得（最後に追加されたもの）
        body = component.bRepBodies.item(component.bRepBodies.count - 1)

        return body

    def _create_sphere(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        球を作成（TemporaryBRepManager使用）

        Args:
            component: コンポーネント
            params: {"radius": mm}
            pos_cm: 位置 (cm)
            rot_deg: 回転 (度)

        Returns:
            作成されたBRepBody
        """
        # mm → cm 変換
        radius_cm = params["radius"] / 10.0

        # 一時BRepマネージャーで球作成
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()

        # 原点中心の球を作成
        center = adsk.core.Point3D.create(0, 0, 0)
        temp_body = temp_brep_mgr.createSphere(center, radius_cm)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        temp_brep_mgr.transform(temp_body, transform)

        # BaseFeatureを使用してコンポーネントに追加
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        component.bRepBodies.add(temp_body, base_feature)
        base_feature.finishEdit()

        # finishEdit後に実際のBRepBodyを取得（最後に追加されたもの）
        body = component.bRepBodies.item(component.bRepBodies.count - 1)

        return body

    def _create_torus(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        トーラスを作成（TemporaryBRepManager使用）

        Args:
            component: コンポーネント
            params: {"majorRadius": mm, "minorRadius": mm}
            pos_cm: 位置 (cm)
            rot_deg: 回転 (度)

        Returns:
            作成されたBRepBody
        """
        # mm → cm 変換
        major_radius_cm = params["majorRadius"] / 10.0
        minor_radius_cm = params["minorRadius"] / 10.0

        # 一時BRepマネージャーでトーラス作成
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()

        # 原点中心、Z軸を中心軸としてトーラス作成
        center = adsk.core.Point3D.create(0, 0, 0)
        axis = adsk.core.Vector3D.create(0, 0, 1)

        temp_body = temp_brep_mgr.createTorus(
            center,
            axis,
            major_radius_cm,
            minor_radius_cm
        )

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        temp_brep_mgr.transform(temp_body, transform)

        # BaseFeatureを使用してコンポーネントに追加
        base_feature = component.features.baseFeatures.add()
        base_feature.startEdit()
        component.bRepBodies.add(temp_body, base_feature)
        base_feature.finishEdit()

        # finishEdit後に実際のBRepBodyを取得（最後に追加されたもの）
        body = component.bRepBodies.item(component.bRepBodies.count - 1)

        return body

    def _create_transform_matrix(self, pos_cm: list[float], rot_deg: list[float]) -> adsk.core.Matrix3D:
        """
        変換行列を作成

        Args:
            pos_cm: 位置 [x, y, z] (cm)
            rot_deg: 回転 [rx, ry, rz] (度)

        Returns:
            変換行列
        """
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
