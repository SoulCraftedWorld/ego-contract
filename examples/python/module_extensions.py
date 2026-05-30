from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket
from typing import BinaryIO, Callable, Dict, Optional

from ego_protocol_packets import (
    EgoFrameHeader,
    FramePayloadType,
    FrameFlags,
    crc32,
)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        data = sock.recv(remaining)
        if not data:
            raise ConnectionError("socket closed while receiving data")
        chunks.append(data)
        remaining -= len(data)
    return b"".join(chunks)


@dataclass(slots=True)
class ReceivedFrame:
    header: EgoFrameHeader
    payload: bytes
    file_offset: int = 0


class DataTcpReceiver:
    def __init__(self, host: str, port: int = 5001) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=5.0)
        self.sock.settimeout(None)

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def read_frame(self) -> ReceivedFrame:
        if self.sock is None:
            raise RuntimeError("receiver is not connected")
        header_bytes = recv_exact(self.sock, EgoFrameHeader.SIZE)
        header = EgoFrameHeader.unpack(header_bytes)
        header.validate_basic()
        payload = recv_exact(self.sock, header.payload_size)
        if crc32(payload) != header.payload_crc32:
            raise ValueError(f"payload CRC mismatch at seq={header.seq}")
        return ReceivedFrame(header=header, payload=payload)


class EgoBinWriter:
    def __init__(self, ego_bin_path: Path, index_path: Path) -> None:
        self.ego_bin_path = ego_bin_path
        self.index_path = index_path
        self.bin_file: Optional[BinaryIO] = None
        self.index_file: Optional[BinaryIO] = None

    def open(self) -> None:
        self.ego_bin_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.bin_file = self.ego_bin_path.open("wb")
        self.index_file = self.index_path.open("w", encoding="utf-8")
        self.index_file.write("seq,frame_type,t0_ns,t1_ns,file_offset,payload_size\n")

    def close(self) -> None:
        if self.bin_file is not None:
            self.bin_file.close()
            self.bin_file = None
        if self.index_file is not None:
            self.index_file.close()
            self.index_file = None

    def write_frame(self, frame: ReceivedFrame) -> None:
        if self.bin_file is None or self.index_file is None:
            raise RuntimeError("writer is not open")
        offset = self.bin_file.tell()
        self.bin_file.write(frame.header.pack())
        self.bin_file.write(frame.payload)
        self.index_file.write(
            f"{frame.header.seq},{frame.header.frame_type},{frame.header.t0_ns},"
            f"{frame.header.t1_ns},{offset},{frame.header.payload_size}\n"
        )


class FrameRouter:
    def __init__(self) -> None:
        self.handlers: Dict[int, Callable[[EgoFrameHeader, bytes], None]] = {}

    def on(self, frame_type: FramePayloadType, handler: Callable[[EgoFrameHeader, bytes], None]) -> None:
        self.handlers[int(frame_type)] = handler

    def route(self, frame: ReceivedFrame) -> None:
        handler = self.handlers.get(frame.header.frame_type)
        if handler is not None:
            handler(frame.header, frame.payload)


class RuntimeRecorder:
    def __init__(self, host: str, output_dir: Path) -> None:
        self.receiver = DataTcpReceiver(host=host, port=5001)
        self.writer = EgoBinWriter(output_dir / "ego.bin", output_dir / "ego.index")

    def run(self, max_frames: int = 0) -> None:
        self.receiver.connect()
        self.writer.open()
        count = 0
        try:
            while True:
                frame = self.receiver.read_frame()
                self.writer.write_frame(frame)
                count += 1
                if max_frames > 0 and count >= max_frames:
                    break
        finally:
            self.writer.close()
            self.receiver.close()


class Mdf4ExportAdapter:
    def __init__(self) -> None:
        self.audio_frames = 0
        self.imu_windows = 0
        self.can_values = 0
        self.trajectory_points = 0
        self.gps_fixes = 0

    def accept(self, header: EgoFrameHeader, payload: bytes) -> None:
        frame_type = FramePayloadType(header.frame_type)
        if frame_type == FramePayloadType.AUDIO_BLOCK:
            self.audio_frames += 1
        elif frame_type == FramePayloadType.IMU_WINDOW:
            self.imu_windows += 1
        elif frame_type == FramePayloadType.CAN_DECODED_VALUE:
            self.can_values += 1
        elif frame_type == FramePayloadType.TRAJECTORY_POINT:
            self.trajectory_points += 1
        elif frame_type == FramePayloadType.GPS_FIX:
            self.gps_fixes += 1

    def summary(self) -> dict[str, int]:
        return {
            "audio_frames": self.audio_frames,
            "imu_windows": self.imu_windows,
            "can_values": self.can_values,
            "trajectory_points": self.trajectory_points,
            "gps_fixes": self.gps_fixes,
        }
