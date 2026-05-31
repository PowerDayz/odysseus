class MobileEvent {
  const MobileEvent({
    required this.id,
    required this.type,
    required this.priority,
    this.createdAt,
    this.expiresAt,
  });

  factory MobileEvent.fromJson(Map<String, dynamic> json) {
    return MobileEvent(
      id: json['id']?.toString() ?? '',
      type: json['type']?.toString() ?? json['event_type']?.toString() ?? 'event',
      priority: json['priority']?.toString() ?? 'normal',
      createdAt: json['created_at']?.toString(),
      expiresAt: json['expires_at']?.toString(),
    );
  }

  final String id;
  final String type;
  final String priority;
  final String? createdAt;
  final String? expiresAt;
}
