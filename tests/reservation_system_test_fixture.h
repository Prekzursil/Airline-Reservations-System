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

class ReservationSystemTest : public ::testing::Test {
protected:
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
    static int getValidatedInt(ReservationSystem& reservation_system, const std::string& prompt) {
        return reservation_system.getValidatedInput<int>(prompt);
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
};

