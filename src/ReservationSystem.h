#ifndef RESERVATIONSYSTEM_H
#define RESERVATIONSYSTEM_H

#include "Airplane.h"
#include "Customer.h"
#include "Booking.h"
#include <vector>
#include <string>
#include <limits> // Required for std::numeric_limits
#include <iostream> // For std::istream, std::ostream

class ReservationSystem {
private:
    std::vector<Airplane> airplanes;
    std::vector<Customer> customers;
    std::vector<Booking> bookings;

    // I/O Stream Pointers - for testing
    std::istream* m_cin_ptr;
    std::ostream* m_cout_ptr;

public: // Made public for testing - consider refactoring for better testability
    // Helper methods for internal logic
    Customer* findCustomerById(const std::string& customerId);
    Airplane* findAirplaneByFlightNumber(const std::string& flightNumber);
    Booking* findBookingById(const std::string& bookingId);
    std::string generateUniqueCustomerId(); // Made public for testing
    static void resetCustomerIdCounterForTest(); // For predictable IDs in tests

private: // Back to private for other members
    // std::string generateUniqueFlightNumber(); // If airplanes are dynamically added

    // Menu interaction methods
    void displayMainMenu() const;
    void handleAddCustomer();
    void handleBookSeat();
    void handleViewFlightDetails(); // Includes seating map, available seats
    void handleSearchCustomer();
    void handleCancelBooking();
    void handleSwapSeats(); // More complex, might need careful thought
    void handleAdminMenu(); // Optional: for adding airplanes, etc.
    void handleAddAirplane(); // Called from admin menu

    // Utility to get validated input
    template<typename T>
    T getValidatedInput(const std::string& prompt); // Will use m_cin_ptr, m_cout_ptr
    int getMenuChoice(int minChoice, int maxChoice); // Will use m_cin_ptr, m_cout_ptr


public:
    ReservationSystem(std::istream& cin_ref = std::cin, std::ostream& cout_ref = std::cout); // Modified constructor
    ~ReservationSystem();

    void initializeSystem(); // To add some default airplanes/customers for testing
    void run(); // Main application loop

    // For testing:
    void setInputStreamForTest(std::istream& inputStream);
    void setOutputStreamForTest(std::ostream& outputStream);
    void resetSystemForTest(); // Clears vectors
    const std::vector<Customer>& getCustomersForTest() const { return customers; }
    const std::vector<Airplane>& getAirplanesForTest() const { return airplanes; }
    const std::vector<Booking>& getBookingsForTest() const { return bookings; }

    // Methods for API interaction (programmatic, no console I/O)
    Customer* addCustomerInternal(const std::string& name, int age, double money, bool autoGenerate);
    Booking* createBookingInternal(const std::string& customerId, const std::string& flightNumber, const std::string& seatId, std::string& errorMessage);
    bool cancelBookingInternal(const std::string& bookingId, std::string& errorMessage);
    bool swapSeatsInternal(const std::string& bookingId1, const std::string& bookingId2, std::string& errorMessage);
};

// Template function definition needs to be in the header or an included .tpp/.ipp file
template<typename T>
T ReservationSystem::getValidatedInput(const std::string& prompt) {
    T value;
    while (true) {
        *m_cout_ptr << prompt;
        *m_cin_ptr >> value;
        if (m_cin_ptr->good()) {
            m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // Clear buffer
            return value;
        } else {
            *m_cout_ptr << "Invalid input. Please try again." << std::endl;
            m_cin_ptr->clear();
            m_cin_ptr->ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        }
    }
}


#endif // RESERVATIONSYSTEM_H
