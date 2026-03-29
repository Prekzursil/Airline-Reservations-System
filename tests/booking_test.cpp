// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include <chrono>
#include <cstdint>
#include <format>
#include <regex>
#include <string>
#include <string_view>
#include <thread>
#include <unordered_set>
#include <vector>

#include "../src/Booking.h"

using enum BookingStatus;

namespace {
struct TransparentStringHash {
    using is_transparent = void;

    std::size_t operator()(std::string_view value) const noexcept {
        return std::hash<std::string_view>{}(value);
    }

    std::size_t operator()(const std::string& value) const noexcept {
        return operator()(std::string_view{value});
    }
};

using TransparentStringSet =
    std::unordered_set<std::string, TransparentStringHash, std::equal_to<>>;
} // namespace

class BookingTestAccess {
public:
    static void setBookingDate(Booking& booking, const std::chrono::system_clock::time_point booking_date) {
        booking.bookingDate = booking_date;
    }

private:
    BookingTestAccess() = default;
    ~BookingTestAccess() = default;
};

std::string bookingStatusToString(BookingStatus status);

class BookingTest : public ::testing::Test {
protected:
    Booking& firstBooking() { return b1_; }
    Booking& secondBooking() { return b2_; }

private:
    Booking b1_{"C0001", "FL101", "1A"};
    Booking b2_ = [] {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        return Booking("C0002", "FL202", "2B");
    }();
};

TEST_F(BookingTest, ConstructorAndGetters) {
    EXPECT_EQ(firstBooking().getCustomerId(), "C0001");
    EXPECT_EQ(firstBooking().getFlightNumber(), "FL101");
    EXPECT_EQ(firstBooking().getSeatId(), "1A");
    EXPECT_EQ(firstBooking().getStatus(), PENDING);
    EXPECT_EQ(firstBooking().getStatusString(), "Pending");

    EXPECT_FALSE(firstBooking().getBookingId().empty());
    EXPECT_NE(firstBooking().getBookingId(), secondBooking().getBookingId());

    EXPECT_FALSE(firstBooking().getBookingDateString().empty());
    EXPECT_TRUE(std::regex_match(firstBooking().getBookingDateString(), std::regex(R"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")));
}

TEST_F(BookingTest, SetStatus) {
    firstBooking().setStatus(CONFIRMED);
    EXPECT_EQ(firstBooking().getStatus(), CONFIRMED);
    EXPECT_EQ(firstBooking().getStatusString(), "Confirmed");

    firstBooking().setStatus(CANCELLED);
    EXPECT_EQ(firstBooking().getStatus(), CANCELLED);
    EXPECT_EQ(firstBooking().getStatusString(), "Cancelled");
}

TEST_F(BookingTest, GetStatusStringAll) {
    firstBooking().setStatus(PENDING);
    EXPECT_EQ(firstBooking().getStatusString(), "Pending");
    firstBooking().setStatus(CONFIRMED);
    EXPECT_EQ(firstBooking().getStatusString(), "Confirmed");
    firstBooking().setStatus(CANCELLED);
    EXPECT_EQ(firstBooking().getStatusString(), "Cancelled");
}

TEST_F(BookingTest, BookingStatusToStringDefault) {
    const auto unknownBs = static_cast<BookingStatus>(99);
    EXPECT_EQ(bookingStatusToString(unknownBs), "Unknown");
}

TEST_F(BookingTest, SetSeatId) {
    firstBooking().setSeatId("NEW10X");
    EXPECT_EQ(firstBooking().getSeatId(), "NEW10X");
}

TEST_F(BookingTest, DisplayBookingDetailsNoCrash) {
    EXPECT_NO_THROW(firstBooking().displayBookingDetails());
}

TEST_F(BookingTest, GenerateBookingIdUniqueness) {
    const std::string id1 = firstBooking().getBookingId();
    Booking tempBooking("C0003", "FL303", "3C");
    const std::string id2 = tempBooking.getBookingId();
    EXPECT_NE(id1, id2);

    Booking tempBooking2("C0004", "FL404", "4D");
    EXPECT_NE(id1, tempBooking2.getBookingId());
    EXPECT_NE(id2, tempBooking2.getBookingId());
}

TEST_F(BookingTest, GenerateBookingIdUsesBkPrefixAndUniqueNumericSuffix) {
    constexpr int booking_count = 20;
    std::vector<std::string> generated_ids;
    generated_ids.reserve(booking_count);

    for (int index = 0; index < booking_count; ++index) {
        Booking booking(
            std::format("C{}", 1000 + index),
            std::format("FL{}", 500 + index),
            std::format("{}A", index + 1)
        );
        generated_ids.push_back(booking.getBookingId());
    }

    const std::regex booking_id_pattern(R"(^BK\d+-\d+$)");
    TransparentStringSet unique_ids;
    TransparentStringSet unique_suffixes;
    for (const std::string& booking_id : generated_ids) {
        ASSERT_TRUE(std::regex_match(booking_id, booking_id_pattern)) << booking_id;
        EXPECT_TRUE(unique_ids.insert(booking_id).second) << booking_id;

        const auto dash_position = booking_id.rfind('-');
        ASSERT_NE(dash_position, std::string::npos) << booking_id;

        const std::string suffix = booking_id.substr(dash_position + 1);
        EXPECT_TRUE(unique_suffixes.insert(suffix).second) << booking_id;
    }
}

TEST_F(BookingTest, GetBookingDateStringHandlesEpochAndNegativeTimes) {
    BookingTestAccess::setBookingDate(firstBooking(), std::chrono::system_clock::time_point{});
    EXPECT_EQ(firstBooking().getBookingDateString(), "1970-01-01 00:00:00");

    BookingTestAccess::setBookingDate(
        firstBooking(),
        std::chrono::system_clock::time_point{std::chrono::seconds{1}});
    EXPECT_EQ(firstBooking().getBookingDateString(), "1970-01-01 00:00:01");

    BookingTestAccess::setBookingDate(
        firstBooking(),
        std::chrono::system_clock::time_point{std::chrono::seconds{-1}});
    EXPECT_EQ(firstBooking().getBookingDateString(), "1969-12-31 23:59:59");

    BookingTestAccess::setBookingDate(
        firstBooking(),
        std::chrono::system_clock::time_point{std::chrono::days{-719469}});
    EXPECT_TRUE(
        std::regex_match(
            firstBooking().getBookingDateString(),
            std::regex(R"(-?\d{3,}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")));

    BookingTestAccess::setBookingDate(
        firstBooking(),
        std::chrono::sys_days{std::chrono::year{2024} / 12 / 31}
            + std::chrono::hours{23}
            + std::chrono::minutes{59}
            + std::chrono::seconds{59});
    EXPECT_EQ(firstBooking().getBookingDateString(), "2024-12-31 23:59:59");

    BookingTestAccess::setBookingDate(
        firstBooking(),
        std::chrono::sys_days{std::chrono::year{-4000} / 1 / 1});
    EXPECT_FALSE(firstBooking().getBookingDateString().empty());
}
