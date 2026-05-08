plugins {
    id("com.android.application")
}

android {
    namespace = "com.masterofrepairs.masternfcwriter"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.masterofrepairs.masternfcwriter"
        minSdk = 23
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-android"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
// Android Studio sync compatibility task for AGP 9 built-in Kotlin support.
tasks.register("prepareKotlinBuildScriptModel") {
    group = "ide"
    description = "No-op compatibility task for Android Studio Kotlin build-script model sync."
}
// Android Studio sync compatibility task for AGP 9 built-in Kotlin support.
tasks.register("prepareKotlinBuildScriptModel") {
    group = "ide"
    description = "No-op compatibility task for Android Studio Kotlin build-script model sync."
}
