// cppcheck-suppress-file missingIncludeSystem
#include "Customer.h"
#include <iomanip>  // For std::setprecision
#include <iostream> // For std::cout, std::endl, std::fixed

// Constructors
Customer::Customer(std::string_view name, int age, std::string_view personId, double initialMoney)
    // cppcheck-suppress misra-c2012-12.3
    : Person(name, age, personId), money(initialMoney) {}

// Destructor
Customer::~Customer() = default;

// Getter for money
double Customer::getMoney() const {
    return money;
}

// Setter for money
void Customer::setMoney(double newMoney) {
    if (newMoney >= 0.0) {
        money = newMoney;
    } else {
        money = 0.0;
    }
}

bool Customer::chargeMoney(double amount) {
    if (amount > 0 && money >= amount) {
        money -= amount;
        return true;
    }
    return false;
}

void Customer::addMoney(double amount) {
    if (amount > 0) {
        money += amount;
    }
}

// Override displayDetails
void Customer::displayDetails() const {
    std::cout << "Customer Details:" << std::endl;
    std::cout << "  ID: " << getPersonId() << std::endl;
    std::cout << "  Name: " << getName() << std::endl;
    std::cout << "  Age: " << getAge() << std::endl;
    std::cout << "  Money: $" << std::fixed << std::setprecision(2) << money << std::endl;
}
