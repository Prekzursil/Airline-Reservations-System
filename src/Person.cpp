#include "Person.h"

// Constructors
Person::Person(const std::string& name, int age, const std::string& personId)
    : name(name), age(age), personId(personId) {
    // std::cout << "Person constructor called for " << this->name << std::endl; // Optional: for debugging
}

// Virtual destructor
Person::~Person() {
    // std::cout << "Person destructor called for " << this->name << std::endl; // Optional: for debugging
}

// Getters
std::string Person::getName() const {
    return name;
}

int Person::getAge() const {
    return age;
}

std::string Person::getPersonId() const {
    return personId;
}

// Setters
void Person::setName(const std::string& name) {
    this->name = name;
}

void Person::setAge(int age) {
    if (age >= 0) { // Basic validation
        this->age = age;
    } else {
        // Potentially throw an error or log, for now, just ignore invalid age
        // std::cerr << "Error: Age cannot be negative." << std::endl;
    }
}

// Note: displayDetails is a pure virtual function and has no implementation in Person.cpp
// Derived classes must implement it.
