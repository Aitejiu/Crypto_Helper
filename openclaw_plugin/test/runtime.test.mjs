import test from "node:test";
import assert from "node:assert/strict";

import { registerRuntimeTools } from "../dist/tools/runtime.js";

test("registerRuntimeTools exposes queue, worker, and finalize tools", () => {
  const tools = [];
  const api = {
    registerTool(tool) {
      tools.push(tool);
    },
  };

  registerRuntimeTools(api);

  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      "crypto_helper_queue_claim_next",
      "crypto_helper_queue_get_task",
      "crypto_helper_queue_mark_done",
      "crypto_helper_queue_mark_failed",
      "crypto_helper_worker_run_persona",
      "crypto_helper_worker_run_report",
      "crypto_helper_worker_run_security",
      "crypto_helper_worker_run_admin",
      "crypto_helper_manager_finalize_task",
    ],
  );
});
