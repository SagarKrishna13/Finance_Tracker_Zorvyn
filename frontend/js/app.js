const API_BASE = ""; // Relative since served by FastAPI

// State Management
let currentUser = { name: "Public User", role: "guest" };
let currentToken = null;
let charts = {};

// DOM Elements
const eLoader = document.getElementById("loader");
const eAuthModal = document.getElementById("auth-modal");
const eDashScreen = document.getElementById("dashboard-screen");
const eLoginForm = document.getElementById("login-form");
const eErrorMsg = document.getElementById("login-error");
const eAdminLoginBtn = document.getElementById("admin-login-btn");
const eLogoutBtn = document.getElementById("logout-btn");

// Init
document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    
    // Bind Events
    eLoginForm.addEventListener("submit", handleLogin);
    eAdminLoginBtn.addEventListener("click", () => eAuthModal.classList.remove("hidden"));
    eLogoutBtn.addEventListener("click", logout);
    document.getElementById("add-txn-nav-btn").addEventListener("click", () => switchTab("manage"));
    document.getElementById("txn-form").addEventListener("submit", handleCreateTransaction);
    document.getElementById("edit-form").addEventListener("submit", submitEditTransaction);
    document.getElementById("download-report-btn").addEventListener("click", downloadReport);
    
    // Bind Tab Nav
    document.querySelectorAll(".nav-links li").forEach(li => {
        li.addEventListener("click", (e) => {
            document.querySelectorAll(".nav-links li").forEach(n => n.classList.remove("active"));
            e.currentTarget.classList.add("active");
            switchTab(e.currentTarget.dataset.tab);
        });
    });
});

// --- Auth flows ---
function checkAuth() {
    const token = localStorage.getItem("auth_token");
    const userStr = localStorage.getItem("auth_user");
    if (token && userStr) {
        currentToken = token;
        currentUser = JSON.parse(userStr);
    } else {
        currentToken = null;
        currentUser = { name: "Public User", role: "guest" };
    }
    showDashboard();
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    
    showLoader();
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (data.success) {
            currentToken = data.data.access_token;
            currentUser = data.data.user;
            localStorage.setItem("auth_token", currentToken);
            localStorage.setItem("auth_user", JSON.stringify(currentUser));
            eErrorMsg.classList.add("hidden");
            eAuthModal.classList.add("hidden");
            showDashboard();
        } else {
            eErrorMsg.textContent = data.error.message;
            eErrorMsg.classList.remove("hidden");
        }
    } catch (err) {
        eErrorMsg.textContent = "Server error. Ensure backend is running.";
        eErrorMsg.classList.remove("hidden");
    }
    hideLoader();
}

function logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    currentToken = null;
    currentUser = { name: "Public User", role: "guest" };
    showDashboard();
}

// --- View Handling ---
function showDashboard() {
    // Set Profile
    document.getElementById("user-name").textContent = currentUser.name;
    document.getElementById("user-role").textContent = (currentUser.role === 'admin') ? 'Administrator' : 'Guest';
    document.getElementById("user-role").className = (currentUser.role === 'admin') ? 'badge admin-badge' : 'badge';
    
    // Toggle Login/Logout buttons
    const isAdmin = currentUser.role === "admin";
    eAdminLoginBtn.classList.toggle("hidden", isAdmin);
    eLogoutBtn.classList.toggle("hidden", !isAdmin);
    
    // Adjust Permissions
    document.querySelectorAll(".admin-only").forEach(el => el.classList.toggle("hidden", !isAdmin));
    
    switchTab("summary");
    loadSummaryData();
}

function switchTab(tabID) {
    document.querySelectorAll(".tab-pane").forEach(tp => tp.classList.add("hidden"));
    document.getElementById(`tab-${tabID}`).classList.remove("hidden");
    
    const titles = {
        "summary": "Dashboard Summary",
        "recent": "Recent Activity",
        "charts": "Financial Analytics",
        "manage": "Add Transaction",
    };
    document.getElementById("current-view-title").textContent = titles[tabID];
    
    // Lazy load data based on tab
    if (tabID === "summary") loadSummaryData();
    if (tabID === "recent") loadRecentActivity();
    if (tabID === "charts") loadAnalytics();
}

function showLoader() { eLoader.classList.remove("hidden"); }
function hideLoader() { eLoader.classList.add("hidden"); }

// --- API Helpers ---
async function apiGet(path) {
    const headers = {};
    if (currentToken) {
        headers["Authorization"] = `Bearer ${currentToken}`;
    }
    const res = await fetch(`${API_BASE}${path}`, { headers });
    // If we get an unauthorized for something that used to work, logout
    if (res.status === 401 && currentToken) return logout();
    return await res.json();
}

async function apiPost(path, body) {
    const headers = { "Content-Type": "application/json" };
    if (currentToken) {
        headers["Authorization"] = `Bearer ${currentToken}`;
    }
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body)
    });
    if (res.status === 401 && currentToken) return logout();
    return await res.json();
}

// --- Feature: Summary View ---
async function loadSummaryData() {
    showLoader();
    const res = await apiGet("/analytics/summary");
    if (res && res.success) {
        document.getElementById("kpi-income").textContent = `₹${res.data.total_income.toLocaleString(undefined, {minimumFractionDigits:2})}`;
        document.getElementById("kpi-expense").textContent = `₹${res.data.total_expenses.toLocaleString(undefined, {minimumFractionDigits:2})}`;
        document.getElementById("kpi-balance").textContent = `₹${res.data.net_balance.toLocaleString(undefined, {minimumFractionDigits:2})}`;
        document.getElementById("kpi-count").textContent = res.data.transaction_count;
    }

    // Fetch Trend
    const trendRes = await apiGet("/analytics/trend");
    if (trendRes && trendRes.success) {
        const trend = trendRes.data;
        const trendEl = document.getElementById("kpi-trend-val");
        const trendIcon = document.getElementById("kpi-trend-icon");
        
        trendEl.textContent = trend.message;
        
        // Color coding: Expenses Up (bad/danger) vs Down (good/income)
        // Wait, trend is based on expenses.
        if (trend.direction === 'up') {
            trendIcon.className = "kpi-icon expense"; // Red
            trendEl.style.color = "var(--danger)";
        } else if (trend.direction === 'down') {
            trendIcon.className = "kpi-icon income"; // Green
            trendEl.style.color = "var(--success)";
        } else {
            trendIcon.className = "kpi-icon net"; // Neutral
            trendEl.style.color = "var(--text-dim)";
        }
    }
    hideLoader();
}

// --- Feature: Recent Activity ---
async function loadRecentActivity() {
    showLoader();
    const res = await apiGet("/analytics/recent");
    if (res && res.success) {
        const tbody = document.getElementById("recent-tbody");
        tbody.innerHTML = "";
        const isAdmin = (currentUser && currentUser.role === 'admin');
        
        // Show/hide actions column header
        document.querySelectorAll(".admin-only").forEach(el => el.classList.toggle("hidden", !isAdmin));

        res.data.transactions.forEach(t => {
            const tr = document.createElement("tr");
            tr.className = t.type === 'income' ? 'row-income' : 'row-expense';
            const sym = t.type === 'income' ? '+' : '-';
            
            let rowHtml = `
                <td>${t.date}</td>
                <td><span style="text-transform:capitalize;">${t.category}</span></td>
                <td>${t.notes || '-'}</td>
                <td>${sym}₹${t.amount.toLocaleString(undefined, {minimumFractionDigits:2})}</td>
                <td>₹${t.balance_after.toLocaleString(undefined, {minimumFractionDigits:2})}</td>
            `;
            
            if (isAdmin) {
                rowHtml += `
                <td class="td-actions">
                    <button class="btn-icon" onclick='openEditModal(${escapeHtml(JSON.stringify(t))})' title="Edit"><i class="fa-solid fa-pen text-primary"></i></button>
                    <button class="btn-icon" onclick="deleteTransaction(${t.id})" title="Delete"><i class="fa-solid fa-trash text-danger"></i></button>
                </td>
                `;
            }
            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        });
    }
    hideLoader();
}

function escapeHtml(unsafe) {
    return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// --- Feature: Analytics (Charts) ---
async function loadAnalytics() {
    showLoader();
    const monthlyRes = await apiGet("/analytics/monthly");
    if (monthlyRes && monthlyRes.success) {
        renderMonthlyChart(monthlyRes.data);
    }
    const catRes = await apiGet("/analytics/category");
    if (catRes && catRes.success) {
        renderPieChart("incomePieChart", "Income Categories", catRes.data.income);
        renderPieChart("expensePieChart", "Expense Categories", catRes.data.expenses);
    }
    hideLoader();
}

// --- Feature: Manage (Create Transaction) ---
async function handleCreateTransaction(e) {
    e.preventDefault();
    const msgEl = document.getElementById("form-msg");
    const payload = {
        amount: parseFloat(document.getElementById("txn-amount").value),
        type: document.getElementById("txn-type").value,
        category: document.getElementById("txn-category").value,
        date: document.getElementById("txn-date").value,
        notes: document.getElementById("txn-notes").value || null
    };
    showLoader();
    const res = await apiPost("/transactions", payload);
    hideLoader();
    msgEl.classList.remove("hidden");
    if (res.success) {
        msgEl.className = "msg success-msg";
        msgEl.textContent = "Transaction created successfully!";
        e.target.reset();
        loadSummaryData();
    } else {
        msgEl.className = "msg error-msg";
        msgEl.textContent = res.error.message;
    }
}

// --- Feature: Download Report ---
async function downloadReport() {
    const format = document.getElementById("report-format").value;
    const btn = document.getElementById("download-report-btn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
    try {
        const headers = {};
        if (currentToken) headers["Authorization"] = `Bearer ${currentToken}`;
        
        const res = await fetch(`${API_BASE}/transactions/export?format=${format}`, { headers });
        if (res.status === 401 && currentToken) { logout(); return; }
        if (!res.ok) { alert("Failed to generate report."); return; }
        
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `finance_report_${new Date().toISOString().slice(0, 10)}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        alert("Error downloading report: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-download"></i> Download Report';
    }
}

// --- Admin Features: Edit / Delete ---
async function deleteTransaction(id) {
    if (!currentToken) return alert("Admin login required");
    if (!confirm("Are you sure?")) return;
    showLoader();
    const res = await fetch(`${API_BASE}/transactions/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (res.ok || res.status === 204) {
        loadRecentActivity();
    } else {
        alert("Delete failed.");
    }
    hideLoader();
}

function openEditModal(txn) {
    if (!currentToken) return alert("Admin login required");
    document.getElementById("edit-modal").classList.remove("hidden");
    document.getElementById("edit-id").value = txn.id;
    document.getElementById("edit-amount").value = txn.amount;
    document.getElementById("edit-type").value = txn.type;
    document.getElementById("edit-category").value = txn.category;
    document.getElementById("edit-date").value = txn.date;
    document.getElementById("edit-notes").value = txn.notes || "";
    document.getElementById("edit-msg").classList.add("hidden");
}

async function submitEditTransaction(e) {
    e.preventDefault();
    const id = document.getElementById("edit-id").value;
    const msgEl = document.getElementById("edit-msg");
    const payload = {
        amount: parseFloat(document.getElementById("edit-amount").value),
        type: document.getElementById("edit-type").value,
        category: document.getElementById("edit-category").value,
        date: document.getElementById("edit-date").value,
        notes: document.getElementById("edit-notes").value || null
    };
    showLoader();
    const res = await fetch(`${API_BASE}/transactions/${id}`, {
        method: "PUT",
        headers: {
            "Authorization": `Bearer ${currentToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
    hideLoader();
    msgEl.classList.remove("hidden");
    if (res.ok) {
        msgEl.className = "msg success-msg";
        msgEl.textContent = "Updated!";
        setTimeout(() => {
            document.getElementById("edit-modal").classList.add("hidden");
            loadRecentActivity();
        }, 1000);
    } else {
        const err = await res.json();
        msgEl.className = "msg error-msg";
        msgEl.textContent = err.error ? err.error.message : "Update failed";
    }
}

// --- Chart Rendering ---
Chart.defaults.color = "#94a3b8";
Chart.defaults.font.family = "'Inter', sans-serif";

function renderMonthlyChart(data) {
    const ctx = document.getElementById("monthlyChart").getContext("2d");
    if (charts.monthly) charts.monthly.destroy();
    charts.monthly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.month),
            datasets: [
                { label: 'Income', data: data.map(d => d.income), backgroundColor: 'rgba(16, 185, 129, 0.8)', borderRadius: 4 },
                { label: 'Expenses', data: data.map(d => d.expenses), backgroundColor: 'rgba(239, 68, 68, 0.8)', borderRadius: 4 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }
    });
}

function renderPieChart(canvasId, title, items) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    if (charts[canvasId]) charts[canvasId].destroy();
    charts[canvasId] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: items.map(d => d.category.charAt(0).toUpperCase() + d.category.slice(1)),
            datasets: [{ data: items.map(d => d.total), backgroundColor: ['#8b5cf6', '#38bdf8', '#ec4899', '#10b981', '#f59e0b', '#ef4444', '#64748b'], borderWidth: 0 }]
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'right' } } }
    });
}
