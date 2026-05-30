from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
import struct
import zlib
from typing import ClassVar, Tuple

EGO_FRAME_MAGIC = 0x314F4745  # 'EGO1' little-endian
EGO_CONTROL_MAGIC = 0x434F4745  # 'EGOC' little-endian
EGO_PROTOCOL_VERSION = 2


class FramePayloadType(IntEnum):
    UNSPECIFIED = 0
    SESSION_STARTED = 1
    CONFIG_SNAPSHOT = 2
    AUDIO_BLOCK = 100
    IMU_WINDOW = 101
    CAN_DECODED_VALUE = 102
    CAN_RAW_FRAME = 103
    TRAJECTORY_POINT = 104
    GPS_FIX = 105
    TIME_STATUS = 200
    SYSTEM_STATUS = 201
    IMU_CALIBRATION_EVENT = 202
    MARKER_EVENT = 203
    SESSION_ENDED = 900


class FrameFlags(IntFlag):
    NONE = 0
    PAYLOAD_PROTOBUF = 1 << 0
    PAYLOAD_BINARY = 1 << 1
    PAYLOAD_COMPRESSED = 1 << 2
    PAYLOAD_KEYFRAME = 1 << 3


@dataclass(slots=True)
class EgoFrameHeader:
    magic: int
    protocol_ver: int
    header_size: int
    frame_type: int
    flags: int
    session_id_hi: int
    session_id_lo: int
    seq: int
    t0_ns: int
    t1_ns: int
    payload_size: int
    payload_crc32: int
    header_crc32: int
    reserved0: int = 0

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<IHHIIQQQQQIIII")
    SIZE: ClassVar[int] = STRUCT.size

    def pack(self) -> bytes:
        return self.STRUCT.pack(
            self.magic,
            self.protocol_ver,
            self.header_size,
            self.frame_type,
            self.flags,
            self.session_id_hi,
            self.session_id_lo,
            self.seq,
            self.t0_ns,
            self.t1_ns,
            self.payload_size,
            self.payload_crc32,
            self.header_crc32,
            self.reserved0,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "EgoFrameHeader":
        return cls(*cls.STRUCT.unpack(data))

    def validate_basic(self) -> None:
        if self.magic != EGO_FRAME_MAGIC:
            raise ValueError(f"bad frame magic: 0x{self.magic:08x}")
        if self.header_size != self.SIZE:
            raise ValueError(f"bad frame header size: {self.header_size}")


@dataclass(slots=True)
class EgoControlMessageHeader:
    magic: int
    protocol_ver: int
    header_size: int
    seq: int
    payload_size: int
    payload_crc32: int
    header_crc32: int
    reserved0: int = 0

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<IHHQIIII")
    SIZE: ClassVar[int] = STRUCT.size

    def pack(self) -> bytes:
        return self.STRUCT.pack(
            self.magic,
            self.protocol_ver,
            self.header_size,
            self.seq,
            self.payload_size,
            self.payload_crc32,
            self.header_crc32,
            self.reserved0,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "EgoControlMessageHeader":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class AudioBlockBinaryHeader:
    audio_block_id: int
    t0_ns: int
    t1_ns: int
    sample_rate_hz: int
    channels_count: int
    bytes_per_sample: int
    frames_count: int
    layout: int
    data_size: int
    reserved0: int = 0

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QQQIHHIIII")
    SIZE: ClassVar[int] = STRUCT.size

    def pack(self) -> bytes:
        return self.STRUCT.pack(
            self.audio_block_id,
            self.t0_ns,
            self.t1_ns,
            self.sample_rate_hz,
            self.channels_count,
            self.bytes_per_sample,
            self.frames_count,
            self.layout,
            self.data_size,
            self.reserved0,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "AudioBlockBinaryHeader":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class ImuWindowPacket:
    window_id: int
    t0_ns: int
    t1_ns: int
    sample_count: int
    flags: int
    accel_mean_x_mps2: float
    accel_mean_y_mps2: float
    accel_mean_z_mps2: float
    gyro_mean_x_rad_s: float
    gyro_mean_y_rad_s: float
    gyro_mean_z_rad_s: float
    delta_velocity_x_mps: float
    delta_velocity_y_mps: float
    delta_velocity_z_mps: float
    delta_angle_x_rad: float
    delta_angle_y_rad: float
    delta_angle_z_rad: float

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QQQHHffffffffffff")
    SIZE: ClassVar[int] = STRUCT.size

    def pack(self) -> bytes:
        return self.to_bytes()

    @classmethod
    def unpack(cls, data: bytes) -> "ImuWindowPacket":
        return cls(*cls.STRUCT.unpack(data))

    def as_tuple(self) -> Tuple[object, ...]:
        return (
            self.window_id, self.t0_ns, self.t1_ns, self.sample_count, self.flags,
            self.accel_mean_x_mps2, self.accel_mean_y_mps2, self.accel_mean_z_mps2,
            self.gyro_mean_x_rad_s, self.gyro_mean_y_rad_s, self.gyro_mean_z_rad_s,
            self.delta_velocity_x_mps, self.delta_velocity_y_mps, self.delta_velocity_z_mps,
            self.delta_angle_x_rad, self.delta_angle_y_rad, self.delta_angle_z_rad,
        )

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(*self.as_tuple())


@dataclass(slots=True)
class CanDecodedValuePacket:
    t_ns: int
    value_id: int
    can_id: int
    value: float
    raw_value: int
    flags: int
    dlc: int
    reserved: bytes = b"\x00\x00\x00"

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QII f I I B 3s".replace(" ", ""))
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(self.t_ns, self.value_id, self.can_id, self.value, self.raw_value, self.flags, self.dlc, self.reserved)

    @classmethod
    def unpack(cls, data: bytes) -> "CanDecodedValuePacket":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class CanRawFramePacket:
    t_ns: int
    can_id: int
    dlc: int
    is_extended: int
    bus_id: int
    flags: int
    data: bytes

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QIBBBB8s")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        data8 = self.data[:8].ljust(8, b"\x00")
        return self.STRUCT.pack(self.t_ns, self.can_id, self.dlc, self.is_extended, self.bus_id, self.flags, data8)

    @classmethod
    def unpack(cls, data: bytes) -> "CanRawFramePacket":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class TrajectoryPointPacket:
    t_ns: int
    x_m: float
    y_m: float
    z_m: float
    vx_mps: float
    vy_mps: float
    vz_mps: float
    yaw_rad: float
    pitch_rad: float
    roll_rad: float
    yaw_rate_rad_s: float
    path_s_m: float
    vehicle_speed_mps: float
    flags: int
    reserved0: int = 0

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QffffffffffffII")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(
            self.t_ns, self.x_m, self.y_m, self.z_m, self.vx_mps, self.vy_mps, self.vz_mps,
            self.yaw_rad, self.pitch_rad, self.roll_rad, self.yaw_rate_rad_s,
            self.path_s_m, self.vehicle_speed_mps, self.flags, self.reserved0,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "TrajectoryPointPacket":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class GpsFixPacket:
    t_ns: int
    lat_deg: float
    lon_deg: float
    alt_m: float
    speed_mps: float
    heading_rad: float
    h_acc_m: float
    v_acc_m: float
    fix_type: int
    rtk_status: int
    satellites: int
    reserved0: int
    flags: int

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QdddffffBBBBI")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(
            self.t_ns, self.lat_deg, self.lon_deg, self.alt_m, self.speed_mps,
            self.heading_rad, self.h_acc_m, self.v_acc_m, self.fix_type,
            self.rtk_status, self.satellites, self.reserved0, self.flags,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "GpsFixPacket":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class TimeStatusPacket:
    t_ns: int
    monotonic_ns: int
    utc_offset_ns: int
    time_source: int
    sync_status: int
    estimated_drift_ppm: float
    sync_error_us: float

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QQqIIff")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(self.t_ns, self.monotonic_ns, self.utc_offset_ns, self.time_source, self.sync_status, self.estimated_drift_ppm, self.sync_error_us)

    @classmethod
    def unpack(cls, data: bytes) -> "TimeStatusPacket":
        return cls(*cls.STRUCT.unpack(data))


@dataclass(slots=True)
class SystemStatusPacket:
    t_ns: int
    audio_status: int
    can_status: int
    imu_status: int
    gps_status: int
    network_status: int
    audio_overruns: int
    imu_fifo_overruns: int
    can_rx_errors: int
    dropped_frames: int
    cpu_load_arm: float
    cpu_load_sharc0: float
    cpu_load_sharc1: float

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QIIIIIIIIIfff")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.to_packed_bytes()

    @classmethod
    def unpack(cls, data: bytes) -> "SystemStatusPacket":
        return cls(*cls.STRUCT.unpack(data))

    def as_tuple(self) -> Tuple[object, ...]:
        return (
            self.t_ns, self.audio_status, self.can_status, self.imu_status,
            self.gps_status, self.network_status, self.audio_overruns,
            self.imu_fifo_overruns, self.can_rx_errors, self.dropped_frames,
            self.cpu_load_arm, self.cpu_load_sharc0, self.cpu_load_sharc1,
        )

    def to_packed_bytes(self) -> bytes:
        return self.STRUCT.pack(*self.as_tuple())


@dataclass(slots=True)
class ImuCalibrationEventPacket:
    t_ns: int
    gyro_bias_x_rad_s: float
    gyro_bias_y_rad_s: float
    gyro_bias_z_rad_s: float
    accel_ref_x_mps2: float
    accel_ref_y_mps2: float
    accel_ref_z_mps2: float
    collect_time_s: float
    sample_count: int
    quality_flags: int

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<QfffffffII")
    SIZE: ClassVar[int] = STRUCT.size

    def to_bytes(self) -> bytes:
        return self.STRUCT.pack(
            self.t_ns, self.gyro_bias_x_rad_s, self.gyro_bias_y_rad_s,
            self.gyro_bias_z_rad_s, self.accel_ref_x_mps2, self.accel_ref_y_mps2,
            self.accel_ref_z_mps2, self.collect_time_s, self.sample_count,
            self.quality_flags,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "ImuCalibrationEventPacket":
        return cls(*cls.STRUCT.unpack(data))


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def make_frame_header(
    frame_type: FramePayloadType,
    flags: int,
    session_id_hi: int,
    session_id_lo: int,
    seq: int,
    t0_ns: int,
    t1_ns: int,
    payload: bytes,
) -> EgoFrameHeader:
    return EgoFrameHeader(
        magic=EGO_FRAME_MAGIC,
        protocol_ver=EGO_PROTOCOL_VERSION,
        header_size=EgoFrameHeader.SIZE,
        frame_type=int(frame_type),
        flags=flags,
        session_id_hi=session_id_hi,
        session_id_lo=session_id_lo,
        seq=seq,
        t0_ns=t0_ns,
        t1_ns=t1_ns,
        payload_size=len(payload),
        payload_crc32=crc32(payload),
        header_crc32=0,
        reserved0=0,
    )
