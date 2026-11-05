---
name: Sober Precision Fintech
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4a42'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a72'
  outline-variant: '#bccac0'
  surface-tint: '#006c4a'
  primary: '#006948'
  on-primary: '#ffffff'
  primary-container: '#00855d'
  on-primary-container: '#f5fff7'
  inverse-primary: '#68dba9'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#0051d5'
  on-tertiary: '#ffffff'
  tertiary-container: '#316bf3'
  on-tertiary-container: '#fefcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f8c4'
  primary-fixed-dim: '#68dba9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#005137'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#003ea8'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  financial-numeric:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  financial-numeric-lg:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.02em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system establishes a high-trust, institutional-grade operational environment engineered for intensive financial workflows—specifically automated bank statement intake, optical extraction, and transaction classification. The aesthetic is "Sober Fintech": a disciplined union of high-density functional minimalism and corporate modernism.

### Target Audience & Emotional Intent
- **Audience:** Senior underwriters, credit risk analysts, audit teams, and financial operations controllers.
- **Emotional Stance:** Calm authority, absolute precision, zero visual fatigue, and unshakeable audit integrity. The UI prioritizes scannability, legibility, and high-speed reconciliation over decorative ornament.

### Visual Foundations & Co-Branding Integration
The visual environment pairs structural deep navy architecture with pristine, high-contrast working canvases:
- **Navigation Shell:** Deep slate/navy anchor surfaces (`#0F172A`) establish institutional structure and frame daily data operations.
- **Data Workspaces:** Crisp white surfaces (`#FFFFFF`) on tinted background canvasses (`#F8FAFC`) maximize visual acuity for high-density ledgers.
- **Brand Identity Integration:** The system houses the "befree" identity mark (featuring its soaring avian icon and gradient energy). In the dark navigation hierarchy, the brand is presented in a dedicated inverted lockup with crisp light typography, preserving brand equity without interfering with transactional semantic signals (green credits, red debits, amber warnings).

## Colors

The color palette enforces rigorous semantic separation to prevent misclassification in dense financial tables.

### Primary & Brand Colors
- **Primary Accent (`#059669` / `#10B981`):** Represents positive state execution, approved reconciliations, primary command buttons, and credit transactions.
- **Secondary Shell (`#0F172A`):** The primary architectural frame, applied to the global sidebar navigation, terminal headers, and deep contrast tooltips.
- **Tertiary Accent (`#2563EB`):** Reserved for contextual metadata, system notifications, informational tooltips, and document classification tags.

### Semantic Transaction Tokens
- **Credit / Inflow:** Emerald 600 (`#059669`) with Emerald 50 (`#ECFDF5`) pill backgrounds.
- **Debit / Outflow:** Red 600 (`#DC2626`) with Red 50 (`#FEF2F2`) pill backgrounds.
- **Attention / Needs Review:** Amber 500 (`#F59E0B`) / Amber 600 (`#D97706`) with Amber 50 (`#FFFBEB`) surfaces for unmapped categories or OCR confidence scores under 85%.
- **Info / System:** Blue 600 (`#2563EB`) with Blue 50 (`#EFF6FF`) fill.

### Neutral & Surface Hierarchy
- **Canvas Base:** `#F8FAFC` (Slate 50) and `#F1F5F9` (Slate 100) for structural division.
- **Card & Surface Base:** `#FFFFFF` pure white.
- **Borders & Dividers:** 1px hairline `#E2E8F0` (Slate 200).
- **Text Tones:** `#0F172A` (Slate 900) for primary headers and monetary figures; `#334155` (Slate 700) for body; `#64748B` (Slate 500) for metadata and labels; `#94A3B8` (Slate 400) for sidebar inactive links and disabled controls.

## Typography

The typographic engine is built on **Inter**, optimized for density and readability across multi-column financial ledgers.

### Tabular Figures & Numerics
All monetary amounts, account numbers, routing strings, and transaction counts must enforce OpenType tabular figures (`font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "cv05" 1`). This prevents character shifting across live balance feeds and ensures perfect vertical decimal alignment.

### Microcopy and Legibility
- **Field & Ledger Data:** Default body size is anchored at `13px`–`14px` (`body-sm` and `body-md`) with calibrated line heights to support high row density without vertical cramming.
- **Metadata & Tags:** Labels utilize `11px`–`12px` medium-to-semibold weights with uppercase or title-casing and slight positive tracking (`+0.02em` to `+0.04em`) to ensure legibility on tinted badge backgrounds.

## Layout & Spacing

The layout is structured around an asymmetrical enterprise workspace: a fixed, dark vertical navigation sidebar (`240px` expanded, `64px` collapsed) docked to a fluid, 12-column analytical canvas.

### Spatial Rhythm
- Base measurement follows a strict **4px/8px grid system**.
- **Compact Data Rows:** Table rows adhere to a tight `36px` to `44px` height to allow reviewers to inspect 20+ transactions simultaneously.
- **Card Separation:** Workspace cards utilize `space-lg` (16px) or `space-xl` (24px) gutters to maintain clear grouping between statement extraction summaries, confidence gauges, and reconciliation logs.

### Responsive Behavior
- **Desktop (1280px+):** Full 12-column layout; split-screen mode available (original PDF statement preview on left 40%, classified ledger on right 60%).
- **Tablet / Small Desktop (1024px–1279px):** Sidebar collapses into icon-only mode (`64px`); PDF and ledger switch to tabbed views or stacked orientation.
- **Under 1024px:** Critical approval/review flows adapt into a single-column stacked view with sticky transaction actions pinned to the viewport bottom.

## Elevation & Depth

This design system avoids high-blur drop shadows and deep blur filters in favor of **low-contrast outlines with subtle ambient elevation**. This ensures that high-volume tables remain flat, stable, and easy on the eyes.

### Surface Elevation Levels
- **Level 0 (Canvas Base):** Flat `#F8FAFC` background.
- **Level 1 (Card & Module Layer):** `#FFFFFF` surfaces wrapped in a crisp `1px solid #E2E8F0` border with an ultra-subtle ambient shadow: `0 1px 2px 0 rgba(15, 23, 42, 0.04)`.
- **Level 2 (Hover & Focus States):** Subtle lift applied to interactive table rows or draggable classification items: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`, bordered by `#CBD5E1`.
- **Level 3 (Dropdowns & Overlays):** Popovers, category pickers, and filter panels sit at `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.03)` with a `1px solid #E2E8F0` rim.
- **Level 4 (Audit Modals):** Central confirmation and verification dialogs feature `0 20px 25px -5px rgba(15, 23, 42, 0.12)` underpinned by a tinted backdrop scrim: `rgba(15, 23, 42, 0.45)` with `backdrop-filter: blur(2px)`.

## Shapes

The geometric framework balances enterprise precision with modern softness:
- **Base Components (Inputs, Buttons, Micro-pills):** `6px` to `8px` corner radius.
- **Cards, Panels, and Data Grids:** `8px` to `12px` corner radius, retaining a structured rectangular footprint that maximizes interior pixel space for tables.
- **Status Badges & Pills:** `9999px` (fully rounded) for transaction state indicators (e.g., "Reconciled", "Requires Review", "Confidence 98%").
- **Table Cell Dividers:** Clean 90-degree internal junctions within cards to ensure columns align with zero visual distraction.

## Components

### 1. Navigation Shell & Brand Lockup
- **Sidebar Container:** Deep navy `#0F172A` with `#1E293B` dividers.
- **Brand Lockup:** Houses the "befree" logo at the top-left of the sidebar (`32px` height). The wordmark renders in pure white (`#FFFFFF`) against the dark background, while the multicolored bird mark sits on an optical safe area with `12px` right padding. Sub-text reads "StatementIQ" in `11px` Slate-400 uppercase tracking (`+0.05em`).
- **Nav Links:** Slate-400 text (`#94A3B8`) on transparent hover (`#1E293B`). Active links feature `#FFFFFF` text, background tint `rgba(5, 150, 105, 0.15)`, and a solid Emerald-500 (`#10B981`) `3px` left-edge vertical indicator line.

### 2. Primary & Action Buttons
- **Primary (Reconcile / Commit / Export):** Solid Emerald-600 (`#059669`), hover Emerald-700 (`#047857`), text `#FFFFFF`, font weight 600. Includes subtle focus ring: `box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px #10B981`.
- **Secondary (Filter / Manage Rules):** Crisp white (`#FFFFFF`) fill, 1px `#E2E8F0` border, Slate-700 (`#334155`) text, hover background Slate-50 (`#F8FAFC`).
- **Destructive (Reject Batch / Flag Fraud):** Soft Red-50 (`#FEF2F2`) fill, Red-600 (`#DC2626`) text and border, hover background Red-100 (`#FEE2E2`).

### 3. Financial Data Grids & Table Rows
- **Headers:** `#F8FAFC` background, `11px` uppercase Slate-500 text, 1px bottom border `#E2E8F0`.
- **Row Heights:** `40px` compact default. Alternate zebra-striping is omitted; instead, use a clean 1px hairline divider with `#F8FAFC` hover highlighting.
- **Numeric Alignment:** Amount columns must always be right-aligned with tabular figures.
- **Credit / Debit Signage:**
  - Credits: Prefix `+`, text Emerald-600 (`#059669`).
  - Debits: Prefix `-`, text Slate-900 (`#0F172A`) or Red-600 (`#DC2626`) depending on ledger view mode.

### 4. Status Chips & Badges
- **Credit:** Emerald-50 background, Emerald-700 text, 1px Emerald-200 border.
- **Debit:** Slate-100 background, Slate-700 text, 1px Slate-200 border.
- **Needs Review:** Amber-50 background, Amber-700 text, 1px Amber-200 border, accompanied by an Amber-500 warning glyph.
- **Verified / Reconciled:** Emerald-50 background, Emerald-600 text, checked dot indicator.

### 5. Input Fields & Select Controls
- **Height & Typography:** `36px` height, `13px` Inter text, `1px solid #CBD5E1`.
- **States:** Default border `#CBD5E1`; focus border `#059669` with a subtle `2px` Emerald-100 glow; disabled background `#F1F5F9`.
- **Quick-Search / Filter Bar:** Integrated with prefix search icon and shortcut badge (`⌘K`) in Slate-400.

### 6. Review & Classification Split-Card
- **Split View:** Left pane anchors the high-resolution scanned statement PDF with bounding-box OCR highlights; right pane contains the auto-populated editable ledger cards.
- **Confidence Rating Pill:** Displays extraction confidence percentage (e.g., `99.2% OCR Match`) with color-coded dot status (Emerald > 90%, Amber 70-89%, Red < 70%).