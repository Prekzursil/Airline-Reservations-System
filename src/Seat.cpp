#include "Seat.h"
#include <iomanip> // For std::setprecision

// Helper function to convert SeatClass enum to string (can be outside class or static member)
std::string seatClassToString(SeatClass sc) {
    switch (sc) {
        case SeatClass::ECONOMY: return "Economy";
        case SeatClass::BUSINESS: return "Business";
        default: return "Unknown";
    }
}

// Constructor
Seat::Seat(const std::string& id, SeatClass sc, double basePrice)
    : seatId(id), isBooked(false), seatClass(sc) {
    if (sc == SeatClass::BUSINESS) {
        this->price = basePrice * 2.0; // Business seats are twice the price of economy base
    } else {
        this->price = basePrice;
    }
    // std::cout << "Seat constructor called for " << this->seatId << std::endl; // Optional
}

// Destructor
Seat::~Seat() {
    // std::cout << "Seat destructor called for " << this->seatId << std::endl; // Optional
}

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
        this->price = newPrice;
    }
    // else { std::cerr << "Price cannot be negative." << std::endl; } // Optional error handling
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
