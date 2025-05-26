#ifndef AIRPLANE_H
#define AIRPLANE_H

#include "Seat.h"
#include "Customer.h" // For suggesting seats based on customer money
#include <vector>
#include <string>
#include <iostream> // For display methods

class Airplane {
private:
    std::string flightNumber;
    std::vector<Seat> seats;
    int totalRows;
    int seatsPerRow; // e.g. 6 for A-F
    int bookedSeatsCount;

    void initializeSeats(); // Helper to create seats based on rows/seatsPerRow

public:
    // Constructor
    Airplane(const std::string& flightNum = "FL000", int rows = 10, int sPerRow = 6);

    // Destructor
    ~Airplane();

    // Getters
    std::string getFlightNumber() const;
    int getCapacity() const;
    int getBookedSeatsCount() const;
    bool isFull() const;
    const std::vector<Seat>& getAllSeats() const; // To view all seats

    // Seat operations
    Seat* findSeat(const std::string& seatId); // Returns pointer to seat, or nullptr if not found
    bool bookSpecificSeat(const std::string& seatId); // Attempts to book a seat by ID
    bool unbookSpecificSeat(const std::string& seatId); // Attempts to unbook a seat by ID

    // Display
    void displaySeatingMap() const; // Visual representation of seats
    void displayAvailableSeats() const;
    void displayAllSeatDetails() const;

    // Advanced features
    std::vector<const Seat*> getAvailableSeatsByClass(SeatClass sc) const;
    std::vector<const Seat*> suggestLowerPriceSeats(const Customer* customer, double maxPrice) const;
};

#endif // AIRPLANE_H
