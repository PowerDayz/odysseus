import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:odysseus_mobile/src/app.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  const secureStorageChannel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(
    secureStorageChannel,
    (call) async => null,
  );

  testWidgets('shows pairing screen on first launch', (tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const OdysseusMobileApp());
    await tester.pumpAndSettle();

    expect(find.text('Pair Odysseus'), findsOneWidget);
    expect(find.text('Pair device'), findsOneWidget);
  });
}
