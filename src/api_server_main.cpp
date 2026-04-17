// cppcheck-suppress-file missingIncludeSystem
#include "api_server_main_body.h"

int main() {
    return airline_api_server_entry(std::cin, std::cout, std::cerr);
}
