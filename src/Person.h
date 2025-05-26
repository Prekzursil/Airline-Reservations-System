#ifndef PERSON_H
#define PERSON_H

#include <string>
#include <iostream> // For std::cout in displayDetails, or for derived classes

class Person {
protected:
    std::string name;
    int age;
    std::string personId;

public:
    // Constructors
    Person(const std::string& name = "Unknown", int age = 0, const std::string& personId = "00000");
    
    // Virtual destructor
    virtual ~Person();

    // Getters
    std::string getName() const;
    int getAge() const;
    std::string getPersonId() const;

    // Setters
    void setName(const std::string& name);
    void setAge(int age);
    // personId is typically not changed after creation, so no setter for it unless specified

    // Pure virtual function for displaying details, making Person an abstract class
    virtual void displayDetails() const = 0; 
};

#endif // PERSON_H
