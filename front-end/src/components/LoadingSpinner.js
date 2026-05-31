import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingSpinner = ({ message = 'Loading...' }) => {
  return (
    <div className="surface p-10 text-center" role="status" aria-live="polite">
      <div className="inline-flex items-center justify-center rounded-full bg-brand-50 p-4 text-brand-600">
        <Loader2 className="h-7 w-7 animate-spin" />
      </div>
      <p className="mt-4 text-sm font-medium text-slate-700">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
