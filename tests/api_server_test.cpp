// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <algorithm>
#include <chrono>
#include <sstream>
#include <thread>

#define main airline_api_server_entry_main
#include "../src/api_server_main.cpp"
#undef main

namespace api_server_test_support {

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
        run_api_server(
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

    const int exit_code = run_api_server(
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

    const auto new_customer_response = client.Post(
        "/api/customers",
        json{{"name", "Server User"}, {"age", 31}, {"money", 500.0}, {"autoGenerate", false}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(new_customer_response);
    ASSERT_EQ(new_customer_response->status, 201);
    const json new_customer = json::parse(new_customer_response->body);
    const std::string customer_id = new_customer.at("personId").get<std::string>();

    const auto customer_details = client.Get("/api/customers/" + customer_id);
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

    const auto cancel_response = client.Delete("/api/bookings/" + booking_id);
    ASSERT_TRUE(cancel_response);
    EXPECT_EQ(cancel_response->status, 200);

    const auto options_response = client.Options("/api/bookings");
    ASSERT_TRUE(options_response);
    EXPECT_EQ(options_response->status, 204);
}

json create_auto_generated_customer(httplib::Client& client) {
    const auto auto_customer_response = client.Post(
        "/api/customers",
        json{{"name", "Ignored"}, {"age", 0}, {"money", 0.0}, {"autoGenerate", true}}.dump(),
        kJsonMimeType);
    EXPECT_TRUE(auto_customer_response);
    EXPECT_EQ(auto_customer_response->status, 201);
    return json::parse(auto_customer_response->body);
}

TEST_F(ApiServerRoutesTest, SupportsAutoGeneratedCustomers) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_name = auto_customer.at("name").get<std::string>();
    EXPECT_TRUE(customer_name.rfind("ApiPat_", 0) == 0 ||
                customer_name.rfind("WebServiceUser_", 0) == 0 ||
                customer_name.rfind("JsonGenClient_", 0) == 0 ||
                customer_name.rfind("SystemPerson_", 0) == 0 ||
                customer_name.rfind("BackendBot_", 0) == 0);
    EXPECT_GE(auto_customer.at("age").get<int>(), 18);
    EXPECT_GE(auto_customer.at("money").get<double>(), 100.0);
}

TEST_F(ApiServerRoutesTest, MapsBookingErrorStatusesForRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_id = auto_customer.at("personId").get<std::string>();

    const auto missing_customer_response = client.Post(
        "/api/bookings",
        json{{"customerId", "CUST9999"}, {"flightNumber", "FL101"}, {"seatId", "4A"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(missing_customer_response);
    EXPECT_EQ(missing_customer_response->status, 404);

    const auto missing_airplane_response = client.Post(
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", "FL999"}, {"seatId", "4A"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(missing_airplane_response);
    EXPECT_EQ(missing_airplane_response->status, 404);

    const auto missing_seat_response = client.Post(
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", "FL101"}, {"seatId", "99Z"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(missing_seat_response);
    EXPECT_EQ(missing_seat_response->status, 404);
}

TEST_F(ApiServerRoutesTest, ReturnsConflictAndPaymentErrorsForRoutes) {
    start_server();
    httplib::Client client("127.0.0.1", bound_port());

    const json auto_customer = create_auto_generated_customer(client);
    const std::string customer_id = auto_customer.at("personId").get<std::string>();

    const auto first_booking_response = client.Post(
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", "FL101"}, {"seatId", "4A"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(first_booking_response);
    ASSERT_EQ(first_booking_response->status, 201);

    const auto second_booking_response = client.Post(
        "/api/bookings",
        json{{"customerId", customer_id}, {"flightNumber", "FL101"}, {"seatId", "4A"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(second_booking_response);
    EXPECT_EQ(second_booking_response->status, 409);

    const auto poor_customer_response = client.Post(
        "/api/customers",
        json{{"name", "Low Funds"}, {"age", 28}, {"money", 10.0}, {"autoGenerate", false}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(poor_customer_response);
    ASSERT_EQ(poor_customer_response->status, 201);
    const std::string poor_customer_id =
        json::parse(poor_customer_response->body).at("personId").get<std::string>();

    const auto insufficient_funds_response = client.Post(
        "/api/bookings",
        json{{"customerId", poor_customer_id}, {"flightNumber", "FL101"}, {"seatId", "4B"}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(insufficient_funds_response);
    EXPECT_EQ(insufficient_funds_response->status, 402);
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
    ASSERT_TRUE(missing_cancel_response);
    EXPECT_EQ(missing_cancel_response->status, 404);

    const auto cancel_response = client.Delete("/api/bookings/" + first_booking_id);
    ASSERT_TRUE(cancel_response);
    ASSERT_EQ(cancel_response->status, 200);

    const auto already_cancelled_response = client.Delete("/api/bookings/" + first_booking_id);
    ASSERT_TRUE(already_cancelled_response);
    EXPECT_EQ(already_cancelled_response->status, 409);
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

    const auto same_booking_swap = client.Post(
        "/api/bookings/swap",
        json{{"bookingId1", second_booking_id}, {"bookingId2", second_booking_id}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(same_booking_swap);
    EXPECT_EQ(same_booking_swap->status, 400);

    const auto different_flights_swap = client.Post(
        "/api/bookings/swap",
        json{{"bookingId1", second_booking_id}, {"bookingId2", third_booking_id}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(different_flights_swap);
    EXPECT_EQ(different_flights_swap->status, 400);

    Booking* refreshed_first_booking = createBooking(first_customer->getPersonId(), "FL101", "5C");
    ASSERT_NE(refreshed_first_booking, nullptr);
    const std::string refreshed_first_booking_id = refreshed_first_booking->getBookingId();

    const auto successful_swap = client.Post(
        "/api/bookings/swap",
        json{{"bookingId1", refreshed_first_booking_id}, {"bookingId2", second_booking_id}}.dump(),
        kJsonMimeType
    );
    ASSERT_TRUE(successful_swap);
    ASSERT_EQ(successful_swap->status, 200);
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

}  // namespace api_server_test_support
