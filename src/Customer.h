#ifndef CUSTOMER_H
#define CUSTOMER_H

#include "Person.h" // Include the base class header
#include <string>

class Customer : public Person {
private:
    double money;

public:
    // Constructors
    Customer(const std::string& name = "Unknown Customer", int age = 0, const std::string& personId = "C0000", double money = 0.0);

    // Destructor
    ~Customer() override;

    // Getter for money
    double getMoney() const;

    // Setter for money
    void setMoney(double money);
    bool chargeMoney(double amount); // Returns true if successful
    void addMoney(double amount);

    // Override displayDetails
    void displayDetails() const override;
};

#endif // CUSTOMER_H
