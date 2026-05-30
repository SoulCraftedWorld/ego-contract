#ifndef EGO_MODULE_EXTENSIONS_HPP
#define EGO_MODULE_EXTENSIONS_HPP

#include <cstdint>
#include <cstddef>
#include <vector>
#include <functional>
#include <stdexcept>
#include <cstring>
#include "../../include/ego_protocol_packets.hpp"

namespace ego::examples {

using namespace ego::protocol::v1;

inline uint32_t crc32_ieee(const uint8_t* data, size_t size) {
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < size; ++i) {
        crc ^= static_cast<uint32_t>(data[i]);
        for (int j = 0; j < 8; ++j) {
            const uint32_t mask = 0u - (crc & 1u);
            crc = (crc >> 1u) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

inline uint32_t crc32_ieee(const std::vector<uint8_t>& data) {
    return crc32_ieee(data.data(), data.size());
}

class DataFrameBuilder {
public:
    DataFrameBuilder(uint64_t session_id_hi, uint64_t session_id_lo)
        : session_id_hi_(session_id_hi), session_id_lo_(session_id_lo) {}

    std::vector<uint8_t> build(FramePayloadType type,
                               uint32_t flags,
                               uint64_t t0_ns,
                               uint64_t t1_ns,
                               const uint8_t* payload,
                               uint32_t payload_size) {
        const uint32_t payload_crc = crc32_ieee(payload, payload_size);
        EgoFrameHeader header = make_frame_header(
            type,
            flags,
            session_id_hi_,
            session_id_lo_,
            seq_++,
            t0_ns,
            t1_ns,
            payload_size,
            payload_crc
        );

        // header_crc32 is calculated with header_crc32 field set to zero.
        header.header_crc32 = 0u;
        header.header_crc32 = crc32_ieee(reinterpret_cast<const uint8_t*>(&header), sizeof(header));

        std::vector<uint8_t> out(sizeof(header) + payload_size);
        std::memcpy(out.data(), &header, sizeof(header));
        std::memcpy(out.data() + sizeof(header), payload, payload_size);
        return out;
    }

    template <typename Packet>
    std::vector<uint8_t> buildBinaryPacket(FramePayloadType type,
                                           uint64_t t0_ns,
                                           uint64_t t1_ns,
                                           const Packet& packet) {
        return build(
            type,
            to_u32(FrameFlags::PAYLOAD_BINARY),
            t0_ns,
            t1_ns,
            reinterpret_cast<const uint8_t*>(&packet),
            static_cast<uint32_t>(sizeof(Packet))
        );
    }

private:
    uint64_t session_id_hi_;
    uint64_t session_id_lo_;
    uint64_t seq_ = 0;
};

class AudioBlockPublisher {
public:
    explicit AudioBlockPublisher(DataFrameBuilder& frame_builder)
        : frame_builder_(frame_builder) {}

    std::vector<uint8_t> publish(uint64_t block_id,
                                 uint64_t t0_ns,
                                 uint64_t t1_ns,
                                 uint32_t sample_rate_hz,
                                 uint16_t channels_count,
                                 uint16_t bytes_per_sample,
                                 uint32_t frames_count,
                                 const uint8_t* pcm,
                                 uint32_t pcm_size) {
        AudioBlockBinaryHeader audio{};
        audio.audio_block_id = block_id;
        audio.t0_ns = t0_ns;
        audio.t1_ns = t1_ns;
        audio.sample_rate_hz = sample_rate_hz;
        audio.channels_count = channels_count;
        audio.bytes_per_sample = bytes_per_sample;
        audio.frames_count = frames_count;
        audio.layout = 0u;
        audio.data_size = pcm_size;

        std::vector<uint8_t> payload(sizeof(audio) + pcm_size);
        std::memcpy(payload.data(), &audio, sizeof(audio));
        std::memcpy(payload.data() + sizeof(audio), pcm, pcm_size);

        return frame_builder_.build(FramePayloadType::AUDIO_BLOCK,
                                    to_u32(FrameFlags::PAYLOAD_BINARY),
                                    t0_ns,
                                    t1_ns,
                                    payload.data(),
                                    static_cast<uint32_t>(payload.size()));
    }

private:
    DataFrameBuilder& frame_builder_;
};

class ImuWindowPublisher {
public:
    explicit ImuWindowPublisher(DataFrameBuilder& frame_builder)
        : frame_builder_(frame_builder) {}

    std::vector<uint8_t> publish(const ImuWindowPacket& packet) {
        return frame_builder_.buildBinaryPacket(FramePayloadType::IMU_WINDOW,
                                                packet.t0_ns,
                                                packet.t1_ns,
                                                packet);
    }

private:
    DataFrameBuilder& frame_builder_;
};

class CanTelemetryPublisher {
public:
    explicit CanTelemetryPublisher(DataFrameBuilder& frame_builder)
        : frame_builder_(frame_builder) {}

    std::vector<uint8_t> publishDecoded(const CanDecodedValuePacket& packet) {
        return frame_builder_.buildBinaryPacket(FramePayloadType::CAN_DECODED_VALUE,
                                                packet.t_ns,
                                                packet.t_ns,
                                                packet);
    }

    std::vector<uint8_t> publishRaw(const CanRawFramePacket& packet) {
        return frame_builder_.buildBinaryPacket(FramePayloadType::CAN_RAW_FRAME,
                                                packet.t_ns,
                                                packet.t_ns,
                                                packet);
    }

private:
    DataFrameBuilder& frame_builder_;
};

class TrajectoryPublisher {
public:
    explicit TrajectoryPublisher(DataFrameBuilder& frame_builder)
        : frame_builder_(frame_builder) {}

    std::vector<uint8_t> publish(const TrajectoryPointPacket& packet) {
        return frame_builder_.buildBinaryPacket(FramePayloadType::TRAJECTORY_POINT,
                                                packet.t_ns,
                                                packet.t_ns,
                                                packet);
    }

private:
    DataFrameBuilder& frame_builder_;
};

class PacketRouter {
public:
    using Handler = std::function<void(const EgoFrameHeader&, const uint8_t*, uint32_t)>;

    Handler on_audio;
    Handler on_imu;
    Handler on_can_decoded;
    Handler on_can_raw;
    Handler on_trajectory;
    Handler on_gps;
    Handler on_status;

    void route(const EgoFrameHeader& header, const uint8_t* payload) const {
        const auto type = static_cast<FramePayloadType>(header.frame_type);
        switch (type) {
            case FramePayloadType::AUDIO_BLOCK:
                if (on_audio) on_audio(header, payload, header.payload_size);
                break;
            case FramePayloadType::IMU_WINDOW:
                if (on_imu) on_imu(header, payload, header.payload_size);
                break;
            case FramePayloadType::CAN_DECODED_VALUE:
                if (on_can_decoded) on_can_decoded(header, payload, header.payload_size);
                break;
            case FramePayloadType::CAN_RAW_FRAME:
                if (on_can_raw) on_can_raw(header, payload, header.payload_size);
                break;
            case FramePayloadType::TRAJECTORY_POINT:
                if (on_trajectory) on_trajectory(header, payload, header.payload_size);
                break;
            case FramePayloadType::GPS_FIX:
                if (on_gps) on_gps(header, payload, header.payload_size);
                break;
            case FramePayloadType::SYSTEM_STATUS:
            case FramePayloadType::TIME_STATUS:
            case FramePayloadType::IMU_CALIBRATION_EVENT:
                if (on_status) on_status(header, payload, header.payload_size);
                break;
            default:
                break;
        }
    }
};

} // namespace ego::examples

#endif // EGO_MODULE_EXTENSIONS_HPP
