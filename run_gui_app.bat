@echo OFF
TITLE Airline Reservation System - GUI Launcher

ECHO Building and Testing C++ API Server...
ECHO =====================================
ECHO.

ECHO Cleaning previous build...
mingw32-make clean
IF ERRORLEVEL 1 (
    ECHO Clean failed, but continuing...
) ELSE (
    ECHO Clean successful.
)
ECHO.

ECHO Building C++ API server (airline_api_server.exe)...
mingw32-make airline_api_server
IF ERRORLEVEL 1 (
    ECHO Build failed for API server! Exiting.
    GOTO :EOF
) ELSE (
    ECHO API server build successful.
)
ECHO.

ECHO Running C++ Unit Tests...
mingw32-make test
IF ERRORLEVEL 1 (
    ECHO Unit tests failed! Please check the output.
    ECHO The API server might be unstable.
    PAUSE
) ELSE (
    ECHO Unit tests passed successfully.
)
ECHO.

ECHO Starting C++ API Server in a new window...
ECHO The API server will run at http://localhost:8080
ECHO Please keep this new window open while using the GUI.
ECHO =====================================================
ECHO.
START "C++ API Server" .\\airline_api_server.exe

ECHO Waiting for API server to initialize (5 seconds)...
TIMEOUT /T 5 /NOBREAK > NUL
ECHO.

ECHO Starting React Frontend Development Server...
ECHO This will open the GUI in your web browser.
ECHO ============================================
ECHO.
cd airline-gui
npm start

ECHO.
ECHO =====================================================
ECHO React development server process initiated.
ECHO If the browser doesn't open automatically, navigate to http://localhost:3000 (or the port indicated above).
ECHO Close the C++ API Server window when done.
PAUSE
