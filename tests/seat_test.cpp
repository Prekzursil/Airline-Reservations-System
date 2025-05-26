#include "gtest/gtest.h"
#include "../src/Seat.h" // Adjust path to Seat.h

// Forward declaration for the helper function in Seat.cpp to test its default case
std::string seatClassToString(SeatClass sc);

// Test fixture for Seat tests
class SeatTest : public ::testing::Test {
protected:
    Seat* economySeat;
    Seat* businessSeat;
    Seat* defaultSeat;

    void SetUp() override {
        economySeat = new Seat("10A", SeatClass::ECONOMY, 100.0);
        businessSeat = new Seat("1B", SeatClass::BUSINESS, 100.0); // Base price 100, so business should be 200
        defaultSeat = new Seat(); // Test default constructor
    }

    void TearDown() override {
        delete economySeat;
        delete businessSeat;
        delete defaultSeat;
        economySeat = nullptr;
        businessSeat = nullptr;
        defaultSeat = nullptr;
    }
};

// Test default constructor
TEST_F(SeatTest, DefaultConstructor) {
    EXPECT_EQ(defaultSeat->getSeatId(), "N/A");
    EXPECT_EQ(defaultSeat->getSeatClass(), SeatClass::ECONOMY);
    EXPECT_DOUBLE_EQ(defaultSeat->getPrice(), 50.0); // Default base price for economy
    EXPECT_FALSE(defaultSeat->getIsBooked());
    EXPECT_EQ(defaultSeat->getSeatClassString(), "Economy");
}

// Test parameterized constructor for Economy seat
TEST_F(SeatTest, ParameterizedConstructorEconomy) {
    EXPECT_EQ(economySeat->getSeatId(), "10A");
    EXPECT_EQ(economySeat->getSeatClass(), SeatClass::ECONOMY);
    EXPECT_DOUBLE_EQ(economySeat->getPrice(), 100.0);
    EXPECT_FALSE(economySeat->getIsBooked());
    EXPECT_EQ(economySeat->getSeatClassString(), "Economy");
}

// Test parameterized constructor for Business seat (price calculation)
TEST_F(SeatTest, ParameterizedConstructorBusiness) {
    EXPECT_EQ(businessSeat->getSeatId(), "1B");
    EXPECT_EQ(businessSeat->getSeatClass(), SeatClass::BUSINESS);
    EXPECT_DOUBLE_EQ(businessSeat->getPrice(), 200.0); // Base price 100.0 * 2.0
    EXPECT_FALSE(businessSeat->getIsBooked());
    EXPECT_EQ(businessSeat->getSeatClassString(), "Business");
}

// Test setPrice
TEST_F(SeatTest, SetPrice) {
    economySeat->setPrice(120.0);
    EXPECT_DOUBLE_EQ(economySeat->getPrice(), 120.0);
}

// Test setPrice with invalid input
TEST_F(SeatTest, SetPriceInvalid) {
    double originalPrice = economySeat->getPrice();
    economySeat->setPrice(-50.0); // Implementation ignores negative price
    EXPECT_DOUBLE_EQ(economySeat->getPrice(), originalPrice);
}

// Test bookSeat when available
TEST_F(SeatTest, BookSeatAvailable) {
    EXPECT_TRUE(economySeat->bookSeat());
    EXPECT_TRUE(economySeat->getIsBooked());
}

// Test bookSeat when already booked
TEST_F(SeatTest, BookSeatAlreadyBooked) {
    economySeat->bookSeat(); // First booking
    EXPECT_FALSE(economySeat->bookSeat()); // Attempt to book again
    EXPECT_TRUE(economySeat->getIsBooked());
}

// Test unbookSeat when booked
TEST_F(SeatTest, UnbookSeatBooked) {
    economySeat->bookSeat();
    EXPECT_TRUE(economySeat->unbookSeat());
    EXPECT_FALSE(economySeat->getIsBooked());
}

// Test unbookSeat when not booked
TEST_F(SeatTest, UnbookSeatNotBooked) {
    EXPECT_FALSE(economySeat->unbookSeat());
    EXPECT_FALSE(economySeat->getIsBooked());
}

// Test getSeatClassString helper
TEST_F(SeatTest, GetSeatClassString) {
    Seat econ("E1", SeatClass::ECONOMY, 50);
    Seat biz("B1", SeatClass::BUSINESS, 100);
    // Seat unknownSeat("U1", static_cast<SeatClass>(99), 10); // To test default in helper

    EXPECT_EQ(econ.getSeatClassString(), "Economy");
    EXPECT_EQ(biz.getSeatClassString(), "Business");
}

// Test seatClassToString default case
TEST_F(SeatTest, SeatClassToStringDefault) {
    // Cast an integer to SeatClass that is out of range for defined enums
    SeatClass unknownSc = static_cast<SeatClass>(99); 
    EXPECT_EQ(seatClassToString(unknownSc), "Unknown");
}

// Test displaySeatInfo - similar to Customer, check for no crash
TEST_F(SeatTest, DisplaySeatInfoNoCrash) {
    EXPECT_NO_THROW(economySeat->displaySeatInfo());
    EXPECT_NO_THROW(businessSeat->displaySeatInfo());
    EXPECT_NO_THROW(defaultSeat->displaySeatInfo());
}
