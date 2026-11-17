# Frontend Instructions

Applies to `frontend/`. A minimal React and TypeScript UI for the four demo
flows, talking only to the local backend. The v0.3 benchmark report is a
separate static page; it does not grow this UI.

## Map

- `src/App.tsx`: layout and cross-panel state.
- `src/api.ts`: typed fetch wrappers. Types mirror `backend/app/schemas.py`
  exactly, with no frontend-only fields.
- `src/components/`: `ChatPanel`, `ConfirmCard`, `CitationPanel`, and
  `AdminOverview`.
- `src/styles.css`: vanilla CSS only.

## Confirmation flow (safety-critical)

- Show `ConfirmCard` only when the backend returns a `pending_action`.
- Call the confirm endpoint only for an `action_id` the backend issued as
  `pending`.
- Offer both confirm and cancel, disable them while a request is in flight, and
  never auto-confirm. After resolution, show the result without the buttons.

## Rules

- Every async interaction shows loading, error, and disabled states.
- Keep semantic HTML, labelled inputs, `aria-live="polite"` on the
  conversation, and an `aria-label` on landmark sections.
- React and ReactDOM are the only runtime dependencies. Do not add state,
  styling, or UI-kit libraries.
- Node `^22.22.2 || ^24.15.0 || ^26.0.0`, default 26 via `../.nvmrc`. Change
  the range in `package.json`, `scripts/dev.py`, and CI together. Install with
  `npm ci`.
- Test visible behavior and HTTP boundaries with Vitest, Testing Library, and
  MSW. Browser flows run in Playwright (`npm run e2e`).
