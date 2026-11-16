import { defineConfig } from "@playwright/test";
const python =
  process.env.GIGBID_PYTHON ||
  (process.platform === "win32" ? "..\\.venv\\Scripts\\python.exe" : "python");
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 120000,
  expect: { timeout: 90000 },
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["html", { open: "never" }],
    ["json", { outputFile: "test-results/results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8001",
    headless: true,
    channel: "chrome",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: python + " -m scripts.test_server",
    cwd: "../..",
    url: "http://127.0.0.1:8001/api/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
