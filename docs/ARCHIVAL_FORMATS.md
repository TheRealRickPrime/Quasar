# Archival Formats Support

## Overview

Quasar supports multiple archival formats for flexible backup options. Users can choose based on their priorities: speed, compression ratio, or compatibility.

## Supported Formats

### TAR.GZ (Recommended)

**Compression:** 40-45% reduction  
**Speed:** ~1.5 sec/GB  
**Compatibility:** Universal  
**Best for:** Most users

**Pros:**
- Works on all systems (Windows, Mac, Linux)
- Fast processing
- Good compression ratio
- Widely supported
- POSIX standard

**Cons:**
- Slightly larger than TAR.BZ2 or 7Z
- Less compression than XZ

**Use case:** Default choice for most backups

---

### TAR.BZ2

**Compression:** 35-40% reduction  
**Speed:** ~3-4 sec/GB  
**Compatibility:** Widely supported  
**Best for:** Long-term storage

**Pros:**
- Better compression than gzip
- Still widely supported
- Good for archival
- Better than ZIP for large files

**Cons:**
- Slower than gzip
- Less supported on Windows without tools

**Use case:** Archival with better compression

---

### TAR.XZ

**Compression:** 30-35% reduction  
**Speed:** ~5-8 sec/GB  
**Compatibility:** Linux-focused  
**Best for:** Long-term archival, Linux systems

**Pros:**
- Excellent compression
- Native on Linux/Mac
- Open standard
- Smallest file size (besides 7Z)

**Cons:**
- Slow processing
- Less common on Windows
- Requires extraction tool

**Use case:** Maximum compression on Linux/Mac, long-term archival

---

### ZIP

**Compression:** 42-45% reduction  
**Speed:** ~1.5 sec/GB  
**Compatibility:** Universal  
**Best for:** Maximum compatibility

**Pros:**
- Works everywhere natively
- No external tools needed
- Windows/Mac/Linux native
- Can split into volumes
- Fast compression

**Cons:**
- Slightly larger files than TAR.GZ
- Older format, some size limitations

**Use case:** When maximum compatibility essential

---

### 7Z

**Compression:** 25-30% reduction  
**Speed:** ~15+ sec/GB  
**Compatibility:** Specialized  
**Best for:** Maximum compression

**Pros:**
- Best compression ratio
- Excellent for archival
- Strong encryption support
- Modern format

**Cons:**
- Slowest option
- Requires 7-Zip software
- Less common than ZIP
- Not natively supported on most systems

**Use case:** Maximum compression for long-term storage, when speed not critical

---

## Comparison Matrix

| Format | Speed | Compression | Compatibility | Size/GB | Best For |
|--------|-------|-------------|---|---------|----------|
| TAR.GZ | 1.5s | 40-45% | Universal | 600MB | Recommended |
| TAR.BZ2 | 3.5s | 35-40% | Widely | 630MB | Archival |
| TAR.XZ | 6s | 30-35% | Linux | 700MB | Max compression |
| ZIP | 1.5s | 42-45% | Universal | 580MB | Compatibility |
| 7Z | 18s | 25-30% | Common | 750MB | Best ratio |

## Selection Guide

### Choose TAR.GZ if:
- ✓ You want the best balance
- ✓ You need universal compatibility
- ✓ You want fast processing
- ✓ You use Linux/Mac/Windows

### Choose TAR.BZ2 if:
- ✓ You prioritize compression
- ✓ You're doing long-term archival
- ✓ You can wait 3-4 seconds/GB
- ✓ You use Linux/Mac primarily

### Choose TAR.XZ if:
- ✓ You want maximum compression
- ✓ You use Linux/Mac
- ✓ You need POSIX compliance
- ✓ Storage space is very limited

### Choose ZIP if:
- ✓ You need Windows compatibility
- ✓ You need native support on all OSes
- ✓ You want no external tools needed
- ✓ You prefer universal support

### Choose 7Z if:
- ✓ You want the absolute smallest file
- ✓ You're archiving for very long-term
- ✓ Speed is not a concern
- ✓ You have 7-Zip installed/available

## Architecture

### ArchiveHandler Interface

```kotlin
interface ArchiveHandler {
    val format: ArchiveFormat
    
    suspend fun archive(
        inputFile: File,
        outputFile: File,
        compressionLevel: Int = 19,
        onProgress: (Float) -> Unit = {}
    ): ArchiveResult
    
    suspend fun extract(
        archiveFile: File,
        outputDirectory: File,
        onProgress: (Float) -> Unit = {}
    ): ArchiveResult
    
    suspend fun verify(archiveFile: File): Boolean
}
```

### ArchiveHandlerFactory

```kotlin
val handler = ArchiveHandlerFactory.createHandler(ArchiveFormat.TAR_GZ)
val result = handler.archive(inputFile, outputFile)
```

### ArchiveResult

```kotlin
data class ArchiveResult(
    val success: Boolean,
    val format: ArchiveFormat?,
    val inputFile: File?,
    val outputFile: File?,
    val originalSize: Long,
    val compressedSize: Long,
    val compressionRatio: Double,
    val elapsedMillis: Long,
    val entriesCount: Int,
    val checksum: String,
    val error: String?
)
```

## Implementation Examples

### Creating an Archive

```kotlin
val handler = ArchiveHandlerFactory.createHandler(ArchiveFormat.TAR_GZ)

val result = handler.archive(
    inputFile = File("/path/to/backup.ab"),
    outputFile = File("/path/to/backup.tar.gz"),
    compressionLevel = 19
) { progress ->
    println("Progress: ${(progress * 100).toInt()}%")
}

if (result.success) {
    println("Compressed: ${result.originalSize} → ${result.compressedSize}")
    println("Ratio: ${(result.compressionRatio * 100).toInt()}%")
    println("Time: ${result.elapsedMillis}ms")
}
```

### Extracting an Archive

```kotlin
val handler = ArchiveHandlerFactory.createHandler(ArchiveFormat.TAR_GZ)

val result = handler.extract(
    archiveFile = File("/path/to/backup.tar.gz"),
    outputDirectory = File("/path/to/output")
) { progress ->
    println("Extraction: ${(progress * 100).toInt()}%")
}

if (result.success) {
    println("Extracted ${result.entriesCount} entries")
}
```

### Verifying an Archive

```kotlin
val handler = ArchiveHandlerFactory.createHandler(ArchiveFormat.TAR_GZ)

if (handler.verify(archiveFile)) {
    println("Archive is valid")
} else {
    println("Archive is corrupted")
}
```

## ArchivalManager

Manages user options and recommendations:

```kotlin
val manager = ArchivalManager()

// Get all options
val options = manager.getArchivalOptions()

// Recommend based on priority
val format = manager.recommendFormat(
    priority = ArchivalManager.Priority.COMPRESSION
)

// Compare formats
val comparison = manager.compareFormats()
```

## UI Integration

Display archival options to users:

```
┌─────────────────────────────────────┐
│ Select Archival Format              │
├─────────────────────────────────────┤
│ ⭐ TAR.GZ (Recommended)              │
│    1.5 sec/GB | 40% compression     │
│    Universal compatibility          │
│                                     │
│ TAR.BZ2                             │
│    3.5 sec/GB | 37% compression     │
│    Better compression               │
│                                     │
│ TAR.XZ                              │
│    6 sec/GB | 32% compression       │
│    Maximum compression (slow)       │
│                                     │
│ ZIP                                 │
│    1.5 sec/GB | 42% compression     │
│    Maximum compatibility            │
│                                     │
│ 7Z                                  │
│    18 sec/GB | 27% compression      │
│    Best ratio (very slow)           │
└─────────────────────────────────────┘
```

## Performance Characteristics

### Speed (Processing Time)
- **Fastest:** TAR.GZ, ZIP (~1.5 sec/GB)
- **Moderate:** TAR.BZ2 (~3.5 sec/GB)
- **Slow:** TAR.XZ (~6 sec/GB)
- **Slowest:** 7Z (~18 sec/GB)

### Compression Ratio (Space Saved)
- **Best:** 7Z (~27%, saves 730MB per GB)
- **Excellent:** TAR.XZ (~32%, saves 680MB per GB)
- **Good:** TAR.BZ2 (~37%, saves 630MB per GB)
- **Good:** TAR.GZ (~40%, saves 600MB per GB)
- **Good:** ZIP (~42%, saves 580MB per GB)

### Compatibility
- **Universal:** TAR.GZ, ZIP
- **Widely Supported:** TAR.BZ2
- **Common:** 7Z
- **Linux/Unix:** TAR.XZ

## Checksum Verification

Each archive result includes SHA-256 checksum for integrity verification:

```kotlin
val result = handler.archive(input, output)
println("Checksum: ${result.checksum}")

// Later, verify
val verifyResult = handler.archive(sameInput, sameOutput)
assert(verifyResult.checksum == result.checksum)
```

## Error Handling

Archive operations include comprehensive error handling:

```kotlin
if (!result.success) {
    println("Error: ${result.error}")
    // Handle based on error message
}
```
