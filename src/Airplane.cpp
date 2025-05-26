#include "Airplane.h"
#include <algorithm> // For std::find_if

// Constructor
Airplane::Airplane(const std::string& flightNum, int rows, int sPerRow)
    : flightNumber(flightNum), totalRows(rows), seatsPerRow(sPerRow), bookedSeatsCount(0) {
    if (this->totalRows <= 0) this->totalRows = 1; // Min 1 row
    if (this->seatsPerRow <= 0) this->seatsPerRow = 1; // Min 1 seat per row
    initializeSeats();
    // std::cout << "Airplane constructor called for " << this->flightNumber << std::endl; // Optional
}

// Destructor
Airplane::~Airplane() {
    // std::cout << "Airplane destructor called for " << this->flightNumber << std::endl; // Optional
}

// Helper to create seats
void Airplane::initializeSeats() {
    seats.clear(); // Clear any existing seats if this method were called again
    char seatLetter = 'A';
    double economyBasePrice = 50.0;  // Default base price for economy
    double businessBasePrice = 100.0; // Default base price for business (or use a multiplier)

    // Example: First 20% of rows are Business, rest Economy
    int businessRows = static_cast<int>(totalRows * 0.2);
    if (businessRows == 0 && totalRows > 0) businessRows = 1; // At least one business row if plane is small but has business class

    for (int i = 1; i <= totalRows; ++i) {
        for (int j = 0; j < seatsPerRow; ++j) {
            std::string id = std::to_string(i) + static_cast<char>(seatLetter + j);
            SeatClass sc = (i <= businessRows) ? SeatClass::BUSINESS : SeatClass::ECONOMY;
            double price = (sc == SeatClass::BUSINESS) ? businessBasePrice : economyBasePrice;
            // Adjust price based on row or seat position if desired (e.g. window seats more expensive)
            // For simplicity, using fixed base prices per class for now.
            seats.emplace_back(id, sc, price);
        }
    }
}

// Getters
std::string Airplane::getFlightNumber() const {
    return flightNumber;
}

int Airplane::getCapacity() const {
    return totalRows * seatsPerRow;
}

int Airplane::getBookedSeatsCount() const {
    return bookedSeatsCount;
}

bool Airplane::isFull() const {
    return bookedSeatsCount >= getCapacity();
}

const std::vector<Seat>& Airplane::getAllSeats() const {
    return seats;
}

// Seat operations
Seat* Airplane::findSeat(const std::string& seatId) {
    for (size_t i = 0; i < seats.size(); ++i) {
        if (seats[i].getSeatId() == seatId) {
            return &seats[i];
        }
    }
    return nullptr; // Not found
}

bool Airplane::bookSpecificSeat(const std::string& seatId) {
    Seat* seatToBook = findSeat(seatId);
    if (seatToBook && !seatToBook->getIsBooked()) {
        if (seatToBook->bookSeat()) {
            bookedSeatsCount++;
            return true;
        }
    }
    return false; // Seat not found or already booked
}

bool Airplane::unbookSpecificSeat(const std::string& seatId) {
    Seat* seatToUnbook = findSeat(seatId);
    if (seatToUnbook && seatToUnbook->getIsBooked()) {
        if (seatToUnbook->unbookSeat()) {
            bookedSeatsCount--;
            return true;
        }
    }
    return false; // Seat not found or not booked
}

// Display
void Airplane::displaySeatingMap() const {
    std::cout << "\n--- Seating Map for Flight " << flightNumber << " ---" << std::endl;
    std::cout << "  "; // Space for row numbers
    for (int j = 0; j < seatsPerRow; ++j) {
        std::cout << static_cast<char>('A' + j) << " ";
    }
    std::cout << std::endl;

    size_t seatIndex = 0; // Changed int to size_t
    for (int i = 1; i <= totalRows; ++i) {
        std::cout << i << (i < 10 ? "  " : " "); // Row number
        for (int j = 0; j < seatsPerRow; ++j) {
            if (seatIndex < seats.size()) {
                const Seat& s = seats[seatIndex++];
                char displayChar = s.getIsBooked() ? 'X' : (s.getSeatClass() == SeatClass::BUSINESS ? 'B' : 'E');
                std::cout << displayChar << " ";
            } else {
                std::cout << "  "; // Should not happen if initialized correctly
            }
        }
        std::cout << std::endl;
    }
    std::cout << "Legend: X=Booked, B=Available Business, E=Available Economy" << std::endl;
}

void Airplane::displayAvailableSeats() const {
    std::cout << "\n--- Available Seats for Flight " << flightNumber << " ---" << std::endl;
    bool found = false;
    for (const auto& seat : seats) {
        if (!seat.getIsBooked()) {
            seat.displaySeatInfo();
            found = true;
        }
    }
    if (!found) {
        std::cout << "No seats available." << std::endl;
    }
}

void Airplane::displayAllSeatDetails() const {
    std::cout << "\n--- All Seat Details for Flight " << flightNumber << " ---" << std::endl;
    if (seats.empty()) {
        std::cout << "No seats configured for this airplane." << std::endl;
        return;
    }
    for (const auto& seat : seats) {
        seat.displaySeatInfo();
    }
}


// Advanced features
std::vector<const Seat*> Airplane::getAvailableSeatsByClass(SeatClass sc) const {
    std::vector<const Seat*> available;
    for (const auto& seat : seats) { // Iterate over const Seat objects
        if (!seat.getIsBooked() && seat.getSeatClass() == sc) {
            available.push_back(&seat); // Push const Seat*
        }
    }
    return available;
}

std::vector<const Seat*> Airplane::suggestLowerPriceSeats(const Customer* customer, double maxPrice) const {
    std::vector<const Seat*> suggestions;
    if (!customer) return suggestions;

    for (const auto& seat : seats) { // Iterate over const Seat objects
        if (!seat.getIsBooked() && seat.getPrice() <= maxPrice && seat.getPrice() <= customer->getMoney()) {
            suggestions.push_back(&seat); // Push const Seat*
        }
    }
    // Optionally sort suggestions by price
    std::sort(suggestions.begin(), suggestions.end(), [](const Seat* a, const Seat* b) {
        return a->getPrice() < b->getPrice();
    });
    return suggestions;
}
