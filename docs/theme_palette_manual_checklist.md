# Theme Palette Manual Checklist

Use this checklist to validate `Soft Light`, `High Contrast`, `Solarized Light`, and `Ocean Blue` in both light and dark mode.

## Test Matrix

Run each palette in:

- Light mode
- Dark mode

That gives 8 combinations total:

1. Soft Light + Light
2. Soft Light + Dark
3. High Contrast + Light
4. High Contrast + Dark
5. Solarized Light + Light
6. Solarized Light + Dark
7. Ocean Blue + Light
8. Ocean Blue + Dark

## Setup

1. Open `Preferences`.
2. Go to `Appearance`.
3. Disable `Follow system theme`.
4. Pick one palette from `Theme preset`.
5. Toggle `Dark mode` off or on.
6. Click `Save & Close`.

## Validate

For each of the 8 combinations, check:

1. Main window chrome:
   Menu bar, toolbars, tabs, status bar, dock titles, and scrollbars match the selected palette with readable contrast.
2. Settings dialog:
   Search highlight border, muted helper text, preview swatches, inputs, lists, and buttons use the same palette family.
3. AI Chat dock:
   Assistant bubbles, code blocks, code headers, action links, and text remain readable and do not fall back to a generic dark skin.
4. Terminal & Tasks dock:
   Terminal background, text, selection colors, and active title-tab accent match the current palette.
5. Print View:
   Editor and Markdown preview surfaces switch to a readable print presentation without ignoring the active theme tokens.
6. Hover/selection states:
   Selected tabs, checked toolbar buttons, focused inputs, and highlighted list rows remain visible without over-saturation.
7. High-contrast behavior:
   In `High Contrast`, muted text is still legible and borders remain visible in both modes.
8. Solarized/Ocean nuance:
   `Solarized Light` keeps its warm base and `Ocean Blue` keeps its cool base in both modes rather than collapsing into the default dark palette.

## Quick Regression Checks

1. Switch rapidly between all palettes without restarting the app.
2. Reopen `Preferences` and confirm the saved palette and dark-mode state persist.
3. Open AI Chat, Terminal & Tasks, and Settings in the same session after switching themes.
4. Confirm no panel shows hard-coded colors like plain black, plain white, or mismatched gray borders.

## Known Non-Goals

- The `NPP Export HTML` output in `misc.py` uses fixed export colors intentionally because it generates standalone HTML content rather than themed runtime UI.
