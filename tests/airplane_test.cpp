#include "gtest/gtest.h"
#include "../src/Airplane.h"
#include "../src/Customer.h"
#include <sstream>

class AirplaneTest : public ::testing::Test {
protected:
    Airplane plane_default{};
    Airplane plane_small{"SM101", 2, 2};
    Airplane plane_mixed{"MX202", 5, 6};
    Customer testCustomer{"Test Cust", 30, "TC001", 150.0};
};

TEST_F(AirplaneTest, DefaultConstructor) {
    EXPECT_EQ(plane_default.getFlightNumber(), "FL000");
    EXPECT_EQ(plane_default.getCapacity(), 10 * 6);
    EXPECT_EQ(plane_default.getBookedSeatsCount(), 0);
    EXPECT_FALSE(plane_default.isFull());
    EXPECT_EQ(plane_default.getAllSeats().size(), 10 * 6);
}

TEST_F(AirplaneTest, ParameterizedConstructorSmall) {
    EXPECT_EQ(plane_small.getFlightNumber(), "SM101");
    EXPECT_EQ(plane_small.getCapacity(), 2 * 2);
    EXPECT_EQ(plane_small.getAllSeats().size(), 2 * 2);
    ASSERT_NE(plane_small.findSeat("1A"), nullptr);
    ASSERT_NE(plane_small.findSeat("2B"), nullptr);
    ASSERT_EQ(plane_small.findSeat("3A"), nullptr);
}

TEST_F(AirplaneTest, ParameterizedConstructorMixed) {
    EXPECT_EQ(plane_mixed.getFlightNumber(), "MX202");
    EXPECT_EQ(plane_mixed.getCapacity(), 5 * 6);
    EXPECT_EQ(plane_mixed.getAllSeats().size(), 30);

    const Seat* firstBusinessSeat = plane_mixed.findSeat("1A");
    ASSERT_NE(firstBusinessSeat, nullptr);
    EXPECT_EQ(firstBusinessSeat->getSeatClass(), SeatClass::BUSINESS);
    EXPECT_DOUBLE_EQ(firstBusinessSeat->getPrice(), 200.0);

    const Seat* firstEconomySeat = plane_mixed.findSeat("2A");
    ASSERT_NE(firstEconomySeat, nullptr);
    EXPECT_EQ(firstEconomySeat->getSeatClass(), SeatClass::ECONOMY);
}

TEST_F(AirplaneTest, ConstructorInvalidDimensions) {
    Airplane plane_invalid_rows("IVR01", 0, 6);
    EXPECT_EQ(plane_invalid_rows.getCapacity(), 1 * 6);

    Airplane plane_invalid_cols("IVC01", 5, 0);
    EXPECT_EQ(plane_invalid_cols.getCapacity(), 5 * 1);
}

TEST_F(AirplaneTest, FindSeat) {
    EXPECT_NE(plane_small.findSeat("1A"), nullptr);
    EXPECT_EQ(plane_small.findSeat("1A")->getSeatId(), "1A");
    EXPECT_EQ(plane_small.findSeat("3C"), nullptr);
}

TEST_F(AirplaneTest, BookSpecificSeat) {
    EXPECT_TRUE(plane_small.bookSpecificSeat("1A"));
    EXPECT_EQ(plane_small.getBookedSeatsCount(), 1);
    const Seat* seat = plane_small.findSeat("1A");
    ASSERT_NE(seat, nullptr);
    EXPECT_TRUE(seat->getIsBooked());

    EXPECT_FALSE(plane_small.bookSpecificSeat("1A"));
    EXPECT_FALSE(plane_small.bookSpecificSeat("5Z"));
    EXPECT_EQ(plane_small.getBookedSeatsCount(), 1);
}

TEST_F(AirplaneTest, UnbookSpecificSeat) {
    plane_small.bookSpecificSeat("1B");
    EXPECT_EQ(plane_small.getBookedSeatsCount(), 1);

    EXPECT_TRUE(plane_small.unbookSpecificSeat("1B"));
    EXPECT_EQ(plane_small.getBookedSeatsCount(), 0);
    const Seat* seat = plane_small.findSeat("1B");
    ASSERT_NE(seat, nullptr);
    EXPECT_FALSE(seat->getIsBooked());

    EXPECT_FALSE(plane_small.unbookSpecificSeat("1B"));
    EXPECT_FALSE(plane_small.unbookSpecificSeat("5Z"));
}

TEST_F(AirplaneTest, IsFull) {
    EXPECT_FALSE(plane_small.isFull());
    plane_small.bookSpecificSeat("1A");
    plane_small.bookSpecificSeat("1B");
    plane_small.bookSpecificSeat("2A");
    EXPECT_FALSE(plane_small.isFull());
    plane_small.bookSpecificSeat("2B");
    EXPECT_TRUE(plane_small.isFull());
    EXPECT_EQ(plane_small.getBookedSeatsCount(), 4);
}

TEST_F(AirplaneTest, GetAvailableSeatsByClass) {
    std::vector<const Seat*> businessSeats = plane_mixed.getAvailableSeatsByClass(SeatClass::BUSINESS);
    std::vector<const Seat*> economySeats = plane_mixed.getAvailableSeatsByClass(SeatClass::ECONOMY);
    EXPECT_EQ(businessSeats.size(), 6);
    EXPECT_EQ(economySeats.size(), 24);

    plane_mixed.bookSpecificSeat("1A");
    plane_mixed.bookSpecificSeat("3C");

    businessSeats = plane_mixed.getAvailableSeatsByClass(SeatClass::BUSINESS);
    economySeats = plane_mixed.getAvailableSeatsByClass(SeatClass::ECONOMY);
    EXPECT_EQ(businessSeats.size(), 5);
    EXPECT_EQ(economySeats.size(), 23);
}

TEST_F(AirplaneTest, SuggestLowerPriceSeats) {
    std::vector<const Seat*> suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 1000.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
        EXPECT_LE(seat->getPrice(), testCustomer.getMoney());
        EXPECT_LE(seat->getPrice(), 1000.0);
    }

    suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 75.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
        EXPECT_LE(seat->getPrice(), 75.0);
    }

    testCustomer.setMoney(300.0);
    suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 200.0);
    EXPECT_EQ(suggestions.size(), 30);
    ASSERT_FALSE(suggestions.empty());
    EXPECT_EQ(suggestions.front()->getSeatClass(), SeatClass::ECONOMY);

    bool businessFound = false;
    for (const auto* seat : suggestions) {
        if (seat->getSeatClass() == SeatClass::BUSINESS) {
            businessFound = true;
        }
        EXPECT_LE(seat->getPrice(), 200.0);
    }
    EXPECT_TRUE(businessFound);

    testCustomer.setMoney(60.0);
    suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 200.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), SeatClass::ECONOMY);
        EXPECT_LE(seat->getPrice(), 60.0);
    }

    testCustomer.setMoney(0.0);
    suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 200.0);
    EXPECT_TRUE(suggestions.empty());

    testCustomer.setMoney(150.0);
    plane_mixed.bookSpecificSeat("3A");
    suggestions = plane_mixed.suggestLowerPriceSeats(&testCustomer, 75.0);
    EXPECT_EQ(suggestions.size(), 23);
}

TEST_F(AirplaneTest, DisplayMethodsNoCrash) {
    EXPECT_NO_THROW(plane_default.displaySeatingMap());
    EXPECT_NO_THROW(plane_default.displayAvailableSeats());
    EXPECT_NO_THROW(plane_default.displayAllSeatDetails());

    Airplane emptyPlane("EP001", 0, 0);
    EXPECT_NO_THROW(emptyPlane.displayAllSeatDetails());
}

TEST_F(AirplaneTest, DisplayAvailableSeatsWhenFull) {
    plane_small.bookSpecificSeat("1A");
    plane_small.bookSpecificSeat("1B");
    plane_small.bookSpecificSeat("2A");
    plane_small.bookSpecificSeat("2B");
    ASSERT_TRUE(plane_small.isFull());

    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream captured;
    std::cout.rdbuf(captured.rdbuf());

    plane_small.displayAvailableSeats();

    std::cout.rdbuf(oldCoutStreamBuf);
    EXPECT_NE(captured.str().find("No seats available."), std::string::npos);
}

TEST_F(AirplaneTest, SuggestLowerPriceSeatsNullCustomer) {
    const std::vector<const Seat*> suggestions = plane_mixed.suggestLowerPriceSeats(nullptr, 100.0);
    EXPECT_TRUE(suggestions.empty());
}
