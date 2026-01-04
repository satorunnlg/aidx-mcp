"""AIDX Fusion 360 アドイン エントリーポイント"""
import adsk.core
import adsk.fusion
import traceback
import importlib
import sys
from pathlib import Path

# モジュールパス追加
_script_dir = Path(__file__).parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from protocol import AIDXServer
from commands.base import AIDXCommand

# グローバル変数
_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_server: AIDXServer = None
_handlers = []


def run(context):
    """アドイン起動時に呼ばれる"""
    global _app, _ui, _server

    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # コマンド自動ロード
        commands = load_commands()

        # AIDXサーバー起動
        _server = AIDXServer(host="127.0.0.1", port=8109)

        # コマンド登録
        for cmd_id, command_instance in commands.items():
            _server.register_command(cmd_id, command_instance.execute)

        # サーバー起動（バックグラウンドスレッド）
        _server.start()

        _ui.messageBox(f"AIDX Addin started. {len(commands)} commands loaded.")

    except:
        if _ui:
            _ui.messageBox(f"Failed to start AIDX:\n{traceback.format_exc()}")


def stop(context):
    """アドイン停止時に呼ばれる"""
    global _server, _ui

    try:
        if _server:
            _server.stop()
            _server = None

        if _ui:
            _ui.messageBox("AIDX Addin stopped.")

    except:
        if _ui:
            _ui.messageBox(f"Failed to stop AIDX:\n{traceback.format_exc()}")


def load_commands() -> dict[int, AIDXCommand]:
    """
    commands/ディレクトリから全コマンドを自動ロード

    Returns:
        CommandID → AIDXCommandインスタンスの辞書
    """
    commands = {}
    commands_dir = _script_dir / "commands"

    # commands/ディレクトリ内の全.pyファイルをスキャン
    for file in commands_dir.glob("*.py"):
        # __init__.py と base.py はスキップ
        if file.name.startswith("_") or file.name == "base.py":
            continue

        try:
            # 動的インポート
            module_name = f"commands.{file.stem}"

            # 既存モジュールの場合はリロード
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)

            # AIDXCommandサブクラスを検索
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # クラスで、AIDXCommandのサブクラスで、AIDXCommand自身ではない
                if (isinstance(attr, type) and
                    issubclass(attr, AIDXCommand) and
                    attr is not AIDXCommand):

                    # インスタンス化
                    instance = attr()

                    # COMMAND_IDチェック
                    if not hasattr(instance, "COMMAND_ID"):
                        raise ValueError(f"{attr_name} does not define COMMAND_ID")

                    cmd_id = instance.COMMAND_ID

                    # 重複チェック
                    if cmd_id in commands:
                        raise ValueError(
                            f"Duplicate COMMAND_ID 0x{cmd_id:04X}: "
                            f"{commands[cmd_id].__class__.__name__} and {attr_name}"
                        )

                    commands[cmd_id] = instance

        except Exception as e:
            # コマンドロードエラーは警告のみ（アドイン起動は継続）
            if _ui:
                _ui.messageBox(
                    f"Warning: Failed to load command from {file.name}:\n{str(e)}"
                )

    return commands
