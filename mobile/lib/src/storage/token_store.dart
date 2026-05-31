import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SavedConnection {
  const SavedConnection({required this.serverUrl, required this.token, required this.owner});

  final String serverUrl;
  final String token;
  final String owner;
}

class TokenStore {
  static const _serverUrlKey = 'odysseus.serverUrl';
  static const _tokenKey = 'odysseus.mobileToken';
  static const _ownerKey = 'odysseus.owner';
  static const _secureStorage = FlutterSecureStorage();

  Future<SavedConnection?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final serverUrl = prefs.getString(_serverUrlKey);
    final token = await _secureStorage.read(key: _tokenKey);
    if (serverUrl == null || token == null || serverUrl.isEmpty || token.isEmpty) {
      return null;
    }
    return SavedConnection(
      serverUrl: serverUrl,
      token: token,
      owner: prefs.getString(_ownerKey) ?? 'unknown',
    );
  }

  Future<void> save(SavedConnection connection) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverUrlKey, connection.serverUrl);
    await _secureStorage.write(key: _tokenKey, value: connection.token);
    await prefs.setString(_ownerKey, connection.owner);
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_serverUrlKey);
    await _secureStorage.delete(key: _tokenKey);
    await prefs.remove(_ownerKey);
  }
}
