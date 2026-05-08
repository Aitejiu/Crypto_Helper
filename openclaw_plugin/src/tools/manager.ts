import { readStringParam } from "openclaw/plugin-sdk/core";
import { Type } from "typebox";

import { createCliBackedTool, optionalStringEnum, type PluginApi } from "./common.js";

const managerHandleRequestSchema = Type.Object(
  {
    message: Type.String({
      description: "The raw user request that manager-agent should classify and route.",
    }),
    channel: Type.String({
      description: "Normalized channel name, usually discord or telegram.",
    }),
    chat_id: Type.String({
      description: "Normalized chat or channel id for the current request.",
    }),
    user_id: Type.String({
      description: "Normalized sender id for the current request.",
    }),
    guild_id: Type.Optional(Type.String({ description: "Optional guild/server id." })),
    is_admin_context: Type.Optional(
      Type.Boolean({ description: "Whether the current request is already in admin context." }),
    ),
    message_id: Type.Optional(Type.String({ description: "Optional source message id." })),
    timestamp: Type.Optional(Type.String({ description: "Optional ISO timestamp." })),
    locale: Type.Optional(Type.String({ description: "Optional locale like zh-CN." })),
    visibility: optionalStringEnum(
      ["public", "private", "admin"],
      "Normalized visibility for the request context.",
    ),
  },
  { additionalProperties: false },
);

export function buildManagerHandleRequestArgs(
  rawParams: Record<string, unknown>,
): string[] {
  const args = [
    "manager",
    "handle-request",
    "--message",
    readStringParam(rawParams, "message", { required: true })!,
    "--channel",
    readStringParam(rawParams, "channel", { required: true })!,
    "--chat-id",
    readStringParam(rawParams, "chat_id", { required: true })!,
    "--user-id",
    readStringParam(rawParams, "user_id", { required: true })!,
  ];
  pushOptional(args, "--guild-id", readStringParam(rawParams, "guild_id"));
  pushOptional(args, "--message-id", readStringParam(rawParams, "message_id"));
  pushOptional(args, "--timestamp", readStringParam(rawParams, "timestamp"));
  pushOptional(args, "--locale", readStringParam(rawParams, "locale"));
  pushOptional(args, "--visibility", readStringParam(rawParams, "visibility"));
  if (rawParams.is_admin_context === true) {
    args.push("--is-admin-context");
  }
  return args;
}

export function registerManagerTools(api: PluginApi): void {
  api.registerTool(
    createCliBackedTool({
      name: "crypto_helper_manager_handle_request",
      label: "Manager Handle Request",
      description:
        "Run the unified manager-agent workflow routing pipeline and return delegation and execution plan.",
      parameters: managerHandleRequestSchema,
      buildCommandArgs: buildManagerHandleRequestArgs,
    })(api),
  );
}

function pushOptional(args: string[], flag: string, value: string | undefined): void {
  if (value) {
    args.push(flag, value);
  }
}
