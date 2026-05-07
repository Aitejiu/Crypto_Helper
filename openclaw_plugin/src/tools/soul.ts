import { readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const kolSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
  },
  { additionalProperties: false },
);

const soulPatchSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
    observed_behavior: Type.String({
      description: "Observed behavior that should inform a mock soul patch.",
    }),
  },
  { additionalProperties: false },
);

const soulApplySchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
    patch_id: Type.Optional(
      Type.String({ description: "Optional explicit patch id to apply." }),
    ),
  },
  { additionalProperties: false },
);

export function registerSoulTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_get_soul",
      label: "Get SOUL",
      description: "Load one KOL SOUL document.",
      parameters: kolSchema,
      buildCommandArgs: (rawParams) => [
        "soul",
        "get",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_get_profile",
      label: "Get Profile",
      description: "Load one KOL profile document.",
      parameters: kolSchema,
      buildCommandArgs: (rawParams) => [
        "profile",
        "get",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_generate_soul_patch_mock",
      label: "Generate Soul Patch",
      description: "Generate a mock SOUL patch from observed behavior.",
      parameters: soulPatchSchema,
      buildCommandArgs: (rawParams) => [
        "soul",
        "patch",
        "--kol",
        readStringParam(rawParams, "kol", { required: true })!,
        "--observed-behavior",
        readStringParam(rawParams, "observed_behavior", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_apply_soul_patch_mock",
      label: "Apply Soul Patch",
      description: "Apply a previously generated mock SOUL patch.",
      parameters: soulApplySchema,
      buildCommandArgs: (rawParams) => {
        const args = [
          "soul",
          "apply-patch",
          "--kol",
          readStringParam(rawParams, "kol", { required: true })!,
        ];
        const patchId = readStringParam(rawParams, "patch_id");
        if (patchId) {
          args.push("--patch-id", patchId);
        }
        return args;
      },
    })(api),
  );
}
