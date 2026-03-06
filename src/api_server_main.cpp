// cppcheck-suppress-file missingIncludeSystem
#include <httplib.h>
#include <nlohmann/json.hpp>

#include <iostream>
#include <string>
#include <vector>

#include "Airplane.h"
#include "Booking.h"
#include "Customer.h"
#include "ReservationSystem.h"
#include "Seat.h"

using json = nlohmann::json;

void to_json(json& j, const Seat& s) {
    j = json{
        {"seatId", s.getSeatId()},
        {"isBooked", s.getIsBooked()},
        {"price", s.getPrice()},
        {"seatClass", s.getSeatClassString()},
    };
}

void to_json(json& j, const Airplane& p) {
    j = json{
        {"flightNumber", p.getFlightNumber()},
        {"capacity", p.getCapacity()},
        {"bookedSeatsCount", p.getBookedSeatsCount()},
        {"isFull", p.isFull()},
    };
}

void to_json(json& j, const Customer& c) {
    j = json{
        {"personId", c.getPersonId()},
        {"name", c.getName()},
        {"age", c.getAge()},
        {"money", c.getMoney()},
    };
}

void to_json(json& j, const Booking& b) {
    j = json{
        {"bookingId", b.getBookingId()},
        {"customerId", b.getCustomerId()},
        {"flightNumber", b.getFlightNumber()},
        {"seatId", b.getSeatId()},
        {"bookingDate", b.getBookingDateString()},
        {"status", b.getStatusString()},
    };
}

constexpr const char* kJsonMimeType = "application/json";
constexpr int kServerPort = 8080;
using ServerListenCallback = bool (*)(httplib::Server&, const char*, int);

bool listen_on_host(httplib::Server& server, const char* host, int port) {
    return server.listen(host, port);
}

void set_common_headers(httplib::Response& res) {
    res.set_header("Access-Control-Allow-Origin", "*");
    res.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization");
    res.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
}

void respond_json(httplib::Response& res, const json& payload, int status = 200) {
    set_common_headers(res);
    res.status = status;
    res.set_content(payload.dump(4), kJsonMimeType);
}

bool contains_fragment(std::string_view text, std::string_view needle) {
    if (needle.empty()) {
        return true;
    }
    if (needle.size() > text.size()) {
        return false;
    }

    const size_t last_start = text.size() - needle.size();
    for (size_t index = 0; index <= last_start; ++index) {
        if (text.substr(index, needle.size()) == needle) {
            return true;
        }
    }
    return false;
}

int booking_error_status(const std::string& message) {
    if (contains_fragment(message, "not found")) {
        return 404;
    }
    if (contains_fragment(message, "already booked")) {
        return 409;
    }
    if (contains_fragment(message, "Insufficient funds")) {
        return 402;
    }
    return 400;
}

int cancel_error_status(const std::string& message) {
    if (contains_fragment(message, "not found")) {
        return 404;
    }
    if (contains_fragment(message, "already cancelled")) {
        return 409;
    }
    return 500;
}

int swap_error_status(const std::string& message) {
    if (contains_fragment(message, "not found") || contains_fragment(message, "not confirmed")) {
        return 404;
    }
    if (contains_fragment(message, "Cannot swap a booking with itself") ||
        contains_fragment(message, "only supported for bookings on the same flight")) {
        return 400;
    }
    return 500;
}

const Booking* find_confirmed_booking_for_seat(
    const std::vector<Booking>& bookings,
    std::string_view flight_number,
    std::string_view seat_id) {
    for (const Booking& booking : bookings) {
        if (std::string_view{booking.getFlightNumber()} == flight_number &&
            std::string_view{booking.getSeatId()} == seat_id &&
            booking.getStatus() == BookingStatus::CONFIRMED) {
            return &booking;
        }
    }
    return nullptr;
}

json build_airplane_details(const ReservationSystem& airline_system, const Airplane& plane) {
    json details = {
        {"flightNumber", plane.getFlightNumber()},
        {"capacity", plane.getCapacity()},
        {"bookedSeatsCount", plane.getBookedSeatsCount()},
        {"isFull", plane.isFull()},
        {"seats", json::array()},
    };

    const auto& all_bookings = airline_system.getBookingsForTest();
    const std::string flight_number = plane.getFlightNumber();
    for (const auto& seat_obj : plane.getAllSeats()) {
        json seat_json;
        to_json(seat_json, seat_obj);

        if (seat_obj.getIsBooked()) {
            if (const Booking* booking =
                    find_confirmed_booking_for_seat(all_bookings, flight_number, seat_obj.getSeatId());
                booking != nullptr) {
                seat_json["bookedByCustomerId"] = booking->getCustomerId();
                seat_json["bookingId"] = booking->getBookingId();
            }
        }

        details["seats"].push_back(seat_json);
    }

    return details;
}

json build_customer_details(const ReservationSystem& airline_system, const Customer& customer) {
    json customer_json;
    to_json(customer_json, customer);

    json bookings_json = json::array();
    for (const auto& booking : airline_system.getBookingsForTest()) {
        if (booking.getCustomerId() == customer.getPersonId()) {
            bookings_json.push_back(booking);
        }
    }
    customer_json["bookings"] = bookings_json;
    return customer_json;
}

void handle_list_airplanes(const ReservationSystem& airline_system, const httplib::Request&, httplib::Response& res) {
    json airplane_list = json::array();
    for (const auto& plane : airline_system.getAirplanesForTest()) {
        json plane_json;
        to_json(plane_json, plane);
        airplane_list.push_back(plane_json);
    }
    respond_json(res, airplane_list);
}

void handle_airplane_details(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    if (const Airplane* plane = airline_system.findAirplaneByFlightNumber(req.matches[1].str()); plane != nullptr) {
        respond_json(res, build_airplane_details(airline_system, *plane));
        return;
    }

    respond_json(res, json{{"error", "Airplane not found"}}, 404);
}

void handle_list_customers(const ReservationSystem& airline_system, const httplib::Request&, httplib::Response& res) {
    respond_json(res, json(airline_system.getCustomersForTest()));
}

void handle_customer_details(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    if (const Customer* customer = airline_system.findCustomerById(req.matches[1].str()); customer != nullptr) {
        respond_json(res, build_customer_details(airline_system, *customer));
        return;
    }

    respond_json(res, json{{"error", "Customer not found"}}, 404);
}

void handle_list_bookings(const ReservationSystem& airline_system, const httplib::Request&, httplib::Response& res) {
    respond_json(res, json(airline_system.getBookingsForTest()));
}

void handle_create_customer(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    try {
        const json body = json::parse(req.body);
        const std::string name = body.value("name", "DefaultName");
        const int age = body.value("age", 0);
        const double money = body.value("money", 0.0);
        const bool auto_generate = body.value("autoGenerate", false);

        if (Customer* new_customer = airline_system.addCustomerInternal(name, age, money, auto_generate);
            new_customer != nullptr) {
            respond_json(res, json(*new_customer), 201);
            return;
        }

        respond_json(res, json{{"error", "Failed to add customer internally"}}, 500);
    } catch (const json::exception& error) {
        respond_json(res, json{{"error", "Error processing customer data: " + std::string(error.what())}}, 400);
    }
}

void handle_create_booking(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    try {
        const json body = json::parse(req.body);
        const std::string customer_id = body.at("customerId").get<std::string>();
        const std::string flight_number = body.at("flightNumber").get<std::string>();
        const std::string seat_id = body.at("seatId").get<std::string>();

        std::string error_message;
        if (Booking* booking = airline_system.createBookingInternal(customer_id, flight_number, seat_id, error_message);
            booking != nullptr) {
            respond_json(res, json(*booking), 201);
            return;
        }

        respond_json(res, json{{"error", error_message}}, booking_error_status(error_message));
    } catch (const json::exception& error) {
        respond_json(res, json{{"error", "Error processing booking data: " + std::string(error.what())}}, 400);
    }
}

void handle_cancel_booking(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    std::string error_message;

    if (const bool success = airline_system.cancelBookingInternal(req.matches[1].str(), error_message); !success) {
        respond_json(res, json{{"error", error_message}}, cancel_error_status(error_message));
        return;
    }

    respond_json(res, json{{"message", error_message}});
}

void handle_swap_booking_seats(ReservationSystem& airline_system, const httplib::Request& req, httplib::Response& res) {
    try {
        const json body = json::parse(req.body);
        const std::string booking_id_1 = body.at("bookingId1").get<std::string>();
        const std::string booking_id_2 = body.at("bookingId2").get<std::string>();

        std::string error_message;
        if (const bool success = airline_system.swapSeatsInternal(booking_id_1, booking_id_2, error_message); !success) {
            respond_json(res, json{{"error", error_message}}, swap_error_status(error_message));
            return;
        }

        respond_json(res, json{{"message", error_message}});
    } catch (const json::exception& error) {
        respond_json(res, json{{"error", "Error processing seat swap request: " + std::string(error.what())}}, 400);
    }
}

void register_routes(httplib::Server& server, ReservationSystem& airline_system) {
    server.Get("/api/airplanes", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_list_airplanes(airline_system, req, res);
    });
    server.Get(R"(/api/airplanes/(\w+))", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_airplane_details(airline_system, req, res);
    });

    server.Get("/api/customers", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_list_customers(airline_system, req, res);
    });
    server.Get(R"(/api/customers/(\w+))", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_customer_details(airline_system, req, res);
    });

    server.Get("/api/bookings", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_list_bookings(airline_system, req, res);
    });
    server.Post("/api/customers", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_create_customer(airline_system, req, res);
    });
    server.Post("/api/bookings", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_create_booking(airline_system, req, res);
    });
    server.Delete(R"(/api/bookings/([A-Za-z0-9\-]+))",
                  [&airline_system](const httplib::Request& req, httplib::Response& res) {
                      handle_cancel_booking(airline_system, req, res);
                  });
    server.Post("/api/bookings/swap", [&airline_system](const httplib::Request& req, httplib::Response& res) {
        handle_swap_booking_seats(airline_system, req, res);
    });

    server.Options(R"((.*))", [](const httplib::Request&, httplib::Response& res) {
        set_common_headers(res);
        res.status = 204;
    });
}

int run_api_server(
    ReservationSystem& airline_system,
    httplib::Server& server,
    std::ostream& out,
    std::ostream& err,
    ServerListenCallback listen_callback = listen_on_host) {
    register_routes(server, airline_system);

    server.set_base_dir("./");
    server.set_logger([](const httplib::Request& req, const httplib::Response& res) {
        std::cout << "HTTP " << req.method << " " << req.path << " -> " << res.status << std::endl;
    });

    out << "Starting API server on http://localhost:" << kServerPort << "..." << std::endl;
    if (!listen_callback(server, "0.0.0.0", kServerPort)) {
        err << "Failed to start server!" << std::endl;
        return 1;
    }

    return 0;
}

int main() {
    ReservationSystem airline_system(std::cin, std::cout);
    httplib::Server server;
    return run_api_server(airline_system, server, std::cout, std::cerr);
}
