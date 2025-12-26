import { useEffect, useState } from 'react';
import { rolesApi } from '../api';

interface Role {
  id: string;
  name: string;
  color: number;
  position: number;
}

interface Category {
  id: string;
  name: string;
  color: number;
  roles: Role[];
  is_real_category: boolean;
}

export default function Roles() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRole, setEditingRole] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const data = await rolesApi.list();
      setCategories(data.categories);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  const handleUpdate = async (roleId: string) => {
    try {
      await rolesApi.update(roleId, {
        name: editName || undefined,
        color: editColor ? parseInt(editColor.replace('#', ''), 16) : undefined
      });
      setEditingRole(null);
      fetchRoles();
    } catch (err) {
      alert('Failed to update role');
    }
  };

  const handleCreate = async () => {
    const name = prompt('Enter role name:');
    if (name) {
      await rolesApi.create(name);
      fetchRoles();
    }
  };

  const handleDelete = async (roleId: string) => {
    if (confirm('Are you sure you want to delete this role?')) {
      await rolesApi.delete(roleId);
      fetchRoles();
    }
  };

  const colorToHex = (color: number) => `#${color.toString(16).padStart(6, '0')}`;

  if (loading) return <div>Loading roles...</div>;

  return (
    <div>
      <h2 style={{ marginBottom: '24px' }}>🎭 Role Management</h2>
      
      <button className="btn btn-primary" onClick={handleCreate} style={{ marginBottom: '20px' }}>
        + Create Role
      </button>

      {categories.map(category => (
        <div className="card" key={category.id}>
          <div className="card-header">
            <span className="card-title" style={{ color: colorToHex(category.color) }}>
              {category.is_real_category ? '📁 ' : '📋 '}{category.name}
            </span>
          </div>
          
          {category.roles.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Color</th>
                  <th>Name</th>
                  <th>Position</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {category.roles.map(role => (
                  <tr key={role.id}>
                    <td>
                      <div style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '4px',
                        backgroundColor: colorToHex(role.color)
                      }} />
                    </td>
                    <td>
                      {editingRole === role.id ? (
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          placeholder={role.name}
                        />
                      ) : (
                        <span style={{ color: colorToHex(role.color) }}>{role.name}</span>
                      )}
                    </td>
                    <td>{role.position}</td>
                    <td>
                      {editingRole === role.id ? (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <input
                            type="color"
                            value={editColor || colorToHex(role.color)}
                            onChange={(e) => setEditColor(e.target.value)}
                            style={{ width: '40px' }}
                          />
                          <button className="btn btn-primary" onClick={() => handleUpdate(role.id)}>Save</button>
                          <button className="btn" onClick={() => setEditingRole(null)}>Cancel</button>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="btn btn-primary" onClick={() => {
                            setEditingRole(role.id);
                            setEditName(role.name);
                            setEditColor(colorToHex(role.color));
                          }}>
                            Edit
                          </button>
                          <button className="btn btn-danger" onClick={() => handleDelete(role.id)}>
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ color: '#888' }}>No roles in this category</p>
          )}
        </div>
      ))}
    </div>
  );
}
