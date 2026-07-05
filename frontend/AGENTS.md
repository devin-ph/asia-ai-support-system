# Frontend Instructions

These instructions apply to all files under `frontend/`.

## Purpose

The frontend is a minimal React and TypeScript interface for the
`v0.1: Runnable Vertical Slice` milestone. It renders the four demo flows
(policy chat, order lookup, ticket confirmation, admin overview) and connects
exclusively to the local backend API.

Read `../docs/demo-scope.md` before changing behavior.

## Architecture

- `src/main.tsx`: React root mount.
- `src/App.tsx`: shell layout and cross-panel state (admin refresh token).
- `src/api.ts`: typed fetch wrappers and API response interfaces.
- `src/styles.css`: global stylesheet; vanilla CSS only.
- `src/components/ChatPanel.tsx`: message form, conversation turns, tool
  events, and inline citations.
- `src/components/ConfirmCard.tsx`: pending-action confirmation and
  cancellation UI.
- `src/components/CitationPanel.tsx`: citation display for policy answers.
- `src/components/AdminOverview.tsx`: aggregate counter panel.

Keep components focused. If a new component exceeds roughly 200 lines,
consider splitting it.

## Confirmation Flow

The confirmation guardrail is the most safety-critical frontend contract:

- `ConfirmCard` must only appear when the backend returns a `pending_action`.
- The UI must never call `POST /api/actions/{action_id}/confirm` unless the
  backend previously issued that `action_id` with status `pending`.
- Buttons must be disabled while a request is in-flight (`isSubmitting`).
- Both **confirm** and **cancel** paths must be available to the user.
- After resolution, the card shows the result and does not offer the buttons
  again.

Do not bypass, auto-confirm, or remove the explicit user confirmation step.

## API Types

All request and response types live in `src/api.ts`. These types must match
the backend Pydantic schemas in `backend/app/schemas.py`:

- `ChatResponse` mirrors the chat envelope.
- `ActionConfirmResponse` mirrors the confirmation response.
- `AdminOverviewData` mirrors the admin overview.

When the backend adds or renames a field, update `api.ts` to match. Do not
add frontend-only fields to API types.

## Dependencies

- React and ReactDOM are the only runtime dependencies.
- Frontend test tooling is limited to Vitest, React Testing Library, jsdom, and
  MSW for this milestone.
- Node.js 22 LTS is the repository default selected by `../.nvmrc`.
- Node.js must satisfy `^20.19.0 || ^22.12.0`; odd and future major versions
  are intentionally unsupported until they are reviewed and added explicitly.
- Install the locked dependency graph with `npm ci`.
- Do not add Redux, Zustand, TanStack Query, Tailwind, or any UI component
  library in this milestone.
- Add a dependency only when the standard React API and vanilla CSS are
  genuinely insufficient for the task.

## Commands

```bash
npm run dev
npm run test
npm run test:watch
npm run typecheck
npm run build
```

Tests should exercise visible behavior and HTTP boundaries rather than
component implementation details or broad snapshots. Run `npm run test` and
`npm run typecheck` before committing frontend changes. Before committing or
opening a pull request, run the repository-level verification from the project
root:

```bash
python scripts/dev.py verify
```

## UI States

Every async interaction must handle three states:

- **Loading / sending**: show a visible indicator and disable the trigger.
- **Error**: display the error message to the user.
- **Disabled**: buttons are disabled when input is empty or a request is
  in-flight.

Do not remove existing loading, error, or disabled handling without a
replacement.

## Accessibility Baseline

- Interactive elements use semantic HTML (`<button>`, `<form>`, `<label>`).
- `aria-live="polite"` on the conversation container.
- `aria-label` on landmark sections (e.g. the confirm card).
- Buttons have visible text; icon-only buttons need `aria-label`.
- Form inputs have associated `<label>` elements.

Preserve these attributes when editing components.

## Style

- Vanilla CSS in `src/styles.css`. No CSS-in-JS, no utility frameworks.
- Keep user-facing Vietnamese natural and correctly accented.
- Keep code identifiers and comments in English.
- Prefer named exports for components.
- Avoid `any`; use the types from `api.ts`.
