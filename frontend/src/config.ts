// Environment configuration for Forge 1 Frontend

interface Config {
  apiUrl: string;
  environment: string;
  version: string;
  features: {
    aiTasks: boolean;
    sessionManagement: boolean;
    errorBoundary: boolean;
  };
}

const config: Config = {
  apiUrl: import.meta.env.VITE_API_URL || "http://localhost:8000",
  environment: import.meta.env.VITE_ENVIRONMENT || "development",
  version: import.meta.env.VITE_APP_VERSION || "1.0.0",
  features: {
    aiTasks: true,
    sessionManagement: true,
    errorBoundary: true,
  },
};

// Validate configuration
if (!config.apiUrl) {
  console.error("VITE_API_URL is not set, using default localhost:8000");
}

// Development helpers
if (config.environment === "development") {
  console.log("Forge 1 Frontend Configuration:", config);
}

export default config;
