@echo off
echo Building InFac P4 application...
echo.
echo NOTE: Since the "inference" library includes enormous machine learning dependencies,
echo the build process will take a significant amount of time (15-30 minutes).
echo Please be patient while PyInstaller collects all necessary files.
echo.
echo Furthermore, the resulting executable might be very large (400MB - 1GB).
echo When you launch the resulting main.exe, it may seem like "it does nothing"
echo for 10-20 seconds. This is because Windows has to extract the massive executable
echo into a temporary directory before it can run.
echo.
echo (TIP: If you want faster startup times in the future, consider using Pyinstaller
echo without the --onefile flag, which creates a folder instead of a single executable file).
echo.
call venv\Scripts\activate.bat
pyinstaller main.spec --clean
echo.
echo Build complete! Check the "dist" folder.
pause
