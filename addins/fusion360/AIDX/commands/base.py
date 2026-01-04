"""AIDXコマンド抽象基底クラス"""
from abc import ABC, abstractmethod


class AIDXCommand(ABC):
    """
    AIDXコマンドの抽象基底クラス

    サブクラスは以下を実装する必要があります:
    - COMMAND_ID: コマンドID（0x0100～0xFFFE）
    - execute(payload): コマンド実行メソッド
    """

    COMMAND_ID: int  # サブクラスで必ず定義

    @abstractmethod
    def execute(self, payload: bytes) -> bytes:
        """
        コマンド実行

        Args:
            payload: リクエストペイロード（分割受信済みの完全なデータ）

        Returns:
            レスポンスペイロード（64KB超過時は自動で分割送信される）

        Raises:
            Exception: コマンド実行エラー（プロトコル層でERR_EXECUTION_ERRORに変換される）
        """
        pass
