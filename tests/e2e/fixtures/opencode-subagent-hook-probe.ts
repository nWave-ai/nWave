// Functional observer plugin for OpenCode hook probe.
// Pure helpers + a single IO edge: appendFileSync to LOG_PATH.
// Never throws — must not interfere with any tool call.

import type { Plugin } from "@opencode-ai/plugin"
import { appendFileSync } from "node:fs"

const LOG_PATH = "/tmp/opencode-probe.jsonl"

// ---- Pure helpers ----------------------------------------------------------

type LogEntry = Readonly<{
  timestamp: string
  hook_name: string
  tool_name: string | null
  session_id: string | null
  parent_session_id: string | null
  is_subagent: boolean | null
  snapshot: unknown
}>

const now = (): string => new Date().toISOString()

const safeGet = (obj: unknown, path: readonly string[]): unknown =>
  path.reduce<unknown>(
    (acc, key) =>
      acc && typeof acc === "object" ? (acc as Record<string, unknown>)[key] : undefined,
    obj,
  )

const asString = (v: unknown): string | null =>
  typeof v === "string" ? v : null

// Extract session id from any of the common shapes OpenCode passes.
const extractSessionId = (payload: unknown): string | null =>
  asString(safeGet(payload, ["sessionID"])) ??
  asString(safeGet(payload, ["session", "id"])) ??
  asString(safeGet(payload, ["session_id"])) ??
  null

const extractParentSessionId = (payload: unknown): string | null =>
  asString(safeGet(payload, ["session", "parentID"])) ??
  asString(safeGet(payload, ["parentID"])) ??
  asString(safeGet(payload, ["parent_session_id"])) ??
  null

// Subagent inference: if a parent session id exists, or payload explicitly
// marks it. Unknown -> null (do not lie).
const inferIsSubagent = (payload: unknown): boolean | null => {
  const parent = extractParentSessionId(payload)
  if (parent) return true
  const explicit = safeGet(payload, ["isSubagent"])
  if (typeof explicit === "boolean") return explicit
  return null
}

// Best-effort JSON snapshot — circular refs become strings, never throws.
const snapshot = (value: unknown): unknown => {
  const seen = new WeakSet<object>()
  try {
    return JSON.parse(
      JSON.stringify(value, (_k, v) => {
        if (typeof v === "object" && v !== null) {
          if (seen.has(v)) return "[circular]"
          seen.add(v)
        }
        if (typeof v === "function") return "[function]"
        if (typeof v === "bigint") return v.toString()
        return v
      }),
    )
  } catch {
    return String(value)
  }
}

const buildEntry = (
  hookName: string,
  toolName: string | null,
  payload: unknown,
): LogEntry => ({
  timestamp: now(),
  hook_name: hookName,
  tool_name: toolName,
  session_id: extractSessionId(payload),
  parent_session_id: extractParentSessionId(payload),
  is_subagent: inferIsSubagent(payload),
  snapshot: snapshot(payload),
})

// ---- IO edge (the only side effect) ---------------------------------------

const writeEntry = (entry: LogEntry): void => {
  try {
    appendFileSync(LOG_PATH, JSON.stringify(entry) + "\n", { encoding: "utf8" })
  } catch {
    // swallow — observer must not interfere
  }
}

const record = (hookName: string, toolName: string | null, payload: unknown): void =>
  writeEntry(buildEntry(hookName, toolName, payload))

// ---- Plugin entry ----------------------------------------------------------

export const ProbePlugin: Plugin = async (ctx) => {
  // Record plugin init itself so we can confirm load per session.
  record("plugin.init", null, {
    directory: (ctx as Record<string, unknown>)?.directory ?? null,
    worktree: (ctx as Record<string, unknown>)?.worktree ?? null,
  })

  return {
    "tool.execute.before": async (input: unknown, output: unknown) => {
      const toolName = asString(safeGet(input, ["tool"])) ?? "unknown"
      record("tool.execute.before", toolName, { input, output })
    },
    "tool.execute.after": async (input: unknown, output: unknown) => {
      const toolName = asString(safeGet(input, ["tool"])) ?? "unknown"
      record("tool.execute.after", toolName, { input, output })
    },
    "session.created": async (payload: unknown) => {
      record("session.created", null, payload)
    },
    "session.idle": async (payload: unknown) => {
      record("session.idle", null, payload)
    },
    "session.updated": async (payload: unknown) => {
      record("session.updated", null, payload)
    },
  } as unknown as Record<string, unknown>
}

export default ProbePlugin
