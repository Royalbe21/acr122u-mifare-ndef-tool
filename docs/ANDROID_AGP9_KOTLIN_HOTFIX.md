# AGP 9 Built-In Kotlin Hotfix

## Problem

Android Studio/Gradle may fail with:

```text
The 'org.jetbrains.kotlin.android' plugin is no longer required for Kotlin support since AGP 9.0.
Solution: Remove the 'org.jetbrains.kotlin.android' plugin from this project's build file.
```

## Cause

Android Gradle Plugin 9.0+ includes built-in Kotlin support for Android projects, so the separate Kotlin Android plugin should not be applied.

## Fix

This hotfix removes:

```kotlin
id("org.jetbrains.kotlin.android")
```

from:

```text
android/MasterNfcWriterAndroid/build.gradle.kts
android/MasterNfcWriterAndroid/app/build.gradle.kts
```

It also removes the old `kotlin { jvmToolchain(17) }` block and uses Android `compileOptions` instead.
