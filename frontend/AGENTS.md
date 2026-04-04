# Kanban Board Frontend Codebase

This document describes the existing Next.js frontend codebase for the Project Management MVP Kanban board.

## Structure

The frontend is a standard Next.js App Router project located in the `src` directory, using standard React conventions.

### `src/app/`
- `layout.tsx` - The root layout of the application.
- `page.tsx` - The main home page, which currently renders the Kanban board demo.
- `globals.css` - Global CSS styles including simple styling.

### `src/components/`
This directory holds the React components responsible for the UI:
- `KanbanBoard.tsx` - The main container component for the Kanban board.
- `KanbanColumn.tsx` - Represents a single column in the Kanban board.
- `KanbanCard.tsx` - Represents an individual card.
- `KanbanCardPreview.tsx` - Represents the preview state of a card while it's being dragged.
- `NewCardForm.tsx` - A form component used to add new cards to a column.

### `src/lib/`
Contains utility functions and types:
- `kanban.ts` - Likely contains the core data structures, types (e.g., `Card`, `Column`, `Board`), and helper functions for manipulating the Kanban state.

## Testing
- The application is set up with Vite for unit testing (`vitest.config.ts`). Test files are located next to their respective components/libs (e.g., `KanbanBoard.test.tsx`, `kanban.test.ts`).
- End-to-end testing config is available via Playwright (`playwright.config.ts`).
