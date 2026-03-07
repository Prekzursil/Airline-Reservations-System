cmake_minimum_required(VERSION 3.20)

project(AirlineReservationsSystem LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(ENABLE_COVERAGE "Enable gcov-style coverage flags" OFF)

if(ENABLE_COVERAGE)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-O0 -g --coverage)
    add_link_options(--coverage)
  endif()
endif()

include(FetchContent)
set(FETCHCONTENT_UPDATES_DISCONNECTED ON)

set(HTTPLIB_REQUIRE_OPENSSL OFF CACHE BOOL "" FORCE)
set(HTTPLIB_REQUIRE_ZLIB OFF CACHE BOOL "" FORCE)
set(HTTPLIB_COMPILE OFF CACHE BOOL "" FORCE)
set(HTTPLIB_INSTALL OFF CACHE BOOL "" FORCE)
set(HTTPLIB_TEST OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
  cpp_httplib
  GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
  GIT_TAG v0.16.3
  GIT_SHALLOW TRUE
)

FetchContent_Declare(
  nlohmann_json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG v3.12.0
  GIT_SHALLOW TRUE
)

set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.15.2
  GIT_SHALLOW TRUE
)

FetchContent_MakeAvailable(cpp_httplib nlohmann_json googletest)

set(CORE_SOURCES
  src/Airplane.cpp
  src/Booking.cpp
  src/Customer.cpp
  src/Person.cpp
  src/ReservationSystem.cpp
  src/ReservationSystemHelpers.cpp
  src/Seat.cpp
)

add_library(airline_core ${CORE_SOURCES})
target_include_directories(airline_core PUBLIC ${PROJECT_SOURCE_DIR}/src)

add_executable(airline_reservation_system src/main.cpp)
target_link_libraries(airline_reservation_system PRIVATE airline_core)

add_executable(airline_api_server src/api_server_main.cpp)
target_include_directories(
  airline_api_server
  PRIVATE
    ${cpp_httplib_SOURCE_DIR}
    ${nlohmann_json_SOURCE_DIR}/include
)
target_link_libraries(
  airline_api_server
  PRIVATE
    airline_core
    nlohmann_json::nlohmann_json
    httplib::httplib
)
if(WIN32)
  target_link_libraries(airline_api_server PRIVATE ws2_32 wsock32)
endif()

enable_testing()

add_executable(
  run_tests_executable
  tests/main_test.cpp
  tests/program_entry_test.cpp
  tests/airplane_test.cpp
  tests/api_server_test.cpp
  tests/booking_test.cpp
  tests/customer_test.cpp
  tests/person_test.cpp
  tests/reservation_system_helpers_test.cpp
  tests/reservation_system_test.cpp
  tests/seat_test.cpp
)
target_include_directories(
  run_tests_executable
  PRIVATE
    ${googletest_SOURCE_DIR}/googletest/include
    ${cpp_httplib_SOURCE_DIR}
    ${nlohmann_json_SOURCE_DIR}/include
)
target_link_libraries(
  run_tests_executable
  PRIVATE
    airline_core
    GTest::gtest
    nlohmann_json::nlohmann_json
    httplib::httplib
)
if(WIN32)
  target_link_libraries(run_tests_executable PRIVATE ws2_32 wsock32)
endif()

include(GoogleTest)
gtest_discover_tests(run_tests_executable DISCOVERY_TIMEOUT 120 TEST_LIST AIRLINE_DISCOVERED_TESTS)
if(AIRLINE_DISCOVERED_TESTS)
  set_tests_properties(${AIRLINE_DISCOVERED_TESTS} PROPERTIES TIMEOUT 120)
endif()

add_test(
  NAME airline_cli_smoke_exit
  COMMAND
    bash
    ${CMAKE_SOURCE_DIR}/tests/run_cli_scenario.sh
    $<TARGET_FILE:airline_reservation_system>
    ${CMAKE_SOURCE_DIR}/tests/cli_exit_input.txt
    "Welcome to the Airline Reservation System!"
    "Exiting system. Goodbye!"
    "Thank you for using the Airline Reservation System."
)

add_test(
  NAME airline_cli_smoke_menu_flow
  COMMAND
    bash
    ${CMAKE_SOURCE_DIR}/tests/run_cli_scenario.sh
    $<TARGET_FILE:airline_reservation_system>
    ${CMAKE_SOURCE_DIR}/tests/cli_menu_flow_input.txt
    "Customer Coverage User with ID CUST0003 added successfully."
    "Booking successful! Booking ID:"
    "Airplane FL303 added successfully."
)
set_tests_properties(airline_cli_smoke_exit airline_cli_smoke_menu_flow PROPERTIES TIMEOUT 120)
