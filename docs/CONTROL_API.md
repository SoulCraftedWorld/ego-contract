# Control TCP API

Control TCP использует protobuf request/response с length-prefixed framing.

## Framing

```text
uint32_le message_size
ControlRequest protobuf bytes
```

Ответ:

```text
uint32_le message_size
ControlResponse protobuf bytes
```

## CONTROL /hello

Проверка соединения и версии протокола.

Request payload: `HelloRequest`

Response payload: `HelloResponse`

## CONTROL /status

Запрос текущего состояния платы.

Request payload: `GetStatusRequest`

Response payload: `RuntimeStatus`

## CONTROL /config/set

Загрузка статической конфигурации сессии и устройства.

Request payload: `SetConfigRequest`

Содержит:

- `SessionMetadata`
- `DeviceConfig`

## CONTROL /session/start

Запуск сессии записи и опционально запуск Data TCP потока.

Request payload: `StartSessionRequest`

## CONTROL /session/stop

Остановка сессии.

Request payload: `StopSessionRequest`

## CONTROL /stream/start

Запуск Data TCP потока без перезапуска сессии.

Request payload: `StartStreamRequest`

## CONTROL /stream/stop

Остановка Data TCP потока без завершения сессии.

Request payload: `StopStreamRequest`
