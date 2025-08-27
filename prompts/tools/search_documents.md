# Document Search - Funnel Approach

## Strategic Search Process

**ALWAYS use a funnel approach for travel queries:**

### Step 1: Filter by Document Type
First, search by category to narrow down relevant documents:
- For flight questions: `category="flights"` or search `"flight"`
- For hotel questions: `category="hotels"` or search `"hotel"`  
- For general travel: start broad, then narrow

### Step 2: Get Document Overview
Use broad terms to get document list with summaries:
- Search `"flight"` to see all flight documents
- Review summaries to identify relevant documents
- Look for document references (doc_1, doc_2, etc.)

### Step 3: Get Specific Details
Use `get_document` with specific document IDs to get full details:
- Take document IDs from search results
- Use get_document to access complete structured data
- Extract specific information from structured data

## Example Funnel for "What time do we land in Israel?"

### Step 1: Find flight documents
```
search_documents(query="flight", category="flights")
```

### Step 2: Review flight summaries
Look at summaries to identify return flights or destinations

### Step 3: Get detailed flight info
```
get_document(document_id="doc_1_id_here")
```
Then parse structured_data for arrival_time and arrival_city

## Smart Search Terms

**Location Intelligence:**
- "Israel" → also try "Tel Aviv", "TLV"
- "Thailand" → also try "Bangkok", "BKK"
- "UAE" → also try "Dubai", "DXB"

**Flight Timing:**
- Use: "arrival", "departure", "time"
- Airport codes: "TLV", "DXB", "BKK"
- Flight numbers: "EK", "FZ"

## Parameters
- `query` (required): Use funnel approach - start broad, then specific
- `category` (optional): Filter by document type first
- `limit` (optional): Usually 10 is fine for overview

## Multi-Step Strategy
1. **Filter** → search by document type
2. **Overview** → get summaries of relevant documents  
3. **Detail** → use get_document for specific information

Always start broad with document type, then drill down to specific details.