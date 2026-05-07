import { readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const securityReviewSchema = Type.Object(
  {
    text: Type.String({ description: "Text that should be reviewed for security policy compliance." }),
  },
  { additionalProperties: false },
);

export function registerSecurityTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_security_review",
      label: "Security Review",
      description: "Run crypto_helper security review on user text.",
      parameters: securityReviewSchema,
      buildCommandArgs: (rawParams) => [
        "security",
        "review",
        readStringParam(rawParams, "text", { required: true })!,
      ],
    })(api),
  );
}
