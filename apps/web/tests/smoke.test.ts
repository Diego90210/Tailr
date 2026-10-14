import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("skeleton smoke", () => {
  it("cn merges classes — Tailwind + shadcn wiring is alive", () => {
    expect(cn("p-2", false && "p-4", "text-sm")).toBe("p-2 text-sm");
  });
});
