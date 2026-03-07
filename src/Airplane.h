// cppcheck-suppress-file missingIncludeSystem
#ifndef AIRPLANE_H
#define AIRPLANE_H

#include "Seat.h"
#include "Customer.h" // For suggesting seats based on customer money
#include <string>
#include <string_view>
#include <vector>

class AirplaneTestAccess;

class Airplane {
private:
    std::string flightNumber;
    std::vector<Seat> seats;
    int totalRows;
    int seatsPerRow; // e.g. 6 for A-F
    int bookedSeatsCount;

    void initializeSeats(); // Helper to create seats based on rows/seatsPerRow

    friend class AirplaneTestAccess;

public:
    // Constructor
    explicit Airplane(std::string_view flightNum = "FL000", int rows = 10, int sPerRow = 6);

    // Destructor
    ~Airplane();

    // Getters
    std::string getFlightNumber() const;
    int getCapacity() const;
    int getBookedSeatsCount() const;
    bool isFull() const;
    const std::vector<Seat>& getAllSeats() const; // To view all seats

    // Seat operations
    Seat* findSeat(std::string_view seatId); // Returns pointer to seat, or nullptr if not found
    bool bookSpecificSeat(std::string_view seatId); // Attempts to book a seat by ID
    bool unbookSpecificSeat(std::string_view seatId); // Attempts to unbook a seat by ID

    // Display
    void displaySeatingMap() const; // Visual representation of seats
    void displayAvailableSeats() const;
    void displayAllSeatDetails() const;

    // Advanced features
    std::vector<const Seat*> getAvailableSeatsByClass(SeatClass sc) const;
    std::vector<const Seat*> suggestLowerPriceSeats(const Customer* customer, double maxPrice) const;
};

#endif // AIRPLANE_H
