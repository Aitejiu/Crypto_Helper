import test from "node:test";
import assert from "node:assert/strict";

import { buildManagerHandleRequestArgs } from "../dist/tools/manager.js";

test("buildManagerHandleRequestArgs includes required context flags", () => {
  const args = buildManagerHandleRequestArgs({
    message: "KOL_A 如果 BTC 跌破 62000，可能怎么看？",
    channel: "discord",
    chat_id: "chat-1",
    user_id: "user-1",
    visibility: "public",
    is_admin_context: false,
  });

  assert.deepEqual(args, [
    "manager",
    "handle-request",
    "--message",
    "KOL_A 如果 BTC 跌破 62000，可能怎么看？",
    "--channel",
    "discord",
    "--chat-id",
    "chat-1",
    "--user-id",
    "user-1",
    "--visibility",
    "public",
  ]);
});

test("buildManagerHandleRequestArgs emits admin flag when requested", () => {
  const args = buildManagerHandleRequestArgs({
    message: "导入数据",
    channel: "telegram",
    chat_id: "admin-chat",
    user_id: "admin-1",
    visibility: "admin",
    is_admin_context: true,
  });

  assert.ok(args.includes("--is-admin-context"));
});
