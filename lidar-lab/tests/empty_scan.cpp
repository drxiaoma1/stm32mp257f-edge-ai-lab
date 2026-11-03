// Test-only synthetic input; never used as displayed LiDAR data.
#include <cstdio>
#include <memory>
#include "../src/scan_validity.h"
int main() {
    auto result = sl::createLidarDriver();
    if (SL_IS_FAIL(result.err)) return 1;
    std::unique_ptr<sl::ILidarDriver> driver(*result);
    sl_lidar_response_measurement_node_hq_t empty[512]{};
    auto original = driver->ascendScanData(empty, 512);
    if (original != SL_RESULT_OPERATION_FAIL) return 2;
    if (SL_IS_FAIL(prepare_measured_scan(*driver, empty, 512))) return 3;
    if (SL_IS_FAIL(prepare_measured_scan(*driver, empty, 0))) return 4;
    empty[250].dist_mm_q2 = 4000;
    empty[250].quality = 40;
    empty[250].angle_z_q14 = 32768;
    if (SL_IS_FAIL(prepare_measured_scan(*driver, empty, 512))) return 5;
    unsigned valid = 0;
    for (const auto& node : empty) if (node.dist_mm_q2) ++valid;
    if (valid != 1) return 6;
    std::printf("PASS: SDK empty-frame error 0x%08x reproduced; empty/zero-count/mixed frames handled.\n", unsigned(original));
}
