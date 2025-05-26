# System Patterns: Airline Reservation System

This document outlines the key architectural patterns, design decisions, and OOP principles guiding the development of the Airline Reservation System.

## Core Architectural Approach
- **Modular Design:** The system will be broken down into distinct classes, each with a specific responsibility. Each class will have its own header (`.h`) and implementation (`.cpp`) file, promoting separation of concerns and maintainability.
- **Object-Oriented Programming (OOP):** The design heavily relies on OOP principles as mandated by the project requirements.
- **Console-Based Interface:** The primary user interaction will be through a command-line interface (CLI) managed by the `ReservationSystem` class.

## Key OOP Principles and Their Application

1.  **Encapsulation:**
    *   All class member variables (attributes) will be declared as `private` or `protected` to restrict direct access from outside the class.
    *   Public `getter` and `setter` methods will be provided for controlled access to these attributes where necessary. This ensures data integrity and allows for validation or other logic to be performed when attributes are accessed or modified.

2.  **Inheritance:**
    *   A `Person` base class will be created to encapsulate common attributes (name, age, ID) and behaviors.
    *   The `Customer` class will inherit from `Person`, adding customer-specific attributes like `money` and potentially overriding or extending base class methods.
    *   This promotes code reuse and establishes an "is-a" relationship (a `Customer` is a `Person`).

3.  **Polymorphism:**
    *   **Method Overriding:** The `displayDetails()` virtual function in the `Person` class will be overridden in the `Customer` class to provide specific display logic for customers.
    *   **Method Overloading:** Constructors for classes may be overloaded to allow object creation with different sets of initial parameters. Search functions (e.g., `searchCustomer` in `ReservationSystem`) might be overloaded to accept different criteria (e.g., search by ID vs. search by name).
    *   The `Person` class might be made abstract by including at least one pure virtual function (e.g., `virtual void displayDetails() = 0;` or a `getRole()` type function), forcing derived classes to implement it.

4.  **Abstraction:**
    *   The `Person` class serves as an abstraction, representing the general concept of a person involved in the system, hiding the specific details of a `Customer`.
    *   Interfaces (if used, though marked as optional in the PDF) would provide a higher level of abstraction for interactions between objects. For now, the focus is on class-based abstraction.

5.  **Constructors and Destructors:**
    *   Each class will have appropriate constructors to ensure objects are initialized in a valid state. This includes default constructors, parameterized constructors, and potentially copy constructors if deep copying is needed (especially for classes managing dynamic memory or complex resources).
    *   Destructors will be implemented for each class to handle cleanup, particularly for releasing any dynamically allocated memory to prevent memory leaks. `virtual` destructors will be used in base classes like `Person` to ensure proper cleanup when dealing with pointers to base class objects that actually point to derived class instances.

6.  **Composition/Aggregation:**
    *   The `Airplane` class will *contain* a collection of `Seat` objects (composition, as seats are integral to an airplane).
    *   The `ReservationSystem` class will *manage* collections of `Airplane`, `Customer`, and `Booking` objects (aggregation, as these objects can exist independently but are managed by the system).

## Data Structures
- **`std::vector`:** Will be the primary choice for managing collections of objects (e.g., `seats` in `Airplane`, `customers` and `bookings` in `ReservationSystem`) due to its dynamic resizing capabilities and ease of use.
- **`std::string`:** For textual data like names, IDs, etc.
- **Enums:** For representing fixed sets of values like `SeatClass` (`ECONOMY`, `BUSINESS`) and `BookingStatus` (`CONFIRMED`, `CANCELLED`).

## Error Handling and Input Validation
- Basic input validation will be implemented in the `ReservationSystem` class to handle user inputs from the console.
- Error messages will be provided to the user for invalid operations (e.g., trying to book an already booked seat, insufficient funds).

## Unique ID Generation
- A simple mechanism will be implemented within `ReservationSystem` (or a utility class/namespace) to generate unique IDs for customers, bookings, etc., possibly by combining a prefix with an incrementing counter or a timestamp.

## Extensibility Considerations (As per PDF)
- The modular design with clear class responsibilities is the primary way to ensure extensibility.
- Using base classes like `Person` allows for new types of people (e.g., `Staff`, `Pilot`) to be added by inheriting from `Person`.
- The `ReservationSystem` acts as a central coordinator, making it easier to add new high-level functionalities by adding new methods to it and potentially new interactions between existing classes.

This document will be updated if significant design patterns or architectural decisions change during development.
