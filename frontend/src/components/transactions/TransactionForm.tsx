import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { getErrorMessage } from "../../api/client";
import {
  PAYMENT_METHOD_LABELS,
  type Category,
  type PaymentMethod,
  type Transaction,
  type TransactionPayload,
} from "../../types";
import { todayISO } from "../../utils/dates";
import { ErrorAlert } from "../common/Feedback";

// Amounts stay strings end-to-end; the backend parses them into Decimal.
export const amountSchema = z
  .string()
  .trim()
  .min(1, "Amount is required")
  .regex(/^\d{1,10}(\.\d{1,2})?$/, "Enter a valid amount with up to 2 decimal places")
  .refine((v) => Number(v) > 0, "Amount must be greater than zero");

const schema = z.object({
  transaction_type: z.enum(["income", "expense"]),
  amount: amountSchema,
  description: z.string().trim().min(1, "Description is required").max(255, "Max 255 characters"),
  category_id: z.string().min(1, "Choose a category"),
  transaction_date: z.string().min(1, "Date is required"),
  payment_method: z.string(),
  notes: z.string().max(1000, "Max 1000 characters"),
});
type FormValues = z.infer<typeof schema>;

interface TransactionFormProps {
  categories: Category[];
  initial?: Transaction | null;
  onSubmit: (payload: TransactionPayload) => Promise<void>;
  onCancel: () => void;
}

export function TransactionForm({ categories, initial, onSubmit, onCancel }: TransactionFormProps) {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      transaction_type: initial?.transaction_type ?? "expense",
      amount: initial?.amount ?? "",
      description: initial?.description ?? "",
      category_id: initial?.category_id ?? "",
      transaction_date: initial?.transaction_date ?? todayISO(),
      payment_method: initial?.payment_method ?? "",
      notes: initial?.notes ?? "",
    },
  });

  const type = watch("transaction_type");
  const options = useMemo(() => categories.filter((c) => c.transaction_type === type), [categories, type]);

  // Clear the category if it doesn't match the newly selected type.
  useEffect(() => {
    const current = getValues("category_id");
    if (current && !options.some((o) => o.id === current)) {
      setValue("category_id", "");
    }
  }, [options, getValues, setValue]);

  const submit = async (values: FormValues) => {
    setError(null);
    try {
      await onSubmit({
        transaction_type: values.transaction_type,
        amount: values.amount,
        description: values.description,
        category_id: values.category_id,
        transaction_date: values.transaction_date,
        payment_method: (values.payment_method || null) as PaymentMethod | null,
        notes: values.notes.trim() || null,
      });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <ErrorAlert message={error} />

      <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1" role="radiogroup" aria-label="Transaction type">
        {(["expense", "income"] as const).map((t) => (
          <label
            key={t}
            className={`cursor-pointer rounded-md py-2 text-center text-sm font-medium transition ${
              type === t ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <input type="radio" value={t} className="sr-only" {...register("transaction_type")} />
            {t === "expense" ? "Expense" : "Income"}
          </label>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="amount" className="label">Amount</label>
          <input id="amount" inputMode="decimal" placeholder="0.00" className={`input ${errors.amount ? "input-error" : ""}`} {...register("amount")} />
          {errors.amount && <p className="field-error">{errors.amount.message}</p>}
        </div>
        <div>
          <label htmlFor="transaction_date" className="label">Date</label>
          <input id="transaction_date" type="date" className={`input ${errors.transaction_date ? "input-error" : ""}`} {...register("transaction_date")} />
          {errors.transaction_date && <p className="field-error">{errors.transaction_date.message}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="description" className="label">Description</label>
        <input id="description" placeholder="e.g. Grocery shopping" className={`input ${errors.description ? "input-error" : ""}`} {...register("description")} />
        {errors.description && <p className="field-error">{errors.description.message}</p>}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="category_id" className="label">Category</label>
          <select id="category_id" className={`input ${errors.category_id ? "input-error" : ""}`} {...register("category_id")}>
            <option value="">Select a category</option>
            {options.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
                {c.is_system ? "" : " (custom)"}
              </option>
            ))}
          </select>
          {errors.category_id && <p className="field-error">{errors.category_id.message}</p>}
        </div>
        <div>
          <label htmlFor="payment_method" className="label">Payment method (optional)</label>
          <select id="payment_method" className="input" {...register("payment_method")}>
            <option value="">Not specified</option>
            {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="notes" className="label">Notes (optional)</label>
        <textarea id="notes" rows={2} className={`input ${errors.notes ? "input-error" : ""}`} {...register("notes")} />
        {errors.notes && <p className="field-error">{errors.notes.message}</p>}
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : initial ? "Save changes" : "Add transaction"}
        </button>
      </div>
    </form>
  );
}
