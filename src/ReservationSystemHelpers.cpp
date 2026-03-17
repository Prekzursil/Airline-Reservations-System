// cppcheck-suppress-file missingIncludeSystem
#include "ReservationSystemHelpers.h"
#include <format>

namespace reservation_system_helpers {
namespace {
using SeedValue = unsigned long long;

constexpr int kMinimumAutoAge = 18;
constexpr int kMaximumAutoAge = 80;
constexpr int kMinimumAutoMoneyCents = 10000;
constexpr int kMaximumAutoMoneyCents = 200000;

SeedValue buildDeterministicSeed(const std::string& value, SeedValue salt) {
    SeedValue hash = 1469598103934665603ULL ^ salt;
    for (const char ch : value) {
        hash ^= static_cast<SeedValue>(static_cast<unsigned char>(ch));
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::string buildDeterministicAutoName(
    const std::vector<std::string>& firstNames,
    const std::string& customerId,
    SeedValue seed
) {
    const auto nameIndex = seed % firstNames.size();
    return firstNames[nameIndex] + "_" + customerId;
}

int buildDeterministicAutoAge(SeedValue seed) {
    const int ageRange = kMaximumAutoAge - kMinimumAutoAge + 1;
    return kMinimumAutoAge + static_cast<int>(seed % static_cast<SeedValue>(ageRange));
}

double buildDeterministicAutoMoney(SeedValue seed) {
    const int moneyRange = kMaximumAutoMoneyCents - kMinimumAutoMoneyCents + 1;
    const int moneyCents = kMinimumAutoMoneyCents + static_cast<int>(seed % static_cast<SeedValue>(moneyRange));
    return static_cast<double>(moneyCents) / 100.0;
}
} // namespace

bool isAffirmative(char value) {
    return value == 'y' || value == 'Y';
}

std::string readNonEmptyLine(std::istream& in, std::ostream& out, const std::string& prompt) {
    std::string value;
    out << prompt;
    if (!std::getline(in, value)) {
        throw InputExhaustedError();
    }
    if (!value.empty()) { return value; }
    out << "Input cannot be empty. Please try again: ";
    if (!std::getline(in, value)) { throw InputExhaustedError(); }
    return value;
}

AutoCustomerData generateAutoCustomerData(const std::string& newId) {
    static const std::vector<std::string> firstNames = {
        "AutoPat",
        "RoboUser",
        "GenClient",
        "SysPerson",
        "BotPassenger",
    };
    const SeedValue seed = buildDeterministicSeed(newId, 0x9E3779B97F4A7C15ULL);
    const std::string name = buildDeterministicAutoName(firstNames, newId, seed);
    const int age = buildDeterministicAutoAge(seed >> 8U);
    const double money = buildDeterministicAutoMoney(seed >> 16U);
    return {name, age, money};
}

AutoCustomerData generateApiAutoCustomerData(const std::string& newId) {
    static const std::vector<std::string> firstNames = {
        "ApiPat",
        "WebServiceUser",
        "JsonGenClient",
        "SystemPerson",
        "BackendBot",
    };
    const SeedValue seed = buildDeterministicSeed(newId, 0xD1B54A32D192ED03ULL);
    const std::string name = buildDeterministicAutoName(firstNames, newId, seed);
    const int age = buildDeterministicAutoAge(seed >> 8U);
    const double money = buildDeterministicAutoMoney(seed >> 16U);
    return {name, age, money};
}

std::string formatCustomerId(int counter) {
    std::string numericPart = std::to_string(counter);
    while (numericPart.size() < 4U) {
        numericPart.insert(numericPart.begin(), '0');
    }
    return "CUST" + numericPart;
}

std::string formatMoneyAmount(double amount) {
    const auto cents = static_cast<long long>(amount * 100.0 + (amount >= 0.0 ? 0.5 : -0.5));
    const long long dollars = cents / 100;
    const long long remainder = cents >= 0 ? cents % 100 : -(cents % 100);
    return std::format("{}.{:02d}", dollars, remainder);
}

void printAvailableFlights(std::ostream& out, const std::vector<Airplane>& availableAirplanes) {
    out << "\nAvailable Flights:" << std::endl;
    for (size_t i = 0; i < availableAirplanes.size(); ++i) {
        out << i + 1 << ". Flight " << availableAirplanes[i].getFlightNumber() << std::endl;
    }
}

void printSeatSuggestions(std::ostream& out, const std::vector<const Seat*>& suggestions) {
    if (suggestions.empty()) { return; }
    out << "Perhaps one of these seats instead?" << std::endl;
    for (const Seat* suggestedSeat : suggestions) {
        if (suggestedSeat == nullptr) continue;
        out << "- " << suggestedSeat->getSeatId() << " (" << suggestedSeat->getSeatClassString() << ") costs $" << suggestedSeat->getPrice() << std::endl;
    } }

bool hasBookSeatPrerequisites(std::ostream& out, const std::vector<Airplane>& availableAirplanes, const std::size_t customerCount) {
    if (availableAirplanes.empty()) { out << "No flights available to book." << std::endl; return false; }
    if (customerCount == 0U) { out << "No customers in the system. Please add a customer first." << std::endl; return false; }
    return true; }

bool tryPrepareSeatForBooking(std::ostream& out, Airplane& airplane, const Customer& customer, const std::string& seatIdToBook, Seat*& selectedSeat) {
    selectedSeat = airplane.findSeat(seatIdToBook);
    if (selectedSeat == nullptr) {
        out << "Seat " << seatIdToBook << " does not exist on this flight." << std::endl;
        return false;
    }
    if (selectedSeat->getIsBooked()) {
        out << "Seat " << seatIdToBook << " is already booked." << std::endl;
        return false;
    }

    const double seatPrice = selectedSeat->getPrice();
    out << "Seat " << seatIdToBook << " (" << selectedSeat->getSeatClassString() << ") costs $" << seatPrice << std::endl;

    if (customer.getMoney() < seatPrice) {
        out << "Insufficient funds. You have $" << customer.getMoney() << ", seat costs $" << seatPrice << "." << std::endl;
        const std::vector<const Seat*> suggestions = airplane.suggestLowerPriceSeats(&customer, customer.getMoney());
        printSeatSuggestions(out, suggestions);
        return false;
    }

    return true;
}
} // namespace reservation_system_helpers
