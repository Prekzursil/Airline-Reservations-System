// cppcheck-suppress-file missingIncludeSystem
#ifndef PERSON_H
#define PERSON_H

#include <string>
#include <string_view>

class Person {
private:
    std::string name;
    int age;
    std::string personId;

public:
    // Constructors
    explicit Person(std::string_view nameValue = "Unknown", int ageValue = 0, std::string_view personIdValue = "00000");
    
    // Virtual destructor
    virtual ~Person();

    // Getters
    std::string getName() const;
    int getAge() const;
    std::string getPersonId() const;

    // Setters
    void setName(std::string_view newName);
    void setAge(int newAge);
    // personId is typically not changed after creation, so no setter for it unless specified

    // Pure virtual function for displaying details, making Person an abstract class
    virtual void displayDetails() const = 0; 
};

#endif // PERSON_H
