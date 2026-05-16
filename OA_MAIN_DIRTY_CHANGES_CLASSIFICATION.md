# OA-main Dirty Changes Classification

Updated: 2026-05-16

This file groups the current `OA-main` working tree changes before the productization commit.

| Group | Files | Purpose | Commit handling |
| --- | --- | --- | --- |
| Account/session UI | `frontend/src/api/auth.ts`, `frontend/src/api/authSession.ts`, `frontend/src/components/common/UserAccountBar.vue`, layout files, `frontend/src/styles/index.scss` | Account switch/status dropdown and session persistence | Include |
| Realtime notifications | `backend/app/api/v1/ws_notifications.py`, `backend/app/services/realtime_notification_service.py`, `frontend/src/store/notification.ts`, notification API/views/components | WebSocket/polling notification center integration | Include |
| Project fields/export normalization | `backend/app/services/project_field_normalizer.py`, project model/schema/API/export files, project list/detail/basic/export views | Normalize undertaking unit, report type, project source, export fields | Include |
| Workflow extensions | contract review, report review, signoff, mailing, invoice, archive, project flow files | Complete lifecycle from contract review to archive | Include |
| UI resilience and navigation | `frontend/src/router/index.ts`, `frontend/src/views/dashboard/HomeView.vue`, `frontend/src/views/projects/ProjectFlowView.vue` | Dynamic import recovery and todo direct navigation | Include |
| Productization docs/migrations/tests | `docs/production-deployment.md`, `docs/role-flow-acceptance-checklist.md`, `backend/migrations/versions/0003_product_schema_alignment.py`, smoke tests | Product-grade deployment, acceptance, schema, and smoke gate | Include |

No deployment-critical files are moved. Zeabur root/backend and `/frontend` deployment layout remains unchanged.
