// cppcheck-suppress-file missingIncludeSystem
#include "Airplane.h"
#include <algorithm>
#include <format>
#include <ranges>

namespace {
std::string buildSeatId(const int rowNumber, const int seatOffset) {
    return std::format("{}{}", rowNumber, static_cast<char>('A' + seatOffset));
}

char seatDisplayChar(const Seat& seat) {
    if (seat.getIsBooked()) {
        return 'X';
    }
    return seat.getSeatClass() == SeatClass::BUSINESS ? 'B' : 'E';
}

void applyAirplaneLayout(int rows, int seatsPerRow, int& totalRowsOut, int& seatsPerRowOut, int& bookedSeatsOut) {
    totalRowsOut = rows > 0 ? rows : 1;
    seatsPerRowOut = seatsPerRow > 0 ? seatsPerRow : 1;
    bookedSeatsOut = 0;
}
} // namespace

Airplane::Airplane(const std::string& flightNum, int rows, int sPerRow)
    : flightNumber(flightNum) {
    applyAirplaneLayout(rows, sPerRow, totalRows, seatsPerRow, bookedSeatsCount);
    initializeSeats();
}

Airplane::~Airplane() = default;

void Airplane::initializeSeats() {
    seats.clear();
    constexpr double kEconomyBasePrice = 50.0;
    constexpr double kBusinessBasePrice = 100.0;

    int businessRows = static_cast<int>(totalRows * 0.2);
    if (businessRows == 0 && totalRows > 0) {
        businessRows = 1;
    }

    for (int i = 1; i <= totalRows; ++i) {
        for (int j = 0; j < seatsPerRow; ++j) {
            const std::string id = buildSeatId(i, j);
            const SeatClass seatClass = (i <= businessRows) ? SeatClass::BUSINESS : SeatClass::ECONOMY;
            const double price = (seatClass == SeatClass::BUSINESS) ? kBusinessBasePrice : kEconomyBasePrice;
            seats.emplace_back(id, seatClass, price);
        }
    }
}

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

Seat* Airplane::findSeat(const std::string& seatId) {
    for (auto& seat : seats) {
        if (seat.getSeatId() == seatId) {
            return &seat;
        }
    }
    return nullptr;
}

bool Airplane::bookSpecificSeat(const std::string& seatId) {
    if (Seat* seatToBook = findSeat(seatId); seatToBook && !seatToBook->getIsBooked() && seatToBook->bookSeat()) {
        ++bookedSeatsCount;
        return true;
    }
    return false;
}

bool Airplane::unbookSpecificSeat(const std::string& seatId) {
    if (Seat* seatToUnbook = findSeat(seatId); seatToUnbook && seatToUnbook->getIsBooked() && seatToUnbook->unbookSeat()) {
        --bookedSeatsCount;
        return true;
    }
    return false;
}

void Airplane::displaySeatingMap() const {
    std::cout << "\n--- Seating Map for Flight " << flightNumber << " ---" << std::endl;
    std::cout << "  ";
    for (int j = 0; j < seatsPerRow; ++j) {
        std::cout << static_cast<char>('A' + j) << ' ';
    }
    std::cout << std::endl;

    size_t seatIndex = 0;
    for (int i = 1; i <= totalRows; ++i) {
        std::cout << i << (i < 10 ? "  " : " ");
        for (int j = 0; j < seatsPerRow; ++j) {
            if (seatIndex < seats.size()) {
                const auto& seat = seats[seatIndex];
                ++seatIndex;
                const char displayChar = seatDisplayChar(seat);
                std::cout << displayChar << ' ';
            } else {
                std::cout << "  ";
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

std::vector<const Seat*> Airplane::getAvailableSeatsByClass(SeatClass sc) const {
    std::vector<const Seat*> available;
    for (const auto& seat : seats)
        if (!seat.getIsBooked() && seat.getSeatClass() == sc)
            available.push_back(&seat);
    return available; }
std::vector<const Seat*> Airplane::suggestLowerPriceSeats(const Customer* customer, double maxPrice) const {
    std::vector<const Seat*> suggestions;
    if (!customer) return suggestions;

    for (const auto& seat : seats)
        if (!seat.getIsBooked() && seat.getPrice() <= maxPrice && seat.getPrice() <= customer->getMoney())
            suggestions.push_back(&seat);
    std::ranges::sort(suggestions, std::ranges::less {}, [](const Seat* seat) { return seat->getPrice(); });
    return suggestions; }
