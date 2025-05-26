#ifndef SEAT_H
#define SEAT_H

#include <string>
#include <iostream> // For display

// Enum for seat class
enum class SeatClass {
    ECONOMY,
    BUSINESS
};

// Forward declaration if needed, but not for simple enums like this
// std::string seatClassToString(SeatClass sc); // Helper function prototype

class Seat {
private:
    std::string seatId;     // e.g., "1A", "12F"
    bool isBooked;
    double price;
    SeatClass seatClass;

public:
    // Constructor
    Seat(const std::string& id = "N/A", SeatClass sc = SeatClass::ECONOMY, double basePrice = 50.0);

    // Destructor
    ~Seat();

    // Getters
    std::string getSeatId() const;
    bool getIsBooked() const; // Renamed from isBooked to follow getter convention
    double getPrice() const;
    SeatClass getSeatClass() const;
    std::string getSeatClassString() const; // Helper to get string representation

    // Setters
    void setPrice(double newPrice);
    // seatId and seatClass are typically set at creation and not changed.

    // Booking operations
    bool bookSeat();   // Returns true if booking was successful
    bool unbookSeat(); // Returns true if unbooking was successful

    // Display
    void displaySeatInfo() const;
};

#endif // SEAT_H
