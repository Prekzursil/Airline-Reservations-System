// cppcheck-suppress-file missingIncludeSystem
#include "ReservationSystem.h"
#include "ReservationSystemHelpers.h"
#include <array>
#include <iostream>

static int g_customerIdCounter = 1; // Global static for resettable ID generation

namespace rsh = reservation_system_helpers;

ReservationSystem::ReservationSystem(std::istream& cin_ref, std::ostream& cout_ref)
    // cppcheck-suppress misra-c2012-12.3
    : m_cin_ptr(&cin_ref), m_cout_ptr(&cout_ref) {
    initializeSystem();
}

ReservationSystem::~ReservationSystem() = default;

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
    const int nextCounter = g_customerIdCounter;
    ++g_customerIdCounter;
    return rsh::formatCustomerId(nextCounter);
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
        if ((*m_cin_ptr) >> choice && choice >= minChoice && choice <= maxChoice) {
            m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n'); 
            return choice;
        }

        if (m_cin_ptr->eof()) {
            throw rsh::InputExhaustedError();
        }

        (*m_cout_ptr) << "Invalid choice. Please enter a number between " << minChoice << " and " << maxChoice << "." << std::endl;
        m_cin_ptr->clear();
        m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    }
}

void ReservationSystem::run() {
    while (true) {
        try {
            displayMainMenu();
            const int choice = getMenuChoice(0, 7);
            executeMenuChoice(choice);
            if (choice == 0) {
                return;
            }
        } catch (const rsh::InputExhaustedError&) {
            (*m_cout_ptr) << "Input stream exhausted. Exiting system." << std::endl;
            return;
        }
    }
}

void ReservationSystem::executeMenuChoice(int choice) {
    using MenuAction = void (ReservationSystem::*)();
    // cppcheck-suppress misra-c2012-12.3
    static const std::array<MenuAction, 7> kActions = {
        &ReservationSystem::handleAddCustomer,
        &ReservationSystem::handleBookSeat,
        &ReservationSystem::handleViewFlightDetails,
        &ReservationSystem::handleSearchCustomer,
        &ReservationSystem::handleCancelBooking,
        &ReservationSystem::handleSwapSeats,
        &ReservationSystem::handleAdminMenu,
    };
    constexpr auto kActionCount = static_cast<int>(kActions.size());

    if (choice == 0) {
        (*m_cout_ptr) << "Exiting system. Goodbye!" << std::endl;
        return;
    }

    if (choice >= 1 && choice <= kActionCount) {
        (this->*kActions[static_cast<size_t>(choice - 1)])();
        return;
    }

    (*m_cout_ptr) << "Invalid choice. Please try again." << std::endl;
}

void ReservationSystem::handleAddCustomer() {
    (*m_cout_ptr) << "\n--- Add New Customer ---" << std::endl;
    const char choice = getValidatedInput<char>("Add customer manually (m) or automatically (a)? ");
    const std::string newId = generateUniqueCustomerId();

    std::string name;
    int age = 0;
    double money = 0.0;

    if (choice == 'a' || choice == 'A') {
        const rsh::AutoCustomerData generated = rsh::generateAutoCustomerData(newId);
        name = generated.name;
        age = generated.age;
        money = generated.money;

        (*m_cout_ptr) << "Generated Customer:" << std::endl;
        (*m_cout_ptr) << "  Name: " << name << std::endl;
        (*m_cout_ptr) << "  Age: " << age << std::endl;
        (*m_cout_ptr) << "  Money: $" << rsh::formatMoneyAmount(money) << std::endl;
    } else if (choice == 'm' || choice == 'M') {
        name = rsh::readNonEmptyLine(*m_cin_ptr, *m_cout_ptr, "Enter customer name: ");
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
    if (!rsh::hasBookSeatPrerequisites(*m_cout_ptr, airplanes, customers)) {
        return;
    }

    const std::string custId = getValidatedInput<std::string>("Enter Customer ID: ");
    const Customer* customer = findCustomerById(custId);
    if (customer == nullptr) {
        (*m_cout_ptr) << "Customer with ID " << custId << " not found." << std::endl;
        return;
    }

    rsh::printAvailableFlights(*m_cout_ptr, airplanes);
    const auto maxChoice = static_cast<int>(airplanes.size());
    const int flightChoice = getMenuChoice(1, maxChoice) - 1;
    Airplane& airplane = airplanes[static_cast<size_t>(flightChoice)];

    (*m_cout_ptr) << "Selected Flight: " << airplane.getFlightNumber() << std::endl;

    const std::string seatIdToBook = getValidatedInput<std::string>("Enter Seat ID to book (e.g., 1A): ");
    Seat* seat = nullptr;
    if (!rsh::tryPrepareSeatForBooking(*m_cout_ptr, airplane, *customer, seatIdToBook, seat)) {
        return;
    }

    if (const auto confirm = getValidatedInput<char>("Confirm booking? (y/n): "); !rsh::isAffirmative(confirm)) {
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
    (*m_cout_ptr) << "Booking successful! Booking ID: " << booking->getBookingId() << std::endl;
}

void ReservationSystem::handleViewFlightDetails() {
    (*m_cout_ptr) << "\n--- View Flight Details ---" << std::endl;
    if (airplanes.empty()) {
        (*m_cout_ptr) << "No flights available to view." << std::endl;
        return;
    }
    rsh::printAvailableFlights(*m_cout_ptr, airplanes);
    const auto maxChoice = static_cast<int>(airplanes.size());
    const int flightChoice = getMenuChoice(1, maxChoice) - 1;
    const auto& airplane = airplanes[static_cast<size_t>(flightChoice)];

    airplane.displaySeatingMap();
    airplane.displayAvailableSeats();
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
        (*m_cout_ptr) << "Bookings for " << customer->getName() << ":" << std::endl;
        bool foundBookings = false;
        for(const auto& booking : bookings) {
            if (booking.getCustomerId() == customer->getPersonId() && booking.getStatus() == BookingStatus::CONFIRMED) {
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
    if (const auto confirm = getValidatedInput<char>("Confirm cancellation? (y/n): "); !rsh::isAffirmative(confirm)) {
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
    Booking* booking1 = promptConfirmedBooking(
        "Enter Booking ID of the first customer: ",
        "First booking ID"
    );
    if (booking1 == nullptr) {
        return;
    }

    Booking* booking2 = promptConfirmedBooking(
        "Enter Booking ID of the second customer: ",
        "Second booking ID"
    );
    if (booking2 == nullptr) {
        return;
    }

    if (!validateSwapPair(*booking1, *booking2)) {
        return;
    }

    (*m_cout_ptr) << "\nBooking 1 Details:" << std::endl;
    const Customer* customer1 = findCustomerById(booking1->getCustomerId());
    (void)customer1;

    (*m_cout_ptr) << "\nBooking 2 Details:" << std::endl;
    const Customer* customer2 = findCustomerById(booking2->getCustomerId());
    (void)customer2;

    const char confirm = getValidatedInput<char>("\nConfirm swap of these two seats? (y/n): ");
    if (!rsh::isAffirmative(confirm)) {
        (*m_cout_ptr) << "Seat swap cancelled by user." << std::endl;
        return;
    }

    const std::string firstSeatId = booking1->getSeatId();
    const std::string secondSeatId = booking2->getSeatId();
    booking1->setSeatId(secondSeatId);
    booking2->setSeatId(firstSeatId);

    (*m_cout_ptr) << "\nSeat swap completed successfully!" << std::endl;
    (*m_cout_ptr) << "New Booking Details:" << std::endl;
    (*m_cout_ptr) << "--- For Booking ID " << booking1->getBookingId() << " (Customer " << booking1->getCustomerId() << "):" << std::endl;
    (*m_cout_ptr) << "--- For Booking ID " << booking2->getBookingId() << " (Customer " << booking2->getCustomerId() << "):" << std::endl;
}

Booking* ReservationSystem::promptConfirmedBooking(const std::string& prompt, const std::string& failurePrefix) {
    const std::string bookingId = getValidatedInput<std::string>(prompt);
    Booking* booking = findBookingById(bookingId);
    if (booking == nullptr || booking->getStatus() != BookingStatus::CONFIRMED) {
        (*m_cout_ptr) << failurePrefix << " not found or not confirmed." << std::endl;
        return nullptr;
    }
    return booking;
}

bool ReservationSystem::validateSwapPair(const Booking& firstBooking, const Booking& secondBooking) const {
    if (firstBooking.getBookingId() == secondBooking.getBookingId()) {
        (*m_cout_ptr) << "Cannot swap a booking with itself." << std::endl;
        return false;
    }

    if (firstBooking.getFlightNumber() != secondBooking.getFlightNumber()) {
        (*m_cout_ptr) << "Seat swaps are currently only supported for bookings on the same flight." << std::endl;
        (*m_cout_ptr) << "Booking 1 is for flight " << firstBooking.getFlightNumber()
                      << ", Booking 2 is for flight " << secondBooking.getFlightNumber() << std::endl;
        return false;
    }

    return true;
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
        case 0:
            return;
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
        const rsh::AutoCustomerData generated = rsh::generateApiAutoCustomerData(newId);
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

    (void)customer->chargeMoney(seat->getPrice());
    (void)airplane->bookSpecificSeat(seat->getSeatId());

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
