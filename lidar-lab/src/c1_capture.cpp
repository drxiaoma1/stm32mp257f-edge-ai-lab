// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 mingkang ma
// Bounded acquisition using the APIs shown in WEEK8, slides 34-36.
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
#include <algorithm>
#include <unistd.h>
#include "sl_lidar.h"
#include "sl_lidar_driver.h"

static volatile sig_atomic_t interrupted = 0;
static void interrupt_handler(int) { interrupted = 1; }
static void check(sl_result result, const char* operation) {
    if (SL_IS_FAIL(result)) {
        char message[160];
        std::snprintf(message, sizeof(message), "%s failed: 0x%08x", operation, unsigned(result));
        throw std::runtime_error(message);
    }
}
struct Session {
    // Delete driver before channel; always stop a scan on normal error/interrupt.
    std::unique_ptr<sl::IChannel> channel;
    std::unique_ptr<sl::ILidarDriver> driver;
    bool connected = false;
    ~Session() {
        if (driver && connected) {
            driver->stop();
            usleep(200000);
            driver->setMotorSpeed(0);
            driver->disconnect();
            std::fprintf(stderr, "Scan stopped; channel disconnected.\n");
        }
    }
};
int main(int argc, char** argv) {
    bool timed = argc == 5 && std::strcmp(argv[2], "--seconds") == 0;
    if (argc != 4 && !timed) {
        std::fprintf(stderr, "Usage: %s /dev/ttyUSB0 scans output.csv\n       %s /dev/ttyUSB0 --seconds 10 output.csv\n", argv[0], argv[0]);
        return 2;
    }
    char* end = nullptr;
    long requested = timed ? 0 : std::strtol(argv[2], &end, 10);
    double seconds = timed ? std::strtod(argv[3], &end) : 0;
    if (!end || *end || (timed ? (!std::isfinite(seconds) || seconds < 1 || seconds > 3600) : (requested < 1 || requested > 10000))) {
        std::fprintf(stderr, "scans: 1..10000; seconds: 1..3600\n"); return 2;
    }
    const char* output = timed ? argv[4] : argv[3];
    std::signal(SIGINT, interrupt_handler);
    std::signal(SIGTERM, interrupt_handler);
    setvbuf(stdout, nullptr, _IOLBF, 0);
    try {
        std::unique_ptr<FILE, decltype(&std::fclose)> csv(std::fopen(output, "wx"), &std::fclose);
        if (!csv) throw std::runtime_error("Cannot create output file (choose a new filename)");
        Session session;
        auto d = sl::createLidarDriver(); check(d.err, "createLidarDriver");
        session.driver.reset(*d);
        auto c = sl::createSerialPortChannel(argv[1], 460800); check(c.err, "createSerialPortChannel");
        session.channel.reset(*c);
        if (!session.driver || !session.channel) throw std::runtime_error("SDK allocation failed");
        auto* drv = session.driver.get();
        check(drv->connect(session.channel.get()), "connect"); session.connected = true;
        sl_lidar_response_device_info_t info{};
        check(drv->getDeviceInfo(info), "getDeviceInfo");
        std::string model;
        check(drv->getModelNameDescriptionString(model, false, &info), "getModelName");
        const char* student_name = std::getenv("C1_STUDENT_NAME");
        const char* student_id = std::getenv("C1_STUDENT_ID");
        std::printf("C1 point-cloud experiment | %s | %s\nSDK: %s\nPort: %s @ 460800, 8N1\nModel: %s (0x%02x)\nSerial: ", student_name ? student_name : "mingkang ma", student_id ? student_id : "523031910621", SL_LIDAR_SDK_VERSION, argv[1], model.c_str(), info.model);
        for (unsigned char b : info.serialnum) std::printf("%02X", b);
        std::printf("\nFirmware: %u.%02u\nHardware: %u\n", info.firmware_version >> 8, info.firmware_version & 255, info.hardware_version);
        sl_lidar_response_device_health_t health{};
        check(drv->getHealth(health), "getHealth");
        std::printf("Health: %u (0=OK); error_code=%u\n", health.status, health.error_code);
        if (health.status == SL_LIDAR_STATUS_ERROR) throw std::runtime_error("Lidar reports internal error");
        std::vector<sl::LidarScanMode> modes;
        check(drv->getAllSupportedScanModes(modes), "getAllSupportedScanModes");
        for (const auto& m : modes)
            std::printf("Supported mode %u: %.64s; %.1f us/sample; %.1f m maximum\n", m.id, m.scan_mode, m.us_per_sample, m.max_distance);
        drv->setMotorSpeed();
        sl::LidarScanMode used{};
        check(drv->startScan(false, true, 0, &used), "startScan");
        std::printf("Selected mode: %.64s; target %s: %.3f\n", used.scan_mode, timed ? "seconds" : "scans", timed ? seconds : double(requested));
        std::fprintf(csv.get(), "scan_id,elapsed_s,angle_deg,distance_m,quality,valid,x_m,y_m,angle_z_q14,dist_mm_q2,quality_raw,flag\n");
        using Clock = std::chrono::steady_clock;
        auto start = Clock::now();
        double first = 0, last = 0;
        long frames = 0; size_t total = 0, valid_total = 0;
        int warmup = 0, failures = 0;
        while ((timed || frames < requested) && !interrupted) {
            double remaining = seconds - std::chrono::duration<double>(Clock::now() - start).count();
            if (timed && remaining <= 0) break;
            sl_lidar_response_measurement_node_hq_t nodes[8192];
            size_t count = sizeof(nodes) / sizeof(nodes[0]);
            unsigned timeout = timed ? unsigned(std::max(1.0, std::min(2000.0, std::ceil(remaining * 1000)))) : 2000;
            sl_result result = drv->grabScanDataHq(nodes, count, timeout);
            if (SL_IS_FAIL(result)) {
                if (timed && std::chrono::duration<double>(Clock::now() - start).count() >= seconds) break;
                std::fprintf(stderr, "Scan read failed: 0x%08x\n", unsigned(result));
                if (++failures >= 3) check(result, "grabScanDataHq (3 consecutive failures)");
                continue;
            }
            failures = 0;
            if (warmup++ < 5) continue;
            check(drv->ascendScanData(nodes, count), "ascendScanData");
            double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
            if (frames == 0) first = elapsed;
            last = elapsed;
            size_t valid = 0;
            for (size_t i = 0; i < count; ++i) {
                const auto& n = nodes[i];
                double angle = n.angle_z_q14 * 90.0 / 16384.0;
                double distance = n.dist_mm_q2 / 4000.0;
                unsigned quality = n.quality >> SL_LIDAR_RESP_MEASUREMENT_QUALITY_SHIFT;
                bool good = distance > 0 && quality > 0;
                std::fprintf(csv.get(), "%ld,%.6f,%.6f,%.6f,%u,%d,", frames, elapsed, angle, distance, quality, good);
                if (good) {
                    double radians = angle * 3.14159265358979323846 / 180.0;
                    // SDK angle increases clockwise; plot +x at SDK zero and +y counterclockwise.
                    std::fprintf(csv.get(), "%.6f,%.6f", distance * std::cos(radians), -distance * std::sin(radians));
                    ++valid;
                } else std::fputc(',', csv.get());
                std::fprintf(csv.get(), ",%u,%u,%u,%u\n", n.angle_z_q14, n.dist_mm_q2, n.quality, n.flag);
            }
            if (std::fflush(csv.get()) != 0) throw std::runtime_error("CSV write failed");
            ++frames; total += count; valid_total += valid;
            if (frames == 1 || frames % 10 == 0 || frames == requested) {
                if (timed) std::printf("Scan %ld: %zu samples, %zu valid; elapsed %.3f / %.3f s\n", frames, count, valid, elapsed, seconds);
                else std::printf("Scan %ld/%ld: %zu samples, %zu valid; elapsed %.3f s\n", frames, requested, count, valid, elapsed);
            }
        }
        double scan_window = std::chrono::duration<double>(Clock::now() - start).count();
        check(drv->stop(), "stop scan");
        double hz = frames > 1 && last > first ? (frames - 1) / (last - first) : 0;
        std::printf("Summary: %ld scans, %zu samples, %zu valid, %.3f Hz\nScan window: %.6f seconds (steady clock)\nSaved: %s\n", frames, total, valid_total, hz, scan_window, output);
        if (interrupted) { std::fprintf(stderr, "Interrupted; partial CSV preserved.\n"); return 130; }
        if (!valid_total) throw std::runtime_error("No valid measurements");
        std::string meta_name = std::string(output) + ".json";
        std::unique_ptr<FILE, decltype(&std::fclose)> meta(std::fopen(meta_name.c_str(), "wx"), &std::fclose);
        if (!meta) throw std::runtime_error("Cannot create metadata file");
        std::fprintf(meta.get(), "{\"timed\":%s,\"requested_seconds\":%.6f,\"scan_window_seconds\":%.6f,\"frames\":%ld,\"samples\":%zu,\"valid_points\":%zu,\"scan_rate_hz\":%.6f,\"first_record_s\":%.6f,\"last_record_s\":%.6f,\"stop_command_ok\":true}\n",timed?"true":"false",seconds,scan_window,frames,total,valid_total,hz,first,last);
        if (std::fflush(meta.get()) != 0) throw std::runtime_error("Metadata write failed");
        std::puts("CAPTURE PASSED");
        return 0;
    } catch (const std::exception& ex) {
        std::fprintf(stderr, "ERROR: %s\n", ex.what());
        return 1;
    }
}
