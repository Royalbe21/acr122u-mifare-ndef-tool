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
