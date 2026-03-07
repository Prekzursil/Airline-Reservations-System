// cppcheck-suppress-file missingIncludeSystem
#include "reservation_system_test_fixture.h"

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
    const Customer* cust = rs.addCustomerInternal("Test User", 25, 1000.0, false);
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
    const Customer* cust1 = rs.addCustomerInternal("Test User", 25, 1000.0, false);
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
    const Customer* cust1 = rs.addCustomerInternal("UserA", 30, 500.0, false);
    const Customer* cust2 = rs.addCustomerInternal("UserB", 35, 600.0, false);
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
