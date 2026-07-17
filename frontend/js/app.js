const API = '/api';

// All valid categories a transaction can belong to
const CATEGORIES = [
  'Food & Dining', 'Groceries', 'Transport', 'Subscriptions',
  'Shopping', 'Health', 'Utilities', 'Travel', 'Entertainment',
  'Income', 'Transfers', 'Uncategorized'
];

async function loadDashboard() {
  // Fetch all data from the backend at the same time, then render everything
  const [summary, subscriptions, transactions] = await Promise.all([
    fetch(`${API}/summary`).then(r => r.json()),
    fetch(`${API}/subscriptions`).then(r => r.json()),
    fetch(`${API}/transactions`).then(r => r.json()),
  ]);

  renderSummary(summary, subscriptions);
  renderSubscriptions(subscriptions);
  renderTransactions(transactions);
  renderChart(summary);
}

function renderSummary(summary, subscriptions) {
  // Add up all debits for total spent, all credits for total received
  const spent = summary.filter(r => r.total < 0).reduce((s, r) => s + Math.abs(r.total), 0);
  const credited = summary.filter(r => r.total > 0).reduce((s, r) => s + r.total, 0);

  // Deduplicate by merchant before summing — same logic as the table
  const seen = new Set();
  const uniqueSubs = subscriptions.filter(t => {
    const key = t.description.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Convert each subscription to a monthly cost based on its frequency
  const monthlyEst = uniqueSubs.reduce((sum, t) => {
    const amt = Math.abs(t.amount);
    if (t.frequency === 'monthly') return sum + amt;
    if (t.frequency === 'annual') return sum + amt / 12;
    if (t.frequency === 'weekly') return sum + amt * 4.33;
    if (t.frequency === 'biweekly') return sum + amt * 2.17;
    return sum;
  }, 0);

  document.getElementById('total-spent').textContent = `$${spent.toFixed(2)}`;
  document.getElementById('total-credited').textContent = `$${credited.toFixed(2)}`;
  document.getElementById('sub-count').textContent = uniqueSubs.length;
  document.getElementById('sub-cost').textContent = `$${monthlyEst.toFixed(2)}/mo`;
}

function renderSubscriptions(subscriptions) {
  // Remove duplicate merchants and sort by highest amount
  const seen = new Set();
  const unique = subscriptions.filter(t => {
    const key = t.description.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount));

  const tbody = document.querySelector('#sub-table tbody');
  if (!unique.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:#64748b;padding:1rem;">No recurring payments detected.</td></tr>';
    return;
  }

  tbody.innerHTML = unique.map(t => {
    const amt = Math.abs(t.amount);
    const monthly = t.frequency === 'monthly' ? amt
      : t.frequency === 'annual' ? amt / 12
      : t.frequency === 'weekly' ? amt * 4.33
      : t.frequency === 'biweekly' ? amt * 2.17 : amt;
    return `<tr>
      <td>${t.description}</td>
      <td>$${amt.toFixed(2)}</td>
      <td>${t.frequency || '—'}</td>
      <td>$${monthly.toFixed(2)}/mo</td>
    </tr>`;
  }).join('');
}

let allTransactions = [];

function renderTransactions(transactions, filterCategory = '') {
  allTransactions = transactions;

  // If a category filter is selected, only show matching transactions
  const filtered = filterCategory
    ? transactions.filter(t => t.category === filterCategory)
    : transactions;

  const tbody = document.querySelector('#tx-table tbody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:#64748b;padding:1rem;">No transactions found.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(t => `
    <tr>
      <td>${t.date}</td>
      <td>${t.description}</td>
      <td class="category-cell" data-id="${t.id}" data-category="${t.category}">
        <span class="category-label">${t.category}</span>
      </td>
      <td class="${t.amount < 0 ? 'debit' : 'credit'}">
        ${t.amount < 0 ? '-' : '+'}$${Math.abs(t.amount).toFixed(2)}
      </td>
    </tr>
  `).join('');

  // Make each category label clickable to open the edit dropdown
  document.querySelectorAll('.category-cell').forEach(cell => {
    cell.addEventListener('click', () => openCategoryEdit(cell));
  });
}

function openCategoryEdit(cell) {
  // Don't open a second dropdown if one is already open
  if (cell.querySelector('select')) return;
  const current = cell.dataset.category;
  const id = cell.dataset.id;

  // Build a dropdown with all available categories
  const select = document.createElement('select');
  CATEGORIES.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = cat;
    if (cat === current) opt.selected = true;
    select.appendChild(opt);
  });

  cell.innerHTML = '';
  cell.appendChild(select);
  select.focus();

  const restore = (label) => {
    cell.innerHTML = `<span class="category-label">${label}</span>`;
    cell.addEventListener('click', () => openCategoryEdit(cell));
  };

  select.addEventListener('change', async () => {
    const newCat = select.value;
    // Save the new category to the database
    await fetch(`${API}/transactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: newCat }),
    });
    cell.dataset.category = newCat;
    restore(newCat);
  });

  // If the user clicks away without changing, restore the original label
  select.addEventListener('blur', () => restore(current));
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();

  // Filter the transaction table when a category is selected
  document.getElementById('category-filter').addEventListener('change', e => {
    renderTransactions(allTransactions, e.target.value);
  });

  // Clear all data when the reset button is clicked
  document.getElementById('reset-btn').addEventListener('click', async () => {
    if (!confirm('Clear all transaction data?')) return;
    await fetch(`${API}/transactions`, { method: 'DELETE' });
    loadDashboard();
  });
});
