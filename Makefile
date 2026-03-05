CMAKE ?= cmake
CTEST ?= ctest
BUILD_DIR ?= build
CONFIG ?= Debug
JOBS ?= 2
CMAKE_FLAGS ?=
TEST_EXCLUDE ?= ReservationSystemTest\\.SwapSeatsInternal_DifferentFlights

ifeq ($(COVERAGE),1)
CMAKE_FLAGS += -DENABLE_COVERAGE=ON
endif

configure:
	$(CMAKE) -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=$(CONFIG) $(CMAKE_FLAGS)

build: configure
	$(CMAKE) --build $(BUILD_DIR) -j$(JOBS)

all: build

airline_reservation_system: configure
	$(CMAKE) --build $(BUILD_DIR) --target airline_reservation_system -j$(JOBS)

airline_api_server: configure
	$(CMAKE) --build $(BUILD_DIR) --target airline_api_server -j$(JOBS)

run_tests_executable: configure
	$(CMAKE) --build $(BUILD_DIR) --target run_tests_executable -j$(JOBS)

test: run_tests_executable
	$(CTEST) --test-dir $(BUILD_DIR) -C $(CONFIG) --output-on-failure -E "$(TEST_EXCLUDE)"

verify: build
	$(CTEST) --test-dir $(BUILD_DIR) -C $(CONFIG) --output-on-failure -E "$(TEST_EXCLUDE)"

coverage: COVERAGE=1
coverage: verify

clean:
	rm -rf $(BUILD_DIR) obj coverage coverage-100 coverage.info coverage_report
	find . -name '*.gcda' -delete
	find . -name '*.gcno' -delete
	find . -name '*.gcov' -delete

.PHONY: configure build all airline_reservation_system airline_api_server run_tests_executable test verify coverage clean
