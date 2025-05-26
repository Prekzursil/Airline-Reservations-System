@echo OFF
ECHO Building and Testing Console Application...
ECHO ==========================================
ECHO.

ECHO Cleaning previous build...
mingw32-make clean
IF ERRORLEVEL 1 (
    ECHO Clean failed, but continuing...
) ELSE (
    ECHO Clean successful.
)
ECHO.

ECHO Building main console application (%TARGET%)...
mingw32-make airline_reservation_system
IF ERRORLEVEL 1 (
    ECHO Build failed for console application! Exiting.
    GOTO :EOF
) ELSE (
    ECHO Console application build successful.
)
ECHO.

ECHO Running C++ Unit Tests...
mingw32-make test
IF ERRORLEVEL 1 (
    ECHO Unit tests failed! Please check the output.
    ECHO You can still try to run the application, but it might be unstable.
    PAUSE
) ELSE (
    ECHO Unit tests passed successfully.
)
ECHO.

ECHO Launching Airline Reservation System (Console)...
ECHO Type '0' in the application menu to exit.
ECHO =================================================
ECHO.
.\\airline_reservation_system.exe

ECHO.
ECHO =================================================
ECHO Console application finished.
PAUSE
