// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include <chrono>
#include <regex>
#include <thread>

#define private public
#include "../src/Booking.h"
#undef private

std::string bookingStatusToString(BookingStatus status);

class BookingTest : public ::testing::Test {
protected:
    Booking b1{"C0001", "FL101", "1A"};
    Booking b2 = [] {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        return Booking("C0002", "FL202", "2B");
    }();
};

TEST_F(BookingTest, ConstructorAndGetters) {
    EXPECT_EQ(b1.getCustomerId(), "C0001");
    EXPECT_EQ(b1.getFlightNumber(), "FL101");
    EXPECT_EQ(b1.getSeatId(), "1A");
    EXPECT_EQ(b1.getStatus(), BookingStatus::PENDING);
    EXPECT_EQ(b1.getStatusString(), "Pending");

    EXPECT_FALSE(b1.getBookingId().empty());
    EXPECT_NE(b1.getBookingId(), b2.getBookingId());

    EXPECT_FALSE(b1.getBookingDateString().empty());
    EXPECT_TRUE(std::regex_match(b1.getBookingDateString(), std::regex(R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")));
}

TEST_F(BookingTest, SetStatus) {
    b1.setStatus(BookingStatus::CONFIRMED);
    EXPECT_EQ(b1.getStatus(), BookingStatus::CONFIRMED);
    EXPECT_EQ(b1.getStatusString(), "Confirmed");

    b1.setStatus(BookingStatus::CANCELLED);
    EXPECT_EQ(b1.getStatus(), BookingStatus::CANCELLED);
    EXPECT_EQ(b1.getStatusString(), "Cancelled");
}

TEST_F(BookingTest, GetStatusStringAll) {
    b1.setStatus(BookingStatus::PENDING);
    EXPECT_EQ(b1.getStatusString(), "Pending");
    b1.setStatus(BookingStatus::CONFIRMED);
    EXPECT_EQ(b1.getStatusString(), "Confirmed");
    b1.setStatus(BookingStatus::CANCELLED);
    EXPECT_EQ(b1.getStatusString(), "Cancelled");
}

TEST_F(BookingTest, BookingStatusToStringDefault) {
    const auto unknownBs = static_cast<BookingStatus>(99);
    EXPECT_EQ(bookingStatusToString(unknownBs), "Unknown");
}

TEST_F(BookingTest, SetSeatId) {
    b1.setSeatId("NEW10X");
    EXPECT_EQ(b1.getSeatId(), "NEW10X");
}

TEST_F(BookingTest, DisplayBookingDetailsNoCrash) {
    EXPECT_NO_THROW(b1.displayBookingDetails());
}

TEST_F(BookingTest, GenerateBookingIdUniqueness) {
    const std::string id1 = b1.getBookingId();
    Booking tempBooking("C0003", "FL303", "3C");
    const std::string id2 = tempBooking.getBookingId();
    EXPECT_NE(id1, id2);

    Booking tempBooking2("C0004", "FL404", "4D");
    EXPECT_NE(id1, tempBooking2.getBookingId());
    EXPECT_NE(id2, tempBooking2.getBookingId());
}

TEST_F(BookingTest, GetBookingDateStringHandlesEpochAndNegativeTimes) {
    b1.bookingDate = std::chrono::system_clock::time_point{};
    EXPECT_EQ(b1.getBookingDateString(), "1970-01-01 00:00:00");

    b1.bookingDate = std::chrono::system_clock::time_point{std::chrono::seconds{-1}};
    EXPECT_EQ(b1.getBookingDateString(), "1969-12-31 23:59:59");
}
