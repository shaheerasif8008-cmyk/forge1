// Environment configuration for Forge1 Frontend

interface Config {
  apiBaseUrl: string;
  envLabel: string;
  useLocalStorageAuth: boolean;
}

const config: Config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  envLabel: process.env.NEXT_PUBLIC_ENV_LABEL || "Development",
  useLocalStorageAuth: process.env.USE_LOCAL_STORAGE_AUTH === "true",
};

// Validate configuration
if (!config.apiBaseUrl) {
  console.error("NEXT_PUBLIC_API_BASE_URL is not set");
}

// Development helpers
if (process.env.NODE_ENV === "development") {
  console.log("Forge1 Frontend Configuration:", config);
}

export default config;