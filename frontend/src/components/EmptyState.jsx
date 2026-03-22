import { FileX, Inbox, Search, Calendar, Users, FileText, DollarSign, ClipboardList } from "lucide-react";
import { Button } from "./ui/button";

const ICONS = {
  default: Inbox,
  search: Search,
  calendar: Calendar,
  users: Users,
  file: FileText,
  finance: DollarSign,
  checklist: ClipboardList,
  empty: FileX,
};

export function EmptyState({
  icon = "default",
  title = "No data yet",
  description = "There's nothing here at the moment.",
  actionLabel,
  onAction,
  className = "",
}) {
  const Icon = ICONS[icon] || ICONS.default;

  return (
    <div
      className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}
      data-testid="empty-state"
    >
      <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-slate-400 dark:text-slate-500" />
      </div>
      <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-1">
        {title}
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-4">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button
          onClick={onAction}
          variant="outline"
          size="sm"
          data-testid="empty-state-action"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
