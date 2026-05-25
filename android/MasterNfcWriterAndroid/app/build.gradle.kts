import java.util.Properties

plugins {
    id("com.android.application")
}

val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties()

if (!keystorePropertiesFile.exists()) {
    throw GradleException("Missing key.properties. Release builds require Android signing credentials.")
}

keystoreProperties.load(keystorePropertiesFile.inputStream())

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

    signingConfigs {
        create("release") {
            storeFile = rootProject.file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = false
            isShrinkResources = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}