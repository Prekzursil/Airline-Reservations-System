#ifndef AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H
#define AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H

#include <array>
#include <string_view>

inline bool has_expected_auto_generated_customer_name(const std::string_view name) {
    constexpr std::array<std::string_view, 5> prefixes = {
        "ApiPat_",
        "WebServiceUser_",
        "JsonGenClient_",
        "SystemPerson_",
        "BackendBot_",
    };
    for (const auto& prefix : prefixes) {
        if (name.starts_with(prefix)) {
            return true;
        }
    }
    return false;
}

#endif
