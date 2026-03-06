#include "gtest/gtest.h"
#include "../src/Person.h"

class ConcretePerson : public Person {
public:
    ConcretePerson(const std::string& name = "Unknown", int age = 0, const std::string& personId = "00000")
        : Person(name, age, personId) {}

    void displayDetails() const override {}
};

class PersonTest : public ::testing::Test {
protected:
    ConcretePerson p1{"Alice", 30, "P123"};
    ConcretePerson pDefault{};
};

TEST_F(PersonTest, DefaultConstructor) {
    EXPECT_EQ(pDefault.getName(), "Unknown");
    EXPECT_EQ(pDefault.getAge(), 0);
    EXPECT_EQ(pDefault.getPersonId(), "00000");
}

TEST_F(PersonTest, ParameterizedConstructor) {
    EXPECT_EQ(p1.getName(), "Alice");
    EXPECT_EQ(p1.getAge(), 30);
    EXPECT_EQ(p1.getPersonId(), "P123");
}

TEST_F(PersonTest, SetName) {
    p1.setName("Bob");
    EXPECT_EQ(p1.getName(), "Bob");
}

TEST_F(PersonTest, SetAge) {
    p1.setAge(25);
    EXPECT_EQ(p1.getAge(), 25);
}

TEST_F(PersonTest, SetAgeInvalid) {
    const int originalAge = p1.getAge();
    p1.setAge(-5);
    EXPECT_EQ(p1.getAge(), originalAge);
}

TEST_F(PersonTest, Getters) {
    EXPECT_EQ(p1.getName(), "Alice");
    EXPECT_EQ(p1.getAge(), 30);
    EXPECT_EQ(p1.getPersonId(), "P123");
}
