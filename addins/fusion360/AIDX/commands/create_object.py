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
        ボックスを作成

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

        # 原点にボックススケッチ作成
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)

        # 矩形描画（原点中心）
        lines = sketch.sketchCurves.sketchLines
        rect = lines.addTwoPointRectangle(
            adsk.core.Point3D.create(-width_cm / 2, -length_cm / 2, 0),
            adsk.core.Point3D.create(width_cm / 2, length_cm / 2, 0)
        )

        # 押し出し
        prof = sketch.profiles.item(0)
        extrudes = component.features.extrudeFeatures

        # 押し出し距離（対称に押し出す）
        distance = adsk.core.ValueInput.createByReal(height_cm)

        # 対称押し出し（中心から上下に）
        extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)
        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(
            adsk.core.ValueInput.createByReal(-height_cm / 2)
        )

        extrude = extrudes.add(extrude_input)
        body = extrude.bodies.item(0)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)

        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)

        return body

    def _create_cylinder(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        円柱を作成

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

        # XY平面に円スケッチ作成
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)

        # 円描画（原点中心）
        circles = sketch.sketchCurves.sketchCircles
        center = adsk.core.Point3D.create(0, 0, 0)
        circle = circles.addByCenterRadius(center, radius_cm)

        # 押し出し
        prof = sketch.profiles.item(0)
        extrudes = component.features.extrudeFeatures

        distance = adsk.core.ValueInput.createByReal(height_cm)
        extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)

        extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_input.startExtent = adsk.fusion.OffsetStartDefinition.create(
            adsk.core.ValueInput.createByReal(-height_cm / 2)
        )

        extrude = extrudes.add(extrude_input)
        body = extrude.bodies.item(0)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)

        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)

        return body

    def _create_sphere(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        球を作成

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

        # YZ平面に半円スケッチ作成
        sketches = component.sketches
        yz_plane = component.yZConstructionPlane
        sketch = sketches.add(yz_plane)

        # 半円描画（回転軸を通る）
        arcs = sketch.sketchCurves.sketchArcs
        start_point = adsk.core.Point3D.create(0, radius_cm, 0)
        end_point = adsk.core.Point3D.create(0, -radius_cm, 0)
        center = adsk.core.Point3D.create(0, 0, 0)

        arc = arcs.addByCenterStartEnd(center, start_point, end_point)

        # 軸を閉じる（直線で）
        lines = sketch.sketchCurves.sketchLines
        line = lines.addByTwoPoints(end_point, start_point)

        # 回転
        prof = sketch.profiles.item(0)
        revolves = component.features.revolveFeatures

        # Y軸を中心に360度回転
        axis = component.yConstructionAxis
        angle = adsk.core.ValueInput.createByReal(math.pi * 2)

        revolve_input = revolves.createInput(prof, axis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        revolve_input.setAngleExtent(False, angle)

        revolve = revolves.add(revolve_input)
        body = revolve.bodies.item(0)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)

        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)

        return body

    def _create_torus(
        self,
        component: adsk.fusion.Component,
        params: dict,
        pos_cm: list[float],
        rot_deg: list[float]
    ) -> adsk.fusion.BRepBody:
        """
        トーラスを作成

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

        # XY平面に円スケッチ作成
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)

        # チューブの円描画（X軸方向にmajor_radius離れた位置に配置）
        circles = sketch.sketchCurves.sketchCircles
        center = adsk.core.Point3D.create(major_radius_cm, 0, 0)
        circle = circles.addByCenterRadius(center, minor_radius_cm)

        # 回転軸を明示的にスケッチ内に作成（Y軸として）
        lines = sketch.sketchCurves.sketchLines
        axis_line = lines.addByTwoPoints(
            adsk.core.Point3D.create(0, -1, 0),
            adsk.core.Point3D.create(0, 1, 0)
        )
        axis_line.isConstruction = True  # 構築線として設定

        # 回転
        prof = sketch.profiles.item(0)
        revolves = component.features.revolveFeatures

        # 作成した軸線を中心に360度回転
        angle = adsk.core.ValueInput.createByReal(math.pi * 2)

        revolve_input = revolves.createInput(prof, axis_line, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        revolve_input.setAngleExtent(False, angle)

        revolve = revolves.add(revolve_input)
        body = revolve.bodies.item(0)

        # 変換行列を適用
        transform = self._create_transform_matrix(pos_cm, rot_deg)
        move_features = component.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(body)

        move_input = move_features.createInput(bodies, transform)
        move_features.add(move_input)

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
