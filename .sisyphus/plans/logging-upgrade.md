# Logging System Upgrade - BHNBot

## Context

### Original Request
User yêu cầu nâng cấp toàn bộ hệ thống logging theo 12 best practices từ video "12 Logging BEST Practices in 12 minutes".

### Interview Summary
**Key Decisions**:
- Framework: **structlog** (production-grade, JSON native)
- Output Format: **JSON only** (machine-parseable)
- Tracing: **Full OpenTelemetry** (traces + spans + correlation)
- Centralization: **Loki + Grafana** (+ keep Discord webhook)
- Retention: **Standard** (90d errors, 30d info, 7d debug)

**Current State**:
- core/logger.py: QueueHandler+QueueListener, TimedRotatingFileHandler (midnight, 30 backups)
- DiscordLogHandler: ERROR/CRITICAL embeds
- 121 files use setup_logger(), 105 files use direct logging.getLogger()
- 281 print() statements should be logs
- Format: TEXT `[timestamp] [level] [name] message` (NOT structured)

### Research Findings
- structlog + stdlib logging is production-ready with minimal performance impact
- JSON output via structlog.processors.JSONRenderer()
- OpenTelemetry Python SDK integrates with stdlib logging
- Loki needs docker-compose + Promtail agent
- Context binding for user_id/guild_id/command via structlog.contextvars

---

## Work Objectives

### Core Objective
Replace the current text-based logging system with a production-grade structured logging stack using structlog + OpenTelemetry + Loki/Grafana for full observability.

### Concrete Deliverables
1. New `core/logging/` module with structlog + OpenTelemetry integration
2. JSON-formatted log files with context binding
3. Docker deployment for Loki + Grafana + Promtail
4. Retention policies (90d/30d/7d)
5. Migration of all 121+ logger usages
6. Conversion of 281 print() statements to structured logs
7. Canonical log lines for Discord commands

### Definition of Done
- [ ] `bun test` equivalent passes (Python tests)
- [ ] Bot starts without logging errors
- [ ] Logs appear in Grafana/Loki dashboard
- [ ] JSON format verified for all log files
- [ ] OpenTelemetry traces visible for commands

### Must Have
- Structured JSON logging với context binding
- OpenTelemetry trace correlation
- Loki + Grafana centralization
- Backwards-compatible migration (gradual rollout)
- Discord webhook errors still work

### Must NOT Have (Guardrails)
- NO logging of sensitive data (tokens, passwords, API keys)
- NO blocking I/O in async context
- NO breaking existing DiscordLogHandler
- NO removing log files during migration (keep both text + JSON during transition)
- NO complex setup requiring manual intervention
- NO migrating all 121 files in one task (batch by cog group)

### Rollback Strategy
If migration causes issues:
1. Revert to compatibility shim: `from core.logging import get_logger as setup_logger`
2. Old logger remains at `core/logger_deprecated.py` for 30 days
3. Log files in both TEXT and JSON during transition period

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO (need to add pytest-structlog)
- **User wants tests**: Manual verification + TDD for core module
- **Framework**: pytest

### Manual QA for Each Phase
Each phase includes verification procedures with specific commands and expected outputs.

---

## Task Flow

```
Phase 1: Core Foundation
    1 → 2 → 3 → 4

Phase 2: OpenTelemetry
    5 → 6 → 7

Phase 3: Infrastructure  
    8 → 9 → 10

Phase 4: Migration
    11 → 12 → [13, 13b, 13c parallel] → 14

Phase 5: Cleanup
    15 → 16
```

## Parallelization

| Group | Tasks | Reason |
|-------|-------|--------|
| A | 2, 3 | Independent structlog components |
| B | 13, 13b, 13c | Can migrate different cog groups in parallel |

| Task | Depends On | Reason |
|------|------------|--------|
| 4 | 1, 2, 3 | Integration requires all components |
| 6 | 5 | Middleware needs SDK |
| 9 | 8 | Promtail needs Loki running |
| 11-14 | 4 | Migration needs new logger ready |
| 13, 13b, 13c | 11, 12 | Need migration script and core migrated first |

---

## TODOs

### Phase 1: Core Logging Foundation

- [ ] 1. Create new logging module structure

  **What to do**:
  - Create `core/logging/__init__.py` with public API
  - Create `core/logging/config.py` for structlog configuration
  - Create `core/logging/processors.py` for custom processors
  - Create `core/logging/handlers.py` for file/discord handlers
  - Install dependencies: `pip install structlog python-json-logger`

  **Must NOT do**:
  - Don't modify existing core/logger.py yet
  - Don't break existing imports

  **Parallelizable**: NO (foundation for all)

  **References**:
  - `core/logger.py:1-50` - Current setup_logger pattern to replicate
  - `core/logger.py:60-100` - DiscordLogHandler to preserve
  - structlog docs: https://www.structlog.org/en/stable/

  **Acceptance Criteria**:
  - [ ] `from core.logging import get_logger` works
  - [ ] `python -c "from core.logging import get_logger; print('OK')"` → OK
  - [ ] No import errors

  **Commit**: YES
  - Message: `feat(logging): create new structlog-based logging module`
  - Files: `core/logging/*.py`, `requirements.txt`

---

- [ ] 2. Implement structlog configuration

  **What to do**:
  - Configure structlog with JSONRenderer for file output
  - Add processors: timestamp, log level, caller info
  - Add context binding support (user_id, guild_id, command)
  - Add sensitive data redaction processor
  - **Add log sampling processor (10% for DEBUG, 100% for ERROR)**

  **Must NOT do**:
  - No console pretty-printing (JSON only per user decision)
  - No third-party cloud integrations yet

  **Parallelizable**: YES (with 3)

  **References**:
  - structlog configuration: https://www.structlog.org/en/stable/configuration.html
  - JSONRenderer: https://www.structlog.org/en/stable/api.html#structlog.processors.JSONRenderer

  **Acceptance Criteria**:
  - [ ] `logger.info("test", user_id=123)` produces JSON output
  - [ ] JSON contains: timestamp, level, event, user_id, caller
  - [ ] Regex patterns redact Discord tokens (NDc...) from output
  - [ ] Log sampling: DEBUG logs sampled at 10%, ERROR always logged

  **Commit**: YES
  - Message: `feat(logging): add structlog configuration with JSON output`
  - Files: `core/logging/config.py`, `core/logging/processors.py`

---

- [ ] 3. Implement async file handlers with rotation

  **What to do**:
  - Port QueueHandler+QueueListener pattern from old logger
  - Implement TimedRotatingFileHandler with retention policies
  - Add retention: 90d for ERROR, 30d for INFO, 7d for DEBUG
  - Add log file paths configuration

  **Must NOT do**:
  - No synchronous file writes
  - No deleting existing log rotation logic

  **Parallelizable**: YES (with 2)

  **References**:
  - `core/logger.py:20-45` - QueueHandler pattern to reuse
  - `core/logger.py:100-150` - TimedRotatingFileHandler config

  **Acceptance Criteria**:
  - [ ] Logs write to `logs/bot.json.log` in JSON format
  - [ ] File rotation works at midnight
  - [ ] Async writes don't block event loop
  - [ ] Retention script cleans old files

  **Commit**: YES
  - Message: `feat(logging): add async file handlers with retention`
  - Files: `core/logging/handlers.py`, `scripts/log_retention.py`

---

- [ ] 4. Integrate DiscordLogHandler with new system

  **What to do**:
  - Port DiscordLogHandler to work with structlog
  - Format JSON logs as Discord embeds
  - Keep ERROR/CRITICAL → Discord webhook behavior
  - Add rate limiting to prevent webhook spam

  **Must NOT do**:
  - Don't change Discord webhook URLs
  - Don't remove embed formatting

  **Parallelizable**: NO (depends on 1, 2, 3)

  **References**:
  - `core/logger.py:60-100` - Current DiscordLogHandler implementation
  - Discord embed limits: 6000 chars total

  **Acceptance Criteria**:
  - [ ] `logger.error("test error")` sends embed to Discord
  - [ ] Embed contains: timestamp, level, event, traceback
  - [ ] Rate limit: max 5 messages per minute
  - [ ] JSON context included in embed fields

  **Commit**: YES
  - Message: `feat(logging): integrate DiscordLogHandler with structlog`
  - Files: `core/logging/handlers.py`

---

### Phase 2: OpenTelemetry Integration

- [ ] 5. Setup OpenTelemetry SDK

  **What to do**:
  - Install: `pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp`
  - Configure TracerProvider with OTLP exporter
  - Create `core/telemetry/` module for OTel setup
  - Add environment variables for OTel endpoint

  **Must NOT do**:
  - No auto-instrumentation (too heavy for Discord bot)
  - No metrics yet (future scope)

  **Parallelizable**: NO (depends on Phase 1)

  **References**:
  - OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
  - OTLP exporter: https://opentelemetry-python.readthedocs.io/

  **Acceptance Criteria**:
  - [ ] `from core.telemetry import tracer` works
  - [ ] TracerProvider configured with OTLP exporter
  - [ ] Environment vars: OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME

  **Commit**: YES
  - Message: `feat(telemetry): add OpenTelemetry SDK setup`
  - Files: `core/telemetry/__init__.py`, `core/telemetry/config.py`, `requirements.txt`

---

- [ ] 6. Create Discord command tracing middleware

  **What to do**:
  - Create decorator `@traced_command` for slash commands
  - Start span on command invoke, end on complete
  - Add span attributes: user_id, guild_id, command_name, duration
  - Inject trace_id into structlog context

  **Must NOT do**:
  - No tracing for every event (too noisy)
  - No automatic instrumentation

  **Parallelizable**: NO (depends on 5)

  **References**:
  - discord.py commands: `cogs/*/cog.py` - command patterns
  - OpenTelemetry spans: https://opentelemetry.io/docs/concepts/signals/traces/

  **Acceptance Criteria**:
  - [ ] `@traced_command` decorator works on app_commands
  - [ ] Span created with: command_name, user_id, guild_id, duration_ms
  - [ ] trace_id appears in log JSON
  - [ ] Failed commands have error status on span

  **Commit**: YES
  - Message: `feat(telemetry): add Discord command tracing middleware`
  - Files: `core/telemetry/middleware.py`

---

- [ ] 7. Add canonical log lines for commands

  **What to do**:
  - Create `log_command_complete()` function
  - Log single entry per command: who, what, where, when, duration, result
  - Include: user_id, guild_id, channel_id, command, args, duration_ms, success
  - Link to trace_id for correlation

  **Must NOT do**:
  - No logging inside command execution (only at end)
  - No duplicate logging

  **Parallelizable**: NO (depends on 6)

  **References**:
  - Video best practice #6: Canonical log lines
  - `cogs/fishing/cog.py` - Command execution patterns

  **Acceptance Criteria**:
  - [ ] Each command produces exactly ONE summary log
  - [ ] Log contains: user_id, guild_id, command, duration_ms, success, trace_id
  - [ ] Can reconstruct full request from single log entry

  **Commit**: YES
  - Message: `feat(logging): add canonical log lines for commands`
  - Files: `core/logging/canonical.py`, `core/telemetry/middleware.py`

---

### Phase 3: Infrastructure (Loki + Grafana)

- [ ] 8. Create Loki + Grafana + Tempo docker-compose

  **What to do**:
  - Create `infrastructure/docker-compose.loki.yml`
  - Configure Loki with retention policies (90d/30d/7d)
  - Configure Grafana with Loki datasource
  - **Add Tempo for OpenTelemetry trace storage**
  - Add default dashboard for BHNBot logs
  - Configure Grafana to link logs ↔ traces

  **Must NOT do**:
  - No production secrets in compose file
  - No exposing ports to public internet

  **Parallelizable**: YES (independent of code)

  **References**:
  - Loki docs: https://grafana.com/docs/loki/latest/
  - Grafana Loki integration: https://grafana.com/docs/grafana/latest/datasources/loki/

  **Acceptance Criteria**:
  - [ ] `docker-compose -f infrastructure/docker-compose.loki.yml up -d` starts services
  - [ ] Grafana accessible at localhost:3000
  - [ ] Loki healthy at localhost:3100/ready
  - [ ] Tempo healthy at localhost:3200/ready
  - [ ] Traces visible in Grafana Explore → Tempo

  **Commit**: YES
  - Message: `infra(logging): add Loki + Grafana + Tempo docker-compose`
  - Files: `infrastructure/docker-compose.loki.yml`, `infrastructure/grafana/`, `infrastructure/tempo/`

---

- [ ] 9. Configure Promtail log shipping

  **What to do**:
  - Add Promtail to docker-compose
  - Configure to read JSON logs from `logs/*.json.log`
  - Add labels: app=bhnbot, env=production, level
  - Parse JSON fields for Loki indexing

  **Must NOT do**:
  - No shipping non-JSON files
  - No shipping sensitive log files

  **Parallelizable**: NO (depends on 8)

  **References**:
  - Promtail config: https://grafana.com/docs/loki/latest/clients/promtail/configuration/
  - `logs/` directory structure

  **Acceptance Criteria**:
  - [ ] Promtail reads `logs/*.json.log`
  - [ ] Logs appear in Grafana Explore
  - [ ] Labels visible: app, env, level, logger

  **Commit**: YES
  - Message: `infra(logging): configure Promtail log shipping`
  - Files: `infrastructure/promtail/config.yml`, `infrastructure/docker-compose.loki.yml`

---

- [ ] 10. Create Grafana dashboard for BHNBot

  **What to do**:
  - Create dashboard with panels: Error rate, Log volume, Top commands, Latency
  - Add log viewer panel with filters
  - Add alert rules: Error spike, Service down
  - Export as JSON for version control

  **Must NOT do**:
  - No overly complex dashboards
  - No dashboards requiring manual setup

  **Parallelizable**: NO (depends on 9)

  **References**:
  - Grafana dashboard JSON: https://grafana.com/docs/grafana/latest/dashboards/json-model/

  **Acceptance Criteria**:
  - [ ] Dashboard auto-provisions on Grafana start
  - [ ] Error rate panel shows last 24h
  - [ ] Log viewer allows filtering by level, command, user_id
  - [ ] Alert fires on >10 errors/minute

  **Commit**: YES
  - Message: `infra(logging): add Grafana dashboard for BHNBot`
  - Files: `infrastructure/grafana/dashboards/bhnbot.json`

---

### Phase 4: Migration

- [ ] 11. Create migration helper script

  **What to do**:
  - Create `scripts/migrate_logging.py` to find all logger usages
  - Generate migration report: file, line, old pattern, new pattern
  - Create AST-based transformer for simple cases
  - Document manual migration steps for complex cases

  **Must NOT do**:
  - No automatic changes without review
  - No breaking existing functionality

  **Parallelizable**: NO (needs core ready)

  **References**:
  - All files with `setup_logger` calls
  - All files with `logging.getLogger` calls

  **Acceptance Criteria**:
  - [ ] Script lists all 121+ files needing migration
  - [ ] Report categorizes: auto-migratable vs manual
  - [ ] Sample migration works correctly

  **Commit**: YES
  - Message: `chore(logging): add migration helper script`
  - Files: `scripts/migrate_logging.py`

---

- [ ] 12. Migrate core modules (database, utils)

  **What to do**:
  - Migrate `core/database.py` to new logger
  - Migrate `core/data_cache.py` to new logger
  - Migrate `core/achievements.py` to new logger
  - Add context: operation type, duration, affected records

  **Must NOT do**:
  - No changing business logic
  - No removing existing log messages

  **Parallelizable**: YES (with 13)

  **References**:
  - `core/database.py` - Database operations logging
  - `core/data_cache.py` - Cache logging

  **Acceptance Criteria**:
  - [ ] All core module logs are JSON
  - [ ] Database queries log: operation, table, duration_ms
  - [ ] No import errors after migration

  **Commit**: YES
  - Message: `refactor(core): migrate core modules to structlog`
  - Files: `core/database.py`, `core/data_cache.py`, `core/achievements.py`

---

- [ ] 13. Migrate cog modules - Group A (fishing, economy, shop)

  **What to do**:
  - Migrate `cogs/fishing/` (heavy logging, 100+ calls)
  - Migrate `cogs/economy/` (transaction logging)
  - Migrate `cogs/shop/` (purchase logging)
  - Add Discord context: guild_id, channel_id, user_id
  - Replace print() statements in these cogs

  **Must NOT do**:
  - No changing game logic
  - No removing debug information

  **Parallelizable**: YES (with 13b, 13c)

  **References**:
  - `cogs/fishing/cog.py` - Heavy logging usage
  - `cogs/economy/cog.py` - Transaction logging

  **Acceptance Criteria**:
  - [ ] fishing, economy, shop cog logs are JSON with context
  - [ ] No print() statements remain in these cogs
  - [ ] Bot starts and commands work

  **Commit**: YES
  - Message: `refactor(cogs): migrate fishing, economy, shop to structlog`
  - Files: `cogs/fishing/*.py`, `cogs/economy/*.py`, `cogs/shop/*.py`

---

- [ ] 13b. Migrate cog modules - Group B (admin, profile, seasonal)

  **What to do**:
  - Migrate `cogs/admin/` (moderation logging)
  - Migrate `cogs/profile/` (user profile logging)
  - Migrate `cogs/seasonal/` (event logging)
  - Add Discord context and fix silent except blocks

  **Must NOT do**:
  - No changing business logic

  **Parallelizable**: YES (with 13, 13c)

  **References**:
  - `cogs/admin/cog.py` - Admin command patterns

  **Acceptance Criteria**:
  - [ ] admin, profile, seasonal cog logs are JSON
  - [ ] Bot starts and commands work

  **Commit**: YES
  - Message: `refactor(cogs): migrate admin, profile, seasonal to structlog`
  - Files: `cogs/admin/*.py`, `cogs/profile/*.py`, `cogs/seasonal/*.py`

---

- [ ] 13c. Migrate cog modules - Group C (remaining cogs)

  **What to do**:
  - Migrate all remaining cogs (aquarium, baucua, noitu, etc.)
  - This is the catch-all for smaller cogs
  - Add Discord context, fix print() and silent excepts

  **Must NOT do**:
  - No changing game logic

  **Parallelizable**: YES (with 13, 13b)

  **References**:
  - Migration script output from Task 11

  **Acceptance Criteria**:
  - [ ] All cog logs are JSON with Discord context
  - [ ] No print() statements remain in production code
  - [ ] Silent except blocks now log errors
  - [ ] Bot starts and all commands work

  **Commit**: YES
  - Message: `refactor(cogs): migrate remaining cogs to structlog`
  - Files: `cogs/*/*.py`

---

- [ ] 14. Migrate main.py and startup

  **What to do**:
  - Migrate main.py to new logger
  - Add startup span for bot initialization
  - Log: cogs loaded, database connected, ready time
  - Add shutdown logging

  **Must NOT do**:
  - No changing bot initialization order
  - No removing startup checks

  **Parallelizable**: NO (final migration step)

  **References**:
  - `main.py` - Bot startup sequence

  **Acceptance Criteria**:
  - [ ] Bot startup produces structured JSON logs
  - [ ] Startup span captures: cogs_loaded, db_connected, ready_time_ms
  - [ ] Shutdown logs captured before exit

  **Commit**: YES
  - Message: `refactor(main): migrate startup to structlog with tracing`
  - Files: `main.py`

---

### Phase 5: Cleanup & Documentation

- [ ] 15. Remove old logger and cleanup

  **What to do**:
  - Rename `core/logger.py` → `core/logger_deprecated.py`
  - Create compatibility shim: `from core.logging import get_logger as setup_logger`
  - Add deprecation warnings for old patterns
  - Schedule removal after 30 days

  **Must NOT do**:
  - No immediate deletion of old logger
  - No breaking existing scripts

  **Parallelizable**: NO (after migration complete)

  **References**:
  - `core/logger.py` - Old logger to deprecate

  **Acceptance Criteria**:
  - [ ] Old logger renamed with deprecation warnings
  - [ ] Compatibility shim works for gradual migration
  - [ ] Bot runs without errors using new logging

  **Commit**: YES
  - Message: `chore(logging): deprecate old logger, add compatibility shim`
  - Files: `core/logger_deprecated.py`, `core/logging/compat.py`

---

- [ ] 16. Create documentation

  **What to do**:
  - Create `docs/logging.md` with architecture overview
  - Document: how to add logs, context binding, tracing
  - Add runbook: how to query Loki, common issues
  - Update README with logging quick start

  **Must NOT do**:
  - No over-documenting obvious things
  - No outdated examples

  **Parallelizable**: YES (can start anytime)

  **References**:
  - New logging module structure
  - Grafana dashboard usage

  **Acceptance Criteria**:
  - [ ] docs/logging.md covers all new features
  - [ ] Examples for common logging patterns
  - [ ] Runbook for troubleshooting
  - [ ] README updated with quick start

  **Commit**: YES
  - Message: `docs(logging): add logging architecture and runbook`
  - Files: `docs/logging.md`, `README.md`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1-4 | `feat(logging): complete core logging module` | core/logging/* | Bot starts, JSON logs |
| 5-7 | `feat(telemetry): complete OpenTelemetry integration` | core/telemetry/* | Traces visible |
| 8-10 | `infra(logging): complete Loki/Grafana stack` | infrastructure/* | Grafana shows logs |
| 11-14 | `refactor: migrate all logging to structlog` | cogs/*, core/* | All logs JSON |
| 15-16 | `chore(logging): cleanup and documentation` | docs/*, core/* | Docs complete |

---

## Success Criteria

### Verification Commands
```bash
# 1. Bot starts without errors
cd /home/phuctruong/Work/BHNBot && .venv/bin/python3 main.py

# 2. Logs are JSON
cat logs/bot.json.log | head -1 | jq .

# 3. Loki receives logs
curl -s http://localhost:3100/loki/api/v1/labels | jq .

# 4. Grafana dashboard works
curl -s http://localhost:3000/api/health | jq .

# 5. OpenTelemetry traces
# Check Jaeger/Tempo UI for traces
```

### Final Checklist
- [ ] All logs output JSON format
- [ ] Log sampling configured (10% DEBUG, 100% ERROR)
- [ ] OpenTelemetry traces for commands (visible in Tempo)
- [ ] Loki + Grafana + Tempo dashboard working
- [ ] Retention policies configured (90d/30d/7d)
- [ ] No sensitive data in logs (tokens redacted)
- [ ] Discord error notifications still work
- [ ] Documentation complete
- [ ] Rollback strategy documented and tested
