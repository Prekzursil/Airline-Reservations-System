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

TEST(ApiServerHelpersTest, SerializationHelpersCoverRemainingStateBranches) {
    Seat economy_seat("2A", SeatClass::ECONOMY, 50.0);
    json economy_seat_json;
    to_json(economy_seat_json, economy_seat);
    EXPECT_EQ(economy_seat_json.at("seatClass"), "Economy");

    Seat unknown_seat("9Z", static_cast<SeatClass>(99), 50.0);
    json unknown_seat_json;
    to_json(unknown_seat_json, unknown_seat);
    EXPECT_EQ(unknown_seat_json.at("seatClass"), "Unknown");

    Airplane full_plane("FULL1", 1, 1);
    ASSERT_TRUE(full_plane.bookSpecificSeat("1A"));
    json full_plane_json;
    to_json(full_plane_json, full_plane);
    EXPECT_EQ(full_plane_json.at("isFull"), true);

    Booking pending_booking("CUST1001", "FL101", "1A");
    json pending_booking_json;
    to_json(pending_booking_json, pending_booking);
    EXPECT_EQ(pending_booking_json.at("status"), "Pending");

    Booking cancelled_booking("CUST1002", "FL101", "1B");
    cancelled_booking.setStatus(BookingStatus::CANCELLED);
    json cancelled_booking_json;
    to_json(cancelled_booking_json, cancelled_booking);
    EXPECT_EQ(cancelled_booking_json.at("status"), "Cancelled");
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
    [[maybe_unused]] const auto seat_it = std::ranges::find_if(
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

TEST(ApiServerHelpersTest, DetailBuildersCoverLookupAndFilterBranches) {
    std::stringstream input;
    std::stringstream output;
    ReservationSystem reservation_system(input, output);

    Customer* first_customer =
        reservation_system.addCustomerInternal("First Builder User", 40, 2000.0, false);
    Customer* second_customer =
        reservation_system.addCustomerInternal("Second Builder User", 41, 2000.0, false);
    ASSERT_NE(first_customer, nullptr);
    ASSERT_NE(second_customer, nullptr);

    std::string booking_error;
    Booking* first_flight_other_seat = reservation_system.createBookingInternal(
        first_customer->getPersonId(),
        "FL101",
        "1B",
        booking_error);
    ASSERT_NE(first_flight_other_seat, nullptr);

    Booking* other_flight_booking = reservation_system.createBookingInternal(
        second_customer->getPersonId(),
        "FL202",
        "2A",
        booking_error);
    ASSERT_NE(other_flight_booking, nullptr);

    Booking* target_booking = reservation_system.createBookingInternal(
        first_customer->getPersonId(),
        "FL101",
        "4A",
        booking_error);
    ASSERT_NE(target_booking, nullptr);
    target_booking->setStatus(BookingStatus::CANCELLED);

    const json customer_details = build_customer_details(reservation_system, *first_customer);
    ASSERT_TRUE(customer_details.contains("bookings"));
    EXPECT_EQ(customer_details.at("bookings").size(), 2);

    const Airplane* airplane = reservation_system.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(airplane, nullptr);
    [[maybe_unused]] const json airplane_details = build_airplane_details(reservation_system, *airplane);
    ASSERT_TRUE(airplane_details.contains("seats"));
    [[maybe_unused]] const auto seat_it = std::ranges::find_if(
        airplane_details.at("seats"),
        [](const json& seat_details) { return seat_details.at("seatId") == "4A"; });
    ASSERT_NE(seat_it, airplane_details.at("seats").end());
    EXPECT_FALSE(seat_it->contains("bookedByCustomerId"));
    EXPECT_FALSE(seat_it->contains("bookingId"));
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

    [[maybe_unused]] const int exit_code = run_api_server_with_listener(
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
    std::optional<ScopedPortOccupier> blocking_listener(std::in_place, kServerPort);
    if (const auto port_reserved = static_cast<bool>(*blocking_listener); !port_reserved) {
        GTEST_SKIP() << "Port 8080 could not be reserved in this environment.";
    }
    std::istringstream input_stream;
    std::ostringstream output_stream;
    std::ostringstream error_stream;
    const int exit_code = airline_api_server_entry(input_stream, output_stream, error_stream);

    EXPECT_EQ(exit_code, 1);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(error_stream.str().find("Failed to start server!"), std::string::npos);
#endif
}

TEST(ApiServerEntryTest, MainWrapperReturnsFailureWhenDefaultPortIsAlreadyInUse) {
#ifdef _WIN32
    GTEST_SKIP() << "Port-collision coverage path is exercised on Linux coverage runners.";
#else
    std::optional<ScopedPortOccupier> blocking_listener(std::in_place, kServerPort);
    if (const auto port_reserved = static_cast<bool>(*blocking_listener); !port_reserved) {
        GTEST_SKIP() << "Port 8080 could not be reserved in this environment.";
    }

    std::ostringstream output_stream;
    std::ostringstream error_stream;
    ScopedStreamRedirect cout_redirect(std::cout, output_stream);
    ScopedStreamRedirect cerr_redirect(std::cerr, error_stream);

    EXPECT_EQ(airline_api_server_entry(std::cin, std::cout, std::cerr), 1);
    EXPECT_NE(output_stream.str().find("Starting API server on http://localhost:8080"), std::string::npos);
    EXPECT_NE(error_stream.str().find("Failed to start server!"), std::string::npos);
#endif
}

TEST(ApiServerEntryTest, RunApiServerUsesLoggerWithRealListenPath) {
    expect_real_listen_success_path();
}

TEST(ApiServerEntryTest, RunApiServerFailsWhenEveryCandidatePortListenerFails) {
    expect_real_listen_failure_path();
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
    std::jthread server_thread(
        [&error_stream, &output_stream, &reservation_system, &server,
         exit_code = std::move(exit_code_promise)]() mutable {
            exit_code.set_value(
                run_api_server(reservation_system, server, output_stream, error_stream)
            );
        }
    );
    ScopedServerShutdown shutdown(server, server_thread);

    const bool observed_healthy = wait_for_status(kServerPort, "/api/airplanes", 200);
    server.stop();

    ASSERT_EQ(exit_code_future.wait_for(kStartupTimeout), std::future_status::ready);
    [[maybe_unused]] const int exit_code = exit_code_future.get();
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
