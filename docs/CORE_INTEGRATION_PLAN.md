# Core Integration Plan

## Purpose

This document defines how to integrate the EGO acquisition functionality into the
existing SAM Audio Starter based project without breaking the current audio,
network, storage, shell, and SHARC IPC paths.

The target system is an ADSP-SC589 MINI based realtime acquisition module that
streams synchronized audio, vehicle motion, CAN, IMU, GPS, time, and status
frames to a mini-PC over TCP. The mini-PC writes `ego.bin`; the board only
produces and transmits frames.

## Confirmed Project Baseline

Current code already provides these useful integration points:

- ARM runs FreeRTOS and owns initialization, storage, Ethernet/lwIP, shell,
  A2B setup, audio routing, and SAE IPC master setup.
- SHARC0 and SHARC1 already start through `adi_core_enable()` when
  `SHARC_AUDIO_ENABLE` is enabled.
- ARM initializes SAE as IPC master and receives SHARC ready/cycle messages.
- `ALL/include/ipc.h` already contains preliminary EGO-related IPC types:
  `IPC_TYPE_MOTION_BLOCK`, `IPC_TYPE_A2B_AUDIO_BLOCK`,
  `IPC_TYPE_IMU_COORDINATE`.
- A2B is already routed through SPORT1A/SPORT1B.
- `contract/headers/include/ego_protocol_packets.hpp` already defines fixed
  production binary packets for Data TCP payloads.

Current A2B/SRU mapping in `ARM/src/init.c` matches the target hardware:

| Signal | Pin | Current route |
|---|---|---|
| A2B BCLK | DAI0_PB07 | SPORT1 clock path |
| A2B SYNC/FS | DAI0_PB08 | SPORT1 frame sync path |
| A2B DTX0 | DAI0_PB09 | SPORT1B primary RX |
| A2B DTX1 | DAI0_PB10 | SPORT1B secondary RX |
| A2B DRX0 | DAI0_PB11 | SPORT1A primary TX |
| A2B DRX1 | DAI0_PB12 | SPORT1A secondary TX |

Current important audio constants:

- `SYSTEM_SAMPLE_RATE` is 48000.
- `SYSTEM_BLOCK_SIZE` is currently 64 frames.
- `A2B_AUDIO_CHANNELS` is 32.
- Audio sample type is `int32_t`.

## Target Core Responsibilities

### SHARC0

SHARC0 is dedicated to A2B/audio capture support.

Responsibilities:

- receive or process A2B/audio blocks already routed by the existing audio
  engine;
- preserve deterministic audio timing;
- attach precise monotonic timestamps to audio block boundaries when the block
  enters the capture path;
- forward audio block metadata and PCM buffer ownership to ARM through SAE IPC;
- keep processing minimal: no CAN parsing, no IMU filtering, no GPS, no TCP.

SHARC0 must stay the highest-priority data source because audio is the largest
and least recoverable stream.

### SHARC1

SHARC1 owns high-rate motion inputs and local trajectory estimation.

Primary responsibilities:

- CAN0 RX timestamping and low-cost extraction of required vehicle signals;
- SPI1 IMU acquisition from LSM6DS3;
- IMU window aggregation;
- local trajectory prediction from latest vehicle speed and gyro yaw rate;
- periodic motion/trajectory block publication to ARM.

Recommended split:

- Do not run a general dynamic DBC parser in the SHARC1 realtime path.
- Use ARM to load/validate DBC/config and compile a small fixed extraction table.
- Send only the extraction table to SHARC1.
- SHARC1 decodes only required runtime signals: vehicle speed, steering angle if
  available, gear if required, and diagnostic/raw fields needed for status.

Reasoning:

CAN messages arrive at 10-20 ms scale for typical vehicle signals. Running a
full parser on SHARC1 does not improve source timing; timestamping at RX and
extracting a small configured signal set does. The general DBC parser is better
placed on ARM or on the mini-PC/offline side.

### ARM Cortex-A5

ARM owns orchestration, storage/config, GPS, TCP, aggregation, and diagnostics.

Responsibilities:

- load and validate configs from SPIFFS/SD/defaults;
- run Control TCP server on port 5000;
- run Data TCP server on port 5001;
- receive SHARC0 audio and SHARC1 motion IPC;
- receive GPS and convert it to `GpsFix` frames;
- build `EgoFrameHeader + payload` records;
- maintain global frame sequence and session state;
- expose status, errors, and overflow flags;
- send frames to the mini-PC without writing `ego.bin` locally.

## Timing Model

Use one board-local monotonic timebase and convert all frame timestamps to
nanoseconds before Data TCP transmission.

Preferred internal representation:

- raw hardware ticks for ISR and IPC metadata;
- `uint64_t t_ns` for contract-facing packets;
- conversion helper on ARM and SHARCs:
  `t_ns = ticks * 1000000000 / CGU_TS_CLK`.

All packet timestamps are board-monotonic nanoseconds relative to the session
timebase. UTC/GPS correction is reported separately through `TimeStatus`.

## Audio Window Decision

Audio rate is fixed at 48 kHz.

For a 4 ms synchronization slice:

```text
48000 frames/s * 0.004 s = 192 frames
```

This is exact and should be the EGO acquisition block size.

Current project `SYSTEM_BLOCK_SIZE` is 64 frames, which is 1.333 ms at 48 kHz.
Do not immediately change the global audio block size because it may affect USB,
RTP, VBAN, WAV, and routing behavior. Instead:

- keep existing 64-frame low-level audio callbacks initially;
- accumulate three 64-frame blocks into one EGO audio frame of 192 frames;
- timestamp the first and last source block boundaries;
- emit one `AudioBlockBinaryHeader + raw PCM` payload every 4 ms.

Only after this works should changing `SYSTEM_BLOCK_SIZE` to 192 be evaluated.

## IMU Rate Decision

The requested 200 Hz IMU ODR gives one sample every 5 ms, which does not fit a
4 ms synchronization slice. It is acceptable for low bandwidth vehicle motion,
but it cannot provide an IMU sample for every 4 ms audio slice.

Recommended IMU ODR:

- use 500 Hz if SPI1/FIFO load is stable;
- aggregate two IMU samples per 4 ms slice;
- publish each 4 ms `ImuWindowPacket` with `sample_count` normally equal to 2.

Fallback:

- use 250 Hz if 500 Hz causes FIFO/CPU pressure;
- aggregate one sample per 4 ms slice, with occasional timestamp interpolation.

Avoid 200 Hz for the primary synchronized mode unless the final requirement is
relaxed to 5 ms slices or interpolation is explicitly accepted.

## CAN Rate Decision

CAN0 runs at 500 kbit/s on:

- `PC_07/CAN0_RX`
- `PC_08/CAN0_TX`

The file `docs/CAN transceiver-controller setup.txt` is currently empty. The
existing `ALL/src/can_bus` code contains preliminary 500 kbit/s timing constants,
but this must be verified against the actual CAN input clock before finalizing.

Recommended CAN realtime path:

- timestamp each received CAN frame as early as possible in the RX callback;
- push raw frame metadata into a fixed ring buffer;
- decode only configured required values on SHARC1;
- retain optional raw CAN frame forwarding as a debug/config mode, not always-on
  production traffic.

Required decoded values for the first implementation:

- vehicle speed;
- steering angle if available;
- gear if available;
- parser/status flags.

## Data Flow

### Audio

```text
A2B bus -> SPORT1B DMA -> ARM audio callback/routing path
        -> SHARC0 audio IPC/capture support
        -> ARM EGO audio aggregator
        -> Data TCP frame AUDIO_BLOCK every 4 ms
```

Implementation note: the existing project currently routes SHARC audio as
generic audio streams. The EGO path should add a capture tap instead of
replacing the existing routing table. The first implementation should copy or
reference the A2B input block into an EGO audio accumulator and leave normal
audio routing intact.

### IMU

```text
LSM6DS3 -> SPI1 + INT PB_13 -> SHARC1 IMU ISR/task
        -> 4 ms IMU window aggregation
        -> SHARC1 trajectory estimator
        -> ARM through SAE IPC
        -> Data TCP IMU_WINDOW and TRAJECTORY_POINT
```

SPI1 pins:

- `PE_15/SPI1_MOSI`
- `PE_14/SPI1_MISO`
- `PE_13/SPI1_CLK`
- `PE_12/SPI1_SEL4`
- `PB_13/INT`

### CAN

```text
CAN0 RX -> SHARC1 CAN RX callback
        -> timestamped raw frame ring
        -> fixed signal extraction table
        -> vehicle state cache
        -> trajectory estimator
        -> ARM through SAE IPC
        -> Data TCP CAN_DECODED_VALUE / optional CAN_RAW_FRAME
```

### GPS

```text
External GPS -> ARM GPS receiver
             -> timestamp/parse
             -> ARM EGO frame builder
             -> Data TCP GPS_FIX
```

GPS is not part of the 1 ms internal motion deadline. It is fused or aligned on
ARM for recording and offline correction.

## Frame Production Rates

| Frame | Producer | Rate | Notes |
|---|---|---:|---|
| `AudioBlockBinaryHeader + PCM` | ARM from SHARC0/A2B tap | 250 Hz | 192 frames at 48 kHz |
| `ImuWindowPacket` | SHARC1 | 250 Hz | 4 ms windows, 500 Hz IMU recommended |
| `TrajectoryPointPacket` | SHARC1 | 250 Hz | calculated before slice boundary |
| `CanDecodedValuePacket` | SHARC1/ARM | on change or on RX | at source CAN timing |
| `CanRawFramePacket` | SHARC1/ARM | optional | debug or configured recording |
| `GpsFixPacket` | ARM | GPS rate | typically 1-20 Hz |
| `TimeStatusPacket` | ARM | 1 Hz | plus on sync changes |
| `SystemStatusPacket` | ARM | 1 Hz | plus on error changes |

## IPC Architecture

Use SAE IPC for all inter-core messages. Keep IPC payloads compact and bounded.

Recommended new shared modules:

```text
ALL/include/ego_time.h
ALL/include/ego_ipc.h
ALL/include/ego_status.h
ARM/src/ego/ego_aggregator.c
ARM/src/ego/ego_frame_builder.c
ARM/src/ego/ego_control_server.c
ARM/src/ego/ego_data_server.c
ARM/src/ego/ego_config_store.c
SHARC0/src/ego_audio_capture.c
SHARC1/src/ego_motion_capture.c
SHARC1/src/ego_can_input.cpp
SHARC1/src/ego_imu_input.c
SHARC1/src/ego_trajectory.c
```

Do not over-split initially. Each module should own one clear runtime concern.

IPC messages to define or clean up:

- `EGO_IPC_AUDIO_BLOCK_READY`
- `EGO_IPC_IMU_WINDOW_READY`
- `EGO_IPC_TRAJECTORY_READY`
- `EGO_IPC_CAN_VALUE_READY`
- `EGO_IPC_CAN_RAW_READY`
- `EGO_IPC_CONFIG_UPDATE`
- `EGO_IPC_SESSION_START`
- `EGO_IPC_SESSION_STOP`
- `EGO_IPC_STATUS`

The current `IPC_MSG` union has variable-length members. Before production use,
separate bounded IPC envelopes from variable payload storage. Variable audio
PCM should use preallocated SAE buffers or ring buffers, not large stack/local
message copies.

## ARM FreeRTOS Tasks

Add EGO tasks after Ethernet and storage initialization, but before dropping the
startup task into the shell.

Recommended tasks:

| Task | Priority | Responsibility |
|---|---:|---|
| `EgoDataTask` | `ETHERNET_PRIORITY` or +1 if needed | Data TCP send loop |
| `EgoControlTask` | `TELNET_TASK_PRIORITY` | Control TCP API |
| `EgoAggregatorTask` | `UAC20_TASK_PRIORITY` or `ETHERNET_PRIORITY` | frame scheduling and queues |
| `EgoGpsTask` | `HOUSEKEEPING_PRIORITY + 1` | GPS parsing |
| `EgoStatusTask` | `HOUSEKEEPING_PRIORITY` | periodic status frames |

Do not do TCP sends directly from audio callbacks or IPC callbacks. Callbacks
should only timestamp, update small state, and enqueue bounded work.

## Buffering Policy

Hard requirement: audio and position are first priority.

Use fixed-size ring buffers with explicit overflow counters:

- audio EGO accumulator: at least 3 x 64-frame source blocks plus one 192-frame
  output block;
- ARM Data TCP queue: enough for several 4 ms slices, but bounded;
- SHARC1 CAN raw ring: bounded, overwrite oldest on overflow;
- SHARC1 IMU FIFO/window buffer: bounded, reset window and flag overflow if
  synchronization is lost.

Overflow behavior:

- log the event;
- increment subsystem counter;
- set status/error flags in the next `SystemStatusPacket`;
- for buffer overflow, drop/reset the affected buffered data and continue;
- do not block the audio callback waiting for TCP or storage.

If Data TCP cannot keep up, the session is degraded:

1. disable optional `CanRawFramePacket`;
2. reduce status/debug traffic;
3. keep audio and trajectory;
4. if audio cannot be transmitted, set fatal session error and require restart.

## Packet Encoding

Use little-endian packed binary payloads for high-rate production frames. This
matches ADSP little-endian operation and the existing `EGO_FRAME_MAGIC`
definition.

Rules:

- all Data TCP records are `EgoFrameHeader + payload`;
- `EgoFrameHeader` is 72 bytes;
- high-rate audio uses `FramePayloadType::AUDIO_BLOCK` with
  `FrameFlags::PAYLOAD_BINARY`;
- audio payload is `AudioBlockBinaryHeader + interleaved int32 PCM`;
- IMU, CAN, trajectory, GPS may initially use protobuf for ease of validation,
  but production should use fixed binary packet structs where defined;
- all timestamps in contract-facing packets are `uint64_t` nanoseconds;
- all structs that cross the wire must be packed and size-checked at compile
  time.

Alignment comment:

Packed structs are used for wire compatibility, not for efficient internal
processing. Internally, modules may use naturally aligned structs and copy into
packed packet structs only at the frame builder boundary.

## Error and Status Model

Maintain per-subsystem counters:

- `audio_overruns`
- `audio_dropped_blocks`
- `imu_fifo_overruns`
- `imu_window_resets`
- `can_rx_errors`
- `can_rx_lost`
- `can_queue_full`
- `tcp_send_errors`
- `data_queue_overflows`
- `gps_parse_errors`

Expose them through `SystemStatusPacket`.

Use flags in each payload for local quality:

- timestamp estimated;
- source invalid;
- overflow occurred;
- interpolation used;
- stale CAN value;
- GPS not locked.

## Integration Phases

### Phase 1: Non-invasive skeleton

- Add EGO modules and headers but keep them disabled by default.
- Add compile-time flag `EGO_ACQ_ENABLE`.
- Add no-op init calls from ARM/SHARC main files.
- Build all cores.

### Phase 2: Time and status base

- Implement shared tick-to-nanosecond conversion.
- Add common status counters.
- Add `SystemStatusPacket` generation on ARM.
- Verify timestamps are monotonic across ARM/SHARC IPC.

### Phase 3: Audio tap

- Add A2B input capture tap without changing the normal route table.
- Accumulate 3 x 64-frame blocks into one 192-frame EGO audio block.
- Emit binary `AUDIO_BLOCK` frames through an internal ARM queue.
- Verify sequence, `t0_ns`, `t1_ns`, payload size, and CRC.

### Phase 4: SHARC1 IMU path

- Add SPI1 platform read/write for `docs/lsm6ds3-pid` driver.
- Configure LSM6DS3 FIFO/INT.
- Start with 500 Hz ODR and 4 ms windows.
- Emit `IMU_WINDOW` and local quality flags.

### Phase 5: SHARC1 CAN path

- Clean up `ALL/src/can_bus` enough to build reliably on target.
- Verify CAN0 pin mux and 500 kbit/s timing from the real CAN clock.
- Add RX timestamping and fixed signal extraction.
- Emit speed and optional steering/gear values.

### Phase 6: Trajectory

- Implement simple dead-reckoning:
  `x/y` from speed and yaw, yaw from gyro z, optional steering correction.
- Publish `TRAJECTORY_POINT` every 4 ms.
- Mark stale CAN speed if no update within configured timeout.

### Phase 7: TCP servers and session control

- Implement Control TCP port 5000.
- Implement Data TCP port 5001.
- Add session start/stop, config snapshot, and frame sequencing.
- Verify mini-PC receives frames and can write `ego.bin`.

### Phase 8: Load and failure testing

- Test full 32-channel 48 kHz audio.
- Test CAN burst/queue full behavior.
- Test IMU FIFO overflow.
- Test TCP client disconnect/reconnect.
- Verify audio and trajectory are preserved under reduced optional traffic.

## Build and IDE Notes

The repository contains `Makefile` files and appears to have been used from a
MinGW shell. The current CLion/IDE workspace is not enough by itself unless it
is configured to call the same toolchain and make targets.

Recommended setup:

- keep using the known working MinGW + make path first;
- identify the exact make target that builds ARM, SHARC0, and SHARC1;
- then configure the IDE external tool or custom build profile to call that
  command;
- use JTAG for load/run after the build is repeatable.

Before code implementation, record the exact successful build command in this
document or in a dedicated build note.

## Open Questions

- Confirm actual CAN peripheral clock used by `adi_candrv_SetCanClock()` and
  validate BRP/TSEG/SJW for 500 kbit/s.
- Confirm whether EGO should record raw CAN continuously or only decoded CAN in
  production mode.
- Confirm GPS physical input: USB CDC, UART, LAN, or other.
- Confirm whether SHARC0 should receive A2B buffers through the existing SHARC
  audio stream mechanism or whether ARM should create the first EGO audio tap.
- Confirm final microphone count and channel-to-microphone mapping for the
  32-channel A2B stream.
- Confirm if 500 Hz IMU ODR is acceptable electrically and mechanically for the
  target vehicle tests.

## Recommended Immediate Next Step

Implement Phase 1 and Phase 2 only:

- add `EGO_ACQ_ENABLE`;
- add common EGO headers;
- add no-op init points on ARM/SHARC0/SHARC1;
- add monotonic timestamp conversion helpers;
- add compile-time size checks for existing protocol structs.

This creates stable integration points without changing existing audio behavior.
