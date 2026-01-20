import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, Play, FolderOpen, 
  Cpu, Activity, Zap, 
  Sun, Moon, CheckSquare, Square,
  CheckCircle2, XCircle, Loader2,
  PieChart, DownloadCloud, RefreshCw,
  Plus, X, Save, RotateCcw, SlidersHorizontal,
  Trash2, Edit3, MoreHorizontal,
  Laptop
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- 组件：Toast 通知 ---
const Toast = ({ message, type = 'info', onClose }: any) => {
    useEffect(() => {
        const timer = setTimeout(onClose, 3000);
        return () => clearTimeout(timer);
    }, []);

    const bgClass = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-red-600' : 'bg-indigo-600');

    return (
        <div className={`fixed bottom-6 right-6 ${bgClass} text-white px-4 py-3 rounded-lg shadow-xl flex items-center gap-3 text-sm font-medium z-50 animate-[slideIn_0.3s_ease-out]`}>
            {type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <Activity className="w-5 h-5" />}
            {message}
        </div>
    );
};

// --- 组件：更新弹窗 ---
const UpdateModal = ({ isOpen, onClose, updateInfo }: any) => {
    if (!isOpen || !updateInfo) return null;

    const handleUpdate = () => {
        if (window.electron) {
            window.electron.ipcRenderer.invoke('shell:openExternal', updateInfo.url);
        } else {
            window.open(updateInfo.url, '_blank');
        }
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
            <div className="bg-slate-900 rounded-xl shadow-2xl border border-cyan-500/30 max-w-md w-full mx-4 overflow-hidden animate-[fadeIn_0.2s_ease-out]" onClick={e => e.stopPropagation()}>
                <div className="p-6 border-b border-slate-800 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 animate-pulse">
                        <DownloadCloud className="w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white">New Model Available</h3>
                        <p className="text-xs text-cyan-400 font-mono">Hugging Face Hub</p>
                    </div>
                </div>
                <div className="p-6 space-y-4">
                    <p className="text-slate-300 text-sm leading-relaxed">
                        A newer version of the <span className="font-bold text-white">DistilBERT</span> model has been detected.
                    </p>
                    <div className="bg-black/40 rounded-lg p-4 border border-slate-800 font-mono text-xs space-y-2">
                        <div className="flex justify-between">
                            <span className="text-slate-500">Current Version:</span>
                            <span className="text-slate-300">{updateInfo.current || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-500">Latest Version:</span>
                            <span className="text-emerald-400 font-bold">{updateInfo.latest}</span>
                        </div>
                    </div>
                </div>
                <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-end gap-3">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                        Skip
                    </button>
                    <button onClick={handleUpdate} className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-lg shadow-cyan-900/20 transition-all">
                        Download Update
                    </button>
                </div>
            </div>
        </div>
    );
};

// --- 霓虹按钮组件 ---
const NeonButton = ({ onClick, children, variant = 'primary', disabled, icon: Icon, isDark }: any) => {
  const baseStyle = "relative overflow-hidden group px-6 py-3 rounded-xl font-bold uppercase tracking-wider text-sm transition-all duration-300 flex items-center gap-2 shadow-lg";
  
  const themes: any = {
    dark: {
      primary: "bg-cyan-500/10 text-cyan-400 border border-cyan-500/50 hover:bg-cyan-500/20 hover:border-cyan-400 hover:shadow-cyan-500/40",
      ghost: "bg-slate-800/40 text-slate-400 border border-transparent hover:bg-slate-700/50 hover:text-white"
    },
    light: {
      primary: "bg-blue-600 text-white border border-blue-700 hover:bg-blue-700 hover:shadow-blue-500/30",
      ghost: "bg-slate-200 text-slate-600 border border-transparent hover:bg-slate-300 hover:text-slate-900"
    }
  };

  const currentTheme = isDark ? themes.dark : themes.light;
  const style = currentTheme[variant] || currentTheme.primary;

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyle} ${style} ${disabled ? 'opacity-50 cursor-not-allowed grayscale' : ''}`}
    >
      {Icon && <Icon className="w-4 h-4" />}
      {children}
      {isDark && <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />}
    </motion.button>
  );
};

// --- 玻璃态卡片组件 ---
const GlassCard = ({ children, title, className = "", isDark }: any) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`
      backdrop-blur-xl border p-6 rounded-2xl shadow-2xl relative overflow-hidden transition-colors duration-500
      ${isDark 
        ? 'bg-slate-900/60 border-slate-700/50 shadow-black/50' 
        : 'bg-white/80 border-slate-200 shadow-slate-200/50'
      }
      ${className}
    `}
  >
    <div className={`absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent ${isDark ? 'via-slate-500/50' : 'via-slate-300/80'} to-transparent`} />
    {title && (
      <h3 className={`text-xs font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
        {title}
      </h3>
    )}
    {children}
  </motion.div>
);

// --- 复选框组件 ---
const Toggle = ({ label, checked, onChange, isDark }: any) => (
  <div 
    onClick={() => onChange(!checked)}
    className={`flex items-center gap-2 cursor-pointer select-none transition-colors ${isDark ? 'hover:text-cyan-400 text-slate-300' : 'hover:text-blue-600 text-slate-600'}`}
  >
    {checked ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
    <span className="text-sm font-medium">{label}</span>
  </div>
);

// --- 目录模式切换组件 ---
const ModeSwitcher = ({ isRecursive, onChange, isDark }: any) => (
  <div className={`flex p-1 rounded-lg border mb-6 ${isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-100 border-slate-200'}`}>
    <button
      onClick={() => onChange(false)}
      className={`flex-1 py-2 rounded-md text-xs font-bold uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2
        ${!isRecursive 
          ? (isDark ? 'bg-slate-800 text-cyan-400 shadow-lg shadow-black/50' : 'bg-white text-blue-600 shadow-sm') 
          : 'text-slate-500 hover:text-slate-400'
        }`}
    >
      <FolderOpen className="w-4 h-4" />
      Single Folder
    </button>
    <button
      onClick={() => onChange(true)}
      className={`flex-1 py-2 rounded-md text-xs font-bold uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2
        ${isRecursive 
          ? (isDark ? 'bg-slate-800 text-purple-400 shadow-lg shadow-black/50' : 'bg-white text-purple-600 shadow-sm') 
          : 'text-slate-500 hover:text-slate-400'
        }`}
    >
      <RefreshCw className="w-4 h-4" />
      Batch Recursive
    </button>
  </div>
);


// --- 组件：语义规则编辑器 ---
// 定义接口，确保类型安全
interface SemanticConfig {
    positive: string[];
    negative: string[];
}

interface SemanticRuleEditorProps {
    isDark: boolean;
    initialConfig: SemanticConfig; // 从父组件传下来的初始数据
    onSave: (config: SemanticConfig) => Promise<void>; // 保存回调，返回 Promise 以处理 loading 状态
}

interface RuleListGroupProps {
    title: string;
    type: 'positive' | 'negative';
    items: string[];
    isDark: boolean;
    onAdd: () => void;
    onEdit: (index: number) => void;
    onDelete: (index: number) => void;
}


const RuleListGroup: React.FC<RuleListGroupProps> = ({ 
    title, type, items, isDark, onAdd, onEdit, onDelete 
}) => {
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 点击空白处取消选择
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setSelectedIndex(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const isPos = type === 'positive';
    //const themeColor = isPos ? 'emerald' : 'rose';
    const borderColor = isPos ? 'border-emerald-500/30' : 'border-rose-500/30';
    //const bgColor = isPos ? 'bg-emerald-500/10' : 'bg-rose-500/10';
    const selectedBg = isPos ? 'bg-emerald-500' : 'bg-rose-500';


    return (
        // 🔥 [修改 3] 将 Ref 绑定到最外层的 div
        <div 
            ref={containerRef} 
            className={`flex-1 flex flex-col h-full rounded-xl border backdrop-blur-md overflow-hidden transition-colors ${isDark ? `bg-slate-900/40 ${borderColor}` : `bg-white/60 ${borderColor}`}`}
        >
            {/* Header */}
            <div className={`px-4 py-3 border-b flex items-center gap-2 font-bold ${isDark ? 'border-slate-700' : 'border-slate-200'} ${isPos ? 'text-emerald-500' : 'text-rose-500'}`}>
                {isPos ? <CheckCircle2 className="w-5 h-5"/> : <XCircle className="w-5 h-5"/>}
                {title}
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                    {items.length}
                </span>
            </div>

            {/* List Box (Windows Style) */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                {items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400 opacity-50 select-none">
                        <MoreHorizontal className="w-8 h-8 mb-2"/>
                        <span className="text-xs">No rules defined</span>
                    </div>
                ) : (
                    items.map((item, i) => {
                        const isSelected = selectedIndex === i;
                        
                        return (
                            <div 
                                key={i}
                                onClick={() => setSelectedIndex(i)}
                                onDoubleClick={() => onEdit(i)}
                                className={`
                                    px-3 py-2 text-sm rounded cursor-default select-none 
                                    transition-all duration-200 ease-in-out
                                    border border-transparent
                                    ${isSelected 
                                        ? `${selectedBg} text-white shadow-md border-white/10 scale-[1.02] z-10 relative whitespace-normal break-words` // 🔥 选中：自动换行，稍微放大，提升层级
                                        : (isDark ? 'text-slate-300 hover:bg-white/5 truncate' : 'text-slate-700 hover:bg-slate-100 truncate') // 🧊 未选中：截断
                                    }
                                `}
                                title={!isSelected ? item : undefined} // 只有没展开时才需要 Tooltip，展开了就不需要了
                            >
                                {item}
                            </div>
                        );
                    })
                )}
            </div>

            {/* Toolbar (Windows Style) */}
            <div className={`p-2 border-t flex gap-2 ${isDark ? 'border-slate-700 bg-slate-900/50' : 'border-slate-200 bg-slate-50/50'}`}>
                <button 
                    onClick={onAdd}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs font-medium border transition-all active:scale-95
                        ${isDark 
                            ? 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700' 
                            : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                        }`}
                >
                    <Plus className="w-3.5 h-3.5"/> New
                </button>
                
                <button 
                    onClick={(e) => {
                        e.stopPropagation(); // 防止冒泡
                        if (selectedIndex !== null) onEdit(selectedIndex);
                    }}
                    disabled={selectedIndex === null}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs font-medium border transition-all active:scale-95
                        ${selectedIndex === null
                            ? 'opacity-50 cursor-not-allowed grayscale'
                            : (isDark ? 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50')
                        }`}
                >
                    <Edit3 className="w-3.5 h-3.5"/> Edit
                </button>

                <button 
                    onClick={(e) => {
                        e.stopPropagation(); // 防止冒泡
                        if (selectedIndex !== null) 
                          onDelete(selectedIndex); 
                          setSelectedIndex(null); // 删除后，重置选中状态
                    }}
                    disabled={selectedIndex === null}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs font-medium border transition-all active:scale-95
                        ${selectedIndex === null
                            ? 'opacity-50 cursor-not-allowed grayscale'
                            : (isDark ? 'bg-slate-800 border-rose-900/50 text-rose-400 hover:bg-rose-900/20' : 'bg-white border-rose-200 text-rose-600 hover:bg-rose-50')
                        }`}
                >
                    <Trash2 className="w-3.5 h-3.5"/> Delete
                </button>
            </div>
        </div>
    );
};

// === 模态框：用于输入/编辑文本 ===
const EditModal = ({ isOpen, title, initialValue, onConfirm, onCancel, isDark }: any) => {
    const [value, setValue] = useState(initialValue);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (isOpen) {
            setValue(initialValue);
            setTimeout(() => inputRef.current?.focus(), 50); // Auto focus
        }
    }, [isOpen, initialValue]);

    if (!isOpen) return null;

    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-8">
            <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`w-full max-w-lg rounded-xl shadow-2xl border p-6 ${isDark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}
            >
                <h3 className={`font-bold text-lg mb-4 ${isDark ? 'text-white' : 'text-slate-800'}`}>{title}</h3>
                <textarea
                    ref={inputRef}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            if(value.trim()) onConfirm(value);
                        }
                    }}
                    spellCheck={true} 
                    lang="en-US" // 指定语言

                    className={`w-full h-32 p-3 rounded-lg border text-sm focus:ring-2 outline-none resize-none mb-6 ${
                        isDark 
                            ? 'bg-slate-950 border-slate-700 text-slate-200 focus:ring-indigo-500/50' 
                            : 'bg-slate-50 border-slate-300 text-slate-700 focus:ring-indigo-500/50'
                    }`}
                    placeholder="Enter semantic rule text here..."
                />
                <div className="flex justify-end gap-3">
                    <button 
                        onClick={onCancel}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800'}`}
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={() => value.trim() && onConfirm(value)}
                        disabled={!value.trim()}
                        className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Confirm
                    </button>
                </div>
            </motion.div>
        </div>
    );
};


// === 主组件 ===
export const SemanticRuleEditor: React.FC<SemanticRuleEditorProps> = ({ isDark, initialConfig, onSave }) => {
    // 本地状态：用于管理用户正在编辑但还没保存的内容
    const [positiveTags, setPositiveTags] = useState<string[]>([]);
    const [negativeTags, setNegativeTags] = useState<string[]>([]);
    const [isSaving, setIsSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false); // 标记是否有未保存的修改
    const [waitingConfirm, setWaitingConfirm] = useState(false);   

    // 模态框状态
    const [modal, setModal] = useState<{
        isOpen: boolean;
        type: 'positive' | 'negative' | null;
        mode: 'add' | 'edit';
        index: number | null; // 仅 edit 模式使用
        initialText: string;
    }>({ isOpen: false, type: null, mode: 'add', index: null, initialText: '' });

    // 初始化数据
    const configStr = JSON.stringify(initialConfig);
    useEffect(() => {
        // 只有当后端传来的配置真正改变时，才重置本地状态
        setPositiveTags(initialConfig.positive || []);
        setNegativeTags(initialConfig.negative || []);
        setIsDirty(false);
    }, [configStr]); // 依赖字符串，而不是对象引用


    // === CRUD 操作 ===
    const openAddModal = (type: 'positive' | 'negative') => {
        setModal({ isOpen: true, type, mode: 'add', index: null, initialText: '' });
    };

    const openEditModal = (type: 'positive' | 'negative', index: number) => {
        const text = type === 'positive' ? positiveTags[index] : negativeTags[index];
        setModal({ isOpen: true, type, mode: 'edit', index, initialText: text });
    };

    const handleDelete = (type: 'positive' | 'negative', index: number) => {
        if (type === 'positive') {
            setPositiveTags(prev => prev.filter((_, i) => i !== index));
        } else {
            setNegativeTags(prev => prev.filter((_, i) => i !== index));
        }
        setIsDirty(true);
    };

    const handleModalConfirm = (text: string) => {
        const { type, mode, index } = modal;
        if (!type) return;

        const cleanText = text.trim();
        if (!cleanText) return;

        // === 1. 查重逻辑 (Duplicate Check) ===
        const targetText = cleanText.toLowerCase();

        // 辅助函数：检查数组里是否有这个词 (排除掉正在编辑的那一项自己)
        const checkDuplicate = (list: string[], ignoreIndex: number | null) => {
            return list.some((item, i) => {
                if (ignoreIndex !== null && i === ignoreIndex) return false; // 编辑模式下，不和自己比
                return item.toLowerCase() === targetText;
            });
        };

        // A. 检查当前列表是否重复
        const currentList = type === 'positive' ? positiveTags : negativeTags;
        if (checkDuplicate(currentList, mode === 'edit' ? index : null)) {
            // 使用简单的原生 alert，或者您可以用 setToast 如果您把 toast 传进来的话
            // 为了简单直接，这里演示用 alert，建议您换成更好的 UI 反馈
            alert("⚠️ Duplicate Rule detected!\nThis rule already exists in the current list.");
            return; // ⛔ 阻止保存，保持弹窗打开，让用户修改
        }

        // B. 检查对面列表是否冲突 (Conflict Check)
        // 如果一个词既在 Positive 又在 Negative，AI 会疯掉
        const otherList = type === 'positive' ? negativeTags : positiveTags;
        if (checkDuplicate(otherList, null)) {
            const otherType = type === 'positive' ? 'Exclusion (Negative)' : 'Inclusion (Positive)';
            alert(`⚠️ Logic Conflict detected!\nThis rule already exists in the ${otherType} list.\nA rule cannot be both included and excluded.`);
            return; // 阻止保存
        }

        // === 2. 正常保存逻辑 (保持不变) ===
        const setTags = type === 'positive' ? setPositiveTags : setNegativeTags;

        if (mode === 'add') {
            setTags(prev => [...prev, cleanText]);
        } else if (mode === 'edit' && index !== null) {
            setTags(prev => {
                const copy = [...prev];
                copy[index] = cleanText;
                return copy;
            });
        }

        setIsDirty(true);
        setModal({ ...modal, isOpen: false });
    };

    // === 全局操作 ===
    const handleSaveClick = async () => {
        setIsSaving(true);
        await onSave({ positive: positiveTags, negative: negativeTags });
        setIsSaving(false);
        setIsDirty(false);
    };

    const handleDiscard = () => {
        if (waitingConfirm) {
            setPositiveTags(initialConfig.positive || []);
            setNegativeTags(initialConfig.negative || []);
            setIsDirty(false);
            setWaitingConfirm(false);
        } else {
            setWaitingConfirm(true);
            setTimeout(() => setWaitingConfirm(false), 3000);
        }
    };


    // --- 渲染部分 ---
    return (
        <div className="flex flex-col h-full overflow-hidden relative">
            {/* 列表区域 (左右分栏) */}
            <div className="flex-1 flex gap-6 min-h-0 pb-20 px-1">
                <RuleListGroup 
                    title="Inclusion Rules (Positive)" 
                    type="positive"
                    items={positiveTags}
                    isDark={isDark}
                    onAdd={() => openAddModal('positive')}
                    onEdit={(idx) => openEditModal('positive', idx)}
                    onDelete={(idx) => handleDelete('positive', idx)}
                />
                
                <RuleListGroup 
                    title="Exclusion Rules (Negative)" 
                    type="negative"
                    items={negativeTags}
                    isDark={isDark}
                    onAdd={() => openAddModal('negative')}
                    onEdit={(idx) => openEditModal('negative', idx)}
                    onDelete={(idx) => handleDelete('negative', idx)}
                />
            </div>

            {/* 弹窗编辑器 */}
            <EditModal 
                isOpen={modal.isOpen}
                title={modal.mode === 'add' ? `Add ${modal.type === 'positive' ? 'Inclusion' : 'Exclusion'} Rule` : 'Edit Rule'}
                initialValue={modal.initialText}
                isDark={isDark}
                onConfirm={handleModalConfirm}
                onCancel={() => setModal({ ...modal, isOpen: false })}
            />

            {/* 底部浮动按钮 */}
            <div className="absolute bottom-6 right-6 flex gap-3 z-10">
                 <motion.button
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ 
                        opacity: isDirty ? 1 : 0, 
                        scale: isDirty ? (waitingConfirm ? 1.05 : 1) : 0.9,
                    }}
                    onClick={handleDiscard}
                    className={`px-4 py-3 rounded-full shadow-lg font-bold flex items-center gap-2 backdrop-blur-sm border transition-all 
                        ${isDirty ? 'pointer-events-auto cursor-pointer' : 'pointer-events-none cursor-default'} 
                        ${waitingConfirm 
                            ? 'bg-rose-500 text-white border-rose-600 animate-pulse' 
                            : (isDark ? 'bg-slate-800/80 border-slate-600 text-slate-300 hover:bg-slate-700' : 'bg-white/90 border-slate-200 text-slate-600 hover:bg-slate-50')
                        }`}
                >
                    {waitingConfirm ? <span className="text-sm">Click again to reset</span> : <><RotateCcw className="w-4 h-4"/> Discard</>}
                </motion.button>
                 
                 <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleSaveClick}
                    disabled={isSaving || !isDirty} 
                    className={`px-6 py-3 rounded-full shadow-xl flex items-center gap-2 font-bold transition-all
                        ${isDirty 
                            ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-indigo-500/30 cursor-pointer' 
                            : 'bg-slate-500/30 text-slate-400 border border-slate-500/10 cursor-not-allowed'
                        }`}
                >
                    {isSaving ? <Loader2 className="w-5 h-5 animate-spin"/> : <Save className="w-5 h-5"/>}
                    {isSaving ? "Saving..." : "Save Rules"}
                </motion.button>
            </div>
        </div>
    );
};

// === 硬件信息接口 ===
interface HardwareInfo {
  device: string; // 'cuda', 'mps', 'cpu'
  details: {
    type: string;
    vram: number; // 显存/内存 GB
    desc: string; // 显卡名称 e.g. "RTX 4060 Laptop"
  };
  active_model?: string;
}


// === 主应用组件 ===
export default function App() {
  const [isDark, setIsDark] = useState(true);
  const [logs, setLogs] = useState<any[]>([{ type: 'sys', msg: 'UI Controller initialized.' }]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const [modelStatus, setModelStatus] = useState<'checking' | 'ready' | 'error'>('checking');
  
  // 递归模式状态
  const [isRecursive, setIsRecursive] = useState(false); 

  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [autoOutput, setAutoOutput] = useState(true); 
  const [autoOpen, setAutoOpen] = useState(false);    
  
  const [updateInfo, setUpdateInfo] = useState(null);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  
  // 状态：控制当前显示 Dashboard 还是 Review Lab
  const [view, setView] = useState<'dashboard' | 'rules' | 'review'>('dashboard'); 
  
  // Toast 状态
  const [toast, setToast] = useState<{msg: string, type: string} | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const hasCheckedModel = useRef(false);
  
  const [highlightRun, setHighlightRun] = useState(false);

  // 统一管理语义配置数据
  const [semanticConfig, setSemanticConfig] = useState({ positive: [], negative: [] });
  
  // 硬件信息状态
  const [sysInfo, setSysInfo] = useState<HardwareInfo | null>(null);

  // 组件加载时，主动向 Python 请求一次配置数据
  useEffect(() => {
    if (window.electron) {
        // 发送我们在 api.py 里写的 'get-semantic-config' 指令
        window.electron.ipcRenderer.send('run-python-command', { action: 'get-semantic-config' });
    }
  }, []);

  useEffect(() => { terminalEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  useEffect(() => {
    const savedInput = localStorage.getItem('inputPath');
    const savedAutoOut = localStorage.getItem('autoOutput');
    const savedAutoOpen = localStorage.getItem('autoOpen');
    const savedRecursive = localStorage.getItem('isRecursive');
    const savedTheme = localStorage.getItem('theme');

    if (savedInput) setInputPath(savedInput);
    if (savedAutoOut) setAutoOutput(savedAutoOut === 'true');
    if (savedAutoOpen) setAutoOpen(savedAutoOpen === 'true');
    if (savedRecursive) setIsRecursive(savedRecursive === 'true');
    if (savedTheme) setIsDark(savedTheme === 'dark');
  }, []);

  useEffect(() => { localStorage.setItem('inputPath', inputPath); }, [inputPath]);
  useEffect(() => { localStorage.setItem('autoOutput', String(autoOutput)); }, [autoOutput]);
  useEffect(() => { localStorage.setItem('autoOpen', String(autoOpen)); }, [autoOpen]);
  useEffect(() => { localStorage.setItem('isRecursive', String(isRecursive)); }, [isRecursive]);
  useEffect(() => { localStorage.setItem('theme', isDark ? 'dark' : 'light'); }, [isDark]);

  useEffect(() => {
    if (autoOutput && inputPath && inputPath !== "Wait for selection...") {
      const newOutput = inputPath + "\\Output"; 
      setOutputPath(newOutput);
    }
  }, [inputPath, autoOutput]);

  useEffect(() => {
    if (window.electron && !hasCheckedModel.current) {
      hasCheckedModel.current = true;
      setTimeout(() => {
        window.electron.ipcRenderer.send('run-python-command', { action: 'check-model' });
        addLog("Sent model check request...", "sys");
      }, 1000);
    }
  }, []);

  useEffect(() => {
    if (window.electron) {
      window.electron.ipcRenderer.on('auto-fill-task', (_: any, dirPath: any) => {
        setInputPath(dirPath);
        addLog(`Received task from Review Lab: ${dirPath}`, 'sys');
        
        // 触发按钮高亮动画
        setHighlightRun(true);
        setTimeout(() => setHighlightRun(false), 3000);
        
        // 收到任务后切回 Dashboard
        setView('dashboard');
        
        // 自动检查模型状态 (如果还没准备好)
        if (modelStatus !== 'ready') {
             window.electron.ipcRenderer.send('run-python-command', { action: 'check-model' });
        }
      });
    }
  }, [modelStatus]);


  // === IPC 监听 ===
  useEffect(() => {
    if (window.electron) {
      // 1. 防御性清理：先移除可能存在的旧监听器，防止重复
      window.electron.ipcRenderer.removeAllListeners('python-log');
      
      // 2. 绑定主监听函数
      window.electron.ipcRenderer.on('python-log', (_: any, data: any) => {
        
        // 调试用
        // console.log("📡 IPC数据:", data);

        // 拦截硬件信息
        if (data.type === 'system-info') {
            console.log("💻 收到硬件信息:", data.data);
            setSysInfo(data.data); // 更新 State，让卡片显示
            return; // 处理完直接返回，不打日志
        }

        // 拦截配置数据回传
        if (data.type === 'config-data') {
            console.log("收到配置数据:", data.data);
            setSemanticConfig(data.data || { positive: [], negative: [] });
            return;
        }

        // 拦截保存成功通知
        if (data.type === 'success' && data.msg === 'Semantic Rules Saved!') {
             setToast({ msg: "Rules saved successfully!", type: "success" });
        }

        // 检查更新消息
        if (data.type === 'update-available') {
            setCheckingUpdate(false);
            setUpdateInfo(data);
            setShowUpdateModal(true);
            return;
        }
        
        // 没有更新 (手动检查反馈)
        if (data.type === 'update-not-found') {
            setCheckingUpdate(false);
            setToast({ msg: "Model is up to date.", type: "success" });
            return;
        }

        // 普通日志显示
        addLog(data.msg, data.type || 'info');
        
        // 状态判断
        if (data.msg && data.msg.includes("Model Found")) {
          setModelStatus('ready');
        }
        if (data.msg && data.msg.includes("Model NOT FOUND")) {
          setModelStatus('error');
        }

        // 进度条
        if (data.progress) setProgress(data.progress);
        
        // 任务完成
        if (data.status === 'done') {
          setIsRunning(false);
          setToast({ msg: "Task Done! Check Review Lab.", type: "success" });
          if (autoOpen && data.resultPath) {
             addLog(`Auto-opening folder: ${data.resultPath}`, 'sys');
             window.electron.ipcRenderer.invoke('shell:openPath', data.resultPath);
          }
        }
      });

      // 触发硬件检测
      const timer = setTimeout(() => {
          window.electron.ipcRenderer.send('run-python-command', { action: 'get-system-info' });
      }, 1000);

      // 清理函数
      return () => {
          clearTimeout(timer);
          if (window.electron) window.electron.ipcRenderer.removeAllListeners('python-log');
      }
    }
  }, [autoOpen]); // 依赖项保持不变;

  const addLog = (msg: string, type = 'info') => {
    setLogs(prev => [...prev, { msg, type, ts: new Date().toLocaleTimeString('en-US', { hour12: false }) }]);
  };

  const handleStart = () => {
    if (!inputPath) {
      addLog("Please select source directory first.", "err");
      return;
    }
    if (modelStatus !== 'ready') {
      addLog("Cannot start: Model not ready.", "err");
      return;
    }

    setIsRunning(true);
    setProgress(0);
    addLog(`Sending start command... (Recursive: ${isRecursive})`, "sys");
    
    if (window.electron) {
      window.electron.ipcRenderer.send('run-python-command', { 
        action: 'start', 
        inputPath, 
        outputPath,
        recursive: isRecursive
      });
    } else {
      setTimeout(() => { addLog("Demo Mode: Backend not connected.", "err"); setIsRunning(false); }, 1000);
    }
  };

  const handleBrowse = async (type: string) => {
    if (window.electron) {
      if (type === 'out' && autoOutput) setAutoOutput(false); 
      const path = await window.electron.ipcRenderer.invoke('dialog:openDirectory');
      if (path) {
        if (type === 'in') setInputPath(path);
        else setOutputPath(path);
        addLog(`Path updated: ${path}`, "success");
      }
    }
  };

  const handleCheckUpdate = () => {
    setCheckingUpdate(true);
    if (window.electron) {
        window.electron.ipcRenderer.send('run-python-command', { action: 'check-update' });
    } else {
        setTimeout(() => { setCheckingUpdate(false); setToast({ msg: "Demo: Up to date", type: "success" }); }, 1000);
    }
  };


  const handleSaveRules = async (newConfig: {positive: string[], negative: string[]}) => {
      if (window.electron) {
          // 发送指令给 Python 保存
          window.electron.ipcRenderer.send('run-python-command', { 
              action: 'save-semantic-config',
              config: newConfig
          });
          
          // 乐观更新：立刻更新本地 UI，不用等后端返回
          setSemanticConfig(newConfig);
          await new Promise(resolve => setTimeout(resolve, 500)); // 模拟等待
      }
  };

  const renderStatusCard = () => {
    const statusConfig = {
      checking: { color: 'text-amber-400', bg: 'bg-amber-500', icon: Loader2, text: 'Checking Model...', animate: 'animate-spin' },
      ready:    { color: 'text-emerald-400', bg: 'bg-emerald-500', icon: CheckCircle2, text: 'DeBERTa Ready', animate: '' },
      error:    { color: 'text-rose-400', bg: 'bg-rose-500', icon: XCircle, text: 'Model Missing', animate: '' }
    };
    const current = statusConfig[modelStatus];
    const StatusIcon = current.icon;

    return (
      <div className={`rounded-xl p-4 border transition-all duration-500 ${isDark ? 'bg-slate-800/50 border-slate-700/50' : 'bg-white border-slate-200 shadow-sm'}`}>
        <div className="flex items-center justify-between mb-2">
          <div className={`text-[10px] font-bold uppercase tracking-widest ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>Core Engine</div>
          <div className={`w-2 h-2 rounded-full ${current.bg} ${modelStatus === 'ready' ? 'shadow-[0_0_8px_rgba(16,185,129,0.6)]' : ''} animate-pulse`} />
        </div>
        <div className={`flex items-center gap-2 ${current.color}`}>
          <StatusIcon className={`w-5 h-5 ${current.animate}`} />
          <span className="font-bold font-mono text-sm">{current.text}</span>
        </div>
        {modelStatus === 'error' && (
          <div className="mt-2 text-[10px] text-slate-500 leading-tight">
            Please place model in /news-body-classifier
          </div>
        )}
      </div>
    );
  };

//硬件卡片

const HardwareCard = ({ info, isDark }: { info: HardwareInfo | null, isDark: boolean }) => {
    
    // =========================================================
    // 🛑 状态 1: 加载中 (带文字提示的呼吸态)
    // =========================================================
    if (!info) {
        return (
            <div className={`rounded-xl border p-3 mb-3 animate-pulse select-none ${
                isDark 
                    ? 'bg-slate-900/40 border-slate-800' 
                    : 'bg-white/60 border-slate-200'
            }`}>
                {/* 顶部行：图标 + 状态文字 */}
                <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                        {/* 占位图标：用 Activity (心跳) 代表正在检测 */}
                        <div className={`w-5 h-5 rounded-md flex items-center justify-center ${
                            isDark ? 'bg-slate-800 text-slate-600' : 'bg-slate-200 text-slate-400'
                        }`}>
                            <Activity className="w-3 h-3" />
                        </div>
                        
                        {/* 文字提示 1: 标题 */}
                        <span className={`text-[10px] font-bold tracking-wider uppercase ${
                            isDark ? 'text-slate-600' : 'text-slate-400'
                        }`}>
                            CHECKING HARDWARE
                        </span>
                    </div>
                </div>
                
                {/* 底部行：详细描述占位 */}
                <div className={`text-[10px] font-medium leading-tight px-0.5 ${
                    isDark ? 'text-slate-700' : 'text-slate-400'
                }`}>
                    Please wait...
                </div>
            </div>
        );
    }

    // =========================================================
    // ✅ 状态 2: 加载完成 (显示真实数据)
    // =========================================================

    // 1. 智能清洗名称
    let displayName = info.details.desc
        .replace(/NVIDIA\s+NVIDIA/ig, 'NVIDIA')
        .replace(/NVIDIA\s+GeForce\s*/ig, '')
        .replace(/NVIDIA\s*/ig, '');
    
    if (!displayName.trim()) displayName = info.details.desc;

    // 2. 样式配置
    const config: any = {
        cuda: {
            container: isDark 
                ? "bg-emerald-900/20 border-emerald-500/20" 
                : "bg-emerald-50 border-emerald-100",
            iconBg: "bg-emerald-500 text-white",
            title: isDark ? "text-emerald-400" : "text-emerald-700",
            desc: isDark ? "text-emerald-100/70" : "text-emerald-900/70", 
            icon: <Zap className="w-3 h-3 fill-current" />,
            label: "CUDA ACCEL"
        },
        mps: {
            container: isDark 
                ? "bg-purple-900/20 border-purple-500/20" 
                : "bg-purple-50 border-purple-100",
            iconBg: "bg-purple-500 text-white",
            title: isDark ? "text-purple-400" : "text-purple-700",
            desc: isDark ? "text-purple-100/70" : "text-purple-900/70",
            icon: <Laptop className="w-3 h-3" />,
            label: "APPLE METAL"
        },
        cpu: {
            container: isDark 
                ? "bg-slate-800 border-slate-700" 
                : "bg-slate-100 border-slate-200",
            iconBg: isDark ? "bg-slate-600 text-slate-200" : "bg-slate-300 text-slate-600",
            title: isDark ? "text-slate-300" : "text-slate-600",
            desc: isDark ? "text-slate-400" : "text-slate-500",
            icon: <Cpu className="w-3 h-3" />,
            label: "CPU MODE"
        }
    };

    const current = config[info.device] || config.cpu;

    return (
        <div className={`rounded-xl border p-3 mb-3 transition-colors duration-500 ${current.container}`}>
            <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 rounded-md flex items-center justify-center shadow-sm ${current.iconBg}`}>
                        {current.icon}
                    </div>
                    <span className={`text-[10px] font-bold tracking-wider uppercase ${current.title}`}>
                        {current.label}
                    </span>
                </div>
                {info.details.vram > 0 && (
                    <span className={`text-[9px] font-mono px-1.5 rounded ${isDark ? 'bg-black/20 text-white/70' : 'bg-white text-slate-500 border border-slate-100'}`}>
                        {info.details.vram}G
                    </span>
                )}
            </div>
            <div className={`text-[10px] font-medium leading-tight px-0.5 ${current.desc}`}>
                {displayName}
            </div>
        </div>
    );
};


  return (
    <div className={`min-h-screen font-sans transition-colors duration-500 overflow-hidden relative selection:bg-cyan-500/30 ${isDark ? 'bg-[#0f172a] text-slate-200' : 'bg-slate-50 text-slate-800'}`}>
      
      <UpdateModal isOpen={showUpdateModal} onClose={() => setShowUpdateModal(false)} updateInfo={updateInfo} />
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}

      {isDark && (
        <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] animate-pulse-slow" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-600/20 rounded-full blur-[120px] animate-pulse-slow delay-1000" />
        </div>
      )}
      
      <div className="relative z-10 flex h-screen max-w-[1600px] mx-auto">
        {/* === 侧边栏 === */}
        <motion.div 
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className={`w-20 lg:w-64 border-r backdrop-blur-md flex flex-col justify-between py-8 transition-colors duration-500
            ${isDark ? 'border-slate-800/60 bg-slate-900/50' : 'border-slate-200 bg-white/50'}
          `}
        >
          <div className="px-6">
            <div className="flex items-center gap-3 mb-12">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${isDark ? 'bg-gradient-to-tr from-cyan-500 to-blue-600 shadow-cyan-500/20' : 'bg-gradient-to-tr from-blue-500 to-indigo-600 shadow-blue-500/20'}`}>
                <Cpu className="text-white w-6 h-6" />
              </div>
              <div className="hidden lg:block">
                <h1 className={`font-bold text-xl tracking-tighter ${isDark ? 'text-white' : 'text-slate-900'}`}>NEURAL</h1>
                <p className={`text-[10px] font-mono tracking-widest uppercase ${isDark ? 'text-cyan-400' : 'text-blue-600'}`}>Clean Pro</p>
              </div>
            </div>
            <nav className="space-y-2">
              {/* Dashboard 按钮 */}
              <button 
                onClick={() => setView('dashboard')}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all 
                  ${view === 'dashboard' 
                    ? (isDark ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-blue-50 text-blue-700 border border-blue-200')
                    : (isDark ? 'text-slate-400 hover:text-white hover:bg-white/5' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50')}
                `}
              >
                <Activity className="w-5 h-5" />
                <span className="hidden lg:block font-medium">Dashboard</span>
              </button>

                {/* Semantic Rules 按钮 */}
              <button 
                onClick={() => setView('rules')}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all 
                  ${view === 'rules' 
                    ? (isDark ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-blue-50 text-blue-700 border border-blue-200')
                    : (isDark ? 'text-slate-400 hover:text-white hover:bg-white/5' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50')}
                `}
              >
                <SlidersHorizontal className="w-5 h-5" />
                <span className="hidden lg:block font-medium">Semantic Rules</span>
              </button>
              {/* Review Lab 按钮 */}
              <button 
                onClick={() => {
                  // 通过 IPC 打开浏览器if (window.electron) {
                  if (window.electron) {
                    window.electron.ipcRenderer.invoke('shell:openExternal', 'http://localhost:3333');
                  } else {
                    // 调试模式下直接打开新窗口
                    window.open('http://localhost:3333', '_blank');}}}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all cursor-pointer 
                  ${view === 'review' // 注意：既然不在内部打开，这个高亮逻辑可能需要移除或改为只要点击了一下就高亮一会
                  ? (isDark ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'bg-blue-50 text-blue-700 border border-blue-200')
                  : (isDark ? 'text-slate-400 hover:text-white hover:bg-white/5' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50')}
                  `}
                  >
                    <PieChart className="w-5 h-5" />
                    <span className="hidden lg:block font-medium">Review Lab</span>
                    </button>
            </nav>
          </div>
          <div className="px-6 pb-6 hidden lg:flex flex-col gap-0">
              {/* 硬件卡片 */}
              <HardwareCard info={sysInfo} isDark={isDark} />
              {/* 2. 原有的核心引擎状态卡片 */}
              {renderStatusCard()}
          </div>
        </motion.div>

        {/* === 主内容区 === */}
        <div className="flex-1 flex flex-col p-8 overflow-hidden relative">
          
          {/* === 1. Dashboard View (原来的内容) === */}
          {view === 'dashboard' && (
             <div className="flex flex-col h-full animate-[fadeIn_0.5s_ease-out]">
                <header className="flex justify-between items-center mb-8">
                  <div>
                    <h2 className={`text-3xl font-bold mb-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>Task Configuration</h2>
                    <p className={isDark ? 'text-slate-400' : 'text-slate-500'}>Setup your NLP pipeline parameters.</p>
                  </div>
                  <NeonButton variant="ghost" isDark={isDark} onClick={() => setIsDark(!isDark)}>
                      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                  </NeonButton>
                </header>

                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0 animate-[slideUp_0.5s_ease-out]">
                  <div className="lg:col-span-2 space-y-6 overflow-y-auto pr-2 custom-scrollbar">
                    <GlassCard title="I/O Streams" isDark={isDark}>
                      {/* ... (此处保持您原来 I/O Streams 卡片内的所有代码) ... */}
                      <ModeSwitcher isRecursive={isRecursive} onChange={setIsRecursive} isDark={isDark} />
                      <div className="space-y-6">
                         {/* Source Input */}
                         <div className="group">
                           {/* ... Source Input 代码 ... */}
                           <label className={`text-sm font-medium mb-2 block ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Source Directory</label>
                            <div className="flex gap-3">
                              <div className={`flex-1 border rounded-lg px-4 py-3 font-mono text-sm truncate transition-colors ${isDark ? 'bg-slate-950/50 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'}`}>
                                {inputPath || "Please select..."}
                              </div>
                              <button onClick={() => handleBrowse('in')} className={`px-4 py-2 rounded-lg border transition-colors ${isDark ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-300' : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600 shadow-sm'}`}>
                                <FolderOpen className="w-5 h-5" />
                              </button>
                            </div>
                         </div>
                         
                         {/* Destination Output */}
                         <div className={`group transition-all duration-300 ${isRecursive ? 'opacity-50 pointer-events-none grayscale' : ''}`}>
                             {/* ... Destination Output 代码 (为了节省篇幅省略，请保留您原有的代码) ... */}
                             <div className="flex justify-between items-center mb-2">
                                <label className={`text-sm font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>Destination Directory</label>
                                <Toggle label="Auto Set /Output" checked={isRecursive ? true : autoOutput} onChange={setAutoOutput} isDark={isDark} />
                              </div>
                              <div className={`flex gap-3 transition-opacity ${(autoOutput || isRecursive) ? 'opacity-60 pointer-events-none' : 'opacity-100'}`}>
                                <div className={`flex-1 border rounded-lg px-4 py-3 font-mono text-sm truncate transition-colors ${isDark ? 'bg-slate-950/50 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'}`}>
                                  {isRecursive ? "🚧 Auto-managed: ./[Subfolder]/output/" : (outputPath || "Auto-generated...")}
                                </div>
                                <button onClick={() => handleBrowse('out')} className={`px-4 py-2 rounded-lg border transition-colors ${isDark ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-300' : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600 shadow-sm'}`}>
                                  <FolderOpen className="w-5 h-5" />
                                </button>
                              </div>
                              {isRecursive && <div className="mt-2 text-[10px] text-purple-400 flex items-center gap-1 animate-pulse"><Activity className="w-3 h-3" /> Output paths are locked to source structure in Batch Mode to prevent conflicts.</div>}
                         </div>
                      </div>
                    </GlassCard>

                    <GlassCard title="Model & Behavior" isDark={isDark}>
                        {/* ... (此处保持您原来 Model 卡片内的所有代码) ... */}
                        <div className="flex items-start justify-between mb-6">
                           <div className="flex items-start gap-4">
                             <div className={`p-3 rounded-lg border ${isDark ? 'bg-purple-500/10 border-purple-500/20 text-purple-400' : 'bg-purple-50 border-purple-200 text-purple-600'}`}><Zap className="w-6 h-6" /></div>
                             <div>
                               <h4 className={`font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>DeBERTa-Multilingual</h4>
                               <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Target: <span className="font-mono bg-black/10 px-1 rounded">{sysInfo?.active_model || 'Loading path...'}</span></p>
                             </div>
                           </div>
                           <button onClick={handleCheckUpdate} disabled={checkingUpdate} className={`p-2 rounded-lg transition-all ${isDark ? 'hover:bg-slate-800 text-slate-400 hover:text-cyan-400' : 'hover:bg-slate-100 text-slate-500 hover:text-blue-600'}`} title="Check for updates">
                             <RefreshCw className={`w-4 h-4 ${checkingUpdate ? 'animate-spin' : ''}`} />
                           </button>
                        </div>
                        <div className="space-y-4 pt-4 border-t border-dashed border-slate-700/50">
                          <Toggle label="Auto open folder on completion" checked={autoOpen} onChange={setAutoOpen} isDark={isDark} />
                        </div>
                    </GlassCard>

                    <div className="flex items-center gap-6 pt-4">
                        <NeonButton onClick={handleStart} disabled={isRunning || modelStatus !== 'ready'} icon={isRunning ? Activity : Play} isDark={isDark} className={highlightRun ? "ring-4 ring-purple-500 ring-opacity-50 animate-pulse" : ""}>
                         {highlightRun ? 'Click to Start Task' : (isRunning ? 'Processing...' : 'Initialize Run')}
                        </NeonButton>
                        {isRunning && (
                          <div className="flex-1">
                            <div className={`flex justify-between text-xs font-mono mb-1 ${isDark ? 'text-cyan-400' : 'text-blue-600'}`}><span>PROGRESS</span><span>{Math.round(progress)}%</span></div>
                            <div className={`h-1.5 w-full rounded-full overflow-hidden ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`}>
                              <motion.div className={`h-full shadow-lg ${isDark ? 'bg-cyan-400 shadow-cyan-500/50' : 'bg-blue-500 shadow-blue-500/30'}`} initial={{ width: 0 }} animate={{ width: `${progress}%` }} />
                            </div>
                          </div>
                        )}
                    </div>
                  </div>

                  <div className="lg:col-span-1 h-full min-h-[400px] flex flex-col">
                    <GlassCard className={`flex-1 flex flex-col !p-0 border ${isDark ? 'border-slate-700/80 bg-black/40' : 'border-slate-200 bg-slate-50'}`} isDark={isDark}>
                      <div className={`h-10 border-b flex items-center px-4 gap-2 ${isDark ? 'bg-slate-900/80 border-slate-800' : 'bg-slate-100 border-slate-200'}`}>
                        <Terminal className={`w-4 h-4 ${isDark ? 'text-slate-500' : 'text-slate-400'}`} />
                        <span className={`text-xs font-mono ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>TERMINAL OUTPUT</span>
                      </div>
                      <div className="flex-1 p-4 font-mono text-xs overflow-y-auto custom-scrollbar space-y-2">
                        <AnimatePresence>
                          {logs.map((log, i) => (
                            <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="flex gap-3">
                              <span className="text-slate-500 shrink-0">[{log.ts}]</span>
                              <span className={`${log.type === 'err' ? 'text-rose-500' : log.type === 'success' ? 'text-emerald-500' : log.type === 'sys' ? 'text-blue-500' : (isDark ? 'text-slate-300' : 'text-slate-700')}`}>
                                {log.type === 'sys' && <span className="text-blue-500 mr-2">➜</span>}{log.msg}
                              </span>
                            </motion.div>
                          ))}
                        </AnimatePresence>
                        <div ref={terminalEndRef} />
                      </div>
                    </GlassCard>
                  </div>
                </div>
             </div>
          )}
          
          {/* === 2. Semantic Rules View (新页面) === */}
          {view === 'rules' && (
             <div className="flex flex-col h-full animate-[fadeIn_0.5s_ease-out]">
                <header className="flex justify-between items-center mb-8">
                  <div>
                    <h2 className={`text-3xl font-bold mb-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>Semantic Rules</h2>
                    <p className={isDark ? 'text-slate-400' : 'text-slate-500'}>Define inclusion & exclusion criteria for the AI.</p>
                  </div>
                  {/* 这里可以复用 DarkMode 按钮，也可以不放 */}
                  <NeonButton variant="ghost" isDark={isDark} onClick={() => setIsDark(!isDark)}>
                      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                  </NeonButton>
                </header>

                <div className="flex-1 min-h-0">
                  {/* 🔥 在这里渲染你的新组件 */}
                  <SemanticRuleEditor 
                      isDark={isDark} 
                      initialConfig={semanticConfig} 
                      onSave={handleSaveRules} 
                  />
                </div>
             </div>
          )}

        </div>
      </div>
      <style>{`.custom-scrollbar::-webkit-scrollbar { width: 6px; } .custom-scrollbar::-webkit-scrollbar-track { background: transparent; } .custom-scrollbar::-webkit-scrollbar-thumb { background: ${isDark ? '#334155' : '#cbd5e1'}; border-radius: 3px; } .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: ${isDark ? '#475569' : '#94a3b8'}; }`}</style>
    </div>
  );
}