"""AIDX MCP Server メインエントリーポイント"""
import asyncio
import base64
import json
import logging
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool
from protocol import AIDXClient, AIDXProtocolError
from config import (
    CMD_SCREENSHOT,
    CMD_IMPORT_FILE,
    CMD_GET_OBJECTS,
    CMD_MODIFY,
    CONNECT_RETRY_MAX,
    CONNECT_RETRY_INTERVAL,
    AIDX_HOST,
    AIDX_PORT,
    CAD_TYPE,
)

# ロギング設定（STDIOサーバーのためstderrに出力）
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)

# MCPサーバーインスタンス
app = Server("aidx-mcp")

# AIDXクライアント（グローバル）
aidx_client: AIDXClient | None = None


@app.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧"""
    logging.debug("list_tools called")
    tools = [
        Tool(
            name="screenshot",
            description="CADビューポートのスクリーンショットを取得",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="import_file",
            description="STEP等の外部ファイルをCADにインポート",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス"},
                    "pos": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "配置座標 [x, y, z] (mm単位)"
                    },
                    "rot": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "回転角度 [x, y, z] (度数法)"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_objects",
            description="CAD内のオブジェクト情報を取得。注意: レスポンス形式はCADによって異なります",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "object",
                        "description": "抽出条件（CAD依存）"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="modify",
            description="既存オブジェクトの変形・移動",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "オブジェクトID"},
                    "matrix": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "4x4変換行列（16要素）"
                    }
                },
                "required": ["id", "matrix"]
            }
        )
    ]
    logging.debug(f"Returning {len(tools)} tools")
    return tools


async def _ensure_connection():
    """
    CAD接続を確保（未接続の場合は接続試行）

    Returns:
        接続済みのAIDXClient

    Raises:
        RuntimeError: 接続に失敗した場合
    """
    global aidx_client

    if aidx_client is None:
        # 初回接続試行（リトライなし、即座に失敗）
        client = AIDXClient()
        try:
            logging.info(f"Connecting to {CAD_TYPE} at {AIDX_HOST}:{AIDX_PORT}...")
            await client.connect()
            logging.info(f"Successfully connected to {CAD_TYPE}!")
            aidx_client = client
        except (ConnectionRefusedError, OSError) as e:
            raise RuntimeError(
                f"Failed to connect to {CAD_TYPE} at {AIDX_HOST}:{AIDX_PORT}. "
                f"Please ensure the CAD addin is running. Details: {e}"
            )

    return aidx_client


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """ツール実行"""
    logging.debug(f"call_tool invoked: name='{name}', arguments={arguments}")

    # CAD接続を確保（遅延接続）
    try:
        logging.debug("Ensuring connection to CAD...")
        await _ensure_connection()
        logging.debug("Connection successful")
    except RuntimeError as e:
        logging.error(f"Connection failed: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Connection error: {e}"
            }],
            "isError": True
        }

    try:
        logging.debug(f"Executing tool: {name}")
        if name == "screenshot":
            result = await _screenshot()
        elif name == "import_file":
            result = await _import_file(arguments)
        elif name == "get_objects":
            result = await _get_objects(arguments)
        elif name == "modify":
            result = await _modify(arguments)
        else:
            logging.warning(f"Unknown tool requested: {name}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: Unknown tool '{name}'"
                }],
                "isError": True
            }

        logging.debug(f"Tool '{name}' executed successfully")
        return result

    except AIDXProtocolError as e:
        # AIDXプロトコルエラー（CAD側からのエラーレスポンス）
        error_msg = f"AIDX Protocol Error (Code 0x{e.code:04X}): {e.message}"
        if e.cmd_id:
            error_msg += f"\nOriginal Command: 0x{e.cmd_id:04X}"
        if e.seq:
            error_msg += f"\nSequence: {e.seq}"

        return {
            "content": [{
                "type": "text",
                "text": error_msg
            }],
            "isError": True
        }

    except Exception as e:
        # 予期しないエラー
        return {
            "content": [{
                "type": "text",
                "text": f"Unexpected error: {type(e).__name__}: {str(e)}"
            }],
            "isError": True
        }


async def _screenshot() -> dict:
    """スクリーンショット取得"""
    image_data = await aidx_client.send_command(CMD_SCREENSHOT)
    return {
        "content": [
            {
                "type": "image",
                "data": base64.b64encode(image_data).decode(),
                "mimeType": "image/png"
            }
        ]
    }


async def _import_file(args: dict) -> dict:
    """ファイルインポート"""
    payload = json.dumps({
        "path": args["path"],
        "pos": args.get("pos", [0, 0, 0]),
        "rot": args.get("rot", [0, 0, 0])
    }).encode("utf-8")

    response = await aidx_client.send_command(CMD_IMPORT_FILE, payload)
    result = json.loads(response.decode("utf-8"))

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def _get_objects(args: dict) -> dict:
    """オブジェクト情報取得"""
    filter_data = args.get("filter", {})
    payload = json.dumps(filter_data).encode("utf-8")

    response = await aidx_client.send_command(CMD_GET_OBJECTS, payload)
    result = json.loads(response.decode("utf-8"))

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def _modify(args: dict) -> dict:
    """オブジェクト変形"""
    payload = json.dumps({
        "id": args["id"],
        "matrix": args["matrix"]
    }).encode("utf-8")

    response = await aidx_client.send_command(CMD_MODIFY, payload)
    result = json.loads(response.decode("utf-8"))

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


async def connect_with_retry() -> AIDXClient:
    """
    CADアドインへの接続（リトライ機能付き）

    Returns:
        接続済みのAIDXClient

    Raises:
        RuntimeError: 最大リトライ回数を超えても接続できなかった場合
    """
    client = AIDXClient()

    for attempt in range(1, CONNECT_RETRY_MAX + 1):
        try:
            logging.info(f"Connecting to {CAD_TYPE} at {AIDX_HOST}:{AIDX_PORT}... (attempt {attempt}/{CONNECT_RETRY_MAX})")
            await client.connect()
            logging.info(f"Successfully connected to {CAD_TYPE}!")
            return client

        except (ConnectionRefusedError, OSError) as e:
            if attempt < CONNECT_RETRY_MAX:
                logging.warning(f"Connection failed: {e}. Retrying in {CONNECT_RETRY_INTERVAL} seconds...")
                await asyncio.sleep(CONNECT_RETRY_INTERVAL)
            else:
                logging.error(f"Connection failed after {CONNECT_RETRY_MAX} attempts.")
                raise RuntimeError(
                    f"Failed to connect to {CAD_TYPE} at {AIDX_HOST}:{AIDX_PORT}. "
                    f"Please ensure the CAD addin is running."
                )


async def main():
    """メインエントリーポイント"""
    global aidx_client

    # 起動時は接続しない（遅延接続方式）
    aidx_client = None
    logging.info(f"AIDX MCP Server started (target: {CAD_TYPE} at {AIDX_HOST}:{AIDX_PORT})")
    logging.info("Connection will be established on first tool use.")

    # MCPサーバー起動（stdio経由）
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
