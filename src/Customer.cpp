#include "Customer.h"
#include <iostream> // For std::cout, std::endl, std::fixed
#include <iomanip>  // For std::setprecision

// Constructors
Customer::Customer(const std::string& name, int age, const std::string& personId, double money)
    : Person(name, age, personId), money(money) {
    // std::cout << "Customer constructor called for " << this->name << std::endl; // Optional: for debugging
}

// Destructor
Customer::~Customer() {
    // std::cout << "Customer destructor called for " << this->name << std::endl; // Optional: for debugging
}

// Getter for money
double Customer::getMoney() const {
    return money;
}

// Setter for money
void Customer::setMoney(double money) {
    if (money >= 0.0) {
        this->money = money;
    } else {
        // std::cerr << "Error: Money cannot be negative." << std::endl;
        this->money = 0.0; // Or handle error appropriately
    }
}

bool Customer::chargeMoney(double amount) {
    if (amount > 0 && this->money >= amount) {
        this->money -= amount;
        return true;
    }
    return false; // Insufficient funds or invalid amount
}

void Customer::addMoney(double amount) {
    if (amount > 0) {
        this->money += amount;
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
