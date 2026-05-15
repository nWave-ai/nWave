// build.gradle.kts — polyglot pilot for the Kotlin state-delta port.
//
// Pinned versions:
//   - Kotlin JVM plugin 1.9.24 (Kotlin 1.9.x line)
//   - Kotest 5.8.1 (kotest-runner-junit5 + kotest-property)
//   - JVM target 17
//
// Build/run:
//   gradle test         # one-shot
//   ./gradlew test      # via wrapper (if generated)

plugins {
    kotlin("jvm") version "1.9.24"
}

group = "nwave.polyglot"
version = "0.0.0"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation("io.kotest:kotest-runner-junit5:5.8.1")
    testImplementation("io.kotest:kotest-assertions-core:5.8.1")
    testImplementation("io.kotest:kotest-property:5.8.1")
}

kotlin {
    jvmToolchain(17)
}

tasks.test {
    useJUnitPlatform()
    // Fail-loud — surface assertion failures with full stack and stdout.
    testLogging {
        events("passed", "skipped", "failed")
        showStandardStreams = true
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}
