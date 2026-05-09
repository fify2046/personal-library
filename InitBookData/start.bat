@echo off
chcp 65001 >nul
title 电子书内容提取工具
cd /d "%~dp0"
python main.py
