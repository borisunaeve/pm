import { useState, type FormEvent } from "react";

type NewCardData = {
  title: string;
  details: string;
  priority: "low" | "medium" | "high";
  due_date: string;
  labels: string;
};

const initialFormState: NewCardData = {
  title: "",
  details: "",
  priority: "medium",
  due_date: "",
  labels: "",
};

type NewCardFormProps = {
  onAdd: (data: NewCardData) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const set = (field: keyof NewCardData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => setFormState((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) return;
    onAdd({ ...formState, title: formState.title.trim(), details: formState.details.trim(), labels: formState.labels.trim() });
    setFormState(initialFormState);
    setIsOpen(false);
  };

  const inputClass = "w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface-strong)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]";

  return (
    <div className="mt-4">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-2">
          <input
            value={formState.title}
            onChange={set("title")}
            placeholder="Card title"
            className={inputClass + " font-medium"}
            required
            autoFocus
          />
          <textarea
            value={formState.details}
            onChange={set("details")}
            placeholder="Details (optional)"
            rows={2}
            className={inputClass + " resize-none"}
          />
          <div className="flex gap-2">
            <select
              value={formState.priority}
              onChange={set("priority")}
              className={inputClass}
            >
              <option value="low">Low priority</option>
              <option value="medium">Medium priority</option>
              <option value="high">High priority</option>
            </select>
            <input
              type="date"
              value={formState.due_date}
              onChange={set("due_date")}
              className={inputClass}
              title="Due date"
            />
          </div>
          <input
            value={formState.labels}
            onChange={set("labels")}
            placeholder="Labels (comma-separated, e.g. frontend,urgent)"
            className={inputClass}
          />
          <div className="flex items-center gap-2 pt-1">
            <button
              type="submit"
              className="rounded-full bg-[var(--purple-sec)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => { setIsOpen(false); setFormState(initialFormState); }}
              className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="w-full rounded-full border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
        >
          Add a card
        </button>
      )}
    </div>
  );
};
