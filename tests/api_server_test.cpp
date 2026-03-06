// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <chrono>
#include <sstream>
#include <thread>

#define main airline_api_server_entry_main
#include "../src/api_server_main.cpp"
#undef main

namespace {

class ApiServerRoutesTest : public ::testing::Test {
protected:
    std::stringstream input;
    std::stringstream output;
    ReservationSystem system{input, output};
    httplib::Server server;
    std::thread server_thread;
    int port = -1;

    void start_server() {
        register_routes(server, system);
        port = server.bind_to_any_port("127.0.0.1");
        ASSERT_GT(port, 0);

        server_thread = std::thread([this]() {
            server.listen_after_bind();
        });

        httplib::Client probe("127.0.0.1", port);
        for (int attempt = 0; attempt < 50; ++attempt) {
            if (probe.Get("/api/airplanes")) {
                return;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        FAIL() << "Server did not start listening in time";
    }

    void TearDown() override {
        server.stop();
        if (server_thread.joinable()) {
            server_thread.join();
        }
    }
};

TEST(ApiServerHelpersTest, ErrorStatusHelpersReturnExpectedCodes) {
    EXPECT_TRUE(contains_fragment("already booked", "booked"));
    EXPECT_FALSE(contains_fragment("abc", "abcd"));

    EXPECT_EQ(booking_error_status("Seat already booked"), 409);
    EXPECT_EQ(booking_error_status("Customer not found"), 404);
    EXPECT_EQ(booking_error_status("Insufficient funds"), 402);
    EXPECT_EQ(booking_error_status("other"), 400);

    EXPECT_EQ(cancel_error_status("Booking not found"), 404);
    EXPECT_EQ(cancel_error_status("already cancelled"), 409);
    EXPECT_EQ(cancel_error_status("other"), 500);

    EXPECT_EQ(swap_error_status("not found"), 404);
    EXPECT_EQ(swap_error_status("not confirmed"), 404);
    EXPECT_EQ(swap_error_status("Cannot swap a booking with itself"), 400);
    EXPECT_EQ(swap_error_status("only supported for bookings on the same flight"), 400);
    EXPECT_EQ(swap_error_status("other"), 500);
}

TEST(ApiServerEntryTest, RunApiServerReportsFailureWhenListenFails) {
    std::stringstream input;
    std::stringstream out;
    std::stringstream err;
    ReservationSystem system(input, out);
    httplib::Server server;

    const auto original_callback = g_server_listen_callback;
    g_server_listen_callback = +[](httplib::Server&, const char*, int) {
        return false;
    };

    EXPECT_EQ(run_api_server(system, server, out, err), 1);
    EXPECT_NE(out.str().find("Starting API server"), std::string::npos);
    EXPECT_NE(err.str().find("Failed to start server!"), std::string::npos);

    g_server_listen_callback = original_callback;
}

TEST(ApiServerEntryTest, MainReturnsSuccessWhenListenHookSucceeds) {
    std::istringstream input;
    std::ostringstream output_stream;
    std::ostringstream error_stream;

    std::streambuf* original_in = std::cin.rdbuf(input.rdbuf());
    std::streambuf* original_out = std::cout.rdbuf(output_stream.rdbuf());
    std::streambuf* original_err = std::cerr.rdbuf(error_stream.rdbuf());

    const auto original_callback = g_server_listen_callback;
    g_server_listen_callback = +[](httplib::Server&, const char*, int) {
        return true;
    };

    const int exit_code = airline_api_server_entry_main();

    g_server_listen_callback = original_callback;
    std::cin.rdbuf(original_in);
    std::cout.rdbuf(original_out);
    std::cerr.rdbuf(original_err);

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output_stream.str().find("Starting API server"), std::string::npos);
    EXPECT_TRUE(error_stream.str().empty());
}

TEST_F(ApiServerRoutesTest, ListsDefaultAirplanesAndCustomers) {
    start_server();
    httplib::Client client("127.0.0.1", port);

    const auto airplanes_response = client.Get("/api/airplanes");
    ASSERT_TRUE(airplanes_response);
    EXPECT_EQ(airplanes_response->status, 200);
    const json airplanes = json::parse(airplanes_response->body);
    ASSERT_EQ(airplanes.size(), 2);

    const auto customers_response = client.Get("/api/customers");
    ASSERT_TRUE(customers_response);
    EXPECT_EQ(customers_response->status, 200);
    const json customers = json::parse(customers_response->body);
    ASSERT_EQ(customers.size(), 2);
}

TEST_F(ApiServerRoutesTest, SupportsCustomerBookingLifecycleRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", port);

    const auto new_customer_response = client.Post(
        "/api/customers",
        json{{"name", "Server User"}, {"age", 31}, {"money", 500.0}, {"autoGenerate", false}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(new_customer_response);
    ASSERT_EQ(new_customer_response->status, 201);
    const json new_customer = json::parse(new_customer_response->body);
    const std::string customer_id = new_customer.at("personId").get<std::string>();

    const auto customer_details = client.Get(("/api/customers/" + customer_id).c_str());
    ASSERT_TRUE(customer_details);
    EXPECT_EQ(customer_details->status, 200);

    const auto booking_response = client.Post(
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", "FL101"}, {"seatId", "4A"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(booking_response);
    ASSERT_EQ(booking_response->status, 201);
    const json booking = json::parse(booking_response->body);
    const std::string booking_id = booking.at("bookingId").get<std::string>();

    const auto airplane_details = client.Get("/api/airplanes/FL101");
    ASSERT_TRUE(airplane_details);
    EXPECT_EQ(airplane_details->status, 200);
    EXPECT_NE(airplane_details->body.find(booking_id), std::string::npos);

    const auto cancel_response = client.Delete(("/api/bookings/" + booking_id).c_str());
    ASSERT_TRUE(cancel_response);
    EXPECT_EQ(cancel_response->status, 200);

    const auto options_response = client.Options("/api/bookings");
    ASSERT_TRUE(options_response);
    EXPECT_EQ(options_response->status, 204);
}

TEST_F(ApiServerRoutesTest, ReturnsBadRequestForMalformedPayloads) {
    start_server();
    httplib::Client client("127.0.0.1", port);

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

}  // namespace
