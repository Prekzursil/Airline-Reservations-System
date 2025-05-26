#include "gtest/gtest.h"
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
    const_cast<std::vector<Customer>*>(&rs.getCustomersForTest())->clear(); // Hacky way to clear private member for test

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
    Booking* booking2 = rs.createBookingInternal(cust2->getPersonId(), "FL202", "1A", bookingError);
    ASSERT_NE(booking2, nullptr);

    std::string errorMsg;
    EXPECT_FALSE(rs.swapSeatsInternal(booking1->getBookingId(), booking2->getBookingId(), errorMsg));
    EXPECT_NE(errorMsg.find("only supported for bookings on the same flight"), std::string::npos);
}
