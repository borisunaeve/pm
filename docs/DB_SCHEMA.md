# SQLite Database Schema

This document outlines the database design for the Project Management MVP Kanban board.

## Overview
We need to store the state of the Kanban board per user. 
The MVP only requires 1 board per user.

We will use SQLite and standard relational tables. This allows the backend and the AI to query specific cards, columns, and relationships easily.

## Schema

### 1. `users`
While the MVP uses a hardcoded "user"/"password", we will create a `users` table to support future expansion.
- `id` (String, Primary Key) - A unique identifier (e.g., "user-1")
- `username` (String, Unique)

### 2. `boards`
Represents a single Kanban board.
- `id` (String, Primary Key)
- `user_id` (String, Foreign Key -> `users.id`)
- `title` (String)

### 3. `columns`
Represents a column in the Kanban board.
- `id` (String, Primary Key)
- `board_id` (String, Foreign Key -> `boards.id`)
- `title` (String)
- `order` (Integer) - Determines the display order from left-to-right on the board.

### 4. `cards`
Represents an individual task/card.
- `id` (String, Primary Key)
- `column_id` (String, Foreign Key -> `columns.id`)
- `title` (String)
- `details` (String)
- `order` (Integer) - Determines the vertical display order within a column.

## Initial Data Population
When the server starts and the DB is created, we will seed it with the "user" account and the default Kanban board state found in `frontend/src/lib/kanban.ts`.

## SQLAlchemy / Pydantic Example Models (Backend Implementation)

```python
class CardModel(BaseModel):
    id: str
    column_id: str
    title: str
    details: str
    order: int

class ColumnModel(BaseModel):
    id: str
    board_id: str
    title: str
    order: int
    cards: List[CardModel] = []
```

## Migration from `kanban.ts` Data Structure
The frontend naturally uses:
```typescript
export type BoardData = {
  columns: Column[]; // Contains an array of cardIds
  cards: Record<string, Card>;
};
```
The FastAPI backend will query the relational tables, construct this nested JSON structure (`BoardData`), and serve it to the frontend via the API. Conversely, updates from the frontend (moving a card) will send the new `column_id` and `order`, which will update the DB.
