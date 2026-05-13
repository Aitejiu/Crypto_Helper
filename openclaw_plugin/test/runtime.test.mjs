import test from "node:test";
import assert from "node:assert/strict";

import {
  buildManagerReceiveWorkerResultArgs,
  buildQueueDispatchUntilEmptyArgs,
  registerRuntimeTools,
} from "../dist/tools/runtime.js";

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
      "crypto_helper_queue_dispatch_until_empty",
      "crypto_helper_worker_run_persona",
      "crypto_helper_worker_run_report",
      "crypto_helper_worker_run_security",
      "crypto_helper_worker_run_admin",
      "crypto_helper_manager_finalize_task",
      "crypto_helper_manager_receive_worker_result",
    ],
  );
});

test("buildQueueDispatchUntilEmptyArgs passes optional loop params through", () => {
  const args = buildQueueDispatchUntilEmptyArgs({
    max_tasks: 5,
    max_seconds: 30,
    target_agent: "report-agent",
  });

  assert.deepEqual(args, [
    "queue",
    "dispatch-until-empty",
    "--max-tasks",
    "5",
    "--max-seconds",
    "30",
    "--target-agent",
    "report-agent",
  ]);
});

test("buildQueueDispatchUntilEmptyArgs supports defaults by omitting params", () => {
  assert.deepEqual(buildQueueDispatchUntilEmptyArgs({}), ["queue", "dispatch-until-empty"]);
});

test("buildManagerReceiveWorkerResultArgs passes task id through", () => {
  assert.deepEqual(buildManagerReceiveWorkerResultArgs({ task_id: "task_1" }), [
    "manager",
    "receive-worker-result",
    "--task-id",
    "task_1",
  ]);
});
