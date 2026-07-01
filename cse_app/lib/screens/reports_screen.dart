import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reports')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Card(
              child: ListTile(
                leading: const Icon(Icons.assignment, color: Colors.blue),
                title: const Text('Tasks Report'),
                subtitle: const Text('Download PDF report of all tasks'),
                trailing: const Icon(Icons.download),
                onTap: () => _downloadReport(context, 'tasks'),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.folder, color: Colors.purple),
                title: const Text('Affairs Report'),
                subtitle: const Text('Download PDF report of all affairs'),
                trailing: const Icon(Icons.download),
                onTap: () => _downloadReport(context, 'affairs'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _downloadReport(BuildContext context, String type) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Report download started')),
    );
  }
}
