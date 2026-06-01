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
- запросы и ответы управления
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

- Метаданные управления, конфигурации и сессии: protobuf.
- Внешний фрейм Data TCP: всегда `EgoFrameHeader`.
- Audio в production-режиме: `AudioBlockBinaryHeader + raw PCM`.
- IMU в production-режиме: `ImuWindowBinaryHeader + sample_count * ImuSampleBinary`.
- Малые частые telemetry-пакеты могут передаваться либо protobuf, либо бинарным пакетом из этих файлов.
- `ego.bin` записывает фреймы как есть: `EgoFrameHeader + payload`.
Текущие примечания по бинарному wire-format:

- `CONFIG_SNAPSHOT` в текущем минимальном режиме firmware:
  `ConfigSnapshotBinaryHeader + text_size байт` конфигурации в формате `key=value`.
- `IMU_WINDOW`: `ImuWindowBinaryHeader + sample_count * ImuSampleBinary`.
- `CAN_DECODED_VALUE`: один 28-байтный `CanDecodedValuePacket`.
- `CAN_RAW_FRAME`: один 28-байтный `CanRawFramePacket`.
- `TRAJECTORY_POINT`: один 44-байтный `TrajectoryPointPacket`.
