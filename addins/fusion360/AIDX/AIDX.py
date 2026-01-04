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
import protocol
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
        protocol._log("=== AIDX Addin run() started ===")
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        protocol._log("Application and UI obtained")

        # 既存サーバーのクリーンアップ（再起動時の対策）
        if _server is not None:
            protocol._log("Cleaning up existing server instance...")
            try:
                _server.stop()
            except Exception as e:
                protocol._log(f"Warning: Failed to stop existing server: {e}")
            _server = None
            protocol._log("Existing server cleaned up")

        # コマンド自動ロード
        protocol._log("Loading commands...")
        commands = load_commands()
        protocol._log(f"Loaded {len(commands)} commands")

        # AIDXサーバー起動
        protocol._log("Creating AIDXServer instance...")
        _server = AIDXServer(host="127.0.0.1", port=8109)
        protocol._log("AIDXServer instance created")

        # コマンド登録
        protocol._log("Registering commands...")
        for cmd_id, command_instance in commands.items():
            _server.register_command(cmd_id, command_instance.execute)
        protocol._log("All commands registered")

        # サーバー起動（バックグラウンドスレッド）
        protocol._log("Starting server...")
        _server.start()
        protocol._log("Server start() returned")

        # 登録コマンドリスト作成
        cmd_list = ", ".join([f"0x{cid:04X}" for cid in sorted(commands.keys())])
        _ui.messageBox(f"AIDX Addin started.\n{len(commands)} commands loaded:\n{cmd_list}")
        protocol._log("=== AIDX Addin run() completed ===")

    except Exception as e:
        error_msg = traceback.format_exc()
        protocol._log(f"ERROR in run(): {error_msg}")
        if _ui:
            _ui.messageBox(f"Failed to start AIDX:\n{error_msg}")


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
