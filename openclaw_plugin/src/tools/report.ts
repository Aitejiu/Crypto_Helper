import { readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const kolReportSchema = Type.Object(
  {
    kol: Type.String({ description: "KOL id, display name, or alias." }),
    time_range: Type.Optional(Type.String({ description: "Report range like 7d." })),
  },
  { additionalProperties: false },
);

const marketReportSchema = Type.Object(
  {
    time_range: Type.Optional(Type.String({ description: "Report range like 1d." })),
  },
  { additionalProperties: false },
);

export function registerReportTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_generate_report",
      label: "Generate KOL Report",
      description: "Generate a KOL report with Evidence Appendix.",
      parameters: kolReportSchema,
      buildCommandArgs: (rawParams) => {
        const args = [
          "report",
          "kol",
          "--kol",
          readStringParam(rawParams, "kol", { required: true })!,
        ];
        const timeRange = readStringParam(rawParams, "time_range");
        if (timeRange) {
          args.push("--range", timeRange);
        }
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_generate_daily_market_report",
      label: "Generate Daily Market Report",
      description: "Generate a daily market report with Evidence Appendix.",
      parameters: marketReportSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["report", "daily-market"];
        const timeRange = readStringParam(rawParams, "time_range");
        if (timeRange) {
          args.push("--range", timeRange);
        }
        return args;
      },
    })(api),
  );
}
