// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "../src/Customer.h"

class CustomerTest : public ::testing::Test {
protected:
    Customer& customer() { return customer_; }
    Customer& defaultCustomer() { return default_customer_; }

private:
    Customer customer_{"Bob The Builder", 45, "C0001", 800.0};
    Customer default_customer_{};
};

TEST_F(CustomerTest, DefaultConstructor) {
    EXPECT_EQ(defaultCustomer().getName(), "Unknown Customer");
    EXPECT_EQ(defaultCustomer().getAge(), 0);
    EXPECT_EQ(defaultCustomer().getPersonId(), "C0000");
    EXPECT_DOUBLE_EQ(defaultCustomer().getMoney(), 0.0);
}

TEST_F(CustomerTest, ParameterizedConstructor) {
    EXPECT_EQ(customer().getName(), "Bob The Builder");
    EXPECT_EQ(customer().getAge(), 45);
    EXPECT_EQ(customer().getPersonId(), "C0001");
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, SetMoney) {
    customer().setMoney(1000.50);
    EXPECT_DOUBLE_EQ(customer().getMoney(), 1000.50);
}

TEST_F(CustomerTest, SetMoneyInvalid) {
    customer().setMoney(-100.0);
    EXPECT_DOUBLE_EQ(customer().getMoney(), 0.0);
}

TEST_F(CustomerTest, ChargeMoneySufficientFunds) {
    EXPECT_TRUE(customer().chargeMoney(100.0));
    EXPECT_DOUBLE_EQ(customer().getMoney(), 700.0);
}

TEST_F(CustomerTest, ChargeMoneyInsufficientFunds) {
    EXPECT_FALSE(customer().chargeMoney(1000.0));
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, ChargeMoneyZeroAmount) {
    EXPECT_FALSE(customer().chargeMoney(0.0));
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, ChargeMoneyNegativeAmount) {
    EXPECT_FALSE(customer().chargeMoney(-50.0));
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, AddMoney) {
    customer().addMoney(200.0);
    EXPECT_DOUBLE_EQ(customer().getMoney(), 1000.0);
}

TEST_F(CustomerTest, AddMoneyZeroAmount) {
    customer().addMoney(0.0);
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, AddMoneyNegativeAmount) {
    customer().addMoney(-50.0);
    EXPECT_DOUBLE_EQ(customer().getMoney(), 800.0);
}

TEST_F(CustomerTest, DisplayDetailsNoCrash) {
    EXPECT_NO_THROW(customer().displayDetails());
    EXPECT_NO_THROW(defaultCustomer().displayDetails());
}

TEST_F(CustomerTest, InheritedSetName) {
    customer().setName("Robert Builder");
    EXPECT_EQ(customer().getName(), "Robert Builder");
}

TEST_F(CustomerTest, InheritedSetAge) {
    customer().setAge(50);
    EXPECT_EQ(customer().getAge(), 50);
}
