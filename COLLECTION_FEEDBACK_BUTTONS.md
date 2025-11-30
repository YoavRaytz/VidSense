# Collection Feedback Buttons Feature

## Overview

Added feedback buttons (👍/👎) to all video sources displayed in the "Similar Past Searches Found" section, allowing users to provide feedback on videos from past collections directly from the search page.

## Implementation

### Frontend Changes (`frontend/src/pages/SearchPage.tsx`)

#### 1. New State Management

**Collection Feedback State**:
```typescript
// Collection feedback state (keyed by collectionId-videoId)
const [collectionFeedback, setCollectionFeedback] = useState<{[key: string]: 'good' | 'bad' | null}>({});
const [collectionFeedbackSubmitting, setCollectionFeedbackSubmitting] = useState<{[key: string]: boolean}>({});
```

**Why composite key?**
- Same video can appear in multiple collections
- Each collection uses its own query for feedback context
- Format: `"${collectionId}-${videoId}"` ensures unique tracking

#### 2. Enhanced Collection Expand Function

**Updated `toggleCollectionExpand()`**:
```typescript
async function toggleCollectionExpand(collectionId: string) {
  const isExpanding = !expandedCollectionIds.has(collectionId);
  
  // Toggle expansion state
  setExpandedCollectionIds(prev => {
    const newSet = new Set(prev);
    if (newSet.has(collectionId)) {
      newSet.delete(collectionId);
    } else {
      newSet.add(collectionId);
    }
    return newSet;
  });
  
  // Load feedback when expanding
  if (isExpanding) {
    const collection = similarCollections.find(c => c.id === collectionId);
    if (collection && collection.videos.length > 0) {
      try {
        const videoIds = collection.videos.map(v => v.id);
        const feedbackResponse = await getRetrievalFeedback(collection.query, videoIds);
        
        // Store feedback with collectionId-videoId key
        const newFeedback: {[key: string]: 'good' | 'bad' | null} = {};
        feedbackResponse.feedback.forEach(fb => {
          const key = `${collectionId}-${fb.video_id}`;
          newFeedback[key] = fb.feedback;
        });
        
        setCollectionFeedback(prev => ({ ...prev, ...newFeedback }));
      } catch (error) {
        console.error('Failed to load feedback:', error);
      }
    }
  }
}
```

**Behavior**:
- Loads feedback only when expanding (lazy loading)
- Uses collection's original query for context
- Merges with existing feedback state
- Non-blocking: errors don't prevent expansion

#### 3. Collection Feedback Handler

**New `handleCollectionFeedback()` function**:
```typescript
async function handleCollectionFeedback(
  collectionId: string,
  collectionQuery: string,
  videoId: string,
  feedbackType: 'good' | 'bad'
) {
  const key = `${collectionId}-${videoId}`;
  setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: true }));
  
  try {
    await saveRetrievalFeedback(collectionQuery, videoId, feedbackType);
    setCollectionFeedback(prev => ({ ...prev, [key]: feedbackType }));
    console.log(`Collection feedback saved: ${feedbackType} for video ${videoId}`);
  } catch (e) {
    console.error('Failed to save collection feedback:', e);
    alert(`Failed to save feedback: ${e}`);
  } finally {
    setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: false }));
  }
}
```

**Key differences from regular feedback**:
- Takes `collectionQuery` parameter (not current search query)
- Uses composite key for state management
- Saves feedback in context of original collection query

#### 4. Auto-load Feedback for First Collection

**Updated `handleSearch()`**:
```typescript
// Auto-expand the first (most similar) collection if found
if (collectionsResult.collections.length > 0) {
  const firstCollection = collectionsResult.collections[0];
  setExpandedCollectionIds(new Set([firstCollection.id]));
  
  // Load feedback for the first collection
  if (firstCollection.videos.length > 0) {
    try {
      const videoIds = firstCollection.videos.map(v => v.id);
      const feedbackResponse = await getRetrievalFeedback(firstCollection.query, videoIds);
      
      const newFeedback: {[key: string]: 'good' | 'bad' | null} = {};
      feedbackResponse.feedback.forEach(fb => {
        const key = `${firstCollection.id}-${fb.video_id}`;
        newFeedback[key] = fb.feedback;
      });
      
      setCollectionFeedback(newFeedback);
    } catch (error) {
      console.error('Failed to load feedback:', error);
    }
  }
}
```

**Why auto-load?**
- First collection is most relevant (highest similarity)
- Already expanded by default
- Users are most likely to interact with it
- Improves UX by showing feedback immediately

#### 5. Updated Video Card UI

**Added feedback buttons to each video card**:
```tsx
{collection.videos.map((video, vidIdx) => {
  const feedbackKey = `${collection.id}-${video.id}`;
  const videoFeedback = collectionFeedback[feedbackKey];
  const isSubmitting = collectionFeedbackSubmitting[feedbackKey];
  
  return (
    <div
      key={video.id}
      style={{
        position: 'relative',  // NEW: for absolute positioning of buttons
        // ... other styles
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#3b82f6';
        e.currentTarget.style.background = '#1f2937';
        const feedbackButtons = e.currentTarget.querySelector('.collection-feedback-buttons');
        if (feedbackButtons) feedbackButtons.style.opacity = '1';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#334155';
        e.currentTarget.style.background = '#1e293b';
        const feedbackButtons = e.currentTarget.querySelector('.collection-feedback-buttons');
        if (feedbackButtons) feedbackButtons.style.opacity = '0';
      }}
    >
      {/* Feedback buttons */}
      <div
        className="collection-feedback-buttons"
        style={{
          position: 'absolute',
          top: 48,  // Below match score
          right: 12,
          display: 'flex',
          gap: 6,
          opacity: 0,  // Hidden by default
          transition: 'opacity 0.2s ease',
          pointerEvents: 'auto',
          zIndex: 10,
        }}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCollectionFeedback(collection.id, collection.query, video.id, 'good');
          }}
          disabled={isSubmitting}
          style={{
            background: videoFeedback === 'good' ? '#10b981' : '#1f2937',
            border: '1px solid ' + (videoFeedback === 'good' ? '#10b981' : '#374151'),
            color: videoFeedback === 'good' ? 'white' : '#9ca3af',
            // ... hover effects
          }}
        >
          👍
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCollectionFeedback(collection.id, collection.query, video.id, 'bad');
          }}
          disabled={isSubmitting}
          style={{
            background: videoFeedback === 'bad' ? '#ef4444' : '#1f2937',
            border: '1px solid ' + (videoFeedback === 'bad' ? '#ef4444' : '#374151'),
            color: videoFeedback === 'bad' ? 'white' : '#9ca3af',
            // ... hover effects
          }}
        >
          👎
        </button>
      </div>
      
      {/* Video content... */}
    </div>
  );
})}
```

## User Experience

### Scenario 1: Search with Similar Collections

**User Action**: Searches for "shoulder exercises"

**System Response**:
1. Finds 2 similar collections
2. Auto-expands first collection (most relevant)
3. **Automatically loads feedback** for first collection's videos
4. Shows videos with feedback buttons

**User Sees**:
- 💡 Similar Past Searches Found
  - "shoulder pain relief" (80% match) [expanded]
    - 🤖 AI Answer (if exists)
    - 📚 Sources (3)
      - [1] Video A - **👍 highlighted** (user previously liked)
      - [2] Video B - **👎 highlighted** (user previously disliked)
      - [3] Video C - buttons hidden (no previous feedback)
  - "shoulder workout" (72% match) [collapsed]

### Scenario 2: Expanding Additional Collections

**User Action**: Clicks "▼ Expand" on second collection

**System Response**:
1. Expands collection
2. **Loads feedback** for that collection's videos
3. Shows feedback buttons with correct states

**Result**: Each collection shows its own feedback context

### Scenario 3: Providing New Feedback

**User Action**: Hovers over Video C, clicks 👍

**System Response**:
1. Saves feedback with collection's query context
2. Updates button to green/highlighted
3. Button stays highlighted even after moving mouse

**Database**: Feedback saved as:
```json
{
  "query": "shoulder pain relief",  // Original collection query
  "video_id": "video_c_id",
  "feedback": "good"
}
```

## Technical Details

### Feedback Context

**Important**: Feedback is saved with the **collection's original query**, not the current search query.

**Example**:
- User searches: "shoulder exercises"
- Finds collection: "shoulder pain relief"
- Likes a video in that collection
- Feedback saved with query: "shoulder pain relief" ✅
- NOT saved with query: "shoulder exercises" ❌

**Why?**
- Maintains semantic consistency
- Future searches for "shoulder pain relief" will benefit
- Feedback is tied to the original context where it was relevant

### State Management

**Composite Key Strategy**:
```typescript
const key = `${collectionId}-${videoId}`;
```

**Prevents conflicts**:
- Same video in Collection A and B
- User likes it in Collection A context
- User dislikes it in Collection B context
- Both states maintained independently

### Loading Strategy

**Lazy Loading**:
- Feedback loaded only when collection is expanded
- Reduces initial API calls
- Improves perceived performance

**Auto-loading First**:
- Exception: first collection loaded immediately
- Already expanded by default
- Most likely to be interacted with

### Button Styling

**States**:
1. **Hidden**: Default state, opacity 0
2. **Visible**: On card hover, opacity 1
3. **Not selected**: Gray background, gray text
4. **Selected**: Green (good) or red (bad), white text
5. **Submitting**: Disabled cursor, maintains state

**Interactions**:
- Hover over card → buttons fade in
- Hover over button → preview highlight
- Click button → permanent highlight
- Move mouse away → stays highlighted if selected

## Integration with Enhanced RAG

This feature complements the Enhanced RAG system:

**Flow**:
1. User searches → similar collections found
2. User provides feedback on collection videos
3. Next similar search → **RAG automatically uses this feedback**
   - Liked videos: included in sources (marked "From Collection")
   - Disliked videos: excluded from search
4. Result: Better answers based on accumulated feedback

**Example**:
```
Search 1: "shoulder pain"
→ Collection found: "shoulder exercises"
→ User likes Video A, dislikes Video B

Search 2: "shoulder pain relief" (similar)
→ RAG finds collection "shoulder exercises"
→ Automatically includes Video A (liked)
→ Automatically excludes Video B (disliked)
→ Answer uses Video A as a source
```

## Benefits

### 1. Consistent Feedback Context
- Feedback tied to original query
- Maintains semantic relationships
- More accurate learning over time

### 2. Immediate Visual Feedback
- Selected state persists
- Users see their previous choices
- Reduces duplicate feedback

### 3. Improved Discovery
- Users can refine past collections
- Feedback improves future similar searches
- Continuous improvement cycle

### 4. Non-Intrusive UX
- Buttons hidden by default
- Only visible on hover
- Doesn't clutter the interface
- Same pattern as main sources section

### 5. Lazy Loading Performance
- Feedback loaded on demand
- Reduces initial API calls
- Faster page load times

## Testing

### Test Case 1: Feedback Loading

**Setup**:
1. Create collection "test collection" with 3 videos
2. Add feedback: like video A, dislike video B
3. Search for similar query

**Expected**:
- Collection appears in "Similar Past Searches"
- Expand collection
- Video A shows 👍 highlighted (green)
- Video B shows 👎 highlighted (red)
- Video C shows both buttons unhighlighted (gray)

### Test Case 2: Feedback Saving

**Setup**:
1. Find similar collection
2. Expand collection
3. Click 👍 on previously unfeedback video

**Expected**:
- Button turns green immediately
- Database updated with collection's query
- Stays green after mouse moves away
- Refresh page: still shows green

### Test Case 3: Multiple Collections

**Setup**:
1. Search finds 3 similar collections
2. Same video appears in 2 different collections
3. Like it in first collection, dislike in second

**Expected**:
- First collection: video shows 👍 (green)
- Second collection: video shows 👎 (red)
- Independent state management
- Both feedbacks saved with different query contexts

### Test Case 4: Auto-load First Collection

**Setup**:
1. Search finds similar collections
2. First collection auto-expands

**Expected**:
- Feedback loads automatically (no manual expand needed)
- Buttons show correct state immediately
- No delay in seeing feedback

## Database Schema

Uses existing `retrieval_feedback` table:

```sql
CREATE TABLE retrieval_feedback (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,              -- Collection's original query
    video_id TEXT NOT NULL,
    feedback TEXT NOT NULL,           -- 'good' or 'bad'
    query_embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(query, video_id)
);
```

**No schema changes required!**

## Future Enhancements

### Potential Improvements

1. **Bulk Feedback**:
   - "Like all" / "Dislike all" button
   - Useful for very relevant/irrelevant collections

2. **Feedback Count Badge**:
   - Show count of liked/disliked videos per collection
   - E.g., "5 liked, 2 disliked" next to collection title

3. **Feedback Filters**:
   - Filter collections by feedback status
   - "Show only collections with liked videos"

4. **Feedback Sync**:
   - Sync feedback across similar collections
   - "Video A liked in Collection 1 → suggest for Collection 2"

5. **Undo Feature**:
   - Quick undo after clicking feedback
   - 2-second toast: "Feedback saved. Undo?"

6. **Keyboard Shortcuts**:
   - Hover + press 'g' for good
   - Hover + press 'b' for bad
   - Faster for power users

## Troubleshooting

### Issue: Feedback Not Showing

**Symptoms**: Buttons always gray, no highlighting

**Causes**:
1. Feedback not loading (API error)
2. Wrong composite key
3. Collection not expanded

**Fix**:
```typescript
// Check console logs
console.log('Collection feedback:', collectionFeedback);
console.log('Expected key:', `${collectionId}-${videoId}`);

// Verify API response
const feedbackResponse = await getRetrievalFeedback(collection.query, videoIds);
console.log('Feedback response:', feedbackResponse);
```

### Issue: Feedback Saves But Doesn't Show

**Symptoms**: Feedback saves (no error) but button stays gray

**Causes**:
- State update not triggering re-render
- Composite key mismatch

**Fix**:
```typescript
// Verify state update
setCollectionFeedback(prev => {
  console.log('Previous state:', prev);
  console.log('New state:', { ...prev, [key]: feedbackType });
  return { ...prev, [key]: feedbackType };
});
```

### Issue: Same Video Different States

**Symptoms**: Video shows different feedback in different collections

**Status**: **This is expected behavior!**

**Explanation**:
- Each collection has its own context
- Same video can be relevant in one context, not in another
- Feedback is context-dependent

**Example**:
- Video about "push-ups"
- Liked in "chest workout" collection
- Disliked in "shoulder rehab" collection
- Both are correct in their contexts!

## Summary

Successfully added feedback buttons to the Similar Past Searches Found section, providing:

✅ Feedback buttons (👍/👎) on all collection videos
✅ Automatic feedback loading when expanding collections
✅ Auto-load for first (most relevant) collection
✅ Visual indication of selected feedback state
✅ Proper context (using collection's original query)
✅ Hover-based UI (non-intrusive)
✅ Lazy loading for performance
✅ Independent state per collection
✅ Full integration with Enhanced RAG system

This completes the feedback system, allowing users to provide feedback at every stage: during initial search, when reviewing collections, and when browsing past searches. All feedback contributes to improving future AI-generated answers through the Enhanced RAG system.
