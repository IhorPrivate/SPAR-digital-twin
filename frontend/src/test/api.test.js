import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";

const ok = (body) => ({ ok: true, json: async () => body });
const fail = (status, body, statusText = "Error") => ({
  ok: false, status, statusText, json: async () => body,
});

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("calls the right endpoints", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({}));
    await api.health();
    await api.cycles("B0005");
    await api.train(false);
    await api.ingest("B0005", { capacity_ah: 1.8 });
    await api.resetTwin("B0005");
    await api.twin("B0005", 7);
    const calls = f.mock.calls.map(([url, o]) => [url, o?.method || "GET"]);
    expect(calls).toEqual([
      ["/api/health", "GET"],
      ["/api/cells/B0005/cycles", "GET"],
      ["/api/train", "POST"],
      ["/api/twins/B0005/ingest", "POST"],
      ["/api/twins/B0005", "DELETE"],
      ["/api/twins/B0005?horizon=7", "GET"],
    ]);
    expect(JSON.parse(f.mock.calls[2][1].body)).toEqual({ evaluate: false });
  });

  it("surfaces the backend's error detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(fail(409, { detail: "Models are not trained yet" }));
    await expect(api.metrics()).rejects.toThrow("Models are not trained yet");
  });

  it("falls back to status text on non-JSON errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false, status: 502, statusText: "Bad Gateway", json: async () => { throw new Error("x"); },
    });
    await expect(api.cells()).rejects.toThrow("Bad Gateway");
  });
});
