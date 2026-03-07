// cppcheck-suppress-file missingIncludeSystem
#include <algorithm>
#include "gtest/gtest.h"
#include <sstream>

#include "../src/Airplane.h"
#include "../src/Customer.h"

using enum SeatClass;

class AirplaneTestAccess {
public:
    static void truncateSeats(Airplane& plane, const std::size_t size) {
        plane.seats.resize(size);
    }

    static void clearSeats(Airplane& plane) {
        plane.seats.clear();
    }

private:
    AirplaneTestAccess() = default;
    ~AirplaneTestAccess() = default;
};

class AirplaneTest : public ::testing::Test {
protected:
    Airplane& planeDefault() { return plane_default_; }
    Airplane& planeSmall() { return plane_small_; }
    Airplane& planeMixed() { return plane_mixed_; }
    Customer& testCustomer() { return test_customer_; }

private:
    Airplane plane_default_{};
    Airplane plane_small_{"SM101", 2, 2};
    Airplane plane_mixed_{"MX202", 5, 6};
    Customer test_customer_{"Test Cust", 30, "TC001", 150.0};
};

TEST_F(AirplaneTest, DefaultConstructor) {
    EXPECT_EQ(planeDefault().getFlightNumber(), "FL000");
    EXPECT_EQ(planeDefault().getCapacity(), 10 * 6);
    EXPECT_EQ(planeDefault().getBookedSeatsCount(), 0);
    EXPECT_FALSE(planeDefault().isFull());
    EXPECT_EQ(planeDefault().getAllSeats().size(), 10 * 6);
}

TEST_F(AirplaneTest, ParameterizedConstructorSmall) {
    EXPECT_EQ(planeSmall().getFlightNumber(), "SM101");
    EXPECT_EQ(planeSmall().getCapacity(), 2 * 2);
    EXPECT_EQ(planeSmall().getAllSeats().size(), 2 * 2);
    ASSERT_NE(planeSmall().findSeat("1A"), nullptr);
    ASSERT_NE(planeSmall().findSeat("2B"), nullptr);
    ASSERT_EQ(planeSmall().findSeat("3A"), nullptr);
}

TEST_F(AirplaneTest, ParameterizedConstructorMixed) {
    EXPECT_EQ(planeMixed().getFlightNumber(), "MX202");
    EXPECT_EQ(planeMixed().getCapacity(), 5 * 6);
    EXPECT_EQ(planeMixed().getAllSeats().size(), 30);

    const Seat* firstBusinessSeat = planeMixed().findSeat("1A");
    ASSERT_NE(firstBusinessSeat, nullptr);
    EXPECT_EQ(firstBusinessSeat->getSeatClass(), BUSINESS);
    EXPECT_DOUBLE_EQ(firstBusinessSeat->getPrice(), 200.0);

    const Seat* firstEconomySeat = planeMixed().findSeat("2A");
    ASSERT_NE(firstEconomySeat, nullptr);
    EXPECT_EQ(firstEconomySeat->getSeatClass(), ECONOMY);
}

TEST_F(AirplaneTest, ConstructorInvalidDimensions) {
    Airplane plane_invalid_rows("IVR01", 0, 6);
    EXPECT_EQ(plane_invalid_rows.getCapacity(), 6);

    Airplane plane_invalid_cols("IVC01", 5, 0);
    EXPECT_EQ(plane_invalid_cols.getCapacity(), 5);
}

TEST_F(AirplaneTest, FindSeat) {
    EXPECT_NE(planeSmall().findSeat("1A"), nullptr);
    EXPECT_EQ(planeSmall().findSeat("1A")->getSeatId(), "1A");
    EXPECT_EQ(planeSmall().findSeat("3C"), nullptr);
}

TEST_F(AirplaneTest, BookSpecificSeat) {
    EXPECT_TRUE(planeSmall().bookSpecificSeat("1A"));
    EXPECT_EQ(planeSmall().getBookedSeatsCount(), 1);
    const Seat* seat = planeSmall().findSeat("1A");
    ASSERT_NE(seat, nullptr);
    EXPECT_TRUE(seat->getIsBooked());

    EXPECT_FALSE(planeSmall().bookSpecificSeat("1A"));
    EXPECT_FALSE(planeSmall().bookSpecificSeat("5Z"));
    EXPECT_EQ(planeSmall().getBookedSeatsCount(), 1);
}

TEST_F(AirplaneTest, UnbookSpecificSeat) {
    planeSmall().bookSpecificSeat("1B");
    EXPECT_EQ(planeSmall().getBookedSeatsCount(), 1);

    EXPECT_TRUE(planeSmall().unbookSpecificSeat("1B"));
    EXPECT_EQ(planeSmall().getBookedSeatsCount(), 0);
    const Seat* seat = planeSmall().findSeat("1B");
    ASSERT_NE(seat, nullptr);
    EXPECT_FALSE(seat->getIsBooked());

    EXPECT_FALSE(planeSmall().unbookSpecificSeat("1B"));
    EXPECT_FALSE(planeSmall().unbookSpecificSeat("5Z"));
}

TEST_F(AirplaneTest, IsFull) {
    EXPECT_FALSE(planeSmall().isFull());
    planeSmall().bookSpecificSeat("1A");
    planeSmall().bookSpecificSeat("1B");
    planeSmall().bookSpecificSeat("2A");
    EXPECT_FALSE(planeSmall().isFull());
    planeSmall().bookSpecificSeat("2B");
    EXPECT_TRUE(planeSmall().isFull());
    EXPECT_EQ(planeSmall().getBookedSeatsCount(), 4);
}

TEST_F(AirplaneTest, GetAvailableSeatsByClass) {
    std::vector<const Seat*> businessSeats = planeMixed().getAvailableSeatsByClass(BUSINESS);
    std::vector<const Seat*> economySeats = planeMixed().getAvailableSeatsByClass(ECONOMY);
    EXPECT_EQ(businessSeats.size(), 6);
    EXPECT_EQ(economySeats.size(), 24);

    planeMixed().bookSpecificSeat("1A");
    planeMixed().bookSpecificSeat("3C");

    businessSeats = planeMixed().getAvailableSeatsByClass(BUSINESS);
    economySeats = planeMixed().getAvailableSeatsByClass(ECONOMY);
    EXPECT_EQ(businessSeats.size(), 5);
    EXPECT_EQ(economySeats.size(), 23);
}

TEST_F(AirplaneTest, GetAvailableSeatsByClassReturnsEmptyWhenAllSeatsInClassAreBooked) {
    ASSERT_TRUE(planeSmall().bookSpecificSeat("2A"));
    ASSERT_TRUE(planeSmall().bookSpecificSeat("2B"));

    const std::vector<const Seat*> economySeats = planeSmall().getAvailableSeatsByClass(ECONOMY);

    EXPECT_TRUE(economySeats.empty());
}

TEST_F(AirplaneTest, SuggestLowerPriceSeats) {
    std::vector<const Seat*> suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 1000.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), ECONOMY);
        EXPECT_LE(seat->getPrice(), testCustomer().getMoney());
        EXPECT_LE(seat->getPrice(), 1000.0);
    }

    suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 75.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), ECONOMY);
        EXPECT_LE(seat->getPrice(), 75.0);
    }

    testCustomer().setMoney(300.0);
    suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 200.0);
    EXPECT_EQ(suggestions.size(), 30);
    ASSERT_FALSE(suggestions.empty());
    EXPECT_EQ(suggestions.front()->getSeatClass(), ECONOMY);

    bool businessFound = false;
    for (const auto* seat : suggestions) {
        if (seat->getSeatClass() == BUSINESS) {
            businessFound = true;
        }
        EXPECT_LE(seat->getPrice(), 200.0);
    }
    EXPECT_TRUE(businessFound);

    testCustomer().setMoney(60.0);
    suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 200.0);
    EXPECT_EQ(suggestions.size(), 24);
    for (const auto* seat : suggestions) {
        EXPECT_EQ(seat->getSeatClass(), ECONOMY);
        EXPECT_LE(seat->getPrice(), 60.0);
    }

    testCustomer().setMoney(0.0);
    suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 200.0);
    EXPECT_TRUE(suggestions.empty());

    testCustomer().setMoney(150.0);
    planeMixed().bookSpecificSeat("3A");
    suggestions = planeMixed().suggestLowerPriceSeats(&testCustomer(), 75.0);
    EXPECT_EQ(suggestions.size(), 23);
}

TEST_F(AirplaneTest, DisplayMethodsNoCrash) {
    EXPECT_NO_THROW(planeDefault().displaySeatingMap());
    EXPECT_NO_THROW(planeDefault().displayAvailableSeats());
    EXPECT_NO_THROW(planeDefault().displayAllSeatDetails());

    Airplane emptyPlane("EP001", 0, 0);
    EXPECT_NO_THROW(emptyPlane.displayAllSeatDetails());
}

TEST_F(AirplaneTest, DisplayAvailableSeatsWhenFull) {
    planeSmall().bookSpecificSeat("1A");
    planeSmall().bookSpecificSeat("1B");
    planeSmall().bookSpecificSeat("2A");
    planeSmall().bookSpecificSeat("2B");
    ASSERT_TRUE(planeSmall().isFull());

    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream captured;
    std::cout.rdbuf(captured.rdbuf());

    planeSmall().displayAvailableSeats();

    std::cout.rdbuf(oldCoutStreamBuf);
    EXPECT_NE(captured.str().find("No seats available."), std::string::npos);
}

TEST_F(AirplaneTest, DisplaySeatingMapShowsBookedSeatsAsX) {
    ASSERT_TRUE(planeSmall().bookSpecificSeat("1A"));

    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream captured;
    std::cout.rdbuf(captured.rdbuf());

    planeSmall().displaySeatingMap();

    std::cout.rdbuf(oldCoutStreamBuf);
    EXPECT_NE(captured.str().find("X "), std::string::npos);
}

TEST_F(AirplaneTest, SuggestLowerPriceSeatsNullCustomer) {
    const std::vector<const Seat*> suggestions = planeMixed().suggestLowerPriceSeats(nullptr, 100.0);
    EXPECT_TRUE(suggestions.empty());
}

TEST_F(AirplaneTest, SuggestLowerPriceSeatsReturnsEmptyWhenNoSeatMatchesBudget) {
    testCustomer().setMoney(10.0);

    const std::vector<const Seat*> suggestions = planeSmall().suggestLowerPriceSeats(&testCustomer(), 10.0);

    EXPECT_TRUE(suggestions.empty());
}

TEST_F(AirplaneTest, DisplaySeatingMapHandlesSparseSeatStorage) {
    AirplaneTestAccess::truncateSeats(planeSmall(), 1);

    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream captured;
    std::cout.rdbuf(captured.rdbuf());

    planeSmall().displaySeatingMap();

    std::cout.rdbuf(oldCoutStreamBuf);
    EXPECT_NE(captured.str().find("Legend: X=Booked, B=Available Business, E=Available Economy"), std::string::npos);
    EXPECT_NE(captured.str().find("\n2  "), std::string::npos);
}

TEST_F(AirplaneTest, DisplayAllSeatDetailsReportsWhenSeatStorageIsEmpty) {
    AirplaneTestAccess::clearSeats(planeSmall());

    std::streambuf* oldCoutStreamBuf = std::cout.rdbuf();
    std::ostringstream captured;
    std::cout.rdbuf(captured.rdbuf());

    planeSmall().displayAllSeatDetails();

    std::cout.rdbuf(oldCoutStreamBuf);
    EXPECT_NE(captured.str().find("No seats configured for this airplane."), std::string::npos);
}

TEST_F(AirplaneTest, SuggestLowerPriceSeatsSortsCustomSeatPricesAscending) {
    ASSERT_EQ(planeSmall().getAllSeats().size(), 4U);
    ASSERT_NE(planeSmall().findSeat("1A"), nullptr);
    ASSERT_NE(planeSmall().findSeat("1B"), nullptr);
    ASSERT_NE(planeSmall().findSeat("2A"), nullptr);
    ASSERT_NE(planeSmall().findSeat("2B"), nullptr);
    planeSmall().findSeat("1A")->setPrice(120.0);
    planeSmall().findSeat("1B")->setPrice(80.0);
    planeSmall().findSeat("2A")->setPrice(100.0);
    planeSmall().findSeat("2B")->setPrice(60.0);

    Customer budgetCustomer{"Budget Buyer", 28, "TC999", 150.0};
    const std::vector<const Seat*> suggestions = planeSmall().suggestLowerPriceSeats(&budgetCustomer, 150.0);

    ASSERT_EQ(suggestions.size(), 4U);
    std::vector<double> prices;
    prices.reserve(suggestions.size());
    for (const auto* seat : suggestions) {
        prices.push_back(seat->getPrice());
    }

    EXPECT_TRUE(std::is_sorted(prices.begin(), prices.end()));
    EXPECT_DOUBLE_EQ(prices.front(), 60.0);
    EXPECT_DOUBLE_EQ(prices.back(), 120.0);
}
