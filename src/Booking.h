#ifndef BOOKING_H
#define BOOKING_H

#include <string>
#include <iostream> // For display
#include <chrono>   // For bookingDate (optional, could use string)
#include <sstream>  // For formatting date
#include <iomanip>  // For formatting date

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

    std::string generateBookingId(); // Helper to create a unique ID

public:
    // Constructor
    Booking(const std::string& custId, const std::string& flightNum, const std::string& seatNum);

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
    void setSeatId(const std::string& newSeatId); // Added for seat swap

    // Display
    void displayBookingDetails() const;
};

#endif // BOOKING_H
