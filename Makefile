# Compiler and flags
CXX = g++
BASE_CXXFLAGS = -std=c++17 -Wall -Wextra # Changed from c++11 to c++17
RELEASE_CXXFLAGS = $(BASE_CXXFLAGS) -O2
DEBUG_CXXFLAGS = $(BASE_CXXFLAGS) -g
COVERAGE_CXXFLAGS = $(DEBUG_CXXFLAGS) -fprofile-arcs -ftest-coverage # For gcov

# Default to debug build for CXXFLAGS
CXXFLAGS = $(DEBUG_CXXFLAGS)

# Source files directories
SRCDIR = src
TESTDIR = tests
THIRDPARTYDIR = third_party

# Object files directory
OBJDIR = obj
TEST_OBJDIR = $(OBJDIR)/tests

# Executable names
TARGET = airline_reservation_system
API_TARGET = airline_api_server
TEST_TARGET = run_tests_executable

# Google Test paths
GTEST_DIR = $(THIRDPARTYDIR)/googletest
GTEST_BUILD_DIR = $(GTEST_DIR)/build
GTEST_INCLUDE = -isystem $(GTEST_DIR)/googletest/include -isystem $(GTEST_DIR)/googlemock/include
GTEST_LIBS_DIR = $(GTEST_BUILD_DIR)/lib
GTEST_LIBS = -L$(GTEST_LIBS_DIR) -lgtest -lgtest_main -pthread

# Core application source files (excluding all main files)
CORE_APP_SOURCES = $(filter-out $(SRCDIR)/main.cpp $(SRCDIR)/api_server_main.cpp, $(wildcard $(SRCDIR)/*.cpp))
CORE_APP_OBJECTS = $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(CORE_APP_SOURCES))

# Console App specific main
CONSOLE_MAIN_SOURCE = $(SRCDIR)/main.cpp
CONSOLE_MAIN_OBJECT = $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(CONSOLE_MAIN_SOURCE))

# API Server specific main
API_MAIN_SOURCE = $(SRCDIR)/api_server_main.cpp
API_MAIN_OBJECT = $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(API_MAIN_SOURCE))

# Test Source files
TEST_SOURCES = $(wildcard $(TESTDIR)/*.cpp)
TEST_OBJECTS = $(patsubst $(TESTDIR)/%.cpp,$(TEST_OBJDIR)/%.o,$(TEST_SOURCES))

# Default target
all: $(TARGET) $(API_TARGET)

# Link the main console executable
$(TARGET): $(CORE_APP_OBJECTS) $(CONSOLE_MAIN_OBJECT)
	$(CXX) $(CXXFLAGS) -o $@ $^

# Link the API server executable
$(API_TARGET): $(CORE_APP_OBJECTS) $(API_MAIN_OBJECT)
ifeq ($(OS),Windows_NT)
	$(CXX) $(CXXFLAGS) -o $@ $^ -lws2_32 -lwsock32
# Windows specific socket libraries
else
	$(CXX) $(CXXFLAGS) -o $@ $^ -pthread
endif

# Link the test executable
$(TEST_TARGET): $(CORE_APP_OBJECTS) $(TEST_OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(GTEST_LIBS)

# Compile core application source files (and specific main files) into object files
$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(CXXFLAGS) $(GTEST_INCLUDE) -I$(SRCDIR) -c -o $@ $<

# Compile test source files into object files
$(TEST_OBJDIR)/%.o: $(TESTDIR)/%.cpp | $(TEST_OBJDIR)
	$(CXX) $(CXXFLAGS) $(GTEST_INCLUDE) -I$(SRCDIR) -c -o $@ $<

# Create object directories if they don't exist
# Use Windows-compatible directory creation
ifeq ($(OS),Windows_NT)
MKDIR_P = if not exist $(subst /,\,$(1)) mkdir $(subst /,\,$(1))
else
MKDIR_P = mkdir -p $(1)
endif

$(OBJDIR):
	$(call MKDIR_P,$(OBJDIR))

$(TEST_OBJDIR):
	$(call MKDIR_P,$(TEST_OBJDIR))

# Target to run tests
test: CXXFLAGS = $(COVERAGE_CXXFLAGS) # Use coverage flags for test build
test: $(TEST_TARGET)
	./$(TEST_TARGET)

# Target to generate coverage report (basic gcov, lcov would make it nicer)
coverage: CXXFLAGS = $(COVERAGE_CXXFLAGS)
coverage: $(TEST_TARGET) # Ensure tests are built with coverage flags
	./$(TEST_TARGET) # Run tests to generate .gcda files
	@echo "Generating gcov reports for application source files..."
ifeq ($(OS),Windows_NT)
	@FOR %%F IN ($(subst /,\,$(CORE_APP_SOURCES))) DO ( \
		echo Processing %%F for coverage... && \
		gcov -r -p -o $(OBJDIR) %%F \
	)
else
	@for src_file in $(CORE_APP_SOURCES); do \
		echo "Processing $$src_file for coverage..."; \
		gcov -r -p -o $(OBJDIR) $$src_file; \
	done
endif
	@echo "Coverage report generation attempted. Check .gcov files (e.g., src#Airplane.cpp.gcov) in the obj directory or alongside source files."
	@echo "For HTML reports, use lcov: lcov --capture --directory . --output-file coverage.info && genhtml coverage.info --output-directory coverage_report"


# Clean up build files
clean:
ifeq ($(OS),Windows_NT)
	-del $(subst /,\,$(TARGET)) 2>nul
	-del $(subst /,\,$(API_TARGET)) 2>nul
	-del $(subst /,\,$(TEST_TARGET)) 2>nul
	-del $(subst /,\,$(TARGET)).exe 2>nul
	-del $(subst /,\,$(API_TARGET)).exe 2>nul
	-del $(subst /,\,$(TEST_TARGET)).exe 2>nul
	-if exist $(subst /,\,$(OBJDIR)) rmdir /s /q $(subst /,\,$(OBJDIR))
	-del $(subst /,\,$(SRCDIR))\*.gcda 2>nul
	-del $(subst /,\,$(SRCDIR))\*.gcno 2>nul
	-del $(subst /,\,$(TESTDIR))\*.gcda 2>nul
	-del $(subst /,\,$(TESTDIR))\*.gcno 2>nul
	-del *.gcda 2>nul
	-del *.gcno 2>nul
	-del $(subst /,\,$(OBJDIR))\*.gcov 2>nul
	-if exist $(subst /,\,$(TEST_OBJDIR)) del $(subst /,\,$(TEST_OBJDIR))\*.gcov 2>nul
	-del coverage.info 2>nul
	-if exist coverage_report rmdir /s /q coverage_report
else
	rm -f $(TARGET) $(API_TARGET) $(TEST_TARGET)
	rm -rf $(OBJDIR)
	rm -f $(SRCDIR)/*.gcda $(SRCDIR)/*.gcno $(TESTDIR)/*.gcda $(TESTDIR)/*.gcno
	rm -f *.gcda *.gcno
	rm -f $(OBJDIR)/*.gcov $(TEST_OBJDIR)/*.gcov
	rm -f coverage.info
	rm -rf coverage_report
endif

# Phony targets
.PHONY: all clean test coverage
