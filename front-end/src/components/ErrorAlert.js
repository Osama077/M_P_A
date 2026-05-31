import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

const ErrorAlert = ({ message, onDismiss }) => {
  const [visible, setVisible] = useState(true);

  const handleDismiss = () => {
    setVisible(false);
    if (onDismiss) onDismiss();
  };

  if (!visible) return null;

  return (
    <div className="surface border-rose-200 bg-rose-50 p-4 text-rose-900" role="alert" aria-live="assertive">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-rose-100 p-2">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="font-semibold">Error</p>
          <p className="text-sm mt-1">{message}</p>
        </div>
        <button
          onClick={handleDismiss}
          className="rounded-md p-1 text-rose-700 transition hover:bg-rose-100"
          aria-label="Dismiss error"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default ErrorAlert;
