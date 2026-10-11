package com.quasar.mobile.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object QuasarColors {
    // Reuters-inspired palette
    val navy = Color(0xFF0E1B2A)          // Deep navy base
    val midnight = Color(0xFF101820)     // Darker navy for backgrounds
    val paper = Color(0xFFF5F5F3)        // Off-white for text
    val steel = Color(0xFFB0B7C0)        // Neutral steel gray
    val accent = Color(0xFFD52B1E)       // Editorial red
    val redGlow = Color(0xFFB51D13)      // Darker red for hover states
    val softGray = Color(0xFF8A8F98)     // Softer gray for secondary text
}

private val QuasarDarkColorScheme = darkColorScheme(
    primary = QuasarColors.accent,
    primaryContainer = QuasarColors.redGlow,
    secondary = QuasarColors.steel,
    secondaryContainer = QuasarColors.softGray,
    background = QuasarColors.midnight,
    surface = QuasarColors.navy,
    surfaceVariant = Color(0xFF1A252F),
    onPrimary = Color.White,
    onBackground = QuasarColors.paper,
    onSurface = QuasarColors.paper,
    outline = QuasarColors.steel.copy(alpha = 0.5f),
)

@Composable
fun QuasarTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = QuasarDarkColorScheme,
        typography = androidx.compose.material3.Typography(),
        content = content,
    )
}
