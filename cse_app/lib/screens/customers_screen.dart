import 'package:flutter/material.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  List<User> _customers = [];
  List<Map<String, dynamic>> _raw = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _raw = await ApiService().getCustomers();
      _customers = _raw.map((j) => User.fromJson(j)).toList();
    } catch (_) {}
    setState(() => _loading = false);
  }

  int _affairCount(int i) => (_raw[i]['affair_count'] ?? 0) as int;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Customers')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                padding: const EdgeInsets.all(8),
                itemCount: _customers.length,
                itemBuilder: (_, i) => Card(
                  child: ListTile(
                    leading: CircleAvatar(child: Text(_customers[i].fullName[0])),
                    title: Text(_customers[i].fullName),
                    subtitle: Text('${_affairCount(i)} affairs'),
                    trailing: _customers[i].isActive
                        ? const Icon(Icons.check_circle, color: Colors.green)
                        : const Icon(Icons.cancel, color: Colors.red),
                    onTap: () => Navigator.pushNamed(
                      context,
                      '/customer-detail',
                      arguments: _customers[i].id,
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}
