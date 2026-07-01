import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:5000/api';
  String? _token;

  static final ApiService _instance = ApiService._();
  factory ApiService() => _instance;
  ApiService._();

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('access_token');
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<void> _saveToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }

  Future<void> clearToken() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  bool get isAuthenticated => _token != null;

  Future<Map<String, dynamic>> login(String username, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'username': username, 'password': password}),
    );
    final data = jsonDecode(res.body);
    if (res.statusCode == 200) {
      await _saveToken(data['access_token']);
    }
    return data;
  }

  Future<Map<String, dynamic>> register(Map<String, dynamic> body) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> getProfile() async {
    final res = await http.get(
      Uri.parse('$baseUrl/auth/profile'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getUsers({String? role}) async {
    final uri = Uri.parse('$baseUrl/users/').replace(
      queryParameters: role != null ? {'role': role} : null,
    );
    final res = await http.get(uri, headers: _headers);
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getEmployees() async {
    final res = await http.get(
      Uri.parse('$baseUrl/users/employees'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> updateUser(String id, Map<String, dynamic> body) async {
    final res = await http.put(
      Uri.parse('$baseUrl/users/$id'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> deleteUser(String id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/users/$id'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getServices() async {
    final res = await http.get(Uri.parse('$baseUrl/services/'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> createService(Map<String, dynamic> body) async {
    final res = await http.post(Uri.parse('$baseUrl/services/'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> updateService(String id, Map<String, dynamic> body) async {
    final res = await http.put(Uri.parse('$baseUrl/services/$id'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> deleteService(String id) async {
    final res = await http.delete(Uri.parse('$baseUrl/services/$id'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getAffairs({String? customerId}) async {
    final params = <String, String>{};
    if (customerId != null) params['customer_id'] = customerId;
    final uri = Uri.parse('$baseUrl/affairs/').replace(queryParameters: params.isNotEmpty ? params : null);
    final res = await http.get(uri, headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> createAffair(Map<String, dynamic> body) async {
    final res = await http.post(Uri.parse('$baseUrl/affairs/'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> updateAffair(String id, Map<String, dynamic> body) async {
    final res = await http.put(Uri.parse('$baseUrl/affairs/$id'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> deleteAffair(String id) async {
    final res = await http.delete(Uri.parse('$baseUrl/affairs/$id'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getTasks() async {
    final res = await http.get(Uri.parse('$baseUrl/tasks/'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> createTask(Map<String, dynamic> body) async {
    final res = await http.post(
      Uri.parse('$baseUrl/tasks/'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> updateTask(String id, Map<String, dynamic> body) async {
    final res = await http.put(
      Uri.parse('$baseUrl/tasks/$id'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> deleteTask(String id) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/tasks/$id'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> getDashboardStats() async {
    final res = await http.get(
      Uri.parse('$baseUrl/dashboard/stats'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getAssignations() async {
    final res = await http.get(
      Uri.parse('$baseUrl/dashboard/assignations'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  Future<List<dynamic>> getAuditLogs({String? entityType, String? entityId}) async {
    final params = <String, String>{};
    if (entityType != null) params['entity_type'] = entityType;
    if (entityId != null) params['entity_id'] = entityId;

    final uri = Uri.parse('$baseUrl/audit/logs').replace(queryParameters: params.isNotEmpty ? params : null);
    final res = await http.get(uri, headers: _headers);
    return jsonDecode(res.body)['logs'];
  }

  String get tasksReportUrl => '$baseUrl/reports/tasks';
  String get affairsReportUrl => '$baseUrl/reports/affairs';

  Future<List<dynamic>> getCustomers() async {
    final res = await http.get(Uri.parse('$baseUrl/customers/'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> getCustomerDetail(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/customers/$id'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> createCustomer(Map<String, dynamic> body) async {
    final res = await http.post(Uri.parse('$baseUrl/customers/'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> updateCustomer(String id, Map<String, dynamic> body) async {
    final res = await http.put(Uri.parse('$baseUrl/customers/$id'), headers: _headers, body: jsonEncode(body));
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> deleteCustomer(String id) async {
    final res = await http.delete(Uri.parse('$baseUrl/customers/$id'), headers: _headers);
    return jsonDecode(res.body);
  }

  Future<Map<String, dynamic>> getAffairDetail(String id) async {
    final res = await http.get(Uri.parse('$baseUrl/affairs/$id'), headers: _headers);
    return jsonDecode(res.body);
  }
}
