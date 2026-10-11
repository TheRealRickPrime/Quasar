package com.quasar.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.quasar.mobile.viewmodel.AuthState
import com.quasar.mobile.viewmodel.AuthViewModel

@Composable
fun SignUpScreen(authViewModel: AuthViewModel, onContinue: () -> Unit) {
    val email = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }
    val fullName = remember { mutableStateOf("") }
    val authState = authViewModel.authState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Create account",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(24.dp))

        TextField(
            value = fullName.value,
            onValueChange = { fullName.value = it },
            label = { Text("Full name") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = email.value,
            onValueChange = { email.value = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = password.value,
            onValueChange = { password.value = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(24.dp))

        when (authState.value) {
            AuthState.Loading -> {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                    color = QuasarColors.accent,
                )
            }
            is AuthState.Error -> {
                Text(
                    text = (authState.value as AuthState.Error).message,
                    color = QuasarColors.accent,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            AuthState.Authenticated -> {
                onContinue()
            }
            else -> {}
        }

        Button(
            onClick = { authViewModel.register(email.value, password.value, fullName.value) },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
            enabled = email.value.isNotEmpty() && password.value.isNotEmpty(),
        ) {
            Text("Create account")
        }
    }
}

@Composable
fun SignInScreen(authViewModel: AuthViewModel, onContinue: () -> Unit) {
    val email = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }
    val authState = authViewModel.authState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Sign in",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(24.dp))

        TextField(
            value = email.value,
            onValueChange = { email.value = it },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(16.dp))

        TextField(
            value = password.value,
            onValueChange = { password.value = it },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = QuasarColors.navy,
                unfocusedContainerColor = QuasarColors.navy,
                focusedTextColor = QuasarColors.paper,
                unfocusedTextColor = QuasarColors.paper,
            ),
        )
        Spacer(modifier = Modifier.height(24.dp))

        when (authState.value) {
            AuthState.Loading -> {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                    color = QuasarColors.accent,
                )
            }
            is AuthState.Error -> {
                Text(
                    text = (authState.value as AuthState.Error).message,
                    color = QuasarColors.accent,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            AuthState.Authenticated -> {
                onContinue()
            }
            else -> {}
        }

        Button(
            onClick = { authViewModel.login(email.value, password.value) },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
            enabled = email.value.isNotEmpty() && password.value.isNotEmpty(),
        ) {
            Text("Sign in")
        }
    }
}
