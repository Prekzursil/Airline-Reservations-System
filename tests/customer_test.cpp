// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "../src/Customer.h"

class CustomerTest : public ::testing::Test {
protected:
    Customer c1{"Bob The Builder", 45, "C0001", 800.0};
    Customer cDefault{};
};

TEST_F(CustomerTest, DefaultConstructor) {
    EXPECT_EQ(cDefault.getName(), "Unknown Customer");
    EXPECT_EQ(cDefault.getAge(), 0);
    EXPECT_EQ(cDefault.getPersonId(), "C0000");
    EXPECT_DOUBLE_EQ(cDefault.getMoney(), 0.0);
}

TEST_F(CustomerTest, ParameterizedConstructor) {
    EXPECT_EQ(c1.getName(), "Bob The Builder");
    EXPECT_EQ(c1.getAge(), 45);
    EXPECT_EQ(c1.getPersonId(), "C0001");
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, SetMoney) {
    c1.setMoney(1000.50);
    EXPECT_DOUBLE_EQ(c1.getMoney(), 1000.50);
}

TEST_F(CustomerTest, SetMoneyInvalid) {
    c1.setMoney(-100.0);
    EXPECT_DOUBLE_EQ(c1.getMoney(), 0.0);
}

TEST_F(CustomerTest, ChargeMoneySufficientFunds) {
    EXPECT_TRUE(c1.chargeMoney(100.0));
    EXPECT_DOUBLE_EQ(c1.getMoney(), 700.0);
}

TEST_F(CustomerTest, ChargeMoneyInsufficientFunds) {
    EXPECT_FALSE(c1.chargeMoney(1000.0));
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, ChargeMoneyZeroAmount) {
    EXPECT_FALSE(c1.chargeMoney(0.0));
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, ChargeMoneyNegativeAmount) {
    EXPECT_FALSE(c1.chargeMoney(-50.0));
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, AddMoney) {
    c1.addMoney(200.0);
    EXPECT_DOUBLE_EQ(c1.getMoney(), 1000.0);
}

TEST_F(CustomerTest, AddMoneyZeroAmount) {
    c1.addMoney(0.0);
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, AddMoneyNegativeAmount) {
    c1.addMoney(-50.0);
    EXPECT_DOUBLE_EQ(c1.getMoney(), 800.0);
}

TEST_F(CustomerTest, DisplayDetailsNoCrash) {
    EXPECT_NO_THROW(c1.displayDetails());
    EXPECT_NO_THROW(cDefault.displayDetails());
}

TEST_F(CustomerTest, InheritedSetName) {
    c1.setName("Robert Builder");
    EXPECT_EQ(c1.getName(), "Robert Builder");
}

TEST_F(CustomerTest, InheritedSetAge) {
    c1.setAge(50);
    EXPECT_EQ(c1.getAge(), 50);
}
