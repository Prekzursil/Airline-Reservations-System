#include "Person.h"

Person::Person(const std::string& nameValue, int ageValue, const std::string& personIdValue)
    : name(nameValue), age(ageValue), personId(personIdValue) {}

Person::~Person() = default;

std::string Person::getName() const {
    return name;
}

int Person::getAge() const {
    return age;
}

std::string Person::getPersonId() const {
    return personId;
}

void Person::setName(const std::string& name) {
    this->name = name;
}

void Person::setAge(int age) {
    if (age >= 0) {
        this->age = age;
    }
}
