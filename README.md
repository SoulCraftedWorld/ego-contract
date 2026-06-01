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
CAN-декодер можно передать как готовый список `CanConfig.signals` или как DBC
строку в `CanConfig.dbc_text`. Каталог `value_id -> name/описание` формируется
на ARM из `CanSignalConfig.name/value_id` или из разобранного DBC и передаётся
в метаданных сессии `SessionMetadata.can_value_descriptions`.

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

## Поток данных

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

## Интеграционные helper-файлы

Пакет также содержит описания пакетов на уровне языков и примеры расширения модулей:

```text
include/ego_protocol_packets.hpp
python/ego_protocol_packets.py
docs/MODULE_EXTENSION_EXAMPLES.md
docs/CPP_PYTHON_STRUCTURES.md
examples/cpp/module_extensions.hpp
examples/python/module_extensions.py
```

Используйте их для интеграции, когда модулю нужно писать или читать бинарные
фреймы данных production-режима без protobuf overhead.
