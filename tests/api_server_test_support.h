#pragma once

namespace api_server_test_support {

constexpr auto kStartupTimeout = std::chrono::seconds(2);
constexpr auto kPollInterval = std::chrono::milliseconds(20);
constexpr int kTestPortStart = 18080;
constexpr int kTestPortCount = 32;

class ScopedStreamRedirect {
public:
    ScopedStreamRedirect(std::ostream& stream, const std::ostream& target)
        : stream_(stream), original_(stream.rdbuf(target.rdbuf())) {}

    ~ScopedStreamRedirect() {
        stream_.rdbuf(original_);
    }

    ScopedStreamRedirect(const ScopedStreamRedirect&) = delete;
    ScopedStreamRedirect& operator=(const ScopedStreamRedirect&) = delete;

private:
    std::ostream& stream_;
    std::streambuf* original_;
};

class ScopedServerShutdown {
public:
    ScopedServerShutdown(httplib::Server& server, std::jthread& server_thread)
        : server_(server), server_thread_(server_thread) {}

    ~ScopedServerShutdown() {
        server_.stop();
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    ScopedServerShutdown(const ScopedServerShutdown&) = delete;
    ScopedServerShutdown& operator=(const ScopedServerShutdown&) = delete;

private:
    httplib::Server& server_;
    std::jthread& server_thread_;
};

bool wait_for_status(const int port, const std::string& path, const int expected_status) {
    const auto deadline = std::chrono::steady_clock::now() + kStartupTimeout;
    httplib::Client client("127.0.0.1", port);
    while (std::chrono::steady_clock::now() < deadline) {
        if (const auto response = client.Get(path); response && response->status == expected_status) {
            return true;
        }
        std::this_thread::sleep_for(kPollInterval);
    }
    return false;
}

bool wait_for_selected_port(const std::atomic<int>& selected_port) {
    const auto deadline = std::chrono::steady_clock::now() + kStartupTimeout;
    while (std::chrono::steady_clock::now() < deadline) {
        if (selected_port.load() > 0) {
            return true;
        }
        std::this_thread::sleep_for(kPollInterval);
    }
    return false;
}

httplib::Result post_json_request(httplib::Client& client, const std::string& path, const json& payload) {
    return client.Post(path, payload.dump(), kJsonMimeType);
}

json create_customer_via_route(httplib::Client& client, const json& payload, const int expected_status = 201) {
    const auto response = post_json_request(client, "/api/customers", payload);
    EXPECT_TRUE(response);
    EXPECT_EQ(response->status, expected_status);
    if (!response) {
        return json::object();
    }
    return json::parse(response->body);
}

httplib::Result create_booking_via_route(
    httplib::Client& client,
    const std::string& customer_id,
    const std::string& flight_number,
    const std::string& seat_id) {
    return post_json_request(
        client,
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", flight_number}, {"seatId", seat_id}});
}

void expect_response_status(const httplib::Result& response, const int expected_status) {
    ASSERT_TRUE(response);
    ASSERT_EQ(response->status, expected_status);
}

json parse_json_response(const httplib::Result& response, const int expected_status) {
    expect_response_status(response, expected_status);
    return json::parse(response->body);
}

httplib::Result swap_bookings_via_route(
    httplib::Client& client,
    const std::string& first_booking_id,
    const std::string& second_booking_id) {
    return post_json_request(
        client,
        "/api/bookings/swap",
        json{{"bookingId1", first_booking_id}, {"bookingId2", second_booking_id}});
}

class ApiServerRoutesTest : public ::testing::Test {
protected:
    int bound_port() const {
        return port_;
    }

    void start_server() {
        register_routes(server_, system_);
        port_ = server_.bind_to_any_port("127.0.0.1");
        ASSERT_GT(port_, 0);

        server_thread_ = std::jthread([this]() {
            server_.listen_after_bind();
        });

        httplib::Client probe("127.0.0.1", port_);
        for (int attempt = 0; attempt < 50; ++attempt) {
            if (probe.Get("/api/airplanes")) {
                return;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        FAIL() << "Server did not start listening in time";
    }

    void TearDown() override {
        server_.stop();
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    Customer* addCustomer(
        const std::string& name = "Route User",
        int age = 30,
        double money = 500.0,
        bool auto_generate = false) {
        Customer* customer = system_.addCustomerInternal(name, age, money, auto_generate);
        if (customer == nullptr) {
            ADD_FAILURE() << "Failed to add customer";
        }
        return customer;
    }

    Booking* createBooking(const std::string& customer_id, const std::string& flight_number, const std::string& seat_id) {
        std::string booking_error;
        Booking* booking = system_.createBookingInternal(customer_id, flight_number, seat_id, booking_error);
        if (booking == nullptr) {
            ADD_FAILURE() << "Booking creation failed: " << booking_error;
        }
        return booking;
    }

private:
    std::stringstream input_;
    std::stringstream output_;
    ReservationSystem system_{input_, output_};
    httplib::Server server_;
    std::jthread server_thread_;
    int port_ = -1;
};
}  // namespace api_server_test_support
