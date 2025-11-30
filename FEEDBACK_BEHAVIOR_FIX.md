# Feedback Behavior Fix

## Problem Summary

**Issues Reported:**
1. Feedback was persisting across page refreshes even without saving the collection
2. Same video showing both "Liked" and "Disliked" states simultaneously
3. Feedback should be tied to collection saves, not saved immediately

**User Expectations:**
- Feedback should be temporary UI state during a search session
- Feedback should only be saved to database when the collection is saved
- Toggle behavior should work: clicking same button unselects, clicking opposite switches
- After page refresh, feedback should not appear unless it was saved with a collection

## Root Cause Analysis

### Previous Behavior (Incorrect)
1. **Immediate Save**: Every feedback button click immediately saved to database via API call
2. **Persistent State**: On each search, system loaded existing feedback from database
3. **No Toggle Logic**: Always tried to INSERT new feedback (causing constraint violations)
4. **Collection-Independent**: Feedback was saved independently of collections

### Why This Was Wrong
- User wanted feedback to be part of collection workflow, not standalone
- Feedback appearing without collection save was confusing
- No way to "try out" feedback before committing

## Solution Implemented

### 1. Local-Only Feedback State

**Changed: `handleFeedback()` function**
```typescript
async function handleFeedback(videoId: string, feedbackType: 'good' | 'bad') {
  // Toggle behavior: if clicking the same feedback, unselect it
  // If clicking opposite feedback, switch to it
  setFeedback(prev => {
    const currentFeedback = prev[videoId];
    
    // If clicking the same feedback type, unselect it (set to null)
    if (currentFeedback === feedbackType) {
      console.log(`Feedback unselected: ${feedbackType} for video ${videoId}`);
      return { ...prev, [videoId]: null };
    }
    
    // Otherwise, set to new feedback type
    console.log(`Feedback selected: ${feedbackType} for video ${videoId}`);
    return { ...prev, [videoId]: feedbackType };
  });
}
```

**Key Changes:**
- ✅ No API call - feedback stays in local state only
- ✅ Toggle logic: clicking same button → unselect (null)
- ✅ Toggle logic: clicking opposite button → switch feedback
- ✅ Simple state update, no async operations

### 2. Save Feedback with Collection

**Changed: `handleSaveCollection()` function**
```typescript
async function handleSaveCollection() {
  // ... existing collection save code ...
  
  // Now save all the feedback for videos in this collection
  const feedbackPromises = Object.entries(feedback)
    .filter(([videoId, feedbackType]) => {
      // Only save feedback that is not null and for videos in this collection
      return feedbackType !== null && videoIds.includes(videoId);
    })
    .map(([videoId, feedbackType]) => {
      console.log(`Saving feedback for video ${videoId}: ${feedbackType}`);
      return saveRetrievalFeedback(query, videoId, feedbackType as 'good' | 'bad');
    });
  
  if (feedbackPromises.length > 0) {
    await Promise.all(feedbackPromises);
    console.log(`Saved ${feedbackPromises.length} feedback records with collection`);
  }
  
  alert('✅ Collection saved successfully!');
}
```

**Key Changes:**
- ✅ Feedback saved ONLY when collection is saved
- ✅ Filters out null feedback (unselected buttons)
- ✅ Only saves feedback for videos in the collection
- ✅ Batch saves all feedback in parallel

### 3. Remove Feedback Loading on Search

**Changed: `handleSearch()`, `handleGenerateNewAnswer()`**

**Before:**
```typescript
// Load existing feedback for these sources
const feedbackResponse = await getRetrievalFeedback(query, videoIds);
const feedbackMap = {};
feedbackResponse.feedback.forEach(fb => {
  feedbackMap[fb.video_id] = fb.feedback;
});
setFeedback(feedbackMap);
```

**After:**
```typescript
// Don't load existing feedback - feedback should only be visible after collection is saved
// User will set feedback during this session, and it will be saved when they save the collection
```

**Also added reset in `handleSearch()`:**
```typescript
setFeedback({}); // Reset feedback for new search - only saved collections keep feedback
```

**Key Changes:**
- ✅ No more loading feedback from database on search
- ✅ Each search starts with clean slate
- ✅ Feedback state reset when starting new search
- ✅ Only saved collections (in "Similar Past Searches") show feedback

### 4. Collection Feedback Behavior (Unchanged)

**Note:** Feedback on videos in "Similar Past Searches Found" section still saves immediately because:
- These are ALREADY saved collections
- Feedback updates existing collection metadata
- User expects changes to saved items to persist

## Behavior Comparison

### New Search Flow

| Action | Old Behavior | New Behavior |
|--------|--------------|--------------|
| User searches query | Loads existing feedback from DB | Starts with empty feedback state |
| User clicks "Like" on source | Immediately saves to DB | Updates local state only |
| User clicks "Like" again | Tries to save again (error) | Unselects (toggles off) |
| User clicks "Dislike" after "Like" | Tries to save again (error) | Switches to "Dislike" |
| User refreshes page | Feedback still visible | Feedback gone (not saved) |
| User saves collection | Collection saved only | Collection + feedback saved together |
| User refreshes after save | Feedback visible in collections | Feedback visible in similar collections section |

### Toggle Behavior

```
State: None
Click "Like" → State: Liked ✅
Click "Like" → State: None (unselected)
Click "Dislike" → State: Disliked ❌

State: Liked ✅
Click "Like" → State: None (unselected)
Click "Dislike" → State: Disliked ❌

State: Disliked ❌
Click "Dislike" → State: None (unselected)
Click "Like" → State: Liked ✅
```

## Testing Guide

### Test 1: Feedback Stays Local Until Saved
1. Search for "machine learning"
2. Click "Like" on first source
3. Verify button is highlighted green
4. **DO NOT save collection**
5. Refresh page
6. Search same query again
7. ✅ Feedback should be GONE (not persisted)

### Test 2: Toggle Behavior
1. Search for any query
2. Click "Like" on a source
3. Verify green highlight
4. Click "Like" again
5. ✅ Should unselect (return to gray)
6. Click "Dislike"
7. ✅ Should highlight red
8. Click "Like"
9. ✅ Should switch to green

### Test 3: Feedback Saves with Collection
1. Search for "neural networks"
2. Generate answer with sources
3. Click "Like" on 2 sources
4. Click "Dislike" on 1 source
5. Click "Save Collection"
6. Verify success message
7. Refresh page
8. Search same query
9. ✅ Should see collection in "Similar Past Searches"
10. ✅ Expand collection - feedback should be visible

### Test 4: No Duplicate Feedback States
1. Search any query
2. Click "Like" on a source
3. ✅ Only "Like" button should be highlighted
4. Click "Dislike" on same source
5. ✅ Only "Dislike" button should be highlighted
6. ✅ "Like" should be un-highlighted

### Test 5: Collection Feedback Still Immediate
1. Search for a query that returns saved collections
2. Expand a collection in "Similar Past Searches"
3. Click "Like" on a video in the collection
4. ✅ Should save immediately (this is correct - it's updating saved collection)
5. Refresh page
6. ✅ Feedback should persist (it's part of saved collection)

## Technical Details

### State Management

**Feedback State Variables:**
```typescript
// For new search results (temporary until collection saved)
const [feedback, setFeedback] = useState<{[videoId: string]: 'good' | 'bad' | null}>({});

// For saved collections (persisted feedback)
const [collectionFeedback, setCollectionFeedback] = useState<{[key: string]: 'good' | 'bad' | null}>({});
```

### Database Schema (Unchanged)
```sql
CREATE TABLE retrieval_feedback (
  id SERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  video_id TEXT NOT NULL,
  feedback TEXT NOT NULL CHECK (feedback IN ('good', 'bad')),
  query_embedding vector(768),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (query, video_id)  -- Prevents duplicates
);
```

### API Endpoints Used

**Save Feedback (backend/app/routes_search.py):**
```python
@router.post("/feedback")
async def save_retrieval_feedback(payload: RetrievalFeedbackPayload, db: Session = Depends(get_db)):
    # Upsert pattern: UPDATE if exists, INSERT if new
    existing_feedback = db.query(RetrievalFeedback).filter(
        RetrievalFeedback.query == payload.query,
        RetrievalFeedback.video_id == payload.video_id
    ).first()
    
    if existing_feedback:
        existing_feedback.feedback = payload.feedback
        existing_feedback.query_embedding = query_embedding
    else:
        feedback = RetrievalFeedback(...)
        db.add(feedback)
    
    db.commit()
```

**Note:** Backend upsert pattern still works correctly for when feedback IS saved (with collection or for saved collections)

## Architecture Decision

### Why This Design?

**Benefits:**
1. **User Intent Alignment**: Feedback is explicitly part of collection save workflow
2. **No Accidental Persistence**: Can't "pollute" database with trial feedback
3. **Clearer UX**: Save button has clear meaning - saves everything together
4. **Better Testing**: Can try different feedback before committing

**Trade-offs:**
1. **Data Loss Risk**: If user forgets to save collection, feedback is lost
2. **Two-Step Process**: Must both select feedback AND save collection
3. **Learning Curve**: User must understand feedback isn't instant

**Mitigation:**
- Clear "Save Collection" button always visible when feedback exists
- Could add warning: "You have unsaved feedback" before navigating away
- Could add auto-save draft collections feature in future

## Files Modified

1. **frontend/src/pages/SearchPage.tsx**
   - `handleFeedback()`: Removed API call, added toggle logic
   - `handleSaveCollection()`: Added batch feedback save
   - `handleSearch()`: Added feedback state reset
   - `handleGenerateNewAnswer()`: Removed feedback loading

## Summary

✅ Feedback is now temporary until collection is saved
✅ Toggle behavior works correctly (same button unselects, opposite switches)
✅ No more duplicate feedback states
✅ Clean separation: temporary feedback vs saved collection feedback
✅ User expectations met: feedback tied to collection workflow

The system now behaves as expected:
- **New searches**: Start with clean slate, feedback is UI-only
- **Saving collections**: Persists feedback with collection metadata
- **Saved collections**: Show persisted feedback, updates save immediately
- **Toggle behavior**: Natural and intuitive (click same to unselect)
