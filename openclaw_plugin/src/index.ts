import { definePluginEntry } from "openclaw/plugin-sdk/core";

import { registerEvidenceTools } from "./tools/evidence.js";
import { registerRegistryTools } from "./tools/registry.js";
import { registerReportTools } from "./tools/report.js";
import { registerSecurityTools } from "./tools/security.js";
import { registerSoulTools } from "./tools/soul.js";
import { registerStatsTools } from "./tools/stats.js";

export default definePluginEntry({
  id: "crypto-helper-tools",
  name: "Crypto Helper Tools",
  description: "Expose crypto_helper Python CLI capabilities as OpenClaw tools.",
  register(api) {
    registerRegistryTools(api);
    registerSoulTools(api);
    registerEvidenceTools(api);
    registerStatsTools(api);
    registerReportTools(api);
    registerSecurityTools(api);
  },
});
