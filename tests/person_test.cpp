#include "gtest/gtest.h"
#include "../src/Person.h" // Adjust path to Person.h

// A minimal concrete class derived from Person to test Person's functionalities
class ConcretePerson : public Person {
public:
    ConcretePerson(const std::string& name = "Unknown", int age = 0, const std::string& personId = "00000")
        : Person(name, age, personId) {}

    // Provide an implementation for the pure virtual function
    void displayDetails() const override {
        // Minimal implementation for testing purposes, or can be empty
        // std::cout << "ConcretePerson displayDetails called." << std::endl;
    }
};

// Test fixture for Person tests (optional, but good practice for setup/teardown)
class PersonTest : public ::testing::Test {
protected:
    ConcretePerson* p1;
    ConcretePerson* p_default;

    void SetUp() override {
        p1 = new ConcretePerson("Alice", 30, "P123");
        p_default = new ConcretePerson(); // Test default constructor
    }

    void TearDown() override {
        delete p1;
        delete p_default;
        p1 = nullptr;
        p_default = nullptr;
    }
};

// Test case for the default constructor
TEST_F(PersonTest, DefaultConstructor) {
    EXPECT_EQ(p_default->getName(), "Unknown");
    EXPECT_EQ(p_default->getAge(), 0);
    EXPECT_EQ(p_default->getPersonId(), "00000");
}

// Test case for the parameterized constructor
TEST_F(PersonTest, ParameterizedConstructor) {
    EXPECT_EQ(p1->getName(), "Alice");
    EXPECT_EQ(p1->getAge(), 30);
    EXPECT_EQ(p1->getPersonId(), "P123");
}

// Test case for setName
TEST_F(PersonTest, SetName) {
    p1->setName("Bob");
    EXPECT_EQ(p1->getName(), "Bob");
}

// Test case for setAge
TEST_F(PersonTest, SetAge) {
    p1->setAge(25);
    EXPECT_EQ(p1->getAge(), 25);
}

// Test case for setAge with invalid input (negative age)
TEST_F(PersonTest, SetAgeInvalid) {
    int originalAge = p1->getAge();
    p1->setAge(-5); // Person.cpp currently ignores invalid age, so it should remain unchanged
    EXPECT_EQ(p1->getAge(), originalAge); 
}

// Test case for getters
TEST_F(PersonTest, Getters) {
    EXPECT_EQ(p1->getName(), "Alice");
    EXPECT_EQ(p1->getAge(), 30);
    EXPECT_EQ(p1->getPersonId(), "P123");
}

// The pure virtual displayDetails() is not directly testable in Person,
// but its concrete implementation in derived classes (like Customer) will be tested.
// The destructor is tested implicitly when objects go out of scope or are deleted.
