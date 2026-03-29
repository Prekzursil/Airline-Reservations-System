// cppcheck-suppress-file missingIncludeSystem
#include "Booking.h"
#include <cstdint>
#include <functional>
#include <format>
#include <sstream>
#include <string_view>

namespace {
constexpr std::int64_t kSecondsPerDay = 24LL * 60LL * 60LL;

struct CivilDateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute;
    int second;
};

std::int64_t floorDiv(std::int64_t dividend, std::int64_t divisor) {
    std::int64_t quotient = dividend / divisor;
    if (const auto remainder = dividend % divisor;
        remainder != 0 && ((remainder < 0) != (divisor < 0))) {
        --quotient;
    }
    return quotient;
}

CivilDateTime toCivilDateTime(std::chrono::system_clock::time_point timePoint) {
    const auto wholeSeconds = std::chrono::duration_cast<std::chrono::seconds>(timePoint.time_since_epoch()).count();

    const std::int64_t dayCount = floorDiv(wholeSeconds, kSecondsPerDay);
    const std::int64_t secondsIntoDay = wholeSeconds - (dayCount * kSecondsPerDay);

    const auto z = dayCount + 719468;
    const std::int64_t era = floorDiv(z, 146097);
    const auto dayOfEra = static_cast<unsigned int>(z - era * 146097);
    const auto yearOfEra = (dayOfEra - dayOfEra / 1460 + dayOfEra / 36524 - dayOfEra / 146096) / 365;
    const auto year = static_cast<int>(yearOfEra + era * 400);
    const auto dayOfYear = dayOfEra - (365 * yearOfEra + yearOfEra / 4 - yearOfEra / 100);
    const auto monthPart = static_cast<int>((5 * dayOfYear + 2) / 153);
    const auto day = static_cast<int>(dayOfYear - (153 * static_cast<unsigned int>(monthPart) + 2) / 5 + 1);
    int month = monthPart;
    if (monthPart < 10) {
        month += 3;
    } else {
        month -= 9;
    }

    const auto hour = static_cast<int>(secondsIntoDay / 3600);
    const auto minute = static_cast<int>((secondsIntoDay % 3600) / 60);
    const auto second = static_cast<int>(secondsIntoDay % 60);

    int adjustedYear = year;
    if (month <= 2) {
        ++adjustedYear;
    }

    return {
        adjustedYear,
        month,
        day,
        hour,
        minute,
        second,
    };
}

std::string formatBookingDate(std::chrono::system_clock::time_point timePoint) {
    const auto civil = toCivilDateTime(timePoint);
    return std::format(
        "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        civil.year,
        civil.month,
        civil.day,
        civil.hour,
        civil.minute,
        civil.second
    );
}

void initializeBookingState(
    std::string_view flightNum,
    std::string_view seatNum,
    std::string& flightNumberOut,
    std::string& seatIdOut,
    std::chrono::system_clock::time_point& bookingDateOut,
    BookingStatus& statusOut
) {
    flightNumberOut = flightNum;
    seatIdOut = seatNum;
    bookingDateOut = std::chrono::system_clock::now();
    statusOut = BookingStatus::PENDING;
}

std::uint64_t bookingSuffixToken(
    const std::chrono::system_clock::time_point timePoint,
    std::string_view customerId,
    std::string_view flightNumber,
    std::string_view seatId
) {
    const auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(
        timePoint.time_since_epoch()
    ).count();
    const auto customerHash = std::hash<std::string_view>{}(customerId);
    const auto flightHash = std::hash<std::string_view>{}(flightNumber);
    const auto seatHash = std::hash<std::string_view>{}(seatId);

    return static_cast<std::uint64_t>(microseconds)
        ^ (customerHash << 1U)
        ^ (flightHash << 7U)
        ^ (seatHash << 13U);
}
} // namespace

std::string bookingStatusToString(BookingStatus status) {
    using enum BookingStatus;
    switch (status) {
        case CONFIRMED: return "Confirmed";
        case CANCELLED: return "Cancelled";
        case PENDING: return "Pending";
        default: return "Unknown";
    }
}

std::string Booking::generateBookingId() const {
    const auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(
        bookingDate.time_since_epoch()
    ).count();
    const auto suffix = bookingSuffixToken(bookingDate, customerId, flightNumber, seatId);

    std::ostringstream stream;
    stream << "BK" << microseconds << '-' << suffix;
    return stream.str();
}

Booking::Booking(const std::string& custId, const std::string& flightNum, const std::string& seatNum)
    : customerId(custId) {
    initializeBookingState(flightNum, seatNum, flightNumber, seatId, bookingDate, status);
    bookingId = generateBookingId();
}

Booking::~Booking() = default;

std::string Booking::getBookingId() const {
    return bookingId;
}

std::string Booking::getCustomerId() const {
    return customerId;
}

std::string Booking::getFlightNumber() const {
    return flightNumber;
}

std::string Booking::getSeatId() const {
    return seatId;
}

std::string Booking::getBookingDateString() const {
    if (bookingDate.time_since_epoch() == std::chrono::system_clock::duration::zero()) {
        return "1970-01-01 00:00:00";
    }
    return formatBookingDate(bookingDate);
}

BookingStatus Booking::getStatus() const {
    return status;
}

std::string Booking::getStatusString() const {
    return bookingStatusToString(status);
}

void Booking::setStatus(BookingStatus newStatus) {
    status = newStatus;
}

void Booking::setSeatId(std::string_view newSeatId) {
    seatId = newSeatId;
}

void Booking::displayBookingDetails() const {
    std::cout << "Booking Details:" << std::endl;
    std::cout << "  Booking ID: " << bookingId << std::endl;
    std::cout << "  Customer ID: " << customerId << std::endl;
    std::cout << "  Flight Number: " << flightNumber << std::endl;
    std::cout << "  Seat ID: " << seatId << std::endl;
    std::cout << "  Booking Date: " << getBookingDateString() << std::endl;
    std::cout << "  Status: " << getStatusString() << std::endl;
}
