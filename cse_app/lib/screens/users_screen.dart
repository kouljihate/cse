import 'package:flutter/material.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  List<User> _users = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await ApiService().getUsers();
      setState(() => _users = data.map((j) => User.fromJson(j)).toList());
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Users')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(8),
              itemCount: _users.length,
              itemBuilder: (_, i) => ListTile(
                leading: CircleAvatar(child: Text(_users[i].fullName[0])),
                title: Text(_users[i].fullName),
                subtitle: Text('${_users[i].role} - ${_users[i].email}'),
                trailing: _users[i].isActive
                    ? const Chip(label: Text('Active'), backgroundColor: Colors.green)
                    : const Chip(label: Text('Inactive'), backgroundColor: Colors.red),
              ),
            ),
    );
  }
}
