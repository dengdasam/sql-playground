@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

REM 用法：
REM   发布.bat          便携版（自包含，约 154MB，免装运行时）
REM   发布.bat lite      轻量版（框架依赖，约 10MB，需 .NET 10 运行时）

set MODE=portable
if /I "%~1"=="lite" set MODE=lite

if /I "%MODE%"=="lite" (set OUT=dist-lite) else (set OUT=dist)

echo ============================================
echo   打包 SQL 查询实验室
echo   模式：%MODE%    输出：%OUT%\
echo ============================================
echo.

echo [1/5] 停止正在运行的实例...
taskkill /IM SqlController.exe  /F >nul 2>&1
taskkill /IM SqlPlayground.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] 生成题库页面...
REM wwwroot\quiz 下的两个 HTML 是构建产物、不入库（见 .gitignore）。
REM 新克隆的仓库里它们不存在，直接发布会打出缺题库的 exe，所以这里补一步。
if not exist "SqlPlayground\wwwroot\quiz\practice.html" goto build_quiz
if not exist "SqlPlayground\wwwroot\quiz\challenge.html" goto build_quiz
echo       已存在，跳过（如需重建请先删除 wwwroot\quiz\*.html 或手动运行 python quiz-src\build.py）
goto quiz_ready

:build_quiz
where python >nul 2>&1
if errorlevel 1 goto no_python
python quiz-src\build.py
if errorlevel 1 goto fail
goto quiz_ready

:no_python
echo.
echo 缺少题库页面：SqlPlayground\wwwroot\quiz\ 下没有 practice.html / challenge.html，
echo 而本机没有 python 可用于生成。
echo.
echo 请先安装 Python 3，然后在 %~dp0 下运行：
echo     python quiz-src\build.py
echo 再重新执行本脚本。
echo.
pause
exit /b 1

:quiz_ready
echo [3/5] 备份 %OUT% 中已有的数据库...
if exist "%OUT%\wms.db" copy /Y "%OUT%\wms.db" "%OUT%\wms.db.bak" >nul

if /I "%MODE%"=="lite" goto publish_lite

:publish_portable
echo [4/5] 发布后端（自包含）...
dotnet publish SqlPlayground\SqlPlayground.csproj -c Release -r win-x64 ^
  --self-contained true -p:PublishSingleFile=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true ^
  -p:PublishReadyToRun=true -o %OUT%
if errorlevel 1 goto fail

echo [4/5] 发布控制器（自包含）...
dotnet publish SqlController\SqlController.csproj -c Release -r win-x64 ^
  --self-contained true -p:PublishSingleFile=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true ^
  -p:PublishReadyToRun=true -o %OUT%
if errorlevel 1 goto fail
goto done

:publish_lite
REM 注意：框架依赖的单文件不能加 EnableCompressionInSingleFile（会报 NETSDK1176），
REM 也不要加 PublishReadyToRun（实测该组合启动即退出），所以这里只保留最基础参数。
echo [4/5] 发布后端（框架依赖）...
dotnet publish SqlPlayground\SqlPlayground.csproj -c Release -r win-x64 ^
  --self-contained false -p:PublishSingleFile=true -o %OUT%
if errorlevel 1 goto fail

echo [4/5] 发布控制器（框架依赖）...
dotnet publish SqlController\SqlController.csproj -c Release -r win-x64 ^
  --self-contained false -p:PublishSingleFile=true -o %OUT%
if errorlevel 1 goto fail

:done
echo [5/5] 恢复数据库（保留你在 %OUT% 里改动过的数据）...
if exist "%OUT%\wms.db.bak" move /Y "%OUT%\wms.db.bak" "%OUT%\wms.db" >nul

echo.
echo --------------------------------------------
echo  打包完成：%OUT%\
echo --------------------------------------------
dir /b %OUT%\*.exe
echo.
echo 启动：双击 %OUT%\SqlController.exe
if /I "%MODE%"=="lite" echo 注意：轻量版需要本机已安装 .NET 10 桌面运行时。
echo.
pause
exit /b 0

:fail
echo.
echo 发布失败，请检查上面的报错。
if exist "%OUT%\wms.db.bak" move /Y "%OUT%\wms.db.bak" "%OUT%\wms.db" >nul
pause
exit /b 1
