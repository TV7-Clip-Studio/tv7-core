# TV7 Product Roadmap

## Phase 1: Technical Debt & Cleanup (Immediate Priority)

### Backend Legacy Cleanup
> **Context**: The backend contains legacy code that must be removed before further feature development.
- [ ] Audit existing endpoints for unused legacy logic.
- [ ] Remove unused media processing code (since backend is now control-plane only).
- [ ] Remove any legacy scheduling logic that predates the "credits" system if applicable.
- [ ] Verify `dramatiq` worker setup focuses **only** on posting, not processing.

## Phase 2: Architecture Sync
- [ ] Ensure `tv7-flutter-studio` implements the "Post Now" vs "Schedule" distinction correctly.
- [ ] Verify `tv7-engine` API surface matches the "local compute only" mandate.
- [ ] Validate `tv7-fastapi-backend` credit ledger implementation.

## Phase 3: Feature Development
*To be populated after cleanup.*
