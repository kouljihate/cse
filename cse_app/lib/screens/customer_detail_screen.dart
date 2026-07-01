import 'package:flutter/material.dart';
import '../services/api_service.dart';

class CustomerDetailScreen extends StatefulWidget {
  final String customerId;
  const CustomerDetailScreen({super.key, required this.customerId});

  @override
  State<CustomerDetailScreen> createState() => _CustomerDetailScreenState();
}

class _CustomerDetailScreenState extends State<CustomerDetailScreen> {
  Map<String, dynamic>? _customer;
  List<dynamic> _tasks = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _customer = await ApiService().getCustomerDetail(widget.customerId);
      _tasks = await ApiService().getTasks();
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_customer?['full_name'] ?? 'Customer')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          CircleAvatar(
                            radius: 30,
                            child: Text((_customer?['full_name'] ?? '?')[0]),
                          ),
                          const SizedBox(height: 8),
                          Text(_customer?['full_name'] ?? '', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          Text(_customer?['email'] ?? ''),
                          Text(_customer?['phone'] ?? ''),
                          const SizedBox(height: 8),
                          Chip(label: Text('${_customer?['affair_count'] ?? 0} affairs')),
                        ],
                      ),
                    ),
                  ),
                  if (_customer?['task_stats'] != null) ...[
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        _statCard('Total', '${_customer!['task_stats']['total']}', Colors.blue),
                        _statCard('Open', '${_customer!['task_stats']['open']}', Colors.orange),
                        _statCard('Done', '${_customer!['task_stats']['completed']}', Colors.green),
                      ],
                    ),
                  ],
                  const SizedBox(height: 16),
                  Text('Tasks', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ..._tasks.map((t) => ListTile(
                    title: Text(t['title'] ?? ''),
                    subtitle: Text('${t['assigned_to_name'] ?? "-"}  •  ${t['status']}'),
                    trailing: Chip(label: Text(t['priority'] ?? '')),
                  )),
                ],
              ),
            ),
    );
  }

  Widget _statCard(String label, String value, Color color) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: color)),
              Text(label, style: const TextStyle(fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
