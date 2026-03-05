#include "ReservationSystem.h"
#include <iostream>
#include <sstream>   // For ID generation

static int g_customerIdCounter = 1; // Global static for resettable ID generation

namespace {
using SeedValue = unsigned long long;

bool isAffirmative(char value) {
    return value == 'y' || value == 'Y';
}

struct AutoCustomerData {
    std::string name;
    int age;
    double money;
};

std::string readNonEmptyLine(std::istream& in, std::ostream& out, const std::string& prompt) {
    std::string value;
    out << prompt;
    std::getline(in, value);
    if (!value.empty()) {
        return value;
    }
    out << "Input cannot be empty. Please try again: ";
    std::getline(in, value);
    return value;
}

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
    std::string numeric_part = std::to_string(counter);
    while (numeric_part.size() < 4U) {
        numeric_part.insert(numeric_part.begin(), '0');
    }
    return "CUST" + numeric_part;
}

std::string formatMoneyAmount(double amount) {
    const long long cents = static_cast<long long>(amount * 100.0 + (amount >= 0.0 ? 0.5 : -0.5));
    const long long dollars = cents / 100;
    const long long remainder = cents >= 0 ? cents % 100 : -(cents % 100);

    std::ostringstream out;
    out << dollars << '.';
    if (remainder < 10) {
        out << '0';
    }
    out << remainder;
    return out.str();
}

void printAvailableFlights(std::ostream& out, const std::vector<Airplane>& availableAirplanes) {
    out << "\nAvailable Flights:" << std::endl;
    for (size_t i = 0; i < availableAirplanes.size(); ++i) {
        out << i + 1 << ". Flight " << availableAirplanes[i].getFlightNumber() << std::endl;
    }
}

void printSeatSuggestions(std::ostream& out, const std::vector<const Seat*>& suggestions) {
    if (suggestions.empty()) {
        return;
    }
    out << "Perhaps one of these seats instead?" << std::endl;
    for (const Seat* suggestedSeat : suggestions) {
        if (suggestedSeat == nullptr) {
            continue;
        }
        out << "- " << suggestedSeat->getSeatId() << " (" << suggestedSeat->getSeatClassString()
            << ") costs $" << suggestedSeat->getPrice() << std::endl;
    }
}

bool hasBookSeatPrerequisites(
    std::ostream& out,
    const std::vector<Airplane>& availableAirplanes,
    const std::vector<Customer>& knownCustomers
) {
    if (availableAirplanes.empty()) {
        out << "No flights available to book." << std::endl;
        return false;
    }
    if (knownCustomers.empty()) {
        out << "No customers in the system. Please add a customer first." << std::endl;
        return false;
    }
    return true;
}

bool tryPrepareSeatForBooking(
    std::ostream& out,
    Airplane& airplane,
    const Customer& customer,
    const std::string& seatIdToBook,
    Seat*& selectedSeat
) {
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
} // namespace

// Constructor
ReservationSystem::ReservationSystem(std::istream& cin_ref, std::ostream& cout_ref)
    : m_cin_ptr(&cin_ref), m_cout_ptr(&cout_ref) {
    // (*m_cout_ptr) << "ReservationSystem constructor called." << std::endl; // Optional
    initializeSystem(); // Populate with some initial data
}

// Destructor
ReservationSystem::~ReservationSystem() {
    // (*m_cout_ptr) << "ReservationSystem destructor called." << std::endl; // Optional
}

void ReservationSystem::setInputStreamForTest(std::istream& inputStream) {
    m_cin_ptr = &inputStream;
}

void ReservationSystem::setOutputStreamForTest(std::ostream& outputStream) {
    m_cout_ptr = &outputStream;
}

void ReservationSystem::resetSystemForTest() {
    airplanes.clear();
    customers.clear();
    bookings.clear();
    resetCustomerIdCounterForTest(); 
}

void ReservationSystem::resetCustomerIdCounterForTest() {
    g_customerIdCounter = 1;
}

void ReservationSystem::initializeSystem() {
    airplanes.emplace_back("FL101", 15, 6); 
    airplanes.emplace_back("FL202", 20, 6); 

    customers.emplace_back("Alice Wonderland", 30, generateUniqueCustomerId(), 1500.0);
    customers.emplace_back("Bob The Builder", 45, generateUniqueCustomerId(), 800.0);
    
    (*m_cout_ptr) << "System initialized with default airplanes and customers." << std::endl;
}

std::string ReservationSystem::generateUniqueCustomerId() {
    const int nextCounter = g_customerIdCounter++;
    return formatCustomerId(nextCounter);
}

Customer* ReservationSystem::findCustomerById(const std::string& customerId) {
    for (auto& customer : customers) {
        if (customer.getPersonId() == customerId) {
            return &customer;
        }
    }
    return nullptr;
}

Airplane* ReservationSystem::findAirplaneByFlightNumber(const std::string& flightNumber) {
    for (auto& airplane : airplanes) {
        if (airplane.getFlightNumber() == flightNumber) {
            return &airplane;
        }
    }
    return nullptr;
}

Booking* ReservationSystem::findBookingById(const std::string& bookingId) {
    for (auto& booking : bookings) {
        if (booking.getBookingId() == bookingId) {
            return &booking;
        }
    }
    return nullptr;
}

void ReservationSystem::displayMainMenu() const {
    (*m_cout_ptr) << "\n===== Airline Reservation System Menu =====" << std::endl;
    (*m_cout_ptr) << "1. Add New Customer" << std::endl;
    (*m_cout_ptr) << "2. Book a Seat" << std::endl;
    (*m_cout_ptr) << "3. View Flight Details (Seating Map, Available Seats)" << std::endl;
    (*m_cout_ptr) << "4. Search Customer" << std::endl;
    (*m_cout_ptr) << "5. Cancel Booking" << std::endl;
    (*m_cout_ptr) << "6. Swap Seats" << std::endl;
    (*m_cout_ptr) << "7. Admin Options" << std::endl;
    (*m_cout_ptr) << "0. Exit" << std::endl;
    (*m_cout_ptr) << "=========================================" << std::endl;
}

int ReservationSystem::getMenuChoice(int minChoice, int maxChoice) {
    int choice;
    while (true) {
        (*m_cout_ptr) << "Enter your choice: ";
        (*m_cin_ptr) >> choice;
        if (m_cin_ptr->good() && choice >= minChoice && choice <= maxChoice) {
            m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n'); 
            return choice;
        } else {
            (*m_cout_ptr) << "Invalid choice. Please enter a number between " << minChoice << " and " << maxChoice << "." << std::endl;
            m_cin_ptr->clear();
            m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        }
    }
}

void ReservationSystem::run() {
    int choice;
    do {
        displayMainMenu();
        choice = getMenuChoice(0, 7);

        switch (choice) {
            case 1: handleAddCustomer(); break;
            case 2: handleBookSeat(); break;
            case 3: handleViewFlightDetails(); break;
            case 4: handleSearchCustomer(); break;
            case 5: handleCancelBooking(); break;
            case 6: handleSwapSeats(); break;
            case 7: handleAdminMenu(); break;
            case 0: (*m_cout_ptr) << "Exiting system. Goodbye!" << std::endl; break;
            default: (*m_cout_ptr) << "Invalid choice. Please try again." << std::endl; break;
        }
    } while (choice != 0);
}

void ReservationSystem::handleAddCustomer() {
    (*m_cout_ptr) << "\n--- Add New Customer ---" << std::endl;
    const char choice = getValidatedInput<char>("Add customer manually (m) or automatically (a)? ");
    const std::string newId = generateUniqueCustomerId();

    std::string name;
    int age = 0;
    double money = 0.0;

    if (choice == 'a' || choice == 'A') {
        const AutoCustomerData generated = generateAutoCustomerData(newId);
        name = generated.name;
        age = generated.age;
        money = generated.money;

        (*m_cout_ptr) << "Generated Customer:" << std::endl;
        (*m_cout_ptr) << "  Name: " << name << std::endl;
        (*m_cout_ptr) << "  Age: " << age << std::endl;
        (*m_cout_ptr) << "  Money: $" << formatMoneyAmount(money) << std::endl;
    } else if (choice == 'm' || choice == 'M') {
        name = readNonEmptyLine(*m_cin_ptr, *m_cout_ptr, "Enter customer name: ");
        age = getValidatedInput<int>("Enter customer age: ");
        money = getValidatedInput<double>("Enter initial money: ");
    } else {
        (*m_cout_ptr) << "Invalid choice. Aborting customer creation." << std::endl;
        return;
    }
    
    customers.emplace_back(name, age, newId, money);
    (*m_cout_ptr) << "Customer " << name << " with ID " << newId << " added successfully." << std::endl;
}

void ReservationSystem::handleBookSeat() {
    (*m_cout_ptr) << "\n--- Book a Seat ---" << std::endl;
    if (!hasBookSeatPrerequisites(*m_cout_ptr, airplanes, customers)) {
        return;
    }

    const std::string custId = getValidatedInput<std::string>("Enter Customer ID: ");
    const Customer* customer = findCustomerById(custId);
    if (customer == nullptr) {
        (*m_cout_ptr) << "Customer with ID " << custId << " not found." << std::endl;
        return;
    }
    // customer->displayDetails(); // Uses std::cout, need to pass m_cout_ptr or refactor

    printAvailableFlights(*m_cout_ptr, airplanes);
    const auto maxChoice = static_cast<int>(airplanes.size());
    const int flightChoice = getMenuChoice(1, maxChoice) - 1;
    Airplane& airplane = airplanes[static_cast<size_t>(flightChoice)];
    
    (*m_cout_ptr) << "Selected Flight: " << airplane.getFlightNumber() << std::endl;
    // airplane->displaySeatingMap(); // Uses std::cout
    // airplane->displayAvailableSeats(); // Uses std::cout

    const std::string seatIdToBook = getValidatedInput<std::string>("Enter Seat ID to book (e.g., 1A): ");
    Seat* seat = nullptr;
    if (!tryPrepareSeatForBooking(*m_cout_ptr, airplane, *customer, seatIdToBook, seat)) {
        return;
    }

    if (const auto confirm = getValidatedInput<char>("Confirm booking? (y/n): "); !isAffirmative(confirm)) {
        (*m_cout_ptr) << "Booking cancelled by user." << std::endl;
        return;
    }

    std::string bookingStatusMessage;
    const auto* booking = createBookingInternal(
        customer->getPersonId(),
        airplane.getFlightNumber(),
        seat->getSeatId(),
        bookingStatusMessage
    );
    if (!booking) {
        (*m_cout_ptr) << bookingStatusMessage << std::endl;
        return;
    }

    (*m_cout_ptr) << "Booking successful! Booking ID: " << booking->getBookingId() << std::endl;
}

void ReservationSystem::handleViewFlightDetails() {
    (*m_cout_ptr) << "\n--- View Flight Details ---" << std::endl;
    if (airplanes.empty()) {
        (*m_cout_ptr) << "No flights available to view." << std::endl;
        return;
    }
    printAvailableFlights(*m_cout_ptr, airplanes);
    const auto maxChoice = static_cast<int>(airplanes.size());
    int flightChoice = getMenuChoice(1, maxChoice) - 1;
    const auto* airplane = &airplanes[static_cast<size_t>(flightChoice)];
    (void)airplane; // Mark as used

    // airplane->displaySeatingMap(); 
    // airplane->displayAvailableSeats(); 
}

void ReservationSystem::handleSearchCustomer() {
    (*m_cout_ptr) << "\n--- Search Customer ---" << std::endl;
    if (customers.empty()){
        (*m_cout_ptr) << "No customers in the system." << std::endl;
        return;
    }
    std::string id = getValidatedInput<std::string>("Enter Customer ID to search: ");
    Customer* customer = findCustomerById(id);
    if (customer) {
        // customer->displayDetails(); 
        (*m_cout_ptr) << "Bookings for " << customer->getName() << ":" << std::endl;
        bool foundBookings = false;
        for(const auto& booking : bookings) {
            if (booking.getCustomerId() == customer->getPersonId() && booking.getStatus() == BookingStatus::CONFIRMED) {
                // booking.displayBookingDetails(); 
                foundBookings = true;
            }
        }
        if (!foundBookings) {
            (*m_cout_ptr) << "No active bookings found for this customer." << std::endl;
        }
    } else {
        (*m_cout_ptr) << "Customer with ID " << id << " not found." << std::endl;
    }
}

void ReservationSystem::handleCancelBooking() {
    (*m_cout_ptr) << "\n--- Cancel Booking ---" << std::endl;
    if (bookings.empty()) {
        (*m_cout_ptr) << "No bookings in the system to cancel." << std::endl;
        return;
    }
    std::string bookingIdToCancel = getValidatedInput<std::string>("Enter Booking ID to cancel: ");
    const auto* booking = findBookingById(bookingIdToCancel);

    if (!booking) {
        (*m_cout_ptr) << "Booking with ID " << bookingIdToCancel << " not found." << std::endl;
        return;
    }
    if (booking->getStatus() == BookingStatus::CANCELLED) {
        (*m_cout_ptr) << "Booking " << bookingIdToCancel << " is already cancelled." << std::endl;
        return;
    }
    // booking->displayBookingDetails(); 
    if (const auto confirm = getValidatedInput<char>("Confirm cancellation? (y/n): "); !isAffirmative(confirm)) {
        (*m_cout_ptr) << "Cancellation aborted by user." << std::endl;
        return;
    }

    std::string cancelStatusMessage;
    if (const auto cancelled = cancelBookingInternal(bookingIdToCancel, cancelStatusMessage); cancelled) {
        (*m_cout_ptr) << cancelStatusMessage << std::endl;
        return;
    }

    (*m_cout_ptr) << cancelStatusMessage << std::endl;
}

void ReservationSystem::handleSwapSeats() {
    (*m_cout_ptr) << "\n--- Swap Seats ---" << std::endl;
    if (bookings.size() < 2) {
        (*m_cout_ptr) << "Not enough bookings in the system to perform a swap." << std::endl;
        return;
    }
    std::string bookingId1_str = getValidatedInput<std::string>("Enter Booking ID of the first customer: ");
    Booking* booking1 = findBookingById(bookingId1_str);
    if (!booking1 || booking1->getStatus() != BookingStatus::CONFIRMED) {
        (*m_cout_ptr) << "First booking ID not found or not confirmed." << std::endl;
        return;
    }
    std::string bookingId2_str = getValidatedInput<std::string>("Enter Booking ID of the second customer: ");
    Booking* booking2 = findBookingById(bookingId2_str);
    if (!booking2 || booking2->getStatus() != BookingStatus::CONFIRMED) {
        (*m_cout_ptr) << "Second booking ID not found or not confirmed." << std::endl;
        return;
    }
    if (booking1->getBookingId() == booking2->getBookingId()) {
        (*m_cout_ptr) << "Cannot swap a booking with itself." << std::endl;
        return;
    }
    if (booking1->getFlightNumber() != booking2->getFlightNumber()) {
        (*m_cout_ptr) << "Seat swaps are currently only supported for bookings on the same flight." << std::endl;
        (*m_cout_ptr) << "Booking 1 is for flight " << booking1->getFlightNumber() 
                  << ", Booking 2 is for flight " << booking2->getFlightNumber() << std::endl;
        return;
    }
    (*m_cout_ptr) << "\nBooking 1 Details:" << std::endl;
    // booking1->displayBookingDetails(); 
    Customer* cust1 = findCustomerById(booking1->getCustomerId());
    (void)cust1; // Mark as used
    // if(cust1) cust1->displayDetails(); 

    (*m_cout_ptr) << "\nBooking 2 Details:" << std::endl;
    // booking2->displayBookingDetails(); 
    Customer* cust2 = findCustomerById(booking2->getCustomerId());
    (void)cust2; // Mark as used
    // if(cust2) cust2->displayDetails(); 

    const char confirm = getValidatedInput<char>("\nConfirm swap of these two seats? (y/n): ");
    if (isAffirmative(confirm)) {
        std::string seatId_cust1 = booking1->getSeatId();
        std::string seatId_cust2 = booking2->getSeatId();
        
        booking1->setSeatId(seatId_cust2);
        booking2->setSeatId(seatId_cust1);

        (*m_cout_ptr) << "\nSeat swap completed successfully!" << std::endl;
        (*m_cout_ptr) << "New Booking Details:" << std::endl;
        (*m_cout_ptr) << "--- For Booking ID " << booking1->getBookingId() << " (Customer " << booking1->getCustomerId() << "):" << std::endl;
        // booking1->displayBookingDetails(); 
        (*m_cout_ptr) << "--- For Booking ID " << booking2->getBookingId() << " (Customer " << booking2->getCustomerId() << "):" << std::endl;
        // booking2->displayBookingDetails(); 
    } else {
        (*m_cout_ptr) << "Seat swap cancelled by user." << std::endl;
    }
}

void ReservationSystem::handleAdminMenu() {
    (*m_cout_ptr) << "\n--- Admin Options ---" << std::endl;
    (*m_cout_ptr) << "1. Add New Airplane" << std::endl;
    (*m_cout_ptr) << "2. View All Customers" << std::endl;
    (*m_cout_ptr) << "3. View All Bookings" << std::endl;
    (*m_cout_ptr) << "0. Back to Main Menu" << std::endl;

    int choice = getMenuChoice(0, 3);
    switch (choice) {
        case 1: handleAddAirplane(); break;
        case 2:
            (*m_cout_ptr) << "\n--- All Customers ---" << std::endl;
            if (customers.empty()) (*m_cout_ptr) << "No customers in system." << std::endl;
            // for(const auto& cust : customers) cust.displayDetails(); 
            break;
        case 3:
            (*m_cout_ptr) << "\n--- All Bookings ---" << std::endl;
            if (bookings.empty()) (*m_cout_ptr) << "No bookings in system." << std::endl;
            // for(const auto& book : bookings) book.displayBookingDetails(); 
            break;
        case 0: return;
    }
}

void ReservationSystem::handleAddAirplane() {
    (*m_cout_ptr) << "\n--- Add New Airplane ---" << std::endl;
    std::string flightNum = getValidatedInput<std::string>("Enter flight number (e.g., FL303): ");
    if (findAirplaneByFlightNumber(flightNum)) {
        (*m_cout_ptr) << "An airplane with flight number " << flightNum << " already exists." << std::endl;
        return;
    }
    int rows = getValidatedInput<int>("Enter number of rows: ");
    int seatsPerRow = getValidatedInput<int>("Enter seats per row: ");

    airplanes.emplace_back(flightNum, rows, seatsPerRow);
    (*m_cout_ptr) << "Airplane " << flightNum << " added successfully." << std::endl;
}

// --- Methods for API interaction (programmatic, no console I/O) ---

Customer* ReservationSystem::addCustomerInternal(const std::string& name_param, int age, double money, bool autoGenerate) {
    std::string name = name_param;
    const std::string newId = generateUniqueCustomerId();

    if (autoGenerate) {
        const AutoCustomerData generated = generateApiAutoCustomerData(newId);
        name = generated.name;
        if (age <= 0) {
            age = generated.age;
        }
        if (money <= 0.0) {
            money = generated.money;
        }
    }
    
    customers.emplace_back(name, age, newId, money);
    return &customers.back(); // Return pointer to the newly added customer
}

Booking* ReservationSystem::createBookingInternal(const std::string& customerId, const std::string& flightNumber, const std::string& seatId, std::string& errorMessage) {
    Customer* customer = findCustomerById(customerId);
    if (!customer) {
        errorMessage = "Customer not found.";
        return nullptr;
    }

    Airplane* airplane = findAirplaneByFlightNumber(flightNumber);
    if (!airplane) {
        errorMessage = "Airplane not found.";
        return nullptr;
    }

    Seat* seat = airplane->findSeat(seatId);
    if (!seat) {
        errorMessage = "Seat not found on this flight.";
        return nullptr;
    }

    if (seat->getIsBooked()) {
        errorMessage = "Seat is already booked.";
        return nullptr;
    }

    if (customer->getMoney() < seat->getPrice()) {
        errorMessage = "Insufficient funds.";
        return nullptr;
    }

    if (!customer->chargeMoney(seat->getPrice())) {
        errorMessage = "Booking failed (could not charge customer - unexpected).";
        return nullptr;
    }

    if (!airplane->bookSpecificSeat(seat->getSeatId())) {
        customer->addMoney(seat->getPrice()); // Refund customer
        errorMessage = "Booking failed internally (airplane could not book seat).";
        return nullptr;
    }

    bookings.emplace_back(customer->getPersonId(), airplane->getFlightNumber(), seat->getSeatId());
    bookings.back().setStatus(BookingStatus::CONFIRMED);
    errorMessage = "Booking successful.";
    return &bookings.back(); // Return pointer to the new booking
}

bool ReservationSystem::cancelBookingInternal(const std::string& bookingId, std::string& errorMessage) {
    Booking* booking = findBookingById(bookingId);

    if (!booking) {
        errorMessage = "Booking with ID " + bookingId + " not found.";
        return false;
    }

    if (booking->getStatus() == BookingStatus::CANCELLED) {
        errorMessage = "Booking " + bookingId + " is already cancelled.";
        return false; // Or true, as it's already in the desired state for cancellation
    }
    
    // Logic from handleCancelBooking
    Customer* customer = findCustomerById(booking->getCustomerId());
    Airplane* airplane = findAirplaneByFlightNumber(booking->getFlightNumber());
    Seat* seat = airplane ? airplane->findSeat(booking->getSeatId()) : nullptr;

    if (customer && airplane && seat) {
        double refundAmount = seat->getPrice(); 
        customer->addMoney(refundAmount);
        airplane->unbookSpecificSeat(seat->getSeatId()); // This updates bookedSeatsCount in Airplane
        booking->setStatus(BookingStatus::CANCELLED);
        errorMessage = "Booking " + bookingId + " cancelled successfully. $" + std::to_string(refundAmount) + " refunded.";
        return true;
    } else {
        errorMessage = "Error: Could not find customer, airplane, or seat associated with this booking. Cancellation failed.";
        // This state should ideally not happen if data integrity is maintained.
        return false;
    }
}

bool ReservationSystem::swapSeatsInternal(const std::string& bookingId1_str, const std::string& bookingId2_str, std::string& errorMessage) {
    errorMessage.clear(); // Ensure errorMessage is in a good state

    Booking* booking1 = findBookingById(bookingId1_str);
    if (!booking1 || booking1->getStatus() != BookingStatus::CONFIRMED) {
        errorMessage = "First booking ID (" + bookingId1_str + ") not found or not confirmed.";
        return false;
    }

    Booking* booking2 = findBookingById(bookingId2_str);
    if (!booking2 || booking2->getStatus() != BookingStatus::CONFIRMED) {
        errorMessage = "Second booking ID (" + bookingId2_str + ") not found or not confirmed.";
        return false;
    }

    if (booking1->getBookingId() == booking2->getBookingId()) {
        errorMessage = "Cannot swap a booking with itself.";
        return false;
    }

    if (booking1->getFlightNumber() != booking2->getFlightNumber()) {
        // Simplified error message to reduce string operations, in case of issues.
        errorMessage = "Seat swaps only supported for bookings on the same flight."; 
        return false;
    }
    
    // Price difference handling is not implemented.
    // This assumes a direct swap of seat assignments.

    std::string tempSeatId1 = booking1->getSeatId(); // Store original seat of booking1
    
    std::string b2_original_seat = booking2->getSeatId();
    booking1->setSeatId(b2_original_seat); // Set booking1's seat to booking2's current/original seat
    booking2->setSeatId(tempSeatId1);      // Set booking2's seat to booking1's original seat

    errorMessage = "Seat swap successful. Booking " + bookingId1_str + " now has seat " + booking1->getSeatId() + 
                   " (was " + tempSeatId1 + "). Booking " + bookingId2_str + " now has seat " + booking2->getSeatId() +
                   " (was " + b2_original_seat + ").";
    return true;
}
