#include "gtest/gtest.h"
#include "../src/Airplane.h" // Adjust path
#include "../src/Customer.h" // For suggestLowerPriceSeats

// Test fixture for Airplane tests
class AirplaneTest : public ::testing::Test {
protected:
    Airplane* plane_default; // Default constructor
    Airplane* plane_small;   // Small plane (e.g., 2 rows, 2 seats/row)
    Airplane* plane_mixed;   // Plane with business and economy (e.g., 5 rows, 6 seats/row)
    Customer* testCustomer;

    void SetUp() override {
        plane_default = new Airplane(); // Default: 10 rows, 6 seats/row
        plane_small = new Airplane("SM101", 2, 2);
        plane_mixed = new Airplane("MX202", 5, 6); // 20% business = 1 row business
        testCustomer = new Customer("Test Cust", 30, "TC001", 150.0);
    }

    void TearDown() override {
        delete plane_default;
        delete plane_small;
        delete plane_mixed;
        delete testCustomer;
        plane_default = nullptr;
        plane_small = nullptr;
        plane_mixed = nullptr;
        testCustomer = nullptr;
    }
};

// Test default constructor
TEST_F(AirplaneTest, DefaultConstructor) {
    EXPECT_EQ(plane_default->getFlightNumber(), "FL000");
    EXPECT_EQ(plane_default->getCapacity(), 10 * 6); // 10 rows, 6 seats
    EXPECT_EQ(plane_default->getBookedSeatsCount(), 0);
    EXPECT_FALSE(plane_default->isFull());
    EXPECT_EQ(plane_default->getAllSeats().size(), 10 * 6);
}

// Test parameterized constructor (small plane)
TEST_F(AirplaneTest, ParameterizedConstructorSmall) {
    EXPECT_EQ(plane_small->getFlightNumber(), "SM101");
    EXPECT_EQ(plane_small->getCapacity(), 2 * 2);
    EXPECT_EQ(plane_small->getAllSeats().size(), 2 * 2);
    // Check seat IDs (e.g., 1A, 1B, 2A, 2B)
    ASSERT_NE(plane_small->findSeat("1A"), nullptr);
    ASSERT_NE(plane_small->findSeat("2B"), nullptr);
    ASSERT_EQ(plane_small->findSeat("3A"), nullptr); // Should not exist
}

// Test parameterized constructor (mixed class plane)
TEST_F(AirplaneTest, ParameterizedConstructorMixed) {
    EXPECT_EQ(plane_mixed->getFlightNumber(), "MX202");
    EXPECT_EQ(plane_mixed->getCapacity(), 5 * 6); // 30 seats
    EXPECT_EQ(plane_mixed->getAllSeats().size(), 30);
    // Row 1 should be Business (5 rows * 0.2 = 1 row Business)
    Seat* firstBusinessSeat = plane_mixed->findSeat("1A");
    ASSERT_NE(firstBusinessSeat, nullptr);
    EXPECT_EQ(firstBusinessSeat->getSeatClass(), SeatClass::BUSINESS);
    EXPECT_DOUBLE_EQ(firstBusinessSeat->getPrice(), 200.0); // Business price is base * 2
    // Row 2 should be Economy
    Seat* firstEconomySeat = plane_mixed->findSeat("2A");
    ASSERT_NE(firstEconomySeat, nullptr);
    EXPECT_EQ(firstEconomySeat->getSeatClass(), SeatClass::ECONOMY);
}

// Test constructor with invalid rows/seatsPerRow (should default to 1)
TEST_F(AirplaneTest, ConstructorInvalidDimensions) {
    Airplane plane_invalid_rows("IVR01", 0, 6);
    EXPECT_EQ(plane_invalid_rows.getCapacity(), 1 * 6); // totalRows defaults to 1

    Airplane plane_invalid_cols("IVC01", 5, 0);
    EXPECT_EQ(plane_invalid_cols.getCapacity(), 5 * 1); // seatsPerRow defaults to 1
}


// Test findSeat
TEST_F(AirplaneTest, FindSeat) {
    EXPECT_NE(plane_small->findSeat("1A"), nullptr);
    EXPECT_EQ(plane_small->findSeat("1A")->getSeatId(), "1A");
    EXPECT_EQ(plane_small->findSeat("3C"), nullptr); // Non-existent seat
}

// Test bookSpecificSeat
TEST_F(AirplaneTest, BookSpecificSeat) {
    EXPECT_TRUE(plane_small->bookSpecificSeat("1A"));
    EXPECT_EQ(plane_small->getBookedSeatsCount(), 1);
    Seat* s = plane_small->findSeat("1A");
    ASSERT_NE(s, nullptr);
    EXPECT_TRUE(s->getIsBooked());

    EXPECT_FALSE(plane_small->bookSpecificSeat("1A")); // Already booked
    EXPECT_FALSE(plane_small->bookSpecificSeat("5Z")); // Non-existent
    EXPECT_EQ(plane_small->getBookedSeatsCount(), 1);
}

// Test unbookSpecificSeat
TEST_F(AirplaneTest, UnbookSpecificSeat) {
    plane_small->bookSpecificSeat("1B");
    EXPECT_EQ(plane_small->getBookedSeatsCount(), 1);

    EXPECT_TRUE(plane_small->unbookSpecificSeat("1B"));
    EXPECT_EQ(plane_small->getBookedSeatsCount(), 0);
    Seat* s = plane_small->findSeat("1B");
    ASSERT_NE(s, nullptr);
    EXPECT_FALSE(s->getIsBooked());

    EXPECT_FALSE(plane_small->unbookSpecificSeat("1B")); // Already unbooked
    EXPECT_FALSE(plane_small->unbookSpecificSeat("5Z")); // Non-existent
}

// Test isFull
TEST_F(AirplaneTest, IsFull) {
    EXPECT_FALSE(plane_small->isFull());
    plane_small->bookSpecificSeat("1A");
    plane_small->bookSpecificSeat("1B");
    plane_small->bookSpecificSeat("2A");
    EXPECT_FALSE(plane_small->isFull());
    plane_small->bookSpecificSeat("2B"); // All 4 seats booked
    EXPECT_TRUE(plane_small->isFull());
    EXPECT_EQ(plane_small->getBookedSeatsCount(), 4);
}

// Test getAvailableSeatsByClass
TEST_F(AirplaneTest, GetAvailableSeatsByClass) {
    // plane_mixed: 1 row (6 seats) Business, 4 rows (24 seats) Economy
    std::vector<const Seat*> business_seats = plane_mixed->getAvailableSeatsByClass(SeatClass::BUSINESS);
    std::vector<const Seat*> economy_seats = plane_mixed->getAvailableSeatsByClass(SeatClass::ECONOMY);
    EXPECT_EQ(business_seats.size(), 6);
    EXPECT_EQ(economy_seats.size(), 24);

    plane_mixed->bookSpecificSeat("1A"); // Book a business seat
    plane_mixed->bookSpecificSeat("3C"); // Book an economy seat

    business_seats = plane_mixed->getAvailableSeatsByClass(SeatClass::BUSINESS);
    economy_seats = plane_mixed->getAvailableSeatsByClass(SeatClass::ECONOMY);
    EXPECT_EQ(business_seats.size(), 5);
    EXPECT_EQ(economy_seats.size(), 23);
}

// Test suggestLowerPriceSeats
TEST_F(AirplaneTest, SuggestLowerPriceSeats) {
    // plane_mixed: Business seats are 100.0, Economy are 50.0
    // testCustomer has 150.0
    
    std::vector<const Seat*> suggestions;

    // Case 1: Customer has 150.0 money. Business seats are 200.0, Economy 50.0. maxPrice filter is high (1000.0).
    // Customer can only afford Economy seats.
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 1000.0 /*maxPrice customer willing to pay*/);
    EXPECT_EQ(suggestions.size(), 24); // Only 24 Economy seats (50.0 <= 150.0)
    if (!suggestions.empty()) {
        for(const auto* seat : suggestions) {
            EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
            EXPECT_LE(seat->getPrice(), testCustomer->getMoney());
            EXPECT_LE(seat->getPrice(), 1000.0);
        }
    }

    // Case 2: Customer can only afford economy seats (maxPrice filter = 75), money is 150.0
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 75.0);
    EXPECT_EQ(suggestions.size(), 24); // Only economy seats (price 50.0)
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
        EXPECT_LE(seat->getPrice(), 75.0);
    }
    
    // Case 3: Customer has 300.0 money, maxPrice willing to pay is 200.0.
    // Economy (50.0 <= 200.0 && 50.0 <= 300.0) -> YES (24 seats)
    // Business (200.0 <= 200.0 && 200.0 <= 300.0) -> YES (6 seats)
    testCustomer->setMoney(300.0);
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 200.0 /*willing to pay up to 200*/);
    EXPECT_EQ(suggestions.size(), 30); // All 24 economy + 6 business
    if (!suggestions.empty()) {
        EXPECT_EQ(suggestions[0]->getSeatClass(), SeatClass::ECONOMY); // Economy should be first due to sort
    }
    bool business_found_case3 = false;
    for(const auto* seat : suggestions) {
        if(seat->getSeatClass() == SeatClass::BUSINESS) business_found_case3 = true;
        EXPECT_LE(seat->getPrice(), 200.0);
    }
    EXPECT_TRUE(business_found_case3);

    // Case 4: Customer money (60.0) limits suggestions, even if willing to pay more (maxPrice 200.0)
    testCustomer->setMoney(60.0);
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 200.0);
    EXPECT_EQ(suggestions.size(), 24); // Only economy seats (50.0 <= 60.0)
     for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
        EXPECT_LE(seat->getPrice(), 60.0);
    }
    
    // Case 5: Customer has no money
    testCustomer->setMoney(0.0);
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 200.0);
    EXPECT_EQ(suggestions.size(), 0);

    // Case 5: Test with a booked seat
    testCustomer->setMoney(150.0); // Reset money
    plane_mixed->bookSpecificSeat("3A"); // Book an economy seat (one of the 24)
    suggestions = plane_mixed->suggestLowerPriceSeats(testCustomer, 75.0); // Max price 75
    EXPECT_EQ(suggestions.size(), 23); // One less economy seat
}

// Test display methods - check for no crash
TEST_F(AirplaneTest, DisplayMethodsNoCrash) {
    EXPECT_NO_THROW(plane_default->displaySeatingMap());
    EXPECT_NO_THROW(plane_default->displayAvailableSeats());
    EXPECT_NO_THROW(plane_default->displayAllSeatDetails());

    Airplane emptyPlane("EP001", 0, 0); // Test with 0 capacity
    EXPECT_NO_THROW(emptyPlane.displayAllSeatDetails());
}

// Test displayAvailableSeats when the plane is full
TEST_F(AirplaneTest, DisplayAvailableSeatsWhenFull) {
    // Fill the small plane
    plane_small->bookSpecificSeat("1A");
    plane_small->bookSpecificSeat("1B");
    plane_small->bookSpecificSeat("2A");
    plane_small->bookSpecificSeat("2B");
    ASSERT_TRUE(plane_small->isFull());

    // Capture cout (basic way, more robust methods exist with gtest extensions)
    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream strCout;
    std::cout.rdbuf(strCout.rdbuf());

    plane_small->displayAvailableSeats();

    std::cout.rdbuf(oldCoutStreamBuf); // Restore cout
    EXPECT_NE(strCout.str().find("No seats available."), std::string::npos);
}

// Test suggestLowerPriceSeats with a null customer
TEST_F(AirplaneTest, SuggestLowerPriceSeatsNullCustomer) {
    std::vector<const Seat*> suggestions = plane_mixed->suggestLowerPriceSeats(nullptr, 100.0);
    EXPECT_TRUE(suggestions.empty());
}
