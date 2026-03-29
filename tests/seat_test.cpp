#include "gtest/gtest.h"
#include "../src/Seat.h"

using enum SeatClass;

std::string seatClassToString(SeatClass sc);

class SeatTest : public ::testing::Test {
protected:
    Seat& economySeat() { return economy_seat_; }
    Seat& businessSeat() { return business_seat_; }
    Seat& defaultSeat() { return default_seat_; }

private:
    Seat economy_seat_{"10A", ECONOMY, 100.0};
    Seat business_seat_{"1B", BUSINESS, 100.0};
    Seat default_seat_{};
};

TEST_F(SeatTest, DefaultConstructor) {
    EXPECT_EQ(defaultSeat().getSeatId(), "N/A");
    EXPECT_EQ(defaultSeat().getSeatClass(), ECONOMY);
    EXPECT_DOUBLE_EQ(defaultSeat().getPrice(), 50.0);
    EXPECT_FALSE(defaultSeat().getIsBooked());
    EXPECT_EQ(defaultSeat().getSeatClassString(), "Economy");
}

TEST_F(SeatTest, ParameterizedConstructorEconomy) {
    EXPECT_EQ(economySeat().getSeatId(), "10A");
    EXPECT_EQ(economySeat().getSeatClass(), ECONOMY);
    EXPECT_DOUBLE_EQ(economySeat().getPrice(), 100.0);
    EXPECT_FALSE(economySeat().getIsBooked());
    EXPECT_EQ(economySeat().getSeatClassString(), "Economy");
}

TEST_F(SeatTest, ParameterizedConstructorBusiness) {
    EXPECT_EQ(businessSeat().getSeatId(), "1B");
    EXPECT_EQ(businessSeat().getSeatClass(), BUSINESS);
    EXPECT_DOUBLE_EQ(businessSeat().getPrice(), 200.0);
    EXPECT_FALSE(businessSeat().getIsBooked());
    EXPECT_EQ(businessSeat().getSeatClassString(), "Business");
}

TEST_F(SeatTest, SetPrice) {
    economySeat().setPrice(120.0);
    EXPECT_DOUBLE_EQ(economySeat().getPrice(), 120.0);
}

TEST_F(SeatTest, SetPriceInvalid) {
    const double originalPrice = economySeat().getPrice();
    economySeat().setPrice(-50.0);
    EXPECT_DOUBLE_EQ(economySeat().getPrice(), originalPrice);
}

TEST_F(SeatTest, BookSeatAvailable) {
    EXPECT_TRUE(economySeat().bookSeat());
    EXPECT_TRUE(economySeat().getIsBooked());
}

TEST_F(SeatTest, BookSeatAlreadyBooked) {
    economySeat().bookSeat();
    EXPECT_FALSE(economySeat().bookSeat());
    EXPECT_TRUE(economySeat().getIsBooked());
}

TEST_F(SeatTest, UnbookSeatBooked) {
    economySeat().bookSeat();
    EXPECT_TRUE(economySeat().unbookSeat());
    EXPECT_FALSE(economySeat().getIsBooked());
}

TEST_F(SeatTest, UnbookSeatNotBooked) {
    EXPECT_FALSE(economySeat().unbookSeat());
    EXPECT_FALSE(economySeat().getIsBooked());
}

TEST_F(SeatTest, GetSeatClassString) {
    Seat econ("E1", ECONOMY, 50);
    Seat biz("B1", BUSINESS, 100);

    EXPECT_EQ(econ.getSeatClassString(), "Economy");
    EXPECT_EQ(biz.getSeatClassString(), "Business");
}

TEST_F(SeatTest, SeatClassToStringDefault) {
    const auto unknownSc = static_cast<SeatClass>(99);
    EXPECT_EQ(seatClassToString(unknownSc), "Unknown");
}

TEST_F(SeatTest, DisplaySeatInfoNoCrash) {
    EXPECT_NO_THROW(economySeat().displaySeatInfo());
    EXPECT_NO_THROW(businessSeat().displaySeatInfo());
    EXPECT_NO_THROW(defaultSeat().displaySeatInfo());
}

TEST_F(SeatTest, DisplaySeatInfoReportsBookedStatus) {
    ASSERT_TRUE(economySeat().bookSeat());

    std::ostringstream captured_output;
    std::streambuf* original_cout = std::cout.rdbuf(captured_output.rdbuf());

    economySeat().displaySeatInfo();

    std::cout.rdbuf(original_cout);

    EXPECT_NE(captured_output.str().find("Status: Booked"), std::string::npos);
}
