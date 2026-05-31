import 'package:flutter/material.dart';

class OdysseusColors {
  static const bg = Color(0xFF282C34);
  static const fg = Color(0xFF9CDEF2);
  static const panel = Color(0xFF111111);
  static const border = Color(0xFF355A66);
  static const red = Color(0xFFE06C75);
  static const muted = Color(0xFF828997);
  static const success = Color(0xFF50FA7B);
  static const warning = Color(0xFFF0AD4E);
}

ThemeData buildOdysseusTheme() {
  const mono = 'monospace';
  final base = ThemeData.dark(useMaterial3: true);
  final textTheme = base.textTheme.apply(
    bodyColor: OdysseusColors.fg,
    displayColor: OdysseusColors.fg,
    fontFamily: mono,
  );

  return base.copyWith(
    scaffoldBackgroundColor: OdysseusColors.bg,
    colorScheme: const ColorScheme.dark(
      primary: OdysseusColors.red,
      secondary: OdysseusColors.fg,
      surface: OdysseusColors.panel,
      error: OdysseusColors.red,
      onPrimary: OdysseusColors.panel,
      onSecondary: OdysseusColors.panel,
      onSurface: OdysseusColors.fg,
      onError: OdysseusColors.panel,
    ),
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(
      backgroundColor: OdysseusColors.panel,
      foregroundColor: OdysseusColors.fg,
      centerTitle: false,
      elevation: 0,
      titleTextStyle: TextStyle(
        color: OdysseusColors.fg,
        fontFamily: mono,
        fontSize: 18,
        fontWeight: FontWeight.w600,
      ),
    ),
    cardTheme: CardTheme(
      color: OdysseusColors.panel,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: OdysseusColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: OdysseusColors.panel,
      labelStyle: const TextStyle(color: OdysseusColors.muted),
      hintStyle: const TextStyle(color: OdysseusColors.muted),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: OdysseusColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: OdysseusColors.red, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: OdysseusColors.red),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: OdysseusColors.red, width: 1.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: OdysseusColors.red,
        foregroundColor: OdysseusColors.panel,
        textStyle: const TextStyle(fontFamily: mono, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: OdysseusColors.fg,
        side: const BorderSide(color: OdysseusColors.border),
        textStyle: const TextStyle(fontFamily: mono, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    dividerColor: OdysseusColors.border,
  );
}
