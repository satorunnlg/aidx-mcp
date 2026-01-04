"""AIDXプロトコル実装（TCPクライアント）"""
import asyncio
import struct
import json
from typing import Optional
from config import (
    AIDX_HOST,
    AIDX_PORT,
    AIDX_MAGIC,
    CHUNK_SIZE,
    RECV_TIMEOUT,
    CMD_ERROR,
)


class AIDXProtocolError(Exception):
    """AIDXプロトコルエラー"""
    def __init__(self, code: int, message: str, cmd_id: int = 0, seq: int = 0):
        super().__init__(message)
        self.code = code
        self.cmd_id = cmd_id
        self.seq = seq


class AIDXClient:
    """AIDXプロトコルクライアント"""

    def __init__(self, host: str = AIDX_HOST, port: int = AIDX_PORT):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._seq_counter = 0
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """CADアドインへ接続"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )

    async def close(self) -> None:
        """接続を閉じる"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    def _next_seq(self) -> int:
        """次のSequence番号を取得（スレッドセーフ）"""
        seq = self._seq_counter
        self._seq_counter = (self._seq_counter + 1) % 65536
        return seq

    async def send_command(
        self,
        cmd_id: int,
        payload: bytes = b"",
        seq: Optional[int] = None
    ) -> bytes:
        """
        コマンドを送信しレスポンスを受信（分割送信対応）

        Args:
            cmd_id: コマンドID
            payload: ペイロードデータ
            seq: Sequence番号（省略時は自動採番）

        Returns:
            レスポンスのペイロード

        Raises:
            AIDXProtocolError: プロトコルエラー
        """
        if seq is None:
            seq = self._next_seq()

        async with self._lock:
            total_size = len(payload)

            if total_size <= CHUNK_SIZE:
                # 単一パケット送信
                header = struct.pack(
                    "<IHHHHII",
                    AIDX_MAGIC,      # Magic (4)
                    cmd_id,          # CommandID (2)
                    0x0000,          # Flags (2) - 単一パケット
                    seq,             # Sequence (2)
                    0x0000,          # Reserved (2)
                    len(payload),    # PayloadSize (4)
                    len(payload),    # TotalSize (4)
                )

                self.writer.write(header + payload)
                await self.writer.drain()
            else:
                # 分割送信
                await self._send_chunked(cmd_id, seq, payload, total_size)

            # レスポンス受信
            return await self._recv_response(seq)

    async def _send_chunked(self, cmd_id: int, seq: int, payload: bytes, total_size: int):
        """
        ペイロードを分割送信

        Args:
            cmd_id: コマンドID
            seq: Sequence番号
            payload: ペイロードデータ
            total_size: 総データサイズ
        """
        offset = 0
        while offset < total_size:
            chunk_size = min(CHUNK_SIZE, total_size - offset)
            chunk = payload[offset:offset + chunk_size]

            # Flags算出（bit 0-1: ChunkState）
            if offset == 0:
                flags = 0x0001  # 開始
            elif offset + chunk_size >= total_size:
                flags = 0x0003  # 終了
            else:
                flags = 0x0002  # 中間

            # ヘッダ構築
            header = struct.pack(
                "<IHHHHII",
                AIDX_MAGIC,
                cmd_id,
                flags,
                seq,
                0x0000,
                len(chunk),
                total_size
            )

            self.writer.write(header + chunk)
            await self.writer.drain()

            offset += chunk_size

    async def _recv_response(self, expected_seq: int) -> bytes:
        """
        レスポンスを受信（分割受信対応）

        Args:
            expected_seq: 期待するSequence番号

        Returns:
            レスポンスペイロード

        Raises:
            AIDXProtocolError: エラーレスポンス受信時
        """
        # ヘッダ受信（16バイト）
        header_data = await asyncio.wait_for(
            self.reader.readexactly(16),
            timeout=RECV_TIMEOUT
        )

        # ヘッダ解析
        magic, cmd_id, flags, seq, reserved, payload_size, total_size = struct.unpack(
            "<IHHHHII", header_data
        )

        # Magic確認
        if magic != AIDX_MAGIC:
            raise AIDXProtocolError(
                0x1000,
                f"Invalid magic: {magic:#x}",
                cmd_id,
                seq
            )

        # Sequence確認
        if seq != expected_seq:
            raise AIDXProtocolError(
                0x1003,
                f"Sequence mismatch: expected {expected_seq}, got {seq}",
                cmd_id,
                seq
            )

        # ペイロード受信
        payload = await asyncio.wait_for(
            self.reader.readexactly(payload_size),
            timeout=RECV_TIMEOUT
        )

        # ChunkState取得（Flags bit 0-1）
        chunk_state = flags & 0x0003

        # 分割受信チェック
        if chunk_state == 0x0000:
            # 単一パケット
            full_payload = payload
        else:
            # 分割受信
            full_payload = await self._recv_chunked(
                expected_seq, chunk_state, payload, total_size, cmd_id
            )

        # エラーレスポンスチェック
        if cmd_id == CMD_ERROR:
            error_data = json.loads(full_payload.decode("utf-8"))
            raise AIDXProtocolError(
                error_data["ErrorCode"],
                error_data["Message"],
                error_data["OriginalCommandID"],
                error_data["OriginalSequence"]
            )

        return full_payload

    async def _recv_chunked(
        self,
        expected_seq: int,
        initial_state: int,
        initial_payload: bytes,
        total_size: int,
        expected_cmd_id: int
    ) -> bytes:
        """
        分割レスポンスを受信して再構築

        Args:
            expected_seq: 期待するSequence番号
            initial_state: 最初のチャンクのChunkState
            initial_payload: 最初のチャンクのペイロード
            total_size: 総データサイズ
            expected_cmd_id: 期待するCommandID

        Returns:
            再構築された完全なペイロード

        Raises:
            AIDXProtocolError: プロトコルエラー
        """
        if initial_state != 0x0001:
            raise AIDXProtocolError(
                0x1003,
                f"Expected chunk start (0x01), got {initial_state:#x}",
                expected_cmd_id,
                expected_seq
            )

        # バッファ初期化
        chunks = [initial_payload]
        received_size = len(initial_payload)

        # 残りのチャンクを受信
        while True:
            # ヘッダ受信
            header_data = await asyncio.wait_for(
                self.reader.readexactly(16),
                timeout=RECV_TIMEOUT
            )

            # ヘッダ解析
            magic, cmd_id, flags, seq, reserved, payload_size, chunk_total_size = struct.unpack(
                "<IHHHHII", header_data
            )

            # Magic確認
            if magic != AIDX_MAGIC:
                raise AIDXProtocolError(
                    0x1000,
                    f"Invalid magic in chunk: {magic:#x}",
                    cmd_id,
                    seq
                )

            # Sequence確認
            if seq != expected_seq:
                raise AIDXProtocolError(
                    0x1003,
                    f"Sequence mismatch in chunk: expected {expected_seq}, got {seq}",
                    cmd_id,
                    seq
                )

            # CommandID確認
            if cmd_id != expected_cmd_id:
                raise AIDXProtocolError(
                    0x1003,
                    f"CommandID mismatch in chunk: expected {expected_cmd_id:#x}, got {cmd_id:#x}",
                    cmd_id,
                    seq
                )

            # TotalSize確認
            if chunk_total_size != total_size:
                raise AIDXProtocolError(
                    0x1003,
                    f"TotalSize mismatch in chunk: expected {total_size}, got {chunk_total_size}",
                    cmd_id,
                    seq
                )

            # ペイロード受信
            payload = await asyncio.wait_for(
                self.reader.readexactly(payload_size),
                timeout=RECV_TIMEOUT
            )

            chunks.append(payload)
            received_size += len(payload)

            # ChunkState確認
            chunk_state = flags & 0x0003

            if chunk_state == 0x0003:
                # 終了チャンク
                break
            elif chunk_state == 0x0002:
                # 中間チャンク、継続
                continue
            else:
                raise AIDXProtocolError(
                    0x1003,
                    f"Invalid chunk state in middle: {chunk_state:#x}",
                    cmd_id,
                    seq
                )

        # 全チャンク結合
        full_payload = b"".join(chunks)

        # サイズ確認
        if len(full_payload) != total_size:
            raise AIDXProtocolError(
                0x1003,
                f"Total size mismatch after reassembly: expected {total_size}, got {len(full_payload)}",
                expected_cmd_id,
                expected_seq
            )

        return full_payload

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
