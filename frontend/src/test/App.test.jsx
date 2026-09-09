import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

const cellsBody = [{ cell_id: "B0005", latest_soh: 0.8, n_cycles: 3 }];
const cyclesBody = [1, 2, 3].map((c) => ({ cycle: c, soh: 0.9 - c * 0.01 }));
const predBody = cyclesBody.map((c) => ({ ...c, soh_p10: c.soh - 0.01, soh_p50: c.soh, soh_p90: c.soh + 0.01 }));
const twinBody = {
  state: {
    cell_id: "B0005", cycles_observed: 3, latest_capacity_ah: 1.74, soh_measured: 0.87,
    soh_predicted: 0.87, soh_p10: 0.86, soh_p90: 0.88, rul_predicted: 100, rul_p10: 90, rul_p90: 110,
    rul_physics: 95, physics: { q0: 1.8, a: 0.001, b: 1 }, health_status: "healthy",
  },
  trajectory: [{ cycle: 4, soh_forecast: 0.86 }],
};
const metricsBody = { n_cells: 1, n_cycles: 3, cv: {} };

function mockBackend(trained) {
  let isTrained = trained;
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, opts = {}) => {
    const json = (body, ok = true, status = 200) => ({ ok, status, statusText: "", json: async () => body });
    if (url === "/api/health") return json({ trained: isTrained, data_source: "synthetic" });
    if (url === "/api/cells") return json(cellsBody);
    if (url === "/api/cells/B0005/cycles") return json(cyclesBody);
    if (url === "/api/cells/B0005/predictions") return isTrained ? json(predBody) : json({ detail: "untrained" }, false, 409);
    if (url.startsWith("/api/twins/B0005/ingest")) return json({ ...twinBody, state: { ...twinBody.state, cycles_observed: 4 } });
    if (url.startsWith("/api/twins/B0005") && opts.method === "DELETE") return json({ reset: "B0005" });
    if (url.startsWith("/api/twins/B0005")) return json(twinBody);
    if (url === "/api/metrics") return isTrained ? json(metricsBody) : json({ detail: "untrained" }, false, 409);
    if (url === "/api/train") { isTrained = true; return json(metricsBody); }
    throw new Error(`unmocked ${url}`);
  });
}

describe("App", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows an untrained notice, then trains and loads the twin", async () => {
    const f = mockBackend(false);
    render(<App />);
    expect(await screen.findByText("Cell B0005")).toBeInTheDocument();
    expect(screen.getByText(/Models are untrained/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Train models" }));
    expect(await screen.findByText("Twin of B0005")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.queryByText(/Models are untrained/)).not.toBeInTheDocument();
    expect(f.mock.calls.some(([u]) => u === "/api/train")).toBe(true);
    expect(f.mock.calls.some(([u]) => u === "/api/cells/B0005/predictions")).toBe(true);
  });

  it("ingests a measurement and updates twin state", async () => {
    mockBackend(true);
    render(<App />);
    expect(await screen.findByText("Twin of B0005")).toBeInTheDocument();
    const observed = () => screen.getByText("Cycles observed").nextElementSibling.textContent;
    expect(observed()).toBe("3");
    await userEvent.click(screen.getByRole("button", { name: "Add cycle" }));
    await waitFor(() => expect(observed()).toBe("4"));
  });

  it("shows an alert when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("ECONNREFUSED"));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unreachable: ECONNREFUSED");
  });
});
