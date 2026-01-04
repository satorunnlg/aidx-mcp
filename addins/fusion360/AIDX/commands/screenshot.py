"""スクリーンショットコマンド実装"""
import adsk.core
import tempfile
import os
from .base import AIDXCommand


class ScreenshotCommand(AIDXCommand):
    """ビューポートのスクリーンショットを取得"""

    COMMAND_ID = 0x0100

    def execute(self, payload: bytes) -> bytes:
        """
        スクリーンショット取得

        Args:
            payload: 空（このコマンドはペイロードを使用しない）

        Returns:
            PNG形式の画像バイナリ
        """
        app = adsk.core.Application.get()
        viewport = app.activeViewport

        # 一時ファイルにスクリーンショット保存
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # スクリーンショット保存
            success = viewport.saveAsImageFile(tmp_path, 0, 0)
            if not success:
                raise RuntimeError("Failed to save screenshot")

            # ファイル読み込み
            with open(tmp_path, "rb") as f:
                image_data = f.read()

            return image_data

        finally:
            # 一時ファイル削除
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
