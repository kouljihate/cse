import 'package:flutter/material.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class AuthProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  User? _user;
  bool _loading = false;
  String? _error;

  User? get user => _user;
  bool get loading => _loading;
  String? get error => _error;
  bool get isAuthenticated => _api.isAuthenticated;
  bool get isAdmin => _user?.isAdmin ?? false;
  bool get isEmployee => _user?.isEmployee ?? false;
  bool get isCustomer => _user?.isCustomer ?? false;

  Future<bool> login(String username, String password) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _api.login(username, password);
      if (data.containsKey('error')) {
        _error = data['error'];
        _loading = false;
        notifyListeners();
        return false;
      }
      _user = User.fromJson(data['user']);
      _loading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = 'Connection error';
      _loading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> loadProfile() async {
    try {
      final data = await _api.getProfile();
      if (data.containsKey('_id')) {
        _user = User.fromJson(data);
        notifyListeners();
      }
    } catch (_) {}
  }

  void logout() {
    _api.clearToken();
    _user = null;
    _error = null;
    notifyListeners();
  }
}
