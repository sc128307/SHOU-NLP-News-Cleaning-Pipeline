@echo off
:: 1. 解决中文乱码
chcp 65001 >nul

echo ==========================================
echo      NLP Corpus Cleaning Tool Launcher
echo ==========================================
echo.

:: 2. 尝试自动激活 Conda 环境
:: 假设用户安装了 Anaconda，并且环境名叫 nlp-corpus
:: 如果您的组员用的是 base 或者其他名字，他们可能需要手动修改这里，或者手动激活

echo 正在尝试激活 Conda 环境 (nlp-corpus)...
call conda activate nlp-corpus 2>nul

if %errorlevel% neq 0 (
    echo [警告] 无法自动激活 'nlp-corpus' 环境。
    echo 请确认您已安装 Anaconda 并在 Anaconda Prompt 中运行此脚本，
    echo 或者手动激活您的 Python 环境。
    echo.
    echo 正在尝试使用系统默认 Python...
) else (
    echo [成功] 已激活 nlp-corpus 环境。
)

echo.
echo 正在检查依赖库...
pip install ttkbootstrap pandas openpyxl striprtf transformers torch nltk >nul 2>&1

echo 正在启动图形界面...
python pipeline_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序崩溃或无法启动。
    echo 请检查错误信息，或联系开发者。
    pause
)