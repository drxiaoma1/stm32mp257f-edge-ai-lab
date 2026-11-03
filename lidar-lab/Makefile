# Run after sourcing the official OpenSTLinux SDK environment.
SDK_LIBRARY := output/libsl_lidar_sdk.a
SDK_INCLUDE := vendor/rplidar_sdk/sdk/include
PROGRAMS := output/c1_capture output/c1_live
.PHONY: all clean
all: $(PROGRAMS)
output/%: src/%.cpp src/scan_validity.h $(SDK_LIBRARY)
	$(CXX) $(CXXFLAGS) -std=c++11 -Wall -Wextra -Werror -Wno-ignored-attributes -I$(SDK_INCLUDE) $< $(SDK_LIBRARY) $(LDFLAGS) -lpthread -lrt -o $@
$(SDK_LIBRARY):
	@echo 'Build the official SDK library first: SDK_ENV=... bash scripts/build.sh'; exit 1
clean:
	rm -f $(PROGRAMS)
