import 'package:flutter/material.dart';

import '../api/odysseus_api.dart';
import '../models/mobile_event.dart';
import '../storage/token_store.dart';
import '../theme.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({required this.connection, required this.onDisconnect, super.key});

  final SavedConnection connection;
  final VoidCallback onDisconnect;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = OdysseusApi();
  late Future<_HomeData> _data;

  @override
  void initState() {
    super.initState();
    _data = _load();
  }

  @override
  void dispose() {
    _api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Odysseus'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () => setState(() => _data = _load()),
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Disconnect',
            onPressed: widget.onDisconnect,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(() => _data = _load()),
        child: FutureBuilder<_HomeData>(
          future: _data,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _ErrorState(message: snapshot.error.toString(), onRetry: () => setState(() => _data = _load()));
            }
            final data = snapshot.data!;
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _StatusCard(status: data.status, serverUrl: widget.connection.serverUrl),
                const SizedBox(height: 16),
                Text('Notifications', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                if (data.events.isEmpty)
                  const _EmptyEvents()
                else
                  for (final event in data.events) ...[
                    _EventCard(event: event, onAck: () => _ack(event.id)),
                    const SizedBox(height: 10),
                  ],
              ],
            );
          },
        ),
      ),
    );
  }

  Future<_HomeData> _load() async {
    final status = await _api.getStatus(serverUrl: widget.connection.serverUrl, token: widget.connection.token);
    final events = await _api.listEvents(serverUrl: widget.connection.serverUrl, token: widget.connection.token);
    return _HomeData(status: status, events: events);
  }

  Future<void> _ack(String eventId) async {
    await _api.ackEvent(serverUrl: widget.connection.serverUrl, token: widget.connection.token, eventId: eventId);
    if (!mounted) return;
    setState(() => _data = _load());
  }
}

class _HomeData {
  const _HomeData({required this.status, required this.events});
  final MobileStatus status;
  final List<MobileEvent> events;
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.status, required this.serverUrl});

  final MobileStatus status;
  final String serverUrl;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Connected', style: TextStyle(color: OdysseusColors.success, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text('owner: ${status.owner}'),
            Text('server: $serverUrl', style: const TextStyle(color: OdysseusColors.muted)),
            if (status.deviceName != null) Text('device: ${status.deviceName}', style: const TextStyle(color: OdysseusColors.muted)),
          ],
        ),
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event, required this.onAck});

  final MobileEvent event;
  final VoidCallback onAck;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            const Icon(Icons.notifications_none, color: OdysseusColors.red),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(event.type, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('priority: ${event.priority}', style: const TextStyle(color: OdysseusColors.muted)),
                  if (event.createdAt != null) Text(event.createdAt!, style: const TextStyle(color: OdysseusColors.muted, fontSize: 12)),
                ],
              ),
            ),
            OutlinedButton(onPressed: onAck, child: const Text('ack')),
          ],
        ),
      ),
    );
  }
}

class _EmptyEvents extends StatelessWidget {
  const _EmptyEvents();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Text('No pending notification events. All quiet on deck.', style: TextStyle(color: OdysseusColors.muted)),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Could not reach Odysseus', style: TextStyle(color: OdysseusColors.red, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Text(message, style: const TextStyle(color: OdysseusColors.muted)),
                const SizedBox(height: 14),
                FilledButton(onPressed: onRetry, child: const Text('Retry')),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
