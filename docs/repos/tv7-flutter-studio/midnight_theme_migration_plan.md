# Midnight Theme Migration Plan
**Bringing the astro-tv7 "Midnight Feel" to Flutter Client**

---

## Executive Summary

Migrate the Flutter app from the default Material 3 teal theme to match the professional "midnight blue" dark aesthetic of the astro-tv7 marketing site. This creates visual consistency across web and desktop platforms and establishes a premium, video-editor-inspired brand identity.

**Design Philosophy**: Professional dark theme inspired by DaVinci Resolve, Premiere Pro, and Final Cut Pro - NOT cyberpunk neon.

---

## 📊 Current State Analysis

### Flutter App (Current)
- **Theme**: Material 3 with `ColorScheme.fromSeed(seedColor: Colors.teal)`
- **Aesthetic**: Generic Material Design, bright teal accents
- **Customization**: None - using Flutter defaults
- **Colors**: Hardcoded throughout (`Colors.red`, `Colors.grey`, etc.)
- **Typography**: Default Roboto font family
- **Components**: Standard Material 3 widgets (no custom styling)

### Astro-TV7 (Target)
- **Theme**: Custom midnight blue with professional video editor aesthetic
- **Palette**: Midnight blue backgrounds + cyan/amber accents
- **Typography**: Instrument Sans (display) + Inter (body)
- **Components**: Custom-styled with glass effects, subtle glows, rounded pills
- **Shadows**: Deep, professional shadows (not neon)
- **Spacing**: Generous padding, consistent gaps

---

## 🎨 Color Palette Migration

### Phase 1: Core Background Colors

**Target Colors** (from `tailwind.config.js`):
```dart
// lib/theme/tv7_colors.dart
class TV7Colors {
  // Backgrounds
  static const Color bg = Color(0xFF0F1419);              // Midnight blue-tinted
  static const Color bgSecondary = Color(0xFF161B22);     // Section backgrounds
  static const Color surface = Color(0xFF1F2937);         // Cards/panels (most visible)

  // Borders
  static const Color border = Color(0xFF374151);          // Standard borders
  static const Color borderStrong = Color(0xFF4B5563);    // Emphasized borders
}
```

**Flutter Implementation**:
```dart
// In ThemeData
scaffoldBackgroundColor: TV7Colors.bg,
cardColor: TV7Colors.surface,
dividerColor: TV7Colors.border,
```

### Phase 2: Brand Accent Colors

```dart
class TV7Colors {
  // Primary Accent (Cyan)
  static const Color cyan = Color(0xFF00E5FF);            // Primary CTA
  static const Color cyanSoft = Color(0xFF4DD4F4);        // Hover state

  // Secondary Accent (Violet)
  static const Color violet = Color(0xFF7A5CFF);          // Secondary accent
  static const Color violetSoft = Color(0xFF9B82FF);      // Hover variant

  // Warm Accent (Amber - timeline/UI elements)
  static const Color amber = Color(0xFFF59E0B);           // Timeline markers, badges
  static const Color amberSoft = Color(0xFFFCD34D);       // Hover state
}
```

**Flutter ColorScheme Mapping**:
```dart
colorScheme: ColorScheme.dark(
  // Primary = Cyan (main brand color)
  primary: TV7Colors.cyan,
  onPrimary: Color(0xFF0F172A),              // Dark slate for text on cyan
  primaryContainer: TV7Colors.cyan.withOpacity(0.15),
  onPrimaryContainer: TV7Colors.cyan,

  // Secondary = Violet
  secondary: TV7Colors.violet,
  onSecondary: Colors.white,
  secondaryContainer: TV7Colors.violet.withOpacity(0.15),
  onSecondaryContainer: TV7Colors.violetSoft,

  // Tertiary = Amber (for timeline, badges)
  tertiary: TV7Colors.amber,
  onTertiary: Color(0xFF0F172A),
  tertiaryContainer: TV7Colors.amber.withOpacity(0.15),
  onTertiaryContainer: TV7Colors.amber,

  // Surfaces
  surface: TV7Colors.surface,
  onSurface: TV7Colors.textPrimary,
  surfaceContainerHighest: TV7Colors.bgSecondary,

  // Error (keep red but adjust tone)
  error: Color(0xFFEF4444),                  // Tailwind red-500
  onError: Colors.white,
)
```

### Phase 3: Text Color Hierarchy

```dart
class TV7Colors {
  // Text (tiered hierarchy)
  static const Color textPrimary = Color(0xFFF3F4F6);     // Headings, main content
  static const Color textSecondary = Color(0xFFD1D5DB);   // Body text
  static const Color textTertiary = Color(0xFF9CA3AF);    // Labels, captions, metadata
}
```

---

## 🔤 Typography Migration

### Phase 1: Google Fonts Integration

**Add Dependency** (`pubspec.yaml`):
```yaml
dependencies:
  google_fonts: ^6.2.1
```

### Phase 2: Font Configuration

```dart
// lib/theme/tv7_typography.dart
import 'package:google_fonts/google_fonts.dart';

class TV7Typography {
  // Display font (Instrument Sans) - for headings
  static TextTheme displayTextTheme(TextTheme base) {
    return GoogleFonts.instrumentSansTextTheme(base).copyWith(
      displayLarge: GoogleFonts.instrumentSans(
        fontSize: 56,
        fontWeight: FontWeight.w700,
        height: 1.1,
        letterSpacing: -0.5,
      ),
      displayMedium: GoogleFonts.instrumentSans(
        fontSize: 44,
        fontWeight: FontWeight.w600,
        height: 1.15,
        letterSpacing: -0.25,
      ),
      displaySmall: GoogleFonts.instrumentSans(
        fontSize: 36,
        fontWeight: FontWeight.w600,
        height: 1.2,
      ),
      headlineLarge: GoogleFonts.instrumentSans(
        fontSize: 32,
        fontWeight: FontWeight.w600,
        height: 1.25,
      ),
      headlineMedium: GoogleFonts.instrumentSans(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        height: 1.3,
      ),
      headlineSmall: GoogleFonts.instrumentSans(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        height: 1.33,
      ),
    );
  }

  // Body font (Inter) - for body text and UI
  static TextTheme bodyTextTheme(TextTheme base) {
    return GoogleFonts.interTextTheme(base).copyWith(
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.5,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.5,
      ),
      bodySmall: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.5,
      ),
      labelLarge: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.1,
      ),
      labelMedium: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.5,
      ),
      labelSmall: GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.5,
      ),
    );
  }

  // Merge display + body
  static TextTheme mergedTextTheme(TextTheme base) {
    final display = displayTextTheme(base);
    final body = bodyTextTheme(base);

    return base.copyWith(
      // Display uses Instrument Sans
      displayLarge: display.displayLarge,
      displayMedium: display.displayMedium,
      displaySmall: display.displaySmall,
      headlineLarge: display.headlineLarge,
      headlineMedium: display.headlineMedium,
      headlineSmall: display.headlineSmall,

      // Body uses Inter
      bodyLarge: body.bodyLarge,
      bodyMedium: body.bodyMedium,
      bodySmall: body.bodySmall,
      labelLarge: body.labelLarge,
      labelMedium: body.labelMedium,
      labelSmall: body.labelSmall,

      // Titles use Inter (UI elements)
      titleLarge: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.w600),
      titleMedium: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
      titleSmall: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
    );
  }
}
```

**Usage in ThemeData**:
```dart
theme: ThemeData(
  colorScheme: /* ... */,
  textTheme: TV7Typography.mergedTextTheme(ThemeData.dark().textTheme),
  useMaterial3: true,
)
```

---

## 🎭 Component Styling

### Phase 1: Buttons

**Primary Button** (Cyan pill with shadow):
```dart
// lib/theme/tv7_theme.dart
ElevatedButtonThemeData get elevatedButtonTheme => ElevatedButtonThemeData(
  style: ElevatedButton.styleFrom(
    backgroundColor: TV7Colors.cyan,
    foregroundColor: Color(0xFF0F172A),        // Dark text on cyan
    elevation: 0,
    shadowColor: TV7Colors.cyan.withOpacity(0.25),
    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(9999),  // Fully rounded pill
    ),
    textStyle: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w600,
    ),
  ).copyWith(
    // Hover state
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.hovered)) {
        return TV7Colors.cyanSoft.withOpacity(0.1);
      }
      return null;
    }),
    elevation: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.hovered)) return 4;
      if (states.contains(WidgetState.pressed)) return 8;
      return 0;
    }),
  ),
);
```

**Outlined Button** (Border button):
```dart
OutlinedButtonThemeData get outlinedButtonTheme => OutlinedButtonThemeData(
  style: OutlinedButton.styleFrom(
    foregroundColor: TV7Colors.textPrimary,
    side: BorderSide(color: TV7Colors.border, width: 1),
    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(9999),  // Pill shape
    ),
  ).copyWith(
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.hovered)) {
        return BorderSide(color: TV7Colors.cyan.withOpacity(0.5), width: 1);
      }
      return BorderSide(color: TV7Colors.border, width: 1);
    }),
    foregroundColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.hovered)) {
        return TV7Colors.cyan;
      }
      return TV7Colors.textPrimary;
    }),
  ),
);
```

**Text Button**:
```dart
TextButtonThemeData get textButtonTheme => TextButtonThemeData(
  style: TextButton.styleFrom(
    foregroundColor: TV7Colors.cyan,
    padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
  ).copyWith(
    foregroundColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.hovered)) {
        return TV7Colors.cyanSoft;
      }
      return TV7Colors.cyan;
    }),
  ),
);
```

### Phase 2: Cards

**Glow Panel** (standard card with glass effect):
```dart
CardTheme get cardTheme => CardTheme(
  color: TV7Colors.surface.withOpacity(0.8),
  elevation: 0,
  shadowColor: Colors.black.withOpacity(0.6),
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(12),      // rounded-xl
    side: BorderSide(color: TV7Colors.border, width: 1),
  ),
  margin: EdgeInsets.zero,
);
```

**Custom Glow Panel Widget**:
```dart
// lib/widgets/glow_panel.dart
class GlowPanel extends StatefulWidget {
  final Widget child;
  final Color? glowColor;
  final double? elevation;
  final BorderRadius? borderRadius;
  final Color? borderColor;
  final EdgeInsets? padding;
  final bool enableHoverEffect;

  const GlowPanel({
    super.key,
    required this.child,
    this.glowColor,
    this.elevation,
    this.borderRadius,
    this.borderColor,
    this.padding,
    this.enableHoverEffect = true,
  });

  @override
  State<GlowPanel> createState() => _GlowPanelState();
}

class _GlowPanelState extends State<GlowPanel> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final glowColor = widget.glowColor ?? TV7Colors.cyan;
    final borderRadius = widget.borderRadius ?? BorderRadius.circular(12);

    return MouseRegion(
      onEnter: (_) => widget.enableHoverEffect
          ? setState(() => _isHovered = true)
          : null,
      onExit: (_) => widget.enableHoverEffect
          ? setState(() => _isHovered = false)
          : null,
      child: AnimatedContainer(
        duration: Duration(milliseconds: 200),
        transform: _isHovered
            ? (Matrix4.identity()..translate(0.0, -2.0))
            : Matrix4.identity(),
        decoration: BoxDecoration(
          color: TV7Colors.surface.withOpacity(0.8),
          borderRadius: borderRadius,
          border: Border.all(
            color: _isHovered
                ? glowColor.withOpacity(0.3)
                : (widget.borderColor ?? TV7Colors.border),
            width: 1,
          ),
          boxShadow: _isHovered
              ? [
                  BoxShadow(
                    color: glowColor.withOpacity(0.15),
                    blurRadius: 20,
                    spreadRadius: 0,
                  ),
                ]
              : [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.6),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
        ),
        child: ClipRRect(
          borderRadius: borderRadius,
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 4, sigmaY: 4),
            child: Padding(
              padding: widget.padding ?? EdgeInsets.all(16),
              child: widget.child,
            ),
          ),
        ),
      ),
    );
  }
}
```

### Phase 3: Input Fields

```dart
InputDecorationTheme get inputDecorationTheme => InputDecorationTheme(
  filled: true,
  fillColor: TV7Colors.surface.withOpacity(0.6),
  border: OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: TV7Colors.border, width: 1),
  ),
  enabledBorder: OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: TV7Colors.border, width: 1),
  ),
  focusedBorder: OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: TV7Colors.cyan, width: 1),
  ),
  errorBorder: OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: Color(0xFFEF4444), width: 1),
  ),
  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  hintStyle: TextStyle(color: TV7Colors.textTertiary),
  labelStyle: TextStyle(color: TV7Colors.textSecondary),
  prefixIconColor: TV7Colors.textTertiary,
);
```

### Phase 4: Navigation Rail

```dart
NavigationRailThemeData get navigationRailTheme => NavigationRailThemeData(
  backgroundColor: TV7Colors.bgSecondary,
  selectedIconTheme: IconThemeData(color: TV7Colors.cyan, size: 24),
  unselectedIconTheme: IconThemeData(color: TV7Colors.textTertiary, size: 24),
  selectedLabelTextStyle: GoogleFonts.inter(
    color: TV7Colors.cyan,
    fontSize: 12,
    fontWeight: FontWeight.w600,
  ),
  unselectedLabelTextStyle: GoogleFonts.inter(
    color: TV7Colors.textTertiary,
    fontSize: 12,
    fontWeight: FontWeight.w500,
  ),
  indicatorColor: TV7Colors.cyan.withOpacity(0.15),
);
```

---

## 📐 Layout & Spacing

### Consistent Spacing Scale

```dart
// lib/theme/tv7_spacing.dart
class TV7Spacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  // Section padding (matches astro-tv7 SectionWrapper)
  static const EdgeInsets sectionTight = EdgeInsets.symmetric(vertical: 40);
  static const EdgeInsets sectionNormal = EdgeInsets.symmetric(vertical: 64);
  static const EdgeInsets sectionLoose = EdgeInsets.symmetric(vertical: 80);

  // Card/Panel padding
  static const EdgeInsets cardPadding = EdgeInsets.all(16);
  static const EdgeInsets panelPadding = EdgeInsets.all(24);

  // Grid gaps
  static const double gridGapSm = 16;
  static const double gridGapMd = 24;
  static const double gridGapLg = 32;
}
```

### Border Radius Scale

```dart
class TV7Radius {
  static const BorderRadius sm = BorderRadius.all(Radius.circular(8));
  static const BorderRadius md = BorderRadius.all(Radius.circular(12));
  static const BorderRadius lg = BorderRadius.all(Radius.circular(16));
  static const BorderRadius xl = BorderRadius.all(Radius.circular(24));
  static const BorderRadius pill = BorderRadius.all(Radius.circular(9999));
}
```

---

## 🎯 Implementation Phases

### **Phase 1: Core Theme Setup** (1-2 hours)
**Priority: HIGH**

**Tasks**:
1. Create `lib/theme/` directory structure:
   ```
   lib/theme/
   ├── tv7_colors.dart       # Color constants
   ├── tv7_typography.dart   # Font configuration
   ├── tv7_spacing.dart      # Spacing/radius constants
   └── tv7_theme.dart        # Main ThemeData assembly
   ```

2. Add `google_fonts` dependency to `pubspec.yaml`

3. Implement `TV7Colors` class with all color constants

4. Implement `TV7Typography` with Instrument Sans + Inter

5. Create `TV7Theme.dark()` method that returns complete `ThemeData`

6. Update `lib/app.dart` to use `TV7Theme.dark()`

**Files to Create**:
- `lib/theme/tv7_colors.dart`
- `lib/theme/tv7_typography.dart`
- `lib/theme/tv7_spacing.dart`
- `lib/theme/tv7_theme.dart`

**Files to Modify**:
- `lib/app.dart` (line 25-28)

**Testing**:
- Run app and verify midnight blue backgrounds appear
- Check that cyan accents replaced teal
- Verify fonts loaded (Instrument Sans in headers, Inter in body)

---

### **Phase 2: Component Refactoring** (3-4 hours)
**Priority: HIGH**

**Tasks**:
1. Create `lib/widgets/glow_panel.dart` - Reusable card with hover glow
2. Create `lib/widgets/accent_divider.dart` - Neon gradient divider
3. Refactor dashboard cards to use `GlowPanel`
4. Replace hardcoded colors with theme colors:
   - `Colors.red` → `theme.colorScheme.error`
   - `Colors.grey` → `TV7Colors.textTertiary`
   - `Colors.teal` → `TV7Colors.cyan`

**Files to Create**:
- `lib/widgets/glow_panel.dart`
- `lib/widgets/accent_divider.dart`
- `lib/widgets/section_header.dart`

**Files to Modify**:
- `lib/features/dashboard/dashboard_page.dart`
  - Replace `Container` cards with `GlowPanel`
  - Update header gradient to midnight blue
  - Add amber left border to video group cards

- `lib/features/ingest/ingest_page.dart`
  - Wrap forms in `GlowPanel`
  - Update button styling

- `lib/features/player/video_player_page.dart`
  - Update timeline colors (amber markers, cyan playhead)
  - Replace deprecated `surfaceVariant` with `surfaceContainerHighest`

**Testing**:
- Verify all cards have subtle cyan glow on hover
- Check that borders are midnight theme colors
- Test hover states (lift + glow effect)

---

### **Phase 3: Advanced Styling** (2-3 hours)
**Priority: MEDIUM**

**Tasks**:
1. Add custom shadows matching astro-tv7:
   ```dart
   static const List<BoxShadow> panelShadow = [
     BoxShadow(
       color: Color(0x99000000),  // rgba(0,0,0,0.6)
       blurRadius: 8,
       offset: Offset(0, 2),
     ),
   ];

   static const List<BoxShadow> accentShadow = [
     BoxShadow(
       color: Color(0x2600E5FF),  // cyan with 15% opacity
       blurRadius: 12,
       offset: Offset(0, 4),
     ),
   ];
   ```

2. Implement gradient backgrounds for hero sections:
   ```dart
   // lib/widgets/gradient_background.dart
   class MidnightGradientBackground extends StatelessWidget {
     @override
     Widget build(BuildContext context) {
       return Container(
         decoration: BoxDecoration(
           gradient: RadialGradient(
             center: Alignment.topLeft,
             radius: 1.5,
             colors: [
               TV7Colors.cyan.withOpacity(0.14),
               Colors.transparent,
             ],
             stops: [0.0, 0.25],
           ),
         ),
       );
     }
   }
   ```

3. Add accent borders (amber left border on feature cards)

4. Implement backdrop blur for panels (using `BackdropFilter`)

**Files to Create**:
- `lib/theme/tv7_shadows.dart`
- `lib/widgets/gradient_background.dart`

**Files to Modify**:
- `lib/features/dashboard/dashboard_page.dart` (add gradients to header)

**Testing**:
- Verify shadows are deep and professional (not harsh)
- Check gradient overlays are subtle (12-18% opacity)
- Test backdrop blur on cards

---

### **Phase 4: Timeline Editor Theming** (1-2 hours)
**Priority: MEDIUM**

**Tasks**:
1. Update timeline track colors:
   - Background: `TV7Colors.surface`
   - Playhead: `TV7Colors.cyan` (2px width)
   - Clip markers: `TV7Colors.amber` with 15% background
   - Selection: `TV7Colors.cyan.withOpacity(0.3)`

2. Style clip suggestion chips:
   ```dart
   Container(
     decoration: BoxDecoration(
       color: TV7Colors.amber.withOpacity(0.15),
       border: Border.all(color: TV7Colors.amber, width: 1),
       borderRadius: BorderRadius.circular(8),
     ),
     padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
     child: Text(
       'Clip 1',
       style: TextStyle(
         color: TV7Colors.amber,
         fontSize: 12,
         fontWeight: FontWeight.w600,
       ),
     ),
   )
   ```

3. Add hover effects to timeline markers

**Files to Modify**:
- `lib/features/player/video_player_page.dart`

**Testing**:
- Verify timeline is readable with midnight background
- Check amber markers stand out
- Test playhead visibility (cyan on dark background)

---

### **Phase 5: Polish & Refinements** (2-3 hours)
**Priority: LOW

**Tasks**:
1. Add loading states with cyan `CircularProgressIndicator`:
   ```dart
   CircularProgressIndicator(
     valueColor: AlwaysStoppedAnimation<Color>(TV7Colors.cyan),
     strokeWidth: 2,
   )
   ```

2. Style `SnackBar` notifications:
   ```dart
   SnackBarThemeData(
     backgroundColor: TV7Colors.surface,
     contentTextStyle: TextStyle(color: TV7Colors.textPrimary),
     shape: RoundedRectangleBorder(
       borderRadius: BorderRadius.circular(8),
       side: BorderSide(color: TV7Colors.border),
     ),
     behavior: SnackBarBehavior.floating,
   )
   ```

3. Update `AlertDialog` styling:
   ```dart
   DialogTheme(
     backgroundColor: TV7Colors.surface,
     shape: RoundedRectangleBorder(
       borderRadius: BorderRadius.circular(12),
       side: BorderSide(color: TV7Colors.border),
     ),
     titleTextStyle: GoogleFonts.instrumentSans(
       fontSize: 20,
       fontWeight: FontWeight.w600,
       color: TV7Colors.textPrimary,
     ),
   )
   ```

4. Add smooth transitions (200ms duration matching astro-tv7)

5. Implement scroll indicator (cyan-to-violet gradient progress bar)

**Files to Modify**:
- `lib/theme/tv7_theme.dart` (add SnackBarTheme, DialogTheme)
- `lib/features/dashboard/dashboard_page.dart` (update loading indicators)

**Testing**:
- Verify dialogs match midnight aesthetic
- Check snackbars are readable
- Test all interactive states

---

## 📋 Component Migration Checklist

### Dashboard Page
- [ ] Replace header gradient with midnight blue
- [ ] Wrap video cards in `GlowPanel`
- [ ] Add amber left border to video group cards
- [ ] Update "Ingest Video" FAB to cyan pill button
- [ ] Replace hardcoded `Colors.grey` with `TV7Colors.textTertiary`
- [ ] Replace hardcoded `Colors.red` with `theme.colorScheme.error`
- [ ] Add hover glow to all interactive cards
- [ ] Update search bar styling (midnight theme)

### Ingest Page
- [ ] Wrap URL input form in `GlowPanel`
- [ ] Wrap file picker area in `GlowPanel`
- [ ] Style progress logs with midnight background
- [ ] Update primary button to cyan pill
- [ ] Add backdrop blur to panels

### Player Page
- [ ] Update timeline track background to `TV7Colors.surface`
- [ ] Change playhead color to cyan (2px width)
- [ ] Style clip markers with amber accent
- [ ] Add amber background (15% opacity) to selected clips
- [ ] Update control buttons to match theme
- [ ] Fix deprecated `surfaceVariant` → `surfaceContainerHighest`
- [ ] Add glow effect to clip suggestion chips

### Login Form
- [ ] Wrap form in `GlowPanel` with cyan accent
- [ ] Update login button to cyan pill
- [ ] Style text fields with midnight theme
- [ ] Add subtle gradient background

---

## 🚨 Breaking Changes & Migrations

### Color Constant Replacements

**Find & Replace**:
```dart
// Before → After
Colors.teal → TV7Colors.cyan
Colors.grey → TV7Colors.textTertiary
Colors.grey.shade300 → TV7Colors.border
Colors.red → theme.colorScheme.error
colorScheme.surfaceVariant → colorScheme.surfaceContainerHighest
Theme.of(context).colorScheme.primaryContainer → TV7Colors.bgSecondary
```

### Widget Replacements

**Before**:
```dart
Container(
  decoration: BoxDecoration(
    color: Theme.of(context).colorScheme.surfaceContainerHighest,
    borderRadius: BorderRadius.circular(16),
  ),
  child: /* ... */,
)
```

**After**:
```dart
GlowPanel(
  borderRadius: BorderRadius.circular(16),
  child: /* ... */,
)
```

---

## 📦 File Structure (After Migration)

```
forgotten_client/lib/
├── theme/
│   ├── tv7_colors.dart          # Color palette constants
│   ├── tv7_typography.dart      # Font configuration (Instrument Sans + Inter)
│   ├── tv7_spacing.dart         # Spacing/radius scale
│   ├── tv7_shadows.dart         # Shadow definitions
│   └── tv7_theme.dart           # Main ThemeData assembly
├── widgets/
│   ├── glow_panel.dart          # Reusable card with hover glow
│   ├── accent_divider.dart      # Cyan-violet gradient divider
│   ├── section_header.dart      # Eyebrow + title + divider
│   └── gradient_background.dart # Radial gradient backgrounds
├── app.dart                      # Updated to use TV7Theme.dark()
└── features/
    ├── dashboard/
    │   └── dashboard_page.dart   # Refactored with GlowPanel
    ├── ingest/
    │   └── ingest_page.dart      # Refactored with GlowPanel
    ├── player/
    │   └── video_player_page.dart # Timeline colors updated
    └── auth/
        └── login_form.dart       # Styled with midnight theme
```

---

## 🧪 Testing Plan

### Visual Regression Testing

**Manual Checks**:
1. **Color Accuracy**: Compare side-by-side with astro-tv7 marketing site
   - Background colors match?
   - Cyan accent identical to web (#00E5FF)?
   - Amber timeline markers match (#F59E0B)?

2. **Typography**:
   - Headers use Instrument Sans?
   - Body text uses Inter?
   - Font weights match (600 for headers, 400-500 for body)?

3. **Component Parity**:
   - Cards have subtle cyan glow on hover?
   - Buttons are rounded pills?
   - Borders are professional (not harsh)?

4. **Spacing Consistency**:
   - Padding matches astro-tv7 (16px cards, 24px panels)?
   - Grid gaps are 24px?

### Automated Tests

**Widget Tests** (`test/theme/tv7_theme_test.dart`):
```dart
testWidgets('Theme uses midnight background color', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: TV7Theme.dark(),
      home: Scaffold(),
    ),
  );

  final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
  expect(scaffold.backgroundColor, TV7Colors.bg);
});

testWidgets('Primary buttons use cyan color', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: TV7Theme.dark(),
      home: Scaffold(
        body: ElevatedButton(
          onPressed: () {},
          child: Text('Test'),
        ),
      ),
    ),
  );

  final button = tester.widget<ElevatedButton>(find.byType(ElevatedButton));
  final style = button.style!;
  final bgColor = style.backgroundColor!.resolve({});
  expect(bgColor, TV7Colors.cyan);
});
```

---

## 📊 Success Metrics

**Definition of Done**:
- [ ] All hardcoded colors replaced with theme constants
- [ ] Instrument Sans used for all headers
- [ ] Inter used for all body text
- [ ] Cards have glass effect with backdrop blur
- [ ] Hover states show subtle cyan glow + lift
- [ ] Timeline uses amber markers and cyan playhead
- [ ] No Material 3 teal colors visible anywhere
- [ ] Side-by-side comparison with astro-tv7 shows consistent aesthetic
- [ ] Flutter analyze shows 0 warnings
- [ ] All widget tests pass

---

## 🎨 Design Reference

**Astro-TV7 Source**:
- Color palette: `/Users/joaquinastelarra/Documents/TV7/astro-tv7/tailwind.config.js` (lines 7-40)
- Typography: `/Users/joaquinastelarra/Documents/TV7/astro-tv7/tailwind.config.js` (lines 42-45)
- Components: `/Users/joaquinastelarra/Documents/TV7/astro-tv7/src/components/`
- Shadows: `/Users/joaquinastelarra/Documents/TV7/astro-tv7/tailwind.config.js` (lines 46-60)

**Key Files**:
- `tailwind.config.js` - Complete design system
- `src/styles/global.css` - Utility classes (glow-panel, btn-primary, etc.)
- `src/components/FeatureCard.astro` - Card with amber left border
- `src/components/Hero.astro` - Gradient backgrounds

---

## 🚀 Rollout Strategy

### Option A: Big Bang (Recommended for MVP)
**Timeline**: 1-2 days
- Implement all phases sequentially
- Single PR with complete theme migration
- Test thoroughly before merge

**Pros**: Clean, consistent migration
**Cons**: Longer dev time, larger PR

### Option B: Incremental (Feature Flags)
**Timeline**: 1 week
- Phase 1: Core theme (merged, flagged off by default)
- Phase 2-3: Components (merged incrementally)
- Phase 4-5: Polish (final PR enables flag)

**Pros**: Smaller PRs, easier review
**Cons**: More complexity, feature flag overhead

**Recommendation**: Use **Option A** - this is a visual redesign, not a feature. Easier to review/test as a cohesive unit.

---

## 📝 Documentation Updates

**After Migration**:
1. Add `docs/theme_guide.md` - Color palette, usage examples
2. Update `README.md` - Mention professional midnight aesthetic
3. Create `docs/component_catalog.md` - Showcase `GlowPanel`, buttons, etc.
4. Add screenshots to `docs/` showing before/after

---

## ⏱️ Estimated Effort

| Phase | Tasks | Time | Priority |
|-------|-------|------|----------|
| Phase 1 | Core theme setup | 1-2 hours | HIGH |
| Phase 2 | Component refactoring | 3-4 hours | HIGH |
| Phase 3 | Advanced styling | 2-3 hours | MEDIUM |
| Phase 4 | Timeline theming | 1-2 hours | MEDIUM |
| Phase 5 | Polish & refinements | 2-3 hours | LOW |
| **TOTAL** | | **9-14 hours** | |

**Recommended Sprint**: 2 days for full implementation + testing

---

## 🎯 Next Actions

1. Review this plan with team
2. Get approval for color palette changes
3. Add `google_fonts` dependency
4. Create `lib/theme/` directory
5. Start Phase 1: Core Theme Setup
6. Test on macOS/Windows/Linux for font rendering
7. Iterate based on visual comparison with astro-tv7

---

**This migration plan brings the professional, midnight-blue aesthetic from the astro-tv7 marketing site to the Flutter desktop client, creating a cohesive brand experience across web and desktop platforms.**
