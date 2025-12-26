import { useEffect, useState } from 'react';
import { usersApi, User } from '../api';

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState<number | null>(null);
  const [seedAmount, setSeedAmount] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    const data = await usersApi.list(page, 20, search);
    setUsers(data.users);
    setTotal(data.total);
    setLoading(false);
  };

  useEffect(() => {
    fetchUsers();
  }, [page, search]);

  const handleAdjustSeeds = async (userId: number) => {
    const amount = parseInt(seedAmount);
    if (isNaN(amount)) return;
    
    try {
      await usersApi.updateSeeds(userId, amount, 'Admin Panel');
      setEditingUser(null);
      setSeedAmount('');
      fetchUsers();
    } catch (err) {
      alert('Failed to update seeds');
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>👥 User Management</h2>
      
      {/* Search */}
      <div style={{ marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="Tìm kiếm user..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: '300px' }}
        />
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Balance</th>
              <th>Last Daily</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5}>Loading...</td></tr>
            ) : users.map(user => (
              <tr key={user.user_id}>
                <td>{user.user_id}</td>
                <td>{user.username || '-'}</td>
                <td>{user.seeds.toLocaleString()} 🌱</td>
                <td>{user.last_daily ? new Date(user.last_daily).toLocaleDateString() : '-'}</td>
                <td>
                  {editingUser === user.user_id ? (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="number"
                        placeholder="+/- amount"
                        value={seedAmount}
                        onChange={(e) => setSeedAmount(e.target.value)}
                        style={{ width: '120px' }}
                      />
                      <button className="btn btn-primary" onClick={() => handleAdjustSeeds(user.user_id)}>
                        ✓
                      </button>
                      <button className="btn" onClick={() => setEditingUser(null)}>
                        ✗
                      </button>
                    </div>
                  ) : (
                    <button className="btn btn-primary" onClick={() => setEditingUser(user.user_id)}>
                      Edit Seeds
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {/* Pagination */}
        <div style={{ marginTop: '16px', display: 'flex', gap: '8px', justifyContent: 'center' }}>
          <button className="btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
            ← Prev
          </button>
          <span style={{ padding: '8px 16px' }}>Page {page} of {Math.ceil(total / 20)}</span>
          <button className="btn" onClick={() => setPage(p => p + 1)} disabled={page * 20 >= total}>
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
