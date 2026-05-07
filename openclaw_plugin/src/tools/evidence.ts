import { readNumberParam, readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, optionalStringEnum, type PluginApi } from "./common.js";

const evidenceSearchSchema = Type.Object(
  {
    kol: Type.Optional(Type.String({ description: "Optional KOL id, display name, or alias." })),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    query: Type.Optional(Type.String({ description: "Optional free-text evidence query." })),
    source_type: Type.Optional(Type.String({ description: "Optional evidence source type filter." })),
    limit: Type.Optional(Type.Number({ description: "Maximum number of results.", minimum: 1 })),
  },
  { additionalProperties: false },
);

const tradeCallSchema = Type.Object(
  {
    kol: Type.Optional(Type.String({ description: "Optional KOL id, display name, or alias." })),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    status: Type.Optional(Type.String({ description: "Optional trade call status filter." })),
    time_range: Type.Optional(Type.String({ description: "Optional time range like 7d or 30d." })),
  },
  { additionalProperties: false },
);

const eventSchema = Type.Object(
  {
    kol: Type.Optional(Type.String({ description: "Optional KOL id, display name, or alias." })),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    event_type: optionalStringEnum(
      [
        "created",
        "update_sl",
        "update_tp",
        "move_to_breakeven",
        "partial_close",
        "full_close",
        "cancelled",
      ],
      "Optional trade call event type filter.",
    ),
    time_range: Type.Optional(Type.String({ description: "Optional time range like 7d or 30d." })),
  },
  { additionalProperties: false },
);

const opinionSchema = Type.Object(
  {
    kol: Type.Optional(Type.String({ description: "Optional KOL id, display name, or alias." })),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    sentiment: Type.Optional(Type.String({ description: "Optional sentiment filter." })),
    time_range: Type.Optional(Type.String({ description: "Optional time range like 7d or 30d." })),
  },
  { additionalProperties: false },
);

const newsSchema = Type.Object(
  {
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    importance: Type.Optional(Type.String({ description: "Optional importance filter." })),
    time_range: Type.Optional(Type.String({ description: "Optional time range like 1d or 7d." })),
  },
  { additionalProperties: false },
);

export function registerEvidenceTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_search_evidence",
      label: "Search Evidence",
      description: "Search aggregated KOL evidence.",
      parameters: evidenceSearchSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["evidence", "search"];
        pushOptionalStringArg(args, "--kol", readStringParam(rawParams, "kol"));
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--query", readStringParam(rawParams, "query"));
        pushOptionalStringArg(args, "--source-type", readStringParam(rawParams, "source_type"));
        const limit = readNumberParam(rawParams, "limit", { integer: true });
        if (limit !== undefined) {
          args.push("--limit", String(limit));
        }
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_query_trade_calls",
      label: "Query Trade Calls",
      description: "Query historical mock trade calls.",
      parameters: tradeCallSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["evidence", "trade-calls"];
        pushOptionalStringArg(args, "--kol", readStringParam(rawParams, "kol"));
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--status", readStringParam(rawParams, "status"));
        pushOptionalStringArg(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_query_events",
      label: "Query Events",
      description: "Query historical mock trade call events.",
      parameters: eventSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["evidence", "events"];
        pushOptionalStringArg(args, "--kol", readStringParam(rawParams, "kol"));
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--event-type", readStringParam(rawParams, "event_type"));
        pushOptionalStringArg(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_query_opinions",
      label: "Query Opinions",
      description: "Query historical mock KOL opinions.",
      parameters: opinionSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["evidence", "opinions"];
        pushOptionalStringArg(args, "--kol", readStringParam(rawParams, "kol"));
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--sentiment", readStringParam(rawParams, "sentiment"));
        pushOptionalStringArg(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_query_news",
      label: "Query News",
      description: "Query historical mock market news.",
      parameters: newsSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["evidence", "news"];
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--importance", readStringParam(rawParams, "importance"));
        pushOptionalStringArg(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );
}

function pushOptionalStringArg(
  args: string[],
  flag: string,
  value: string | undefined,
): void {
  if (value) {
    args.push(flag, value);
  }
}
