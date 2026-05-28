# EGO Protocol Contract

Контракт сетевого обмена между ADSP-SC589 и бортовым мини-ПК.

## Состав

```text
proto/ego/v1/ego_common.proto
proto/ego/v1/ego_metadata.proto
proto/ego/v1/ego_data.proto
proto/ego/v1/ego_control.proto

docs/FRAME_CONTRACT.md
docs/CONTROL_API.md
docs/DATA_PACKETS.md
docs/EGO_BIN.md

scripts/gen_cpp.sh
scripts/gen_python.sh
```

## Каналы

| Канал | Назначение |
|---|---|
| Control TCP | управление, настройки, старт/стоп, статус |
| Data TCP | поток фреймов данных |

## Генерация C++

```bash
./scripts/gen_cpp.sh
```

## Генерация Python

```bash
./scripts/gen_python.sh
```
## Ключевая схема контракта
### 5000 Control TCP:
- protobuf request/response
- hello / status / set_config / start_session / stop_session

### 5001 Data TCP:
- EgoFrameHeader + payload
- payload = protobuf или production binary payload

## Принцип

- Статические метаданные и конфиги описаны protobuf.
- Высокочастотные данные могут передаваться protobuf или production binary payload.
- `ego.bin` на мини-ПК является последовательностью принятых Data TCP фреймов.
