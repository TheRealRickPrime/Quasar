import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

val unsignedRelease = providers.gradleProperty("unsignedRelease").orNull == "true"

android {
    namespace = "com.quasar.mobile"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.quasar.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 6
        versionName = "0.4.0"
        ndk { abiFilters += setOf("arm64-v8a", "armeabi-v7a", "x86_64", "x86") }
    }

    flavorDimensions += "edition"
    productFlavors {
        listOf("free" to "free", "freeAds" to "free-ads", "supporter" to "supporter", "pro" to "pro")
            .forEach { (name, id) ->
                create(name) {
                    dimension = "edition"
                    buildConfigField("String", "EDITION", "\"$id\"")
                    resValue("string", "app_name", "Quasar " + when (id) {
                        "free-ads" -> "Free with Ads"
                        "supporter" -> "Supporter"
                        "pro" -> "Pro"
                        else -> "Free"
                    })
                }
            }
    }
    val signingProps = Properties().apply {
        val f = File(System.getenv("QUASAR_SIGNING_PROPERTIES") ?: "D:/Quasar-licensing/android-signing.properties")
        if (f.exists()) f.inputStream().use { load(it) }
    }
    signingConfigs {
        if (signingProps.isNotEmpty()) create("release") {
            storeFile = file(signingProps.getProperty("storeFile"))
            storePassword = signingProps.getProperty("storePassword")
            keyAlias = signingProps.getProperty("keyAlias")
            keyPassword = signingProps.getProperty("keyPassword")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Keystore and passwords live outside the repo; releases are never signed with the debug key.
            signingConfig = if (unsignedRelease) null else signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true; buildConfig = true }
    testOptions {
        unitTests.all {
            it.maxHeapSize = "1536m"
            if (providers.gradleProperty("nativeCryptoTests").orNull == "true") {
                it.systemProperty("quasar.nativeTests", "true")
                it.systemProperty("jna.library.path",
                    File(System.getenv("QUASAR_NATIVE_TEST_LIBRARY")).parent)
            }
        }
    }
    packaging {
        jniLibs.useLegacyPackaging = false
        resources.excludes += setOf("META-INF/{AL2.0,LGPL2.1}", "META-INF/DEPENDENCIES", "META-INF/LICENSE*",
            "META-INF/NOTICE*", "META-INF/INDEX.LIST")
    }
}

tasks.configureEach {
    if (name.startsWith("package") && name.endsWith("Release")) {
        doFirst {
            check(unsignedRelease || (System.getenv("QUASAR_SIGNING_PROPERTIES")?.let { File(it).isFile }
                ?: File("D:/Quasar-licensing/android-signing.properties").isFile)) {
                "Release keystore configuration missing. See QUASAR_SIGNING_PROPERTIES."
            }
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.navigation:navigation-compose:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("com.google.android.material:material:1.12.0")

    implementation("com.google.code.gson:gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    testImplementation("junit:junit:4.13.2")
    if (providers.gradleProperty("nativeCryptoTests").orNull == "true") {
        testRuntimeOnly("net.java.dev.jna:jna:5.19.1")
    }

    implementation("com.github.luben:zstd-jni:1.5.7-4@aar")
    implementation(files(rootProject.file("native/lazysodium-android-5.1.0-quasar.aar")))
    implementation("net.java.dev.jna:jna:5.19.1@aar")

    implementation("org.apache.commons:commons-compress:1.26.2")
    implementation("net.lingala.zip4j:zip4j:2.11.5")
    implementation("org.tukaani:xz:1.10")
}
