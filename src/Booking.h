// cppcheck-suppress-file missingIncludeSystem
#ifndef BOOKING_H
#define BOOKING_H

#include <chrono>   // For bookingDate (optional, could use string)
#include <iostream> // For display
#include <string>
#include <string_view>

class BookingTestAccess;

enum class BookingStatus {
    CONFIRMED,
    CANCELLED,
    PENDING
};

class Booking {
private:
    std::string bookingId;
    std::string customerId; // Link to Customer
    std::string flightNumber; // Link to Airplane
    std::string seatId;     // Link to Seat
    std::chrono::system_clock::time_point bookingDate; // Or std::string for simplicity
    BookingStatus status;

    std::string generateBookingId() const; // Helper to create a unique ID
    void applyFlightAndSeat(std::string_view flightNum, std::string_view seatNum); // Helper to populate state

    friend class BookingTestAccess;

public:
    // Constructor
    Booking(std::string_view custId, std::string_view flightNum, std::string_view seatNum);

    // Destructor
    ~Booking();

    // Getters
    std::string getBookingId() const;
    std::string getCustomerId() const;
    std::string getFlightNumber() const;
    std::string getSeatId() const;
    std::string getBookingDateString() const; // Returns formatted date string
    BookingStatus getStatus() const;
    std::string getStatusString() const;

    // Setters
    void setStatus(BookingStatus newStatus);
    void setSeatId(std::string_view newSeatId); // Added for seat swap

    // Display
    void displayBookingDetails() const;
};

#endif // BOOKING_H
