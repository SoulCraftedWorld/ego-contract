# **EGO Protocol Contract v1.3**

Контракт сетевого обмена между **ADSP-SC589 ego acquisition module** и бортовым мини-ПК.

## Назначение

Контракт описывает:

- Control TCP API для управления платой и загрузки конфигураций;
- Data TCP frame format для передачи измерительных данных;
- protobuf-схемы конфигураций, метаданных и small/structured data payload;
- формат сырого файла `ego.bin`;
- правила последующей сборки MDF4 на мини-ПК.

## Главная схема

ADSP-SC589 работает как TCP-сервер.

| Канал | Порт | Назначение |
|---|---:|---|
| Control TCP | 5000 | команды, конфигурации, статус, старт/стоп |
| Data TCP | 5001 | поток фреймов данных для записи в `ego.bin` |

## Конфигурации

Конфигурации устройства не передаются внутри `StartSessionRequest`.

До запуска сессии клиент отдельно загружает и сохраняет на SD-карту платы:

- `AudioConfig`;
- `ImuConfig`;
- `CanConfig`;
- `GpsConfig`;
- `VehicleGeometryConfig`;
- `TimeConfig`;
- `NetworkConfig`.

После прошивки на плате уже должны быть конфигурации по умолчанию. Пользовательские конфигурации могут обновляться по отдельности.

## Старт сессии

`StartSessionRequest` содержит только метаданные испытания:

- `session_id`;
- `test_id`;
- `test_description`;
- `scenario_id`;
- `scenario_name`;
- `operator_name`;
- `project`;
- `vehicle_id`;
- `source_id`;
- `tags`.

Перед запуском плата проверяет наличие и валидность сохранённых конфигураций. Если required-конфигурация отсутствует или невалидна, старт отклоняется, а ответ содержит `missing_configs` и `invalid_configs`.

## Data stream

После успешного старта плата передаёт по Data TCP:

```text
SessionStarted
ConfigSnapshotFrame
AudioBlock / ImuWindow / CanDecodedValue / CanRawFrame / TrajectoryPoint / GpsFix / ...
SessionEnded
```

`ConfigSnapshotFrame` нужен, чтобы `ego.bin` был самодостаточным и мог быть преобразован в MDF4 без отдельного доступа к SD-карте платы.

## Генерация

```bash
make cpp
make python
```

или напрямую:

```bash
./scripts/gen_cpp.sh
./scripts/gen_python.sh
```

## Integration helpers

The package also contains language-level packet descriptions and module extension examples:

```text
include/ego_protocol_packets.hpp
python/ego_protocol_packets.py
docs/MODULE_EXTENSION_EXAMPLES.md
docs/CPP_PYTHON_STRUCTURES.md
examples/cpp/module_extensions.hpp
examples/python/module_extensions.py
```

Use them for integration when a module needs to write or read production binary data frames without protobuf overhead.
