class Task {
  final String id;
  final String title;
  final String? description;
  final String assignedTo;
  final String? assignedToName;
  final String affairId;
  final String? affairName;
  final String? serviceId;
  final String? serviceName;
  final String createdBy;
  final String priority;
  final String status;
  final String? dueDate;
  final String createdAt;
  final String updatedAt;

  Task({
    required this.id,
    required this.title,
    this.description,
    required this.assignedTo,
    this.assignedToName,
    required this.affairId,
    this.affairName,
    this.serviceId,
    this.serviceName,
    required this.createdBy,
    required this.priority,
    required this.status,
    this.dueDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['_id'] ?? '',
      title: json['title'] ?? '',
      description: json['description'],
      assignedTo: json['assigned_to'] ?? '',
      assignedToName: json['assigned_to_name'],
      affairId: json['affair_id'] ?? '',
      affairName: json['affair_name'],
      serviceId: json['service_id'],
      serviceName: json['service_name'],
      createdBy: json['created_by'] ?? '',
      priority: json['priority'] ?? 'medium',
      status: json['status'] ?? 'pending',
      dueDate: json['due_date'],
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
    );
  }
}
