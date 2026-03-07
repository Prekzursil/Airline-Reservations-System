// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "auto_generated_customer_test_helpers.h"
#include "../src/ReservationSystem.h" 
#include "../src/Customer.h"
#include "../src/Airplane.h"
#include "../src/Booking.h"
#include <sstream> // For std::stringstream
#include <string>

class ReservationSystemTest : public ::testing::Test {
protected:
    std::stringstream test_in;
    std::stringstream test_out;
    ReservationSystem rs;

    ReservationSystemTest() : rs(test_in, test_out) {} // Constructor to pass streams

    void SetUp() override {
        // Reset system state and streams before each test
        rs.resetSystemForTest(); // Clears vectors and resets ID counter
        rs.initializeSystem();   // Re-initialize with default data for a consistent start
        test_in.clear();
        test_in.str("");
        test_out.clear();
        test_out.str("");
        // Set the streams for the rs object for each test
        rs.setInputStreamForTest(test_in);
        rs.setOutputStreamForTest(test_out);
    }

    Customer* addCustomer(
        const std::string& name = "Test User",
        int age = 25,
        double money = 1000.0,
        bool auto_generate = false) {
        Customer* customer = rs.addCustomerInternal(name, age, money, auto_generate);
        if (customer == nullptr) {
            ADD_FAILURE() << "Failed to add customer";
        }
        return customer;
    }

    Booking* createConfirmedBooking(const std::string& customer_id, const std::string& flight_number, const std::string& seat_id) {
        std::string booking_error;
        Booking* booking = rs.createBookingInternal(customer_id, flight_number, seat_id, booking_error);
        if (booking == nullptr) {
            ADD_FAILURE() << "Booking creation failed: " << booking_error;
        }
        return booking;
    }

    Booking* findBooking(const std::string& booking_id) {
        Booking* booking = rs.findBookingById(booking_id);
        if (booking == nullptr) {
            ADD_FAILURE() << "Booking not found: " << booking_id;
        }
        return booking;
    }
};

class ReservationSystemTestAccess {
public:
    static int getValidatedInt(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<int>(prompt);
    }

    static void executeMenuChoice(ReservationSystem& reservation_system, const int choice) {
        reservation_system.executeMenuChoice(choice);
    }

    static bool validateSwapPair(
        const ReservationSystem& reservation_system,
        const Booking& first_booking,
        const Booking& second_booking) {
        return reservation_system.validateSwapPair(first_booking, second_booking);
    }
};

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

TEST_F(ReservationSystemTest, CancelBookingInternal_Success) {
    // Setup: Create a customer and a booking
    Customer* cust = rs.addCustomerInternal("Cancel User", 25, 1000.0, false);
    ASSERT_NE(cust, nullptr);
    std::string flightNum = "FL101";
    std::string seatId = "5A"; // Economy seat on FL101

    std::string bookingError;
    Booking* booking = rs.createBookingInternal(cust->getPersonId(), flightNum, seatId, bookingError);
    ASSERT_NE(booking, nullptr) << "Booking creation failed: " << bookingError;
    ASSERT_EQ(booking->getStatus(), BookingStatus::CONFIRMED);
    std::string bookingId = booking->getBookingId();

    Airplane* plane = rs.findAirplaneByFlightNumber(flightNum);
    ASSERT_NE(plane, nullptr);
    Seat* seatObj = plane->findSeat(seatId);
    ASSERT_NE(seatObj, nullptr);
    EXPECT_TRUE(seatObj->getIsBooked());
    double originalMoney = cust->getMoney();

    // Action: Cancel the booking
    std::string cancelError;
    bool cancelSuccess = rs.cancelBookingInternal(bookingId, cancelError);

    // Assertions
    EXPECT_TRUE(cancelSuccess) << "Cancellation failed: " << cancelError;
    EXPECT_EQ(booking->getStatus(), BookingStatus::CANCELLED);
    EXPECT_FALSE(seatObj->getIsBooked()); // Seat should be available again
    EXPECT_DOUBLE_EQ(cust->getMoney(), originalMoney + seatObj->getPrice()); // Money refunded
    EXPECT_NE(cancelError.find("cancelled successfully"), std::string::npos);
}

TEST_F(ReservationSystemTest, CancelBookingInternal_NotFound) {
    std::string errorMsg;
    EXPECT_FALSE(rs.cancelBookingInternal("BK_NONEXISTENT", errorMsg));
    EXPECT_NE(errorMsg.find("not found"), std::string::npos);
}

TEST_F(ReservationSystemTest, CancelBookingInternal_AlreadyCancelled) {
    Customer* cust = rs.addCustomerInternal("Test User", 25, 1000.0, false);
    std::string flightNum = "FL101";
    std::string seatId = "5B";
    std::string bookingError;
    Booking* booking = rs.createBookingInternal(cust->getPersonId(), flightNum, seatId, bookingError);
    ASSERT_NE(booking, nullptr);
    std::string bookingId = booking->getBookingId();

    std::string cancelError1;
    ASSERT_TRUE(rs.cancelBookingInternal(bookingId, cancelError1)); // First cancellation

    std::string cancelError2;
    EXPECT_FALSE(rs.cancelBookingInternal(bookingId, cancelError2)); // Try to cancel again
    EXPECT_NE(cancelError2.find("already cancelled"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleCancelBookingNoBookings) {
    test_in.str("5\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("No bookings in the system to cancel."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleCancelBookingNotFound) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "5C");
    ASSERT_NE(booking, nullptr);

    test_in.str("5\nBK_FAKE\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("Booking with ID BK_FAKE not found."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleCancelBookingAlreadyCancelled) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "5D");
    ASSERT_NE(booking, nullptr);
    const std::string booking_id = booking->getBookingId();

    std::string cancel_error;
    ASSERT_TRUE(rs.cancelBookingInternal(booking_id, cancel_error));

    test_in.str("5\n" + booking_id + "\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("Booking " + booking_id + " is already cancelled."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, HandleCancelBookingCancelledByUser) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "5E");
    ASSERT_NE(booking, nullptr);
    const std::string booking_id = booking->getBookingId();

    test_in.str("5\n" + booking_id + "\nn\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("Cancellation aborted by user."), std::string::npos);
    EXPECT_EQ(rs.findBookingById(booking_id)->getStatus(), BookingStatus::CONFIRMED);
}

TEST_F(ReservationSystemTest, HandleCancelBookingSuccessfulViaMenu) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "5F");
    ASSERT_NE(booking, nullptr);
    const std::string booking_id = booking->getBookingId();

    test_in.str("5\n" + booking_id + "\ny\n0\n");
    rs.run();

    const Booking* updated_booking = rs.findBookingById(booking_id);
    ASSERT_NE(updated_booking, nullptr);
    EXPECT_EQ(updated_booking->getStatus(), BookingStatus::CANCELLED);
    EXPECT_NE(test_out.str().find("cancelled successfully"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleCancelBookingReportsInternalFailureMessage) {
    Customer* customer = addCustomer("CancelFailureUser", 30, 500.0, false);
    ASSERT_NE(customer, nullptr);

    Booking* booking = createConfirmedBooking(customer->getPersonId(), "FL101", "7A");
    ASSERT_NE(booking, nullptr);
    const std::string booking_id = booking->getBookingId();

    rs.clearCustomersForTest();
    test_in.str("5\n" + booking_id + "\ny\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("Error: Could not find customer, airplane, or seat associated with this booking."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, CancelBookingInternalFailsWhenAssociatedCustomerIsMissing) {
    Booking* booking = createConfirmedBooking("CUST0001", "FL101", "6A");
    ASSERT_NE(booking, nullptr);

    rs.clearCustomersForTest();

    std::string error_message;
    EXPECT_FALSE(rs.cancelBookingInternal(booking->getBookingId(), error_message));
    EXPECT_NE(
        error_message.find("Error: Could not find customer, airplane, or seat associated with this booking."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, SwapSeatsInternal_Success) {
    // Setup: Create two customers and two bookings on the same flight
    Customer* cust1 = rs.addCustomerInternal("Swapper One", 30, 500.0, false);
    Customer* cust2 = rs.addCustomerInternal("Swapper Two", 35, 600.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    std::string flightNum = "FL101";
    std::string seatId1 = "6A";
    std::string seatId2 = "6B";
    std::string bookingError;

    Booking* booking1 = rs.createBookingInternal(cust1->getPersonId(), flightNum, seatId1, bookingError);
    ASSERT_NE(booking1, nullptr) << bookingError;
    std::string bookingId1 = booking1->getBookingId();

    Booking* booking2 = rs.createBookingInternal(cust2->getPersonId(), flightNum, seatId2, bookingError);
    ASSERT_NE(booking2, nullptr) << bookingError;
    std::string bookingId2 = booking2->getBookingId();
    
    // Action
    std::string swapError;
    bool swapSuccess = rs.swapSeatsInternal(bookingId1, bookingId2, swapError);

    // Assertions
    EXPECT_TRUE(swapSuccess) << "Swap failed: " << swapError;
    
    // Re-fetch pointers to ensure we are checking the objects in the vector
    Booking* b1_after_swap = rs.findBookingById(bookingId1);
    Booking* b2_after_swap = rs.findBookingById(bookingId2);
    ASSERT_NE(b1_after_swap, nullptr);
    ASSERT_NE(b2_after_swap, nullptr);

    EXPECT_EQ(b1_after_swap->getSeatId(), seatId2); // Booking1 should now have seatId2
    EXPECT_EQ(b2_after_swap->getSeatId(), seatId1); // Booking2 should now have seatId1
    EXPECT_NE(swapError.find("Seat swap successful"), std::string::npos);
}

TEST_F(ReservationSystemTest, SwapSeatsInternal_BookingNotFound) {
    std::string errorMsg;
    EXPECT_FALSE(rs.swapSeatsInternal("BK_FAKE1", "BK_FAKE2", errorMsg));
    EXPECT_NE(errorMsg.find("not found"), std::string::npos);
}

TEST_F(ReservationSystemTest, SwapSeatsInternal_SameBookingId) {
    Customer* cust1 = rs.addCustomerInternal("Test User", 25, 1000.0, false);
    std::string flightNum = "FL101";
    std::string seatId1 = "6C";
    std::string bookingError;
    Booking* booking1 = rs.createBookingInternal(cust1->getPersonId(), flightNum, seatId1, bookingError);
    ASSERT_NE(booking1, nullptr);
    std::string bookingId1 = booking1->getBookingId();

    std::string errorMsg;
    EXPECT_FALSE(rs.swapSeatsInternal(bookingId1, bookingId1, errorMsg));
    EXPECT_NE(errorMsg.find("Cannot swap a booking with itself"), std::string::npos);
}

TEST_F(ReservationSystemTest, SwapSeatsInternal_DifferentFlights) {
    Customer* cust1 = rs.addCustomerInternal("UserA", 30, 500.0, false);
    Customer* cust2 = rs.addCustomerInternal("UserB", 35, 600.0, false);
    std::string bookingError;

    Booking* booking1 = rs.createBookingInternal(cust1->getPersonId(), "FL101", "7A", bookingError);
    ASSERT_NE(booking1, nullptr);
    const std::string bookingId1 = booking1->getBookingId();
    Booking* booking2 = rs.createBookingInternal(cust2->getPersonId(), "FL202", "1A", bookingError);
    ASSERT_NE(booking2, nullptr);
    const std::string bookingId2 = booking2->getBookingId();

    std::string errorMsg;
    EXPECT_FALSE(rs.swapSeatsInternal(bookingId1, bookingId2, errorMsg));
    EXPECT_NE(errorMsg.find("only supported for bookings on the same flight"), std::string::npos);
}

TEST_F(ReservationSystemTest, SwapSeatsInternal_SecondBookingNotConfirmed) {
    Customer* cust1 = addCustomer("First Swapper", 30, 500.0, false);
    Customer* cust2 = addCustomer("Second Swapper", 32, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "7B");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL101", "7C");
    ASSERT_NE(booking2, nullptr);
    const std::string second_booking_id = booking2->getBookingId();

    std::string cancel_error;
    ASSERT_TRUE(rs.cancelBookingInternal(second_booking_id, cancel_error));

    std::string swap_error;
    EXPECT_FALSE(rs.swapSeatsInternal(first_booking_id, second_booking_id, swap_error));
    EXPECT_NE(swap_error.find("Second booking ID"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsNotEnoughBookings) {
    test_in.str("6\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("Not enough bookings in the system to perform a swap."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsRejectsUnconfirmedFirstBooking) {
    Customer* cust1 = addCustomer("First", 30, 500.0, false);
    Customer* cust2 = addCustomer("Second", 31, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "8A");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL101", "8B");
    ASSERT_NE(booking2, nullptr);

    std::string cancel_error;
    ASSERT_TRUE(rs.cancelBookingInternal(first_booking_id, cancel_error));

    test_in.str("6\n" + first_booking_id + "\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("First booking ID not found or not confirmed."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsRejectsUnconfirmedSecondBooking) {
    Customer* cust1 = addCustomer("First", 30, 500.0, false);
    Customer* cust2 = addCustomer("Second", 31, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "8C");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL101", "8D");
    ASSERT_NE(booking2, nullptr);
    const std::string second_booking_id = booking2->getBookingId();

    std::string cancel_error;
    ASSERT_TRUE(rs.cancelBookingInternal(second_booking_id, cancel_error));

    test_in.str("6\n" + first_booking_id + "\n" + second_booking_id + "\n0\n");
    rs.run();

    EXPECT_NE(
        test_out.str().find("Second booking ID not found or not confirmed."),
        std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsRejectsSameBookingViaMenu) {
    Customer* customer = addCustomer("Swap User", 30, 500.0, false);
    ASSERT_NE(customer, nullptr);

    Booking* booking1 = createConfirmedBooking(customer->getPersonId(), "FL101", "9A");
    ASSERT_NE(booking1, nullptr);
    const std::string booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking("CUST0001", "FL101", "9B");
    ASSERT_NE(booking2, nullptr);

    test_in.str("6\n" + booking_id + "\n" + booking_id + "\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("Cannot swap a booking with itself."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsRejectsDifferentFlightsViaMenu) {
    Customer* cust1 = addCustomer("MenuUserA", 30, 500.0, false);
    Customer* cust2 = addCustomer("MenuUserB", 32, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "9C");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL202", "1B");
    ASSERT_NE(booking2, nullptr);
    const std::string second_booking_id = booking2->getBookingId();

    test_in.str("6\n" + first_booking_id + "\n" + second_booking_id + "\n0\n");
    rs.run();

    const std::string output = test_out.str();
    EXPECT_NE(
        output.find("Seat swaps are currently only supported for bookings on the same flight."),
        std::string::npos);
    EXPECT_NE(output.find("Booking 1 is for flight FL101, Booking 2 is for flight FL202"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleSwapSeatsCancelledByUser) {
    Customer* cust1 = addCustomer("CancelUserA", 30, 500.0, false);
    Customer* cust2 = addCustomer("CancelUserB", 32, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "9D");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL101", "9E");
    ASSERT_NE(booking2, nullptr);
    const std::string second_booking_id = booking2->getBookingId();

    test_in.str("6\n" + first_booking_id + "\n" + second_booking_id + "\nn\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("Seat swap cancelled by user."), std::string::npos);
    EXPECT_EQ(rs.findBookingById(first_booking_id)->getSeatId(), "9D");
    EXPECT_EQ(rs.findBookingById(second_booking_id)->getSeatId(), "9E");
}

TEST_F(ReservationSystemTest, HandleSwapSeatsSuccessfulViaMenu) {
    Customer* cust1 = addCustomer("SwapUserA", 30, 500.0, false);
    Customer* cust2 = addCustomer("SwapUserB", 32, 500.0, false);
    ASSERT_NE(cust1, nullptr);
    ASSERT_NE(cust2, nullptr);

    Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), "FL101", "9F");
    ASSERT_NE(booking1, nullptr);
    const std::string first_booking_id = booking1->getBookingId();
    Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), "FL101", "10A");
    ASSERT_NE(booking2, nullptr);
    const std::string second_booking_id = booking2->getBookingId();

    test_in.str("6\n" + first_booking_id + "\n" + second_booking_id + "\ny\n0\n");
    rs.run();

    const Booking* updated_booking_1 = rs.findBookingById(first_booking_id);
    const Booking* updated_booking_2 = rs.findBookingById(second_booking_id);
    ASSERT_NE(updated_booking_1, nullptr);
    ASSERT_NE(updated_booking_2, nullptr);
    EXPECT_EQ(updated_booking_1->getSeatId(), "10A");
    EXPECT_EQ(updated_booking_2->getSeatId(), "9F");
    EXPECT_NE(test_out.str().find("Seat swap completed successfully!"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleAdminMenuShowsEmptyCustomersAndBookings) {
    rs.resetSystemForTest();

    test_in.str("7\n2\n7\n3\n0\n");
    rs.run();

    const std::string output = test_out.str();
    EXPECT_NE(output.find("--- All Customers ---"), std::string::npos);
    EXPECT_NE(output.find("No customers in system."), std::string::npos);
    EXPECT_NE(output.find("--- All Bookings ---"), std::string::npos);
    EXPECT_NE(output.find("No bookings in system."), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleAdminMenuReturnsToMainMenuOnZero) {
    test_in.str("7\n0\n0\n");
    rs.run();

    EXPECT_NE(test_out.str().find("--- Admin Options ---"), std::string::npos);
}

TEST_F(ReservationSystemTest, HandleAdminMenuAddsAirplaneAndRejectsDuplicateFlight) {
    test_in.str("7\n1\nFL303\n3\n4\n7\n1\nFL303\n0\n");
    rs.run();

    Airplane* added_airplane = rs.findAirplaneByFlightNumber("FL303");
    ASSERT_NE(added_airplane, nullptr);
    EXPECT_EQ(added_airplane->getCapacity(), 12);

    const std::string output = test_out.str();
    EXPECT_NE(output.find("Airplane FL303 added successfully."), std::string::npos);
    EXPECT_NE(output.find("An airplane with flight number FL303 already exists."), std::string::npos);
}

TEST_F(ReservationSystemTest, AddCustomerInternalAutoGeneratesApiDefaults) {
    Customer* customer = rs.addCustomerInternal("Ignored", 0, 0.0, true);
    ASSERT_NE(customer, nullptr);

    EXPECT_TRUE(has_expected_auto_generated_customer_name(customer->getName()));
    EXPECT_GE(customer->getAge(), 18);
    EXPECT_LE(customer->getAge(), 80);
    EXPECT_GE(customer->getMoney(), 100.0);
    EXPECT_LE(customer->getMoney(), 2000.0);
}

TEST_F(ReservationSystemTest, CreateBookingInternalReturnsDetailedErrors) {
    std::string error_message;

    EXPECT_EQ(rs.createBookingInternal("CUST9999", "FL101", "1A", error_message), nullptr);
    EXPECT_EQ(error_message, "Customer not found.");

    EXPECT_EQ(rs.createBookingInternal("CUST0001", "FL999", "1A", error_message), nullptr);
    EXPECT_EQ(error_message, "Airplane not found.");

    EXPECT_EQ(rs.createBookingInternal("CUST0001", "FL101", "99Z", error_message), nullptr);
    EXPECT_EQ(error_message, "Seat not found on this flight.");

    Airplane* plane = rs.findAirplaneByFlightNumber("FL101");
    ASSERT_NE(plane, nullptr);
    ASSERT_TRUE(plane->bookSpecificSeat("1A"));
    EXPECT_EQ(rs.createBookingInternal("CUST0001", "FL101", "1A", error_message), nullptr);
    EXPECT_EQ(error_message, "Seat is already booked.");

    Customer* poor_customer = rs.findCustomerById("CUST0002");
    ASSERT_NE(poor_customer, nullptr);
    poor_customer->setMoney(10.0);
    EXPECT_EQ(rs.createBookingInternal("CUST0002", "FL101", "4A", error_message), nullptr);
    EXPECT_EQ(error_message, "Insufficient funds.");
}
