import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'services/api_service.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/tasks_screen.dart';
import 'screens/task_create_screen.dart';
import 'screens/users_screen.dart';
import 'screens/reports_screen.dart';
import 'screens/audit_screen.dart';
import 'screens/customers_screen.dart';
import 'screens/customer_detail_screen.dart';
import 'screens/services_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiService().init();
  runApp(const CseApp());
}

class CseApp extends StatelessWidget {
  const CseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()..loadProfile()),
      ],
      child: MaterialApp(
        title: 'Global Service & Document Manager',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorSchemeSeed: const Color(0xFF1a237e),
          useMaterial3: true,
          brightness: Brightness.light,
        ),
        initialRoute: '/login',
        routes: {
          '/login': (_) => const LoginScreen(),
          '/dashboard': (_) => const DashboardScreen(),
          '/tasks': (_) => const TasksScreen(),
          '/task-create': (_) => const TaskCreateScreen(),
          '/users': (_) => const UsersScreen(),
          '/reports': (_) => const ReportsScreen(),
          '/audit': (_) => const AuditScreen(),
          '/services': (_) => const ServicesScreen(),
          '/customers': (_) => const CustomersScreen(),
          '/customer-detail': (context) {
            final id = ModalRoute.of(context)!.settings.arguments as String;
            return CustomerDetailScreen(customerId: id);
          },
        },
      ),
    );
  }
}
