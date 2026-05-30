# Описание пакетов данных

## Общий принцип

Data TCP передаёт последовательность `EgoFrameHeader + payload`.

`frame_type` в заголовке определяет, какой protobuf-сообщение или binary payload находится внутри.

Все временные метки передаются в наносекундах относительно общей временной базы платы.

## SessionStarted

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

Содержит агрегированное окно IMU от LSM6DS3.

Поля:

- `window_id`;
- `time.t0_ns`;
- `time.t1_ns`;
- `sample_count`;
- `flags`;
- среднее ускорение XYZ;
- средняя угловая скорость XYZ;
- интегральное приращение скорости XYZ;
- интегральное приращение угла XYZ.

Назначение: вход для локальной траектории и последующей записи в MDF4.

## CanDecodedValue

Декодированное значение CAN-сигнала.

Поля:

- `t_ns`;
- `value_id`;
- `can_id`;
- `value`;
- `raw_value`;
- `flags`;
- `dlc`.

Используется для скорости автомобиля, режима АКПП и опционально угла руля.

## CanRawFrame

Сырой CAN-фрейм.

Поля:

- `t_ns`;
- `can_id`;
- `dlc`;
- `is_extended`;
- `bus_id`;
- `flags`;
- `data`.

Назначение: отладка, проверка декодера, возможный offline-пересчёт.

## TrajectoryPoint

Точка локальной траектории.

Поля:

- `t_ns`;
- `x_m`, `y_m`, `z_m`;
- `vx_mps`, `vy_mps`, `vz_mps`;
- `yaw_rad`, `pitch_rad`, `roll_rad`;
- `yaw_rate_rad_s`;
- `path_s_m`;
- `vehicle_speed_mps`;
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

Финальный frame сессии.

Поля:

- `t_ns`;
- `session_id`;
- `reason`;
- `total_frames`;
- `total_bytes`.
