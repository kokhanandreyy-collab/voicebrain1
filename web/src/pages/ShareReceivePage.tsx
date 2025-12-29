import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { savePendingUpload } from '../lib/storage';

export default function ShareReceivePage() {
    const navigate = useNavigate();
    const [status, setStatus] = useState("Processing shared file...");

    useEffect(() => {
        const processShare = async () => {
            try {
                // 1. Open 'share-target' cache created by SW
                const cache = await caches.open('share-target');
                const response = await cache.match('/shared-file');

                if (response) {
                    const blob = await response.blob();

                    // 2. Save to Pending Uploads (IndexedDB)
                    await savePendingUpload(blob);

                    // 3. Cleanup Cache
                    await cache.delete('/shared-file');

                    // 4. Redirect to Dashboard (which auto-syncs)
                    setStatus("Redirecting to dashboard...");
                    setTimeout(() => {
                        navigate('/dashboard');
                    }, 500);
                } else {
                    // Fallback if accessed directly or text share
                    // For now MVP only handles file via SW cache interception
                    setStatus("No shared file found. Redirecting...");
                    setTimeout(() => {
                        navigate('/dashboard');
                    }, 1500);
                }
            } catch (error) {
                console.error("Share processing failed:", error);
                setStatus("Error processing share.");
                setTimeout(() => {
                    navigate('/dashboard');
                }, 2000);
            }
        };

        processShare();
    }, [navigate]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="text-center space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-brand-blue mx-auto" />
                <h2 className="text-xl font-semibold text-slate-800">{status}</h2>
                <p className="text-slate-500">Please wait while we prepare your upload.</p>
            </div>
        </div>
    );
}
