# Описание пакетов данных

## Общий принцип

Data TCP передаёт последовательность `EgoFrameHeader + payload`.

`frame_type` в заголовке определяет, какое protobuf-сообщение или какой бинарный payload находится внутри.

Все временные метки передаются в наносекундах относительно общей временной базы платы.

## SessionStarted

В текущем минимальном режиме ARM firmware отправляет этот фрейм как маркер без
payload. `session_id`, `seq` и временная метка находятся в
`EgoFrameHeader`. Целевой формат для расширенных метаданных сессии остаётся
protobuf.

Первый служебный фрейм после успешного старта сессии.

Содержит:

- `t_ns`;
- `SessionMetadata`;
- `ConfigInventory`.

Назначение: зафиксировать факт начала сессии и связать поток данных с метаданными испытания.

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

Текущий минимальный режим firmware: пока protobuf-кодирование не включено на
плате, `CONFIG_SNAPSHOT` отправляется как бинарный ключевой фрейм с флагами
`FrameFlags::PAYLOAD_BINARY | FrameFlags::PAYLOAD_KEYFRAME`. Формат payload:

```text
ConfigSnapshotBinaryHeader
ASCII/UTF-8 текст key=value, text_size байт
```

Текстовый блок содержит эффективную конфигурацию из `sd:ego/config/effective.cfg`
или значения firmware по умолчанию, если SD-файл конфигурации отсутствует.

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

Правило времени: `t0_ns` — время первого audio-фрейма блока. Время любого сэмпла восстанавливается по `sample_rate_hz` и индексу фрейма внутри блока.

Для production-режима допускается не использовать protobuf `pcm_data`, а передавать raw PCM как payload с тем же внешним `EgoFrameHeader`.

## ImuWindow

Бинарный payload в production-режиме:

- `ImuWindowBinaryHeader` (40 байт): `imu_window_id`, `t0_ns`, `t1_ns`, `odr_hz`, `sample_count`, `sample_size`, `flags`, `reserved0`.
- Далее идут `sample_count` записей `ImuSampleBinary` по 40 байт каждая: `t_ns`, `accel_mps2[3]`, `gyro_rad_s[3]`, `temperature_c`, `flags`.

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

Бинарный payload в production-режиме: один 28-байтный `CanDecodedValuePacket` с полями `t_ns`, `signal_id`, `can_id`, `value`, `quality`, `flags`.

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

Бинарный payload в production-режиме: один 28-байтный `CanRawFramePacket` с полями `t_ns`, `can_id`, `dlc`, `bus`, `flags`, `data[8]`, `reserved0`.

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

Бинарный payload в production-режиме: один 44-байтный `TrajectoryPointPacket` с полями `t_ns`, `loc_x_m`, `loc_y_m`, `loc_z_m`, `yaw_rad`, `pitch_rad`, `roll_rad`, `velocity_mps`, `yaw_rate_rad_s`, `flags`.

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

В текущем минимальном режиме ARM firmware отправляет этот фрейм как финальный
маркер без payload. Финальный маркер ставится в очередь после последних
`TIME_STATUS`/`SYSTEM_STATUS` фреймов и до закрытия файла записи.

Финальный фрейм сессии.

Поля:

- `t_ns`;
- `session_id`;
- `reason`;
- `total_frames`;
- `total_bytes`.
