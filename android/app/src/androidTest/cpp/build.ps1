# EYKO-108: builds the two libraries (NEON and no NEON) for arm64-v8a with the NDK and copies them to
# androidTest/jniLibs, which puts them in the test APK only. Usage: powershell -File build.ps1 [-Ndk 28.2.13676358]
param([string]$Ndk = "28.2.13676358")
$sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$ndkDir = Join-Path $sdk "ndk\$Ndk"
$cmakeBin = Join-Path $sdk "cmake\3.22.1\bin"
$out = Join-Path $PSScriptRoot "..\jniLibs\arm64-v8a"
New-Item -ItemType Directory -Force $out | Out-Null
foreach ($v in @(@{ Name = "eykon_r4"; Neon = "ON" }, @{ Name = "eykon_r4_noneon"; Neon = "OFF" })) {
  $b = Join-Path $PSScriptRoot "build-$($v.Name)"
  & "$cmakeBin\cmake.exe" -S $PSScriptRoot -B $b -G Ninja "-DCMAKE_MAKE_PROGRAM=$cmakeBin\ninja.exe" `
    "-DCMAKE_TOOLCHAIN_FILE=$ndkDir\build\cmake\android.toolchain.cmake" -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-31 `
    -DCMAKE_BUILD_TYPE=Release "-DR4_NEON=$($v.Neon)" "-DR4_LIBNAME=$($v.Name)"
  & "$cmakeBin\cmake.exe" --build $b
  Copy-Item (Join-Path $b "lib$($v.Name).so") $out -Force
}
Get-ChildItem $out | Select-Object Name, Length
