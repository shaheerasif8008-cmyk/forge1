declare global {
  interface Window {
    __BUILD_INFO?: {
      sha?: string;
      builtAt?: string;
      env?: string;
    };
  }
}

export const buildInfo = {
  sha: process.env.NEXT_PUBLIC_GIT_SHA ?? "unknown",
  builtAt: new Date().toISOString(),
  env: process.env.NEXT_PUBLIC_ENV_LABEL ?? "",
};

if (typeof window !== "undefined") {
  window.__BUILD_INFO = buildInfo;
}

export type BuildInfo = typeof buildInfo;


