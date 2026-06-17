# Контракт сетевого потока EGO

## Назначение

Поток данных передаётся от ADSP-SC589 на бортовой мини-ПК по TCP. Мини-ПК последовательно пишет принятые фреймы в `ego.bin` и строит рядом индекс `ego.index`.

`ego.bin` — конечный сырой файл сессии, но он состоит из последовательности сетевых фреймов. По сети передаётся не весь файл, а отдельные фреймы.

## TCP-каналы

| Порт | Канал | Назначение |
|---:|---|---|
| 5000 | Control TCP | команды, конфигурации, старт/стоп, статус |
| 5001 | Data TCP | поток фреймов данных |

ADSP-SC589 работает как TCP-сервер. Мини-ПК подключается как TCP-клиент.

## Фрейм Data TCP

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
| `frame_type` | тип payload из `FramePayloadType` |
| `seq` | общий монотонный счётчик фреймов в сессии |
| `t0_ns` | начало временного диапазона данных |
| `t1_ns` | конец временного диапазона данных |
| `payload_size` | размер payload после заголовка |
| `payload_crc32` | CRC32 payload |
| `header_crc32` | CRC32 заголовка с обнулённым `header_crc32` |

## Типы payload

| frame_type | Payload |
|---:|---|
| 1 | `SessionStarted` protobuf или `SessionEventBinaryHeader + metadata_text` в минимальном режиме firmware |
| 2 | `ConfigSnapshotFrame` protobuf или бинарный снимок text-kv в минимальном режиме firmware |
| 100 | `AudioBlockBinaryHeader + raw PCM` в production-режиме |
| 101 | `ImuWindowPacket` в бинарном формате production-режима |
| 102 | `CanDecodedValuePacket` в бинарном формате production-режима |
| 103 | `CanRawFramePacket` в бинарном формате production-режима |
| 104 | `TrajectoryPointPacket` в бинарном формате production-режима |
| 105 | `GpsFixPacket` в бинарном формате production-режима; v1.4 payload 104 байта, первые 56 байт совместимы с v1.3 |
| 200 | `TimeStatusPacket` в бинарном формате production-режима |
| 201 | `SystemStatusPacket` в бинарном формате production-режима |
| 202 | `ImuCalibrationEvent` protobuf |
| 203 | `MarkerEvent` protobuf |
| 900 | `SessionEnded` protobuf или `SessionEventBinaryHeader + metadata_text` в минимальном режиме firmware |

## Кодирование payload

Для payload метаданных, конфигурации, статуса и событий используется protobuf.

Для высокочастотного аудио допустимы два режима:

| Режим | Описание |
|---|---|
| Prototype | `AudioBlock` protobuf с `pcm_data` |
| Production | компактный бинарный заголовок аудиоблока + raw PCM payload |

Текущие фреймы данных production-режима используют `FrameFlags::PAYLOAD_BINARY`.
Переменные фреймы метаданных, конфигурации, сессии и событий остаются protobuf,
если они явно не перенесены в фиксированный бинарный пакет.
Текущая ARM firmware отправляет `SESSION_STARTED` и `SESSION_ENDED` как
бинарные ключевые фреймы `SessionEventBinaryHeader + metadata_text`, пока на
плате не включены полные protobuf-метаданные сессии. Метка времени и session id
также дублируются в `EgoFrameHeader`.
Текущая ARM firmware также отправляет `CONFIG_SNAPSHOT` как бинарный ключевой фрейм:
`ConfigSnapshotBinaryHeader + text_size байт` эффективной конфигурации в формате
`key=value`. Целевой формат остаётся protobuf `DeviceConfigSnapshot`.
В полном protobuf snapshot CAN-декодер может быть задан списком `signals` или
строкой `dbc_text`; каталог `value_id` передаётся в
`SessionMetadata.can_value_descriptions`.

В обоих режимах внешний `EgoFrameHeader` остаётся одинаковым.

Data TCP сервер firmware хранит ограниченное replay-окно последних фреймов в
RAM. Новый клиент после переподключения получает это окно перед текущим
потоком. Окно не является бесконечным журналом; полный поток сохраняется на SD
в `ego_*.bin`, если запись на SD включена и доступна.
