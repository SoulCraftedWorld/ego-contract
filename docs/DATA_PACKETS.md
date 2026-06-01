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

Бинарный payload в production-режиме: один 76-байтный `ImuWindowPacket`.

Содержит агрегированное окно IMU от LSM6DS3, привязанное к аудио-блоку.
Отдельные IMU-сэмплы в поток не передаются, чтобы не расходовать место на
второстепенные данные.

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

Бинарный payload в production-режиме: один 20-байтный `CanDecodedValuePacket` с полями `t_ns`, `value_id`, `can_id`, `value`.

Декодированное значение CAN-сигнала.

Поля:

- `t_ns`;
- `value_id`;
- `can_id`;
- `value`.

Используется для скорости автомобиля, режима АКПП и опционально угла руля.

## CanRawFrame

Бинарный payload в production-режиме: один 24-байтный `CanRawFramePacket` с полями `t_ns`, `can_id`, `dlc`, `is_extended`, `bus_id`, `flags`, `data[8]`.

Сырой CAN-фрейм.

Поля:

- `t_ns`;
- `can_id`;
- `dlc`;
- `is_extended`;
- `bus_id`;
- `flags`;
- `data[8]`.

Назначение: отладка, проверка декодера, возможный offline-пересчёт.

## TrajectoryPoint

Бинарный payload в production-режиме: один 52-байтный `TrajectoryPointPacket` с полями `t_ns`, `x_m`, `y_m`, `z_m`, `yaw_rad`, `pitch_rad`, `roll_rad`, `yaw_rate_rad_s`, `path_s_m`, `vehicle_speed_mps`, `flags`, `reserved0`.

Точка локальной траектории.

Поля:

- `t_ns`;
- `x_m`, `y_m`, `z_m`;
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
