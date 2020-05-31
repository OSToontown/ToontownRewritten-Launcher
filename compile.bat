@echo off
rmdir bin /s /q
pyinstaller --onefile main.py
rmdir build /s /q
REN dist bin
XCOPY /E /I resources bin\resources\
PAUSE