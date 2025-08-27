# Get Document - Step 3 of Search Funnel

## Funnel Strategy: Filter → Overview → Details

**This is the final step** after using search_documents to find relevant documents.

## When to Use
- **After search_documents** identifies potential documents with summaries
- **When you need specific details** like exact times, flight numbers, confirmation codes
- **To access structured data** containing precise information

## Required Funnel Approach for Travel Questions

### For Flight Timing Questions (like "What time do we land?"):
1. **First**: `search_documents(query="flight")` → get flight document list
2. **Then**: `get_document(document_id="doc_X")` → get arrival_time from structured_data
3. **Extract**: Look for `arrival_time`, `arrival_city`, `arrival_airport` in response

### For Booking Details:
1. **First**: `search_documents(query="booking")` → find reservations  
2. **Then**: `get_document(document_id="doc_X")` → get confirmation details
3. **Extract**: Look for booking_reference, dates, traveler_name

## What This Tool Provides
- **Complete structured data**: JSON with flight times, airports, dates
- **Full document content**: All text and processed information
- **Specific details**: Exact answers to user questions

## Key Structured Data Fields
**For Flight Questions:**
- `arrival_time` → "18:15" (landing time)
- `arrival_city` → "Tel Aviv" (destination)
- `arrival_airport` → "TLV" (airport code)
- `all_flights` → complete flight itinerary array

## Parameters
- `document_id` (required): Use references from search_documents results (doc_1, doc_2, etc.)

## Natural Flow
- "Let me get the complete flight details..."
- "I'll check the full itinerary for exact times..."
- "Let me pull up that boarding pass for the arrival information..."

**Never use this tool first - always start with search_documents to find the right documents, then use this for specific details.**