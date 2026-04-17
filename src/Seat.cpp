// cppcheck-suppress-file missingIncludeSystem
#include "Seat.h"
#include <iomanip> // For std::setprecision

// Helper function to convert SeatClass enum to string (can be outside class or static member)
std::string seatClassToString(SeatClass sc) {
    using enum SeatClass;

    switch (sc) {
        case ECONOMY: return "Economy";
        case BUSINESS: return "Business";
        default: return "Unknown";
    }
}

// Constructor
Seat::Seat(std::string_view id, SeatClass sc, double basePrice)
    : isBooked(false) {
    applyIdentityAndPrice(id, sc, basePrice);
}

void Seat::applyIdentityAndPrice(std::string_view id, SeatClass sc, double basePrice) {
    seatId = id;
    price = (sc == SeatClass::BUSINESS) ? basePrice * 2.0 : basePrice;
    seatClass = sc;
}

// Destructor
Seat::~Seat() = default;

// Getters
std::string Seat::getSeatId() const {
    return seatId;
}

bool Seat::getIsBooked() const {
    return isBooked;
}

double Seat::getPrice() const {
    return price;
}

SeatClass Seat::getSeatClass() const {
    return seatClass;
}

std::string Seat::getSeatClassString() const {
    return seatClassToString(this->seatClass);
}

// Setters
void Seat::setPrice(double newPrice) {
    if (newPrice >= 0.0) {
        price = newPrice;
    }
}

// Booking operations
bool Seat::bookSeat() {
    if (!isBooked) {
        isBooked = true;
        return true; // Successfully booked
    }
    return false; // Already booked
}

bool Seat::unbookSeat() {
    if (isBooked) {
        isBooked = false;
        return true; // Successfully unbooked
    }
    return false; // Was not booked
}

// Display
void Seat::displaySeatInfo() const {
    std::cout << "Seat ID: " << seatId
              << ", Class: " << getSeatClassString()
              << ", Price: $" << std::fixed << std::setprecision(2) << price
              << ", Status: " << (isBooked ? "Booked" : "Available") << std::endl;
}
