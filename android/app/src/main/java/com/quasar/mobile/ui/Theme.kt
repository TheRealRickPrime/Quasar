package com.quasar.mobile.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.unit.dp

object QuasarColors {
    // Reuters-inspired palette
    val navy = Color(0xFF0E1B2A)          // Deep navy base
    val midnight = Color(0xFF101820)     // Darker navy for backgrounds
    val paper = Color(0xFFF5F5F3)        // Off-white for text
    val steel = Color(0xFFB0B7C0)        // Neutral steel gray
    val accent = Color(0xFFD52B1E)       // Editorial red
    val redGlow = Color(0xFFB51D13)      // Darker red for hover states
    val softGray = Color(0xFFADB6C6)
}

fun Modifier.spaceTexture(): Modifier = drawBehind {
    drawRect(Brush.linearGradient(listOf(Color(0xFF111E32), Color(0xFF080D18))))
    for (i in 0 until 48) {
        val x = ((i * 137 + 31) % 997) / 997f * size.width
        val y = ((i * 251 + 73) % 991) / 991f * size.height
        drawCircle(Color(0xFFB8D5EF).copy(alpha = 0.08f), 0.7.dp.toPx(), Offset(x, y))
    }
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
