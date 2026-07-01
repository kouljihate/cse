import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});

  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  List<dynamic> _logs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _logs = await ApiService().getAuditLogs();
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Audit Logs')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                padding: const EdgeInsets.all(8),
                itemCount: _logs.length,
                itemBuilder: (_, i) {
                  final log = _logs[i];
                  return ListTile(
                    leading: _actionIcon(log['action']),
                    title: Text(log['description'] ?? ''),
                    subtitle: Text('${log['performed_by_name']} - ${_formatDate(log['created_at'])}'),
                  );
                },
              ),
            ),
    );
  }

  Widget _actionIcon(String? action) {
    switch (action) {
      case 'create': return const Icon(Icons.add_circle, color: Colors.green);
      case 'update': return const Icon(Icons.edit, color: Colors.orange);
      case 'delete': return const Icon(Icons.delete, color: Colors.red);
      default: return const Icon(Icons.info, color: Colors.blue);
    }
  }

  String _formatDate(dynamic dt) {
    if (dt is String) return dt.substring(0, 10);
    return '';
  }
}
