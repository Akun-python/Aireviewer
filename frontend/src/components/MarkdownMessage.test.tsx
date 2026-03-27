import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownMessage } from "./MarkdownMessage";

describe("MarkdownMessage", () => {
  it("renders markdown structures and math formulas", () => {
    render(<MarkdownMessage content={"# 标题\n\n- 列表项\n\n行内公式 $E=mc^2$\n\n$$\na^2+b^2=c^2\n$$"} />);

    expect(screen.getByRole("heading", { level: 1, name: "标题" })).toBeInTheDocument();
    expect(screen.getByText("列表项")).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(document.querySelector(".katex-display")).not.toBeNull();
  });
});
