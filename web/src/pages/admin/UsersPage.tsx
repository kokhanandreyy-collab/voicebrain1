import { useState, useEffect } from 'react';
import api from '../../api';
import { Search, LogIn, Ban, Shield, Gift, X } from 'lucide-react';

export default function UsersPage() {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    // Grant Modal State
    const [grantingUser, setGrantingUser] = useState<any>(null);
    const [grantTier, setGrantTier] = useState('pro');
    const [grantDuration, setGrantDuration] = useState<string>(''); // empty for lifetime

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchUsers();
        }, 500);
        return () => clearTimeout(timer);
    }, [search]);

    const fetchUsers = async () => {
        try {
            const { data } = await api.get(`/admin/users?search=${search}`);
            setUsers(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleImpersonate = async (userId: string) => {
        if (!confirm("Войти под этим пользователем?")) return;
        try {
            const { data } = await api.post(`/admin/impersonate/${userId}`);
            localStorage.setItem('token', data.access_token);
            window.location.href = '/dashboard';
        } catch (e) {
            alert('Ошибка входа');
        }
    };

    const handleGrant = async () => {
        if (!grantingUser) return;
        try {
            const duration = grantDuration ? parseInt(grantDuration) : null;
            await api.post(`/admin/users/${grantingUser.id}/grant_subscription`, {
                tier: grantTier,
                duration_days: duration
            });
            alert('Подписка выдана успешно');
            setGrantingUser(null);
            fetchUsers();
        } catch (e) {
            alert('Ошибка выдачи подписки');
        }
    };

    const handleBan = async (user: any) => {
        if (!confirm(`Вы уверены, что хотите ${user.is_active ? 'заблокировать' : 'разблокировать'} пользователя ${user.email}?`)) return;
        try {
            // Re-using ban endpoint. If we want unban we need another endpoint or toggle logic. 
            // Currently backend only has /ban which sets is_active=False. 
            // Assuming for now it's just ban. 
            // "Ban User" usually implies one direction unless we make it a toggle.
            // Let's assume for MVP it's just BAN.
            await api.post(`/admin/users/${user.id}/ban`);
            // Optimistic update
            setUsers(users.map(u => u.id === user.id ? { ...u, is_active: false } : u));
        } catch (e) {
            alert('Ошибка блокировки');
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold dark:text-white">Пользователи</h1>
                <div className="relative w-64">
                    <input
                        type="text"
                        placeholder="Поиск по email..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm"
                    />
                    <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
                </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-xs uppercase font-bold tracking-wider">
                        <tr>
                            <th className="p-4">Email</th>
                            <th className="p-4">Тариф</th>
                            <th className="p-4">Использовано минут</th>
                            <th className="p-4">Дата регистрации</th>
                            <th className="p-4 text-right">Действия</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {users.map((user) => (
                            <tr key={user.id} className={`hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors ${!user.is_active ? 'opacity-50 grayscale bg-red-50/10' : ''}`}>
                                <td className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-brand-blue/10 flex items-center justify-center text-brand-blue font-bold text-xs uppercase">
                                            {user.email[0]}
                                        </div>
                                        <div>
                                            <p className="font-medium text-slate-900 dark:text-white text-sm flex items-center gap-2">
                                                {user.email}
                                                {!user.is_active && <span className="text-[10px] bg-red-100 text-red-600 px-1 rounded uppercase font-bold">BANNED</span>}
                                            </p>
                                            {user.role === 'admin' && <span className="text-[10px] bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded font-bold flex items-center gap-1 w-fit mt-1"><Shield size={8} /> ADMIN</span>}
                                        </div>
                                    </div>
                                </td>
                                <td className="p-4">
                                    <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${user.tier === 'premium' ? 'bg-purple-50 text-purple-600' :
                                        user.tier === 'pro' ? 'bg-blue-50 text-blue-600' :
                                            'bg-slate-100 text-slate-500'
                                        }`}>
                                        {user.tier}
                                    </span>
                                </td>
                                <td className="p-4 text-sm text-slate-600 dark:text-slate-400">
                                    {Math.round((user.monthly_usage_seconds || 0) / 60)} мин
                                </td>
                                <td className="p-4 text-sm text-slate-500">
                                    {new Date(user.created_at).toLocaleDateString("ru-RU")}
                                </td>
                                <td className="p-4 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <button
                                            title="Выдать подписку"
                                            onClick={() => setGrantingUser(user)}
                                            className="p-1.5 text-slate-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                        >
                                            <Gift size={16} />
                                        </button>
                                        <button
                                            title="Войти как пользователь"
                                            onClick={() => handleImpersonate(user.id)}
                                            className="p-1.5 text-slate-400 hover:text-brand-blue hover:bg-blue-50 rounded-lg transition-colors"
                                        >
                                            <LogIn size={16} />
                                        </button>
                                        <button
                                            title={user.is_active ? "Блокировать" : "Разблокировать (Not Impl)"}
                                            onClick={() => handleBan(user)}
                                            className={`p-1.5 rounded-lg transition-colors ${user.is_active ? 'text-slate-400 hover:text-red-500 hover:bg-red-50' : 'text-red-500 hover:text-slate-500'}`}
                                        >
                                            <Ban size={16} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {users.length === 0 && !loading && (
                    <div className="p-8 text-center text-slate-500">Пользователи не найдены.</div>
                )}
            </div>

            {/* Grant Modal */}
            {grantingUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-200 dark:border-slate-800 animate-in fade-in zoom-in duration-200">
                        <div className="flex justify-between items-start mb-6">
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <Gift className="text-green-500" />
                                Выдать подписку
                            </h2>
                            <button onClick={() => setGrantingUser(null)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="mb-6">
                            <p className="text-slate-500 text-sm mb-4">
                                Выдача доступа для <span className="font-bold text-slate-900 dark:text-white">{grantingUser.email}</span>
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Тариф</label>
                                    <select
                                        value={grantTier}
                                        onChange={(e) => setGrantTier(e.target.value)}
                                        className="w-full p-2 bg-slate-50 dark:bg-slate-800 border-none rounded-lg"
                                    >
                                        <option value="pro">Pro</option>
                                        <option value="premium">Premium</option>
                                        <option value="free">Free (Отключить)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Длительность (Дней)</label>
                                    <input
                                        type="number"
                                        placeholder="Пусто = навсегда"
                                        value={grantDuration}
                                        onChange={(e) => setGrantDuration(e.target.value)}
                                        className="w-full p-2 bg-slate-50 dark:bg-slate-800 border-none rounded-lg"
                                    />
                                    <p className="text-[10px] text-slate-400 mt-1">Оставьте пустым для вечного доступа (или до ручной отмены).</p>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setGrantingUser(null)}
                                className="px-4 py-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg font-medium transition-colors"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={handleGrant}
                                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold shadow-lg shadow-green-500/20 transition-all"
                            >
                                Выдать доступ
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
