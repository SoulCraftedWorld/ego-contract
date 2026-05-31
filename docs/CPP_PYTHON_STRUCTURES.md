# C++ и Python структуры пакетов

Для интеграции без protobuf runtime в высокочастотных участках добавлены два файла:

| Язык | Файл                                       |
|---|--------------------------------------------|
| C++ | `headers/include/ego_protocol_packets.hpp` |
| Python | `headers/python/ego_protocol_packets.py`           |

Они описывают фиксированные бинарные структуры:

- `EgoFrameHeader`
- `EgoControlMessageHeader`
- `AudioBlockBinaryHeader`
- `ImuSampleBinary`
- `ImuWindowBinaryHeader` / `ImuWindowPacket`
- `CanDecodedValuePacket`
- `CanRawFramePacket`
- `TrajectoryPointPacket`
- `GpsFixPacket`
- `TimeStatusPacket`
- `SystemStatusPacket`
- `ImuCalibrationEventPacket`

Строковые и переменные данные остаются в protobuf:

- `SessionStarted`
- `ConfigSnapshotFrame`
- `MarkerEvent`
- `SessionEnded`
- control request/response
- конфигурации устройства

## Размеры структур

| Структура | Размер, байт |
|---|---:|
| `EgoFrameHeader` | 72 |
| `EgoControlMessageHeader` | 32 |
| `AudioBlockBinaryHeader` | 48 |
| `ImuSampleBinary` | 40 |
| `ImuWindowBinaryHeader` / `ImuWindowPacket` | 40 |
| `CanDecodedValuePacket` | 28 |
| `CanRawFramePacket` | 28 |
| `TrajectoryPointPacket` | 44 |
| `GpsFixPacket` | 56 |
| `TimeStatusPacket` | 40 |
| `SystemStatusPacket` | 56 |
| `ImuCalibrationEventPacket` | 44 |

## Правило использования

- Control/config/session metadata: protobuf.
- Data TCP outer frame: всегда `EgoFrameHeader`.
- Audio production: `AudioBlockBinaryHeader + raw PCM`.
- IMU production: `ImuWindowBinaryHeader + sample_count * ImuSampleBinary`.
- Малые частые telemetry packets могут передаваться либо protobuf, либо binary packet из этих файлов.
- `ego.bin` записывает фреймы как есть: `EgoFrameHeader + payload`.
Current binary wire-format notes:

- `IMU_WINDOW`: `ImuWindowBinaryHeader + sample_count * ImuSampleBinary`.
- `CAN_DECODED_VALUE`: one 28-byte `CanDecodedValuePacket`.
- `CAN_RAW_FRAME`: one 28-byte `CanRawFramePacket`.
- `TRAJECTORY_POINT`: one 44-byte `TrajectoryPointPacket`.
