dependencies {
    // ... existing dependencies ...
    
    // TAR/compression support
    implementation("org.apache.commons:commons-compress:1.24.0")
    
    // ZIP support (already included via zip4j)
    implementation("net.lingala.zip4j:zip4j:2.11.5")
    
    // 7z support
    implementation("net.sf.sevenzipjbinding:sevenzipjbinding:16.02-2.01")
    implementation("net.sf.sevenzipjbinding:sevenzipjbinding-all-windows:16.02-2.01")
    implementation("net.sf.sevenzipjbinding:sevenzipjbinding-all-linux:16.02-2.01")
    implementation("net.sf.sevenzipjbinding:sevenzipjbinding-all-mac:16.02-2.01")
    
    // ... rest of dependencies ...
}
