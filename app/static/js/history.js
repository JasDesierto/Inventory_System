const historyFilterForm = document.getElementById("history-filter-form");

if (historyFilterForm) {
    // History filtering is client-side because the full transaction list is
    // already rendered for admins and the dataset is expected to stay modest.
    const rows = Array.from(document.querySelectorAll("[data-history-row]"));
    const tableBody = document.getElementById("history-table-body");
    const pagination = document.getElementById("history-pagination");
    const dateFromInput = document.getElementById("history-date-from");
    const dateToInput = document.getElementById("history-date-to");
    const typeInput = document.getElementById("history-type-filter");
    const itemInput = document.getElementById("history-item-search");
    const userInput = document.getElementById("history-user-search");
    const pageSize = 10;
    let currentPage = 1;

    if (!rows.length) {
        if (pagination) {
            pagination.hidden = true;
        }
        return;
    }

    const emptyRow = document.createElement("tr");
    emptyRow.hidden = true;
    emptyRow.innerHTML = '<td colspan="8" class="empty-state">No transactions match the current filters.</td>';
    tableBody?.appendChild(emptyRow);

    const normalize = (value) => String(value ?? "").trim().toLowerCase();

    const getFilteredRows = () => {
        const from = dateFromInput?.value || "";
        const to = dateToInput?.value || "";
        const type = typeInput?.value || "";
        const item = normalize(itemInput?.value);
        const user = normalize(userInput?.value);

        return rows.filter((row) => {
            const rowDate = row.dataset.date || "";
            const rowType = row.dataset.type || "";
            const rowItem = `${row.dataset.item || ""} ${row.dataset.remarks || ""}`;
            const rowUser = row.dataset.user || "";

            if (from && rowDate < from) {
                return false;
            }
            if (to && rowDate > to) {
                return false;
            }
            if (type && rowType !== type) {
                return false;
            }
            if (item && !rowItem.includes(item)) {
                return false;
            }
            if (user && !rowUser.includes(user)) {
                return false;
            }
            return true;
        });
    };

    const renderPagination = (totalPages) => {
        if (!pagination) {
            return;
        }

        if (totalPages <= 1) {
            pagination.hidden = true;
            pagination.innerHTML = "";
            return;
        }

        pagination.hidden = false;
        pagination.innerHTML = `
            <button class="button button--ghost" type="button" data-page-action="prev" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
            <span class="pagination-bar__status">Page ${currentPage} of ${totalPages}</span>
            <button class="button button--ghost" type="button" data-page-action="next" ${currentPage === totalPages ? "disabled" : ""}>Next</button>
        `;
    };

    const render = () => {
        // Pagination happens after filtering so page counts always reflect the
        // active search constraints.
        const filteredRows = getFilteredRows();
        const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
        currentPage = Math.min(Math.max(currentPage, 1), totalPages);

        const startIndex = (currentPage - 1) * pageSize;
        const visibleRows = new Set(filteredRows.slice(startIndex, startIndex + pageSize));

        rows.forEach((row) => {
            row.hidden = !visibleRows.has(row);
        });

        emptyRow.hidden = filteredRows.length > 0;
        renderPagination(filteredRows.length ? totalPages : 0);
    };

    historyFilterForm.addEventListener("input", () => {
        currentPage = 1;
        render();
    });

    historyFilterForm.addEventListener("reset", () => {
        window.setTimeout(() => {
            currentPage = 1;
            render();
        }, 0);
    });

    pagination?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-page-action]");
        if (!button) {
            return;
        }
        currentPage += button.dataset.pageAction === "next" ? 1 : -1;
        render();
    });

    render();
}
