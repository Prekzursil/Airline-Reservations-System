#include "gtest/gtest.h"
#include "../src/Seat.h"

std::string seatClassToString(SeatClass sc);

class SeatTest : public ::testing::Test {
protected:
    Seat economySeat{"10A", SeatClass::ECONOMY, 100.0};
    Seat businessSeat{"1B", SeatClass::BUSINESS, 100.0};
    Seat defaultSeat{};
};

TEST_F(SeatTest, DefaultConstructor) {
    EXPECT_EQ(defaultSeat.getSeatId(), "N/A");
    EXPECT_EQ(defaultSeat.getSeatClass(), SeatClass::ECONOMY);
    EXPECT_DOUBLE_EQ(defaultSeat.getPrice(), 50.0);
    EXPECT_FALSE(defaultSeat.getIsBooked());
    EXPECT_EQ(defaultSeat.getSeatClassString(), "Economy");
}

TEST_F(SeatTest, ParameterizedConstructorEconomy) {
    EXPECT_EQ(economySeat.getSeatId(), "10A");
    EXPECT_EQ(economySeat.getSeatClass(), SeatClass::ECONOMY);
    EXPECT_DOUBLE_EQ(economySeat.getPrice(), 100.0);
    EXPECT_FALSE(economySeat.getIsBooked());
    EXPECT_EQ(economySeat.getSeatClassString(), "Economy");
}

TEST_F(SeatTest, ParameterizedConstructorBusiness) {
    EXPECT_EQ(businessSeat.getSeatId(), "1B");
    EXPECT_EQ(businessSeat.getSeatClass(), SeatClass::BUSINESS);
    EXPECT_DOUBLE_EQ(businessSeat.getPrice(), 200.0);
    EXPECT_FALSE(businessSeat.getIsBooked());
    EXPECT_EQ(businessSeat.getSeatClassString(), "Business");
}

TEST_F(SeatTest, SetPrice) {
    economySeat.setPrice(120.0);
    EXPECT_DOUBLE_EQ(economySeat.getPrice(), 120.0);
}

TEST_F(SeatTest, SetPriceInvalid) {
    const double originalPrice = economySeat.getPrice();
    economySeat.setPrice(-50.0);
    EXPECT_DOUBLE_EQ(economySeat.getPrice(), originalPrice);
}

TEST_F(SeatTest, BookSeatAvailable) {
    EXPECT_TRUE(economySeat.bookSeat());
    EXPECT_TRUE(economySeat.getIsBooked());
}

TEST_F(SeatTest, BookSeatAlreadyBooked) {
    economySeat.bookSeat();
    EXPECT_FALSE(economySeat.bookSeat());
    EXPECT_TRUE(economySeat.getIsBooked());
}

TEST_F(SeatTest, UnbookSeatBooked) {
    economySeat.bookSeat();
    EXPECT_TRUE(economySeat.unbookSeat());
    EXPECT_FALSE(economySeat.getIsBooked());
}

TEST_F(SeatTest, UnbookSeatNotBooked) {
    EXPECT_FALSE(economySeat.unbookSeat());
    EXPECT_FALSE(economySeat.getIsBooked());
}

TEST_F(SeatTest, GetSeatClassString) {
    Seat econ("E1", SeatClass::ECONOMY, 50);
    Seat biz("B1", SeatClass::BUSINESS, 100);

    EXPECT_EQ(econ.getSeatClassString(), "Economy");
    EXPECT_EQ(biz.getSeatClassString(), "Business");
}

TEST_F(SeatTest, SeatClassToStringDefault) {
    const SeatClass unknownSc = static_cast<SeatClass>(99);
    EXPECT_EQ(seatClassToString(unknownSc), "Unknown");
}

TEST_F(SeatTest, DisplaySeatInfoNoCrash) {
    EXPECT_NO_THROW(economySeat.displaySeatInfo());
    EXPECT_NO_THROW(businessSeat.displaySeatInfo());
    EXPECT_NO_THROW(defaultSeat.displaySeatInfo());
}
