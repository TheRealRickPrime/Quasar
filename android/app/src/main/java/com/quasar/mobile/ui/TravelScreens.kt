package com.quasar.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.quasar.mobile.data.ESimPlan
import com.quasar.mobile.data.ESimUsage

@Composable
fun TravelESimBrowseScreen(onSelectPlan: (ESimPlan) -> Unit, plans: List<ESimPlan> = emptyList()) {
    val selectedDestination = remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
    ) {
        Text(
            text = "Travel eSIM",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Stay connected abroad with instant eSIM activation",
            style = MaterialTheme.typography.bodyMedium,
            color = QuasarColors.steel,
        )
        Spacer(modifier = Modifier.height(20.dp))

        // Display plans or placeholder
        if (plans.isEmpty()) {
            Text(
                text = "No plans available",
                style = MaterialTheme.typography.bodyMedium,
                color = QuasarColors.paper,
            )
        } else {
            plans.forEach { plan ->
                PlanCard(plan = plan, onSelect = onSelectPlan)
                Spacer(modifier = Modifier.height(12.dp))
            }
        }
    }
}

@Composable
fun PlanCard(plan: ESimPlan, onSelect: (ESimPlan) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = QuasarColors.navy),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = plan.destination,
                        style = MaterialTheme.typography.titleMedium,
                        color = QuasarColors.paper,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = plan.name,
                        style = MaterialTheme.typography.bodySmall,
                        color = QuasarColors.steel,
                    )
                }
                Text(
                    text = "$${plan.priceCents / 100}.${String.format("%02d", plan.priceCents % 100)}",
                    style = MaterialTheme.typography.titleSmall,
                    color = QuasarColors.accent,
                    fontWeight = FontWeight.Bold,
                )
            }

            Divider(color = QuasarColors.midnight, thickness = 1.dp)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${plan.dataGb}GB",
                    style = MaterialTheme.typography.labelMedium,
                    color = QuasarColors.paper,
                )
                Text(
                    text = "•",
                    style = MaterialTheme.typography.labelMedium,
                    color = QuasarColors.steel,
                )
                Text(
                    text = "${plan.validityDays} days",
                    style = MaterialTheme.typography.labelMedium,
                    color = QuasarColors.paper,
                )
                if (plan.instantActivation) {
                    Text(
                        text = "•",
                        style = MaterialTheme.typography.labelMedium,
                        color = QuasarColors.steel,
                    )
                    Text(
                        text = "Instant",
                        style = MaterialTheme.typography.labelMedium,
                        color = QuasarColors.accent,
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = { onSelect(plan) },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
            ) {
                Text("Buy now")
            }
        }
    }
}

@Composable
fun ESimOrderConfirmScreen(plan: ESimPlan, onConfirm: (ESimPlan) -> Unit, onCancel: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        Column {
            Text(
                text = "Confirm purchase",
                style = MaterialTheme.typography.headlineMedium,
                color = QuasarColors.paper,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(24.dp))

            // Order summary
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = QuasarColors.navy),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Destination:", color = QuasarColors.steel)
                        Text(plan.destination, color = QuasarColors.paper, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Data:", color = QuasarColors.steel)
                        Text("${plan.dataGb}GB", color = QuasarColors.paper, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Validity:", color = QuasarColors.steel)
                        Text("${plan.validityDays} days", color = QuasarColors.paper, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Divider(color = QuasarColors.midnight)
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Total:", color = QuasarColors.paper, fontWeight = FontWeight.Bold)
                        Text(
                            text = "$${plan.priceCents / 100}.${String.format("%02d", plan.priceCents % 100)}",
                            color = QuasarColors.accent,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleMedium,
                        )
                    }
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp),
            ) {
                Text("Cancel")
            }
            Button(
                onClick = { onConfirm(plan) },
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp),
                colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
            ) {
                Text("Confirm")
            }
        }
    }
}

@Composable
fun ESimActivationScreen(orderId: String, activationCode: String, onContinue: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Activation code",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "Use this code to activate your eSIM. Copy it and paste into your device settings under Mobile Networks.",
            style = MaterialTheme.typography.bodyMedium,
            color = QuasarColors.paper.copy(alpha = 0.85f),
        )
        Spacer(modifier = Modifier.height(24.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = QuasarColors.navy),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = activationCode,
                    style = MaterialTheme.typography.headlineSmall,
                    color = QuasarColors.accent,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(onClick = { /* Copy to clipboard */ }) {
                    Text("Copy code")
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = QuasarColors.accent),
        ) {
            Text("Activated")
        }
    }
}

@Composable
fun ESimUsageScreen(usage: ESimUsage, onBack: () -> Unit = {}) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(QuasarColors.midnight)
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Text(
            text = "Data usage",
            style = MaterialTheme.typography.headlineMedium,
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(20.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = QuasarColors.navy),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column {
                        Text(
                            text = "Status: ${usage.status}",
                            color = QuasarColors.paper,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "${usage.dataUsedMb}MB / ${usage.dataTotalMb}MB",
                            color = QuasarColors.steel,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    Text(
                        text = "${String.format("%.1f", usage.usagePercent)}%",
                        color = QuasarColors.accent,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                LinearProgressIndicator(
                    progress = { usage.usagePercent / 100f },
                    modifier = Modifier.fillMaxWidth(),
                    color = if (usage.usagePercent > 80) QuasarColors.accent else QuasarColors.accent,
                    trackColor = QuasarColors.midnight,
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "Country",
            color = QuasarColors.paper,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium,
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = usage.countryCode,
            color = QuasarColors.steel,
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}
