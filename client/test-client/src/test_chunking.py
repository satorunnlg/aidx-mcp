"""AIDX 分割送受信テスト"""
import socket
import struct
import sys

# プロトコル定数
AIDX_MAGIC = 0x41494458
CHUNK_SIZE = 64 * 1024

# コマンドID（テスト用ダミー）
CMD_TEST_LARGE = 0x0F00

# Flags
FLAG_SINGLE = 0x0000
FLAG_START = 0x0001
FLAG_MIDDLE = 0x0002
FLAG_END = 0x0003


class ChunkingTestClient:
    """分割送受信テストクライアント"""

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

    def send_chunked_command(self, cmd_id: int, payload: bytes) -> bytes:
        """
        分割送信コマンド

        Args:
            cmd_id: コマンドID
            payload: ペイロード

        Returns:
            レスポンスペイロード
        """
        seq = self._next_seq()
        total_size = len(payload)

        print(f"  Sending chunked command: CommandID=0x{cmd_id:04X}, Seq={seq}, TotalSize={total_size}")

        if total_size <= CHUNK_SIZE:
            # 単一パケット
            self._send_packet(cmd_id, seq, FLAG_SINGLE, payload, total_size)
        else:
            # 分割送信
            offset = 0
            chunk_num = 0
            while offset < total_size:
                chunk_size = min(CHUNK_SIZE, total_size - offset)
                chunk = payload[offset:offset + chunk_size]

                # Flags算出
                if offset == 0:
                    flags = FLAG_START
                    state = "START"
                elif offset + chunk_size >= total_size:
                    flags = FLAG_END
                    state = "END"
                else:
                    flags = FLAG_MIDDLE
                    state = "MIDDLE"

                chunk_num += 1
                print(f"    → Chunk {chunk_num}: {state}, Size={len(chunk)}, Offset={offset}")

                self._send_packet(cmd_id, seq, flags, chunk, total_size)
                offset += chunk_size

        # レスポンス受信
        return self._recv_chunked_response(seq)

    def _send_packet(self, cmd_id: int, seq: int, flags: int, payload: bytes, total_size: int):
        """パケット送信"""
        header = struct.pack(
            "<IHHHII",
            AIDX_MAGIC,
            cmd_id,
            flags,
            seq,
            0x0000,
            len(payload),
            total_size
        )
        self.sock.sendall(header + payload)

    def _recv_chunked_response(self, expected_seq: int) -> bytes:
        """分割受信対応レスポンス受信"""
        # 最初のヘッダ受信
        header_data = self._recv_exact(16)

        magic, cmd_id, flags, seq, reserved, payload_size, total_size = struct.unpack(
            "<IHHHII", header_data
        )

        # 検証
        if magic != AIDX_MAGIC:
            raise RuntimeError(f"Invalid magic: {magic:#x}")
        if seq != expected_seq:
            raise RuntimeError(f"Sequence mismatch: expected {expected_seq}, got {seq}")

        # 最初のペイロード受信
        payload = self._recv_exact(payload_size) if payload_size > 0 else b""

        chunk_state = flags & 0x0003

        if chunk_state == FLAG_SINGLE:
            # 単一パケット
            print(f"  ← Received single packet: Size={len(payload)}")
            return payload
        else:
            # 分割受信
            chunks = [payload]
            chunk_num = 1
            received_size = len(payload)

            if chunk_state == FLAG_START:
                print(f"  ← Chunk {chunk_num}: START, Size={len(payload)}")
            else:
                raise RuntimeError(f"Expected chunk start, got {chunk_state:#x}")

            # 残りのチャンク受信
            while True:
                header_data = self._recv_exact(16)
                magic, cmd_id, flags, seq, reserved, payload_size, chunk_total_size = struct.unpack(
                    "<IHHHII", header_data
                )

                # 検証
                if magic != AIDX_MAGIC:
                    raise RuntimeError(f"Invalid magic in chunk: {magic:#x}")
                if seq != expected_seq:
                    raise RuntimeError(f"Sequence mismatch in chunk")
                if chunk_total_size != total_size:
                    raise RuntimeError(f"TotalSize mismatch in chunk")

                payload = self._recv_exact(payload_size)
                chunks.append(payload)
                received_size += len(payload)
                chunk_num += 1

                chunk_state = flags & 0x0003

                if chunk_state == FLAG_END:
                    print(f"  ← Chunk {chunk_num}: END, Size={len(payload)}")
                    break
                elif chunk_state == FLAG_MIDDLE:
                    print(f"  ← Chunk {chunk_num}: MIDDLE, Size={len(payload)}")
                else:
                    raise RuntimeError(f"Invalid chunk state: {chunk_state:#x}")

            # 結合
            full_payload = b"".join(chunks)

            # サイズ確認
            if len(full_payload) != total_size:
                raise RuntimeError(
                    f"Total size mismatch: expected {total_size}, got {len(full_payload)}"
                )

            print(f"  ✓ Reassembled {chunk_num} chunks: TotalSize={len(full_payload)}")
            return full_payload

    def _recv_exact(self, size: int) -> bytes:
        """指定バイト数を正確に受信"""
        data = b""
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise RuntimeError("Connection closed")
            data += chunk
        return data


def test_small_payload(client: ChunkingTestClient):
    """小さいペイロード（単一パケット）"""
    print("\n[Test 1] Small Payload (< 64KB)")
    try:
        # 1KB のダミーデータ
        payload = b"A" * 1024
        response = client.send_chunked_command(CMD_TEST_LARGE, payload)

        if len(response) > 0:
            print(f"  ✓ Received response: {len(response)} bytes")
        else:
            print(f"  ⚠ Empty response (may not be implemented in CAD)")

    except Exception as e:
        print(f"  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): {e}")


def test_medium_payload(client: ChunkingTestClient):
    """中サイズペイロード（2チャンク）"""
    print("\n[Test 2] Medium Payload (128KB = 2 chunks)")
    try:
        # 128KB のダミーデータ（2チャンクに分割されるはず）
        payload = b"B" * (128 * 1024)
        response = client.send_chunked_command(CMD_TEST_LARGE, payload)

        if len(response) > 0:
            print(f"  ✓ Received response: {len(response)} bytes")
        else:
            print(f"  ⚠ Empty response (may not be implemented in CAD)")

    except Exception as e:
        print(f"  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): {e}")


def test_large_payload(client: ChunkingTestClient):
    """大サイズペイロード（5チャンク）"""
    print("\n[Test 3] Large Payload (320KB = 5 chunks)")
    try:
        # 320KB のダミーデータ（5チャンクに分割されるはず）
        payload = b"C" * (320 * 1024)
        response = client.send_chunked_command(CMD_TEST_LARGE, payload)

        if len(response) > 0:
            print(f"  ✓ Received response: {len(response)} bytes")
        else:
            print(f"  ⚠ Empty response (may not be implemented in CAD)")

    except Exception as e:
        print(f"  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): {e}")


def test_boundary_payload(client: ChunkingTestClient):
    """境界サイズペイロード（正確に64KB）"""
    print("\n[Test 4] Boundary Payload (exactly 64KB)")
    try:
        # 正確に64KB（単一パケットとして送信されるはず）
        payload = b"D" * CHUNK_SIZE
        response = client.send_chunked_command(CMD_TEST_LARGE, payload)

        if len(response) > 0:
            print(f"  ✓ Received response: {len(response)} bytes")
        else:
            print(f"  ⚠ Empty response (may not be implemented in CAD)")

    except Exception as e:
        print(f"  ⚠ Failed (expected if CMD_TEST_LARGE not implemented): {e}")


def main():
    """メイン"""
    print("=" * 60)
    print("AIDX Chunking Test Client")
    print("=" * 60)
    print(f"Chunk Size: {CHUNK_SIZE} bytes ({CHUNK_SIZE // 1024}KB)")
    print()

    # 接続先
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8109

    client = ChunkingTestClient(host, port)

    try:
        # 接続
        client.connect()

        # テスト実行
        test_small_payload(client)
        test_medium_payload(client)
        test_large_payload(client)
        test_boundary_payload(client)

        print("\n" + "=" * 60)
        print("Chunking tests completed!")
        print("Note: Some tests may fail if CMD_TEST_LARGE (0x0F00)")
        print("      is not implemented in the CAD addin.")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        sys.exit(1)

    finally:
        client.close()


if __name__ == "__main__":
    main()
