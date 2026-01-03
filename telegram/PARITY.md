# VoiceBrain Telegram Bot Parity Status

This document tracks the functional parity between the VoiceBrain React Web Application and the Telegram Bot.

## Core Features
| Feature | Web App | Telegram Bot | Notes |
|---------|---------|--------------|-------|
| Voice Note Recording | ✅ | ✅ | TG uses native voice messages |
| Text Note Creation | ✅ | ✅ | TG uses `/new_note` FSM flow |
| AI Summary | ✅ | ✅ | Rich Markdown format |
| Action Items | ✅ | ✅ | Extracted automatically |
| Tags Management | ✅ | ⚠️ | Partial (View/Delete work, manual add in progress) |
| Semantic Search | ✅ | ✅ | via `/ask` command |
| Adaptive Memory | ✅ | ✅ | Full clarification loop with editing |

## Advanced Features
| Feature | Web App | Telegram Bot | Notes |
|---------|---------|--------------|-------|
| Streaming AI | ✅ | ✅ | Chunked message updates |
| Integration Sync | ✅ | ✅ | Notion, Slack, Todoist, etc. |
| Graph View | ✅ | ❌ | No visual graph in TG (Bot limitation) |
| Health Metrics | ✅ | ✅ | Extracted from summaries |
| Billing/Pro Tier | ✅ | ✅ | Verified via API Key |

## UX & Technical
| Feature | Web App | Telegram Bot | Notes |
|---------|---------|--------------|-------|
| Dark Mode | ✅ | ✅ | TG Native Dark Mode |
| Responsive Design| ✅ | ✅ | TG Native Mobile/Desktop |
| Throttling | ✅ | ✅ | Anti-flood middleware active |
| Error Handling | ✅ | ✅ | User-friendly API error messages |

## Parity Checklist (Remaining Gaps)
- [ ] **Batch Actions**: Web allows selecting multiple notes for deletion/sync. TG is currently 1-by-1.
- [ ] **Profile Settings**: Detailed profile editing (name, identity summary) via Bot commands.
- [ ] **Visual Data**: Maps, links, and PDF exports are accessible via links, but embedded preview can be improved.

---
*Last Updated: 2026-01-03*
