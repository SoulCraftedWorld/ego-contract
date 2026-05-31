# Control TCP API

Control TCP использует protobuf request/response с length-prefixed framing.

## Framing

Запрос:

```text
uint32_le message_size
ControlRequest protobuf bytes
```

Ответ:

```text
uint32_le message_size
ControlResponse protobuf bytes
```

## Основной workflow

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

client -> START_SESSION(session metadata)
device -> StartSessionResponse OK или REJECTED

device -> DATA: SessionStarted
device -> DATA: ConfigSnapshotFrame
device -> DATA: realtime frames
```

## CONTROL /hello

Проверка соединения и версии протокола.

Request payload: `HelloRequest`

Response payload: `HelloResponse`

## CONTROL /status

Запрос текущего состояния платы.

Request payload: `GetStatusRequest`

Response payload: `DeviceStatus`

## CONTROL /config/inventory

Запрос перечня сохранённых конфигураций и их состояния.

Request payload: `GetConfigInventoryRequest`

Response payload: `ConfigInventory`

## CONTROL /config/get

Запрос текущего effective snapshot.

Request payload: `GetConfigSnapshotRequest`

Response payload: `DeviceConfigSnapshot`

## CONTROL /config/update

Обновление одной или нескольких конфигураций.

Request payload: `UpdateConfigRequest`

Особенности:

- `DeviceConfigUpdate` содержит optional-поля;
- можно обновить только audio, только CAN или любой другой набор;
- `validate_only=true` выполняет проверку без сохранения;
- `save_to_sd=true` сохраняет конфигурации на SD-карту.

## CONTROL /config/save

Сохранение текущих конфигураций на SD-карту.

Request payload: `SaveConfigRequest`

## CONTROL /config/defaults

Восстановление конфигураций по умолчанию.

Request payload: `RestoreDefaultConfigRequest`

## CONTROL /session/start

Запуск сессии.

Request payload: `StartSessionRequest`

Важно:

- команда содержит только session/test metadata;
- audio/IMU/CAN/GPS/vehicle configs должны уже быть на плате;
- при `require_valid_saved_configs=true` старт отклоняется, если required-конфигурации отсутствуют или невалидны.

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

Request payload: `StopSessionRequest`

## CONTROL /marker

Добавление пользовательской метки события в текущую сессию.

Request payload: `MarkerRequest`

## Current minimal firmware mode

The current firmware exposes a line-oriented debug/control interface before the
full protobuf control API is enabled.

```text
start [bin_path] [index_path]
stop
status
logs
log_get <name>
log_delete <ego_log_name.bin>
```

If `bin_path` is omitted, firmware creates a new log in `sd:ego/logs/`:
`ego_YYYYMMDD_HHMMSS.bin` when RTC/GPS time is valid, otherwise
`ego_mono_<timestamp>.bin`. If `bin_path` is custom and `index_path` is omitted,
the firmware derives the index path by replacing the binary file extension with
`.index`.

`logs` lists completed `.bin` and `.index` files in `sd:ego/logs/`.
`log_get` streams one selected file from `sd:ego/logs/`: the response starts
with `OK log name=<name> size=<bytes>`, then exactly `size` raw bytes, then an
`END log` line. The client must read by byte count, not by newline scanning.
`log_delete` accepts only `ego_*.bin`, deletes the matching `.index`, and is
rejected while a session is active.
