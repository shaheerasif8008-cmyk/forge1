import { useEffect, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";
import { useToast } from "../components/Toast";
import { CopyButton } from "../components/CopyButton";

interface UserRow { id: number; email: string; role: string }

export default function AdminUsersPage() {
  const { token } = useSession();
  const { push } = useToast();
  const [rows, setRows] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteLink, setInviteLink] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${config.apiUrl}/api/v1/admin/users`, { headers: { Authorization: `Bearer ${token}` } });
      if (resp.ok) setRows(await resp.json());
    } catch {}
    setLoading(false);
  };

  useEffect(() => { if (token) void load(); }, [token]);

  const invite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Tenant passed server-side from session; role included here
      const resp = await fetch(`${config.apiUrl}/api/v1/admin/users/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email: inviteEmail, tenant_id: "", role: inviteRole }),
      });
      const data = await resp.json();
      if (resp.ok) { setInviteLink(data.link || null); push("Invite created", "success"); }
      else push(data.detail || "Failed to invite", "error");
    } catch { push("Network error", "error"); }
  };

  const changeRole = async (userId: number, role: string) => {
    const resp = await fetch(`${config.apiUrl}/api/v1/admin/users/${userId}/role`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ role }),
    });
    if (resp.ok) { push("Role updated", "success"); void load(); } else push("Failed to update role", "error");
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Users</h1>
      <form onSubmit={invite} className="flex gap-2 items-end">
        <div>
          <label className="block text-sm">Email</label>
          <input className="border rounded px-3 py-2" type="email" value={inviteEmail} onChange={(e)=>setInviteEmail(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm">Role</label>
          <select className="border rounded px-3 py-2" value={inviteRole} onChange={(e)=>setInviteRole(e.target.value)}>
            <option value="owner">owner</option>
            <option value="admin">admin</option>
            <option value="member">member</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <button className="bg-blue-600 text-white rounded px-3 py-2">Invite</button>
        {inviteLink && (
          <div className="flex items-center gap-2 text-sm">
            <code className="break-all">{inviteLink}</code>
            <CopyButton text={inviteLink} />
          </div>
        )}
      </form>

      <div className="bg-white rounded shadow divide-y">
        <div className="grid grid-cols-3 p-3 font-medium text-sm"><div>Email</div><div>Role</div><div>Actions</div></div>
        {loading ? (
          <div className="p-3 text-sm">Loading...</div>
        ) : rows.length === 0 ? (
          <div className="p-3 text-sm text-gray-500">No users</div>
        ) : (
          rows.map((u) => (
            <div key={u.id} className="grid grid-cols-3 p-3 text-sm items-center">
              <div>{u.email}</div>
              <div>
                <select className="border rounded px-2 py-1" value={u.role} onChange={(e)=>changeRole(u.id, e.target.value)}>
                  <option value="owner">owner</option>
                  <option value="admin">admin</option>
                  <option value="member">member</option>
                  <option value="viewer">viewer</option>
                </select>
              </div>
              <div className="text-right">
                {/* Placeholder for session revoke per-user; a sessions page can render user's sessions */}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}


