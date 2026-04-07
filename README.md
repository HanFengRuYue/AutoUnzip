<p align="center">
  <img src="assets/app_icon.png" width="120" alt="AutoUnzip logo">
</p>

<h1 align="center">AutoUnzip</h1>

<p align="center">自动识别伪装后缀、分卷和密码压缩包，并持续解压到最终文件夹。</p>

<p align="center">
  <img alt="GitHub stars" src="https://img.shields.io/github/stars/HanFengRuYue/AutoUnzip?style=for-the-badge">
  <img alt="Last commit" src="https://img.shields.io/github/last-commit/HanFengRuYue/AutoUnzip?style=for-the-badge">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows-2b6de5?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.14-4b8cff?style=for-the-badge">
</p>

## 功能

- 自动连续解压多层嵌套压缩包
- 识别伪装后缀，例如 `.jpg`、`.jpeg`、`.psd`，并支持自定义后缀库
- 支持分卷压缩包，例如 `.7z.001`、`.zip.001`、`.part1.rar`、`.z01 + .zip`
- 支持密码库轮询、手动输入密码，并可保存到本地密码库
- 内置 7-Zip，打包后可直接单独运行 EXE
- 配置默认保存在 EXE 同目录，权限不足时自动申请管理员权限

## 使用

1. 打开程序。
2. 拖拽压缩包或文件夹，或点击选择文件/文件夹。
3. 点击开始解压，输出目录会自动生成在源文件旁边。

## 构建

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

构建完成后，产物位于 `dist\AutoUnzip\AutoUnzip.exe`。
