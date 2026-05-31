# Описание пакетов данных

## Общий принцип

Data TCP передаёт последовательность `EgoFrameHeader + payload`.

`frame_type` в заголовке определяет, какой protobuf-сообщение или binary payload находится внутри.

Все временные метки передаются в наносекундах относительно общей временной базы платы.

## SessionStarted

Current minimal ARM firmware mode emits this as a zero-payload marker. The
session id, sequence number, and timestamp are in `EgoFrameHeader`. Full
protobuf metadata remains the target format for richer session description.

Первый служебный frame после успешного старта сессии.

Содержит:

- `t_ns`;
- `SessionMetadata`;
- `ConfigInventory`.

Назначение: зафиксировать факт начала сессии и связать data stream с метаданными испытания.

## ConfigSnapshotFrame

Передаётся сразу после `SessionStarted`.

Содержит полный `DeviceConfigSnapshot`:

- audio config;
- IMU config;
- CAN config;
- GPS config;
- vehicle geometry;
- time config;
- network config;
- inventory/version/crc.

Назначение: сделать `ego.bin` самодостаточным для offline-конвертации в MDF4.

Current minimal firmware mode: until protobuf encoding is enabled on the target,
`CONFIG_SNAPSHOT` is emitted as a binary keyframe with
`FrameFlags::PAYLOAD_BINARY | FrameFlags::PAYLOAD_KEYFRAME`. Payload layout:

```text
ConfigSnapshotBinaryHeader
ASCII/UTF-8 key=value text, text_size bytes
```

The text blob is the effective `sd:ego/config/effective.cfg` content or firmware
defaults if the SD config file is missing.

## AudioBlock

Содержит аудиоблок.

Поля:

- `audio_block_id`;
- `time.t0_ns`;
- `time.t1_ns`;
- `sample_rate_hz`;
- `channels_count`;
- `bytes_per_sample`;
- `frames_count`;
- `layout`;
- `pcm_data` для prototype-режима.

Правило времени: `t0_ns` — время первого audio frame блока. Время любого сэмпла восстанавливается по `sample_rate_hz` и индексу frame внутри блока.

Для production-режима допускается не использовать protobuf `pcm_data`, а передавать raw PCM как payload с тем же внешним `EgoFrameHeader`.

## ImuWindow

Production binary payload:

- `ImuWindowBinaryHeader` (40 bytes): `imu_window_id`, `t0_ns`, `t1_ns`, `odr_hz`, `sample_count`, `sample_size`, `flags`, `reserved0`.
- Followed by `sample_count` records of `ImuSampleBinary` (40 bytes each): `t_ns`, `accel_mps2[3]`, `gyro_rad_s[3]`, `temperature_c`, `flags`.

Содержит окно timestamped IMU-сэмплов от LSM6DS3, привязанное к аудио-блоку.

Поля:

- `imu_window_id`;
- `time.t0_ns`;
- `time.t1_ns`;
- `odr_hz`;
- `sample_count`;
- `sample_size`;
- `flags`;

Назначение: вход для локальной траектории и последующей записи в MDF4.

## CanDecodedValue

Production binary payload: one 28-byte `CanDecodedValuePacket` with `t_ns`, `signal_id`, `can_id`, `value`, `quality`, `flags`.

Декодированное значение CAN-сигнала.

Поля:

- `t_ns`;
- `signal_id`;
- `can_id`;
- `value`;
- `quality`;
- `flags`;

Используется для скорости автомобиля, режима АКПП и опционально угла руля.

## CanRawFrame

Production binary payload: one 28-byte `CanRawFramePacket` with `t_ns`, `can_id`, `dlc`, `bus`, `flags`, `data[8]`, `reserved0`.

Сырой CAN-фрейм.

Поля:

- `t_ns`;
- `can_id`;
- `dlc`;
- `bus`;
- `flags`;
- `data[8]`;
- `reserved0`.

Назначение: отладка, проверка декодера, возможный offline-пересчёт.

## TrajectoryPoint

Production binary payload: one 44-byte `TrajectoryPointPacket` with `t_ns`, `loc_x_m`, `loc_y_m`, `loc_z_m`, `yaw_rad`, `pitch_rad`, `roll_rad`, `velocity_mps`, `yaw_rate_rad_s`, `flags`.

Точка локальной траектории.

Поля:

- `t_ns`;
- `loc_x_m`, `loc_y_m`, `loc_z_m`;
- `yaw_rad`, `pitch_rad`, `roll_rad`;
- `velocity_mps`;
- `yaw_rate_rad_s`;
- `flags`.

Строится на SHARC1 по скорости CAN и гироскопу.

## GpsFix

Внешний GPS/RTK fix, принятый ARM.

Поля:

- `t_ns`;
- `lat_deg`;
- `lon_deg`;
- `alt_m`;
- `speed_mps`;
- `heading_rad`;
- `h_acc_m`;
- `v_acc_m`;
- `fix_type`;
- `satellites`;
- `rtk_status`;
- `flags`.

## TimeStatus

Статус временной базы.

Поля:

- `t_ns`;
- `monotonic_ns`;
- `utc_offset_ns`;
- `time_source`;
- `sync_status`;
- `estimated_drift_ppm`;
- `sync_error_us`.

## SystemStatus

Периодический статус подсистем.

Поля:

- `t_ns`;
- `audio_status`;
- `can_status`;
- `imu_status`;
- `gps_status`;
- `network_status`;
- `audio_overruns`;
- `imu_fifo_overruns`;
- `can_rx_errors`;
- `dropped_frames`;
- `cpu_load_arm`;
- `cpu_load_sharc0`;
- `cpu_load_sharc1`.

## ImuCalibrationEvent

Событие калибровки IMU.

Поля:

- `t_ns`;
- `gyro_bias_x/y/z`;
- `accel_ref_x/y/z`;
- `collect_time_s`;
- `sample_count`;
- `quality_flags`.

## MarkerEvent

Пользовательская или сценарная метка.

Поля:

- `t_ns`;
- `marker_id`;
- `description`;
- `tags`.

## SessionEnded

Current minimal ARM firmware mode emits this as a zero-payload final marker.
The final marker is queued after final time/system status frames and before the
record file is closed.

Финальный frame сессии.

Поля:

- `t_ns`;
- `session_id`;
- `reason`;
- `total_frames`;
- `total_bytes`.
