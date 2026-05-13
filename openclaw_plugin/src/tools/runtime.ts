import { readNumberParam, readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, type PluginApi } from "./common.js";

const queueClaimNextSchema = Type.Object(
  {
    target_agent: Type.Optional(
      Type.String({ description: "Optional target agent filter when claiming the next task." }),
    ),
  },
  { additionalProperties: false },
);

const queueTaskSchema = Type.Object(
  {
    task_id: Type.String({ description: "Delegation task id." }),
  },
  { additionalProperties: false },
);

const queueDispatchUntilEmptySchema = Type.Object(
  {
    max_tasks: Type.Optional(
      Type.Number({ description: "Maximum tasks to process in this dispatch loop.", minimum: 1 }),
    ),
    max_seconds: Type.Optional(
      Type.Number({ description: "Maximum seconds to spend in this dispatch loop.", minimum: 1 }),
    ),
    target_agent: Type.Optional(
      Type.String({ description: "Optional target agent filter for dispatching queued tasks." }),
    ),
  },
  { additionalProperties: false },
);

const queueMarkDoneSchema = Type.Object(
  {
    task_id: Type.String({ description: "Delegation task id." }),
    target_agent: Type.String({ description: "Worker agent that produced this result." }),
    status: Type.Optional(
      Type.String({ description: "Worker execution status, defaults to completed." }),
    ),
    output_payload_json: Type.String({ description: "JSON object string for worker output payload." }),
    evidence_refs_json: Type.Optional(
      Type.String({ description: "JSON array string of evidence refs." }),
    ),
    limitations_json: Type.Optional(
      Type.String({ description: "JSON array string of limitations." }),
    ),
    error: Type.Optional(Type.String({ description: "Optional worker error string." })),
  },
  { additionalProperties: false },
);

const queueMarkFailedSchema = Type.Object(
  {
    task_id: Type.String({ description: "Delegation task id." }),
    error: Type.String({ description: "Failure reason." }),
  },
  { additionalProperties: false },
);

export function buildQueueDispatchUntilEmptyArgs(rawParams: Record<string, unknown>): string[] {
  const args = ["queue", "dispatch-until-empty"];
  const maxTasks = readNumberParam(rawParams, "max_tasks", { integer: true });
  const maxSeconds = readNumberParam(rawParams, "max_seconds", { integer: true });
  const targetAgent = readStringParam(rawParams, "target_agent");
  if (maxTasks !== undefined) {
    args.push("--max-tasks", String(maxTasks));
  }
  if (maxSeconds !== undefined) {
    args.push("--max-seconds", String(maxSeconds));
  }
  if (targetAgent) {
    args.push("--target-agent", targetAgent);
  }
  return args;
}

export function buildManagerReceiveWorkerResultArgs(
  rawParams: Record<string, unknown>,
): string[] {
  return [
    "manager",
    "receive-worker-result",
    "--task-id",
    readStringParam(rawParams, "task_id", { required: true })!,
  ];
}

export function registerRuntimeTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_queue_claim_next",
      label: "Queue Claim Next",
      description: "Claim the next pending async delegation task.",
      parameters: queueClaimNextSchema,
      buildCommandArgs: (rawParams) => {
        const args = ["queue", "claim-next"];
        const targetAgent = readStringParam(rawParams, "target_agent");
        if (targetAgent) {
          args.push("--target-agent", targetAgent);
        }
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_queue_get_task",
      label: "Queue Get Task",
      description: "Inspect one async delegation task and any stored result payload.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "queue",
        "get-task",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_queue_mark_done",
      label: "Queue Mark Done",
      description: "Mark an async delegation task as done and store its worker result.",
      parameters: queueMarkDoneSchema,
      buildCommandArgs: (rawParams) => {
        const args = [
          "queue",
          "mark-done",
          "--task-id",
          readStringParam(rawParams, "task_id", { required: true })!,
          "--target-agent",
          readStringParam(rawParams, "target_agent", { required: true })!,
          "--output-payload-json",
          readStringParam(rawParams, "output_payload_json", { required: true })!,
        ];
        const status = readStringParam(rawParams, "status");
        const evidenceRefs = readStringParam(rawParams, "evidence_refs_json");
        const limitations = readStringParam(rawParams, "limitations_json");
        const error = readStringParam(rawParams, "error");
        if (status) args.push("--status", status);
        if (evidenceRefs) args.push("--evidence-refs-json", evidenceRefs);
        if (limitations) args.push("--limitations-json", limitations);
        if (error) args.push("--error", error);
        return args;
      },
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_queue_mark_failed",
      label: "Queue Mark Failed",
      description: "Mark an async delegation task as failed.",
      parameters: queueMarkFailedSchema,
      buildCommandArgs: (rawParams) => [
        "queue",
        "mark-failed",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
        "--error",
        readStringParam(rawParams, "error", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_queue_dispatch_until_empty",
      label: "Queue Dispatch Until Empty",
      description: "Dispatch queued workflows until the queue is empty or loop limits are reached.",
      parameters: queueDispatchUntilEmptySchema,
      buildCommandArgs: buildQueueDispatchUntilEmptyArgs,
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_worker_run_persona",
      label: "Worker Run Persona",
      description: "Run the persona worker adapter for a claimed delegation task.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "worker",
        "run-persona",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_worker_run_report",
      label: "Worker Run Report",
      description: "Run the report worker adapter for a claimed delegation task.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "worker",
        "run-report",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_worker_run_security",
      label: "Worker Run Security",
      description: "Run the security worker adapter for a claimed delegation task.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "worker",
        "run-security",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_worker_run_admin",
      label: "Worker Run Admin",
      description: "Run the admin worker adapter for a claimed delegation task.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "worker",
        "run-admin",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_manager_finalize_task",
      label: "Manager Finalize Task",
      description: "Build the final manager-facing response from a completed worker task result.",
      parameters: queueTaskSchema,
      buildCommandArgs: (rawParams) => [
        "manager",
        "finalize-task",
        "--task-id",
        readStringParam(rawParams, "task_id", { required: true })!,
      ],
    })(api),
  );

  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_manager_receive_worker_result",
      label: "Manager Receive Worker Result",
      description: "Build a manager-agent handoff from a stored worker result.",
      parameters: queueTaskSchema,
      buildCommandArgs: buildManagerReceiveWorkerResultArgs,
    })(api),
  );
}
