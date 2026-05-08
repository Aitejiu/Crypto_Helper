import { readNumberParam, readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const rebuildIndexSchema = Type.Object({}, { additionalProperties: false });

const indexStatusSchema = Type.Object({}, { additionalProperties: false });

const vectorSearchSchema = Type.Object(
  {
    query: Type.String({ description: "Free-text semantic vector query." }),
    kol: Type.Optional(Type.String({ description: "Optional KOL id, display name, or alias." })),
    symbol: Type.Optional(Type.String({ description: "Optional symbol filter." })),
    source_type: Type.Optional(Type.String({ description: "Optional source type filter." })),
    limit: Type.Optional(Type.Number({ description: "Maximum number of results.", minimum: 1 })),
  },
  { additionalProperties: false },
);

export function registerVectorTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_vector_rebuild_index",
      label: "Vector Rebuild Index",
      description: "Rebuild the local Chroma vector index for crypto_helper.",
      parameters: rebuildIndexSchema,
      buildCommandArgs: () => ["vector", "rebuild-index"],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_vector_index_status",
      label: "Vector Index Status",
      description: "Inspect the local crypto_helper vector index status.",
      parameters: indexStatusSchema,
      buildCommandArgs: () => ["vector", "index-status"],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_vector_search",
      label: "Vector Search",
      description: "Search the local crypto_helper vector index with optional structured filters.",
      parameters: vectorSearchSchema,
      buildCommandArgs: (rawParams) => {
        const args = [
          "vector",
          "search",
          "--query",
          readStringParam(rawParams, "query", { required: true })!,
        ];
        pushOptionalStringArg(args, "--kol", readStringParam(rawParams, "kol"));
        pushOptionalStringArg(args, "--symbol", readStringParam(rawParams, "symbol"));
        pushOptionalStringArg(args, "--source-type", readStringParam(rawParams, "source_type"));
        const limit = readNumberParam(rawParams, "limit", { integer: true });
        if (limit !== undefined) {
          args.push("--limit", String(limit));
        }
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
