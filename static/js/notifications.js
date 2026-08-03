document.addEventListener('DOMContentLoaded', () => {
    const listEl = document.getElementById('notificationsList');
    const unreadBadge = document.getElementById('unreadBadge');
    const searchInput = document.getElementById('notificationSearch');
    const startDateInput = document.getElementById('notificationStartDate');
    const endDateInput = document.getElementById('notificationEndDate');
    const filterDateBtn = document.getElementById('filterDateBtn');
    const groupByCategoryBtn = document.getElementById('groupByCategoryBtn');
    const unreadOnlyBtn = document.getElementById('unreadOnlyBtn');
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    const refreshBtn = document.getElementById('refreshNotificationsBtn');

    let allNotifications = [];
    let unreadOnly = false;
    let groupByCategory = false;
    let appliedStartDate = '';
    let appliedEndDate = '';

    const TYPE_ORDER = [
        'nfm_reported',
        'nfm_fixed',
        'absence_created',
        'schedule_confirmed',
        'weekend_confirmed',
        'rest_days_updated',
    ];

    const TYPE_CONFIG = {
        nfm_reported: { label: 'Machine en panne', icon: 'fa-exclamation-triangle' },
        nfm_fixed: { label: 'Machine réparée', icon: 'fa-wrench' },
        absence_created: { label: 'Absences', icon: 'fa-user-clock' },
        schedule_confirmed: { label: 'Planning confirmé', icon: 'fa-calendar-check' },
        weekend_confirmed: { label: 'Programme week-end', icon: 'fa-calendar-week' },
        rest_days_updated: { label: 'Jours de repos', icon: 'fa-bed' },
    };

    const EMAIL_STATUS_CONFIG = {
        pending: { label: 'Email en attente', icon: 'fa-clock' },
        sent: { label: 'Email envoyé', icon: 'fa-paper-plane' },
        failed: { label: 'Email échoué', icon: 'fa-exclamation-circle' },
        skipped: { label: 'Email ignoré', icon: 'fa-envelope' },
    };

    const READ_STATUS_CONFIG = {
        unread: { label: 'Marquer comme lu' },
        read: { label: 'Lu' },
    };

    function getTypeConfig(type) {
        return TYPE_CONFIG[type] || { label: type, icon: 'fa-bell' };
    }

    function getTypeClass(type) {
        return TYPE_CONFIG[type] ? `notif-type-${type}` : 'notif-type-default';
    }

    function formatTime(timeStr) {
        if (!timeStr) {
            return '';
        }
        return timeStr.slice(0, 5);
    }

    function formatDateLabel(dateStr) {
        if (!dateStr) {
            return '';
        }
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return dateStr;
    }

    function getDisplayTitle(notification) {
        const title = notification.title || '';
        const prefixes = {
            absence_created: /^Absence enregistrée\s*:\s*/i,
            schedule_confirmed: /^Planning confirmé\s*[—-]\s*/i,
            nfm_reported: /^Machine en panne\s*:\s*/i,
            nfm_fixed: /^Machine réparée\s*:\s*/i,
            weekend_confirmed: /^Programme week-end confirmé\s*[—-]\s*/i,
            rest_days_updated: /^Jours de repos mis à jour\s*[—-]\s*/i,
        };

        let display = title;
        if (prefixes[notification.type]) {
            display = title.replace(prefixes[notification.type], '').trim();
        }
        return display || title;
    }

    function formatNotificationDate(dateStr, timeStr) {
        const dateLabel = formatDateLabel(dateStr);
        const timeLabel = formatTime(timeStr);
        if (dateLabel && timeLabel) {
            return `${dateLabel} · ${timeLabel}`;
        }
        return dateLabel || timeLabel;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function buildQuery() {
        const params = new URLSearchParams();
        if (unreadOnly) {
            params.set('unread_only', 'true');
        }
        const query = params.toString();
        return query ? `?${query}` : '';
    }

    function updateUnreadBadge(count) {
        if (count > 0) {
            unreadBadge.textContent = count;
            unreadBadge.style.display = 'inline-block';
        } else {
            unreadBadge.style.display = 'none';
        }
    }

    function initializeDateRange() {
        if (startDateInput && !startDateInput.value) {
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
        }
        if (endDateInput && !endDateInput.value) {
            endDateInput.value = new Date().toISOString().split('T')[0];
        }
    }

    function filterByDateRange(notifications) {
        if (!appliedStartDate && !appliedEndDate) {
            return notifications;
        }
        return notifications.filter((notification) => {
            const notificationDate = notification.date || '';
            if (!notificationDate) {
                return false;
            }
            if (appliedStartDate && appliedEndDate) {
                return notificationDate >= appliedStartDate && notificationDate <= appliedEndDate;
            }
            if (appliedStartDate) {
                return notificationDate >= appliedStartDate;
            }
            if (appliedEndDate) {
                return notificationDate <= appliedEndDate;
            }
            return true;
        });
    }

    function applyDateFilter() {
        const startDate = startDateInput ? startDateInput.value : '';
        const endDate = endDateInput ? endDateInput.value : '';

        if (startDate && endDate && startDate > endDate) {
            alert('La date de début doit être antérieure à la date de fin.');
            return;
        }

        appliedStartDate = startDate;
        appliedEndDate = endDate;
        renderNotificationsList(allNotifications);
    }

    function filterBySearch(notifications) {
        const query = searchInput.value.trim().toLowerCase();
        if (!query) {
            return notifications;
        }
        return notifications.filter((notification) => {
            const typeLabel = getTypeConfig(notification.type).label.toLowerCase();
            const displayTitle = getDisplayTitle(notification).toLowerCase();
            return (
                notification.title.toLowerCase().includes(query) ||
                displayTitle.includes(query) ||
                (notification.description || '').toLowerCase().includes(query) ||
                typeLabel.includes(query)
            );
        });
    }

    function applyFilters(notifications) {
        return filterBySearch(filterByDateRange(notifications));
    }

    function hasActiveFilters() {
        return Boolean(
            searchInput.value.trim()
            || appliedStartDate
            || appliedEndDate
        );
    }

    function sortNotifications(notifications) {
        return [...notifications].sort((a, b) => {
            const dateA = `${a.date} ${a.time}`;
            const dateB = `${b.date} ${b.time}`;
            return dateB.localeCompare(dateA);
        });
    }

    function groupNotificationsByType(notifications) {
        const grouped = {};
        notifications.forEach((notification) => {
            if (!grouped[notification.type]) {
                grouped[notification.type] = [];
            }
            grouped[notification.type].push(notification);
        });

        return Object.keys(grouped)
            .sort((a, b) => {
                const indexA = TYPE_ORDER.indexOf(a);
                const indexB = TYPE_ORDER.indexOf(b);
                if (indexA === -1 && indexB === -1) {
                    return a.localeCompare(b);
                }
                if (indexA === -1) {
                    return 1;
                }
                if (indexB === -1) {
                    return -1;
                }
                return indexA - indexB;
            })
            .map((type) => ({
                type,
                items: sortNotifications(grouped[type]),
            }));
    }

    function renderActionSlot(className, iconClass, title) {
        return `
            <span class="notif-slot ${className}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}">
                <i class="fas ${iconClass}"></i>
            </span>
        `;
    }

    function renderNotificationItem(notification) {
        const unreadClass = notification.is_read ? '' : ' unread';
        const typeConfig = getTypeConfig(notification.type);
        const emailConfig = EMAIL_STATUS_CONFIG[notification.email_status] || {
            label: notification.email_status,
            icon: 'fa-envelope',
        };
        const readKey = notification.is_read ? 'read' : 'unread';
        const readLabel = READ_STATUS_CONFIG[readKey].label;
        const dateLabel = formatNotificationDate(notification.date, notification.time);
        const displayTitle = notification.display_title || getDisplayTitle(notification);

        const markReadBtn = notification.is_read
            ? `<span class="notif-slot notif-slot-read" title="${escapeHtml(readLabel)}" aria-label="${escapeHtml(readLabel)}"><i class="bx bx-check"></i></span>`
            : `<button type="button" class="notif-slot notif-slot-mark" data-action="mark-read" data-id="${notification.id}" title="${escapeHtml(readLabel)}" aria-label="${escapeHtml(readLabel)}"><i class="bx bx-check"></i></button>`;

        return `
            <article class="notification-item${unreadClass}" data-id="${notification.id}">
                <div class="notification-type-icon notif-type-blue" title="${escapeHtml(typeConfig.label)}" aria-label="${escapeHtml(typeConfig.label)}">
                    <i class="fas ${typeConfig.icon}"></i>
                </div>
                <div class="notification-content">
                    <h5 class="notification-title">${escapeHtml(displayTitle)}</h5>
                    <p class="notification-description">${escapeHtml(notification.description || '—')}</p>
                </div>
                ${dateLabel ? `<span class="notification-date">${escapeHtml(dateLabel)}</span>` : ''}
                <div class="notification-actions-row">
                    ${renderActionSlot(`notif-email-${notification.email_status}`, emailConfig.icon, emailConfig.label)}
                    ${markReadBtn}
                    <button type="button" class="notif-slot notif-slot-delete" data-action="delete" data-id="${notification.id}" title="Supprimer" aria-label="Supprimer">
                        <i class="bx bx-x"></i>
                    </button>
                </div>
            </article>
        `;
    }

    function renderEmptyState(message) {
        listEl.innerHTML = `
            <div class="empty-notifications-state text-center py-5">
                <i class="fas fa-bell-slash fa-2x mb-3 text-muted"></i>
                <p class="text-muted mb-0">${escapeHtml(message)}</p>
            </div>
        `;
    }

    function renderNotificationsList(notifications) {
        const filtered = applyFilters(notifications);

        if (!filtered.length) {
            renderEmptyState(
                hasActiveFilters()
                    ? 'Aucune notification ne correspond à vos critères.'
                    : 'Aucune notification.'
            );
            return;
        }

        if (groupByCategory) {
            const groups = groupNotificationsByType(filtered);
            listEl.innerHTML = groups.map(({ type, items }) => {
                const typeConfig = getTypeConfig(type);
                return `
                    <section class="notification-category-section">
                        <div class="notification-category-header">
                            <div class="notification-category-icon notif-type-blue">
                                <i class="fas ${typeConfig.icon}"></i>
                            </div>
                            <h4 class="notification-category-title">${escapeHtml(typeConfig.label)}</h4>
                            <span class="notification-category-count">${items.length}</span>
                        </div>
                        <div class="notification-category-items">
                            ${items.map(renderNotificationItem).join('')}
                        </div>
                    </section>
                `;
            }).join('');
            return;
        }

        listEl.innerHTML = sortNotifications(filtered).map(renderNotificationItem).join('');
    }

    function loadNotifications() {
        fetch(`/api/notifications${buildQuery()}`)
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.message || 'Erreur lors du chargement');
                }
                allNotifications = data.notifications;
                renderNotificationsList(allNotifications);
                updateUnreadBadge(data.unread_count);
            })
            .catch(err => {
                listEl.innerHTML = `
                    <div class="alert alert-danger mb-0">${escapeHtml(err.message)}</div>
                `;
            });
    }

    function markAsRead(id) {
        fetch(`/api/notifications/${id}/read`, { method: 'PUT' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                } else {
                    alert(data.message || 'Erreur');
                }
            });
    }

    function deleteNotification(id) {
        if (!confirm('Supprimer cette notification ?')) {
            return;
        }
        fetch(`/api/notifications/${id}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                } else {
                    alert(data.message || 'Erreur');
                }
            });
    }

    listEl.addEventListener('click', (event) => {
        const button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        const id = button.dataset.id;
        if (button.dataset.action === 'mark-read') {
            markAsRead(id);
        } else if (button.dataset.action === 'delete') {
            deleteNotification(id);
        }
    });

    searchInput.addEventListener('input', () => {
        renderNotificationsList(allNotifications);
    });

    if (filterDateBtn) {
        filterDateBtn.addEventListener('click', applyDateFilter);
    }

    initializeDateRange();
    appliedStartDate = startDateInput ? startDateInput.value : '';
    appliedEndDate = endDateInput ? endDateInput.value : '';

    groupByCategoryBtn.addEventListener('click', () => {
        groupByCategory = !groupByCategory;
        groupByCategoryBtn.classList.toggle('active', groupByCategory);
        renderNotificationsList(allNotifications);
    });

    unreadOnlyBtn.addEventListener('click', () => {
        unreadOnly = !unreadOnly;
        unreadOnlyBtn.classList.toggle('active', unreadOnly);
        loadNotifications();
    });

    refreshBtn.addEventListener('click', loadNotifications);

    markAllReadBtn.addEventListener('click', () => {
        fetch('/api/notifications/read-all', { method: 'PUT' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                } else {
                    alert(data.message || 'Erreur');
                }
            });
    });

    loadNotifications();
});
