// cppcheck-suppress-file missingIncludeSystem
#include "reservation_system_test_fixture.h"

TEST_F(ReservationSystemTest, InitialSystemStateAndFinders) {
    Airplane* plane1 = rs.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(plane1, nullptr);
    EXPECT_EQ(plane1->getFlightNumber(), "FL101");

    Customer* cust1 = rs.findCustomerById("CUST0001");
    ASSERT_NE(cust1, nullptr);
    EXPECT_EQ(cust1->getName(), "Alice Wonderland");
    
    EXPECT_EQ(rs.findAirplaneByFlightNumber("FL999"), nullptr);
    EXPECT_EQ(rs.findCustomerById("CUST9999"), nullptr);
}

TEST_F(ReservationSystemTest, GenerateUniqueCustomerId) {
    rs.resetSystemForTest(); // Ensure counter starts at 1 for this specific test
    std::string id1 = rs.generateUniqueCustomerId();
    std::string id2 = rs.generateUniqueCustomerId();
    EXPECT_EQ(id1, "CUST0001");
    EXPECT_EQ(id2, "CUST0002");
    EXPECT_NE(id1, id2);
}

TEST_F(ReservationSystemTest, FindBookingByIdEmpty) {
    EXPECT_EQ(rs.findBookingById("BK123"), nullptr);
}

TEST_F(ReservationSystemTest, HandleAddCustomerManual) {
    test_in.str("m\nTest User\n30\n500.0\n"); // Simulate manual input
    // rs.handleAddCustomer(); // Direct call for testing specific handler
    
    // To test handleAddCustomer via run()
    test_in.clear(); test_in.str("1\nm\nTest User\n30\n500.0\n0\n"); // 1 for add, then manual, then data, then 0 to exit run()
    rs.run(); // This will call handleAddCustomer

    Customer* newCust = rs.findCustomerById("CUST0003"); // Default customers CUST0001, CUST0002 already exist
    ASSERT_NE(newCust, nullptr);
    EXPECT_EQ(newCust->getName(), "Test User");
    EXPECT_EQ(newCust->getAge(), 30);
    EXPECT_DOUBLE_EQ(newCust->getMoney(), 500.0);
    
    std::string output = test_out.str();
    EXPECT_NE(output.find("Customer Test User with ID CUST0003 added successfully."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleAddCustomerAutomatic) {
    test_in.str("1\na\n0\n"); // Menu: 1 (add cust), a (auto), 0 (exit)
    rs.run();

    Customer* newCust = rs.findCustomerById("CUST0003");
    ASSERT_NE(newCust, nullptr);
    // Name is partly random, check prefix
    EXPECT_TRUE(newCust->getName().rfind("AutoPat_CUST0003", 0) == 0 ||
                newCust->getName().rfind("RoboUser_CUST0003", 0) == 0 ||
                newCust->getName().rfind("GenClient_CUST0003", 0) == 0 ||
                newCust->getName().rfind("SysPerson_CUST0003", 0) == 0 ||
                newCust->getName().rfind("BotPassenger_CUST0003", 0) == 0);
    EXPECT_GE(newCust->getAge(), 18);
    EXPECT_LE(newCust->getAge(), 80);
    EXPECT_GE(newCust->getMoney(), 100.0);
    EXPECT_LE(newCust->getMoney(), 2000.0);
    
    std::string output = test_out.str();
    EXPECT_NE(output.find("added successfully."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleAddCustomerInvalidChoice) {
    test_in.str("1\nx\n0\n"); // Menu: 1 (add cust), x (invalid), 0 (exit)
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Invalid choice. Aborting customer creation."), std::string::npos);
    EXPECT_EQ(rs.getCustomersForTest().size(), 2); // Should still be 2 default customers
}

TEST_F(ReservationSystemTest, RunRejectsInvalidMenuInputBeforeExit) {
    test_in.str("abc\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("Invalid choice. Please enter a number between 0 and 7."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, GetValidatedInputRetriesAfterInvalidNumericInput) {
    test_in.str("oops\n42\n");

    const int value = ReservationSystemTestAccess::getValidatedInt(rs, "Enter number: ");

    EXPECT_EQ(value, 42);
    EXPECT_NE(test_out.str().find("Invalid input. Please try again."), std::string::npos);
}

TEST_F(ReservationSystemTest, GetValidatedInputThrowsWhenNumericInputEndsAfterRetry) {
    test_in.str("oops");

    EXPECT_THROW(
        static_cast<void>(ReservationSystemTestAccess::getValidatedInt(rs, "Enter number: ")),
        reservation_system_helpers::InputExhaustedError);
    EXPECT_NE(test_out.str().find("Invalid input. Please try again."), std::string::npos);
}

TEST_F(ReservationSystemTest, GetValidatedDoubleRetriesAfterInvalidNumericInput) {
    test_in.str("oops\n123.5\n");

    const double value = ReservationSystemTestAccess::getValidatedDouble(rs, "Enter fare: ");

    EXPECT_DOUBLE_EQ(value, 123.5);
    EXPECT_NE(test_out.str().find("Invalid input. Please try again."), std::string::npos);
}

TEST_F(ReservationSystemTest, GetValidatedDoubleThrowsWhenInputEndsAfterRetry) {
    test_in.str("oops");

    EXPECT_THROW(
        static_cast<void>(ReservationSystemTestAccess::getValidatedDouble(rs, "Enter fare: ")),
        reservation_system_helpers::InputExhaustedError);
    EXPECT_NE(test_out.str().find("Invalid input. Please try again."), std::string::npos);
}

TEST_F(ReservationSystemTest, GetValidatedStringReturnsFirstTokenWithoutRetry) {
    test_in.str("FL101\n");

    const std::string value = ReservationSystemTestAccess::getValidatedString(rs, "Enter flight: ");

    EXPECT_EQ(value, "FL101");
    EXPECT_EQ(test_out.str(), "Enter flight: ");
}

TEST_F(ReservationSystemTest, GetValidatedStringThrowsOnImmediateEof) {
    test_in.str("");

    EXPECT_THROW(
        static_cast<void>(ReservationSystemTestAccess::getValidatedString(rs, "Enter flight: ")),
        reservation_system_helpers::InputExhaustedError);
    EXPECT_EQ(test_out.str(), "Enter flight: ");
}

TEST_F(ReservationSystemTest, ExecuteMenuChoiceReportsOutOfRangeChoice) {
    ReservationSystemTestAccess::executeMenuChoice(rs, 99);

    EXPECT_NE(test_out.str().find("Invalid choice. Please try again."), std::string::npos);
}

TEST_F(ReservationSystemTest, ValidateSwapPairReportsDifferentFlights) {
    Customer* first_customer = addCustomer("HelperUserA", 30, 500.0, false);
    ASSERT_NE(first_customer, nullptr);
    const std::string first_customer_id = first_customer->getPersonId();

    Customer* second_customer = addCustomer("HelperUserB", 31, 500.0, false);
    ASSERT_NE(second_customer, nullptr);
    const std::string second_customer_id = second_customer->getPersonId();

    Booking* first_booking = createConfirmedBooking(first_customer_id, "FL101", "8A");
    ASSERT_NE(first_booking, nullptr);
    const std::string first_booking_id = first_booking->getBookingId();
    Booking* second_booking = createConfirmedBooking(second_customer_id, "FL202", "1A");
    ASSERT_NE(second_booking, nullptr);
    const std::string second_booking_id = second_booking->getBookingId();
    first_booking = findBooking(first_booking_id);
    second_booking = findBooking(second_booking_id);
    ASSERT_NE(first_booking, nullptr);
    ASSERT_NE(second_booking, nullptr);

    EXPECT_FALSE(ReservationSystemTestAccess::validateSwapPair(rs, *first_booking, *second_booking));
    EXPECT_NE(
        test_out.str().find("Booking 1 is for flight FL101, Booking 2 is for flight FL202"),
        std::string::npos);
}


TEST_F(ReservationSystemTest, HandleBookSeatNoFlights) {
    rs.resetSystemForTest(); // Clear default airplanes
    test_in.str("2\n0\n"); // Menu: 2 (book), 0 (exit)
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("No flights available to book."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatNoCustomers) {
    rs.resetSystemForTest();
    rs.initializeSystem(); // Add planes
    rs.resetSystemForTest(); // Clear customers but keep planes (this is a bit clunky)
                             // Better: rs.airplanes.emplace_back("FLTEST",1,1); after reset
    // Let's re-initialize and then clear customers
    rs.resetSystemForTest();
    rs.initializeSystem(); // Adds planes and customers
    rs.clearCustomersForTest();

    test_in.str("2\n0\n"); 
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("No customers in the system."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatCustomerNotFound) {
    test_in.str("2\nCUST9999\n0\n"); // Try to book for non-existent customer
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Customer with ID CUST9999 not found."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatSeatNotFound) {
    test_in.str("2\nCUST0001\n1\n99Z\n0\n"); // Cust1, Flight 1, Seat 99Z (non-existent)
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Seat 99Z does not exist on this flight."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatAlreadyBooked) {
    Airplane* plane = rs.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(plane, nullptr);
    plane->bookSpecificSeat("1A"); // Pre-book a seat

    test_in.str("2\nCUST0001\n1\n1A\n0\n"); // Cust1, Flight 1, Seat 1A (now booked)
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Seat 1A is already booked."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatInsufficientFunds) {
    Customer* cust = rs.findCustomerById("CUST0002"); // Bob, 800.0
    ASSERT_NE(cust, nullptr);
    cust->setMoney(10.0); // Not enough for any seat

    test_in.str("2\nCUST0002\n1\n3A\n0\n"); // Cust2, Flight 1, Seat 3A (Economy, likely $50)
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Insufficient funds."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleBookSeatSuccessful) {
    // CUST0001 (Alice, 1500.0) books FL101 (Plane 1), Seat 4A (Economy, $50)
    // FL101: 15 rows. 15*0.2 = 3 business rows. So row 4 is Economy.
    test_in.str("2\nCUST0001\n1\n4A\ny\n0\n"); 
    rs.run();
    
    std::string output = test_out.str();
    EXPECT_NE(output.find("Booking successful!"), std::string::npos);

    Customer* cust = rs.findCustomerById("CUST0001");
    ASSERT_NE(cust, nullptr);
    EXPECT_DOUBLE_EQ(cust->getMoney(), 1450.0); // 1500 - 50

    Airplane* plane = rs.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(plane, nullptr);
    Seat* seat = plane->findSeat("4A");
    ASSERT_NE(seat, nullptr);
    EXPECT_TRUE(seat->getIsBooked());
    // The plane already has 2 default customers, this is the 3rd booking if we count them.
    // No, initializeSystem does not make bookings. So this is the first booking.
    EXPECT_EQ(plane->getBookedSeatsCount(), 1); 

    EXPECT_EQ(rs.getBookingsForTest().size(), 1);
    if (!rs.getBookingsForTest().empty()) {
        const Booking& b = rs.getBookingsForTest().front();
        EXPECT_EQ(b.getCustomerId(), "CUST0001");
        EXPECT_EQ(b.getFlightNumber(), "FL101");
        EXPECT_EQ(b.getSeatId(), "4A");
        EXPECT_EQ(b.getStatus(), BookingStatus::CONFIRMED);
    }
}

TEST_F(ReservationSystemTest, HandleBookSeatCancelledByUser) {
    test_in.str("2\nCUST0001\n1\n4B\nn\n0\n"); // n for no to confirm
    rs.run();
    std::string output = test_out.str();
    EXPECT_NE(output.find("Booking cancelled by user."), std::string::npos);
    EXPECT_EQ(rs.getBookingsForTest().size(), 0); // No booking should be made
}

TEST_F(ReservationSystemTest, HandleViewFlightDetailsNoFlights) {
    rs.resetSystemForTest();

    test_in.str("3\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("No flights available to view."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleViewFlightDetailsDisplaysSelectedFlight) {
    std::ostringstream captured_stdout;
    std::streambuf* original_cout = std::cout.rdbuf(captured_stdout.rdbuf());

    test_in.str("3\n1\n0\n");
    rs.run();

    std::cout.rdbuf(original_cout);

    EXPECT_NE(test_out.str().find("Available Flights:"), std::string::npos);
    EXPECT_NE(captured_stdout.str().find("Seating Map for Flight FL101"), std::string::npos);
    EXPECT_NE(captured_stdout.str().find("Available Seats for Flight FL101"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSearchCustomerNoCustomers) {
    rs.resetSystemForTest();

    test_in.str("4\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("No customers in the system."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSearchCustomerNotFound) {
    test_in.str("4\nCUST9999\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("Customer with ID CUST9999 not found."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSearchCustomerReportsWhenNoActiveBookingsExist) {
    test_in.str("4\nCUST0001\n0\n");
    rs.run();

    const std::string output = test_out.str();
    EXPECT_NE(output.find("Bookings for Alice Wonderland:"), std::string::npos);
    EXPECT_NE(output.find("No active bookings found for this customer."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSearchCustomerSuppressesNoBookingsMessageWhenBookingExists) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "4C");
    ASSERT_NE(booking, nullptr);

    test_in.str("4\nCUST0001\n0\n");
    rs.run();

    const std::string output = test_out.str();
    EXPECT_NE(output.find("Bookings for Alice Wonderland:"), std::string::npos);
    EXPECT_EQ(output.find("No active bookings found for this customer."), std::string::npos);
}


// More tests for other handlers (handleViewFlightDetails, handleSearchCustomer, handleCancelBooking, handleSwapSeats, handleAdminMenu)
// would follow a similar pattern: prepare input stream, call rs.run() with menu choices, check output stream and internal state.
// This is becoming more like integration testing due to the nature of run().

// Note: The hacky way to clear customers in HandleBookSeatNoCustomers is not ideal.
// A better test setup would allow constructing ReservationSystem without default data,
// then adding specific data for each test. resetSystemForTest() helps with this.
