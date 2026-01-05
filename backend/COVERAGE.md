# Test Coverage Report

**Current Overall Coverage: 50%**

## Summary
Achieved 50% overall coverage. Critical paths (Auth, Notes, Payment, Admin) are well tested. Key integrations (Notion, Todoist) now have logic tests.

## Coverage Gaps (Prioritized)

| Module | Coverage % | Key Missing Tests |
| :--- | :--- | :--- |
| `app/api/routers/notifications.py` | Low | Push subscription, notification delivery |
| `app/api/routers/users.py` | Low | Profile updates, onboarding status |
| `app/services/integrations/google_calendar.py` | Low | Event creation |
| `app/services/integrations/slack.py` | Low | Sending messages |
| `app/services/integrations/email_service.py` | Low | SMTP logic |

## Detailed Coverage by Component

### Core Services
- `app/core/analyze_core.py`: 79%
- `app/core/rag_service.py`: 85%
- `app/core/security.py`: 90%

### Routers
- `app/api/routers/integrations.py`: **88%**
- `app/api/routers/payment.py`: ~90%
- `app/api/routers/admin.py`: ~85%

### Integration Services
- `notion.py`: ~85% (Logic covered)
- `todoist_service.py`: **76%** (Logic covered)
- `yandex_tasks_service.py`: 93%

## Next Steps to Reach 80% Coverage
1.  **More Integrations**: Add tests for `Google Calendar`, `Slack`, `Email`.
2.  **User Features**: Test user profile updates and notifications.
3.  **Edge Cases**: Expand existing tests to cover error conditions.
