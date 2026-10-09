@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins"
msbuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo
echo MSBUILD_EXIT=%errorlevel%