// cppcheck-suppress-file missingIncludeSystem
#include "Booking.h"
#include <cstdint>
#include <format>
#include <random>

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
    if (const auto remainder = dividend % divisor; remainder != 0 && ((remainder < 0) != (divisor < 0))) {
        --quotient;
    }
    return quotient;
}

CivilDateTime toCivilDateTime(std::chrono::system_clock::time_point timePoint) {
    const auto wholeSeconds = std::chrono::duration_cast<std::chrono::seconds>(timePoint.time_since_epoch()).count();

    std::int64_t dayCount = floorDiv(wholeSeconds, kSecondsPerDay);
    std::int64_t secondsIntoDay = wholeSeconds - (dayCount * kSecondsPerDay);
    if (secondsIntoDay < 0) {
        secondsIntoDay += kSecondsPerDay;
        --dayCount;
    }

    auto z = dayCount + 719468;
    const std::int64_t era = (z >= 0 ? z : z - 146096) / 146097;
    const auto dayOfEra = static_cast<unsigned int>(z - era * 146097);
    const auto yearOfEra = (dayOfEra - dayOfEra / 1460 + dayOfEra / 36524 - dayOfEra / 146096) / 365;
    const int year = static_cast<int>(yearOfEra + era * 400);
    const auto dayOfYear = dayOfEra - (365 * yearOfEra + yearOfEra / 4 - yearOfEra / 100);
    const auto monthPart = static_cast<int>((5 * dayOfYear + 2) / 153);
    const int day = static_cast<int>(dayOfYear - (153 * static_cast<unsigned int>(monthPart) + 2) / 5 + 1);
    const int month = monthPart + (monthPart < 10 ? 3 : -9);

    const int hour = static_cast<int>(secondsIntoDay / 3600);
    const int minute = static_cast<int>((secondsIntoDay % 3600) / 60);
    const int second = static_cast<int>(secondsIntoDay % 60);

    return {
        year + (month <= 2 ? 1 : 0),
        month,
        day,
        hour,
        minute,
        second,
    };
}

std::string formatBookingDate(std::chrono::system_clock::time_point timePoint) {
    const CivilDateTime civil = toCivilDateTime(timePoint);
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
    const std::string& flightNum,
    const std::string& seatNum,
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
} // namespace

std::string bookingStatusToString(BookingStatus status) {
    switch (status) {
        case BookingStatus::CONFIRMED: return "Confirmed";
        case BookingStatus::CANCELLED: return "Cancelled";
        case BookingStatus::PENDING: return "Pending";
        default: return "Unknown";
    }
}

std::string Booking::generateBookingId() {
    const auto now = std::chrono::system_clock::now();
    const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> distrib(100, 999);
    const int randomNumber = distrib(gen);

    std::ostringstream stream;
    stream << "BK" << seconds << '-' << randomNumber;
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
    return bookingStatusToString(this->status);
}

void Booking::setStatus(BookingStatus newStatus) {
    this->status = newStatus;
}

void Booking::setSeatId(const std::string& newSeatId) {
    this->seatId = newSeatId;
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
