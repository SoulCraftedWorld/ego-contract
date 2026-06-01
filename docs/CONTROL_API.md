# API Control TCP

Control TCP использует protobuf-запросы и protobuf-ответы с фреймингом по префиксу длины.

## Фрейминг

Запрос:

```text
uint32_le message_size
байты protobuf `ControlRequest`
```

Ответ:

```text
uint32_le message_size
байты protobuf `ControlResponse`
```

## Основной процесс

```text
client -> HELLO
device -> HELLO_RESPONSE + config inventory

client -> GET_CONFIG_INVENTORY
device -> ConfigInventory

client -> UPDATE_CONFIG(audio)
device -> UpdateConfigResponse

client -> UPDATE_CONFIG(imu)
device -> UpdateConfigResponse

client -> UPDATE_CONFIG(can)
device -> UpdateConfigResponse

client -> UPDATE_CONFIG(gps)
device -> UpdateConfigResponse

client -> UPDATE_CONFIG(vehicle)
device -> UpdateConfigResponse

client -> START_SESSION(метаданные сессии)
device -> StartSessionResponse OK или REJECTED

device -> DATA: SessionStarted
device -> DATA: ConfigSnapshotFrame
device -> DATA: фреймы реального времени
```

## CONTROL /hello

Проверка соединения и версии протокола.

Payload запроса: `HelloRequest`

Payload ответа: `HelloResponse`

## CONTROL /status

Запрос текущего состояния платы.

Payload запроса: `GetStatusRequest`

Payload ответа: `DeviceStatus`

## CONTROL /config/inventory

Запрос перечня сохранённых конфигураций и их состояния.

Payload запроса: `GetConfigInventoryRequest`

Payload ответа: `ConfigInventory`

## CONTROL /config/get

Запрос текущего эффективного снимка конфигурации.

Payload запроса: `GetConfigSnapshotRequest`

Payload ответа: `DeviceConfigSnapshot`

## CONTROL /config/update

Обновление одной или нескольких конфигураций.

Payload запроса: `UpdateConfigRequest`

Особенности:

- `DeviceConfigUpdate` содержит optional-поля;
- можно обновить только audio, только CAN или любой другой набор;
- для CAN можно передать либо `signals`, либо DBC-текст в `dbc_text`;
- `validate_only=true` выполняет проверку без сохранения;
- `save_to_sd=true` сохраняет конфигурации на SD-карту.

## CONTROL /config/save

Сохранение текущих конфигураций на SD-карту.

Payload запроса: `SaveConfigRequest`

## CONTROL /config/defaults

Восстановление конфигураций по умолчанию.

Payload запроса: `RestoreDefaultConfigRequest`

## CONTROL /session/start

Запуск сессии.

Payload запроса: `StartSessionRequest`

Важно:

- команда содержит только метаданные сессии и испытания;
- конфигурации audio/IMU/CAN/GPS/vehicle должны уже быть на плате;
- при `require_valid_saved_configs=true` старт отклоняется, если обязательные конфигурации отсутствуют или невалидны.

Пример отказа:

```json
{
  "result": "RESULT_CODE_REJECTED",
  "error": {
    "code": "RESULT_CODE_REJECTED",
    "message": "Required configuration is missing or invalid",
    "missing_configs": ["CONFIG_TYPE_CAN"],
    "invalid_configs": ["CONFIG_TYPE_AUDIO"]
  }
}
```

## CONTROL /session/stop

Остановка сессии.

Payload запроса: `StopSessionRequest`

## CONTROL /marker

Добавление пользовательской метки события в текущую сессию.

Payload запроса: `MarkerRequest`

## Текущий минимальный режим firmware

Пока полный protobuf API Control TCP не включён на плате, firmware предоставляет
строчный отладочный интерфейс управления.

```text
start [bin_path] [index_path]
stop
status
logs
log_get <name>
log_delete <ego_log_name.bin>
config_get
config_set <key> <value>
config_reload
config_save
```

Если `bin_path` не задан, firmware создаёт новый лог в `sd:ego/logs/`:
`ego_YYYYMMDD_HHMMSS.bin`, когда RTC/GPS-время валидно, иначе
`ego_mono_<timestamp>.bin`. Если `bin_path` задан, а `index_path` отсутствует,
путь к индексу строится заменой расширения бинарного файла на `.index`.

`logs` выводит завершённые `.bin` и `.index` файлы из `sd:ego/logs/`.
`log_get` передаёт выбранный файл из `sd:ego/logs/`: ответ начинается строкой
`OK log name=<name> size=<bytes>`, затем идёт ровно `size` байт файла, затем
строка `END log`. Клиент должен читать файл по количеству байт, а не искать
перевод строки.
`log_delete` принимает только `ego_*.bin`, удаляет соответствующий `.index` и
отклоняется во время активной сессии.

`config_get` возвращает активную эффективную конфигурацию в формате text-kv.
`config_set` обновляет один ключ и сохраняет `sd:ego/config/effective.cfg`;
изменения отклоняются во время активной сессии. `config_reload` перечитывает
SD-конфигурацию или возвращается к значениям firmware по умолчанию.
`config_save` записывает текущую эффективную конфигурацию на SD.
