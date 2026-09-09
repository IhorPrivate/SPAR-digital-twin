import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// recharts measures its container; jsdom has no layout, so stub ResizeObserver.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver;
vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(800);
vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(400);
