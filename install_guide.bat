@echo off
rem Windows PowerShell版本的安装脚本
rem 重启后在PowerShell中运行此脚本

echo ================================================
echo 重启后WSL + Node.js + Codex安装指南
echo ================================================
echo.

echo 步骤1：启动WSL
echo ----------------------------------------
echo 请在PowerShell中运行：
echo wsl
echo.
echo 等待WSL启动完成后，继续下一步...
echo.

echo 步骤2：在WSL中执行安装
echo ----------------------------------------
echo 在WSL shell中，导航到项目目录并运行：
echo cd /mnt/e/OneDrive/Documents/GitHub/WaterNet
echo bash install_nodejs_codex.sh
echo.

echo 或者手动执行以下命令：
echo.
echo 1. 安装nvm：
echo curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh ^| bash
echo.
echo 2. 重新加载shell或开启新的WSL会话
echo.
echo 3. 安装Node.js 22：
echo nvm install 22
echo.
echo 4. 安装Codex：
echo npm i -g @openai/codex
echo.
echo 5. 运行Codex：
echo codex
echo.

echo ================================================
echo 注意事项：
echo ================================================
echo 1. 确保计算机已重新启动
echo 2. WSL功能已完全启用
echo 3. 网络连接正常
echo 4. 如果遇到权限问题，可能需要使用sudo
echo ================================================

pause