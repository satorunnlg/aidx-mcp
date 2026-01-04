"""AIDXプロトコル実装（TCPサーバー側 / Fusion 360）"""
import socket
import struct
import threading
import queue
import json
from typing import Optional, Callable

# プロトコル定数
AIDX_MAGIC = 0x41494458
CHUNK_SIZE = 64 * 1024  # 64KB
RECV_TIMEOUT = 30  # 秒

# CommandID
CMD_ERROR = 0xFFFF

# Flags (ChunkState: bit 0-1)
FLAG_SINGLE = 0x0000
FLAG_START = 0x0001
FLAG_MIDDLE = 0x0002
FLAG_END = 0x0003

# エラーコード
ERR_PARSE_ERROR = 0x1000
ERR_INVALID_COMMAND = 0x1001
ERR_INVALID_PAYLOAD = 0x1002
ERR_INVALID_SEQUENCE = 0x1003
ERR_EXECUTION_ERROR = 0x2000
ERR_TIMEOUT = 0x3000


class AIDXProtocolError(Exception):
    """AIDXプロトコルエラー"""
    def __init__(self, code: int, message: str, cmd_id: int = 0, seq: int = 0):
        super().__init__(message)
        self.code = code
        self.message = message
        self.cmd_id = cmd_id
        self.seq = seq


class AIDXServer:
    """AIDXプロトコルサーバー（分割送受信対応）"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8109):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # コマンドディスパッチャ（CommandID → Callable[[bytes], bytes]）
        self.command_handlers: dict[int, Callable[[bytes], bytes]] = {}

        # 分割受信バッファ（Sequence → {total_size, chunks, received_size}）
        self._recv_buffers: dict[int, dict] = {}

    def register_command(self, cmd_id: int, handler: Callable[[bytes], bytes]):
        """コマンドハンドラを登録"""
        self.command_handlers[cmd_id] = handler

    def start(self):
        """TCPサーバーを起動（バックグラウンドスレッド）"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """TCPサーバーを停止"""
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=5)

    def _server_loop(self):
        """サーバーループ（バックグラウンドスレッドで実行）"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)  # accept()のタイムアウト

        while self.running:
            try:
                # クライアント接続待機
                self.client_socket, addr = self.server_socket.accept()
                self.client_socket.settimeout(RECV_TIMEOUT)

                # リクエスト処理ループ
                while self.running:
                    try:
                        self._handle_request()
                    except socket.timeout:
                        # タイムアウトは継続（接続維持）
                        continue
                    except AIDXProtocolError as e:
                        # プロトコルエラーはエラーレスポンス送信
                        self._send_error_response(e)
                    except Exception as e:
                        # 予期しないエラーは接続切断
                        break

            except socket.timeout:
                # accept()タイムアウトは継続
                continue
            except Exception as e:
                # 接続エラーは継続（再接続待機）
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                    self.client_socket = None

    def _handle_request(self):
        """1リクエストの処理"""
        # ヘッダ受信（16バイト）
        header_data = self._recv_exact(16)

        # ヘッダ解析
        magic, cmd_id, flags, seq, reserved, payload_size, total_size = struct.unpack(
            "<IHHHHII", header_data
        )

        # Magic確認
        if magic != AIDX_MAGIC:
            raise AIDXProtocolError(
                ERR_PARSE_ERROR,
                f"Invalid magic: expected 0x{AIDX_MAGIC:08X}, got 0x{magic:08X}",
                cmd_id,
                seq
            )

        # ペイロード受信
        payload = self._recv_exact(payload_size) if payload_size > 0 else b""

        # ChunkState取得（Flags bit 0-1）
        chunk_state = flags & 0x0003

        # 分割受信処理
        if chunk_state == FLAG_SINGLE:
            # 単一パケット
            full_payload = payload
        else:
            # 分割パケット
            full_payload = self._handle_chunked_receive(
                seq, chunk_state, payload, total_size
            )
            if full_payload is None:
                # まだ全チャンク受信していない
                return

        # コマンド実行
        try:
            if cmd_id not in self.command_handlers:
                raise AIDXProtocolError(
                    ERR_INVALID_COMMAND,
                    f"Unknown command: 0x{cmd_id:04X}",
                    cmd_id,
                    seq
                )

            handler = self.command_handlers[cmd_id]
            response_payload = handler(full_payload)

            # レスポンス送信（分割送信対応）
            self.send_response(cmd_id, seq, response_payload)

        except AIDXProtocolError:
            raise
        except Exception as e:
            raise AIDXProtocolError(
                ERR_EXECUTION_ERROR,
                str(e),
                cmd_id,
                seq
            )

    def _handle_chunked_receive(
        self, seq: int, chunk_state: int, payload: bytes, total_size: int
    ) -> Optional[bytes]:
        """
        分割受信処理

        Returns:
            完全なペイロード（全チャンク受信完了時）、またはNone（受信中）
        """
        if chunk_state == FLAG_START:
            # 開始: バッファ初期化
            self._recv_buffers[seq] = {
                "total_size": total_size,
                "chunks": [payload],
                "received_size": len(payload)
            }
            return None

        elif chunk_state == FLAG_MIDDLE or chunk_state == FLAG_END:
            # 中間/終了: バッファに追加
            if seq not in self._recv_buffers:
                raise AIDXProtocolError(
                    ERR_INVALID_SEQUENCE,
                    f"Missing start chunk for sequence {seq}",
                    0,
                    seq
                )

            buf = self._recv_buffers[seq]

            # TotalSize確認
            if buf["total_size"] != total_size:
                raise AIDXProtocolError(
                    ERR_INVALID_SEQUENCE,
                    f"TotalSize mismatch: expected {buf['total_size']}, got {total_size}",
                    0,
                    seq
                )

            buf["chunks"].append(payload)
            buf["received_size"] += len(payload)

            if chunk_state == FLAG_END:
                # 終了: 全チャンク結合
                full_payload = b"".join(buf["chunks"])

                # サイズ確認
                if len(full_payload) != total_size:
                    raise AIDXProtocolError(
                        ERR_INVALID_SEQUENCE,
                        f"Total size mismatch: expected {total_size}, got {len(full_payload)}",
                        0,
                        seq
                    )

                # バッファクリア
                del self._recv_buffers[seq]

                return full_payload
            else:
                # 中間: まだ受信中
                return None

        else:
            raise AIDXProtocolError(
                ERR_PARSE_ERROR,
                f"Invalid chunk state: {chunk_state}",
                0,
                seq
            )

    def send_response(self, cmd_id: int, seq: int, payload: bytes):
        """レスポンス送信（64KB超過時は自動分割）"""
        total_size = len(payload)

        if total_size <= CHUNK_SIZE:
            # 単一パケット
            self._send_packet(cmd_id, seq, FLAG_SINGLE, payload, total_size)
        else:
            # 分割送信
            offset = 0
            while offset < total_size:
                chunk_size = min(CHUNK_SIZE, total_size - offset)
                chunk = payload[offset:offset + chunk_size]

                # Flags算出
                if offset == 0:
                    flags = FLAG_START
                elif offset + chunk_size >= total_size:
                    flags = FLAG_END
                else:
                    flags = FLAG_MIDDLE

                self._send_packet(cmd_id, seq, flags, chunk, total_size)
                offset += chunk_size

    def _send_packet(self, cmd_id: int, seq: int, flags: int, payload: bytes, total_size: int):
        """単一パケット送信"""
        header = struct.pack(
            "<IHHHHII",
            AIDX_MAGIC,
            cmd_id,
            flags,
            seq,
            0x0000,  # Reserved
            len(payload),
            total_size
        )

        self.client_socket.sendall(header + payload)

    def _send_error_response(self, error: AIDXProtocolError):
        """エラーレスポンス送信"""
        error_payload = json.dumps({
            "ErrorCode": error.code,
            "Message": error.message,
            "OriginalCommandID": error.cmd_id,
            "OriginalSequence": error.seq
        }).encode("utf-8")

        try:
            self.send_response(CMD_ERROR, error.seq, error_payload)
        except:
            # エラーレスポンス送信失敗は無視（接続切断）
            pass

    def _recv_exact(self, size: int) -> bytes:
        """指定バイト数を正確に受信"""
        data = b""
        while len(data) < size:
            chunk = self.client_socket.recv(size - len(data))
            if not chunk:
                raise AIDXProtocolError(
                    ERR_PARSE_ERROR,
                    f"Connection closed while receiving {size} bytes (got {len(data)} bytes)"
                )
            data += chunk
        return data
