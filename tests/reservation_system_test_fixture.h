#pragma once
// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "auto_generated_customer_test_helpers.h"
#include "../src/ReservationSystem.h" 
#include "../src/Customer.h"
#include "../src/Airplane.h"
#include "../src/Booking.h"
#include <sstream> // For std::stringstream
#include <string>
#include <string_view>

class ReservationSystemTest : public ::testing::Test {
public:
    std::stringstream test_in;
    std::stringstream test_out;
    ReservationSystem rs;

    ReservationSystemTest() : rs(test_in, test_out) {} // Constructor to pass streams

    void SetUp() override {
        // Reset system state and streams before each test
        rs.resetSystemForTest(); // Clears vectors and resets ID counter
        rs.initializeSystem();   // Re-initialize with default data for a consistent start
        test_in.clear();
        test_in.str("");
        test_out.clear();
        test_out.str("");
        // Set the streams for the rs object for each test
        rs.setInputStreamForTest(test_in);
        rs.setOutputStreamForTest(test_out);
    }

    Customer* addCustomer(
        const std::string& name = "Test User",
        int age = 25,
        double money = 1000.0,
        bool auto_generate = false) {
        Customer* customer = rs.addCustomerInternal(name, age, money, auto_generate);
        if (customer == nullptr) {
            ADD_FAILURE() << "Failed to add customer";
        }
        return customer;
    }

    Booking* createConfirmedBooking(const std::string& customer_id, const std::string& flight_number, const std::string& seat_id) {
        std::string booking_error;
        Booking* booking = rs.createBookingInternal(customer_id, flight_number, seat_id, booking_error);
        if (booking == nullptr) {
            ADD_FAILURE() << "Booking creation failed: " << booking_error;
        }
        return booking;
    }

    // Holds the booking IDs produced by setupTwoConfirmedBookings so swap
    // tests can reference each leg without repeating the two-customer setup.
    struct ConfirmedBookingPair {
        std::string first_booking_id;
        std::string second_booking_id;
    };

    // Creates two customers, each with a confirmed booking on the same flight,
    // and returns their booking IDs. Shared by the swap-flow tests that only
    // differ by the seat identifiers they reserve.
    ConfirmedBookingPair setupTwoConfirmedBookings(
        const std::string& flight_number,
        const std::string& first_seat_id,
        const std::string& second_seat_id) {
        Customer* cust1 = addCustomer("First", 30, 500.0, false);
        Customer* cust2 = addCustomer("Second", 31, 500.0, false);
        EXPECT_NE(cust1, nullptr);
        EXPECT_NE(cust2, nullptr);
        ConfirmedBookingPair pair;
        if (cust1 == nullptr || cust2 == nullptr) {
            return pair;
        }
        Booking* booking1 = createConfirmedBooking(cust1->getPersonId(), flight_number, first_seat_id);
        Booking* booking2 = createConfirmedBooking(cust2->getPersonId(), flight_number, second_seat_id);
        EXPECT_NE(booking1, nullptr);
        EXPECT_NE(booking2, nullptr);
        if (booking1 != nullptr) {
            pair.first_booking_id = booking1->getBookingId();
        }
        if (booking2 != nullptr) {
            pair.second_booking_id = booking2->getBookingId();
        }
        return pair;
    }

    Booking* findBooking(const std::string& booking_id) {
        Booking* booking = rs.findBookingById(booking_id);
        if (booking == nullptr) {
            ADD_FAILURE() << "Booking not found: " << booking_id;
        }
        return booking;
    }
};

class ReservationSystemTestAccess {
public:
    static int getMenuChoice(ReservationSystem& reservation_system, const int min_choice, const int max_choice) {
        return reservation_system.getMenuChoice(min_choice, max_choice);
    }

    static char getValidatedChar(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<char>(prompt);
    }

    static int getValidatedInt(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<int>(prompt);
    }

    static double getValidatedDouble(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<double>(prompt);
    }

    static std::string getValidatedString(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<std::string>(prompt);
    }

    static void executeMenuChoice(ReservationSystem& reservation_system, const int choice) {
        reservation_system.executeMenuChoice(choice);
    }

    static bool validateSwapPair(
        const ReservationSystem& reservation_system,
        const Booking& first_booking,
        const Booking& second_booking) {
        return reservation_system.validateSwapPair(first_booking, second_booking);
    }

    static void handleAddCustomer(ReservationSystem& reservation_system) {
        reservation_system.handleAddCustomer();
    }

    static void handleSearchCustomer(ReservationSystem& reservation_system) {
        reservation_system.handleSearchCustomer();
    }

    static void handleSwapSeats(ReservationSystem& reservation_system) {
        reservation_system.handleSwapSeats();
    }

    static void handleAdminMenu(ReservationSystem& reservation_system) {
        reservation_system.handleAdminMenu();
    }

    static void clearAirplanesForTest(ReservationSystem& reservation_system) {
        reservation_system.airplanes.clear();
    }

    static void replaceAirplaneForTest(
        ReservationSystem& reservation_system,
        std::string_view flight_number,
        const Airplane& replacement) {
        for (Airplane& airplane : reservation_system.airplanes) {
            if (airplane.getFlightNumber() == flight_number) {
                airplane = replacement;
                return;
            }
        }
    }
};
