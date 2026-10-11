dependencies {
    // ... existing dependencies ...
    
    // Zstandard compression
    implementation("com.github.luben:zstd-jni:1.5.5-11")
    
    // ZIP/DEFLATE support
    implementation("net.lingala.zip4j:zip4j:2.11.5")
    
    // Libsodium for XChaCha20-Poly1305
    implementation("com.goterl:lazysodium-android:5.1.0")
    
    // ... rest of dependencies ...
}
