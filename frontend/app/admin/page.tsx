// app/admin/page.tsx
export default function AdminPage() {
  const fakeUsers = [
    { name: "Adarsh", role: "frontend" },
    { name: "Shreya", role: "backend" },
    { name: "Arnav", role: "devops" },
  ];

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="mb-6 text-2xl font-bold text-gray-800">Admin</h1>

      <div className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-3 text-lg font-semibold text-gray-700">Users</h2>
        <ul className="space-y-2">
          {fakeUsers.map((u) => (
            <li key={u.name} className="flex justify-between text-gray-700">
              <span>{u.name}</span>
              <span className="text-sm text-gray-400">{u.role}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-3 text-lg font-semibold text-gray-700">
          Model Version
        </h2>
        <p className="text-gray-600">v0.1.0-dummy (placeholder until AI/ML integration)</p>
      </div>
    </div>
  );
}