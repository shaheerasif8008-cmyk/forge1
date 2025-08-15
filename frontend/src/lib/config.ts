// Environment configuration for Forge1 Frontend

interface Config {
	apiBaseUrl: string;
	envLabel: string;
	useLocalStorageAuth: boolean;
	testingServiceKey?: string;
	testingApiBaseUrl: string;
	eventsToken?: string;
}

const config: Config = {
	apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
	envLabel: process.env.NEXT_PUBLIC_ENV_LABEL || "Development",
	useLocalStorageAuth: process.env.USE_LOCAL_STORAGE_AUTH === "true",
	testingServiceKey: process.env.NEXT_PUBLIC_TESTING_SERVICE_KEY,
	testingApiBaseUrl: process.env.NEXT_PUBLIC_TESTING_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
	eventsToken: process.env.NEXT_PUBLIC_EVENTS_TOKEN || process.env.NEXT_PUBLIC_ADMIN_JWT,
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