# Примеры надстроек по модулям

Документ описывает прикладные надстройки поверх базового protobuf/binary контракта. Надстройка — это небольшой слой проекта, который использует общий контракт, но решает задачу конкретного модуля.

## Сводная таблица

| Модуль | Надстройка | Назначение | Основной вход | Основной выход |
|---|---|---|---|---|
| Control TCP client | `ConfigUploader` | Загрузка и сохранение конфигураций на плате | `DeviceConfigUpdate` | `UpdateConfigResponse` |
| Control TCP client | `SessionController` | Старт/стоп сессии испытания | `SessionMetadata` | `StartSessionResponse` |
| ADSP ARM | `ConfigStore` | Валидация и хранение конфигураций на SD | protobuf config | сохранённый config + inventory |
| ADSP ARM | `ControlDispatcher` | Обработка команд control-канала | `ControlRequest` | `ControlResponse` |
| ADSP ARM | `DataStreamServer` | Отправка data-фреймов на мини-ПК | payload packets | `EgoFrameHeader + payload` |
| SHARC0 audio | `AudioBlockPublisher` | Публикация аудиоблоков | A2B audio DMA block | `AudioBlockBinaryHeader + PCM` |
| SHARC1 IMU | `ImuWindowPublisher` | Публикация окон LSM6DS3 | FIFO/DMA samples | `ImuWindowPacket` |
| SHARC1 CAN | `CanTelemetryPublisher` | Публикация CAN значений | raw CAN frame | `CanDecodedValuePacket`, `CanRawFramePacket` |
| SHARC1 navigation | `TrajectoryPublisher` | Публикация локальной траектории | CAN speed + gyro | `TrajectoryPointPacket` |
| ADSP ARM GPS | `GpsPublisher` | Публикация внешнего GPS/RTK | NMEA/UBX/custom | `GpsFixPacket` |
| ADSP ARM status | `StatusPublisher` | Периодическая диагностика | counters/status | `SystemStatusPacket`, `TimeStatusPacket` |
| Mini-PC runtime | `DataTcpReceiver` | Приём TCP data stream | TCP bytes | frames |
| Mini-PC runtime | `EgoBinWriter` | Запись сырого файла сессии | frames | `ego.bin`, `ego.index` |
| Mini-PC offline | `EgoBinReader` | Чтение сырого файла сессии | `ego.bin` | packet iterator |
| Mini-PC offline | `Mdf4ExportAdapter` | Подготовка каналов для MDF4 | decoded packets | MDF4 channel groups |

---

## 1. ConfigUploader

Используется на мини-ПК или сервисном приложении. Отправляет отдельные конфигурации до старта сессии.

Типовые действия:

1. `HELLO`.
2. `GET_CONFIG_INVENTORY`.
3. `UPDATE_CONFIG(audio)`.
4. `UPDATE_CONFIG(imu)`.
5. `UPDATE_CONFIG(can)`.
6. `UPDATE_CONFIG(vehicle)`.
7. `GET_CONFIG_SNAPSHOT`.

Правило: обновляются только те поля, которые реально переданы в `DeviceConfigUpdate`.

---

## 2. SessionController

Передаёт только метаданные текущего испытания.

`StartSessionRequest` не содержит audio/IMU/CAN/GPS/vehicle конфигурации. Они уже должны быть сохранены на плате.

Если конфигураций нет или они невалидны, плата возвращает отказ:

```text
result = RESULT_CODE_REJECTED
error.missing_configs = [...]
error.invalid_configs = [...]
```

---

## 3. ConfigStore

Работает на ARM ADSP-SC589.

Функции:

- хранит default-конфигурации после прошивки;
- принимает обновления по control-каналу;
- валидирует конфигурации;
- сохраняет конфигурации на SD;
- выдаёт `ConfigInventory`;
- перед стартом сессии собирает `DeviceConfigSnapshot`.

---

## 4. DataStreamServer

Работает на ARM ADSP-SC589.

Функции:

- принимает payload от SHARC0/SHARC1/ARM модулей;
- добавляет `EgoFrameHeader`;
- считает CRC32 payload;
- увеличивает общий `seq`;
- отправляет frame по Data TCP;
- при старте сессии первым отправляет `SessionStarted`, вторым — `ConfigSnapshotFrame`.

---

## 5. AudioBlockPublisher

Работает в связке SHARC0 → ARM.

Рекомендуемый production payload:

```text
EgoFrameHeader(frame_type = AUDIO_BLOCK, flags = PAYLOAD_BINARY)
AudioBlockBinaryHeader
raw PCM bytes
```

Причина: аудио — самый тяжёлый поток, поэтому не стоит заворачивать PCM в protobuf на SC589.

---

## 6. ImuWindowPublisher

Работает на SHARC1.

Функции:

- читает LSM6DS3 через SPI + FIFO/DMA;
- собирает короткие окна 1–5 мс;
- считает mean accel/gyro;
- считает delta angle/delta velocity;
- отправляет `ImuWindowPacket`.

---

## 7. CanTelemetryPublisher

Работает на SHARC1.

Функции:

- принимает CAN frame;
- проверяет жёстко заданные CAN ID;
- декодирует скорость, режим АКПП, опционально угол руля;
- отправляет `CanDecodedValuePacket`;
- опционально отправляет `CanRawFramePacket` для диагностики.

---

## 8. TrajectoryPublisher

Работает на SHARC1.

Функции:

- принимает скорость из CAN;
- принимает gyro Z из IMU;
- оценивает yaw и локальную траекторию;
- отправляет `TrajectoryPointPacket`.

---

## 9. EgoBinWriter

Работает на мини-ПК в runtime.

Функции:

- принимает Data TCP;
- проверяет `EgoFrameHeader`;
- проверяет CRC32;
- пишет `header + payload` в `ego.bin` без изменения;
- пишет индекс `ego.index` с `seq`, `frame_type`, `t0_ns`, `file_offset`, `payload_size`.

---

## 10. Mdf4ExportAdapter

Работает offline.

Функции:

- читает `ego.bin`;
- извлекает `ConfigSnapshotFrame`;
- строит группы каналов MDF4;
- раскладывает audio/IMU/CAN/GPS/trajectory/status по временным осям;
- сохраняет MDF4.
