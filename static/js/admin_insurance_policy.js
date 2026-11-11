document.addEventListener('DOMContentLoaded', function () {
    const userField = document.getElementById('id_user');
    const cashFlowField = document.getElementById('id_linked_cash_flow');
    const premiumField = document.getElementById('id_premium_amount');
    const frequencyField = document.getElementById('id_payment_frequency');

    if (!cashFlowField) return;

    let cashflows = [];
    try {
        const raw = cashFlowField.getAttribute('data-cashflows');
        if (raw) {
            cashflows = JSON.parse(raw);
        }
    } catch (e) {
        cashflows = [];
    }

    const byId = new Map();
    cashflows.forEach(function (cf) {
        byId.set(String(cf.id), cf);
    });

    function filterCashFlowsByUser() {
        if (!userField) return;
        const selectedUserId = String(userField.value || '');
        const currentValue = String(cashFlowField.value || '');
        const emptyLabel = (cashFlowField.options[0] && cashFlowField.options[0].value === '')
            ? cashFlowField.options[0].textContent
            : '---------';

        cashFlowField.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = emptyLabel;
        cashFlowField.appendChild(defaultOpt);

        let keepCurrent = false;
        if (selectedUserId) {
            cashflows.forEach(function (cf) {
                if (String(cf.user_id) === selectedUserId) {
                    const opt = document.createElement('option');
                    opt.value = String(cf.id);
                    opt.textContent = cf.linked_policy
                        ? `${cf.label} (bereits verknüpft: ${cf.linked_policy})`
                        : cf.label;
                    if (cf.is_disabled) {
                        opt.disabled = true;
                    }
                    if (String(cf.id) === currentValue && !cf.is_disabled) {
                        opt.selected = true;
                        keepCurrent = true;
                    }
                    cashFlowField.appendChild(opt);
                }
            });
        }

        if (!keepCurrent) {
            cashFlowField.value = '';
        }
    }

    function applySelectedCashFlowAmount() {
        const selectedId = String(cashFlowField.value || '');
        if (!selectedId) return;
        const cf = byId.get(selectedId);
        if (!cf || cf.is_disabled) return;

        if (premiumField && cf.value !== null && cf.value !== undefined) {
            premiumField.value = cf.value;
        }
        if (frequencyField && cf.frequency) {
            frequencyField.value = cf.frequency;
        }
    }

    if (userField) {
        userField.addEventListener('change', filterCashFlowsByUser);
    }

    cashFlowField.addEventListener('change', applySelectedCashFlowAmount);
});
