import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	env: {
		NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
		NEXT_PUBLIC_ENV_LABEL: process.env.NEXT_PUBLIC_ENV_LABEL,
		USE_LOCAL_STORAGE_AUTH: process.env.USE_LOCAL_STORAGE_AUTH,
		NEXT_PUBLIC_TESTING_SERVICE_KEY: process.env.NEXT_PUBLIC_TESTING_SERVICE_KEY,
	},
	// Use standalone output for containerization
	output: process.env.NEXT_BUILD_MODE === "export" ? "export" : "standalone",
	trailingSlash: true,
};

export default nextConfig;
