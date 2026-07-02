import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _stats;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    setState(() => _loading = true);
    try {
      final data = await ApiService().getDashboardStats();
      setState(() => _stats = data);
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadStats,
          ),
          PopupMenuButton(
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'profile', child: Text('Profile')),
              const PopupMenuItem(value: 'logout', child: Text('Logout')),
            ],
            onSelected: (v) {
              if (v == 'logout') {
                auth.logout();
                Navigator.pushReplacementNamed(context, '/login');
              }
            },
          ),
        ],
      ),
      drawer: _buildDrawer(context, auth),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadStats,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _buildStatsGrid(),
                  const SizedBox(height: 24),
                  if (_stats != null) ...[
                    Text('Recent Activities', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    ...(_stats!['recent_activities'] as List? ?? []).take(5).map(
                      (a) => ListTile(
                        dense: true,
                        leading: _activityIcon(a['action']),
                        title: Text(a['description'] ?? ''),
                        subtitle: Text('${a['performed_by_name']} - ${_formatDate(a['created_at'])}'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _buildDrawer(BuildContext context, AuthProvider auth) {
    return Drawer(
      child: ListView(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(color: Theme.of(context).primaryColor),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                const CircleAvatar(radius: 30, child: Icon(Icons.person, size: 30)),
                const SizedBox(height: 8),
                Text(auth.user?.fullName ?? '', style: const TextStyle(color: Colors.white, fontSize: 18)),
                Text(auth.user?.role ?? '', style: const TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.dashboard),
            title: const Text('Dashboard'),
            onTap: () => Navigator.pop(context),
          ),
          ListTile(
            leading: const Icon(Icons.task),
            title: const Text('Tasks'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushNamed(context, '/tasks');
            },
          ),
          if (auth.isAdmin) ...[
            ListTile(
              leading: const Icon(Icons.person_badge),
              title: const Text('Customers'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/customers');
              },
            ),
            ListTile(
              leading: const Icon(Icons.build),
              title: const Text('Services'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/services');
              },
            ),
            ListTile(
              leading: const Icon(Icons.people),
              title: const Text('Users'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/users');
              },
            ),
            ListTile(
              leading: const Icon(Icons.history),
              title: const Text('Audit Logs'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/audit');
              },
            ),
            ListTile(
              leading: const Icon(Icons.description),
              title: const Text('Reports'),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, '/reports');
              },
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatsGrid() {
    if (_stats == null) return const SizedBox.shrink();
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        _statCard('Total Tasks', '${_stats!['total_tasks']}', Colors.blue),
        _statCard('This Month', '${_stats!['monthly_tasks']}', Colors.green),
        if (_stats!['users_count'] != null)
          _statCard('Users', '${_stats!['users_count']}', Colors.orange),
        if (_stats!['services_count'] != null)
          _statCard('Services', '${_stats!['services_count']}', Colors.purple),
        if (_stats!['total_activities'] != null)
          _statCard('Activities', '${_stats!['total_activities']}', Colors.teal),
      ],
    );
  }

  Widget _statCard(String label, String value, Color color) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(value, style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: color)),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: Colors.grey), textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }

  Widget _activityIcon(String action) {
    switch (action) {
      case 'create': return const Icon(Icons.add_circle, color: Colors.green);
      case 'update': return const Icon(Icons.edit, color: Colors.orange);
      case 'delete': return const Icon(Icons.delete, color: Colors.red);
      default: return const Icon(Icons.info, color: Colors.blue);
    }
  }

  String _formatDate(String? iso) {
    if (iso == null) return '';
    try {
      return iso.substring(0, 10);
    } catch (_) {
      return iso;
    }
  }
}
