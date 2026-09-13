const API_URL = "/api/incidents";

const incidentForm = document.getElementById("incidentForm");
const searchForm = document.getElementById("searchForm");
const searchInput = document.getElementById("search");
const refreshButton = document.getElementById("refreshButton");
const clearSearchButton = document.getElementById("clearSearchButton");
const formMessage = document.getElementById("formMessage");
const loadingState = document.getElementById("loadingState");
const emptyState = document.getElementById("emptyState");
const errorState = document.getElementById("errorState");
const incidentList = document.getElementById("incidentList");

function showState(state) {
    loadingState.hidden = state !== "loading";
    emptyState.hidden = state !== "empty";
    errorState.hidden = state !== "error";
    incidentList.hidden = state !== "list";
}

function showMessage(message, isError = false) {
    formMessage.textContent = message;
    formMessage.hidden = false;

    if (isError) {
        formMessage.classList.add("error-state");
    } else {
        formMessage.classList.remove("error-state");
    }
}

async function getErrorMessage(response) {
    try {
        const data = await response.json();

        if (typeof data.detail === "string") {
            return data.detail;
        }

        return "The request could not be completed.";
    } catch {
        return "The request could not be completed.";
    }
}

function createIncidentCard(incident) {
    const card = document.createElement("article");
    card.className = "incident-card";

    const title = document.createElement("h3");
    title.textContent = incident.title;

    const description = document.createElement("p");
    description.textContent = incident.description;

    const incidentId = document.createElement("p");
    incidentId.className = "incident-id";
    incidentId.textContent = `Incident ID: ${incident.id}`;

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.textContent = "Edit";
    editButton.addEventListener("click", () => {
        updateIncident(incident);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.className = "delete-button";
    deleteButton.addEventListener("click", () => {
        deleteIncident(incident);
    });

    actions.append(editButton, deleteButton);
    card.append(title, description, incidentId, actions);

    return card;
}

function displayIncidents(incidents) {
    incidentList.replaceChildren();

    if (incidents.length === 0) {
        showState("empty");
        return;
    }

    incidents.forEach((incident) => {
        incidentList.appendChild(createIncidentCard(incident));
    });

    showState("list");
}

async function loadIncidents(search = "") {
    showState("loading");

    try {
        const url = search
            ? `${API_URL}?search=${encodeURIComponent(search)}`
            : API_URL;

        const response = await fetch(url, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Unable to load incidents.");
        }

        const incidents = await response.json();
        displayIncidents(incidents);
    } catch (error) {
        console.error(error);
        showState("error");
    }
}

async function createIncident(event) {
    event.preventDefault();

    const title = document.getElementById("title").value.trim();
    const description = document
        .getElementById("description")
        .value
        .trim();

    if (!title || !description) {
        showMessage(
            "Enter both an incident title and description.",
            true
        );
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title,
                description
            })
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        window.location.href = "/";
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function updateIncident(incident) {
    const title = window.prompt(
        "Enter the updated incident title:",
        incident.title
    );

    if (title === null) {
        return;
    }

    const description = window.prompt(
        "Enter the updated incident description:",
        incident.description
    );

    if (description === null) {
        return;
    }

    if (!title.trim() || !description.trim()) {
        showMessage(
            "The title and description cannot be empty.",
            true
        );
        return;
    }

    try {
        const response = await fetch(
            `${API_URL}/${incident.id}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    title: title.trim(),
                    description: description.trim()
                })
            }
        );

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        window.location.href = "/";
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function deleteIncident(incident) {
    const confirmed = window.confirm(
        `Delete incident ${incident.id}: ${incident.title}?`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            `${API_URL}/${incident.id}`,
            {
                method: "DELETE"
            }
        );

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        window.location.href = "/";
    } catch (error) {
        showMessage(error.message, true);
    }
}

incidentForm.addEventListener("submit", createIncident);

searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadIncidents(searchInput.value.trim());
});

clearSearchButton.addEventListener("click", () => {
    searchInput.value = "";
    loadIncidents();
});

refreshButton.addEventListener("click", () => {
    loadIncidents(searchInput.value.trim());
});

document.addEventListener("DOMContentLoaded", () => {
    const parameters = new URLSearchParams(window.location.search);

    if (parameters.get("state") === "error") {
        showState("error");
        return;
    }

    loadIncidents();
});