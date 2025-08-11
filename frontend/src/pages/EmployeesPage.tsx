import { useEffect, useState } from "react";
import config from "../config";

type Employee = { id: string; name: string; tenant_id: string };

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [name, setName] = useState("");
  const [role, setRole] = useState("Sales Agent");
  const [desc, setDesc] = useState("Helps with sales outreach and follow-up");

  const reload = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const res = await fetch(`${config.apiUrl}/api/v1/employees/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setEmployees(res.ok ? ((await res.json()) as Employee[]) : []);
  };

  useEffect(() => {
    void reload();
  }, []);

  const create = async () => {
    const token = localStorage.getItem("access_token");
    if (!token || !name.trim()) return;
    const res = await fetch(`${config.apiUrl}/api/v1/employees/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name, role_name: role, description: desc, tools: ["api_caller"] }),
    });
    if (res.ok) {
      await reload();
      setName("");
    }
  };

  const run = async (id: string) => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    await fetch(`${config.apiUrl}/api/v1/employees/${id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ task: "Introduce yourself." }),
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Employees</h1>
      <div className="bg-white rounded shadow p-4 flex flex-col sm:flex-row gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className="border rounded px-3 py-2 flex-1" />
        <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role" className="border rounded px-3 py-2" />
        <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Description" className="border rounded px-3 py-2 flex-[2]" />
        <button onClick={create} className="bg-green-600 text-white px-4 py-2 rounded">Create</button>
      </div>
      <div className="bg-white rounded shadow p-4">
        {employees.length ? (
          <ul className="divide-y">
            {employees.map((e) => (
              <li key={e.id} className="py-2 flex justify-between items-center">
                <div>
                  <div className="font-medium">{e.name}</div>
                  <div className="text-xs text-gray-500">{e.id}</div>
                </div>
                <button onClick={() => run(e.id)} className="px-3 py-1 bg-blue-600 text-white rounded">Run</button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-600 text-sm">No employees yet</p>
        )}
      </div>
    </div>
  );
}


