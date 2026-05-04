---
name: NSS Engine Core
colors:
  surface: '#121317'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e12'
  surface-container-low: '#1a1b1f'
  surface-container: '#1e1f23'
  surface-container-high: '#292a2e'
  surface-container-highest: '#343539'
  on-surface: '#e3e2e7'
  on-surface-variant: '#baccb0'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3034'
  outline: '#85967c'
  outline-variant: '#3c4b35'
  surface-tint: '#2ae500'
  primary: '#efffe3'
  on-primary: '#053900'
  primary-container: '#39ff14'
  on-primary-container: '#107100'
  inverse-primary: '#106e00'
  secondary: '#c8c6c9'
  on-secondary: '#303033'
  secondary-container: '#47464a'
  on-secondary-container: '#b6b4b8'
  tertiary: '#fcf9fb'
  on-tertiary: '#303032'
  tertiary-container: '#dfdcdf'
  on-tertiary-container: '#616063'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#79ff5b'
  primary-fixed-dim: '#2ae500'
  on-primary-fixed: '#022100'
  on-primary-fixed-variant: '#095300'
  secondary-fixed: '#e4e2e5'
  secondary-fixed-dim: '#c8c6c9'
  on-secondary-fixed: '#1b1b1e'
  on-secondary-fixed-variant: '#47464a'
  tertiary-fixed: '#e4e2e4'
  tertiary-fixed-dim: '#c8c6c8'
  on-tertiary-fixed: '#1b1b1d'
  on-tertiary-fixed-variant: '#474649'
  background: '#121317'
  on-background: '#e3e2e7'
  surface-variant: '#343539'
typography:
  h1:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  code-lg:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '500'
    lineHeight: '1.5'
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.4'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 1px
---

## Brand & Style
The design system is engineered for high-performance developer environments, prioritizing data density, legibility, and technical precision. The brand personality is cold, calculating, and authoritative, designed to evoke the feeling of a sophisticated command center or kernel-level interface.

The visual style blends **Technical Minimalism** with **Cyberpunk** influences. It utilizes a strict "Obsidian-first" dark mode to reduce eye strain during long sessions, punctuated by high-frequency neon accents that draw attention to critical system states. Layouts are strictly governed by visible or implied grids, reinforcing a sense of architectural stability and logical order.

## Colors
The palette is anchored by **Deep Obsidian**, providing a near-infinite depth that makes the interface feel expansive yet focused. The **Neon Cyber-green** serves as the primary action color and status indicator, reserved for successful states, primary CTAs, and active progress.

Secondary colors consist of **Slate-grey** and dark charcoal tones used for structural borders and surface nesting. This design system avoids traditional box shadows, instead using color-shifting borders and subtle green glows (`rgba(57, 255, 20, 0.15)`) to indicate focus or elevation.

## Typography
This design system employs a dual-typeface strategy. **Inter** is utilized for high-level UI headings and prose to maintain modern readability and structural clarity. **JetBrains Mono** is the workhorse font for all data-driven elements, code snippets, system logs, and UI labels.

All technical labels and status indicators should be rendered in uppercase JetBrains Mono with increased letter spacing to mimic serial numbers or hardware stamping. Line heights are kept tight to support high information density.

## Layout & Spacing
The layout philosophy is a **Fixed Grid** system based on 8px increments, though internal component padding often utilizes 4px for tighter density. A visible 1px slate-grey grid pattern should be applied to the base background layer at 32px intervals to provide a technical "blueprint" feel.

Margins and gutters are rigid. Content blocks are separated by 1px borders rather than whitespace to maximize the screen real estate, creating a tiled, modular aesthetic.

## Elevation & Depth
Elevation is conveyed through **Tonal Layering** and **Subtle Glows** rather than physical shadows. 
- **Level 0 (Base):** Deep Obsidian (#0A0A0B).
- **Level 1 (Panels):** Surface Color (#121214) with a 1px Slate-grey border.
- **Level 2 (Modals/Popovers):** Surface Color with a 1px Primary Green border and a 10px outer glow in Primary Green at 10% opacity.

Depth is also suggested through the use of scan-line overlays (1px horizontal lines at 50% opacity) on background elements to push them behind the active interactive layer.

## Shapes
The shape language is strictly **Sharp (0px)**. All containers, buttons, and input fields must have square corners. This reinforces the "NSS Engine" technical identity and suggests a rigid, machine-like precision. Rounded corners are only permitted for circular status pips or specific iconography.

## Components
- **Terminal Buttons:** Rectangular, sharp-edged. The primary button features a solid Green background with black text. Hover states trigger a high-intensity green glow and a "glitch" transition effect.
- **Progress Bars:** Designed as segmented blocks (stepped) rather than a smooth continuous fill. Active segments use the primary green; inactive segments use the slate-grey border color.
- **Input Fields:** Styled like CLI prompts. They feature a 1px bottom border only, with a blinking rectangular cursor for the focus state.
- **Chips/Tags:** Monospace font inside a slate-grey outline. Active tags should toggle to a solid green outline with a faint green background tint.
- **Cards:** Simple 1px bordered boxes. The top-left corner should feature a "label-caps" header to act as a hardware-style tag for the container.
- **Data Grids:** Alternating row highlights using subtle tonal shifts (e.g., #1A1A1C) with strict vertical and horizontal borders to ensure data alignment.