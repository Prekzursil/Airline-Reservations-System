#include "gtest/gtest.h"
#include "../src/Customer.h" // Adjust path to Customer.h
#include <limits> // For std::numeric_limits for double comparison

// Test fixture for Customer tests
class CustomerTest : public ::testing::Test {
protected:
    Customer* c1;
    Customer* c_default;

    void SetUp() override {
        c1 = new Customer("Bob The Builder", 45, "C0001", 800.0);
        c_default = new Customer(); // Test default constructor
    }

    void TearDown() override {
        delete c1;
        delete c_default;
        c1 = nullptr;
        c_default = nullptr;
    }
};

// Test case for the default constructor (inherits from Person, adds money)
TEST_F(CustomerTest, DefaultConstructor) {
    EXPECT_EQ(c_default->getName(), "Unknown Customer"); // Default from Customer constructor
    EXPECT_EQ(c_default->getAge(), 0);
    EXPECT_EQ(c_default->getPersonId(), "C0000"); // Default from Customer constructor
    EXPECT_DOUBLE_EQ(c_default->getMoney(), 0.0);
}

// Test case for the parameterized constructor
TEST_F(CustomerTest, ParameterizedConstructor) {
    EXPECT_EQ(c1->getName(), "Bob The Builder");
    EXPECT_EQ(c1->getAge(), 45);
    EXPECT_EQ(c1->getPersonId(), "C0001");
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0);
}

// Test case for setMoney
TEST_F(CustomerTest, SetMoney) {
    c1->setMoney(1000.50);
    EXPECT_DOUBLE_EQ(c1->getMoney(), 1000.50);
}

// Test case for setMoney with invalid input (negative money)
TEST_F(CustomerTest, SetMoneyInvalid) {
    c1->setMoney(-100.0); // Customer.cpp sets to 0.0 if negative
    EXPECT_DOUBLE_EQ(c1->getMoney(), 0.0);
}

// Test case for chargeMoney (successful)
TEST_F(CustomerTest, ChargeMoneySufficientFunds) {
    EXPECT_TRUE(c1->chargeMoney(100.0));
    EXPECT_DOUBLE_EQ(c1->getMoney(), 700.0);
}

// Test case for chargeMoney (insufficient funds)
TEST_F(CustomerTest, ChargeMoneyInsufficientFunds) {
    EXPECT_FALSE(c1->chargeMoney(1000.0)); // c1 has 800.0
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0); // Money should not change
}

// Test case for chargeMoney (zero amount)
TEST_F(CustomerTest, ChargeMoneyZeroAmount) {
    EXPECT_FALSE(c1->chargeMoney(0.0)); // chargeMoney expects positive amount
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0);
}

// Test case for chargeMoney (negative amount)
TEST_F(CustomerTest, ChargeMoneyNegativeAmount) {
    EXPECT_FALSE(c1->chargeMoney(-50.0)); // chargeMoney expects positive amount
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0);
}

// Test case for addMoney
TEST_F(CustomerTest, AddMoney) {
    c1->addMoney(200.0);
    EXPECT_DOUBLE_EQ(c1->getMoney(), 1000.0);
}

// Test case for addMoney (zero amount)
TEST_F(CustomerTest, AddMoneyZeroAmount) {
    c1->addMoney(0.0); // addMoney expects positive amount
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0);
}

// Test case for addMoney (negative amount)
TEST_F(CustomerTest, AddMoneyNegativeAmount) {
    c1->addMoney(-50.0); // addMoney expects positive amount
    EXPECT_DOUBLE_EQ(c1->getMoney(), 800.0);
}

// Test displayDetails - This is harder to test directly with gtest for console output.
// Typically, you'd refactor displayDetails to return a string or use output redirection.
// For now, we'll assume it works if other parts work, or manually verify.
// A simple test could be to ensure it doesn't crash.
TEST_F(CustomerTest, DisplayDetailsNoCrash) {
    EXPECT_NO_THROW(c1->displayDetails());
    EXPECT_NO_THROW(c_default->displayDetails());
}

// Test inherited methods from Person
TEST_F(CustomerTest, InheritedSetName) {
    c1->setName("Robert Builder");
    EXPECT_EQ(c1->getName(), "Robert Builder");
}

TEST_F(CustomerTest, InheritedSetAge) {
    c1->setAge(50);
    EXPECT_EQ(c1->getAge(), 50);
}
