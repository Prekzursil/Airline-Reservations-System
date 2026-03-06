// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <atomic>
#include <chrono>
#include <functional>
#include <optional>
#include <sstream>
#include <string>
#include <thread>

#include "Airplane.h"
#include "Booking.h"
#include "Customer.h"
#include "ReservationSystem.h"
#include "Seat.h"

using json = nlohmann::json;

void to_json(json& j, const Seat& s);
void to_json(json& j, const Airplane& p);
void to_json(json& j, const Customer& c);
bool listen_on_host(httplib::Server& server, const char* host, int port);
using ServerListenCallback = std::function<bool(httplib::Server&, const char*, int)>;
json build_airplane_details(const ReservationSystem& airline_system, const Airplane& plane);
void register_routes(httplib::Server& server, ReservationSystem& airline_system);
int run_api_server(
    ReservationSystem& airline_system,
    httplib::Server& server,
    std::ostream& out,
    std::ostream& err,
    ServerListenCallback listen_callback);

namespace {

constexpr char kJsonMimeType[] = "application/json";
constexpr auto kStartupTimeout = std::chrono::seconds(2);
constexpr auto kPollInterval = std::chrono::milliseconds(20);
constexpr int kTestPortStart = 18080;
constexpr int kTestPortCount = 32;

std::atomic<int> g_selected_port{-1};

class ScopedStreamRedirect {
public:
    ScopedStreamRedirect(std::ostream& stream, std::streambuf* replacement)
        : stream_(stream), original_(stream.rdbuf(replacement)) {}

    ~ScopedStreamRedirect() {
        stream_.rdbuf(original_);
    }

    ScopedStreamRedirect(const ScopedStreamRedirect&) = delete;
    ScopedStreamRedirect& operator=(const ScopedStreamRedirect&) = delete;

private:
    std::ostream& stream_;
    std::streambuf* original_;
};

class CallbackStateGuard {
public:
    ~CallbackStateGuard() {
        g_selected_port.store(-1, std::memory_order_release);
    }
};

bool listen_on_first_available_port(httplib::Server& server, const char* host, int) {
    for (int offset = 0; offset < kTestPortCount; ++offset) {
        const int port = kTestPortStart + offset;
        g_selected_port.store(port, std::memory_order_release);
        if (listen_on_host(server, host, port)) {
            return true;
        }
    }

    g_selected_port.store(-1, std::memory_order_release);
    return false;
}

bool wait_for_status(int port, const std::string& path, int expected_status) {
    const auto deadline = std::chrono::steady_clock::now() + kStartupTimeout;
    httplib::Client client("127.0.0.1", port);

    while (std::chrono::steady_clock::now() < deadline) {
        if (const auto response = client.Get(path)) {
            if (response->status == expected_status) {
                return true;
            }
        }
        std::this_thread::sleep_for(kPollInterval);
    }

    return false;
}

bool wait_for_selected_port() {
    const auto deadline = std::chrono::steady_clock::now() + kStartupTimeout;
    while (std::chrono::steady_clock::now() < deadline) {
        if (g_selected_port.load(std::memory_order_acquire) >= 0) {
            return true;
        }
        std::this_thread::sleep_for(kPollInterval);
    }

    return false;
}

class RealApiRoutesTest : public ::testing::Test {
protected:
    void SetUp() override {
        register_routes(server_, system_);
        port_ = server_.bind_to_any_port("127.0.0.1");
        ASSERT_GT(port_, 0);

        server_thread_ = std::jthread([this]() {
            server_.listen_after_bind();
        });
        server_.wait_until_ready();
    }

    void TearDown() override {
        server_.stop();
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    httplib::Client make_client() const {
        return httplib::Client("127.0.0.1", port_);
    }

private:
    std::stringstream input_;
    std::stringstream output_;
    ReservationSystem system_{input_, output_};
    httplib::Server server_;
    std::jthread server_thread_;
    int port_ = -1;
};

TEST(ApiServerAdditionalHelpersTest, SerializationHelpersCoverCountedFields) {
    Seat seat("1A", SeatClass::BUSINESS, 100.0);
    ASSERT_TRUE(seat.bookSeat());
    json seat_json;
    to_json(seat_json, seat);
    EXPECT_EQ(seat_json.at("isBooked"), seat.getIsBooked());
    EXPECT_EQ(seat_json.at("price"), seat.getPrice());

    Airplane plane("HX123", 1, 1);
    ASSERT_TRUE(plane.bookSpecificSeat("1A"));
    json airplane_json;
    to_json(airplane_json, plane);
    EXPECT_EQ(airplane_json.at("capacity"), plane.getCapacity());
    EXPECT_EQ(airplane_json.at("bookedSeatsCount"), plane.getBookedSeatsCount());
    EXPECT_EQ(airplane_json.at("isFull"), plane.isFull());

    Customer customer("Helper User", 29, "CUST9998", 321.5);
    json customer_json;
    to_json(customer_json, customer);
    EXPECT_EQ(customer_json.at("age"), customer.getAge());
    EXPECT_EQ(customer_json.at("money"), customer.getMoney());
}

TEST(ApiServerAdditionalHelpersTest, BuildAirplaneDetailsIncludesCapacityAndBookingCounts) {
    std::stringstream input;
    std::stringstream output;
    ReservationSystem reservation_system(input, output);
    Customer* customer = reservation_system.addCustomerInternal("Coverage User", 33, 1000.0, false);
    ASSERT_NE(customer, nullptr);

    std::string booking_error;
    Booking* booking = reservation_system.createBookingInternal(
        customer->getPersonId(),
        "FL101",
        "4A",
        booking_error);
    ASSERT_NE(booking, nullptr) << booking_error;

    const Airplane* flight = reservation_system.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(flight, nullptr);

    const json details = build_airplane_details(reservation_system, *flight);
    EXPECT_EQ(details.at("capacity"), flight->getCapacity());
    EXPECT_EQ(details.at("bookedSeatsCount"), flight->getBookedSeatsCount());
    EXPECT_EQ(details.at("isFull"), flight->isFull());
    ASSERT_FALSE(details.at("seats").empty());
}

TEST_F(RealApiRoutesTest, MalformedPayloadRoutesReturnBadRequestFromRealObjectCode) {
    httplib::Client client = make_client();

    const auto customer_response = client.Post("/api/customers", "{bad json", kJsonMimeType);
    ASSERT_TRUE(customer_response);
    EXPECT_EQ(customer_response->status, 400);

    const auto booking_response = client.Post("/api/bookings", "{bad json", kJsonMimeType);
    ASSERT_TRUE(booking_response);
    EXPECT_EQ(booking_response->status, 400);

    const auto swap_response = client.Post("/api/bookings/swap", "{bad json", kJsonMimeType);
    ASSERT_TRUE(swap_response);
    EXPECT_EQ(swap_response->status, 400);
}

TEST(ApiServerAdditionalEntryTest, RunApiServerUsesLoggerWithRealListenPath) {
    CallbackStateGuard callback_guard;

    std::stringstream input;
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    std::ostringstream log_stream;
    ScopedStreamRedirect redirect_cout(std::cout, log_stream.rdbuf());
    ReservationSystem reservation_system(input, output_stream);
    httplib::Server server;

    std::optional<int> exit_code;
    std::jthread server_thread([&]() {
        exit_code = run_api_server(
            reservation_system,
            server,
            output_stream,
            error_stream,
            listen_on_first_available_port);
    });

    ASSERT_TRUE(wait_for_selected_port());
    const int port = g_selected_port.load(std::memory_order_acquire);
    ASSERT_GT(port, 0);
    ASSERT_TRUE(wait_for_status(port, "/api/airplanes", 200));
    server.stop();
    server_thread.join();

    ASSERT_TRUE(exit_code.has_value());
    EXPECT_EQ(*exit_code, 0);
    EXPECT_NE(log_stream.str().find("HTTP GET /api/airplanes -> 200"), std::string::npos);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_TRUE(error_stream.str().empty());
}

}  // namespace
