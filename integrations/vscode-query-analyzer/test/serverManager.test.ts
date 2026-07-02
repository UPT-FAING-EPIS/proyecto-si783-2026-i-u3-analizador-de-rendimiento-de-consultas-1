import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import test from "node:test";

import {
  ServerManager,
  buildBundledExecutablePath,
  findAvailablePort,
  resolveDevelopmentRepoRoot,
  resolveApiUrl,
  resolveManagedApiCommand,
  resolveTargetPlatform
} from "../src/serverManager";

test("resolveTargetPlatform maps supported release targets", () => {
  assert.equal(resolveTargetPlatform("win32", "x64"), "win32-x64");
  assert.equal(resolveTargetPlatform("linux", "x64"), "linux-x64");
  assert.equal(resolveTargetPlatform("darwin", "arm64"), "darwin-arm64");
  assert.equal(resolveTargetPlatform("darwin", "x64"), undefined);
});

test("buildBundledExecutablePath chooses the platform executable name", () => {
  assert.match(buildBundledExecutablePath("/ext", "win32-x64"), /bin[\\/]qa\.exe$/);
  assert.match(buildBundledExecutablePath("/ext", "linux-x64"), /bin[\\/]qa$/);
});

test("resolveDevelopmentRepoRoot finds local source checkout from extension folder", () => {
  const repoRoot = path.resolve(__dirname, "..", "..", "..", "..");

  assert.equal(
    resolveDevelopmentRepoRoot(path.join(repoRoot, "integrations", "vscode-query-analyzer")),
    repoRoot
  );
});

test("resolveManagedApiCommand falls back to uv in local development", () => {
  const repoRoot = createLocalSourceCheckout();
  const extensionRoot = path.join(repoRoot, "integrations", "vscode-query-analyzer");
  const command = resolveManagedApiCommand(extensionRoot, 8123);

  assert.equal(command.command, "uv");
  assert.deepEqual(command.args, ["run", "qa-api"]);
  assert.equal(command.cwd, repoRoot);
  assert.equal(command.env?.QA_API_HOST, "127.0.0.1");
  assert.equal(command.env?.QA_API_PORT, "8123");
});

test("resolveManagedApiCommand prefers bundled executable when present", () => {
  const extensionRoot = fs.mkdtempSync(path.join(os.tmpdir(), "qa-vscode-extension-"));
  const target = resolveTargetPlatform();

  if (!target) {
    return;
  }

  const executablePath = buildBundledExecutablePath(extensionRoot, target);
  fs.mkdirSync(path.dirname(executablePath), { recursive: true });
  fs.writeFileSync(executablePath, "");

  const command = resolveManagedApiCommand(extensionRoot, 8124);

  assert.equal(command.command, executablePath);
  assert.deepEqual(command.args, ["api", "--host", "127.0.0.1", "--port", "8124"]);
  assert.equal(command.cwd, extensionRoot);
});

test("findAvailablePort returns a bindable local port", async () => {
  const port = await findAvailablePort();

  assert.equal(Number.isInteger(port), true);
  assert.equal(port > 0, true);
});

test("resolveApiUrl returns external URL when configured", async () => {
  const server = {
    getManagedApiUrl: async () => "http://127.0.0.1:9999"
  } as ServerManager;
  const config = {
    get<T>(key: string, fallback: T): T {
      return (key === "apiMode" ? "external" : "http://example.test:8000") as T;
    }
  };

  assert.equal(await resolveApiUrl(config, server), "http://example.test:8000");
});

test("resolveApiUrl starts managed server by default", async () => {
  const server = {
    getManagedApiUrl: async () => "http://127.0.0.1:8765"
  } as ServerManager;
  const config = {
    get<T>(_key: string, fallback: T): T {
      return fallback;
    }
  };

  assert.equal(await resolveApiUrl(config, server), "http://127.0.0.1:8765");
});

function createLocalSourceCheckout(): string {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "qa-source-checkout-"));

  fs.writeFileSync(path.join(repoRoot, "pyproject.toml"), "[project]\nname = \"query-analyzer\"\n");
  fs.mkdirSync(path.join(repoRoot, "query_analyzer"));
  fs.mkdirSync(path.join(repoRoot, "integrations", "vscode-query-analyzer"), {
    recursive: true
  });

  return repoRoot;
}
