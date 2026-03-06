#include "Person.h"

Person::Person(std::string_view nameValue, int ageValue, std::string_view personIdValue)
    // cppcheck-suppress misra-c2012-12.3
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

void Person::setName(std::string_view newName) {
    name = newName;
}

void Person::setAge(int newAge) {
    if (newAge >= 0) {
        age = newAge;
    }
}
