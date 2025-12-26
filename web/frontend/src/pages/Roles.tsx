
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  DndContext, 
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  defaultDropAnimationSideEffects,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Move, Save, RefreshCw, Folder, Plus, ChevronDown, ChevronRight, Edit2, Trash2 } from 'lucide-react';

// --- Types ---
interface Role {
  id: string;
  name: string;
  color: number;
  position: number;
}

interface Category {
  id: string;
  name: string;
  roles: Role[];
  is_real_category: boolean;
  position: number;
}

interface PendingUpdate {
  id: string;
  name?: string;
  color?: number;
}

// --- Sortable Item Component ---
function SortableItem({ id, children, className, style, disabled }: any) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id, disabled });

  const combinedStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    ...style
  };

  return (
    <div ref={setNodeRef} style={combinedStyle} className={className} {...attributes} {...listeners}>
       {children}
    </div>
  );
}

// --- Main Component ---
export default function Roles() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState('');
  
  // New Features State
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [pendingUpdates, setPendingUpdates] = useState<Record<string, PendingUpdate>>({});

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    fetchRoles();
  }, []);

  // Poll for task status
  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/roles/batch/${taskId}`);
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          setSaving(false);
          setStatusMsg(res.data.status === 'completed' ? 'Saved Successfully!' : `Error: ${res.data.error}`);
          setTaskId(null);
          setDirty(false);
          setPendingUpdates({}); // Clear updates on success
          clearInterval(interval);
          if (res.data.status === 'completed') fetchRoles(); 
        } else {
          setStatusMsg(`Saving... ${res.data.progress}%`);
        }
      } catch (e) {
        console.error(e);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [taskId]);

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/roles');
      const fetchedCats = res.data.categories || [];
      setCategories(fetchedCats);
      
      // Default expand all
      const initialExpanded: Record<string, boolean> = {};
      fetchedCats.forEach((c: Category) => initialExpanded[c.id] = true);
      setExpanded(initialExpanded);
      
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setStatusMsg('Queuing update...');
    try {
      const payload = {
        updates: Object.values(pendingUpdates),
        reorder: {
            categories: categories.map(c => ({
                id: c.id,
                is_real_category: c.is_real_category,
                role_ids: c.roles.map(r => r.id)
            }))
        }
      };

      const res = await axios.post('/api/roles/batch', payload);
      setTaskId(res.data.task_id);
    } catch (err) {
      console.error(err);
      setSaving(false);
      setStatusMsg('Failed to start save job.');
    }
  };

  // --- Actions ---
  const toggleExpand = (catId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent drag start when clicking toggle
    setExpanded(prev => ({...prev, [catId]: !prev[catId]}));
  };

  const startEditing = (id: string, currentName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(id);
    setEditValue(currentName);
  };

  const saveEditing = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!editingId) return;

    // Determine if it's a category or role
    let isCat = false;
    let found = false;

    // Update Local State
    const newCats = categories.map(c => {
        if (c.id === editingId) {
            isCat = true;
            found = true;
            return { ...c, name: editValue };
        }
        const updatedRoles = c.roles.map(r => {
            if (r.id === editingId) {
                found = true;
                return { ...r, name: editValue };
            }
            return r;
        });
        return { ...c, roles: updatedRoles };
    });

    if (found) {
        setCategories(newCats);
        setDirty(true);
        setPendingUpdates(prev => ({
            ...prev,
            [editingId]: { ...prev[editingId], id: editingId, name: editValue }
        }));
    }
    setEditingId(null);
  };

  const handleCreateRole = async (catId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const roleName = prompt("Enter new role name:");
    if (!roleName) return;

    try {
        setLoading(true);
        // Call API to create (Default position is bottom on Discord, but we just need the ID)
        const res = await axios.post('/api/roles/create', { name: roleName });
        const newRole = res.data; // { id, name, ... }
        
        // Add to local state in the correct category
        setCategories(prev => prev.map(c => {
            if (c.id === catId) {
                return { 
                    ...c, 
                    roles: [
                        { id: newRole.id, name: newRole.name, color: newRole.color, position: 0 }, 
                        ...c.roles 
                    ] 
                };
            }
            return c;
        }));
        
        setDirty(true); // Position needs saving
        setStatusMsg('Role created! Click Save to sync position.');
    } catch (err) {
        alert('Failed to create role');
    } finally {
        setLoading(false);
    }
  };

  // --- Drag Handlers ---
  function findContainer(id: string) {
    if (categories.find(c => c.id === id)) return id;
    return categories.find(c => c.roles.find(r => r.id === id))?.id;
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;
    
    const activeId = String(active.id);
    const overId = String(over.id);
    const activeContainer = findContainer(activeId);
    const overContainer = findContainer(overId);
    
    if (!activeContainer || !overContainer || activeContainer === overContainer) {
      return;
    }

    setCategories(prev => {
        const activeItems = prev.find(c => c.id === activeContainer)?.roles || [];
        const overItems = prev.find(c => c.id === overContainer)?.roles || [];
        const activeIndex = activeItems.findIndex(r => r.id === activeId);
        const overIndex = overItems.findIndex(r => r.id === overId);
        
        let newIndex;
        if (overId in prev.find(c => c.id === overContainer)!) { 
             newIndex = overItems.length + 1;
        } else {
             const isBelowOverItem =
              over &&
              active.rect.current.translated &&
              active.rect.current.translated.top >
                over.rect.top + over.rect.height;
    
            const modifier = isBelowOverItem ? 1 : 0;
            newIndex = overIndex >= 0 ? overIndex + modifier : overItems.length + 1;
        }
        return prev; 
    });
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    const activeId = String(active.id);
    const overId = String(over ? over.id : '');

    if (!over) return;
    if (editingId) return; // Disable drag while editing

    const activeCatIndex = categories.findIndex(c => c.id === activeId);
    const overCatIndex = categories.findIndex(c => c.id === overId);

    if (activeCatIndex !== -1 && overCatIndex !== -1) {
       if (activeCatIndex !== overCatIndex) {
           setCategories(prev => arrayMove(prev, activeCatIndex, overCatIndex));
           setDirty(true);
       }
       return;
    }

    const activeContainer = findContainer(activeId);
    if (activeContainer) {
        const catIndex = categories.findIndex(c => c.id === activeContainer);
        const roles = categories[catIndex].roles;
        const activeIndex = roles.findIndex(r => r.id === activeId);
        const overIndex = roles.findIndex(r => r.id === overId);
        
        if (activeIndex !== -1 && overIndex !== -1 && activeIndex !== overIndex) {
            const newRoles = arrayMove(roles, activeIndex, overIndex);
            const newCats = [...categories];
            newCats[catIndex] = { ...newCats[catIndex], roles: newRoles };
            setCategories(newCats);
            setDirty(true);
        }
    }
  };

  if (loading && !categories.length) return <div style={{padding:'20px'}}>Loading Roles...</div>;

  return (
    <div className="roles-page" style={{paddingBottom: '80px'}}>
      
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2>Role Management</h2>
        <button className="btn btn-secondary" onClick={fetchRoles} disabled={loading}>
            <RefreshCw size={16}/> Refresh
        </button>
      </div>

      {/* Sticky Header - Only show if dirty or saving */}
      {(dirty || saving) && (
        <div className="sticky-bar">
            <span style={{fontWeight: 'bold', color: 'var(--accent-warning)'}}>
                ⚠️ Unsaved Changes
            </span>
            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                {statusMsg && <span style={{color: 'var(--text-secondary)'}}>{statusMsg}</span>}
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                    <Save size={16} /> Save Changes
                </button>
            </div>
        </div>
      )}

      <DndContext 
        sensors={sensors} 
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext 
          items={categories.map(c => c.id)} 
          strategy={verticalListSortingStrategy}
        >
          {categories.map((category) => (
            <SortableItem key={category.id} id={category.id} className="card" style={{padding: '0', overflow: 'hidden'}}>
                
                {/* Category Header */}
                <div 
                   className="card-header" 
                   style={{
                       background: 'var(--bg-overlay)', 
                       padding: '0.8rem 1rem', 
                       margin:0,
                       cursor: 'grab',
                       borderBottom: expanded[category.id] ? '1px solid var(--border-color)' : 'none',
                       display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                   }}
                >
                    <div style={{display: 'flex', alignItems: 'center', gap: '10px', flex: 1}}>
                        {/* Toggle Collapse */}
                        <div 
                            onClick={(e) => toggleExpand(category.id, e)} 
                            style={{cursor: 'pointer', display: 'flex', alignItems: 'center'}}
                            onPointerDown={e => e.stopPropagation()} 
                        >
                            {expanded[category.id] ? <ChevronDown size={18}/> : <ChevronRight size={18}/>}
                        </div>
                        
                        <Folder size={18} color="var(--accent-primary)"/>
                        
                        {/* Editable Name */}
                        {editingId === category.id ? (
                            <input 
                                autoFocus
                                value={editValue}
                                onChange={e => setEditValue(e.target.value)}
                                onBlur={() => saveEditing()}
                                onKeyDown={e => e.key === 'Enter' && saveEditing()}
                                onClick={e => e.stopPropagation()}
                                onPointerDown={e => e.stopPropagation()}
                                style={{background: 'var(--bg-base)', border:'1px solid var(--accent-primary)', color: 'white'}}
                            />
                        ) : (
                            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                                <span 
                                    className="mono" 
                                    onDoubleClick={(e) => startEditing(category.id, category.name, e)}
                                    title="Double click to rename"
                                >
                                    {category.name}
                                </span>
                                <button 
                                    className="btn-icon" 
                                    style={{background: 'transparent', border:'none', cursor:'pointer', color:'var(--text-dim)'}}
                                    onClick={(e) => startEditing(category.id, category.name, e)}
                                    onPointerDown={e => e.stopPropagation()}
                                >
                                    <Edit2 size={12}/>
                                </button>
                            </div>
                        )}

                        {category.is_real_category && <span style={{fontSize:'0.7em', padding: '2px 6px', background: 'var(--bg-base)', borderRadius:'4px', color:'var(--text-dim)'}}>CAT</span>}
                        <span style={{fontSize:'0.8em', color:'var(--text-dim)'}}>({category.roles.length} Roles)</span>
                    </div>

                    {/* Actions */}
                    <div className="actions" style={{display: 'flex', gap: '8px'}}>
                        <button 
                            className="btn-icon" 
                            title="Add Role Here"
                            style={{background: 'transparent', border:'none', cursor:'pointer', color:'var(--accent-success)'}}
                            onClick={(e) => handleCreateRole(category.id, e)}
                            onPointerDown={e => e.stopPropagation()}
                        >
                            <Plus size={16}/>
                        </button>
                    </div>
                </div>

                 {/* Roles List */}
                 {expanded[category.id] && (
                     <div style={{padding: '0.5rem'}}>
                        <SortableContext items={category.roles.map(r => r.id)} strategy={verticalListSortingStrategy}>
                            {category.roles.map(role => (
                                <SortableItem key={role.id} id={role.id} className="role-item">
                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: '10px',
                                        padding: '8px', 
                                        background: 'var(--bg-base)',
                                        marginBottom: '6px',
                                        borderRadius: '4px',
                                        border: '1px solid var(--border-color)',
                                        cursor: 'grab'
                                    }}
                                    >
                                        <Move size={14} color="var(--text-dim)"/>
                                        <div 
                                          style={{
                                              width: '12px', height: '12px', borderRadius: '50%', 
                                              backgroundColor: role.color ? `#${role.color.toString(16).padStart(6, '0')}` : '#99aab5'
                                          }}
                                        />
                                        
                                        {/* Editable Role Name */}
                                        {editingId === role.id ? (
                                            <input 
                                                autoFocus
                                                value={editValue}
                                                onChange={e => setEditValue(e.target.value)}
                                                onBlur={() => saveEditing()}
                                                onKeyDown={e => e.key === 'Enter' && saveEditing()}
                                                onClick={e => e.stopPropagation()}
                                                onPointerDown={e => e.stopPropagation()}
                                                style={{background: 'var(--bg-base)', border:'1px solid var(--accent-primary)', color: 'white', flex: 1}}
                                            />
                                        ) : (
                                            <div style={{display: 'flex', alignItems: 'center', gap: '8px', flex: 1}}>
                                                <span 
                                                    onDoubleClick={(e) => startEditing(role.id, role.name, e)}
                                                    title="Double click to rename"
                                                >
                                                    {role.name}
                                                </span>
                                                <button 
                                                    className="btn-icon" 
                                                    style={{background: 'transparent', border:'none', cursor:'pointer', color:'var(--text-dim)', opacity: 0.5}}
                                                    onClick={(e) => startEditing(role.id, role.name, e)}
                                                    onPointerDown={e => e.stopPropagation()}
                                                >
                                                    <Edit2 size={12}/>
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </SortableItem>
                            ))}
                        </SortableContext>
                     </div>
                 )}
            </SortableItem>
          ))}
        </SortableContext>
      </DndContext>
    </div>
  );
}
