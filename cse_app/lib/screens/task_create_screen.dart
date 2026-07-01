import 'package:flutter/material.dart';
import '../services/api_service.dart';

class TaskCreateScreen extends StatefulWidget {
  const TaskCreateScreen({super.key});

  @override
  State<TaskCreateScreen> createState() => _TaskCreateScreenState();
}

class _TaskCreateScreenState extends State<TaskCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  String _priority = 'medium';
  String? _selectedEmployee;
  String? _selectedAffair;
  String? _selectedService;
  List<dynamic> _employees = [];
  List<dynamic> _affairs = [];
  List<dynamic> _services = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final api = ApiService();
      _employees = await api.getEmployees();
      _affairs = await api.getAffairs();
      _services = await api.getServices();
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedEmployee == null || _selectedAffair == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select employee and affair')),
      );
      return;
    }

    await ApiService().createTask({
      'title': _titleCtrl.text,
      'description': _descCtrl.text,
      'assigned_to': _selectedEmployee,
      'affair_id': _selectedAffair,
      'service_id': _selectedService,
      'priority': _priority,
    });

    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Task')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  TextFormField(
                    controller: _titleCtrl,
                    decoration: const InputDecoration(labelText: 'Task Title', border: OutlineInputBorder()),
                    validator: (v) => v == null || v.isEmpty ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _descCtrl,
                    maxLines: 3,
                    decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedAffair,
                    decoration: const InputDecoration(labelText: 'Affair', border: OutlineInputBorder()),
                    items: _affairs.map((a) => DropdownMenuItem(
                      value: a['_id'],
                      child: Text(a['name']),
                    )).toList(),
                    onChanged: (v) => setState(() => _selectedAffair = v),
                    validator: (v) => v == null ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedService,
                    decoration: const InputDecoration(labelText: 'Service (optional)', border: OutlineInputBorder()),
                    items: _services.map((s) => DropdownMenuItem(
                      value: s['_id'],
                      child: Text(s['name']),
                    )).toList(),
                    onChanged: (v) => setState(() => _selectedService = v),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedEmployee,
                    decoration: const InputDecoration(labelText: 'Assign To', border: OutlineInputBorder()),
                    items: _employees.map((e) => DropdownMenuItem(
                      value: e['_id'],
                      child: Text(e['full_name']),
                    )).toList(),
                    onChanged: (v) => setState(() => _selectedEmployee = v),
                    validator: (v) => v == null ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _priority,
                    decoration: const InputDecoration(labelText: 'Priority', border: OutlineInputBorder()),
                    items: ['low', 'medium', 'high', 'critical'].map((p) => DropdownMenuItem(
                      value: p,
                      child: Text(p),
                    )).toList(),
                    onChanged: (v) => setState(() => _priority = v ?? 'medium'),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _submit,
                    child: const Text('Create Task', style: TextStyle(fontSize: 16)),
                  ),
                ],
              ),
            ),
    );
  }
}
