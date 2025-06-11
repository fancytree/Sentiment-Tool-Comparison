import { createContext, useContext, useState, ReactNode } from 'react';
import * as RadixToast from '@radix-ui/react-toast';

type ToastType = 'success' | 'error' | 'info';

interface ToastContextType {
  showToast: (message: string, type: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  const [type, setType] = useState<ToastType>('info');
  const [open, setOpen] = useState(false);

  const showToast = (message: string, type: ToastType) => {
    setMessage(message);
    setType(type);
    setOpen(true);
    setTimeout(() => setOpen(false), 3000);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <RadixToast.Provider swipeDirection="right">
        <RadixToast.Root
          className="ToastRoot"
          open={open}
          onOpenChange={setOpen}
          style={{
            backgroundColor: type === 'error' ? '#ef4444' : type === 'success' ? '#22c55e' : '#3b82f6',
            borderRadius: '6px',
            padding: '12px',
            display: 'flex',
            color: 'white',
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            zIndex: 1000,
          }}
        >
          <RadixToast.Description>{message}</RadixToast.Description>
        </RadixToast.Root>
        <RadixToast.Viewport />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
} 