#ifndef AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H
#define AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H

#include <algorithm>
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
    return std::ranges::any_of(prefixes, [name](std::string_view prefix) {
        return name.starts_with(prefix);
    });
}

#endif
