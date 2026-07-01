class User {
  final String id;
  final String username;
  final String email;
  final String role;

  final String fullName;
  final String? phone;
  final bool isActive;
  final String createdAt;
  final String updatedAt;

  User({
    required this.id,
    required this.username,
    required this.email,
    required this.role,
    required this.fullName,
    this.phone,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['_id'] ?? '',
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      role: json['role'] ?? 'customer',
      fullName: json['full_name'] ?? '',
      phone: json['phone'],
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
    );
  }

  bool get isAdmin => role == 'admin';
  bool get isEmployee => role == 'employee';
  bool get isCustomer => role == 'customer';
}
