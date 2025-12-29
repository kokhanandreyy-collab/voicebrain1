import React, { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import {
    Settings,
    CreditCard,
    LayoutDashboard,
    Mic,
    Users,
    Book,
    Search,
    FileText,
    Calendar,
    ArrowRight
} from 'lucide-react';
import api from '../api';
import { Note } from '../types';

export function GlobalSearch() {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [notes, setNotes] = useState<Note[]>([]);
    const navigate = useNavigate();

    // Toggle on CMD+K
    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((open) => !open);
            }
        };

        document.addEventListener('keydown', down);
        return () => document.removeEventListener('keydown', down);
    }, []);

    // Search existing notes when user types
    useEffect(() => {
        if (search.length > 2) {
            const fetchResults = async () => {
                try {
                    const { data } = await api.get(`/notes?q=${search}`);
                    setNotes(data.notes || []);
                } catch (err) {
                    console.error("Search failed", err);
                }
            };
            fetchResults();
        } else {
            setNotes([]);
        }
    }, [search]);

    const runCommand = (command: () => void) => {
        setOpen(false);
        command();
    };

    if (!open) return null;

    return (
        <Command.Dialog
            open={open}
            onOpenChange={setOpen}
            label="Global Command Palette"
            className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh] bg-slate-900/60 dark:bg-black/70 backdrop-blur-sm p-4"
        >
            <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="flex items-center border-b border-slate-100 dark:border-slate-800 px-4">
                    <Search className="text-slate-400 dark:text-slate-500 mr-3" size={18} />
                    <Command.Input
                        autoFocus
                        placeholder="Search for notes, actions, or pages..."
                        className="w-full h-14 bg-transparent border-none outline-none text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                        onValueChange={setSearch}
                    />
                </div>

                <Command.List className="max-h-[300px] overflow-y-auto p-2 scrollbar-hide">
                    <Command.Empty className="py-6 text-center text-sm text-slate-500 dark:text-slate-400 italic">
                        No results found for "{search}"
                    </Command.Empty>

                    <Command.Group heading="Navigation" className=" px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                        <Item shortcut="⌘ D" onSelect={() => runCommand(() => navigate('/dashboard'))}>
                            <LayoutDashboard className="mr-3" size={16} /> Dashboard <ArrowRight size={12} className="ml-auto opacity-0 group-aria-selected:opacity-100 transition-opacity" />
                        </Item>
                        <Item shortcut="⌘ P" onSelect={() => runCommand(() => navigate('/pricing'))}>
                            <CreditCard className="mr-3" size={16} /> Pricing <ArrowRight size={12} className="ml-auto opacity-0 group-aria-selected:opacity-100 transition-opacity" />
                        </Item>
                        <Item shortcut="⌘ S" onSelect={() => runCommand(() => navigate('/settings'))}>
                            <Settings className="mr-3" size={16} /> Settings <ArrowRight size={12} className="ml-auto opacity-0 group-aria-selected:opacity-100 transition-opacity" />
                        </Item>
                    </Command.Group>

                    <Command.Group heading="Quick Actions" className="mt-2 px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                        <Item onSelect={() => runCommand(() => window.dispatchEvent(new CustomEvent('start-recording')))}>
                            <Mic className="mr-3 text-brand-blue" size={16} /> Record New Note
                        </Item>
                        <Item onSelect={() => runCommand(() => console.log("Meeting Mode"))}>
                            <Users className="mr-3 text-purple-500" size={16} /> Switch to Meeting Mode
                        </Item>
                        <Item onSelect={() => runCommand(() => console.log("Journal Mode"))}>
                            <Book className="mr-3 text-emerald-500" size={16} /> Switch to Journal Mode
                        </Item>
                    </Command.Group>

                    {notes.length > 0 && (
                        <Command.Group heading="Recent Notes" className="mt-2 px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                            {notes.map(note => (
                                <Item key={note.id} onSelect={() => runCommand(() => navigate(`/dashboard?id=${note.id}`))}>
                                    <div className="flex items-center justify-between w-full">
                                        <div className="flex items-center">
                                            <FileText className="mr-3 text-slate-400 dark:text-slate-500" size={16} />
                                            <span className="truncate max-w-[200px] text-slate-800 dark:text-slate-200">{note.title || "Untitled Note"}</span>
                                        </div>
                                        <span className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
                                            <Calendar size={10} /> {new Date(note.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                </Item>
                            ))}
                        </Command.Group>
                    )}
                </Command.List>

                <div className="flex items-center justify-between border-t border-slate-50 dark:border-slate-800 p-3 bg-slate-50/50 dark:bg-slate-950/50">
                    <div className="flex items-center gap-4 text-[10px] text-slate-400 dark:text-slate-500 font-medium">
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-slate-500 dark:text-slate-400">↵</span> Select</span>
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-slate-500 dark:text-slate-400">↑↓</span> Navigate</span>
                        <span className="flex items-center gap-1"><span className="px-1.5 py-0.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-slate-500 dark:text-slate-400">esc</span> Close</span>
                    </div>
                </div>
            </div>
        </Command.Dialog>
    );
}

function Item({ children, shortcut, onSelect }: { children: React.ReactNode, shortcut?: string, onSelect: () => void }) {
    return (
        <Command.Item
            onSelect={onSelect}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer aria-selected:bg-blue-50 dark:aria-selected:bg-blue-900/20 aria-selected:text-brand-blue dark:aria-selected:text-blue-400 group transition-all text-slate-700 dark:text-slate-300"
        >
            <div className="flex items-center text-sm font-medium">
                {children}
            </div>
            {shortcut && (
                <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 group-aria-selected:text-blue-400 dark:group-aria-selected:text-blue-300">
                    {shortcut}
                </span>
            )}
        </Command.Item>
    );
}
