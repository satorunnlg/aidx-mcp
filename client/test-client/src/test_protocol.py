"""AIDX プロトコル基本テスト"""
import socket
import struct
import json
import sys

# プロトコル定数
AIDX_MAGIC = 0x41494458
CHUNK_SIZE = 64 * 1024

# コマンドID
CMD_SCREENSHOT = 0x0100
CMD_IMPORT_FILE = 0x0200
CMD_GET_OBJECTS = 0x0300
CMD_MODIFY = 0x0400
CMD_ERROR = 0xFFFF

# Flags
FLAG_SINGLE = 0x0000


class AIDXTestClient:
    """AIDXプロトコルテストクライアント（同期版）"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8109):
        self.host = host
        self.port = port
        self.sock: socket.socket = None
        self.seq_counter = 0

    def connect(self):
        """接続"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"✓ Connected to {self.host}:{self.port}")

    def close(self):
        """切断"""
        if self.sock:
            self.sock.close()
            self.sock = None
            print("✓ Disconnected")

    def _next_seq(self) -> int:
        """次のSequence番号"""
        seq = self.seq_counter
        self.seq_counter = (self.seq_counter + 1) % 65536
        return seq

    def send_command(self, cmd_id: int, payload: bytes = b"") -> bytes:
        """
        コマンド送信（単一パケットのみ）

        Args:
            cmd_id: コマンドID
            payload: ペイロード

        Returns:
            レスポンスペイロード
        """
        seq = self._next_seq()

        # ヘッダ構築
        header = struct.pack(
            "<IHHHII",
            AIDX_MAGIC,
            cmd_id,
            FLAG_SINGLE,
            seq,
            0x0000,
            len(payload),
            len(payload)
        )

        # 送信
        self.sock.sendall(header + payload)
        print(f"  → Sent: CommandID=0x{cmd_id:04X}, Seq={seq}, PayloadSize={len(payload)}")

        # レスポンス受信
        return self._recv_response(seq, cmd_id)

    def _recv_response(self, expected_seq: int, sent_cmd_id: int) -> bytes:
        """レスポンス受信（単一パケットのみ）"""
        # ヘッダ受信
        header_data = self._recv_exact(16)

        # ヘッダ解析
        magic, cmd_id, flags, seq, reserved, payload_size, total_size = struct.unpack(
            "<IHHHII", header_data
        )

        print(f"  ← Recv: CommandID=0x{cmd_id:04X}, Seq={seq}, PayloadSize={payload_size}, TotalSize={total_size}, Flags=0x{flags:04X}")

        # 検証
        if magic != AIDX_MAGIC:
            raise RuntimeError(f"Invalid magic: {magic:#x}")
        if seq != expected_seq:
            raise RuntimeError(f"Sequence mismatch: expected {expected_seq}, got {seq}")

        # ペイロード受信
        payload = self._recv_exact(payload_size) if payload_size > 0 else b""

        # エラーレスポンスチェック
        if cmd_id == CMD_ERROR:
            error_data = json.loads(payload.decode("utf-8"))
            raise RuntimeError(
                f"AIDX Error: Code=0x{error_data['ErrorCode']:04X}, "
                f"Message={error_data['Message']}"
            )

        return payload

    def _recv_exact(self, size: int) -> bytes:
        """指定バイト数を正確に受信"""
        data = b""
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise RuntimeError("Connection closed")
            data += chunk
        return data


def test_screenshot(client: AIDXTestClient):
    """スクリーンショット取得テスト"""
    print("\n[Test 1] Screenshot")
    try:
        response = client.send_command(CMD_SCREENSHOT)
        print(f"  ✓ Received {len(response)} bytes (PNG image)")

        # PNGヘッダ確認
        if response[:8] == b'\x89PNG\r\n\x1a\n':
            print(f"  ✓ Valid PNG header")
        else:
            print(f"  ✗ Invalid PNG header")

    except Exception as e:
        print(f"  ✗ Failed: {e}")


def test_import_file(client: AIDXTestClient):
    """ファイルインポートテスト"""
    print("\n[Test 2] ImportFile")
    try:
        payload = json.dumps({
            "path": "/path/to/test.step",
            "pos": [10, 20, 30],
            "rot": [0, 0, 45]
        }).encode("utf-8")

        response = client.send_command(CMD_IMPORT_FILE, payload)
        result = json.loads(response.decode("utf-8"))
        print(f"  Result: {json.dumps(result, indent=4)}")

        if result.get("success"):
            print(f"  ✓ Import succeeded")
        else:
            print(f"  ✓ Import failed (expected, file doesn't exist): {result.get('error')}")

    except Exception as e:
        print(f"  ✗ Failed: {e}")


def test_get_objects(client: AIDXTestClient):
    """オブジェクト情報取得テスト"""
    print("\n[Test 3] GetObjects")
    try:
        payload = json.dumps({}).encode("utf-8")
        response = client.send_command(CMD_GET_OBJECTS, payload)
        result = json.loads(response.decode("utf-8"))

        objects = result.get("objects", [])
        print(f"  Found {len(objects)} objects")

        for i, obj in enumerate(objects[:3]):  # 最初の3つだけ表示
            print(f"    Object {i+1}: type={obj.get('type')}, name={obj.get('name')}")

        print(f"  ✓ GetObjects succeeded")

    except Exception as e:
        print(f"  ✗ Failed: {e}")


def test_invalid_command(client: AIDXTestClient):
    """無効なコマンドIDテスト"""
    print("\n[Test 4] Invalid Command ID")
    try:
        response = client.send_command(0x9999)
        print(f"  ✗ Should have received error response")
    except RuntimeError as e:
        if "AIDX Error" in str(e):
            print(f"  ✓ Received expected error: {e}")
        else:
            print(f"  ✗ Unexpected error: {e}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")


def main():
    """メイン"""
    print("=" * 60)
    print("AIDX Protocol Test Client")
    print("=" * 60)

    # 接続先
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8109

    client = AIDXTestClient(host, port)

    try:
        # 接続
        client.connect()

        # テスト実行
        test_screenshot(client)
        test_import_file(client)
        test_get_objects(client)
        test_invalid_command(client)

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        sys.exit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
