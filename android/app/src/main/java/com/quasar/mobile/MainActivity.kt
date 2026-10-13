package com.quasar.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.material3.MaterialTheme
import com.quasar.mobile.ui.QuasarApp
import com.quasar.mobile.ui.QuasarTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            QuasarTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) { QuasarApp() }
            }
        }
    }
}
