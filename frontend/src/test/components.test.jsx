import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import CellRail from "../components/CellRail";
import HealthChart from "../components/HealthChart";
import MetricsPanel from "../components/MetricsPanel";
import TwinPanel, { IngestForm } from "../components/TwinPanel";

const cells = [
  { cell_id: "B0005", latest_soh: 0.81 },
  { cell_id: "B0006", latest_soh: 0.72 },
];

describe("CellRail", () => {
  it("lists cells and marks the selected one", async () => {
    const onSelect = vi.fn();
    render(<CellRail cells={cells} selected="B0005" onSelect={onSelect} source="nasa" trained={false} training={false} onTrain={() => {}} />);
    expect(screen.getByText("Data: NASA PCoE Li-ion set")).toBeInTheDocument();
    expect(screen.getByText("B0005").closest("button")).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("72 %")).toBeInTheDocument();
    await userEvent.click(screen.getByText("B0006"));
    expect(onSelect).toHaveBeenCalledWith("B0006");
  });

  it("changes the train button label with state", () => {
    const { rerender } = render(<CellRail cells={[]} source="synthetic" trained={false} training={false} onTrain={() => {}} />);
    expect(screen.getByRole("button", { name: "Train models" })).toBeEnabled();
    rerender(<CellRail cells={[]} source="synthetic" trained={true} training={false} onTrain={() => {}} />);
    expect(screen.getByRole("button", { name: "Retrain models" })).toBeInTheDocument();
    rerender(<CellRail cells={[]} source="synthetic" trained={true} training={true} onTrain={() => {}} />);
    expect(screen.getByRole("button", { name: "Training…" })).toBeDisabled();
  });
});

describe("HealthChart", () => {
  it("shows an empty state without data", () => {
    render(<HealthChart data={[]} />);
    expect(screen.getByText("No cycles to show.")).toBeInTheDocument();
  });
  it("renders the legend with data", () => {
    render(<HealthChart data={[{ cycle: 1, measured: 0.9 }, { cycle: 2, measured: 0.89 }]} />);
    expect(screen.getByText("Measured SOH")).toBeInTheDocument();
    expect(screen.getByText("Physics forecast")).toBeInTheDocument();
  });
});

describe("MetricsPanel", () => {
  it("renders nothing without metrics", () => {
    const { container } = render(<MetricsPanel metrics={null} />);
    expect(container).toBeEmptyDOMElement();
  });
  it("renders a per-cell table", () => {
    const metrics = {
      n_cells: 2, n_cycles: 100,
      cv: {
        soh: { mae: 0.0123, rmse: 0.02, per_cell: { B0005: { mae: 0.01, rmse: 0.02 }, B0006: { mae: 0.015, rmse: 0.03 } } },
        rul: { mae: 5.5, rmse: 7, per_cell: { B0005: { mae: 4, rmse: 6 }, B0006: { mae: 7, rmse: 8 } } },
      },
    };
    render(<MetricsPanel metrics={metrics} />);
    expect(screen.getByText("0.0123")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3);
    expect(screen.getByText("B0006")).toBeInTheDocument();
  });
});

describe("TwinPanel", () => {
  const twin = {
    state: {
      cell_id: "B0005", cycles_observed: 80, latest_capacity_ah: 1.62,
      soh_measured: 0.81, soh_predicted: 0.805, soh_p10: 0.79, soh_p90: 0.82,
      rul_predicted: 33.4, rul_p10: 20, rul_p90: 45, rul_physics: 30,
      physics: { q0: 1.86, a: 0.0016, b: 1.15 }, health_status: "maintenance_due",
    },
    trajectory: [],
  };

  it("asks to train when models are untrained", () => {
    render(<TwinPanel twin={null} trained={false} />);
    expect(screen.getByText(/Train the models/)).toBeInTheDocument();
  });

  it("shows state and status badge", () => {
    render(<TwinPanel twin={twin} trained={true} onIngest={() => {}} onReset={() => {}} />);
    expect(screen.getByText("Twin of B0005")).toBeInTheDocument();
    expect(screen.getByText("Maintenance due")).toBeInTheDocument();
    expect(screen.getByText("81.0 %")).toBeInTheDocument();
    expect(screen.getByText("33 cycles")).toBeInTheDocument();
    expect(screen.getByText("30 cycles")).toBeInTheDocument();
  });

  it("submits numeric measurement and resets", async () => {
    const onSubmit = vi.fn();
    const onReset = vi.fn();
    render(<IngestForm onSubmit={onSubmit} onReset={onReset} busy={false} />);
    const cap = screen.getByLabelText("Capacity (Ah)");
    await userEvent.clear(cap);
    await userEvent.type(cap, "1.55");
    await userEvent.click(screen.getByRole("button", { name: "Add cycle" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const body = onSubmit.mock.calls[0][0];
    expect(body.capacity_ah).toBe(1.55);
    expect(typeof body.discharge_time_s).toBe("number");
    await userEvent.click(screen.getByRole("button", { name: "Reset twin" }));
    expect(onReset).toHaveBeenCalled();
  });
});
