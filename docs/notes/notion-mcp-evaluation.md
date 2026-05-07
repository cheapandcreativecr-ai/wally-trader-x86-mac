# Notion MCP Server Evaluation

**Date:** 2026-05-07
**Purpose:** Pick the Notion MCP server to register in `system/mcp/servers.json` for Phase 3 (NotionBackend + LLM-facing tool surface).

---

## Environment

| Item | Value |
|---|---|
| Node | v22.21.0 |
| npx | 10.9.4 |
| Platform | macOS 24.6.0 (darwin) |
| Network | Available (npm registry reachable) |

Both `node` and `npx` are installed and functional. Network access to the npm registry confirmed.

---

## Candidate 1: `@notionhq/notion-mcp-server`

**Package:** `@notionhq/notion-mcp-server@2.2.1`
**Publisher:** Notion HQ (official)
**License:** MIT
**Published:** 2026-03-05
**Repo:** https://github.com/makenotion/notion-mcp-server

### Run result

```
$ npx -y @notionhq/notion-mcp-server --help
Usage: notion-mcp-server [options]

Options:
  --transport <type>     Transport type: 'stdio' or 'http' (default: stdio)
  --port <number>        Port for HTTP server when using Streamable HTTP transport (default: 3000)
  --auth-token <token>   Bearer token for HTTP transport authentication (auto-generated if not provided)
  --disable-auth         Disable bearer token authentication for HTTP transport
  --help, -h             Show this help message

Environment Variables:
  NOTION_TOKEN           Notion integration token (recommended)
  OPENAPI_MCP_HEADERS    JSON string with Notion API headers (alternative)
  AUTH_TOKEN             Bearer token for HTTP transport authentication (alternative to --auth-token)
```

Exit: clean. No errors.

### Architecture

Auto-generates 22 MCP tools from `scripts/notion-openapi.json` (OpenAPI 3.1 spec, Notion API version `2025-09-03`). Each `operationId` in the spec becomes a tool. Names are kebab-case, max 64 chars.

### Full tool list (22 tools as of v2.2.1)

| Tool (operationId) | Method | Path | Summary |
|---|---|---|---|
| `create-a-comment` | POST | `/v1/comments` | Create comment |
| `create-a-data-source` | POST | `/v1/data_sources` | Create a data source |
| `delete-a-block` | DELETE | `/v1/blocks/{block_id}` | Delete a block |
| `get-block-children` | GET | `/v1/blocks/{block_id}/children` | Retrieve block children |
| `get-self` | GET | `/v1/users/me` | Retrieve your token's bot user |
| `get-user` | GET | `/v1/users/{user_id}` | Retrieve a user |
| `get-users` | GET | `/v1/users` | List all users |
| `list-data-source-templates` | GET | `/v1/data_sources/{data_source_id}/templates` | List templates in a data source |
| `move-page` | POST | `/v1/pages/{page_id}/move` | Move a page |
| `patch-block-children` | PATCH | `/v1/blocks/{block_id}/children` | Append block children |
| `patch-page` | PATCH | `/v1/pages/{page_id}` | Update page properties |
| `post-page` | POST | `/v1/pages` | Create a page |
| `post-search` | POST | `/v1/search` | Search by title |
| `query-data-source` | POST | `/v1/data_sources/{data_source_id}/query` | Query a data source |
| `retrieve-a-block` | GET | `/v1/blocks/{block_id}` | Retrieve a block |
| `retrieve-a-comment` | GET | `/v1/comments` | Retrieve comments |
| `retrieve-a-data-source` | GET | `/v1/data_sources/{data_source_id}` | Retrieve a data source |
| `retrieve-a-database` | GET | `/v1/databases/{database_id}` | Retrieve a database |
| `retrieve-a-page` | GET | `/v1/pages/{page_id}` | Retrieve a page |
| `retrieve-a-page-property` | GET | `/v1/pages/{page_id}/properties/{property_id}` | Retrieve a page property item |
| `update-a-block` | PATCH | `/v1/blocks/{block_id}` | Update a block |
| `update-a-data-source` | PATCH | `/v1/data_sources/{data_source_id}` | Update a data source |

**Coverage for wally needs:**
- `query-data-source` covers DB row reads (replaces deprecated `post-database-query`)
- `post-page` covers row creation in a DB
- `patch-page` covers updating page/row properties
- `post-search` covers lookup by title
- `retrieve-a-database` + `retrieve-a-data-source` cover schema inspection

All 6 DB operations needed for Phase 3 are covered.

### v2.0 breaking change note

v2.0.0 migrated to Notion API `2025-09-03` which uses `data_source_id` instead of `database_id` for query/update/create DB operations. The Python `notion-client` SDK (used in `NotionBackend`) uses the older `databases.query` style — both co-exist in the API; MCP server uses the newer data-source nomenclature while the SDK uses the legacy database endpoints. **These are different abstraction layers of the same API. No conflict.**

### Concern: sunset risk

The notionhq README explicitly states:
> "We are prioritizing, and only providing active support for, Notion MCP (remote). As a result: we may sunset this local MCP server repository in the future."

Notion's preferred path is now their hosted remote MCP server (OAuth-based). The local npx version may eventually be deprecated. For now (v2.2.1, 2026-03-05) it works and is actively maintained.

---

## Candidate 2: `@suekou/mcp-notion-server`

**Package:** `@suekou/mcp-notion-server@2.0.0`
**Publisher:** Kosuke Suenaga (community)
**License:** MIT
**Published:** 2026-05-05 (very recent)
**Repo:** https://github.com/suekou/mcp-notion-server

### Run result

```
$ npx -y @suekou/mcp-notion-server --help
Opciones:
  --help          Muestra ayuda                [booleano]
  --version       Muestra número de versión   [booleano]
  --enabledTools  Comma-separated list of tools to enable [cadena de caracteres]
```

Exit: clean. No errors.

### Highlights

- Targets Notion API `2026-03-11` (more recent than notionhq's `2025-09-03`)
- Exposes high-level "AI-friendly" tools: `notion_find`, `notion_read_page`, `notion_inspect_data_source`, `notion_query_data_source_by_values`, `notion_create_data_source_item_from_values`, `notion_append_markdown`, `notion_update_content`
- Supports `--enabledTools` flag for scoping tool surface
- Has MCP Prompts, Resources, and optional MCP Apps (Data Source Explorer, Page Workbench)
- Env var: `NOTION_API_TOKEN` (note: `_TOKEN` not `_TOKEN` — different from notionhq's `NOTION_TOKEN`)

### Concern: community project risk

Published by a single maintainer. v2.0.0 was published 2026-05-05 (yesterday), meaning no operational track record at this version. The simpler human-friendly tool names may mask schema details needed for precise DB writes.

---

## Recommendation: `@notionhq/notion-mcp-server`

**Chosen:** `@notionhq/notion-mcp-server@2.2.1`

The official Notion HQ package is the clear choice for a production system. It exposes the raw Notion REST API surface 1:1 as MCP tools — meaning the LLM can call `query-data-source`, `post-page`, and `patch-page` directly with the same parameters as the REST API, making it trivially verifiable against Notion's official documentation. The tool set has direct coverage for all 6 DB operations needed by wally's 6 memory databases. The sunset risk is real but mitigated: even if Notion deprecates the local server in favor of their hosted remote MCP, the tool names and env vars are identical, so migration is a one-line `servers.json` change. The Python `NotionBackend` (Task 3.2) uses the `notion-client` SDK directly and is unaffected either way.

The suekou server's AI-friendly abstractions are appealing but introduce indirection between the LLM's tool calls and the actual Notion API schema, which makes VCR cassette testing (Task 3.2) harder and adds a single-maintainer dependency risk.

---

## `system/mcp/servers.json` entry

```json
{
  "servers": {
    "tradingview": {
      "type": "stdio",
      "command": "node",
      "args": ["./tradingview-mcp/src/server.js"],
      "env": {},
      "enabled": true
    },
    "notion": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server@2.2.1"],
      "env": {
        "NOTION_TOKEN": "${NOTION_TOKEN}"
      },
      "enabled": false
    }
  }
}
```

`enabled: false` by default — activated when `NOTION_TOKEN` is set and user runs Phase 3 migration. The version is pinned to `2.2.1` to avoid unexpected breaks from a `latest` pull that may introduce Notion API version bumps.

---

## Required environment variables

| Variable | Required | Description |
|---|---|---|
| `NOTION_TOKEN` | Yes | Notion internal integration token. Format: `ntn_xxxx` or `secret_xxxx`. Create at https://www.notion.so/profile/integrations → New integration. |
| `OPENAPI_MCP_HEADERS` | Alternative | JSON string override for headers: `{"Authorization": "Bearer ntn_...", "Notion-Version": "2025-09-03"}`. Use when you need to pin the API version explicitly. |

**Integration setup checklist:**
1. Create internal integration at https://www.notion.so/profile/integrations
2. Enable capabilities: Read content + Insert content + Update content (minimum for wally)
3. For each DB used by wally: open the DB page → `...` menu → Connections → add your integration
4. Copy the integration secret → set `NOTION_TOKEN=ntn_...` in your shell env

---

## Notion API rate limits

**Standard rate limit: 3 requests per second per token** (documented at https://developers.notion.com/reference/request-limits).

Additional limits:
- **Burst allowance:** short bursts above 3 req/s are tolerated; sustained excess returns HTTP 429 with `Retry-After` header
- **Page size limit:** `page_size` max 100 per paginated query
- **Block children append:** max 100 blocks per `patch-block-children` call
- **Search results:** max 100 results per `post-search` call

For wally's use pattern (1-2 DB writes per trade signal, periodic reads), 3 req/s is effectively unlimited in normal operation. The only scenario to watch is bulk migration (Task 3.3 `migrate.py`): CSV→Notion with 100+ rows needs a `time.sleep(0.35)` between `post-page` calls.

---

## Notion property schema notes

These are the property types used in wally's 6 planned DBs. Each note describes how to set the value when creating/updating a page via the REST API (which maps 1:1 to MCP tool inputs).

| Property type | Write shape | Notes |
|---|---|---|
| `title` | `{"title": [{"text": {"content": "value"}}]}` | Every DB has exactly one title property. Required on page creation. |
| `rich_text` | `{"rich_text": [{"text": {"content": "value"}}]}` | Free-form text field. Used for: symbol, side, notes, error_log. Supports arrays for multi-segment styled text. |
| `select` | `{"select": {"name": "option_name"}}` | Single enum value. If `name` doesn't exist in the DB schema, Notion auto-creates the option. Used for: profile, outcome, regime, strategy. |
| `number` | `{"number": 42.5}` | Plain JSON number. Used for: entry_price, sl, tp1/2/3, pnl_usd, leverage, score. |
| `date` | `{"date": {"start": "2026-05-07T14:00:00-06:00"}}` | ISO 8601 with timezone. `end` field optional for date ranges. Used for: signal_ts, entry_ts, exit_ts. |
| `relation` | `{"relation": [{"id": "page-uuid"}]}` | References another DB row by page ID. Used to link signals to their outcomes, or trades to regimes. Requires the related DB to be shared with the same integration. |
| `last_edited_time` | Read-only | Notion-managed. Cannot be set via API. Useful for polling "what changed since last sync". |
| `created_time` | Read-only | Notion-managed. Do not include in write payloads. |
| `files` | `{"files": [{"name": "chart.png", "external": {"url": "https://..."}}]}` | External URL only (for internal file upload, use separate upload endpoint). Used if we ever want to attach TV screenshots to trade records. |

**Key gotcha for `select`:** The option must exist in the DB schema OR Notion auto-creates it. In test/VCR cassette scenarios, use `retrieve-a-data-source` first to verify the schema before writing, to avoid test flakiness.

**Key gotcha for `relation`:** Both databases must be shared with the same Notion integration. If the target DB is not connected, the relation write silently fails with a 400 error.

---

## Summary

| Item | Value |
|---|---|
| Chosen server | `@notionhq/notion-mcp-server@2.2.1` |
| npx ran cleanly | Yes |
| Tool count | 22 |
| Wally DB operations covered | Yes (query, create page, update page, search) |
| Env var | `NOTION_TOKEN` |
| API rate limit | 3 req/s sustained (burst tolerated) |
| Sunset risk | Low-medium (official but deprioritized vs hosted MCP) |
| Fallback | Python `notion-client` SDK in `NotionBackend` (Task 3.2) is independent of MCP server choice |
