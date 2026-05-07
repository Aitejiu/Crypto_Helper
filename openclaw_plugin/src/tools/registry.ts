import { readStringArrayParam, readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, optionalStringEnum, type PluginApi } from "./common.js";

const registryListSchema = Type.Object(
  {
    status: optionalStringEnum(
      ["active", "disabled", "archived", "all"],
      "Optional registry status filter. Defaults to active.",
    ),
  },
  { additionalProperties: false },
);

const registryLookupSchema = Type.Object(
  {
    query: Type.String({ description: "KOL id, display name, or alias." }),
  },
  { additionalProperties: false },
);

const registryAddMockSchema = Type.Object(
  {
    display_name: Type.String({ description: "Display name for the new mock KOL." }),
    allowed_symbols: Type.Array(Type.String(), {
      description: "Allowed trading symbols for the new mock KOL.",
      minItems: 1,
    }),
  },
  { additionalProperties: false },
);

const registryStatusSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
  },
  { additionalProperties: false },
);

export function registerRegistryTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_lookup",
      label: "Registry Lookup",
      description: "Look up one KOL from the crypto_helper registry.",
      parameters: registryLookupSchema,
      buildCommandArgs: (rawParams) => [
        "registry",
        "lookup",
        "--query",
        readStringParam(rawParams, "query", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_list",
      label: "Registry List",
      description: "List KOLs from the crypto_helper registry.",
      parameters: registryListSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["registry", "list"];
        const status = readStringParam(rawParams, "status");
        if (status) {
          args.push("--status", status);
        }
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_get_active",
      label: "Registry Active",
      description: "List active KOLs from the crypto_helper registry.",
      parameters: Type.Object({}, { additionalProperties: false }),
      buildCommandArgs: () => ["registry", "list", "--status", "active"],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_add_mock",
      label: "Registry Add Mock",
      description: "Create a new dynamic mock KOL in the registry.",
      parameters: registryAddMockSchema,
      buildCommandArgs: (rawParams) => {
        const displayName = readStringParam(rawParams, "display_name", { required: true })!;
        const symbols = readStringArrayParam(rawParams, "allowed_symbols", {
          required: true,
        })!;
        return [
          "registry",
          "add-mock",
          "--display-name",
          displayName,
          "--symbols",
          symbols.join(","),
        ];
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_disable_mock",
      label: "Registry Disable",
      description: "Disable a KOL in the registry without deleting historical data.",
      parameters: registryStatusSchema,
      buildCommandArgs: (rawParams) => [
        "registry",
        "disable",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_registry_archive_mock",
      label: "Registry Archive",
      description: "Archive a KOL in the registry while preserving historical data.",
      parameters: registryStatusSchema,
      buildCommandArgs: (rawParams) => [
        "registry",
        "archive",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
      ],
    })(api),
  );
}
