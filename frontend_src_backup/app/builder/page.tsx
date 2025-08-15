"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";

export default function BuilderPage() {
  const steps = ["Template", "Tools", "Knowledge", "Memory", "Policies", "Review"] as const;
  return (
    <div className="space-y-3">
      <Tabs defaultValue="Template">
        <TabsList>
          {steps.map((s) => (
            <TabsTrigger key={s} value={s}>
              {s}
            </TabsTrigger>
          ))}
        </TabsList>
        {steps.map((s) => (
          <TabsContent key={s} value={s}>
            <Card>
              <CardContent className="p-4 text-sm text-muted-foreground">{s} step</CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}


