@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
for %%I in ("%ROOT_DIR%") do set ROOT_DIR=%%~fI

set PROTO_DIR=%ROOT_DIR%\proto
set OUT_DIR=%ROOT_DIR%\generated\python

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

python -m grpc_tools.protoc ^
  -I "%PROTO_DIR%" ^
  --python_out="%OUT_DIR%" ^
  "%PROTO_DIR%\ego\v1\ego_common.proto" ^
  "%PROTO_DIR%\ego\v1\ego_config.proto" ^
  "%PROTO_DIR%\ego\v1\ego_data.proto" ^
  "%PROTO_DIR%\ego\v1\ego_control.proto"

if errorlevel 1 (
    echo Python protobuf generation failed.
    exit /b 1
)

echo Generated Python protobuf files into:
echo %OUT_DIR%

endlocal