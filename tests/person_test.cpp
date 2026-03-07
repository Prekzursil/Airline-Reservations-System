#include "gtest/gtest.h"
#include "../src/Person.h"

class ConcretePerson : public Person {
public:
    explicit ConcretePerson(const std::string& name = "Unknown", int age = 0, const std::string& personId = "00000")
        : Person(name, age, personId) {}

    void displayDetails() const override {
        // Intentionally empty test double.
    }
};

class PersonTest : public ::testing::Test {
protected:
    ConcretePerson& person() { return person_; }
    ConcretePerson& defaultPerson() { return default_person_; }

private:
    ConcretePerson person_{"Alice", 30, "P123"};
    ConcretePerson default_person_{};
};

TEST_F(PersonTest, DefaultConstructor) {
    EXPECT_EQ(defaultPerson().getName(), "Unknown");
    EXPECT_EQ(defaultPerson().getAge(), 0);
    EXPECT_EQ(defaultPerson().getPersonId(), "00000");
}

TEST_F(PersonTest, ParameterizedConstructor) {
    EXPECT_EQ(person().getName(), "Alice");
    EXPECT_EQ(person().getAge(), 30);
    EXPECT_EQ(person().getPersonId(), "P123");
}

TEST_F(PersonTest, SetName) {
    person().setName("Bob");
    EXPECT_EQ(person().getName(), "Bob");
}

TEST_F(PersonTest, SetAge) {
    person().setAge(25);
    EXPECT_EQ(person().getAge(), 25);
}

TEST_F(PersonTest, SetAgeInvalid) {
    const int originalAge = person().getAge();
    person().setAge(-5);
    EXPECT_EQ(person().getAge(), originalAge);
}

TEST_F(PersonTest, Getters) {
    EXPECT_EQ(person().getName(), "Alice");
    EXPECT_EQ(person().getAge(), 30);
    EXPECT_EQ(person().getPersonId(), "P123");
}
