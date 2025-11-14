# Collections Collapse Feature

## Overview

Added the ability to collapse/expand the entire "Similar Past Searches Found" section with a single button, giving users better control over the UI and screen space.

## Changes Made

### 1. New State Variable

**File**: `frontend/src/pages/SearchPage.tsx`

Added state to track if the similar collections section is expanded:

```typescript
const [similarCollectionsExpanded, setSimilarCollectionsExpanded] = useState(true);
```

**Default**: `true` (expanded by default, so users see results immediately)

### 2. Updated UI Layout

**Header Section**: Reorganized to have a flex layout with:
- **Left side**: Title and description
- **Right side**: "Collapse All" / "Expand All" button

```tsx
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
  <div style={{ flex: 1 }}>
    <h3>💡 Similar Past Searches Found</h3>
    <p>The system detected {count} previous searches...</p>
  </div>
  
  <button onClick={() => setSimilarCollectionsExpanded(!similarCollectionsExpanded)}>
    {similarCollectionsExpanded ? '▲ Collapse All' : '▼ Expand All'}
  </button>
</div>
```

### 3. Conditional Content Rendering

Wrapped the entire collections list and "Generate New Answer" button in a conditional fragment:

```tsx
{similarCollectionsExpanded && (
  <>
    {/* Generate New Answer button */}
    {!ragResponse && <button>Generate New Answer Anyway</button>}
    
    {/* Collections list */}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {similarCollections.map(collection => (...))}
    </div>
  </>
)}
```

## User Experience

### Initial State (Expanded)
1. User searches and similar collections are found
2. Section shows with all collections visible
3. Button displays: **"▲ Collapse All"**
4. User can see all matched collections immediately

### Collapsed State
1. User clicks "▲ Collapse All"
2. All collection cards hide
3. Button changes to: **"▼ Expand All"**
4. Only the title and count remain visible
5. Takes up minimal screen space

### Re-expanding
1. User clicks "▼ Expand All"
2. All collections become visible again
3. Button changes back to: **"▲ Collapse All"**
4. Individual collection expand/collapse states are preserved

## Benefits

### 1. **Screen Space Management**
- Users can hide collections if not relevant
- Useful when multiple collections are found (3+)
- Makes it easier to focus on AI answer or search results

### 2. **Quick Overview**
- Collapsed state still shows count: "5 previous searches"
- Users know similar results exist without seeing details
- Can expand when ready to review

### 3. **Non-Destructive**
- Collapsing doesn't remove data
- Individual collection states preserved
- Can toggle multiple times without re-fetching

### 4. **Visual Consistency**
- Matches the expand/collapse pattern used for individual collections
- Same button style and hover effects
- Intuitive arrows: ▼ = expand, ▲ = collapse

## Implementation Details

### Button Styling
```tsx
style={{
  padding: '8px 16px',
  background: '#2563eb',
  border: 'none',
  borderRadius: 6,
  color: 'white',
  cursor: 'pointer',
  fontSize: 14,
  fontWeight: 500,
  whiteSpace: 'nowrap',  // Prevents text wrapping
}}
```

### Hover Effects
- Default: `#2563eb` (blue)
- Hover: `#1d4ed8` (darker blue)
- Smooth transition with cursor pointer

### Responsive Layout
- Uses flexbox for header alignment
- Button aligned to top-right
- Description text wraps naturally
- Button stays fixed width with `whiteSpace: 'nowrap'`

## Interaction with Other Features

### 1. **Individual Collection Expand/Collapse**
- Independent from master collapse
- When section is collapsed, individual states are preserved
- When re-expanded, collections return to their previous states

### 2. **"Generate New Answer" Button**
- Hidden when section is collapsed (inside conditional)
- Reappears when section is expanded
- Only shows when no AI answer exists yet

### 3. **Auto-expand Most Relevant**
- First collection still auto-expands on search (if similarCollectionsExpanded = true)
- Master collapse takes precedence over auto-expand

## Use Cases

### Scenario 1: Too Many Results
**Problem**: User searches, finds 6 similar collections, feels overwhelmed
**Solution**: Click "Collapse All" to hide details, focus on AI answer

### Scenario 2: Quick Scan
**Problem**: User wants to know IF similar searches exist, not see details yet
**Solution**: Section shows count even when collapsed

### Scenario 3: Screen Space Limited
**Problem**: Laptop screen, collections taking too much space
**Solution**: Collapse to see AI answer and sources without scrolling

### Scenario 4: Not Relevant
**Problem**: Similar collections found but user wants fresh results
**Solution**: Collapse section, click "Generate New Answer Anyway" (when expanded)

## Future Enhancements

### Potential Improvements
1. **Remember Preference**: Store collapse state in localStorage
2. **Smart Default**: Collapse automatically if >5 collections found
3. **Keyboard Shortcut**: Toggle with Ctrl+K or similar
4. **Animation**: Smooth slide transition when collapsing/expanding
5. **Badge**: Show collection count in collapsed state more prominently

### Configuration Options
```typescript
const COLLAPSE_CONFIG = {
  defaultExpanded: true,           // Start expanded
  autoCollapseThreshold: 5,        // Auto-collapse if >5 collections
  rememberState: false,            // Persist to localStorage
  animationDuration: 200,          // Collapse/expand animation (ms)
};
```

## Testing Checklist

- [ ] Section is expanded by default
- [ ] Clicking "Collapse All" hides all collections
- [ ] Button text changes to "Expand All" when collapsed
- [ ] Clicking "Expand All" shows all collections again
- [ ] Individual collection states are preserved
- [ ] "Generate New Answer" button hidden when collapsed
- [ ] Hover effects work on collapse button
- [ ] Works with 1, 3, and 10+ collections
- [ ] No layout shift or visual glitches

## Files Modified

1. **frontend/src/pages/SearchPage.tsx**
   - Added `similarCollectionsExpanded` state
   - Updated header layout with flex
   - Added collapse/expand button
   - Wrapped content in conditional fragment

## Related Features

- Individual collection expand/collapse (per-collection state)
- Similar collections search (semantic matching at 70%)
- Generate New Answer button (approval flow)
- Auto-expand most relevant collection

## Summary

The collapse feature provides users with better control over the UI:
- **Quick toggle**: Single button collapses/expands everything
- **Space efficient**: Collapsed state shows only title and count
- **Non-destructive**: Individual states preserved
- **Consistent UX**: Matches existing expand/collapse patterns

This is especially useful when many similar collections are found, allowing users to focus on the most relevant content without clutter.
