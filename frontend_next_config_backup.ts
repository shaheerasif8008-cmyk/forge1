import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // SSR/hybrid build for Azure SWA; do not use static export
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_ENV_LABEL: process.env.NEXT_PUBLIC_ENV_LABEL,
    NEXT_PUBLIC_GIT_SHA: process.env.NEXT_PUBLIC_GIT_SHA,
  },
};

export default nextConfig;
