@echo off
chcp 65001 >nul
title 图书管理系统

echo ========================================
echo   启动图书管理系统
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 启动后端服务...
start "Backend" cmd /k "cd /d "%~dp0backend" && python main.py"

timeout /t 3 /nobreak >nul

echo [2/3] 启动前端服务...
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   服务已启动！
echo ========================================
echo   后端: http://localhost:8000
echo   前端: http://localhost:3000
echo   API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键打开浏览器访问...
pause >nul

start http://localhost:3000
