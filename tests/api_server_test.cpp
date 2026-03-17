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

#define main airline_api_server_entry_main
#include "../src/api_server_main.cpp"
#undef main

#include "api_server_test_support.h"

using namespace api_server_test_support;

namespace {

struct DefaultListenOverrideObservation {
    bool invoked = false;
    std::string host;
    int port = -1;
};

#ifndef _WIN32
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

        if (::bind(socket_fd_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0 ||
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

    bool is_listening() const {
        return socket_fd_ >= 0;
    }

private:
    int socket_fd_ = -1;
};
#endif

}  // namespace

TEST(ApiServerHelpersTest, ErrorStatusHelpersReturnExpectedCodes) {
    EXPECT_TRUE(contains_fragment("already booked", "booked"));
    EXPECT_FALSE(contains_fragment("abc", "abcd"));
    EXPECT_TRUE(contains_fragment("abc", ""));

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

TEST(ApiServerHelpersTest, SerializationHelpersReturnExpectedPayloads) {
    Seat seat("1A", SeatClass::BUSINESS, 100.0);
    ASSERT_TRUE(seat.bookSeat());
    json seat_json;
    to_json(seat_json, seat);
    EXPECT_EQ(seat_json.at("seatId"), "1A");
    EXPECT_EQ(seat_json.at("isBooked"), true);
    EXPECT_EQ(seat_json.at("price"), 200.0);
    EXPECT_EQ(seat_json.at("seatClass"), "Business");

    Airplane plane("HX123", 2, 2);
    json airplane_json;
    to_json(airplane_json, plane);
    EXPECT_EQ(airplane_json.at("flightNumber"), "HX123");
    EXPECT_EQ(airplane_json.at("capacity"), 4);
    EXPECT_EQ(airplane_json.at("bookedSeatsCount"), 0);
    EXPECT_EQ(airplane_json.at("isFull"), false);

    Customer customer("Helper User", 29, "CUST9998", 321.5);
    json customer_json;
    to_json(customer_json, customer);
    EXPECT_EQ(customer_json.at("personId"), "CUST9998");
    EXPECT_EQ(customer_json.at("name"), "Helper User");
    EXPECT_EQ(customer_json.at("age"), 29);
    EXPECT_EQ(customer_json.at("money"), 321.5);

    Booking booking("CUST9998", "HX123", "1A");
    booking.setStatus(BookingStatus::CONFIRMED);
    json booking_json;
    to_json(booking_json, booking);
    EXPECT_EQ(booking_json.at("customerId"), "CUST9998");
    EXPECT_EQ(booking_json.at("flightNumber"), "HX123");
    EXPECT_EQ(booking_json.at("seatId"), "1A");
    EXPECT_EQ(booking_json.at("status"), "Confirmed");
}

TEST(ApiServerHelpersTest, DetailBuildersReturnExpectedPayloads) {
    std::stringstream input;
    std::stringstream output;
    ReservationSystem reservation_system(input, output);
    Customer* api_customer = reservation_system.addCustomerInternal("Builder User", 40, 800.0, false);
    ASSERT_NE(api_customer, nullptr);
    std::string booking_error;
    Booking* api_booking = reservation_system.createBookingInternal(
        api_customer->getPersonId(),
        "FL101",
        "4A",
        booking_error);
    ASSERT_NE(api_booking, nullptr);

    const Airplane* flight = reservation_system.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(flight, nullptr);
    json airplane_details = build_airplane_details(reservation_system, *flight);
    EXPECT_EQ(airplane_details.at("capacity"), flight->getCapacity());
    EXPECT_EQ(airplane_details.at("bookedSeatsCount"), flight->getBookedSeatsCount());
    EXPECT_EQ(airplane_details.at("isFull"), flight->isFull());
    const auto seat_it = std::ranges::find_if(
        airplane_details.at("seats"),
        [](const json& seat_details) { return seat_details.at("seatId") == "4A"; });
    ASSERT_NE(seat_it, airplane_details.at("seats").end());
    EXPECT_EQ(seat_it->at("bookedByCustomerId"), api_customer->getPersonId());
    EXPECT_EQ(seat_it->at("bookingId"), api_booking->getBookingId());

    api_booking->setStatus(BookingStatus::CANCELLED);
    EXPECT_EQ(
        find_confirmed_booking_for_seat(reservation_system.getBookingsForTest(), "FL101", "4A"),
        nullptr);

    json customer_details = build_customer_details(reservation_system, *api_customer);
    ASSERT_TRUE(customer_details.contains("bookings"));
    ASSERT_EQ(customer_details.at("bookings").size(), 1);
    EXPECT_EQ(customer_details.at("bookings").front().at("bookingId"), api_booking->getBookingId());
}

TEST(ApiServerHelpersTest, RespondJsonSetsContentTypeAndCorsHeaders) {
    httplib::Response response;

    respond_json(response, json{{"ok", true}}, 201);

    EXPECT_EQ(response.status, 201);
    EXPECT_EQ(response.get_header_value("Content-Type"), kJsonMimeType);
    EXPECT_EQ(response.get_header_value("Access-Control-Allow-Origin"), "*");
    EXPECT_EQ(
        response.get_header_value("Access-Control-Allow-Methods"),
        "GET, POST, PUT, DELETE, OPTIONS");
}

TEST(ApiServerEntryTest, RunApiServerReportsFailureWhenListenFails) {
    std::stringstream input;
    std::stringstream out;
    std::stringstream err;
    ReservationSystem reservation_system(input, out);
    httplib::Server server;

    EXPECT_EQ(
        run_api_server_with_listener(
            reservation_system,
            server,
            out,
            err,
            +[](httplib::Server&, const char*, int) {
                return false;
            }),
        1);
    EXPECT_NE(out.str().find("Starting API server"), std::string::npos);
    EXPECT_NE(err.str().find("Failed to start server!"), std::string::npos);
}

TEST(ApiServerEntryTest, MainReturnsSuccessWhenListenHookSucceeds) {
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    std::stringstream input;
    ReservationSystem reservation_system(input, output_stream);
    httplib::Server server;

    const int exit_code = run_api_server_with_listener(
        reservation_system,
        server,
        output_stream,
        error_stream,
        +[](httplib::Server&, const char*, int) {
            return true;
        });

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output_stream.str().find("Starting API server"), std::string::npos);
    EXPECT_TRUE(error_stream.str().empty());
}

TEST(ApiServerEntryTest, MainReturnsFailureWhenDefaultListenOverrideFails) {
    DefaultListenOverrideObservation observation;
    std::istringstream input_stream;
    std::ostringstream output_stream;
    std::ostringstream error_stream;

    const int exit_code = airline_api_server_entry(
        input_stream,
        output_stream,
        error_stream,
        [&observation](httplib::Server&, const char* host, int port) {
            observation.invoked = true;
            observation.host = host == nullptr ? "" : host;
            observation.port = port;
            return false;
        });

    EXPECT_EQ(exit_code, 1);
    EXPECT_TRUE(observation.invoked);
    EXPECT_EQ(observation.host, "0.0.0.0");
    EXPECT_EQ(observation.port, kServerPort);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(error_stream.str().find("Failed to start server!"), std::string::npos);
}

TEST(ApiServerEntryTest, AirlineApiServerEntryReturnsFailureWhenDefaultPortIsAlreadyInUse) {
#ifdef _WIN32
    GTEST_SKIP() << "Port-collision coverage path is exercised on Linux coverage runners.";
#else
    ScopedPortOccupier blocking_listener(kServerPort);
    ASSERT_TRUE(blocking_listener.is_listening());
    std::istringstream input_stream;
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    const int exit_code = airline_api_server_entry(input_stream, output_stream, error_stream);

    EXPECT_EQ(exit_code, 1);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(error_stream.str().find("Failed to start server!"), std::string::npos);
#endif
}

TEST(ApiServerEntryTest, RunApiServerUsesLoggerWithRealListenPath) {
    std::atomic selected_port{-1};
    auto listen_on_first_available_port = [&selected_port](httplib::Server& server, const char* host, int) {
        for (int offset = 0; offset < kTestPortCount; ++offset) {
            const int port = kTestPortStart + offset;
            selected_port.store(port, std::memory_order_release);
            if (listen_on_host(server, host, port)) {
                return true;
            }
        }
        selected_port.store(-1, std::memory_order_release);
        return false;
    };

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

    ASSERT_TRUE(wait_for_selected_port(selected_port));
    const int port = selected_port.load(std::memory_order_acquire);
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

TEST(ApiServerEntryTest, RunApiServerUsesDefaultListenWrapper) {
    std::stringstream input;
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    std::ostringstream log_stream;
    ScopedStreamRedirect redirect(std::cout, log_stream);
    ReservationSystem reservation_system(input, output_stream);
    httplib::Server server;
    std::promise<int> exit_code_promise;
    std::future<int> exit_code_future = exit_code_promise.get_future();
    std::jthread server_thread([&error_stream, &output_stream, &reservation_system, &server, exit_code = std::move(exit_code_promise)]() mutable {
        exit_code.set_value(run_api_server(reservation_system, server, output_stream, error_stream));
    });
    ScopedServerShutdown shutdown(server, server_thread);

    const bool observed_healthy = wait_for_status(kServerPort, "/api/airplanes", 200);
    server.stop();

    ASSERT_EQ(exit_code_future.wait_for(kStartupTimeout), std::future_status::ready);
    const int exit_code = exit_code_future.get();
    if (exit_code == 0) {
        EXPECT_TRUE(observed_healthy);
        EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
        EXPECT_NE(log_stream.str().find("HTTP GET /api/airplanes -> 200"), std::string::npos);
        EXPECT_TRUE(error_stream.str().empty());
        return;
    }

    EXPECT_EQ(exit_code, 1);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(error_stream.str().find("Failed to start server!"), std::string::npos);
}

TEST_F(ApiServerRoutesTest, ListsDefaultAirplanesAndCustomers) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

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

TEST_F(ApiServerRoutesTest, ListsBookingsAndReturnsNotFoundForMissingResources) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const auto bookings_response = client.Get("/api/bookings");
    ASSERT_TRUE(bookings_response);
    EXPECT_EQ(bookings_response->status, 200);
    EXPECT_EQ(json::parse(bookings_response->body).size(), 0);

    const auto airplane_response = client.Get("/api/airplanes/FL999");
    ASSERT_TRUE(airplane_response);
    EXPECT_EQ(airplane_response->status, 404);
    EXPECT_EQ(json::parse(airplane_response->body).at("error"), "Airplane not found");

    const auto customer_response = client.Get("/api/customers/CUST9999");
    ASSERT_TRUE(customer_response);
    EXPECT_EQ(customer_response->status, 404);
    EXPECT_EQ(json::parse(customer_response->body).at("error"), "Customer not found");
}

TEST_F(ApiServerRoutesTest, SupportsCustomerBookingLifecycleRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json new_customer = create_customer_via_route(
        client,
        json{{"name", "Server User"}, {"age", 31}, {"money", 500.0}, {"autoGenerate", false}});
    const std::string customer_id = new_customer.at("personId").get<std::string>();

    const auto customer_details = client.Get("/api/customers/" + customer_id);
    expect_response_status(customer_details, 200);

    const auto booking_response = create_booking_via_route(client, customer_id, "FL101", "4A");
    const json booking = parse_json_response(booking_response, 201);
    const std::string booking_id = booking.at("bookingId").get<std::string>();

    const auto airplane_details = client.Get("/api/airplanes/FL101");
    expect_response_status(airplane_details, 200);
    EXPECT_NE(airplane_details->body.find(booking_id), std::string::npos);

    const auto cancel_response = client.Delete("/api/bookings/" + booking_id);
    expect_response_status(cancel_response, 200);

    const auto options_response = client.Options("/api/bookings");
    expect_response_status(options_response, 204);
}

json create_auto_generated_customer(httplib::Client& client) {
    return create_customer_via_route(
        client,
        json{{"name", "Ignored"}, {"age", 0}, {"money", 0.0}, {"autoGenerate", true}});
}

TEST_F(ApiServerRoutesTest, SupportsAutoGeneratedCustomers) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_name = auto_customer.at("name").get<std::string>();
    EXPECT_TRUE(has_expected_auto_generated_customer_name(customer_name));
    EXPECT_GE(auto_customer.at("age").get<int>(), 18);
    EXPECT_GE(auto_customer.at("money").get<double>(), 100.0);
}

TEST_F(ApiServerRoutesTest, MapsBookingErrorStatusesForRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_id = auto_customer.at("personId").get<std::string>();

    const auto missing_customer_response = create_booking_via_route(client, "CUST9999", "FL101", "4A");
    expect_response_status(missing_customer_response, 404);

    const auto missing_airplane_response = create_booking_via_route(client, customer_id, "FL999", "4A");
    expect_response_status(missing_airplane_response, 404);

    const auto missing_seat_response = create_booking_via_route(client, customer_id, "FL101", "99Z");
    expect_response_status(missing_seat_response, 404);
}

TEST_F(ApiServerRoutesTest, ReturnsConflictAndPaymentErrorsForRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_id = auto_customer.at("personId").get<std::string>();

    const auto first_booking_response = create_booking_via_route(client, customer_id, "FL101", "4A");
    expect_response_status(first_booking_response, 201);

    const auto second_booking_response = create_booking_via_route(client, customer_id, "FL101", "4A");
    expect_response_status(second_booking_response, 409);

    const json poor_customer = create_customer_via_route(
        client,
        json{{"name", "Low Funds"}, {"age", 28}, {"money", 10.0}, {"autoGenerate", false}});
    const std::string poor_customer_id = poor_customer.at("personId").get<std::string>();

    const auto insufficient_funds_response = create_booking_via_route(client, poor_customer_id, "FL101", "4B");
    expect_response_status(insufficient_funds_response, 402);
}

TEST_F(ApiServerRoutesTest, CancelRoutesMapErrorsAndSuccess) {
    Customer* first_customer = addCustomer("First Route User", 30, 500.0, false);
    Customer* second_customer = addCustomer("Second Route User", 31, 500.0, false);
    ASSERT_NE(first_customer, nullptr);
    ASSERT_NE(second_customer, nullptr);

    Booking* first_booking = createBooking(first_customer->getPersonId(), "FL101", "5A");
    ASSERT_NE(first_booking, nullptr);
    const std::string first_booking_id = first_booking->getBookingId();

    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const auto missing_cancel_response = client.Delete("/api/bookings/BK_FAKE");
    expect_response_status(missing_cancel_response, 404);

    const auto cancel_response = client.Delete("/api/bookings/" + first_booking_id);
    expect_response_status(cancel_response, 200);

    const auto already_cancelled_response = client.Delete("/api/bookings/" + first_booking_id);
    expect_response_status(already_cancelled_response, 409);
}

TEST_F(ApiServerRoutesTest, SwapRoutesMapErrorsAndSuccess) {
    Customer* first_customer = addCustomer("First Route User", 30, 500.0, false);
    Customer* second_customer = addCustomer("Second Route User", 31, 500.0, false);
    Customer* third_customer = addCustomer("Third Route User", 32, 500.0, false);
    ASSERT_NE(first_customer, nullptr);
    ASSERT_NE(second_customer, nullptr);
    ASSERT_NE(third_customer, nullptr);

    Booking* first_booking = createBooking(first_customer->getPersonId(), "FL101", "5A");
    ASSERT_NE(first_booking, nullptr);
    Booking* second_booking = createBooking(second_customer->getPersonId(), "FL101", "5B");
    ASSERT_NE(second_booking, nullptr);
    const std::string second_booking_id = second_booking->getBookingId();
    Booking* third_booking = createBooking(third_customer->getPersonId(), "FL202", "2A");
    ASSERT_NE(third_booking, nullptr);
    const std::string third_booking_id = third_booking->getBookingId();

    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const auto same_booking_swap = swap_bookings_via_route(client, second_booking_id, second_booking_id);
    expect_response_status(same_booking_swap, 400);

    const auto different_flights_swap = swap_bookings_via_route(client, second_booking_id, third_booking_id);
    expect_response_status(different_flights_swap, 400);

    Booking* refreshed_first_booking = createBooking(first_customer->getPersonId(), "FL101", "5C");
    ASSERT_NE(refreshed_first_booking, nullptr);
    const std::string refreshed_first_booking_id = refreshed_first_booking->getBookingId();

    const auto successful_swap = swap_bookings_via_route(client, refreshed_first_booking_id, second_booking_id);
    expect_response_status(successful_swap, 200);
    EXPECT_NE(json::parse(successful_swap->body).at("message").get<std::string>().find("Seat swap successful"), std::string::npos);
}

TEST_F(ApiServerRoutesTest, ReturnsBadRequestForMalformedPayloads) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

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
