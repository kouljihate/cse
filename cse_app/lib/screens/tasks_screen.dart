import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/task.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  List<Task> _tasks = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadTasks();
  }

  Future<void> _loadTasks() async {
    setState(() => _loading = true);
    try {
      final data = await ApiService().getTasks();
      setState(() => _tasks = data.map((j) => Task.fromJson(j)).toList());
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _updateStatus(Task task, String status) async {
    await ApiService().updateTask(task.id, {'status': status});
    _loadTasks();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tasks'),
        actions: [
          if (auth.isAdmin)
            IconButton(
              icon: const Icon(Icons.add),
              onPressed: () async {
                final result = await Navigator.pushNamed(context, '/task-create');
                if (result == true) _loadTasks();
              },
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadTasks,
              child: _tasks.isEmpty
                  ? const Center(child: Text('No tasks found'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: _tasks.length,
                      itemBuilder: (_, i) => Card(
                        child: ListTile(
                          title: Text(_tasks[i].title, style: const TextStyle(fontWeight: FontWeight.w600)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Status: ${_tasks[i].status}'),
                            ],
                          ),
                          trailing: _statusChip(_tasks[i].status),
                          isThreeLine: false,
                          onTap: () => _showTaskDialog(_tasks[i], auth),
                        ),
                      ),
                    ),
            ),
    );
  }

  void _showTaskDialog(Task task, AuthProvider auth) {
    showModalBottomSheet(
      context: context,
      builder: (_) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(task.title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            if (task.description != null) ...[
              const SizedBox(height: 8),
              Text(task.description!),
            ],
            const SizedBox(height: 8),
            Text('Status: ${task.status}'),
            const SizedBox(height: 16),
            if (auth.isAdmin || auth.isEmployee)
              Wrap(
                spacing: 8,
                children: ['pending', 'in_progress', 'completed', 'cancelled'].where((s) => s != task.status).map((s) {
                  return ActionChip(
                    label: Text('Mark $s'),
                    onPressed: () {
                      _updateStatus(task, s);
                      Navigator.pop(context);
                    },
                  );
                }).toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _statusChip(String status) {
    final color = switch (status) {
      'pending' => Colors.orange,
      'in_progress' => Colors.blue,
      'completed' => Colors.green,
      'cancelled' => Colors.red,
      _ => Colors.grey,
    };
    return Chip(label: Text(status, style: const TextStyle(fontSize: 11)), backgroundColor: color.withOpacity(0.2));
  }
}
