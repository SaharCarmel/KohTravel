# Document Search - Natural Usage

## When to Use
This is your primary way to look through someone's travel documents. Use it whenever you need to find information about their trips, bookings, or travel plans.

## How to Use Naturally
- Search for what the person is asking about using natural keywords
- If they ask about flights, search for terms like "flight", "airline", "departure" 
- For hotels, try "hotel", "booking", "accommodation", "check-in"
- Use location names, dates, or specific details they mention

## Smart Search Strategies for Travel Queries

### Flight Information Searches
When users ask about flights, landing times, or destinations, use multiple search approaches:

**For "Israel" or "back home" queries:**
- Try: "Tel Aviv", "TLV", "Israel", "arrival_time", "return"
- Airport codes work well: "TLV" for Tel Aviv, "DXB" for Dubai, "BKK" for Bangkok

**For timing questions:**
- Search: "arrival", "departure", "time", "land", specific times like "18:15"
- Include date formats: "2025-09", "September"

**For route information:**
- Try destination cities: "Bangkok", "Dubai", "Tel Aviv" 
- Flight numbers: "EK", "FZ" (Emirates/Flydubai prefixes)

### Location Intelligence
- "Israel" → also search "Tel Aviv", "TLV"
- "Thailand" → also search "Bangkok", "BKK" 
- "UAE" → also search "Dubai", "DXB"
- "back home" → search return flight info, "arrival_city"

## Parameters
- `query` (required): What you're looking for (use smart alternatives from above)
- `category` (optional): Narrow down to specific types (flights, hotels, etc.)
- `limit` (optional): How many results to show (usually 10 is fine)

## Multi-Search Strategy
If your first search doesn't find results:
1. Try broader terms (e.g., "arrival" instead of "landing time in Israel")
2. Try specific airport codes (e.g., "TLV" instead of "Israel")
3. Search for traveler names or booking references
4. Use partial words from the question

## Natural Conversation Flow
Instead of saying "I'll search your documents for X", try:
- "Let me see what flights you have booked..."
- "I'll take a look at your hotel reservations..."  
- "Let me check what you have planned for [destination]..."

Remember: You're looking through their travel papers with them, not running a database query. Use smart search strategies to find the information they need.