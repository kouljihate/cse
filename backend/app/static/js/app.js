const API_BASE = '/api';

async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const res = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers,
    });

    if (res.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return;
    }

    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        return res.json();
    }
    return res;
}

async function login(username, password) {
    const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
    }
    return data;
}

async function logout() {
    try {
        await apiRequest('/auth/logout', { method: 'POST' });
    } catch (_) {}
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem('user'));
    } catch {
        return null;
    }
}

function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) {
        const div = document.createElement('div');
        div.id = 'toast-container';
        div.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        div.style = 'z-index: 9999';
        document.body.appendChild(div);
    }
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.getElementById('toast-container').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function formatDate(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyy = d.getFullYear();
        const hh = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        const ss = String(d.getSeconds()).padStart(2, '0');
        const formatted = dd + '/' + mm + '/' + yyyy + ' ' + hh + ':' + min + ':' + ss;
        if (document.documentElement.lang === 'ar') {
            return '<span dir="ltr" class="western-nums">' + formatted + '</span>';
        }
        return formatted;
    } catch {
        return iso;
    }
}

let socket = null;
window.onlineUserIds = new Set();

function initSocketIO() {
    const token = localStorage.getItem('access_token');
    if (!token || socket) return;

    socket = io({
        query: { token },
        transports: ['websocket', 'polling'],
    });

    socket.on('notification', function (data) {
        showToast(data.title || 'New notification', 'info');
        if (typeof updateNotificationBadge === 'function') {
            updateNotificationBadge();
        }
        if (window.location.pathname === '/notifications' && typeof loadNotificationsPage === 'function') {
            loadNotificationsPage();
        }
        if (data.type && data.type.startsWith('activity_') && window.location.pathname === '/activities' && typeof loadActivities === 'function') {
            loadActivities();
        }
        if (window.location.pathname === '/audit' && typeof loadAudit === 'function') {
            loadAudit();
        }
    });

    socket.on('notification_badge', function (data) {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    });

    socket.on('online_users', function (data) {
        window.onlineUserIds = new Set(data.user_ids || []);
    });

    socket.on('disconnect', function () {
        window.onlineUserIds = new Set();
    });
}

async function sendNotification(userId, message, title) {
    return apiRequest('/activities/notifications/send', {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, message: message, title: title || 'Notification' }),
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const lang = document.documentElement.lang || localStorage.getItem('lang') || 'en';
    document.documentElement.lang = lang;
    if (lang === 'ar') {
        document.documentElement.dir = 'rtl';
    }
    localStorage.setItem('lang', lang);
    if (isAuthenticated()) initSocketIO();
});
