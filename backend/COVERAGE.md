# Test Coverage Report

**Current Overall Coverage: 44%**

## Summary
The test suite has been stabilized, and all critical modules (`auth`, `notes`, `integrations`, `analysis`) have passing tests. Coverage has improved significantly in the Integrations Router due to new tests.

## Coverage Gaps (Prioritized)

| Module | Coverage % | Key Missing Tests |
| :--- | :--- | :--- |
| `app/api/routers/payment.py` | Low | Stripe webhook, subscription lifecycle, checkout sessions |
| `app/api/routers/admin.py` | 10% | Admin dashboard stats, user management, plan updates |
| `app/services/integrations/` | Mixed | Provider-specific logic (Notion, Todoist, Slack, etc.) needs mocking. |
| `app/api/routers/notifications.py`| Low | Push subscription, notification delivery |
| `app/api/routers/users.py` | Low | Profile updates, onboarding status |

## Detailed Coverage by Component

### Core Services (High Confidence)
- `app/core/analyze_core.py`: 79%
- `app/core/rag_service.py`: 85%
- `app/core/security.py`: 90%
- `app/services/pipeline.py`: 70%

### Routers
- `app/api/routers/integrations.py`: **88%** (Greatly Improved)
- `app/api/routers/notes.py`: 60%
- `app/api/routers/auth.py`: 75%

### Integration Services (Needs Work)
- `yandex_tasks_service.py`: 93%
- `tasks_service.py`: 80%
- `google_maps_service.py`: 68%
- `notion.py`: < 15% (Urgent)
- `todoist.py`: < 25% (Urgent)

## Next Steps to Reach 80% Coverage
1.  **Payment Router**: Implement tests for `payment.py`, mocking the payment provider responses.
2.  **Admin Router**: Add tests for admin endpoints to ensure RBAC works and stats are retrieved.
3.  **Integration Services**: Create unit tests for individual integration services (Notion, Todoist, etc.) by mocking their respective HTTP clients.
4.  **Notifications**: Test the push notification subscription and sending logic.
