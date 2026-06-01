# Формат `ego.bin`

`ego.bin` — append-only файл, который формируется на мини-ПК из фреймов Data TCP.

## Запись

Мини-ПК пишет в файл каждый принятый фрейм без изменения:

```text
EgoFrameHeader
байты payload
EgoFrameHeader
байты payload
...
```

## Состав

В начале нормальной сессии должны быть:

```text
SessionStarted
ConfigSnapshotFrame
```

Далее идут фреймы реального времени:

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

## Текущая запись на SD в firmware

- ARM firmware пишет на SD тот же поток `EgoFrameHeader + payload`, который
  отправляется по TCP.
- `SESSION_STARTED` и `SESSION_ENDED` в текущем минимальном режиме содержат
  бинарный payload `SessionEventBinaryHeader + metadata_text`, поэтому начало и
  конец записи имеют метаданные даже без protobuf-кодера на плате.
- По умолчанию логи создаются в `sd:ego/logs/` с именем
  `ego_YYYYMMDD_HHMMSS.bin`, если RTC/GPS-время валидно. Пока время не
  валидно, используется резервное имя `ego_mono_<timestamp>.bin`.
- Рядом с `.bin` также пишется CSV-файл `.index` с полями:
  `seq,frame_type,t0_ns,t1_ns,file_offset,payload_size,payload_crc32,header_crc32,flags`.
- Если задан пользовательский путь бинарного файла, путь к индексу строится
  заменой расширения на `.index`, если явный путь индекса не передан в текущую
  минимальную Control TCP команду `start`.
- Firmware создаёт `sd:ego/logs/` для записей и `sd:ego/config/` для настроек
  модулей. Автоматическая очистка удаляет только старые `ego_*.bin` из
  `sd:ego/logs/` и соответствующие `.index` файлы.
- Перед записью и затем периодически во время записи firmware проверяет, что на
  SD свободно не менее 1 GiB. Если места меньше, firmware пытается удалить
  самый старый завершённый лог.
- Data TCP держит в памяти ограниченное replay-окно последних фреймов. При
  переподключении клиента firmware сначала отправляет сохранённые в памяти
  фреймы, затем продолжает текущий поток. Если клиент отсутствует дольше, чем
  помещается в replay-окно, старые фреймы вытесняются, но при наличии SD они
  остаются в `ego_*.bin`.
- Текущий минимальный Control TCP поддерживает обслуживание логов:
  `logs`, `log_get <name>` и `log_delete <ego_*.bin>`. Бинарная выгрузка
  начинается с текстового заголовка с размером в байтах, затем отправляется
  ровно это количество байт файла.
- Текущая минимальная firmware отправляет `CONFIG_SNAPSHOT` сразу после
  `SESSION_STARTED`. Это бинарный ключевой фрейм с `ConfigSnapshotBinaryHeader` и
  активной текстовой конфигурацией `key=value`, поэтому SD-лог остаётся
  самодостаточным до включения полного protobuf-кодера конфигураций.
