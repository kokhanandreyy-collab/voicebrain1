import { useState, useEffect } from 'react';
import api from '../../api';
import { Save, Check } from 'lucide-react';

interface Plan {
    id: string;
    name: string;
    price_monthly_usd: number;
    price_yearly_usd: number;
    price_monthly_rub: number;
    price_yearly_rub: number;
    features: {
        monthly_transcription_seconds: number;
        storage_months: number;
        allowed_integrations: string[];
    };
    is_active: boolean;
}

export default function PlansPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<string | null>(null);

    useEffect(() => {
        fetchPlans();
    }, []);

    const fetchPlans = async () => {
        try {
            const { data } = await api.get('/admin/plans');
            // Sort to ensure Free -> Pro -> Premium order if names match, else created_at
            const order = ['free', 'pro', 'premium'];
            const sorted = data.sort((a: Plan, b: Plan) => order.indexOf(a.name) - order.indexOf(b.name));
            setPlans(sorted);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (plan: Plan) => {
        setSavingId(plan.id);
        try {
            await api.put(`/admin/plans/${plan.id}`, {
                price_monthly_usd: plan.price_monthly_usd,
                price_yearly_usd: plan.price_yearly_usd,
                price_monthly_rub: plan.price_monthly_rub,
                price_yearly_rub: plan.price_yearly_rub,
                features: plan.features,
                is_active: plan.is_active
            });
            // Show checkmark or toast?
        } catch (e) {
            alert('Failed to update plan');
        } finally {
            setTimeout(() => setSavingId(null), 1000);
        }
    };

    const updateField = (index: number, field: string, value: any) => {
        const newPlans = [...plans];
        // @ts-ignore
        newPlans[index][field] = value;
        setPlans(newPlans);
    };

    const updateFeature = (index: number, feature: string, value: any) => {
        const newPlans = [...plans];
        // @ts-ignore
        newPlans[index].features[feature] = value;
        setPlans(newPlans);
    };

    if (loading) return <div>Загрузка тарифов...</div>;

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold dark:text-white">Тарифные планы</h1>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {plans.map((plan, idx) => (
                    <div key={plan.id} className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="font-bold text-lg uppercase tracking-wide text-slate-900 dark:text-white">{plan.name}</h3>
                                {plan.is_active ?
                                    <span className="text-[10px] bg-green-100 text-green-700 px-2 py-1 rounded-full font-bold">АКТИВЕН</span> :
                                    <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-1 rounded-full font-bold">НЕАКТИВЕН</span>
                                }
                            </div>
                        </div>

                        <div className="p-6 space-y-6 flex-1">
                            {/* Limits */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Лимиты</h4>
                                <div className="space-y-3">
                                    <div>
                                        <label className="block text-xs font-medium text-slate-500 mb-1">Минут в месяц</label>
                                        <input
                                            type="number"
                                            value={Math.round(plan.features.monthly_transcription_seconds / 60)}
                                            onChange={(e) => updateFeature(idx, 'monthly_transcription_seconds', parseInt(e.target.value) * 60)}
                                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-slate-500 mb-1">Хранение (Месяцев)</label>
                                        <input
                                            type="number"
                                            value={plan.features.storage_months}
                                            onChange={(e) => updateFeature(idx, 'storage_months', parseInt(e.target.value))}
                                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Integrations */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Доступные интеграции</h4>
                                <div className="space-y-2">
                                    {['notion', 'google_calendar', 'zapier'].map(integration => (
                                        <label key={integration} className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={plan.features.allowed_integrations.includes(integration)}
                                                onChange={(e) => {
                                                    const current = plan.features.allowed_integrations;
                                                    let next = [];
                                                    if (e.target.checked) next = [...current, integration];
                                                    else next = current.filter(i => i !== integration);
                                                    updateFeature(idx, 'allowed_integrations', next);
                                                }}
                                                className="rounded text-brand-blue focus:ring-brand-blue"
                                            />
                                            <span className="text-sm dark:text-slate-300 capitalize">{integration.replace('_', ' ')}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Pricing */}
                            <div>
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Prices (Multi-Currency)</h4>
                                <div className="space-y-4">
                                    {/* USD Section */}
                                    <div className="bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-lg border border-blue-100 dark:border-blue-800">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-lg">🇺🇸</span>
                                            <span className="text-sm font-bold text-blue-900 dark:text-blue-100">USD Pricing</span>
                                        </div>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label className="block text-xs font-medium text-slate-500 mb-1">Monthly ($)</label>
                                                <input
                                                    type="number"
                                                    step="0.01"
                                                    value={plan.price_monthly_usd}
                                                    onChange={(e) => updateField(idx, 'price_monthly_usd', parseFloat(e.target.value))}
                                                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-slate-500 mb-1">Yearly ($)</label>
                                                <input
                                                    type="number"
                                                    step="0.01"
                                                    value={plan.price_yearly_usd}
                                                    onChange={(e) => updateField(idx, 'price_yearly_usd', parseFloat(e.target.value))}
                                                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* RUB Section */}
                                    <div className="bg-red-50/50 dark:bg-red-900/10 p-3 rounded-lg border border-red-100 dark:border-red-800">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-lg">🇷🇺</span>
                                            <span className="text-sm font-bold text-red-900 dark:text-red-100">RUB Pricing</span>
                                        </div>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <label className="block text-xs font-medium text-slate-500 mb-1">Monthly (₽)</label>
                                                <input
                                                    type="number"
                                                    step="1"
                                                    value={plan.price_monthly_rub}
                                                    onChange={(e) => updateField(idx, 'price_monthly_rub', parseFloat(e.target.value))}
                                                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-slate-500 mb-1">Yearly (₽)</label>
                                                <input
                                                    type="number"
                                                    step="1"
                                                    value={plan.price_yearly_rub}
                                                    onChange={(e) => updateField(idx, 'price_yearly_rub', parseFloat(e.target.value))}
                                                    className="w-full px-3 py-2 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                            <button
                                onClick={() => handleUpdate(plan)}
                                disabled={savingId === plan.id}
                                className="w-full py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                            >
                                {savingId === plan.id ? <Check size={18} /> : <Save size={18} />}
                                {savingId === plan.id ? 'Сохранено' : 'Сохранить изменения'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
