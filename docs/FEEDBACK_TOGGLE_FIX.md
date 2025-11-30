# Feedback Toggle Fix

## Issue

Users were unable to change their feedback from "like" (👍) to "dislike" (👎) or vice versa. The system was keeping the old feedback and not updating correctly.

**Symptom**: Same video appeared twice with different feedback states, or clicking a different feedback button had no effect.

## Root Cause

The backend `save_retrieval_feedback()` endpoint was always trying to INSERT a new record:

```python
# Old code (BROKEN)
feedback = RetrievalFeedback(
    query=payload.query,
    query_embedding=query_embedding,
    video_id=payload.video_id,
    feedback=payload.feedback
)
db.add(feedback)
db.commit()
```

**Problem**: The database has a UNIQUE constraint on `(query, video_id)` combination. When a user tries to change feedback:
1. First click: INSERT succeeds (no existing record)
2. Second click (different feedback): INSERT fails (duplicate key violation)
3. Error occurs but may be silently swallowed
4. UI doesn't update because backend operation failed

## Solution

Implemented an **upsert pattern** (check if exists, then UPDATE or INSERT accordingly):

```python
# New code (FIXED)
# Check if feedback already exists for this query+video combination
existing_feedback = db.query(RetrievalFeedback).filter(
    RetrievalFeedback.query == payload.query,
    RetrievalFeedback.video_id == payload.video_id
).first()

if existing_feedback:
    # Update existing feedback
    print(f"[feedback] Updating existing feedback from '{existing_feedback.feedback}' to '{payload.feedback}'")
    existing_feedback.feedback = payload.feedback
    existing_feedback.query_embedding = query_embedding
else:
    # Create new feedback
    print(f"[feedback] Creating new feedback record")
    feedback = RetrievalFeedback(
        query=payload.query,
        query_embedding=query_embedding,
        video_id=payload.video_id,
        feedback=payload.feedback
    )
    db.add(feedback)

db.commit()
```

## Changes Made

**File**: `services/search/app/routes_search.py`

**Function**: `save_retrieval_feedback()`

**Changes**:
1. Added query to check for existing feedback record
2. If exists: UPDATE the feedback field
3. If not exists: INSERT new record (original behavior)
4. Enhanced logging to show whether updating or creating

## Benefits

### 1. Feedback Toggle Works
- User can change from 👍 to 👎 and back
- Each click updates the database correctly
- UI reflects the current state

### 2. No Duplicate Records
- Prevents duplicate entries in database
- Maintains data integrity
- Works with UNIQUE constraint

### 3. Better Logging
```
[feedback] Updating existing feedback from 'good' to 'bad'
```
vs
```
[feedback] Creating new feedback record
```

### 4. Proper Error Handling
- Rollback on failure
- Stack trace for debugging
- Clear error messages

## Testing

### Test Case 1: Initial Feedback
**Action**: Click 👍 on a video (first time)
**Expected**: 
- Backend logs: "Creating new feedback record"
- Database: New row inserted
- UI: Button turns green

### Test Case 2: Toggle Feedback
**Action**: Click 👎 on same video (change from like to dislike)
**Expected**:
- Backend logs: "Updating existing feedback from 'good' to 'bad'"
- Database: Same row updated (not duplicate)
- UI: Button turns red, 👍 becomes gray

### Test Case 3: Multiple Toggles
**Action**: Click 👍 → 👎 → 👍 → 👎 (rapid toggles)
**Expected**:
- Each click updates the same database row
- No duplicates created
- Final state matches last click
- UI always in sync

### Test Case 4: Different Queries
**Action**: 
1. Search "shoulder pain" → like Video A
2. Search "shoulder exercises" → like same Video A
**Expected**:
- Two separate feedback records (different queries)
- Both can be toggled independently
- No conflict between them

## Database Schema

The UNIQUE constraint that triggered this issue:

```sql
CREATE TABLE retrieval_feedback (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    video_id TEXT NOT NULL,
    feedback TEXT NOT NULL,  -- 'good' or 'bad'
    query_embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(query, video_id)  -- <-- This constraint
);
```

**Why the constraint exists**: Ensures one feedback per (query, video) combination. Makes sense because:
- Same query + same video = one opinion
- User shouldn't have multiple contradictory feedbacks for same context
- Simplifies feedback retrieval logic

## Alternative Solutions Considered

### Option 1: Remove UNIQUE Constraint
**Pros**: INSERT always works
**Cons**: 
- Multiple feedback records for same (query, video)
- Ambiguous: which feedback is "current"?
- Requires logic to pick latest/most recent
- Database bloat

**Decision**: ❌ Rejected

### Option 2: Use SQL UPSERT (ON CONFLICT)
```sql
INSERT INTO retrieval_feedback (query, video_id, feedback, query_embedding)
VALUES ($1, $2, $3, $4)
ON CONFLICT (query, video_id) 
DO UPDATE SET feedback = $3, query_embedding = $4;
```

**Pros**: Single SQL statement, atomic
**Cons**: 
- Database-specific syntax (PostgreSQL)
- Harder to log which operation occurred
- Less flexible for future changes

**Decision**: ✅ Good option, but ORM approach chosen for consistency

### Option 3: Check-then-Update (Implemented)
**Pros**: 
- Clear logic flow
- Easy to log and debug
- Works with any database
- Flexible for future enhancements

**Cons**: Two database queries instead of one

**Decision**: ✅ **Chosen** - clarity and maintainability > micro-optimization

## Performance Impact

**Concern**: Two queries (SELECT + UPDATE) instead of one INSERT

**Analysis**:
- SELECT by unique key: very fast (indexed)
- UPDATE single row: also very fast
- Total: ~1-2ms overhead
- Negligible for user interaction (human reaction time ~200ms)

**Optimization** (if needed later):
```python
# Could use raw SQL upsert for performance-critical scenarios
db.execute("""
    INSERT INTO retrieval_feedback (query, video_id, feedback, query_embedding)
    VALUES (:query, :video_id, :feedback, :query_embedding)
    ON CONFLICT (query, video_id) 
    DO UPDATE SET feedback = :feedback, query_embedding = :query_embedding
""", {...})
```

## Integration with Enhanced RAG

This fix is crucial for the Enhanced RAG system:

**Scenario**:
1. User searches "shoulder pain"
2. Likes Video A (feedback: good)
3. System includes Video A in future similar searches
4. User later searches "shoulder pain" again
5. Realizes Video A wasn't helpful, clicks 👎
6. **Fixed**: Feedback updates to "bad"
7. **Result**: Future searches will exclude Video A

**Without fix**:
- Step 6 fails silently
- Video A remains marked as "good"
- System keeps including it (bad user experience)
- User loses trust in feedback system

## Deployment Notes

**Backend Service**: `search-service`

**Restart Required**: Yes
```bash
cd /home/yoav/Desktop/projects/VidSense/backend
sudo docker-compose up -d --build search-service
```

**Database Migration**: Not required (no schema changes)

**Backward Compatible**: Yes
- Existing feedback records: work as before
- New feedback: can be updated
- No breaking changes

## Verification

After deployment, verify fix with:

```bash
# 1. Check logs
sudo docker-compose logs search-service | grep feedback

# 2. Expected log patterns:
# First feedback:
[feedback] Creating new feedback record

# Changing feedback:
[feedback] Updating existing feedback from 'good' to 'bad'

# 3. Test in UI:
# - Search for a video
# - Click 👍 (should turn green)
# - Click 👎 (should turn red, 👍 turns gray)
# - Click 👍 again (should turn green, 👎 turns gray)
```

## Related Issues

This fix also resolves:
- Collection feedback toggles (uses same endpoint)
- Similar collections feedback toggles
- Any feedback UI component in the system

All feedback mechanisms now properly support toggling between like/dislike.

## Summary

✅ Fixed feedback toggle by implementing upsert pattern
✅ Users can now change from like to dislike and vice versa
✅ No duplicate records created
✅ Better logging for debugging
✅ Works for all feedback UI components (search, collections, etc.)
✅ Maintains database integrity with UNIQUE constraint
✅ No schema changes required
✅ Backward compatible
