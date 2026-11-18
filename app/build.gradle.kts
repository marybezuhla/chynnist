import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// The version people see (major.minor.patch), set by hand before each release in version.txt.
val appVersion = rootProject.file("version.txt").readText().trim()
// versionCode comes from the same file, so anyone can rebuild the same APK from source: 1.2.4 -> 10204
val appVersionCode = appVersion.split(".").map { it.toInt() }.also {
    require(it.size == 3) { "version.txt must be major.minor.patch" }
}.let { (a, b, c) ->
    require(b < 100 && c < 100) { "version.txt: minor and patch must be below 100" }
    a * 10000 + b * 100 + c
}

android {
    // Lint runs in CI; any error stops the build, and the report goes with the build log
    lint {
        abortOnError = true
        checkReleaseBuilds = true
        textReport = true
        textOutput = file("build/reports/lint-results-release.txt")
        lintConfig = file("lint.xml")
    }

    namespace = "ua.chynnist"
    compileSdk = 36

    defaultConfig {
        applicationId = "ua.chynnist"
        minSdk = 31
        targetSdk = 36
        versionCode = appVersionCode
        versionName = appVersion
    }

    // No Google-readable list of libraries inside the APK
    dependenciesInfo {
        includeInApk = false
        includeInBundle = false
    }

    buildTypes {
        release {
            // Smaller APK: unused code and resources are left out (the extra rules in proguard-rules.pro: no log lines)
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Left unsigned here; signed later in a separate step that runs no build code
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    // Screen tests run on the computer (Robolectric) and need the app's resources
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
        }
    }

    // Lets Android 13+ offer Chynnist's own language setting (English, Ukrainian)
    androidResources {
        generateLocaleConfig = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2025.09.00")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")

    // core-ktx, not core: other libraries ask for it, and this keeps the one already reviewed
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-compose:1.10.1")

    testImplementation("junit:junit:4.13.2")
    // Screen tests only (never in the app): draw each screen with made-up data, so a crash is caught
    // before a release and the look can be reviewed
    testImplementation(composeBom)
    testImplementation("androidx.compose.ui:ui-test-junit4")
    testImplementation("androidx.compose.ui:ui-test-manifest")
    testImplementation("androidx.test.ext:junit:1.2.1")
    testImplementation("org.robolectric:robolectric:4.16.1")
}
