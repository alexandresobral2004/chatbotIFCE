import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'info' | 'warning' | 'success' | 'error';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, variant = 'info' }) => {
  if (!status) return null;

  const variantStyles = {
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
    success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
    error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };

  const dots = (
    <span className="flex gap-0.5" aria-label="Loading">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-current animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </span>
  );

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        transition-all duration-300
        ${variantStyles[variant]}
      `}
      role="status"
      aria-live="polite"
    >
      {dots}
      <span>{status}</span>
    </div>
  );
};

export default StatusBadge;