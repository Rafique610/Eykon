pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // EYKO-106 route R2: requery sqlite-android is published only on JitPack; nothing else may come from there
        maven("https://jitpack.io") { content { includeGroup("com.github.requery") } }
    }
}

rootProject.name = "EykonMemory"
include(":app")
