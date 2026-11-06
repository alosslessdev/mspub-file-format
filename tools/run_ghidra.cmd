@echo off
rem Usage: run_ghidra.cmd <binary> <project-name> <output-decomp-dir>
rem Ghidra rejects project paths containing spaces, so the managed project lives
rem in C:\pwrk\ghproj. Output (decompiled C) may live anywhere.
setlocal
for %%i in ("%~dp0..") do set ROOT=%%~fi
set JAVA_HOME=%ROOT%\toolchain\jdk-25.0.5+8
set MAXMEM=6G
set PROJ=C:\pwrk\ghproj
if not exist "%PROJ%" mkdir "%PROJ%"
if not exist "%PROJ%" (
  echo ERROR: cannot create %PROJ%
  exit /b 2
)
call "%ROOT%\toolchain\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat" "%PROJ%" %~2 -import "%~1" -scriptPath "%ROOT%\tools\ghidra_scripts" -postScript DumpDecomp.java "%~3" -analysisTimeoutPerFile 3600 -deleteProject
endlocal
