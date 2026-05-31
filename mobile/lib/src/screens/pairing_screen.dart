import 'package:flutter/material.dart';

import '../api/odysseus_api.dart';
import '../theme.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({required this.onPaired, super.key});

  final ValueChanged<PairingResult> onPaired;

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _serverController = TextEditingController(text: 'http://localhost:7000');
  final _tokenController = TextEditingController();
  final _api = OdysseusApi();
  bool _pairing = false;
  String? _error;

  @override
  void dispose() {
    _api.close();
    _serverController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(
              padding: const EdgeInsets.all(20),
              shrinkWrap: true,
              children: [
                const _ShipMark(),
                const SizedBox(height: 24),
                Text('Pair Odysseus', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                const Text(
                  'Start pairing in the web UI, then paste the server URL and pairing token here. Your mobile token stays on this device.',
                  style: TextStyle(color: OdysseusColors.muted, height: 1.4),
                ),
                const SizedBox(height: 24),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        TextField(
                          controller: _serverController,
                          keyboardType: TextInputType.url,
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(labelText: 'Server URL', hintText: 'http://localhost:7000'),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _tokenController,
                          textInputAction: TextInputAction.done,
                          decoration: const InputDecoration(labelText: 'Pairing token'),
                          onSubmitted: (_) => _pair(),
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Text(_error!, style: const TextStyle(color: OdysseusColors.red)),
                          ),
                        ],
                        const SizedBox(height: 18),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: _pairing ? null : _pair,
                            icon: _pairing
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                : const Icon(Icons.link),
                            label: const Text('Pair device'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _pair() async {
    setState(() {
      _pairing = true;
      _error = null;
    });
    try {
      final result = await _api.completePairing(
        serverUrl: _serverController.text,
        pairingToken: _tokenController.text,
      );
      widget.onPaired(result);
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _pairing = false);
    }
  }
}

class _ShipMark extends StatelessWidget {
  const _ShipMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 72,
      height: 72,
      decoration: BoxDecoration(
        color: OdysseusColors.panel,
        border: Border.all(color: OdysseusColors.border),
        borderRadius: BorderRadius.circular(18),
      ),
      child: const Icon(Icons.sailing, color: OdysseusColors.red, size: 40),
    );
  }
}
