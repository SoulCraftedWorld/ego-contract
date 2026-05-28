# Контракт сетевого потока EGO

## Назначение

Поток данных передаётся от ADSP-SC589 на бортовой мини-ПК по TCP. Мини-ПК последовательно пишет принятые фреймы в `ego.bin` и строит рядом индекс `ego.index`.

`ego.bin` — это конечный сырой файл сессии, но он состоит из последовательности сетевых фреймов. По сети передаётся не весь файл, а отдельные фреймы.

## TCP-каналы

| Порт | Канал | Назначение |
|---:|---|---|
| 5000 | Control TCP | команды, настройки, старт/стоп, статус |
| 5001 | Data TCP | поток фреймов данных |

ADSP-SC589 работает как TCP-сервер. Мини-ПК подключается как TCP-клиент.

## Data TCP frame

Каждый фрейм в Data TCP имеет фиксированный бинарный заголовок и payload.

```c
#define EGO_FRAME_MAGIC 0x314F4745u /* 'EGO1' little-endian */

typedef struct {
    uint32_t magic;
    uint16_t protocol_ver;
    uint16_t header_size;

    uint32_t frame_type;
    uint32_t flags;

    uint64_t session_id_hi;
    uint64_t session_id_lo;

    uint64_t seq;
    uint64_t t0_ns;
    uint64_t t1_ns;

    uint32_t payload_size;
    uint32_t payload_crc32;
    uint32_t header_crc32;
    uint32_t reserved0;
} EgoFrameHeader;
```

Размер заголовка: 72 байта.

## Правила

| Поле | Правило |
|---|---|
| `magic` | всегда `EGO1` |
| `protocol_ver` | версия бинарного контракта |
| `header_size` | размер `EgoFrameHeader`, сейчас 72 |
| `frame_type` | тип payload из `FrameType` |
| `seq` | общий монотонный счётчик фреймов в сессии |
| `t0_ns` | начало временного диапазона данных |
| `t1_ns` | конец временного диапазона данных |
| `payload_size` | размер payload после заголовка |
| `payload_crc32` | CRC32 payload |
| `header_crc32` | CRC32 заголовка с обнулённым `header_crc32` |

## Типы payload

| frame_type | Payload |
|---:|---|
| 1 | `SessionMetadata` protobuf |
| 2 | `DeviceConfig` protobuf |
| 3 | `AudioConfig` protobuf |
| 4 | `ImuConfig` protobuf |
| 5 | `CanConfig` protobuf |
| 6 | `GpsConfig` protobuf |
| 7 | `VehicleConfig` protobuf |
| 100 | `AudioBlock` protobuf или raw audio block по production-схеме |
| 101 | `ImuWindow` protobuf |
| 102 | `CanDecodedValue` protobuf |
| 103 | `CanRawFrame` protobuf |
| 104 | `TrajectoryPoint` protobuf |
| 105 | `GpsFix` protobuf |
| 200 | `TimeStatus` protobuf |
| 201 | `SystemStatus` protobuf |
| 202 | `ImuCalibrationEvent` protobuf |
| 203 | `MarkerEvent` protobuf |
| 900 | `SessionEnd` protobuf |

## Audio production mode

Для прототипа можно передавать аудио как protobuf `AudioBlock` с полем `pcm_data`.

Для production-режима рекомендуется payload:

```text
AudioBlockFixedHeader + raw PCM bytes
```

Это уменьшает нагрузку на ADSP-SC589 и упрощает запись больших аудиоблоков.
