#include "Booking.h"
#include <random> // For more unique ID generation (optional)
#include <sstream> // For ID generation and date formatting
#include <iomanip> // For date formatting (std::put_time)
#include <ctime>   // For std::time_t, std::localtime

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
    : customerId(custId), flightNumber(flightNum), seatId(seatNum), 
      bookingDate(std::chrono::system_clock::now()), status(BookingStatus::PENDING) {
    this->bookingId = generateBookingId();
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
    // Convert to tm struct for formatting
    // Note: std::localtime is not thread-safe. For multithreaded apps, use localtime_s (Windows) or localtime_r (POSIX).
    // For a simple console app, std::localtime is generally fine.
    std::tm bt = *std::localtime(&time); 
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
