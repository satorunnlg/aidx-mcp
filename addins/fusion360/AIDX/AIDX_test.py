"""起動テスト用の簡易版"""
import traceback
from pathlib import Path
import os
from datetime import datetime

# ログファイル
LOG_FILE = Path(os.environ.get("TEMP", "/tmp")) / "aidx_startup_test.log"

def _log(msg):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
            f.flush()
    except:
        pass

def run(context):
    try:
        _log("=== Test Started ===")
        _log(f"__file__ = {__file__}")

        # protocol.pyのインポートテスト
        _log("Attempting to import protocol...")
        import protocol
        _log(f"protocol module imported: {protocol}")

        # _log関数の存在確認
        _log(f"protocol._log exists: {hasattr(protocol, '_log')}")

        # AIDXServerのインポートテスト
        _log("Attempting to import AIDXServer...")
        from protocol import AIDXServer
        _log(f"AIDXServer imported: {AIDXServer}")

        # protocol._logの呼び出しテスト
        _log("Attempting to call protocol._log...")
        protocol._log("Test message from AIDX_test.py")
        _log("protocol._log succeeded")

        _log("=== Test Completed Successfully ===")

    except Exception as e:
        error_msg = traceback.format_exc()
        _log(f"ERROR: {error_msg}")

def stop(context):
    pass
