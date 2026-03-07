// cppcheck-suppress-file missingIncludeSystem
#ifndef CUSTOMER_H
#define CUSTOMER_H

#include "Person.h" // Include the base class header
#include <string_view>

class Customer : public Person {
private:
    double money;

public:
    // Constructors
    explicit Customer(std::string_view name = "Unknown Customer", int age = 0, std::string_view personId = "C0000", double initialMoney = 0.0);

    // Destructor
    ~Customer() override;

    // Getter for money
    double getMoney() const;

    // Setter for money
    void setMoney(double newMoney);
    bool chargeMoney(double amount); // Returns true if successful
    void addMoney(double amount);

    // Override displayDetails
    void displayDetails() const override;
};

#endif // CUSTOMER_H
