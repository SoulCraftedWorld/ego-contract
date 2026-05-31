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

## Состав

В начале нормальной сессии должны быть:

```text
SessionStarted
ConfigSnapshotFrame
```

Далее идут realtime frames:

```text
AudioBlock
ImuWindow
CanDecodedValue
CanRawFrame
TrajectoryPoint
GpsFix
TimeStatus
SystemStatus
ImuCalibrationEvent
MarkerEvent
...
SessionEnded
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
- time status;
- system status;
- calibration events;
- markers.

## Current firmware SD recording note

- The ARM firmware writes the same `EgoFrameHeader + payload` stream to SD
  while it streams frames to TCP.
- Default log files are created under `sd:ego/logs/` as
  `ego_YYYYMMDD_HHMMSS.bin` when RTC/GPS time is valid. Before time is valid,
  the fallback name is `ego_mono_<timestamp>.bin`.
- It also writes a sidecar CSV `.index` next to the `.bin` file with:
  `seq,frame_type,t0_ns,t1_ns,file_offset,payload_size,payload_crc32,header_crc32,flags`.
- For a custom binary path, the index path is derived by replacing the extension
  with `.index`, unless an explicit index path is passed to the current minimal
  Control TCP `start` command.
- Firmware creates `sd:ego/logs/` for recordings and `sd:ego/config/` for module
  settings. Automatic cleanup deletes only old `ego_*.bin` logs from
  `sd:ego/logs/` and their matching `.index` files.
- Before recording and then periodically during recording, firmware checks that
  SD free space is at least 1 GiB. If it is lower, it tries to remove the oldest
  completed log file.
- Current minimal Control TCP supports log maintenance:
  `logs`, `log_get <name>`, and `log_delete <ego_*.bin>`. Binary download starts
  with a text header that contains the byte size, then sends exactly that many
  file bytes.
