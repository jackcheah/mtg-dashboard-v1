# UX/UI & Usability Improvement Plan

**Status:** Draft / Proposal
**Date:** 2025-12-15
**Target:** Frontend Dashboard (`dashboard_ultra_modern.html`)

## 1. Interaction Design & Flow (High Impact)

### 1.1 Replace Native Browser Dialogs
**Current State:** Uses `window.confirm()` for edits and `window.prompt()` for edit reasons. These are blocking, cannot be styled, and break the "ultra modern" immersion.
**Improvement:**
- Implement a custom **Edit Confirmation Modal**.
- Implement a custom **Reason Input Modal** (or combine with confirmation).
- **Benefit:** Consistent styling, non-blocking UI, better mobile experience.

### 1.2 "Sticky" Control Bar
**Current State:** The top bar (Timer, Round Selector, Submit Round) scrolls away. With 16 tables (16 teams), the page is very long.
**Improvement:**
- Make the top control bar (`.glass-panel`) sticky at the top of the viewport (`position: sticky`).
- Add a backdrop blur effect when scrolling over content.
- **Benefit:** Always-accessible timer and round controls without scrolling back up.

### 1.3 Smart Keyboard Navigation
**Current State:** Mouse-heavy interaction. Must click specific W/D/L buttons.
**Improvement:**
- Add keyboard shortcuts:
    - `Tab` / `Shift+Tab` to navigate players.
    - `1`, `2`, `3` or `W`, `D`, `L` keys to set scores.
    - `Ctrl+Enter` to submit the active table.
- **Benefit:** Significantly faster data entry for tournament admins.

### 1.4 Auto-Fill Losers on Win (Smart Defaulting)
**Current State:** User must manually click "L" for all 3 losers after selecting a Winner. This requires 4 clicks per table.
**Improvement:**
- **Logic:** When "Win" (5pts) is selected for Player A, automatically set players B, C, and D to "Loss" (0pts).
- **Override:** Users can distinctively change a specific player to "Draw" if needed, but the default assumes a clear winner.
- **Benefit:** Reduces clicks per table from 4 down to 1 for the most common outcome (75% reduction in physical effort).

---

## 2. Visual Layout & Information Architecture

### 2.1 "Compact Mode" Switch
**Current State:** Large, spacious cards. Great for 8 tables, but requires extensive scrolling for 16 tables (which has 4 Swiss rounds + Top 8).
**Improvement:**
- Add a toggle: **"Comfortable" (Current) vs "Compact"**.
- **Compact Mode:**
    - Reduce padding inside table cards.
    - Smaller font sizes for player names.
    - Horizontal layout for score buttons (if vertical space needs saving).
- **Benefit:** View more tables at once; less scrolling.

### 2.2 Submit Status Visuals
**Current State:** Green "SUBMITTED" badge and disabled buttons.
**Improvement:**
- **Dimming:** Reduce opacity of the entire submitted card to 0.7 to deemphasize it visually, letting unsubmitted tables "pop".
- **Focus:** Add a subtle pulse animation or highlight border to *unsubmitted* tables when >80% of round is complete.
- **Benefit:** rapid identification of pending work.

### 2.3 "Submit All" Shortcut
**Current State:** Must click "Submit Table Results" for every single table individually.
**Improvement:**
- Add a **"Batch Submit"** button in the floating header.
- Validates all filled-but-unsubmitted tables and submits them in one go.
- **Benefit:** Huge time saver for fast rounds or data entry from paper slips.

---

## 3. UI Element Refinements

### 3.1 Score Input Segmented Control
**Current State:** Three separate buttons [W] [D] [L].
**Improvement:**
- Unify into a **Segmented Control** (single pill shape with 3 segments).
- Active state fills the segment (Green/Gray/Red).
- **Benefit:** Cleaner look, clearer mutual exclusivity.

### 3.2 Dynamic Timer Visuals
**Current State:** Simple digital clock.
**Improvement:**
- Change timer color based on remaining time (e.g., turns Orange at 10m, Red at 5m).
- **Benefit:** Peripheral awareness of round time limits.

### 3.3 Toast Notification Stacking
**Current State:** Single toast or simple overlap.
**Improvement:**
- Implement a proper **Toast Stack** (notifications push previous ones down or up).
- **Benefit:** Prevents missing messages if multiple events happen quickly (e.g., auto-updates).

---

## 4. Implementation Priorities

| Priority | Feature | Effort | Impact |
|:---:|---|:---:|:---:|
| 🔴 **High** | **Custom Modals (No native prompt)** | Medium | High (UX Polish) |
| 🔴 **High** | **Sticky Header** | Low | High (Usability) |
| 🟡 **Med** | **Compact View** | Medium | Medium (Readability) |
| 🟡 **Med** | **Keyboard Shortcuts** | Medium | High (Power Users) |
| 🟢 **Low** | **Segmented Score Buttons** | Low | Low (Aesthetics) |
| 🔴 **High** | **Auto-Fill Losers** | Low | High (Efficiency) |
