import fs from "node:fs";
import path from "node:path";

import { jsonResult } from "openclaw/plugin-sdk/core";
import { runPluginCommandWithTimeout } from "openclaw/plugin-sdk/run-command";
import { Type } from "typebox";

const DEFAULT_PROJECT_ROOT = "/home/zhmao/crypto_helper";

export type PluginApi = any;

export function optionalStringEnum(values: string[], description: string) {
  return Type.Optional(
    Type.Unsafe({
      type: "string",
      enum: values,
      description,
    }),
  );
}

export function createCliBackedTool(params: {
  name: string;
  label: string;
  description: string;
  parameters: unknown;
  buildCommandArgs: (rawParams: Record<string, unknown>) => string[];
}) {
  return (api: PluginApi) => ({
    name: params.name,
    label: params.label,
    description: params.description,
    parameters: params.parameters,
    execute: async (
      _toolCallId: string,
      rawParams: Record<string, unknown>,
      signal?: AbortSignal,
    ) => {
      const payload = await runCryptoHelperCommand(
        api,
        params.buildCommandArgs(rawParams),
        signal,
      );
      return jsonResult(payload);
    },
  });
}

export async function runCryptoHelperCommand(
  api: PluginApi,
  commandArgs: string[],
  _signal?: AbortSignal,
): Promise<unknown> {
  const projectRoot = resolveConfigString(api.config.projectRoot) ?? DEFAULT_PROJECT_ROOT;
  if (!fs.existsSync(path.join(projectRoot, "pyproject.toml"))) {
    return {
      ok: false,
      error: `crypto_helper project root not found: ${projectRoot}`,
      code: "PROJECT_ROOT_NOT_FOUND",
      metadata: { projectRoot },
    };
  }

  const uvBinary = resolveConfigString(api.config.uvBinary) ?? "uv";
  const env = { ...process.env };
  const dataDir = resolveConfigString(api.config.dataDir);
  if (dataDir) {
    env.CRYPTO_HELPER_DATA_DIR = dataDir;
  }

  return await spawnJsonCommand(
    [uvBinary, "run", "crypto-helper", ...commandArgs, "--json"],
    {
      cwd: projectRoot,
      env,
    },
  );
}

type SpawnOptions = {
  cwd: string;
  env: NodeJS.ProcessEnv;
};

async function spawnJsonCommand(
  argv: string[],
  options: SpawnOptions,
): Promise<unknown> {
  try {
    const result = await runPluginCommandWithTimeout({
      argv,
      cwd: options.cwd,
      env: options.env,
      timeoutMs: 120000,
    });
    const trimmed = result.stdout.trim();
    if (trimmed) {
      try {
        return JSON.parse(trimmed);
      } catch (error) {
        return {
          ok: false,
          error: `Failed to parse crypto-helper JSON output: ${String(error)}`,
          code: "CLI_JSON_PARSE_ERROR",
          metadata: {
            argv,
            exitCode: result.code,
            stdout: trimmed,
            stderr: result.stderr.trim() || undefined,
          },
        };
      }
    }

    return {
      ok: false,
      error: result.stderr.trim() || `crypto-helper exited with code ${result.code}`,
      code: "CLI_EMPTY_OUTPUT",
      metadata: {
        argv,
        exitCode: result.code,
      },
    };
  } catch (error) {
    return {
      ok: false,
      error: String(error),
      code: "PLUGIN_EXEC_ERROR",
      metadata: {
        argv,
        cwd: options.cwd,
      },
    };
  }
}

export function resolveConfigString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}
