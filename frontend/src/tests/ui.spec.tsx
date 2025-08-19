import { test, expect } from "@playwright/test";
import { render, screen } from "@testing-library/react";
import { Card, CardContent } from "@/components/ui/card";

test.skip("renders a basic card (jsdom)", async () => {
  render(
    <Card>
      <CardContent>hello</CardContent>
    </Card>
  );
  const el = screen.getByText("hello");
  expect(el).toBeTruthy();
});


