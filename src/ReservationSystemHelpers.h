// cppcheck-suppress-file missingIncludeSystem
#ifndef RESERVATIONSYSTEMHELPERS_H
#define RESERVATIONSYSTEMHELPERS_H

#include "Airplane.h"
#include "Customer.h"
#include "Seat.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace reservation_system_helpers {

class InputExhaustedError : public std::runtime_error {
public:
    InputExhaustedError() : std::runtime_error("Input stream exhausted") {}
};

struct AutoCustomerData {
    std::string name;
    int age;
    double money;
};

bool isAffirmative(char value);
std::string readNonEmptyLine(std::istream& in, std::ostream& out, const std::string& prompt);
AutoCustomerData generateAutoCustomerData(const std::string& newId);
AutoCustomerData generateApiAutoCustomerData(const std::string& newId);
std::string formatCustomerId(int counter);
std::string formatMoneyAmount(double amount);
void printAvailableFlights(std::ostream& out, const std::vector<Airplane>& availableAirplanes);
void printSeatSuggestions(std::ostream& out, const std::vector<const Seat*>& suggestions);
bool hasBookSeatPrerequisites(
    std::ostream& out,
    const std::vector<Airplane>& availableAirplanes,
    const std::vector<Customer>& knownCustomers
);
bool tryPrepareSeatForBooking(
    std::ostream& out,
    Airplane& airplane,
    const Customer& customer,
    const std::string& seatIdToBook,
    Seat*& selectedSeat
);

} // namespace reservation_system_helpers

#endif // RESERVATIONSYSTEMHELPERS_H
