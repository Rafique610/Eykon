# EYKO-108 (route R4, throwaway): SQLite + sqlite-vec compiled into one .so, no plugin loading.
# Build: see build.ps1 in this folder. Sources are not committed: fetch.ps1 downloads them and checks SHA256.
cmake_minimum_required(VERSION 3.22)
project(eykon_r4 C)

set(SRC "${CMAKE_CURRENT_SOURCE_DIR}/third_party")
option(R4_NEON "compile sqlite-vec with NEON" ON)
set(R4_LIBNAME "eykon_r4" CACHE STRING "output library name")

add_library(${R4_LIBNAME} SHARED
    ${SRC}/sqlite3.c
    ${SRC}/sqlite-vec.c
    r4_jni.c)
target_include_directories(${R4_LIBNAME} PRIVATE ${SRC})
target_compile_options(${R4_LIBNAME} PRIVATE -O3)
target_compile_definitions(${R4_LIBNAME} PRIVATE
    SQLITE_CORE            # sqlite-vec calls SQLite directly instead of through sqlite3ext.h
    SQLITE_ENABLE_FTS5
    SQLITE_OMIT_LOAD_EXTENSION  # nothing is loaded at run time
    SQLITE_THREADSAFE=1)
if(R4_NEON)
    target_compile_definitions(${R4_LIBNAME} PRIVATE SQLITE_VEC_ENABLE_NEON)
endif()
