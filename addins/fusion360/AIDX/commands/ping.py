"""Ping コマンド - 接続確認用の最軽量コマンド"""
import json
from .base import AIDXCommand


class PingCommand(AIDXCommand):
    """
    Pingコマンド

    接続確認用の最軽量コマンド。
    ペイロードなしで呼び出し可能で、即座にpongを返します。
    """

    COMMAND_ID = 0x0001

    def execute(self, payload: bytes) -> bytes:
        """
        Ping実行

        Args:
            payload: 空またはオプションのメッセージ

        Returns:
            {"status": "pong", "message": ...} のJSON
        """
        # ペイロードがあればデコード、なければ空文字列
        message = payload.decode("utf-8") if payload else ""

        response = {
            "status": "pong",
            "message": message if message else "AIDX server is alive"
        }

        return json.dumps(response, ensure_ascii=False).encode("utf-8")
