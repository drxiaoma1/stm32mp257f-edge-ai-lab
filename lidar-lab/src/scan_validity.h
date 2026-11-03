// SPDX-License-Identifier: BSD-2-Clause
#pragma once
#include <cstddef>
#include "sl_lidar_driver.h"

// SDK ascendScanData returns OPERATION_FAIL for an all-zero-distance revolution.
// That is a valid empty measurement, not a serial transport failure.
inline sl_result prepare_measured_scan(sl::ILidarDriver& driver,
    sl_lidar_response_measurement_node_hq_t* nodes, size_t count) {
    for (size_t i = 0; i < count; ++i)
        if (nodes[i].dist_mm_q2 != 0)
            return driver.ascendScanData(nodes, count);
    return SL_RESULT_OK;
}
