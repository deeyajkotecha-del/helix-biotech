/**
 * Helix Authentication JavaScript
 */

const API_BASE = '/api';

// Tab switching
document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        // Update tabs
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        this.classList.add('active');

        // Update forms
        const targetForm = this.dataset.tab;
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.remove('active');
        });
        document.getElementById(`${targetForm}-form`).classList.add('active');

        // Clear messages
        hideMessages();
    });
});

function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.classList.add('show');
    document.getElementById('success-message').classList.remove('show');
}

function showSuccess(message) {
    const successEl = document.getElementById('success-message');
    successEl.textContent = message;
    successEl.classList.add('show');
    document.getElementById('error-message').classList.remove('show');
}

function hideMessages() {
    document.getElementById('error-message').classList.remove('show');
    document.getElementById('success-message').classList.remove('show');
}

function saveToken(token) {
    localStorage.setItem('helix_token', token);
}

function getToken() {
    return localStorage.getItem('helix_token');
}

// Login form
document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    hideMessages();

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const submitBtn = this.querySelector('button[type="submit"]');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in...';

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (response.ok) {
            saveToken(data.access_token);
            showSuccess('Login successful! Redirecting...');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        } else {
            showError(data.detail || 'Login failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Log In';
    }
});

// Signup form
document.getElementById('signup-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    hideMessages();

    const fullName = document.getElementById('signup-name').value;
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const submitBtn = this.querySelector('button[type="submit"]');

    if (password.length < 8) {
        showError('Password must be at least 8 characters');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating account...';

    try {
        const response = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
                full_name: fullName || null,
            }),
        });

        const data = await response.json();

        if (response.ok) {
            saveToken(data.access_token);
            showSuccess('Account created! Redirecting...');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        } else {
            showError(data.detail || 'Signup failed');
        }
    } catch (error) {
        showError('Network error. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
    }
});

// Check if already logged in
if (getToken()) {
    // Verify token is still valid
    fetch(`${API_BASE}/auth/me`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`,
        },
    }).then(response => {
        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            localStorage.removeItem('helix_token');
        }
    }).catch(() => {
        // Network error, stay on login page
    });
}
