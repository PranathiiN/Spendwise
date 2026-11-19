import { useState } from "react";
import { getErrorMessage } from "../api/client";
import { goalsApi } from "../api/goals";
import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { EmptyState, ErrorAlert, PageHeader } from "../components/common/Feedback";
import { Icon } from "../components/common/Icon";
import { Modal } from "../components/common/Modal";
import { PageLoader } from "../components/common/Spinner";
import { StatCard } from "../components/dashboard/SummaryCards";
import { ContributeForm } from "../components/goals/ContributeForm";
import { GoalCard } from "../components/goals/GoalCard";
import { GoalForm } from "../components/goals/GoalForm";
import { useApi } from "../hooks/useApi";
import { useCurrency } from "../hooks/useCurrency";
import type { SavingsGoal, SavingsGoalPayload } from "../types";
import { toNumber } from "../utils/currency";

type ContributionState = { goal: SavingsGoal; action: "deposit" | "withdraw" } | null;

export function SavingsGoalsPage() {
  const { format } = useCurrency();
  const { data, loading, error, reload } = useApi(() => goalsApi.list(), []);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<SavingsGoal | null>(null);
  const [contribution, setContribution] = useState<ContributionState>(null);
  const [deleting, setDeleting] = useState<SavingsGoal | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const goals = data ?? [];
  const totalSaved = goals.reduce((s, g) => s + toNumber(g.current_amount), 0);
  const totalTarget = goals.reduce((s, g) => s + toNumber(g.target_amount), 0);
  const completed = goals.filter((g) => g.is_completed).length;

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
  };

  const handleSubmit = async (payload: SavingsGoalPayload) => {
    if (editing) {
      const { current_amount: _ignored, ...rest } = payload;
      await goalsApi.update(editing.id, rest);
    } else {
      await goalsApi.create(payload);
    }
    closeForm();
    reload();
  };

  const handleContribute = async (amount: string) => {
    if (!contribution) return;
    await goalsApi.contribute(contribution.goal.id, amount, contribution.action);
    setContribution(null);
    reload();
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    setActionError(null);
    try {
      await goalsApi.remove(deleting.id);
      setDeleting(null);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Savings goals"
        subtitle="Plan for the things that matter and track your progress"
        actions={
          <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
            <Icon name="plus" className="h-4 w-4" /> New goal
          </button>
        }
      />

      <ErrorAlert message={actionError} />
      <ErrorAlert message={error} onRetry={reload} />

      {loading && !data ? (
        <PageLoader />
      ) : goals.length === 0 ? (
        <EmptyState
          title="No savings goals yet"
          description="Create a goal such as an emergency fund, a trip or a new laptop."
          action={
            <button type="button" className="btn-primary" onClick={() => setFormOpen(true)}>
              <Icon name="plus" className="h-4 w-4" /> New goal
            </button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Total saved" value={format(totalSaved)} />
            <StatCard label="Total target" value={format(totalTarget)} />
            <StatCard label="Goals completed" value={`${completed} / ${goals.length}`} />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {goals.map((g) => (
              <GoalCard
                key={g.id}
                goal={g}
                format={format}
                onDeposit={() => setContribution({ goal: g, action: "deposit" })}
                onWithdraw={() => setContribution({ goal: g, action: "withdraw" })}
                onEdit={() => {
                  setEditing(g);
                  setFormOpen(true);
                }}
                onDelete={() => setDeleting(g)}
              />
            ))}
          </div>
        </>
      )}

      <Modal open={formOpen} title={editing ? "Edit goal" : "New savings goal"} onClose={closeForm}>
        <GoalForm key={editing?.id ?? "new"} initial={editing} onSubmit={handleSubmit} onCancel={closeForm} />
      </Modal>

      <Modal
        open={contribution !== null}
        title={contribution?.action === "withdraw" ? "Withdraw from goal" : "Add money to goal"}
        onClose={() => setContribution(null)}
        size="sm"
      >
        {contribution && (
          <ContributeForm
            key={`${contribution.goal.id}-${contribution.action}`}
            goal={contribution.goal}
            action={contribution.action}
            format={format}
            onSubmit={handleContribute}
            onCancel={() => setContribution(null)}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete goal"
        message={`Delete "${deleting?.name ?? ""}"? Its saved progress will be removed.`}
        loading={busy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
