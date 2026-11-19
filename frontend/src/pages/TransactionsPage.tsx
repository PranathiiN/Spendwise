import { useEffect, useState } from "react";
import { getErrorMessage } from "../api/client";
import { transactionsApi } from "../api/transactions";
import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { EmptyState, ErrorAlert, PageHeader } from "../components/common/Feedback";
import { Icon } from "../components/common/Icon";
import { Modal } from "../components/common/Modal";
import { Pagination } from "../components/common/Pagination";
import { PageLoader } from "../components/common/Spinner";
import { QuickAddBar } from "../components/transactions/QuickAddBar";
import { TransactionFiltersBar } from "../components/transactions/TransactionFiltersBar";
import { TransactionForm } from "../components/transactions/TransactionForm";
import { TransactionTable } from "../components/transactions/TransactionTable";
import { useApi } from "../hooks/useApi";
import { useCategories } from "../hooks/useCategories";
import { useCurrency } from "../hooks/useCurrency";
import { useDebounce } from "../hooks/useDebounce";
import type { ParsedTransaction, Transaction, TransactionFilters, TransactionPayload } from "../types";

const DEFAULT_FILTERS: TransactionFilters = {
  page: 1,
  page_size: 20,
  sort_by: "transaction_date",
  sort_order: "desc",
};

const AMOUNT_RE = /^\d+(\.\d{1,2})?$/;

export function TransactionsPage() {
  const { format } = useCurrency();
  const { categories, error: categoriesError } = useCategories();
  const [filters, setFilters] = useState<TransactionFilters>(DEFAULT_FILTERS);
  const [searchText, setSearchText] = useState("");
  const debouncedSearch = useDebounce(searchText);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [prefill, setPrefill] = useState<ParsedTransaction | null>(null);
  const [formKey, setFormKey] = useState(0);
  const [deleting, setDeleting] = useState<Transaction | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setFilters((f) => ((f.search ?? "") === debouncedSearch ? f : { ...f, search: debouncedSearch, page: 1 }));
  }, [debouncedSearch]);

  // Ignore half-typed amount filters instead of sending invalid values to the API.
  const effectiveFilters: TransactionFilters = {
    ...filters,
    min_amount: filters.min_amount && AMOUNT_RE.test(filters.min_amount) ? filters.min_amount : "",
    max_amount: filters.max_amount && AMOUNT_RE.test(filters.max_amount) ? filters.max_amount : "",
  };
  const filterKey = JSON.stringify(effectiveFilters);
  const { data, loading, error, reload } = useApi(() => transactionsApi.list(effectiveFilters), [filterKey]);

  const updateFilters = (patch: Partial<TransactionFilters>) => setFilters((f) => ({ ...f, ...patch, page: 1 }));

  const handleSort = (column: NonNullable<TransactionFilters["sort_by"]>) => {
    setFilters((f) => ({
      ...f,
      sort_by: column,
      sort_order: f.sort_by === column && f.sort_order === "desc" ? "asc" : "desc",
      page: 1,
    }));
  };

  const openCreate = () => {
    setEditing(null);
    setPrefill(null);
    setFormKey((k) => k + 1);
    setFormOpen(true);
  };

  const openPrefilled = (parsed: ParsedTransaction) => {
    setEditing(null);
    setPrefill(parsed);
    setFormKey((k) => k + 1);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
    setPrefill(null);
  };

  const handleSubmit = async (payload: TransactionPayload) => {
    if (editing) {
      await transactionsApi.update(editing.id, payload);
    } else {
      await transactionsApi.create(payload);
    }
    closeForm();
    reload();
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    setActionError(null);
    try {
      await transactionsApi.remove(deleting.id);
      setDeleting(null);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setDeleteBusy(false);
    }
  };

  const hasActiveFilters = Boolean(
    filters.search || filters.transaction_type || filters.category_id || filters.payment_method ||
      filters.start_date || filters.end_date || filters.min_amount || filters.max_amount,
  );

  return (
    <div className="space-y-4">
      <PageHeader
        title="Transactions"
        subtitle="Record, search and organise your income and expenses"
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            <Icon name="plus" className="h-4 w-4" /> Add transaction
          </button>
        }
      />

      <QuickAddBar onParsed={openPrefilled} />

      <ErrorAlert message={categoriesError} />
      <ErrorAlert message={actionError} />

      <TransactionFiltersBar
        filters={filters}
        searchText={searchText}
        onSearchChange={setSearchText}
        onChange={updateFilters}
        onReset={() => {
          setSearchText("");
          setFilters(DEFAULT_FILTERS);
        }}
        categories={categories}
      />

      {data && (
        <div className="flex flex-wrap gap-4 text-sm text-slate-600">
          <span>
            Income: <span className="font-semibold text-[#1d5aa3]">{format(data.total_income)}</span>
          </span>
          <span>
            Expenses: <span className="font-semibold text-slate-900">{format(data.total_expense)}</span>
          </span>
          <span className="text-slate-400">({data.total} matching)</span>
        </div>
      )}

      <ErrorAlert message={error} onRetry={reload} />

      {loading && !data ? (
        <PageLoader />
      ) : data && data.items.length === 0 ? (
        <EmptyState
          title={hasActiveFilters ? "No matching transactions" : "No transactions yet"}
          description={hasActiveFilters ? "Try changing or resetting your filters." : "Add your first income or expense to get started."}
          action={
            !hasActiveFilters && (
              <button type="button" className="btn-primary" onClick={openCreate}>
                <Icon name="plus" className="h-4 w-4" /> Add transaction
              </button>
            )
          }
        />
      ) : data ? (
        <div className={`space-y-4 ${loading ? "opacity-60" : ""}`}>
          <TransactionTable
            items={data.items}
            format={format}
            sortBy={filters.sort_by}
            sortOrder={filters.sort_order}
            onSort={handleSort}
            onEdit={(tx) => {
              setEditing(tx);
              setPrefill(null);
              setFormOpen(true);
            }}
            onDelete={setDeleting}
          />
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            total={data.total}
            pageSize={data.page_size}
            onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
          />
        </div>
      ) : null}

      <Modal
        open={formOpen}
        title={editing ? "Edit transaction" : "Add transaction"}
        onClose={closeForm}
      >
        <TransactionForm
          key={editing?.id ?? `new-${formKey}`}
          categories={categories}
          initial={editing}
          prefill={prefill}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete transaction"
        message={`Delete "${deleting?.description ?? ""}"? This cannot be undone.`}
        loading={deleteBusy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </div>
  );
}
