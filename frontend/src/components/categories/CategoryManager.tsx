import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { categoriesApi } from "../../api/categories";
import { getErrorMessage } from "../../api/client";
import { useCategories } from "../../hooks/useCategories";
import type { Category } from "../../types";
import { CategoryDot } from "../common/CategoryDot";
import { ColorPicker } from "../common/ColorPicker";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { ErrorAlert } from "../common/Feedback";
import { Icon } from "../common/Icon";
import { Modal } from "../common/Modal";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(50, "Max 50 characters"),
  transaction_type: z.enum(["income", "expense"]),
  color: z.string(),
});
type FormValues = z.infer<typeof schema>;

function CategoryFormModal({
  initial,
  open,
  onClose,
  onSaved,
}: {
  initial: Category | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? "",
      transaction_type: initial?.transaction_type ?? "expense",
      color: initial?.color ?? "#6250d6",
    },
  });

  const submit = async (values: FormValues) => {
    setError(null);
    try {
      if (initial) {
        await categoriesApi.update(initial.id, { name: values.name, color: values.color });
      } else {
        await categoriesApi.create(values);
      }
      onSaved();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <Modal open={open} title={initial ? "Edit category" : "New category"} onClose={onClose} size="sm">
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <ErrorAlert message={error} />
        <div>
          <label htmlFor="cat-name" className="label">Name</label>
          <input id="cat-name" className={`input ${errors.name ? "input-error" : ""}`} {...register("name")} />
          {errors.name && <p className="field-error">{errors.name.message}</p>}
        </div>
        <div>
          <label htmlFor="cat-type" className="label">Type</label>
          {initial ? (
            <input id="cat-type" className="input capitalize" value={initial.transaction_type} disabled />
          ) : (
            <select id="cat-type" className="input" {...register("transaction_type")}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </select>
          )}
          {initial && <p className="mt-1 text-xs text-slate-500">The type can't be changed after creation.</p>}
        </div>
        <div>
          <span className="label">Color</span>
          <Controller control={control} name="color" render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />} />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={isSubmitting}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={isSubmitting}>{isSubmitting ? "Saving..." : "Save"}</button>
        </div>
      </form>
    </Modal>
  );
}

export function CategoryManager() {
  const { categories, loading, error, reload } = useCategories();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [deleting, setDeleting] = useState<Category | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const custom = categories.filter((c) => !c.is_system);
  const system = categories.filter((c) => c.is_system);

  const confirmDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    setActionError(null);
    try {
      await categoriesApi.remove(deleting.id);
      setDeleting(null);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
      setDeleting(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Categories</h2>
          <p className="text-sm text-slate-500">Default categories are shared; custom ones are private to you.</p>
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          <Icon name="plus" className="h-4 w-4" /> Add
        </button>
      </div>
      <ErrorAlert message={error} onRetry={reload} />
      <ErrorAlert message={actionError} />

      <h3 className="mt-2 mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">Your categories</h3>
      {loading ? (
        <p className="text-sm text-slate-500">Loading...</p>
      ) : custom.length === 0 ? (
        <p className="text-sm text-slate-500">You haven't created any custom categories yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {custom.map((c) => (
            <li key={c.id} className="flex items-center justify-between py-2">
              <span className="flex items-center gap-3 text-sm">
                <CategoryDot color={c.color} name={c.name} size="sm" />
                <span className="font-medium text-slate-800">{c.name}</span>
                <span className="text-xs text-slate-500 capitalize">{c.transaction_type}</span>
              </span>
              <span>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setEditing(c);
                    setFormOpen(true);
                  }}
                  aria-label={`Edit ${c.name}`}
                >
                  <Icon name="edit" className="h-4 w-4" />
                </button>
                <button type="button" className="btn-ghost hover:text-critical" onClick={() => setDeleting(c)} aria-label={`Delete ${c.name}`}>
                  <Icon name="trash" className="h-4 w-4" />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <h3 className="mt-6 mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">Default categories</h3>
      <div className="flex flex-wrap gap-2">
        {system.map((c) => (
          <span key={c.id} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-700">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: c.color }} aria-hidden="true" />
            {c.name}
          </span>
        ))}
      </div>

      {formOpen && (
        <CategoryFormModal
          key={editing?.id ?? "new"}
          initial={editing}
          open={formOpen}
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            reload();
          }}
        />
      )}

      <ConfirmDialog
        open={deleting !== null}
        title="Delete category"
        message={`Delete "${deleting?.name ?? ""}"? Categories used by transactions can't be deleted.`}
        loading={busy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
