class Service {
  final String id;
  final String name;
  final String? description;
  final double? price;
  final bool isActive;
  final List<String> taskIds;
  final String createdAt;
  final String updatedAt;

  Service({
    required this.id,
    required this.name,
    this.description,
    this.price,
    required this.isActive,
    this.taskIds = const [],
    required this.createdAt,
    required this.updatedAt,
  });

  factory Service.fromJson(Map<String, dynamic> json) {
    return Service(
      id: json['_id'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      price: (json['price'] as num?)?.toDouble(),
      isActive: json['is_active'] ?? true,
      taskIds: (json['task_ids'] as List?)?.cast<String>() ?? [],
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
    );
  }
}
