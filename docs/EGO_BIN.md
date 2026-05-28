# Формат `ego.bin`

`ego.bin` — append-only файл, который формируется на мини-ПК из Data TCP фреймов.

## Запись

Мини-ПК пишет в файл каждый принятый фрейм без изменения:

```text
EgoFrameHeader
payload bytes
EgoFrameHeader
payload bytes
...
```

## Индекс

Рядом рекомендуется создавать `ego.index`.

Минимальная запись индекса:

```c
typedef struct {
    uint64_t seq;
    uint32_t frame_type;
    uint32_t payload_size;
    uint64_t t0_ns;
    uint64_t t1_ns;
    uint64_t file_offset;
} EgoIndexRecord;
```

## Конвертация в MDF4

Offline-конвертер читает:

```text
ego.bin + ego.index -> MDF4
```

MDF4 должен получить отдельные группы каналов:

- audio;
- IMU;
- CAN decoded;
- CAN raw;
- trajectory;
- GPS;
- system status;
- calibration events.
