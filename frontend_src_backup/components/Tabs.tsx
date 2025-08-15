import { useState } from "react";

export type TabItem = { key: string; label: string; badgeCount?: number };

interface TabsProps {
  tabs: TabItem[];
  activeKey?: string;
  onChange?: (key: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeKey, onChange, className = "" }: TabsProps) {
  const [internalKey, setInternalKey] = useState(tabs[0]?.key);
  const current = activeKey ?? internalKey;
  const setKey = (k: string) => {
    setInternalKey(k);
    onChange?.(k);
  };
  return (
    <div className={`border-b flex gap-2 overflow-x-auto ${className}`}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => setKey(t.key)}
          className={`px-3 py-2 text-sm border-b-2 -mb-px transition whitespace-nowrap ${
            current === t.key ? "border-blue-600 text-blue-700" : "border-transparent text-gray-600 hover:text-gray-900"
          }`}
          aria-selected={current === t.key}
          role="tab"
        >
          <span>{t.label}</span>
          {typeof t.badgeCount === "number" && (
            <span className="ml-2 inline-flex items-center rounded-full bg-gray-200 px-2 text-xs text-gray-700">
              {t.badgeCount}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}


