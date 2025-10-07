# PowerShell版本的Node.js和Codex安装脚本
# 适用于Windows环境直接安装

Write-Host "================================================" -ForegroundColor Green
Write-Host "Windows环境下安装Node.js和Codex" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# 检查是否有管理员权限
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "警告: 建议以管理员身份运行此脚本" -ForegroundColor Yellow
}

# 步骤1：检查并安装winget（如果需要）
Write-Host ""
Write-Host "步骤1：检查Windows包管理器 (winget)..." -ForegroundColor Cyan
Write-Host "----------------------------------------"

try {
    $wingetVersion = winget --version
    Write-Host "winget已安装: $wingetVersion" -ForegroundColor Green
} catch {
    Write-Host "winget未安装，请从Microsoft Store安装'应用安装程序'" -ForegroundColor Red
    Write-Host "或访问: https://github.com/microsoft/winget-cli/releases" -ForegroundColor Yellow
    exit 1
}

# 步骤2：安装Node.js
Write-Host ""
Write-Host "步骤2：安装Node.js..." -ForegroundColor Cyan
Write-Host "----------------------------------------"

try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Node.js已安装: $nodeVersion" -ForegroundColor Green
    } else {
        throw "Not installed"
    }
} catch {
    Write-Host "正在安装Node.js..."
    try {
        winget install OpenJS.NodeJS -e --accept-source-agreements --accept-package-agreements
        Write-Host "Node.js安装完成" -ForegroundColor Green
        
        # 刷新环境变量
        $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = $machinePath + ";" + $userPath
        
        Start-Sleep -Seconds 3
        $nodeVersion = node --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Node.js版本: $nodeVersion" -ForegroundColor Green
        } else {
            Write-Host "Node.js安装完成，但需要重新启动PowerShell才能使用" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Node.js安装失败" -ForegroundColor Red
        Write-Host "请手动从 https://nodejs.org/ 下载并安装" -ForegroundColor Yellow
        exit 1
    }
}

# 检查npm
try {
    $npmVersion = npm --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "npm版本: $npmVersion" -ForegroundColor Green
    } else {
        Write-Host "npm未找到，Node.js安装可能有问题" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "npm未找到，Node.js安装可能有问题" -ForegroundColor Red
    exit 1
}

# 步骤3：安装Codex
Write-Host ""
Write-Host "步骤3：安装OpenAI Codex..." -ForegroundColor Cyan
Write-Host "----------------------------------------"

try {
    $codexCheck = npm list -g @openai/codex 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "@openai/codex已安装" -ForegroundColor Green
    } else {
        throw "Not installed"
    }
} catch {
    Write-Host "正在安装@openai/codex..."
    try {
        npm install -g @openai/codex
        if ($LASTEXITCODE -eq 0) {
            Write-Host "@openai/codex安装成功" -ForegroundColor Green
        } else {
            throw "Installation failed"
        }
    } catch {
        Write-Host "@openai/codex安装失败" -ForegroundColor Red
        Write-Host "可能的原因:" -ForegroundColor Yellow
        Write-Host "1. 网络连接问题" -ForegroundColor Yellow
        Write-Host "2. npm权限问题" -ForegroundColor Yellow
        Write-Host "3. @openai/codex包可能不存在或已更名" -ForegroundColor Yellow
        
        Write-Host ""
        Write-Host "尝试替代方案：安装其他AI编程工具..." -ForegroundColor Cyan
        try {
            # 尝试安装GitHub Copilot CLI
            npm install -g @githubnext/github-copilot-cli
            if ($LASTEXITCODE -eq 0) {
                Write-Host "已安装GitHub Copilot CLI作为替代" -ForegroundColor Green
            }
        } catch {
            Write-Host "替代工具安装也失败" -ForegroundColor Red
        }
    }
}

# 安装完成
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "安装完成!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "安装总结:" -ForegroundColor White

try {
    $nodeVer = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Node.js: $nodeVer" -ForegroundColor Green
    }
} catch {
    Write-Host "Node.js: 可能需要重启PowerShell" -ForegroundColor Yellow
}

try {
    $npmVer = npm --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "npm: $npmVer" -ForegroundColor Green
    }
} catch {
    Write-Host "npm: 可能需要重启PowerShell" -ForegroundColor Yellow
}

try {
    $codexCheck = npm list -g @openai/codex 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "@openai/codex: 已安装" -ForegroundColor Green
        Write-Host ""
        Write-Host "现在您可以运行以下命令启动Codex:" -ForegroundColor White
        Write-Host "codex" -ForegroundColor Yellow
    } else {
        Write-Host "@openai/codex: 安装可能有问题" -ForegroundColor Yellow
    }
} catch {
    Write-Host "@openai/codex: 安装可能有问题" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "如果遇到问题，请检查:" -ForegroundColor White
Write-Host "1. 网络连接是否正常" -ForegroundColor Yellow
Write-Host "2. 是否以管理员身份运行" -ForegroundColor Yellow
Write-Host "3. npm全局包安装权限" -ForegroundColor Yellow
Write-Host "4. 可能需要重启PowerShell或重新加载环境变量" -ForegroundColor Yellow

Write-Host ""
Write-Host "按回车键退出..."
Read-Host