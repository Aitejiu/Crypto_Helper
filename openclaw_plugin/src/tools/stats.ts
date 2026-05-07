import { readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const compareSchema = Type.Object(
  {
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    time_range: Type.Optional(Type.String({ description: "Comparison range like 30d." })),
    include_dynamic: Type.Optional(
      Type.Boolean({ description: "Whether dynamic KOLs should be included." }),
    ),
  },
  { additionalProperties: false },
);

const performanceSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    time_range: Type.Optional(Type.String({ description: "Performance range like 30d or 90d." })),
  },
  { additionalProperties: false },
);

const activeSymbolsSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
  },
  { additionalProperties: false },
);

const marketSummarySchema = Type.Object(
  {
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    time_range: Type.Optional(Type.String({ description: "Summary range like 1d." })),
  },
  { additionalProperties: false },
);

export function registerStatsTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_compare_kols",
      label: "Compare KOLs",
      description: "Compare KOL performance over a historical range.",
      parameters: compareSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["stats", "compare"];
        pushOptional(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptional(args, "--range", readStringParam(rawParams, "time_range"));
        if (rawParams.include_dynamic === false) {
          args.push("--exclude-dynamic");
        }
        if (rawParams.include_dynamic === true) {
          args.push("--include-dynamic");
        }
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_get_kol_performance",
      label: "KOL Performance",
      description: "Get historical performance for one KOL.",
      parameters: performanceSchema,
      buildCommandArgs: (rawParams) => {
        const args = [
          "stats",
          "performance",
          "--kol",
          readStringParam(rawParams, "kol", { required: true })!,
        ];
        pushOptional(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptional(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_get_active_symbols",
      label: "Active Symbols",
      description: "Get active symbols for one KOL profile.",
      parameters: activeSymbolsSchema,
      buildCommandArgs: (rawParams) => [
        "stats",
        "active-symbols",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_get_market_summary",
      label: "Market Summary",
      description: "Get a historical market summary from mock news, calls, and opinions.",
      parameters: marketSummarySchema,
      buildCommandArgs: (rawParams) => {
        const args = ["stats", "market-summary"];
        pushOptional(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptional(args, "--range", readStringParam(rawParams, "time_range"));
        return args;
      },
    })(api),
  );
}

function pushOptional(args: string[], flag: string, value: string | undefined): void {
  if (value) {
    args.push(flag, value);
  }
}
