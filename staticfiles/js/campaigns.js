/**
 * Campaigns AJAX Handler
 * Replaces HTMX functionality with vanilla JavaScript fetch API
 */

document.addEventListener('DOMContentLoaded', function () {
    initializeAjaxForms();
    initializeIntervalPreview();
});

/**
 * Initialize all forms with data-ajax attribute to submit via fetch
 */
function initializeAjaxForms() {
    document.body.addEventListener('submit', async function (e) {
        const form = e.target.closest('form[data-ajax]');
        if (!form) return;

        e.preventDefault();

        const formData = new FormData(form);
        const targetSelector = form.dataset.target;
        const swapMethod = form.dataset.swap || 'innerHTML';
        const submitBtn = form.querySelector('button[type="submit"]');

        // Disable submit button and show loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.dataset.originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
        }

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success && data.html) {
                const target = document.querySelector(targetSelector);
                if (target) {
                    if (swapMethod === 'outerHTML') {
                        target.outerHTML = data.html;
                    } else {
                        target.innerHTML = data.html;
                    }
                }

                // Close modal if open
                closeOpenModals();

                // Reinitialize event handlers for dynamically added content
                initializeIntervalPreview();
                initializeTooltips();
            } else if (data.error) {
                console.error('Server error:', data.error);
                showToast('Error: ' + data.error, 'danger');
            }

        } catch (error) {
            console.error('Form submission error:', error);
            showToast('An error occurred. Please try again.', 'danger');
        } finally {
            // Restore submit button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.dataset.originalText;
            }
        }
    });
}

/**
 * Close all open Bootstrap modals and clean up backdrops
 */
function closeOpenModals() {
    const openModal = document.querySelector('.modal.show');
    if (openModal) {
        const modalInstance = bootstrap.Modal.getInstance(openModal);
        if (modalInstance) modalInstance.hide();
    }

    // Clean up any remaining backdrops
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
}

/**
 * Show a Bootstrap toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1100';
        document.body.appendChild(toastContainer);
    }

    const toastHTML = `
        <div class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastEl = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();

    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

/**
 * Initialize interval preview functionality for time input groups
 */
function initializeIntervalPreview() {
    document.querySelectorAll('[data-interval-group]').forEach(group => {
        const previewElement = group.querySelector('[data-interval-preview]');
        if (!previewElement) return;

        const inputs = group.querySelectorAll('input[type="number"]');

        const updatePreview = () => {
            const hours = group.querySelector('[name*="hours"]')?.value || 0;
            const minutes = group.querySelector('[name*="minutes"]')?.value || 0;
            const seconds = group.querySelector('[name*="seconds"]')?.value || 0;
            previewElement.textContent = humanizeInterval(hours, minutes, seconds);
        };

        inputs.forEach(input => {
            input.addEventListener('input', updatePreview);
        });

        // Initial update
        updatePreview();
    });
}

/**
 * Humanize time interval to readable string
 */
function humanizeInterval(hours, minutes, seconds) {
    const totalSeconds = (parseInt(hours) || 0) * 3600 + (parseInt(minutes) || 0) * 60 + (parseInt(seconds) || 0);
    if (totalSeconds < 30) return 'Minimum 30 seconds';

    const duration = moment.duration(totalSeconds, 'seconds');
    const parts = [];

    if (duration.hours() > 0) parts.push(duration.hours() + ' hour' + (duration.hours() > 1 ? 's' : ''));
    if (duration.minutes() > 0) parts.push(duration.minutes() + ' minute' + (duration.minutes() > 1 ? 's' : ''));
    if (duration.seconds() > 0) parts.push(duration.seconds() + ' second' + (duration.seconds() > 1 ? 's' : ''));

    if (parts.length === 0) return 'Not set';
    if (parts.length === 1) return 'Every ' + parts[0];
    if (parts.length === 2) return 'Every ' + parts.join(' and ');
    return 'Every ' + parts.slice(0, -1).join(', ') + ', and ' + parts[parts.length - 1];
}
