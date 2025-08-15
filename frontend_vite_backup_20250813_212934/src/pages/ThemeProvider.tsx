import { type ReactNode } from "react";
import { useEffect, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";

type Branding = {
  logo_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  dark_mode?: boolean;
};

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { token } = useSession();
  const [branding, setBranding] = useState<Branding | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${config.apiUrl}/api/v1/branding`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        });
        if (res.ok) setBranding(await res.json());
      } catch {}
      if (!cancelled) {
        // noop
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const root = document.documentElement;
    if (branding?.primary_color) root.style.setProperty("--brand-primary", branding.primary_color);
    if (branding?.secondary_color) root.style.setProperty("--brand-secondary", branding.secondary_color);
    if (branding?.dark_mode) root.classList.add("dark"); else root.classList.remove("dark");
  }, [branding]);

  return <>{children}</>;
}


