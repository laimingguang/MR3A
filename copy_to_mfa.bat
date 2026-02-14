@echo off
chcp 65001 >nul
setlocal

set "target=E:\MFAAvalonia"

echo ℹ️  [信息] 目标目录：%target%
echo.

:: ============ 步骤1：精准清理（仅删除 resource 文件夹和 interface.json） ============
if exist "%target%\resource\" (
    echo ℹ️  [信息] 正在删除 resource 文件夹...
    rd /s /q "%target%\resource" 2>nul
    if errorlevel 1 (
        echo ✗ [错误] 无法删除 resource 文件夹，可能被占用
        goto :end
    )
    echo ✅ [成功] resource 文件夹已删除
) else (
    echo ⚠️  [提示] resource 文件夹不存在，跳过
)

if exist "%target%\interface.json" (
    echo ℹ️  [信息] 正在删除 interface.json...
    del /f /q "%target%\interface.json" 2>nul
    if errorlevel 1 (
        echo ✗ [错误] 无法删除 interface.json
        goto :end
    )
    echo ✅ [成功] interface.json 已删除
) else (
    echo ⚠️  [提示] interface.json 不存在，跳过
)

:: ============ 步骤2：复制新资源 ============
echo.
echo ℹ️  [信息] 复制新资源...

:: 复制 resource 文件夹
if exist "assets\resource\" (
    echo ℹ️  [信息] 复制 resource 文件夹...
    xcopy "assets\resource" "%target%\resource\" /E /I /Y /Q >nul 2>&1
    if errorlevel 1 (
        echo ✗ [错误] resource 复制失败
        goto :end
    )
    echo ✅ [成功] resource 文件夹更新完成
) else (
    echo ⚠️  [警告] 源目录 assets\resource 不存在，跳过
)

:: 复制 interface.json
if exist "assets\interface.json" (
    echo ℹ️  [信息] 复制 interface.json...
    copy /Y "assets\interface.json" "%target%\" >nul 2>&1
    if errorlevel 1 (
        echo ✗ [错误] interface.json 复制失败
        goto :end
    )
    echo ✅ [成功] interface.json 更新完成
) else (
    echo ⚠️  [警告] 源文件 assets\interface.json 不存在，跳过
)

:: ============ 步骤3：启动应用 ============
echo.
echo ✅ [完成] 资源更新成功！路径：%target%
echo.

if exist "%target%\MFAAvalonia.exe" (
    echo 🚀 [启动] 启动应用程序...
    start "" "%target%\MFAAvalonia.exe"
    echo ✅ [成功] 应用程序已启动
) else (
    echo ⚠️  [提示] 未找到 MFAAvalonia.exe，未自动启动
)

goto :end

:end
echo.
pause
exit /b %errorlevel%