import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/mobile_event.dart';

class PairingResult {
  const PairingResult({
    required this.serverUrl,
    required this.token,
    required this.owner,
  });

  final String serverUrl;
  final String token;
  final String owner;
}

class MobileStatus {
  const MobileStatus({required this.owner, this.deviceName});

  factory MobileStatus.fromJson(Map<String, dynamic> json) {
    final device = json['device'];
    return MobileStatus(
      owner: json['owner']?.toString() ?? 'unknown',
      deviceName: device is Map<String, dynamic> ? device['name']?.toString() : null,
    );
  }

  final String owner;
  final String? deviceName;
}

class OdysseusApiException implements Exception {
  const OdysseusApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class OdysseusApi {
  OdysseusApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<PairingResult> completePairing({
    required String serverUrl,
    required String pairingToken,
    String deviceName = 'Odysseus Flutter',
  }) async {
    final normalized = _normalizeServerUrl(serverUrl);
    final response = await _client
        .post(
          _uri(normalized, '/api/mobile/pair/complete'),
          headers: _jsonHeaders(),
          body: jsonEncode({
            'pairing_token': pairingToken.trim(),
            'device_name': deviceName,
            'platform': defaultTargetPlatform.name,
            'notification_mode': 'local',
            'notification_privacy_level': 1,
          }),
        )
        .timeout(const Duration(seconds: 15));
    final json = _decodeObject(response);
    final token = json['token']?.toString();
    if (token == null || token.isEmpty) {
      throw const OdysseusApiException('Pairing response did not include a token.');
    }
    final status = await getStatus(serverUrl: normalized, token: token);
    return PairingResult(serverUrl: normalized, token: token, owner: status.owner);
  }

  Future<MobileStatus> getStatus({required String serverUrl, required String token}) async {
    final response = await _client
        .get(
          _uri(serverUrl, '/api/mobile/status'),
          headers: _authHeaders(token),
        )
        .timeout(const Duration(seconds: 10));
    return MobileStatus.fromJson(_decodeObject(response));
  }

  Future<List<MobileEvent>> listEvents({required String serverUrl, required String token}) async {
    final response = await _client
        .get(
          _uri(serverUrl, '/api/mobile/events'),
          headers: _authHeaders(token),
        )
        .timeout(const Duration(seconds: 10));
    final json = _decodeObject(response);
    final events = json['events'];
    if (events is! List) return const [];
    return events
        .whereType<Map<String, dynamic>>()
        .map(MobileEvent.fromJson)
        .where((event) => event.id.isNotEmpty)
        .toList(growable: false);
  }

  Future<void> ackEvent({required String serverUrl, required String token, required String eventId}) async {
    final response = await _client
        .post(
          _uri(serverUrl, '/api/mobile/events/$eventId/ack'),
          headers: _authHeaders(token),
        )
        .timeout(const Duration(seconds: 10));
    _decodeObject(response);
  }

  void close() => _client.close();

  static Uri _uri(String serverUrl, String path) {
    final base = Uri.parse(_normalizeServerUrl(serverUrl));
    return base.replace(path: _joinPaths(base.path, path));
  }

  static String _normalizeServerUrl(String value) {
    final trimmed = value.trim().replaceAll(RegExp(r'/+$'), '');
    if (trimmed.isEmpty) {
      throw const OdysseusApiException('Enter your Odysseus server URL.');
    }
    final withScheme = trimmed.contains('://') ? trimmed : 'http://$trimmed';
    final uri = Uri.tryParse(withScheme);
    if (uri == null || uri.host.isEmpty || (uri.scheme != 'http' && uri.scheme != 'https')) {
      throw const OdysseusApiException('Use a valid http(s) Odysseus server URL.');
    }
    return uri.replace(path: uri.path.replaceAll(RegExp(r'/+$'), '')).toString().replaceAll(RegExp(r'/+$'), '');
  }

  static String _joinPaths(String basePath, String path) {
    final left = basePath.replaceAll(RegExp(r'/+$'), '');
    final right = path.replaceAll(RegExp(r'^/+'), '');
    return left.isEmpty ? '/$right' : '$left/$right';
  }

  static Map<String, String> _jsonHeaders() => const {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  static Map<String, String> _authHeaders(String token) => {
        ..._jsonHeaders(),
        'Authorization': 'Bearer ' + token,
      };

  static Map<String, dynamic> _decodeObject(http.Response response) {
    final text = response.body.trim();
    final decoded = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
    final object = decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final detail = object['detail']?.toString();
      throw OdysseusApiException(detail == null || detail.isEmpty ? 'Odysseus request failed (${response.statusCode}).' : detail);
    }
    return object;
  }
}
