// cppcheck-suppress-file missingIncludeSystem
#include "Booking.h"
#include <random> // For more unique ID generation (optional)
#include <sstream> // For ID generation and date formatting
#include <iomanip> // For date formatting (std::put_time)
#include <ctime>   // For std::time_t, std::localtime

namespace {
bool convertToLocalTime(std::time_t value, std::tm& outTm) {
#if defined(_WIN32)
    return localtime_s(&outTm, &value) == 0;
#else
    return localtime_r(&value, &outTm) != nullptr;
#endif
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

// Helper to convert BookingStatus to string
std::string bookingStatusToString(BookingStatus status) {
    switch (status) {
        case BookingStatus::CONFIRMED: return "Confirmed";
        case BookingStatus::CANCELLED: return "Cancelled";
        case BookingStatus::PENDING:   return "Pending";
        default: return "Unknown";
    }
}

// Helper to generate a somewhat unique booking ID
// A more robust system would use a global counter or UUIDs
std::string Booking::generateBookingId() {
    // Simple ID: BK + timestamp (seconds since epoch) + random number
    auto now = std::chrono::system_clock::now();
    auto epoch = now.time_since_epoch();
    auto seconds = std::chrono::duration_cast<std::chrono::seconds>(epoch).count();

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> distrib(100, 999);
    int randomNumber = distrib(gen);

    std::ostringstream oss;
    oss << "BK" << seconds << "-" << randomNumber;
    return oss.str();
}

// Constructor
Booking::Booking(const std::string& custId, const std::string& flightNum, const std::string& seatNum)
    : customerId(custId) {
    initializeBookingState(flightNum, seatNum, flightNumber, seatId, bookingDate, status);
    bookingId = generateBookingId();
    // std::cout << "Booking constructor called. ID: " << this->bookingId << std::endl; // Optional
}

// Destructor
Booking::~Booking() {
    // std::cout << "Booking destructor called for ID: " << this->bookingId << std::endl; // Optional
}

// Getters
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
    std::time_t time = std::chrono::system_clock::to_time_t(bookingDate);
    std::tm bt{};
    if (!convertToLocalTime(time, bt)) {
        return "1970-01-01 00:00:00";
    }
    std::ostringstream oss;
    oss << std::put_time(&bt, "%Y-%m-%d %H:%M:%S"); // Format: YYYY-MM-DD HH:MM:SS
    return oss.str();
}

BookingStatus Booking::getStatus() const {
    return status;
}

std::string Booking::getStatusString() const {
    return bookingStatusToString(this->status);
}

// Setters
void Booking::setStatus(BookingStatus newStatus) {
    this->status = newStatus;
}

void Booking::setSeatId(const std::string& newSeatId) {
    this->seatId = newSeatId;
}

// Display
void Booking::displayBookingDetails() const {
    std::cout << "Booking Details:" << std::endl;
    std::cout << "  Booking ID: " << bookingId << std::endl;
    std::cout << "  Customer ID: " << customerId << std::endl;
    std::cout << "  Flight Number: " << flightNumber << std::endl;
    std::cout << "  Seat ID: " << seatId << std::endl;
    std::cout << "  Booking Date: " << getBookingDateString() << std::endl;
    std::cout << "  Status: " << getStatusString() << std::endl;
}
