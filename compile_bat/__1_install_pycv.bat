@ECHO OFF
REM ------------------------------------------------
REM COPYRIGHT (C) 2014-2025 Mitsuo KONDOU.
REM This software is released under the MIT License.
REM https://github.com/konsan1101
REM Thank you for keeping the rules.
REM ------------------------------------------------

REM CALL __setpath.bat

ECHO; ワーク削除
IF EXIST "build"        RD "build"        /s /q
IF EXIST "dist"         RD "dist"         /s /q
IF EXIST "__pycache__"  RD "__pycache__"  /s /q
PAUSE

ECHO;
ECHO ----------
ECHO 2024/12/21
ECHO ----------
ECHO Python==3.13.1
ECHO setuptools==75.6.0
ECHO pyinstaller==6.11.1
ECHO psutil==6.1.1
ECHO websocket-client==1.8.0
ECHO numpy==2.2.0
ECHO opencv-python==4.10.0.84
ECHO opencv-contrib-python==4.10.0.84
rem  pysimplegui==5.0.7
ECHO matplotlib==3.10.0
ECHO pandas==2.2.3

ECHO;
ECHO ----------
ECHO 2025/02/16
ECHO ----------
ECHO Python==3.13.2
ECHO setuptools==75.8.0
ECHO pyinstaller==6.12.0
ECHO psutil==7.0.0
ECHO websocket-client==1.8.0
ECHO numpy==2.2.3
ECHO opencv-python==4.10.0.84
ECHO opencv-contrib-python==4.10.0.84
rem  pysimplegui==5.0.8
ECHO matplotlib==3.10.0
ECHO pandas==2.2.3

ECHO;
ECHO -----
ECHO tools
ECHO -----
rem           pip  install --upgrade pip
    python -m pip  install --upgrade pip
    python -m pip  install --upgrade wheel
    python -m pip  install --upgrade setuptools
    python -m pip  install --upgrade pyinstaller

ECHO;
ECHO -------
ECHO etc
ECHO -------
    python -m pip  install --upgrade keyboard
rem python -m pip  install --upgrade mouse 使用禁止
    python -m pip  install --upgrade screeninfo
    python -m pip  install --upgrade pyautogui
    python -m pip  install --upgrade pywin32
    python -m pip  install --upgrade comtypes
    python -m pip  install --upgrade psutil
    python -m pip  install --upgrade rainbow-logging-handler
    python -m pip  install --upgrade pycryptodome

    python -m pip  install --upgrade matplotlib
rem python -m pip  install --upgrade pysimplegui
    python -m pip  install --upgrade pillow
    python -m pip  install --upgrade pykakasi
rem ↓ use vs code
    python -m pip  install --upgrade pylint

ECHO;
ECHO -------------
ECHO communication
ECHO -------------
    python -m pip  install --upgrade requests
    python -m pip  install --upgrade requests_toolbelt
    python -m pip  install --upgrade uuid
    python -m pip  install --upgrade bs4
    python -m pip  install --upgrade pyopenssl
    python -m pip  install --upgrade feedparser
    python -m pip  install --upgrade selenium
    python -m pip  install --upgrade flask
    python -m pip  install --upgrade flask-login

ECHO;
ECHO -----
ECHO audio
ECHO -----
    python -m pip  install --upgrade wave
    python -m pip  install --upgrade sounddevice
    python -m pip  install --upgrade speechrecognition

ECHO;
ECHO ------
ECHO vision
ECHO ------
    python -m pip  install --upgrade numpy
rem python -m pip  install --upgrade numpy==2.2.0
rem python -m pip  install --upgrade opencv-python
rem python -m pip  install --upgrade opencv-contrib-python
rem python -m pip  install --upgrade opencv-python==4.9.0.80
rem python -m pip  install --upgrade opencv-contrib-python==4.9.0.80
    python -m pip  install --upgrade opencv-python==4.10.0.84
    python -m pip  install --upgrade opencv-contrib-python==4.10.0.84
    python -m pip  install --upgrade pillow
    python -m pip  install --upgrade pyzbar

ECHO;
ECHO --------
ECHO OpenAI
ECHO --------
rem python -m pip  install --upgrade httpx==0.25.0
    python -m pip  install --upgrade httpx
    python -m pip  install --upgrade openai
    python -m pip  install --upgrade tiktoken

ECHO;
ECHO ----------
ECHO IBM Watson
ECHO ----------
rem python -m pip  install --upgrade watson-developer-cloud==1.0.2
rem python -m pip  install --upgrade watson-developer-cloud
    python -m pip  install --upgrade ibm-watson
    python -m pip  install --upgrade ibm_cloud_sdk_core

rem ECHO;
rem ECHO -------------------------
rem ECHO IBM Watson,version update
rem ECHO -------------------------
rem python -m pip  uninstall -y  websocket-client
rem python -m pip  install       websocket-client==0.48.0

ECHO;
ECHO ---------------
ECHO microsoft,azure
ECHO ---------------
rem python -m pip  install --upgrade mstranslator
    python -m pip  install --upgrade cognitive_face
rem python -m pip  install --upgrade azure-storage
    python -m pip  install --upgrade azure-storage-blob==2.1.0

ECHO;
ECHO ---------------
ECHO amazon,AWS
ECHO ---------------
    python -m pip  install --upgrade boto3

ECHO;
ECHO --------
ECHO google
ECHO --------
    python -m pip  install --upgrade google-cloud-core
    python -m pip  install --upgrade google-cloud-speech
    python -m pip  install --upgrade google-cloud-translate
    python -m pip  install --upgrade google-cloud-vision
    python -m pip  install --upgrade google-api-python-client
    python -m pip  install --upgrade gtts
rem python -m pip  install --upgrade googletrans
    python -m pip  install --upgrade goslate
    python -m pip  install --upgrade ggtrans
    python -m pip  uninstall -y gtts-token
    python -m pip  install --upgrade gtts-token



rem  --------
rem  PAUSE
rem  --------

ECHO;
ECHO -------------------
ECHO pip list --outdated
ECHO -------------------
    python -m pip  list --outdated

ECHO;
ECHO Waiting...5s
ping localhost -w 1000 -n 5 >nul

ECHO;
ECHO --------
ECHO pip list
ECHO --------
rem python -m pip  list

rem  --------
     PAUSE
rem  --------
