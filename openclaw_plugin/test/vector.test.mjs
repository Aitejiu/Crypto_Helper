import test from "node:test";
import assert from "node:assert/strict";

import { registerVectorTools } from "../dist/tools/vector.js";

test("registerVectorTools exposes three vector tools", () => {
  const tools = [];
  const api = {
    registerTool(tool) {
      tools.push(tool);
    },
  };

  registerVectorTools(api);

  assert.equal(tools.length, 3);
  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      "crypto_helper_vector_rebuild_index",
      "crypto_helper_vector_index_status",
      "crypto_helper_vector_search",
    ],
  );
});
