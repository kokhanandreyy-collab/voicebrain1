import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, Navigate } from 'react-router-dom';
import { LayoutDashboard, Users, CreditCard, ShieldAlert, Tag, Bot } from 'lucide-react';
import api from '../api';

export default function AdminLayout() {
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const location = useLocation();

    useEffect(() => {
        api.get('/auth/me').then(({ data }) => {
            setUser(data);
            setLoading(false);
        }).catch(() => {
            setLoading(false);
        });
    }, []);

    if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950"><div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-blue border-t-transparent"></div></div>;

    if (!user || user.role !== 'admin') {
        return <Navigate to="/dashboard" replace />;
    }

    const navItems = [
        { icon: LayoutDashboard, label: 'Обзор', path: '/admin' },
        { icon: Users, label: 'Пользователи', path: '/admin/users' },
        { icon: CreditCard, label: 'Тарифы', path: '/admin/plans' },
        { icon: Tag, label: 'Промокоды', path: '/admin/promocodes' },
        { icon: Bot, label: 'Промпты ИИ', path: '/admin/prompts' },
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex">
            {/* Sidebar */}
            <aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col fixed h-full z-20">
                <div className="p-6">
                    <div className="flex items-center gap-2 text-brand-blue font-bold text-xl">
                        <ShieldAlert /> Admin
                    </div>
                </div>

                <nav className="flex-1 px-4 space-y-1">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${isActive
                                    ? 'bg-brand-blue/10 text-brand-blue'
                                    : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 dark:text-slate-400'
                                    }`}
                            >
                                <item.icon size={20} />
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                <div className="p-4 border-t border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-3 px-4 py-3">
                        <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700" />
                        <div className="overflow-hidden">
                            <p className="text-sm font-bold truncate dark:text-white">{user.email}</p>
                            <p className="text-xs text-slate-400">Administrator</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8">
                <Outlet />
            </main>
        </div>
    );
}
