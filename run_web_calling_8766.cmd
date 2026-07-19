@echo off
cd /d "%~dp0"
set PYTHONPATH=src
python src\web_calling\web_call_server.py --host 127.0.0.1 --port 8766 --stt-provider faster_whisper --tts-provider windows_sapi
