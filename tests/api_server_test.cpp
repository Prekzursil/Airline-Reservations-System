// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <future>
#include <optional>
#include <sstream>
#include <thread>

#ifndef _WIN32
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

#include "auto_generated_customer_test_helpers.h"

#include "../src/api_server_main_body.h"

#include "api_server_test_support.h"

using namespace api_server_test_support;

namespace {

struct DefaultListenOverrideObservation {
    bool invoked = false;
    std::string host;
    int port = -1;
};

struct RealListenHarness {
    std::atomic<int> selected_port{-1};
    std::atomic<bool> force_failure{false};
};

#ifndef _WIN32
sockaddr* as_sockaddr(sockaddr_in& address) {
    return static_cast<sockaddr*>(static_cast<void*>(&address));
}

class ScopedPortOccupier {
public:
    explicit ScopedPortOccupier(const int port) {
        socket_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (socket_fd_ < 0) {
            return;
        }

        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_ANY);
        address.sin_port = htons(static_cast<uint16_t>(port));

        if (::bind(socket_fd_, as_sockaddr(address), sizeof(address)) != 0 ||
            ::listen(socket_fd_, SOMAXCONN) != 0) {
            ::close(socket_fd_);
            socket_fd_ = -1;
        }
    }

    ~ScopedPortOccupier() {
        if (socket_fd_ >= 0) {
            ::close(socket_fd_);
        }
    }

    ScopedPortOccupier(const ScopedPortOccupier&) = delete;
    ScopedPortOccupier& operator=(const ScopedPortOccupier&) = delete;
    explicit operator bool() const {
        return socket_fd_ >= 0;
    }

private:
    int socket_fd_ = -1;
};
#endif

auto make_listen_on_first_available_port(RealListenHarness& harness) {
    return [&harness](httplib::Server& server, const char* host, int) {
        if (harness.force_failure.load()) {
            harness.selected_port.store(-1);
            return false;
        }

        for (int offset = 0; offset < kTestPortCount; ++offset) {
            const int port = kTestPortStart + offset;
            harness.selected_port.store(port);
            if (listen_on_host(server, host, port)) {
                return true;
            }
        }

        harness.selected_port.store(-1);
        return false;
    };
}

void expect_real_listen_success_path() {
    RealListenHarness harness;
    auto listen_on_first_available_port = make_listen_on_first_available_port(harness);

    std::stringstream input;
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    std::ostringstream log_stream;
    ScopedStreamRedirect redirect(std::cout, log_stream);
    ReservationSystem reservation_system(input, output_stream);
    httplib::Server server;
    std::optional<int> exit_code;
    std::jthread server_thread([&error_stream, &exit_code, &listen_on_first_available_port, &output_stream, &reservation_system, &server]() {
        exit_code = run_api_server_with_listener(
            reservation_system,
            server,
            output_stream,
            error_stream,
            listen_on_first_available_port);
    });
    ScopedServerShutdown shutdown(server, server_thread);

    ASSERT_TRUE(wait_for_selected_port(harness.selected_port));
    const int port = harness.selected_port.load();
    ASSERT_TRUE(wait_for_status(port, "/api/airplanes", 200));
    server.stop();
    if (server_thread.joinable()) {
        server_thread.join();
    }

    ASSERT_TRUE(exit_code.has_value());
    EXPECT_EQ(*exit_code, 0);
    EXPECT_NE(log_stream.str().find("HTTP GET /api/airplanes -> 200"), std::string::npos);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_TRUE(error_stream.str().empty());
}

void expect_real_listen_failure_path() {
    RealListenHarness harness;
    harness.force_failure = true;
    auto listen_on_first_available_port = make_listen_on_first_available_port(harness);

    std::stringstream failure_input;
    std::ostringstream failure_output;
    std::ostringstream failure_error;
    ReservationSystem failure_reservation_system(failure_input, failure_output);
    httplib::Server failure_server;

    EXPECT_EQ(
        run_api_server_with_listener(
            failure_reservation_system,
            failure_server,
            failure_output,
            failure_error,
            listen_on_first_available_port),
        1);
    EXPECT_EQ(harness.selected_port.load(), -1);
    EXPECT_NE(failure_output.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(failure_error.str().find("Failed to start server!"), std::string::npos);
}

}  // namespace

#include "api_server_entry_and_helpers_cases.inc"
#include "api_server_routes_cases.inc"
