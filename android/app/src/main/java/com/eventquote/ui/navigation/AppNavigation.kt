package com.eventquote.ui.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.eventquote.ui.screens.*
import com.eventquote.ui.viewmodel.EventQuoteViewModel

@Composable
fun AppNavigation(vm: EventQuoteViewModel = viewModel()) {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = "login") {
        composable("login") {
            LoginScreen(
                vm = vm,
                onNavigateToRegister = {
                    vm.limpiarMensajes()
                    navController.navigate("register")
                },
                onLoginSuccess = { rol ->
                    val dest = if (rol == "admin") "admin_home" else "cliente_home"
                    navController.navigate(dest) {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }
        composable("register") {
            RegisterScreen(
                vm = vm,
                onBackToLogin = { navController.popBackStack() }
            )
        }
        composable("cliente_home") {
            ClienteHomeScreen(
                vm = vm,
                onLogout = {
                    navController.navigate("login") {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
        composable("admin_home") {
            AdminHomeScreen(
                vm = vm,
                onLogout = {
                    navController.navigate("login") {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
    }
}
