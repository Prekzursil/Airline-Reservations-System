#include "gtest/gtest.h"
#include "../src/Booking.h" // Adjust path
#include <thread> // For std::this_thread::sleep_for
#include <chrono> // For std::chrono::milliseconds

// Forward declaration for the helper function in Booking.cpp to test its default case
std::string bookingStatusToString(BookingStatus status);

// Test fixture for Booking tests
class BookingTest : public ::testing::Test {
protected:
    Booking* b1;
    Booking* b2;

    void SetUp() override {
        b1 = new Booking("C0001", "FL101", "1A");
        // Introduce a small delay to ensure booking IDs and dates are different if generated close together
        std::this_thread::sleep_for(std::chrono::milliseconds(10)); 
        b2 = new Booking("C0002", "FL202", "2B");
    }

    void TearDown() override {
        delete b1;
        delete b2;
        b1 = nullptr;
        b2 = nullptr;
    }
};

// Test constructor and getters
TEST_F(BookingTest, ConstructorAndGetters) {
    EXPECT_EQ(b1->getCustomerId(), "C0001");
    EXPECT_EQ(b1->getFlightNumber(), "FL101");
    EXPECT_EQ(b1->getSeatId(), "1A");
    EXPECT_EQ(b1->getStatus(), BookingStatus::PENDING); // Default status
    EXPECT_EQ(b1->getStatusString(), "Pending");
    
    // Booking ID should be generated and not empty
    EXPECT_FALSE(b1->getBookingId().empty());
    EXPECT_NE(b1->getBookingId(), b2->getBookingId()); // IDs should be unique

    // Booking date string should be generated and not empty
    EXPECT_FALSE(b1->getBookingDateString().empty());
    // std::cout << "B1 Date: " << b1->getBookingDateString() << std::endl; // For manual inspection
    // std::cout << "B2 Date: " << b2->getBookingDateString() << std::endl;
    // Dates might be very close, but IDs should differ due to random component or time progression
}

// Test setStatus
TEST_F(BookingTest, SetStatus) {
    b1->setStatus(BookingStatus::CONFIRMED);
    EXPECT_EQ(b1->getStatus(), BookingStatus::CONFIRMED);
    EXPECT_EQ(b1->getStatusString(), "Confirmed");

    b1->setStatus(BookingStatus::CANCELLED);
    EXPECT_EQ(b1->getStatus(), BookingStatus::CANCELLED);
    EXPECT_EQ(b1->getStatusString(), "Cancelled");
}

// Test getStatusString for all statuses
TEST_F(BookingTest, GetStatusStringAll) {
    b1->setStatus(BookingStatus::PENDING);
    EXPECT_EQ(b1->getStatusString(), "Pending");
    b1->setStatus(BookingStatus::CONFIRMED);
    EXPECT_EQ(b1->getStatusString(), "Confirmed");
    b1->setStatus(BookingStatus::CANCELLED);
    EXPECT_EQ(b1->getStatusString(), "Cancelled");
    // Test for an unknown status if it were possible to set one (not directly possible with enum class)
}

// Test bookingStatusToString default case
TEST_F(BookingTest, BookingStatusToStringDefault) {
    // Cast an integer to BookingStatus that is out of range for defined enums
    BookingStatus unknownBs = static_cast<BookingStatus>(99);
    EXPECT_EQ(bookingStatusToString(unknownBs), "Unknown");
}

// Test setSeatId
TEST_F(BookingTest, SetSeatId) {
    b1->setSeatId("NEW10X");
    EXPECT_EQ(b1->getSeatId(), "NEW10X");
}

// Test displayBookingDetails - check for no crash
TEST_F(BookingTest, DisplayBookingDetailsNoCrash) {
    EXPECT_NO_THROW(b1->displayBookingDetails());
}

// Test generateBookingId uniqueness (probabilistic)
TEST_F(BookingTest, GenerateBookingIdUniqueness) {
    std::string id1 = b1->getBookingId();
    // Create a new booking to get another ID
    Booking tempBooking("C0003", "FL303", "3C");
    std::string id2 = tempBooking.getBookingId();
    EXPECT_NE(id1, id2);

    // Test a few more times
    Booking tempBooking2("C0004", "FL404", "4D");
    EXPECT_NE(id1, tempBooking2.getBookingId());
    EXPECT_NE(id2, tempBooking2.getBookingId());
}
