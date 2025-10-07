#!/bin/bash

# WSL重启后Node.js和Codex安装脚本
# 使用方法：在WSL中运行 bash install_nodejs_codex.sh

echo "================================================"
echo "开始在WSL中安装Node.js和Codex"
echo "================================================"

# 检查是否在WSL环境中
if [[ ! -f /proc/version ]] || ! grep -q Microsoft /proc/version 2>/dev/null; then
    echo "❌ 错误：此脚本需要在WSL环境中运行"
    echo "请先运行：wsl"
    exit 1
fi

echo "✅ 已确认在WSL环境中"

# 步骤1：安装nvm
echo ""
echo "步骤1：安装Node Version Manager (nvm)..."
echo "----------------------------------------"

if command -v nvm &> /dev/null; then
    echo "✅ nvm已安装"
else
    echo "正在下载并安装nvm..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh | bash
    
    # 重新加载bash配置
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    if command -v nvm &> /dev/null; then
        echo "✅ nvm安装成功"
    else
        echo "❌ nvm安装失败，请手动安装"
        exit 1
    fi
fi

# 步骤2：安装Node.js 22
echo ""
echo "步骤2：安装Node.js 22..."
echo "----------------------------------------"

# 确保nvm可用
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "正在安装Node.js 22..."
nvm install 22

if nvm use 22; then
    echo "✅ Node.js 22安装并设置成功"
    echo "Node.js版本：$(node --version)"
    echo "npm版本：$(npm --version)"
else
    echo "❌ Node.js 22安装失败"
    exit 1
fi

# 步骤3：安装Codex
echo ""
echo "步骤3：安装OpenAI Codex..."
echo "----------------------------------------"

if npm list -g @openai/codex &> /dev/null; then
    echo "✅ @openai/codex已安装"
else
    echo "正在安装@openai/codex..."
    if npm install -g @openai/codex; then
        echo "✅ @openai/codex安装成功"
    else
        echo "❌ @openai/codex安装失败"
        echo "可能的原因："
        echo "1. 网络连接问题"
        echo "2. npm权限问题"
        echo "3. @openai/codex包可能不存在或已更名"
        exit 1
    fi
fi

# 安装完成
echo ""
echo "================================================"
echo "🎉 安装完成！"
echo "================================================"
echo ""
echo "安装总结："
echo "✅ WSL环境：已确认"
echo "✅ nvm：$(nvm --version 2>/dev/null || echo '已安装')"
echo "✅ Node.js：$(node --version)"
echo "✅ npm：$(npm --version)"
echo "✅ @openai/codex：已安装"
echo ""
echo "现在您可以运行以下命令启动Codex："
echo "codex"
echo ""
echo "如果遇到问题，请检查："
echo "1. 确保在WSL环境中运行"
echo "2. 检查网络连接"
echo "3. 确认npm全局包安装权限"