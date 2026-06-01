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
- запросы и ответы управления
- конфигурации устройства

## Размеры структур

| Структура | Размер, байт |
|---|---:|
| `EgoFrameHeader` | 72 |
| `EgoControlMessageHeader` | 32 |
| `AudioBlockBinaryHeader` | 48 |
| `ImuWindowPacket` | 76 |
| `CanDecodedValuePacket` | 20 |
| `CanRawFramePacket` | 24 |
| `TrajectoryPointPacket` | 52 |
| `GpsFixPacket` | 56 |
| `TimeStatusPacket` | 40 |
| `SystemStatusPacket` | 56 |
| `ImuCalibrationEventPacket` | 44 |

## Правило использования

- Метаданные управления, конфигурации и сессии: protobuf.
- Внешний фрейм Data TCP: всегда `EgoFrameHeader`.
- Audio в production-режиме: `AudioBlockBinaryHeader + raw PCM`.
- IMU в production-режиме: один агрегированный `ImuWindowPacket` с дельтами.
- Малые частые telemetry-пакеты могут передаваться либо protobuf, либо бинарным пакетом из этих файлов.
- `ego.bin` записывает фреймы как есть: `EgoFrameHeader + payload`.
Текущие примечания по бинарному wire-format:

- `CONFIG_SNAPSHOT` в текущем минимальном режиме firmware:
  `ConfigSnapshotBinaryHeader + text_size байт` конфигурации в формате `key=value`.
- `IMU_WINDOW`: один 76-байтный `ImuWindowPacket` с mean/delta полями, без отдельных IMU-сэмплов.
- `CAN_DECODED_VALUE`: один 20-байтный `CanDecodedValuePacket` без `raw_value`, `dlc` и `flags`.
- `CAN_RAW_FRAME`: один 24-байтный `CanRawFramePacket` в формате v1.3.
- `TRAJECTORY_POINT`: один 52-байтный `TrajectoryPointPacket` в формате v1.3, но без `vx/vy/vz`.
