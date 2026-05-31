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
| 1 | `SessionStarted` protobuf, or zero-payload session marker in minimal firmware mode |
| 2 | `ConfigSnapshotFrame` protobuf, or binary text-kv snapshot in minimal firmware mode |
| 100 | `AudioBlockBinaryHeader + raw PCM` in production |
| 101 | `ImuWindowBinaryHeader + ImuSampleBinary[]` in production |
| 102 | `CanDecodedValuePacket` binary in production |
| 103 | `CanRawFramePacket` binary in production |
| 104 | `TrajectoryPointPacket` binary in production |
| 105 | `GpsFixPacket` binary in production |
| 200 | `TimeStatusPacket` binary in production |
| 201 | `SystemStatusPacket` binary in production |
| 202 | `ImuCalibrationEvent` protobuf |
| 203 | `MarkerEvent` protobuf |
| 900 | `SessionEnded` protobuf, or zero-payload final marker in minimal firmware mode |

## Payload encoding

Для metadata/config/status/event payload используется protobuf.

Для высокочастотного аудио допустимы два режима:

| Режим | Описание |
|---|---|
| Prototype | `AudioBlock` protobuf с `pcm_data` |
| Production | компактный бинарный audio block header + raw PCM payload |

Current production data frames use `FrameFlags::PAYLOAD_BINARY`.
Variable metadata/config/session/event frames remain protobuf unless explicitly moved to a fixed binary packet.
Current ARM firmware emits zero-payload `SESSION_STARTED` and `SESSION_ENDED`
markers around the binary data stream until full protobuf session metadata is
enabled on target. The marker timestamp and session id are carried by
`EgoFrameHeader`.
Current ARM firmware also emits `CONFIG_SNAPSHOT` as a binary keyframe:
`ConfigSnapshotBinaryHeader + text_size bytes` of `key=value` effective config
text. The target format remains protobuf `DeviceConfigSnapshot`.

В обоих режимах внешний `EgoFrameHeader` остаётся одинаковым.
