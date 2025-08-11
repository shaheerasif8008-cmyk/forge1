import { useEffect, useState } from "react";
import { useSession } from "../components/SessionManager";
import config from "../config";

type Health = { status: string; postgres: boolean; redis: boolean };
type ModelInfo = { name: string; capabilities: string[]; available: boolean };
type TaskResult = { 
  success: boolean; 
  output: string; 
  model_used: string; 
  execution_time: number; 
  metadata: Record<string, any>; 
  error?: string; 
};

type Employee = {
  id: string;
  name: string;
  tenant_id: string;
  owner_user_id?: number;
  config: Record<string, any>;
};

export default function DashboardPage() {
  const { user, logout } = useSession();
  const [health, setHealth] = useState<Health | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [taskInput, setTaskInput] = useState("");
  const [taskType, setTaskType] = useState("general");
  const [selectedModel, setSelectedModel] = useState("");
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);
  const [executing, setExecuting] = useState(false);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [newEmpName, setNewEmpName] = useState("");
  const [newEmpRole, setNewEmpRole] = useState("Sales Agent");
  const [newEmpDesc, setNewEmpDesc] = useState("Helps with sales outreach and lead follow-up");

  useEffect(() => {
    // Fetch health status
    fetch(`${config.apiUrl}/api/v1/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));

    // Fetch AI models and capabilities
    const token = localStorage.getItem("access_token");
    if (token) {
      fetch(`${config.apiUrl}/api/v1/ai/models`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          setModels(data || []);
          if (data && data.length > 0) {
            setSelectedModel(data[0].name);
          }
        })
        .catch(() => setModels([]));

      fetch(`${config.apiUrl}/api/v1/ai/capabilities`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setCapabilities(data || []))
        .catch(() => setCapabilities([]));

      // Load employees
      fetch(`${config.apiUrl}/api/v1/employees/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setEmployees(data || []))
        .catch(() => setEmployees([]));
    }
    const pollId = setInterval(() => {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      fetch(`${config.apiUrl}/api/v1/employees/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => setEmployees(data || []))
        .catch(() => {});
    }, 10000);
    return () => clearInterval(pollId);
  }, []);

  const executeTask = async () => {
    if (!taskInput.trim()) return;

    setExecuting(true);
    setTaskResult(null);

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${config.apiUrl}/api/v1/ai/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          task: taskInput,
          task_type: taskType,
          model_name: selectedModel || undefined,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setTaskResult(result);
      } else {
        const error = await response.text();
        setTaskResult({
          success: false,
          output: "",
          model_used: "",
          execution_time: 0,
          metadata: {},
          error: error,
        });
      }
    } catch (error) {
      setTaskResult({
        success: false,
        output: "",
        model_used: "",
        execution_time: 0,
        metadata: {},
        error: `Network error: ${error}`,
      });
    } finally {
      setExecuting(false);
    }
  };

  const createEmployee = async () => {
    const token = localStorage.getItem("access_token");
    if (!token || !newEmpName.trim()) return;
    const resp = await fetch(`${config.apiUrl}/api/v1/employees/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: newEmpName,
        role_name: newEmpRole,
        description: newEmpDesc,
        tools: ["api_caller", "web_scraper"],
      }),
    });
    if (resp.ok) {
      const created = (await resp.json()) as Employee;
      setEmployees([created, ...employees]);
      setNewEmpName("");
    }
  };

  const runEmployee = async (employeeId: string) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    await fetch(`${config.apiUrl}/api/v1/employees/${employeeId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ task: taskInput || "Introduce yourself." }),
    });
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-semibold">Forge 1 Dashboard</h1>
        <button
          onClick={logout}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
        >
          Logout
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Health & User Info */}
        <div className="space-y-6">
          {/* Health Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-medium mb-4">Backend Health</h2>
            {health ? (
              <ul className="space-y-2 text-sm">
                <li className="flex items-center">
                  <span className="font-medium">Status:</span>
                  <span
                    className={`ml-2 px-2 py-1 rounded text-xs ${
                      health.status === "healthy"
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {health.status}
                  </span>
                </li>
                <li className="flex items-center">
                  <span className="font-medium">Postgres:</span>
                  <span
                    className={`ml-2 px-2 py-1 rounded text-xs ${
                      health.postgres
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {String(health.postgres)}
                  </span>
                </li>
                <li className="flex items-center">
                  <span className="font-medium">Redis:</span>
                  <span
                    className={`ml-2 px-2 py-1 rounded text-xs ${
                      health.redis
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {String(health.redis)}
                  </span>
                </li>
              </ul>
            ) : (
              <p className="text-gray-600 text-sm">Loading...</p>
            )}
          </div>

          {/* User Info Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-medium mb-4">User Info</h2>
            {user ? (
              <div className="space-y-2 text-sm">
                <p>
                  <span className="font-medium">ID:</span> {user.id}
                </p>
                <p>
                  <span className="font-medium">Tenant:</span> {user.tenant_id}
                </p>
                {user.email && (
                  <p>
                    <span className="font-medium">Email:</span> {user.email}
                  </p>
                )}
                {user.username && (
                  <p>
                    <span className="font-medium">Username:</span> {user.username}
                  </p>
                )}
                {user.role && (
                  <p>
                    <span className="font-medium">Role:</span> {user.role}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-red-600 text-sm">Failed to load user info</p>
            )}
          </div>

          {/* Models Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-medium mb-4">Available Models</h2>
            {models.length > 0 ? (
              <div className="space-y-2">
                {models.map((model) => (
                  <div key={model.name} className="text-sm">
                    <div className="font-medium">{model.name}</div>
                    <div className="text-gray-600 text-xs">
                      {model.capabilities.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-600 text-sm">No models available</p>
            )}
          </div>
        </div>

        {/* Right Column - AI Task Interface */}
        <div className="lg:col-span-2 space-y-6">
          {/* Employees Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-medium mb-4">Employees</h2>
            <div className="flex flex-col md:flex-row gap-2 mb-4">
              <input
                placeholder="New employee name"
                value={newEmpName}
                onChange={(e) => setNewEmpName(e.target.value)}
                className="border rounded px-3 py-2 flex-1"
              />
              <input
                placeholder="Role"
                value={newEmpRole}
                onChange={(e) => setNewEmpRole(e.target.value)}
                className="border rounded px-3 py-2"
              />
              <input
                placeholder="Description"
                value={newEmpDesc}
                onChange={(e) => setNewEmpDesc(e.target.value)}
                className="border rounded px-3 py-2 flex-[2]"
              />
              <button onClick={createEmployee} className="bg-green-600 text-white px-4 py-2 rounded">
                Create
              </button>
            </div>
            {employees.length ? (
              <ul className="divide-y">
                {employees.map((e) => (
                  <li key={e.id} className="py-2 flex justify-between items-center">
                    <div>
                      <div className="font-medium">{e.name}</div>
                      <div className="text-xs text-gray-500">{e.id}</div>
                    </div>
                    <button
                      onClick={() => runEmployee(e.id)}
                      className="px-3 py-1 bg-blue-600 text-white rounded"
                    >
                      Run
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-600 text-sm">No employees yet</p>
            )}
          </div>

          {/* Task Input Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-medium mb-4">AI Task Execution</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Task Description</label>
                <textarea
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  placeholder="Describe what you want the AI to do..."
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-500"
                  rows={4}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Task Type</label>
                  <select
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                    className="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-500"
                  >
                    {capabilities.map((cap) => (
                      <option key={cap} value={cap}>
                        {cap.charAt(0).toUpperCase() + cap.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Model (Optional)</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-500"
                  >
                    <option value="">Auto-select</option>
                    {models.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={executeTask}
                disabled={executing || !taskInput.trim()}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
              >
                {executing ? "Executing..." : "Execute Task"}
              </button>
            </div>
          </div>

          {/* Task Result Panel */}
          {taskResult && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-medium mb-4">Task Result</h2>
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <span className="font-medium">Status:</span>
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      taskResult.success
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {taskResult.success ? "Success" : "Failed"}
                  </span>
                  <span className="text-sm text-gray-600">
                    Model: {taskResult.model_used}
                  </span>
                  <span className="text-sm text-gray-600">
                    Time: {taskResult.execution_time.toFixed(2)}s
                  </span>
                </div>

                {taskResult.error && (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <p className="text-red-800 text-sm">{taskResult.error}</p>
                  </div>
                )}

                {taskResult.output && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Output</label>
                    <div className="bg-gray-50 border rounded p-3">
                      <pre className="whitespace-pre-wrap text-sm text-gray-800">
                        {taskResult.output}
                      </pre>
                    </div>
                  </div>
                )}

                {Object.keys(taskResult.metadata).length > 0 && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Metadata</label>
                    <div className="bg-gray-50 border rounded p-3">
                      <pre className="text-sm text-gray-800">
                        {JSON.stringify(taskResult.metadata, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
