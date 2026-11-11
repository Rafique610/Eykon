plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.eykon.memory"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.eykon.memory"
        minSdk = 31
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = freeCompilerArgs + listOf("-Xskip-metadata-version-check")
    }

    buildFeatures {
        compose = true
    }

    // The on-phone tests read the same test pictures as the JVM tests (src/test/resources/filters).
    sourceSets {
        getByName("androidTest") {
            assets.srcDir("src/test/resources")
            // EYKO-105: our own sqlite-vec builds from EYKO-104 (task build-sqlite-vec-android), kept out of git
            val sqliteVec = file(findProperty("sqliteVecOut") as String? ?: "D:/eykon-cache/sqlite-vec-android/out")
            if (sqliteVec.exists()) assets.srcDir(sqliteVec)
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    val roomVersion = "2.6.1"
    val coroutinesVersion = "1.9.0"
    val serializationVersion = "1.7.1"
    val workVersion = "2.10.0"

    // Core & Lifecycle
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.activity:activity-compose:1.9.3")

    // Jetpack Compose BOM
    val composeBom = platform("androidx.compose:compose-bom:2024.10.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    // Room (SQLite)
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // KotlinX Serialization & Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:$serializationVersion")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:$coroutinesVersion")

    // EYKO-44: WorkManager runs the video jobs as long-running work with a foreground notification. Apache License 2.0 (owner/lead approved on the card, 10 Nov 2026).
    implementation("androidx.work:work-runtime-ktx:$workVersion")

    // Google AI Edge LiteRT-LM On-Device LLM Runtime
    implementation("com.google.ai.edge.litertlm:litertlm-android:0.16.1")

    // ONNX Runtime for embeddings and cross-encoder
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.18.0")

    // Unit Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:$coroutinesVersion")

    // Instrumented Testing
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.room:room-testing:$roomVersion")
    // EYKO-44: test-only, checks the unique work is enqueued once. Apache License 2.0 (approved on the card, 10 Nov 2026).
    androidTestImplementation("androidx.work:work-testing:$workVersion")
    // EYKO-105 route R1: Google's bundled SQLite, which can load sqlite-vec. The test alone needs
    // androidx.sqlite 2.7.1 (the driver API), and AGP makes the app use the same version as its tests,
    // so the app's androidx.sqlite goes 2.4.0 -> 2.7.1 on this throwaway branch (Room 2.6.1 unchanged).
    androidTestImplementation("androidx.sqlite:sqlite-bundled:2.7.1")
    implementation("androidx.sqlite:sqlite-framework:2.7.1")
    // EYKO-106 route R2: requery's SQLite (3.49.0 tag, JitPack), which can load sqlite-vec; test only
    androidTestImplementation("com.github.requery:sqlite-android:3.49.0")
}
