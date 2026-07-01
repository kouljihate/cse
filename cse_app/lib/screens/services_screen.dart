import 'package:flutter/material.dart';
import '../models/service.dart';
import '../services/api_service.dart';

class ServicesScreen extends StatefulWidget {
  const ServicesScreen({super.key});

  @override
  State<ServicesScreen> createState() => _ServicesScreenState();
}

class _ServicesScreenState extends State<ServicesScreen> {
  List<Service> _services = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await ApiService().getServices();
      setState(() => _services = data.map((j) => Service.fromJson(j)).toList());
    } catch (_) {}
    setState(() => _loading = false);
  }

  Future<void> _create() async {
    final nameCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    final priceCtrl = TextEditingController();
    bool isActive = true;

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Create Service'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: descCtrl, maxLines: 3, decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Price', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                CheckboxListTile(
                  title: const Text('Active'),
                  value: isActive,
                  onChanged: (v) => setDialogState(() => isActive = v ?? true),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );

    if (result == true) {
      await ApiService().createService({
        'name': nameCtrl.text,
        'description': descCtrl.text.isEmpty ? null : descCtrl.text,
        'price': priceCtrl.text.isEmpty ? null : double.tryParse(priceCtrl.text),
        'is_active': isActive,
      });
      _load();
    }
  }

  Future<void> _edit(Service s) async {
    final nameCtrl = TextEditingController(text: s.name);
    final descCtrl = TextEditingController(text: s.description ?? '');
    final priceCtrl = TextEditingController(text: s.price?.toString() ?? '');
    bool isActive = s.isActive;

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Edit Service'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: descCtrl, maxLines: 3, decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                TextField(controller: priceCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Price', border: OutlineInputBorder())),
                const SizedBox(height: 12),
                CheckboxListTile(
                  title: const Text('Active'),
                  value: isActive,
                  onChanged: (v) => setDialogState(() => isActive = v ?? true),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );

    if (result == true) {
      await ApiService().updateService(s.id, {
        'name': nameCtrl.text,
        'description': descCtrl.text.isEmpty ? null : descCtrl.text,
        'price': priceCtrl.text.isEmpty ? null : double.tryParse(priceCtrl.text),
        'is_active': isActive,
      });
      _load();
    }
  }

  Future<void> _delete(Service s) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Service'),
        content: Text('Delete "${s.name}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete'), style: ElevatedButton.styleFrom(backgroundColor: Colors.red)),
        ],
      ),
    );
    if (confirm == true) {
      await ApiService().deleteService(s.id);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Services'),
        actions: [
          IconButton(icon: const Icon(Icons.add), onPressed: _create),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: _services.isEmpty
                  ? const Center(child: Text('No services'))
                  : ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: _services.length,
                      itemBuilder: (_, i) => Card(
                        child: ListTile(
                          leading: const Icon(Icons.build, color: Colors.blue),
                          title: Text(_services[i].name, style: const TextStyle(fontWeight: FontWeight.w600)),
                          subtitle: Text(
                            '${_services[i].description ?? '-'}  •  \$${(_services[i].price ?? 0).toStringAsFixed(2)}',
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (!_services[i].isActive)
                                const Chip(label: Text('Inactive', style: TextStyle(fontSize: 10)), backgroundColor: Colors.red.withOpacity(0.2)),
                              IconButton(icon: const Icon(Icons.edit, size: 20), onPressed: () => _edit(_services[i])),
                              IconButton(icon: const Icon(Icons.delete, size: 20, color: Colors.red), onPressed: () => _delete(_services[i])),
                            ],
                          ),
                        ),
                      ),
                    ),
            ),
    );
  }
}
