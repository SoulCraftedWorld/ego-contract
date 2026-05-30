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
- `ImuWindowPacket`
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
| `ImuWindowPacket` | 76 |
| `CanDecodedValuePacket` | 32 |
| `CanRawFramePacket` | 24 |
| `TrajectoryPointPacket` | 64 |
| `GpsFixPacket` | 56 |
| `TimeStatusPacket` | 40 |
| `SystemStatusPacket` | 56 |
| `ImuCalibrationEventPacket` | 44 |

## Правило использования

- Control/config/session metadata: protobuf.
- Data TCP outer frame: всегда `EgoFrameHeader`.
- Audio production: `AudioBlockBinaryHeader + raw PCM`.
- Малые частые telemetry packets могут передаваться либо protobuf, либо binary packet из этих файлов.
- `ego.bin` записывает фреймы как есть: `EgoFrameHeader + payload`.
