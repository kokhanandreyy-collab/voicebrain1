import { useState, useEffect } from 'react';
import api from '../api';
import { ArrowLeft, Clock, BarChart3, PieChart as PieIcon, CheckCircle, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface UserStats {
    total_notes: number;
    saved_time_minutes: number;
    usage_minutes_this_month: number;
    limit_minutes: number;
    balance_days_remaining: number;
    subscription_renews_at: string;
    plan_name: string;
    productivity_trend: { date: string; count: number }[];
    integration_usage: { name: string; value: number }[];
}

export default function StatsPage() {
    const [stats, setStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const { data } = await api.get('/users/stats');
            setStats(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950"><div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-blue border-t-transparent"></div></div>;
    if (!stats) return <div className="p-8 text-center">Failed to load stats</div>;

    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];
    const usagePercent = Math.min(100, (stats.usage_minutes_this_month / stats.limit_minutes) * 100);

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-12">
            <div className="max-w-6xl mx-auto space-y-12">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <Link to="/dashboard" className="p-2 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors">
                        <ArrowLeft className="text-slate-500 dark:text-slate-400" />
                    </Link>
                    <h1 className="text-3xl font-bold dark:text-white">Your Profile & Stats</h1>
                </div>

                {/* Hero Card: Time Saved */}
                <div className="bg-gradient-to-br from-brand-blue to-blue-600 rounded-[32px] p-8 md:p-12 text-white shadow-xl shadow-brand-blue/20 relative overflow-hidden">
                    <div className="relative z-10">
                        <div className="flex items-center gap-3 text-blue-100 mb-2 font-medium">
                            <Clock size={20} /> Total Impact
                        </div>
                        <h2 className="text-5xl md:text-7xl font-bold tracking-tight mb-4">
                            {Math.round(stats.saved_time_minutes / 60)}h {stats.saved_time_minutes % 60}m
                        </h2>
                        <p className="text-lg text-blue-100 max-w-lg leading-relaxed">
                            You've saved this much time by using VoiceBrain instead of typing. That's assuming you speak 3x faster than you type!
                        </p>
                    </div>
                    {/* Background decorations */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16" />
                    <div className="absolute bottom-0 left-0 w-48 h-48 bg-black/10 rounded-full blur-2xl -ml-10 -mb-10" />
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Subscription Widget */}
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col justify-between">
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="font-bold text-slate-500 dark:text-slate-400 text-sm uppercase tracking-wider">Plan Status</h3>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${stats.plan_name === 'premium' ? 'bg-purple-100 text-purple-600' :
                                        stats.plan_name === 'pro' ? 'bg-brand-blue/10 text-brand-blue' :
                                            'bg-slate-100 text-slate-500'
                                    }`}>
                                    {stats.plan_name}
                                </span>
                            </div>

                            <div className="mb-6">
                                <div className="flex justify-between text-sm mb-2 font-medium dark:text-slate-300">
                                    <span>Usage Reset</span>
                                    <span>{new Date(stats.subscription_renews_at).toLocaleDateString()}</span>
                                </div>
                                <div className="flex justify-between text-sm mb-2 font-medium dark:text-slate-300">
                                    <span>Balance</span>
                                    <span className="text-brand-blue">{stats.balance_days_remaining} Days Left</span>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-bold text-slate-400 uppercase">
                                    <span>Transcription Usage</span>
                                    <span>{stats.usage_minutes_this_month} / {stats.limit_minutes === Infinity ? '∞' : stats.limit_minutes}m</span>
                                </div>
                                <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full transition-all duration-1000 ${usagePercent > 90 ? 'bg-red-500' : 'bg-brand-blue'}`}
                                        style={{ width: `${usagePercent}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                        <Link to="/pricing" className="mt-8 w-full block text-center py-3 bg-slate-900 dark:bg-slate-700 text-white font-bold rounded-xl hover:opacity-90 transition-opacity">
                            Manage Subscription
                        </Link>
                    </div>

                    {/* Productivity Trend */}
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-sm lg:col-span-2">
                        <div className="flex items-center gap-2 mb-8">
                            <BarChart3 className="text-brand-blue" />
                            <h3 className="text-xl font-bold dark:text-white">Productivity Trend</h3>
                        </div>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={stats.productivity_trend}>
                                    <Tooltip
                                        cursor={{ fill: 'transparent' }}
                                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                                    />
                                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Integrations Pie */}
                    <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-sm">
                        <div className="flex items-center gap-2 mb-8">
                            <PieIcon className="text-purple-500" />
                            <h3 className="text-xl font-bold dark:text-white">Where It Goes</h3>
                        </div>
                        <div className="h-64 flex items-center justify-center">
                            {stats.integration_usage.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={stats.integration_usage}
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {stats.integration_usage.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="text-center text-slate-400">
                                    <p>No integrations used yet.</p>
                                </div>
                            )}
                        </div>
                        <div className="flex flex-wrap justify-center gap-4 mt-6">
                            {stats.integration_usage.map((entry, index) => (
                                <div key={entry.name} className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                                    <span className="text-sm text-slate-500 capitalize">{entry.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Fun Insight or Achievement */}
                    <div className="bg-orange-50 dark:bg-orange-900/10 p-8 rounded-[32px] border border-orange-100 dark:border-orange-900/30 flex items-center justify-center md:col-span-2">
                        <div className="text-center">
                            <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center mx-auto mb-4 text-orange-500">
                                <Zap size={32} />
                            </div>
                            <h3 className="text-xl font-bold text-orange-900 dark:text-orange-100 mb-2">Voice Master</h3>
                            <p className="text-orange-700/80 dark:text-orange-300/80 max-w-sm mx-auto">
                                You've created {stats.total_notes} notes. Keep it up!
                                {stats.total_notes > 10 ? " You are becoming a prolific thinker." : " Start capturing more ideas to unlock your potential."}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
