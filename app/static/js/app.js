// Frontend logic for task CRUD, analytics refresh, and live updates.
const taskList = document.querySelector("#taskList");
const taskForm = document.querySelector("#taskForm");
const taskIdInput = document.querySelector("#taskId");
const titleInput = document.querySelector("#title");
const descriptionInput = document.querySelector("#description");
const priorityInput = document.querySelector("#priority");
const statusInput = document.querySelector("#status");
const saveButton = document.querySelector("#saveButton");
const resetButton = document.querySelector("#resetButton");
const liveStatus = document.querySelector("#liveStatus");

const api = {
    async request(path, options = {}) {
        const response = await fetch(path, {
            headers: { "Content-Type": "application/json", ...(options.headers || {}) },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || "Request failed");
        }

        return response.json();
    },
    getTasks: () => api.request("/api/tasks"),
    getAnalytics: () => api.request("/api/analytics"),
    createTask: (task) => api.request("/api/tasks", { method: "POST", body: JSON.stringify(task) }),
    updateTask: (id, task) => api.request(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(task) }),
    deleteTask: (id) => api.request(`/api/tasks/${id}`, { method: "DELETE" }),
};

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function badgeClass(value) {
    return String(value).toLowerCase().replaceAll(" ", "-");
}

function formatDate(value) {
    return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function taskTemplate(task) {
    return `
        <article class="task-card" data-id="${task.id}">
            <header>
                <div>
                    <h3>${escapeHtml(task.title)}</h3>
                    <p>${escapeHtml(task.description || "No description")}</p>
                </div>
                <div class="task-actions">
                    <button type="button" data-action="edit">Edit</button>
                    <button type="button" class="delete" data-action="delete">Delete</button>
                </div>
            </header>
            <div class="task-meta">
                <span class="badge ${badgeClass(task.priority)}">${escapeHtml(task.priority)}</span>
                <span class="badge ${badgeClass(task.status)}">${escapeHtml(task.status)}</span>
                <span class="badge">Created ${formatDate(task.created_date)}</span>
            </div>
        </article>
    `;
}

async function loadTasks() {
    const tasks = await api.getTasks();
    taskList.innerHTML = tasks.length
        ? tasks.map(taskTemplate).join("")
        : '<div class="empty-state">No tasks yet. Add your first task.</div>';
}

async function loadAnalytics() {
    const analytics = await api.getAnalytics();
    Object.entries(analytics).forEach(([key, value]) => {
        const element = document.querySelector(`[data-key="${key}"]`);
        if (element) {
            element.textContent = value;
        }
    });
}

async function refreshDashboard() {
    await Promise.all([loadTasks(), loadAnalytics()]);
}

function getFormTask() {
    return {
        title: titleInput.value.trim(),
        description: descriptionInput.value.trim(),
        priority: priorityInput.value,
        status: statusInput.value,
    };
}

function resetForm() {
    taskIdInput.value = "";
    taskForm.reset();
    priorityInput.value = "Medium";
    statusInput.value = "Pending";
    saveButton.textContent = "Add Task";
}

taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = taskIdInput.value;
    const task = getFormTask();

    if (id) {
        await api.updateTask(id, task);
    } else {
        await api.createTask(task);
    }

    resetForm();
    await refreshDashboard();
});

resetButton.addEventListener("click", resetForm);

taskList.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    const card = event.target.closest(".task-card");
    if (!button || !card) {
        return;
    }

    const id = card.dataset.id;
    const tasks = await api.getTasks();
    const task = tasks.find((item) => String(item.id) === String(id));

    if (button.dataset.action === "edit" && task) {
        taskIdInput.value = task.id;
        titleInput.value = task.title;
        descriptionInput.value = task.description;
        priorityInput.value = task.priority;
        statusInput.value = task.status;
        saveButton.textContent = "Update Task";
        titleInput.focus();
    }

    if (button.dataset.action === "delete") {
        await api.deleteTask(id);
        if (taskIdInput.value === id) {
            resetForm();
        }
        await refreshDashboard();
    }
});

const socket = io();

socket.on("connect", () => {
    liveStatus.textContent = "Live updates on";
});

socket.on("disconnect", () => {
    liveStatus.textContent = "Reconnecting...";
});

["task_created", "task_updated", "task_deleted"].forEach((eventName) => {
    socket.on(eventName, refreshDashboard);
});

refreshDashboard().catch((error) => {
    taskList.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
});
