# Configuration workflow

Конфигурации устройства являются долгоживущими настройками платы и хранятся на SD-карте ADSP-SC589.

## Конфигурации по умолчанию

После прошивки на плате должны быть default-конфигурации:

- audio;
- IMU;
- CAN;
- GPS;
- vehicle geometry;
- time;
- network.

Состояние default-конфигурации обозначается как `CONFIG_STATE_DEFAULT`.

Если пользователь загрузил и сохранил свою конфигурацию, состояние становится `CONFIG_STATE_USER_SAVED`.

## Обновление

Клиент обновляет конфигурации командой:

```text
ControlRequest.update_config
```

В `DeviceConfigUpdate` все поля optional:

- `audio`;
- `imu`;
- `can`;
- `gps`;
- `vehicle`;
- `time`;
- `network`.

Устройство валидирует только переданные поля.

## Сохранение

При `save_to_sd=true` принятые конфигурации сохраняются на SD-карту.

Если сохранение невозможно, возвращается:

```text
RESULT_CODE_STORAGE_ERROR
```

## Старт сессии

`StartSessionRequest` не содержит конфигурации. Он содержит только метаданные испытания.

Перед стартом устройство проверяет required configs.

Если конфигурация отсутствует:

```text
missing_configs += CONFIG_TYPE_...
```

Если конфигурация есть, но не проходит проверку:

```text
invalid_configs += CONFIG_TYPE_...
```

## Config snapshot в data stream

После успешного старта устройство отправляет:

```text
SessionStarted
ConfigSnapshotFrame
```

`ConfigSnapshotFrame` содержит полный effective snapshot всех конфигураций, использованных в этой сессии. Это делает `ego.bin` самодостаточным.
