// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 mingkang ma
// Continuous user-space C1 acquisition; publish one measured revolution per second.
#include <cstdio>
#include <cstdlib>
#include <csignal>
#include <cmath>
#include <chrono>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstring>
#include <unistd.h>
#include <sys/stat.h>
#include "sl_lidar.h"
#include "sl_lidar_driver.h"
#include "scan_validity.h"

static volatile sig_atomic_t stopping = 0;
static void on_signal(int) { stopping = 1; }
static void checked(sl_result result, const char* label) {
    if (SL_IS_FAIL(result)) {
        char message[120];
        std::snprintf(message, sizeof(message), "%s failed: 0x%08x", label, unsigned(result));
        throw std::runtime_error(message);
    }
}
using File = std::unique_ptr<FILE, decltype(&std::fclose)>;
static File create_file(const std::string& name) {
    File file(std::fopen(name.c_str(), "w"), &std::fclose);
    if (!file) throw std::runtime_error("Cannot create " + name);
    return file;
}
static void finish_file(File& file) {
    if (std::fflush(file.get()) || std::ferror(file.get())) throw std::runtime_error("Output write failed");
    if (std::fclose(file.release())) throw std::runtime_error("Output close failed");
}
static void publish(const std::string& temp, const std::string& final) {
    if (std::rename(temp.c_str(), final.c_str())) throw std::runtime_error("Cannot publish " + final);
}
struct LidarSession {
    std::unique_ptr<sl::IChannel> channel;
    std::unique_ptr<sl::ILidarDriver> driver;
    bool connected = false;
    ~LidarSession() {
        if (connected && driver) {
            driver->stop();
            usleep(200000);
            driver->setMotorSpeed(0);
            driver->disconnect();
        }
    }
};

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr, "Usage: %s /dev/c1lidar output-directory\nContinues until SIGINT or SIGTERM; display snapshots at 1 Hz.\n", argv[0]);
        return 2;
    }
    std::signal(SIGINT, on_signal);
    std::signal(SIGTERM, on_signal);
    setvbuf(stdout, nullptr, _IOLBF, 0);
    try {
        const std::string directory = argv[2];
        const std::string frames_dir = directory + "/frames";
        if (mkdir(frames_dir.c_str(), 0755)) throw std::runtime_error("Use a new output directory without a frames subdirectory");
        LidarSession session;
        auto driver_result = sl::createLidarDriver(); checked(driver_result.err, "createLidarDriver");
        session.driver.reset(*driver_result);
        auto channel_result = sl::createSerialPortChannel(argv[1], 460800); checked(channel_result.err, "createSerialPortChannel");
        session.channel.reset(*channel_result);
        if (!session.driver || !session.channel) throw std::runtime_error("SDK allocation failed");
        auto* driver = session.driver.get();
        checked(driver->connect(session.channel.get()), "connect"); session.connected = true;
        sl_lidar_response_device_info_t info{};
        checked(driver->getDeviceInfo(info), "getDeviceInfo");
        if (info.model != 0x41) throw std::runtime_error("Expected C1 (model 0x41)");
        sl_lidar_response_device_health_t health{};
        checked(driver->getHealth(health), "getHealth");
        if (health.status == SL_LIDAR_STATUS_ERROR) throw std::runtime_error("C1 reports internal error");
        std::printf("C1 LIVE | user space | SDK %s | %s @ 460800\nModel: 0x%02x | Health: %u\nSerial: ", SL_LIDAR_SDK_VERSION, argv[1], info.model, health.status);
        for (auto byte : info.serialnum) std::printf("%02X", byte);
        std::puts("");
        checked(driver->setMotorSpeed(), "setMotorSpeed");
        sl::LidarScanMode mode{};
        checked(driver->startScan(false, true, 0, &mode), "startScan");
        std::printf("Selected mode: %.64s; live until stopped; display 1 Hz\n", mode.scan_mode);
        using Clock = std::chrono::steady_clock;
        const auto start = Clock::now();
        auto next_publish = start;
        unsigned warmup = 0, failures = 0;
        unsigned long frames = 0, samples = 0, valid_total = 0, sequence = 0;
        std::string last_csv;
        size_t last_samples = 0, last_valid = 0;
        double last_elapsed = 0;
        while (!stopping) {
            sl_lidar_response_measurement_node_hq_t nodes[8192];
            size_t count = sizeof(nodes) / sizeof(nodes[0]);
            auto result = driver->grabScanDataHq(nodes, count, 1000);
            if (SL_IS_FAIL(result)) {
                if (stopping) break;
                if (++failures >= 3) checked(result, "grabScanDataHq (3 failures)");
                continue;
            }
            failures = 0;
            if (warmup++ < 5) continue;
            if (count == 0) continue;
            checked(prepare_measured_scan(*driver, nodes, count), "prepare_measured_scan");
            ++frames; samples += count;
            size_t valid = 0;
            for (size_t i = 0; i < count; ++i)
                if (nodes[i].dist_mm_q2 && (nodes[i].quality >> SL_LIDAR_RESP_MEASUREMENT_QUALITY_SHIFT)) ++valid;
            valid_total += valid;
            const auto now = Clock::now();
            if (now < next_publish) continue;
            next_publish = now + std::chrono::seconds(1);
            const double elapsed = std::chrono::duration<double>(now - start).count();
            ++sequence;
            const std::string csv = frames_dir + "/" + std::to_string(sequence) + ".csv";
            auto file = create_file(csv + ".tmp");
            std::fputs("scan_id,elapsed_s,angle_deg,distance_m,quality,valid,x_m,y_m,angle_z_q14,dist_mm_q2,quality_raw,flag\n", file.get());
            for (size_t i = 0; i < count; ++i) {
                const auto& node = nodes[i];
                const double angle = node.angle_z_q14 * 90.0 / 16384.0;
                const double distance = node.dist_mm_q2 / 4000.0;
                const unsigned quality = node.quality >> SL_LIDAR_RESP_MEASUREMENT_QUALITY_SHIFT;
                const bool good = distance > 0 && quality > 0;
                std::fprintf(file.get(), "%lu,%.6f,%.6f,%.6f,%u,%d,", frames, elapsed, angle, distance, quality, good);
                if (good) {
                    const double radians = angle * 3.14159265358979323846 / 180.;
                    std::fprintf(file.get(), "%.6f,%.6f", distance * std::cos(radians), -distance * std::sin(radians));
                } else std::fputc(',', file.get());
                std::fprintf(file.get(), ",%u,%u,%u,%u\n", node.angle_z_q14, node.dist_mm_q2, node.quality, node.flag);
            }
            finish_file(file); publish(csv + ".tmp", csv);
            auto meta = create_file(csv + ".json.tmp");
            std::fprintf(meta.get(), "{\"live\":true,\"timed\":false,\"sequence\":%lu,\"elapsed_seconds\":%.6f,\"frames\":1,\"samples\":%zu,\"valid_points\":%zu,\"total_frames\":%lu,\"total_samples\":%lu,\"total_valid_points\":%lu,\"refresh_target_hz\":1,\"stop_command_ok\":false}\n", sequence, elapsed, count, valid, frames, samples, valid_total);
            finish_file(meta); publish(csv + ".json.tmp", csv + ".json");
            auto pointer = create_file(directory + "/live.json.tmp");
            std::fprintf(pointer.get(), "{\"sequence\":%lu,\"csv\":\"frames/%lu.csv\",\"elapsed_seconds\":%.6f,\"total_frames\":%lu}\n", sequence, sequence, elapsed, frames);
            finish_file(pointer); publish(directory + "/live.json.tmp", directory + "/live.json");
            // Retain eight displayed revolutions. This bounds disk use during long sessions.
            if (sequence > 8) {
                const std::string expired = frames_dir + "/" + std::to_string(sequence - 8) + ".csv";
                std::remove(expired.c_str()); std::remove((expired + ".json").c_str());
            }
            last_csv = csv; last_samples = count; last_valid = valid; last_elapsed = elapsed;
            std::printf("LIVE_FRAME %lu elapsed=%.3f frame=%lu valid=%zu\n", sequence, elapsed, frames, valid);
        }
        checked(driver->stop(), "stop");
        const double duration = std::chrono::duration<double>(Clock::now() - start).count();
        auto summary = create_file(directory + "/session.json.tmp");
        std::fprintf(summary.get(), "{\"mode\":\"continuous\",\"execution_context\":\"user space\",\"elapsed_seconds\":%.6f,\"total_frames\":%lu,\"total_samples\":%lu,\"total_valid_points\":%lu,\"display_frames\":%lu,\"last_frame_elapsed_seconds\":%.6f,\"last_frame_samples\":%zu,\"last_frame_valid_points\":%zu,\"stop_requested\":true,\"stop_command_ok\":true,\"refresh_target_hz\":1}\n", duration, frames, samples, valid_total, sequence, last_elapsed, last_samples, last_valid);
        finish_file(summary); publish(directory + "/session.json.tmp", directory + "/session.json");
        std::printf("LIVE STOPPED: %.3f seconds, %lu rotations, %lu valid points, %lu display frames; stop command OK\n", duration, frames, valid_total, sequence);
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "ERROR: %s\n", error.what());
        return 1;
    }
}
