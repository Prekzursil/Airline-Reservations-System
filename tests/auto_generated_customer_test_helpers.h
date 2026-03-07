#ifndef AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H
#define AUTO_GENERATED_CUSTOMER_TEST_HELPERS_H

#include <string_view>

inline bool has_expected_auto_generated_customer_name(const std::string_view name) {
    return name.starts_with("ApiPat_") ||
           name.starts_with("WebServiceUser_") ||
           name.starts_with("JsonGenClient_") ||
           name.starts_with("SystemPerson_") ||
           name.starts_with("BackendBot_");
}

#endif
