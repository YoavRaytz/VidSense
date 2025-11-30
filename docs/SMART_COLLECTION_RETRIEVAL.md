# Smart Collection Retrieval Feature

## Overview
Implemented intelligent collection retrieval system that finds and displays similar past searches when users perform new searches. The system uses semantic similarity to match queries and presents relevant past results, saving time and API costs.

## Key Features

### 1. **Semantic Collection Matching**
- Compares new search queries against all saved collections
- Uses vector embeddings for semantic understanding (e.g., "cock" matches "rooster")
- Threshold: 70% similarity (0.70)
- Returns full collection details ordered by relevance

### 2. **Smart Search UI**
- **Single Search Button**: Unified search action
- **"Generate Answer" Checkbox**: Toggle AI answer generation (default: ON)
- **Workflow**:
  1. User enters query and clicks Search
  2. System finds similar past collections (if any)
  3. If checkbox is ON: Also generates new AI answer
  4. Displays similar collections first, then new results

### 3. **Collection Display**
- **Header**: Shows similarity percentage, original query, save date, source count
- **Expandable Cards**: Click "Expand" to view full details
- **Full Content**:
  - AI Answer (with markdown formatting)
  - All source videos with metadata
  - Clickable videos to view details
- **Auto-expand**: Most relevant collection (highest similarity) opens automatically

### 4. **Query Embedding Generation**
- Automatically generates embeddings when saving new collections
- Backfill script for existing collections without embeddings
- 384-dimensional vectors using `sentence-transformers/all-MiniLM-L6-v2`

## Implementation Details

### Backend Changes

#### 1. **Database Schema**
```sql
ALTER TABLE collections 
ADD COLUMN query_embedding vector(384);

CREATE INDEX collections_query_embedding_idx 
ON collections USING hnsw (query_embedding vector_cosine_ops);
```

#### 2. **New Endpoint: `/search/similar-collections`**
**File**: `services/search/app/routes_search.py`

**Request**:
```json
{
  "query": "i have a video with a cock",
  "k": 10,
  "k_ann": 50
}
```

**Response**:
```json
{
  "query": "i have a video with a cock",
  "collections": [
    {
      "id": "collection_id",
      "query": "video with a rooster",
      "similarity": 0.7374,
      "ai_answer": "...",
      "videos": [...],
      "created_at": "2025-11-14T...",
      "metadata_json": {}
    }
  ]
}
```

**Logic**:
1. Generate embedding for search query
2. Query database:
   ```sql
   SELECT *, 1 - (query_embedding <=> :query_vec) AS similarity
   FROM collections
   WHERE query_embedding IS NOT NULL
     AND 1 - (query_embedding <=> :query_vec) > 0.70
   ORDER BY similarity DESC
   LIMIT 10
   ```
3. Fetch full video details for each collection
4. Return ordered by similarity (highest first)

#### 3. **Collection Creation Enhancement**
**File**: `backend/app/routes_collections.py`

Updated `create_collection()` to automatically generate embeddings:
```python
query_embedding = embed_text(payload.query)
collection = Collection(
    id=collection_id,
    query=payload.query,
    query_embedding=query_embedding,  # NEW
    ai_answer=payload.ai_answer,
    video_ids=payload.video_ids,
    metadata_json=payload.metadata_json,
)
```

#### 4. **Backfill Script**
**File**: `backend/backfill_collection_embeddings.py`

Generates embeddings for existing collections:
```bash
cd backend
python3 backfill_collection_embeddings.py
```

**Output**:
```
Found 6 collections without embeddings
Processing collection: 4e96ec9f... - 'a funny video with a rooster'
  ✓ Updated (embedding dim: 384)
...
✅ Successfully updated 6/6 collections
```

### Frontend Changes

#### 1. **API Integration**
**File**: `frontend/src/api.ts`

Added types and function:
```typescript
export interface SimilarCollectionResult {
  id: string;
  query: string;
  similarity: number;
  ai_answer: string | null;
  videos: CollectionVideo[];
  created_at: string;
  metadata_json: Record<string, any>;
}

export async function findSimilarCollections(
  query: string, 
  k: number = 10, 
  k_ann: number = 50
): Promise<SimilarCollectionsResponse>
```

#### 2. **SearchPage Redesign**
**File**: `frontend/src/pages/SearchPage.tsx`

**New State**:
```typescript
const [generateAnswer, setGenerateAnswer] = useState(true); // Checkbox
const [similarCollections, setSimilarCollections] = useState<SimilarCollectionResult[]>([]);
const [expandedCollectionIds, setExpandedCollectionIds] = useState<Set<string>>(new Set());
```

**Updated Search Logic**:
```typescript
async function handleSearch() {
  // 1. Find similar collections
  const collectionsResult = await findSimilarCollections(query, 10, 50);
  setSimilarCollections(collectionsResult.collections);
  
  // Auto-expand most similar
  if (collectionsResult.collections.length > 0) {
    setExpandedCollectionIds(new Set([collectionsResult.collections[0].id]));
  }
  
  // 2. Generate new answer if checkbox is checked
  if (generateAnswer) {
    const result = await ragAnswer(query, 20, 5);
    setRagResponse(result);
  }
  
  // 3. Get search results if no collections found
  if (collectionsResult.collections.length === 0) {
    const searchResult = await searchVideos(query, 10);
    setSearchResults(searchResult.hits);
  }
}
```

**UI Components**:
```tsx
{/* Checkbox */}
<label>
  <input
    type="checkbox"
    checked={generateAnswer}
    onChange={(e) => setGenerateAnswer(e.target.checked)}
  />
  <span>✨ Generate AI Answer</span>
</label>

{/* Similar Collections */}
{similarCollections.length > 0 && (
  <div className="card">
    <h3>💡 Similar Past Searches Found</h3>
    <p>The system detected {similarCollections.length} previous searches</p>
    
    {similarCollections.map((collection) => (
      <div key={collection.id}>
        <div className="header">
          <span>{(collection.similarity * 100).toFixed(0)}% match</span>
          <h4>{collection.query}</h4>
          <button onClick={() => toggleCollectionExpand(collection.id)}>
            {expanded ? '▲ Collapse' : '▼ Expand'}
          </button>
        </div>
        
        {expanded && (
          <>
            {/* AI Answer */}
            <ReactMarkdown>{collection.ai_answer}</ReactMarkdown>
            
            {/* Source Videos */}
            {collection.videos.map((video) => (
              <div onClick={() => handleVideoClick(video)}>
                {/* Video card with all metadata */}
              </div>
            ))}
          </>
        )}
      </div>
    ))}
  </div>
)}

{/* New RAG Answer (if generated) */}
{ragResponse && <div>...</div>}
```

## Testing & Validation

### Test Case 1: Semantic Similarity
**Query**: "i have a video with a cock"  
**Expected**: Should match collections with "rooster"

**Result**:
```bash
# Direct embedding similarity test
Similarity between "cock" and "rooster": 0.7374 (73.74%) ✅

# API endpoint test
curl -X POST http://localhost:8082/search/similar-collections \
  -d '{"query": "i have a video with a cock"}'

Response:
{
  "collections": [
    {
      "query": "video with a rooster",
      "similarity": 0.7374
    }
  ]
} ✅
```

### Test Case 2: Collection Embedding Backfill
```bash
# Before
SELECT query, (query_embedding IS NOT NULL) FROM collections;
my shoulder pain         | f
video with a rooster     | f

# After backfill
my shoulder pain         | t ✅
video with a rooster     | t ✅
```

### Test Case 3: New Collection Creation
```bash
# Save new collection
POST /collections/ {"query": "shoulder exercises", ...}

# Verify embedding generated
SELECT query, (query_embedding IS NOT NULL) FROM collections 
WHERE query = 'shoulder exercises';

shoulder exercises | t ✅
```

## Performance Considerations

1. **Index Usage**: HNSW index for fast ANN search on collections table
2. **Similarity Threshold**: 70% reduces false positives while maintaining recall
3. **Limit**: Returns max 10 similar collections to avoid overwhelming UI
4. **Caching**: Embedding model loaded once and cached in memory

## User Experience Flow

### Scenario 1: Similar Collection Found
1. User searches: "i have a video with a cock"
2. System finds: "video with a rooster" (73% match)
3. UI shows: "💡 Similar Past Searches Found"
4. Collection auto-expands showing:
   - Original AI answer about roosters
   - All source videos
   - User can view immediately without regenerating
5. If "Generate Answer" is checked:
   - New answer appears below similar collections
   - User can compare old vs new results

### Scenario 2: No Similar Collection
1. User searches: "completely new topic"
2. No collections above 70% threshold
3. If "Generate Answer" checked:
   - Generates new answer
   - Shows search results
4. If unchecked:
   - Just shows search results

### Scenario 3: Multiple Similar Collections
1. User searches: "shoulder pain"
2. Finds: "my shoulder pain" (95%), "shoulder hurts" (88%), "shoulder exercises" (75%)
3. All three shown, ordered by similarity
4. First one (95%) auto-expands
5. User can expand others to compare

## Benefits

1. **Faster Results**: Instant access to past answers without API calls
2. **Cost Savings**: Avoid regenerating answers for similar queries
3. **Better UX**: Users see what was previously found
4. **Learning System**: Accumulates knowledge over time
5. **Semantic Understanding**: Matches meaning, not just keywords

## Future Enhancements

1. **Feedback Integration**: Show feedback from similar collections
2. **Merge Results**: Combine similar collections intelligently
3. **Similarity Tuning**: User-adjustable threshold
4. **Collection Suggestions**: "Did you mean..." prompts
5. **Analytics**: Track which collections get reused most

## Related Files

- `services/search/app/routes_search.py` - Similar collections endpoint
- `services/search/app/models.py` - Collection model with query_embedding
- `backend/app/routes_collections.py` - Create collection with embeddings
- `backend/backfill_collection_embeddings.py` - Migration script
- `frontend/src/api.ts` - API types and functions
- `frontend/src/pages/SearchPage.tsx` - Smart search UI
- `backend/sql/add_collection_embeddings.sql` - SQL migration

## Troubleshooting

### Collections not appearing
```bash
# Check if embeddings exist
docker exec 2f2f5ac5192e psql -U tips -d tipsdb \
  -c "SELECT COUNT(*) FROM collections WHERE query_embedding IS NOT NULL;"

# If 0, run backfill
cd backend && python3 backfill_collection_embeddings.py
```

### Low similarity scores
```python
# Test embedding similarity
from app.embeddings import embed_text
import numpy as np

emb1 = embed_text("your query")
emb2 = embed_text("collection query")
similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
print(f"Similarity: {similarity:.4f}")
```

### Index not being used
```sql
-- Check index exists
\d collections

-- Recreate if needed
DROP INDEX IF EXISTS collections_query_embedding_idx;
CREATE INDEX collections_query_embedding_idx 
ON collections USING hnsw (query_embedding vector_cosine_ops);
```
