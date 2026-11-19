import { useMemo, useState } from "react";
import { budgetsApi } from "../api/budgets";
import { getErrorMessage } from "../api/client";
import { BudgetCard } from "../components/budgets/BudgetCard";
import { BudgetForm, type BudgetFormValues } from "../components/budgets/BudgetForm";
import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { EmptyState, ErrorAlert, PageHeader, SuccessAlert } from "../components/common/Feedback";
import { Icon } from "../components/common/Icon";
import { Modal } from "../components/common/Modal";
import { MonthPicker } from "../components/common/MonthPicker";
import { PageLoader } from "../components/common/Spinner";
import { StatCard } from "../components/dashboard/SummaryCards";
import { useApi } from "../hooks/useApi";
import { useCategories } from "../hooks/useCategories";
import { useCurrency } from "../hooks/useCurrency";
import type { Budget } from "../types";
import { toNumber } from "../utils/currency";
import { currentMonth, formatMonthLabel } from "../utils/dates";

export function BudgetsPage() {
  const { format } = useCurrency();
  const { expenseCategories } = useCategories();
  const [month, setMonth] = useState(currentMonth());
  const { data, loading, error, reload } = useApi(() => budgetsApi.list(month), [month]);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Budget | null>(null);
  const [deleting, setDeleting] = useState<Budget | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const availableCategories = useMemo(() => {
    const used = new Set((data?.budgets ?? []).map((b) => b.category.id));
    return expenseCategories.filter((c) => !used.has(c.id));
  }, [data, expenseCategories]);

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
  };

  const handleSubmit = async (values: BudgetFormValues) => {
    if (editing) {
      await budgetsApi.update(editing.id, { amount: values.amount, alert_threshold: values.alert_threshold });
    } else {
      await budgetsApi.create({ ...values, month });
    }
    closeForm();
    reload();
  };

  const copyPrevious = async () => {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const res = await budgetsApi.copyPrevious(month);
      setNotice(res.created > 0 ? `Copied ${res.created} budget(s) from last month.` : "Nothing new to copy from last month.");
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    setActionError(null);
    try {
      await budgetsApi.remove(deleting.id);
      setDeleting(null);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const remaining = toNumber(data?.total_remaining);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Budgets"
        subtitle="Set monthly limits per category and get warned before you overspend"
        actions={
          <>
            <MonthPicker value={month} onChange={setMonth} />
            <button type="button" className="btn-secondary" onClick={copyPrevious} disabled={busy}>
              <Icon name="copy" className="h-4 w-4" /> Copy last month
            </button>
            <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
              <Icon name="plus" className="h-4 w-4" /> New budget
            </button>
          </>
        }
      />

      <SuccessAlert message={notice} />
      <ErrorAlert message={actionError} />
      <ErrorAlert message={error} onRetry={reload} />

      {loading && !data ? (
        <PageLoader />
      ) : data ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Total budgeted" value={format(data.total_budgeted)} hint={`${data.budgets.length} budget(s)`} />
            <StatCard label="Spent so far" value={format(data.total_spent)} hint="Across budgeted categories" />
            <StatCard
              label={remaining < 0 ? "Over budget" : "Remaining"}
              value={format(String(Math.abs(remaining)))}
              hint={`${data.warning_count} near limit · ${data.exceeded_count} exceeded`}
            />
          </div>

          {data.budgets.length === 0 ? (
            <EmptyState
              title={`No budgets for ${formatMonthLabel(month)}`}
              description="Create a budget for a category, or copy last month's budgets."
              action={
                <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
                  <Icon name="plus" className="h-4 w-4" /> New budget
                </button>
              }
            />
          ) : (
            <div className={`grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 ${loading ? "opacity-60" : ""}`}>
              {data.budgets.map((b) => (
                <BudgetCard
                  key={b.id}
                  budget={b}
                  format={format}
                  onEdit={() => {
                    setEditing(b);
                    setFormOpen(true);
                  }}
                  onDelete={() => setDeleting(b)}
                />
              ))}
            </div>
          )}
        </>
      ) : null}

      <Modal open={formOpen} title={editing ? "Edit budget" : "New budget"} onClose={closeForm}>
        <BudgetForm
          key={editing?.id ?? `new-${month}`}
          month={month}
          availableCategories={availableCategories}
          initial={editing}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete budget"
        message={`Delete the ${deleting?.category.name ?? ""} budget for ${formatMonthLabel(month)}?`}
        loading={busy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
