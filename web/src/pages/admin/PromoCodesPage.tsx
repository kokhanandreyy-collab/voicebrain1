import { useState, useEffect } from 'react';
import api from '../../api';
import { Tag, Trash2, Plus, Copy, Check } from 'lucide-react';

interface PromoCode {
    id: string;
    code: string;
    discount_percent: number;
    usage_limit: number;
    times_used: number;
    is_active: boolean;
    created_at: string;
}

export default function PromoCodesPage() {
    const [codes, setCodes] = useState<PromoCode[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);

    // Create Form
    const [newCode, setNewCode] = useState('');
    const [newDiscount, setNewDiscount] = useState(20);
    const [newLimit, setNewLimit] = useState(100);

    const [copiedId, setCopiedId] = useState<string | null>(null);

    useEffect(() => {
        fetchCodes();
    }, []);

    const fetchCodes = async () => {
        try {
            const { data } = await api.get('/admin/promocodes');
            setCodes(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/admin/promocodes', {
                code: newCode.toUpperCase(),
                discount_percent: newDiscount,
                usage_limit: newLimit
            });
            setIsCreating(false);
            setNewCode('');
            fetchCodes();
        } catch (e) {
            alert('Ошибка создания (возможно код уже существует)');
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Удалить этот промокод?')) return;
        try {
            await api.delete(`/admin/promocodes/${id}`);
            setCodes(codes.filter(c => c.id !== id));
        } catch (e) {
            alert('Ошибка удаления');
        }
    };

    const copyToClipboard = (code: string, id: string) => {
        navigator.clipboard.writeText(code);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold dark:text-white">Промокоды</h1>
                <button
                    onClick={() => setIsCreating(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-brand-blue hover:bg-blue-600 text-white rounded-xl font-bold transition-all shadow-lg shadow-blue-500/20"
                >
                    <Plus size={18} /> Создать код
                </button>
            </div>

            {isCreating && (
                <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 animate-in slide-in-from-top-4">
                    <form onSubmit={handleCreate} className="flex flex-col md:flex-row gap-4 items-end">
                        <div className="flex-1 w-full">
                            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Код</label>
                            <input
                                type="text"
                                value={newCode}
                                onChange={e => setNewCode(e.target.value.toUpperCase())}
                                placeholder="LETO2025"
                                className="w-full px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                                required
                            />
                        </div>
                        <div className="w-32">
                            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Скидка %</label>
                            <input
                                type="number"
                                value={newDiscount}
                                onChange={e => setNewDiscount(parseInt(e.target.value))}
                                className="w-full px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                                min="1" max="100"
                            />
                        </div>
                        <div className="w-32">
                            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Лимит</label>
                            <input
                                type="number"
                                value={newLimit}
                                onChange={e => setNewLimit(parseInt(e.target.value))}
                                className="w-full px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800"
                            />
                        </div>
                        <button type="submit" className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold rounded-lg hover:opacity-90">
                            Создать
                        </button>
                    </form>
                </div>
            )}

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 text-xs uppercase font-bold tracking-wider">
                        <tr>
                            <th className="p-4">Код</th>
                            <th className="p-4">Скидка</th>
                            <th className="p-4">Использовано</th>
                            <th className="p-4">Создан</th>
                            <th className="p-4 text-right">Действия</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {codes.map((code) => (
                            <tr key={code.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                <td className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-green-100 text-green-600 flex items-center justify-center font-bold">
                                            <Tag size={14} />
                                        </div>
                                        <button
                                            onClick={() => copyToClipboard(code.code, code.id)}
                                            className="font-mono font-bold text-slate-900 dark:text-white hover:text-brand-blue flex items-center gap-2 group"
                                        >
                                            {code.code}
                                            {copiedId === code.id ? <Check size={12} className="text-green-500" /> : <Copy size={12} className="opacity-0 group-hover:opacity-100 text-slate-400" />}
                                        </button>
                                    </div>
                                </td>
                                <td className="p-4 font-bold text-slate-700 dark:text-slate-300">
                                    {code.discount_percent}%
                                </td>
                                <td className="p-4 text-sm text-slate-600 dark:text-slate-400">
                                    <span className={code.times_used >= code.usage_limit ? 'text-red-500 font-bold' : ''}>
                                        {code.times_used}
                                    </span>
                                    <span className="text-slate-400"> / {code.usage_limit}</span>
                                </td>
                                <td className="p-4 text-sm text-slate-500">
                                    {new Date(code.created_at).toLocaleDateString("ru-RU")}
                                </td>
                                <td className="p-4 text-right">
                                    <button
                                        onClick={() => handleDelete(code.id)}
                                        className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {codes.length === 0 && !loading && (
                    <div className="p-8 text-center text-slate-500">Нет активных промокодов.</div>
                )}
            </div>
        </div>
    );
}
