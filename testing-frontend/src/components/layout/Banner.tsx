export function AdminJwtBanner() {
  const hasJwt = Boolean(localStorage.getItem('testing_admin_jwt') || (import.meta as any).env?.VITE_TESTING_ADMIN_JWT)
  if (hasJwt) return null
  return (
    <div className="w-full bg-yellow-100 px-4 py-2 text-sm text-yellow-900">
      Warning: Admin JWT not set. Protected endpoints may fail. Set VITE_TESTING_ADMIN_JWT or localStorage key "testing_admin_jwt".
    </div>
  )
}


