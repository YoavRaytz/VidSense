# Collections Page Feedback Feature

## Overview
Extended the retrieval feedback system to the Collections page, allowing users to provide feedback (👍 good / 👎 bad) on videos within saved collections.

## Implementation Details

### Frontend Changes (`frontend/src/pages/CollectionsPage.tsx`)

#### 1. **Added Imports**
```typescript
import { saveRetrievalFeedback } from '../api';
```

#### 2. **Added State Management**
```typescript
// Feedback state - tracks user feedback for each video
const [feedback, setFeedback] = useState<{[videoId: string]: 'good' | 'bad' | null}>({});

// Tracks which videos are currently submitting feedback
const [feedbackSubmitting, setFeedbackSubmitting] = useState<{[videoId: string]: boolean}>({});
```

#### 3. **Added Feedback Handler**
```typescript
const handleFeedback = async (videoId: string, feedbackType: 'good' | 'bad') => {
  if (!expandedCollection) return;
  
  // Optimistic update - show feedback immediately
  setFeedback(prev => ({ ...prev, [videoId]: feedbackType }));
  setFeedbackSubmitting(prev => ({ ...prev, [videoId]: true }));
  
  try {
    // Save to backend using the collection's query
    await saveRetrievalFeedback(expandedCollection.query, videoId, feedbackType);
    console.log(`Feedback saved: ${feedbackType} for video ${videoId}`);
  } catch (error) {
    console.error('Failed to save feedback:', error);
    // Revert on error
    setFeedback(prev => ({ ...prev, [videoId]: null }));
    alert('Failed to save feedback. Please try again.');
  } finally {
    setFeedbackSubmitting(prev => ({ ...prev, [videoId]: false }));
  }
};
```

#### 4. **Added UI Components**
- **Feedback buttons** positioned on the right side, below the match score
- Buttons appear on hover over video source cards
- Green background for "good" feedback (👍)
- Red background for "bad" feedback (👎)
- Hover effects with color transitions
- Disabled state during submission

### UI Features

#### Button Styling
- **Position**: Absolute positioning (top: 48px, right: 12px) - below match score
- **Appearance**: Hidden by default (opacity: 0), shown on card hover
- **Size**: Compact (4px 8px padding, 14px font)
- **Colors**:
  - Good (selected): Green (#10b981)
  - Bad (selected): Red (#ef4444)
  - Neutral: Dark gray (#1f2937)
  - Hover: Respective color preview

#### User Experience
1. **Hover to reveal**: Move mouse over any video source card to show feedback buttons
2. **Click feedback**: Click 👍 or 👎 to provide feedback
3. **Visual confirmation**: Button changes color to indicate selected state
4. **Persistent state**: Feedback remains visible in current session
5. **Non-intrusive**: Buttons don't cover important information (match score, title)

## Workflow

1. User navigates to Collections page
2. User expands a collection to view sources
3. User hovers over a video source card
4. Feedback buttons (👍 👎) appear on the right side
5. User clicks a button to provide feedback
6. Button shows loading state (cursor: wait)
7. Feedback saved to backend with:
   - Query text (from collection)
   - Video ID
   - Feedback type ('good' or 'bad')
8. Button shows selected state with colored background
9. Future searches with similar queries will use this feedback

## Backend Integration

The Collections page uses the same backend endpoint as the Search page:

```typescript
POST /search/feedback
{
  "query": "collection query text",
  "video_id": "video_id_here",
  "feedback": "good" | "bad"
}
```

The backend:
- Generates query embedding
- Stores feedback in `retrieval_feedback` table
- Uses feedback in future similar queries (≥85% similarity)
- Includes "good" sources in RAG context
- Excludes "bad" sources from results

## Benefits

1. **Continuous Learning**: System learns from feedback on saved collections
2. **Consistent UX**: Same feedback mechanism across Search and Collections pages
3. **Improved Results**: Historical feedback improves future search quality
4. **User Control**: Users can mark helpful/unhelpful sources for training
5. **Session Persistence**: Feedback state maintained during browsing session

## Technical Notes

- **Query Source**: Uses `expandedCollection.query` for feedback context
- **Optimistic Updates**: UI updates immediately, reverts on error
- **Error Handling**: Shows alert on failure, reverts visual state
- **State Management**: Per-video feedback and submitting states
- **Hover Logic**: Uses CSS opacity and event handlers for smooth transitions

## Future Enhancements

1. **Load Existing Feedback**: Fetch and display previously saved feedback
2. **Feedback Statistics**: Show aggregate feedback for each video
3. **Bulk Actions**: Allow marking multiple sources at once
4. **Undo/Change**: Allow users to change their feedback
5. **Feedback History**: Show when feedback was given
6. **Export Feedback**: Download feedback data for analysis

## Testing

To test the feature:

1. Navigate to Collections page
2. Expand any saved collection
3. Hover over a video source card
4. Click 👍 (good) or 👎 (bad)
5. Verify button changes color
6. Check browser console for success message
7. Check backend logs to confirm feedback saved
8. Perform similar search to verify feedback is used

## Related Files

- `frontend/src/pages/CollectionsPage.tsx` - Main implementation
- `frontend/src/pages/SearchPage.tsx` - Original feedback implementation
- `frontend/src/api.ts` - API function definitions
- `services/search/app/routes_search.py` - Backend endpoints
- `services/search/app/models.py` - Database models
- `RETRIEVAL_FEEDBACK.md` - Original feature documentation
