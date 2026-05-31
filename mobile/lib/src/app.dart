import 'package:flutter/material.dart';

import 'api/odysseus_api.dart';
import 'screens/home_screen.dart';
import 'screens/pairing_screen.dart';
import 'storage/token_store.dart';
import 'theme.dart';

class OdysseusMobileApp extends StatelessWidget {
  const OdysseusMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Odysseus Mobile',
      debugShowCheckedModeBanner: false,
      theme: buildOdysseusTheme(),
      home: const OdysseusBootstrap(),
    );
  }
}

class OdysseusBootstrap extends StatefulWidget {
  const OdysseusBootstrap({super.key});

  @override
  State<OdysseusBootstrap> createState() => _OdysseusBootstrapState();
}

class _OdysseusBootstrapState extends State<OdysseusBootstrap> {
  final _store = TokenStore();
  late Future<SavedConnection?> _connection;

  @override
  void initState() {
    super.initState();
    _connection = _store.load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<SavedConnection?>(
      future: _connection,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        final connection = snapshot.data;
        if (connection == null) {
          return PairingScreen(onPaired: _handlePaired);
        }
        return HomeScreen(connection: connection, onDisconnect: _handleDisconnect);
      },
    );
  }

  Future<void> _handlePaired(PairingResult result) async {
    await _store.save(SavedConnection(serverUrl: result.serverUrl, token: result.token, owner: result.owner));
    if (!mounted) return;
    setState(() => _connection = _store.load());
  }

  Future<void> _handleDisconnect() async {
    await _store.clear();
    if (!mounted) return;
    setState(() => _connection = _store.load());
  }
}
