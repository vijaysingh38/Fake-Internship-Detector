
console.log("JobGuard script.js loaded");

const $ = (id) => document.getElementById(id);

const API_URL = "/api/check";

const jobText = $("jobText");
const checkButton = $("checkButton");
const message = $("message");
const analysisSection = $("analysisSection");

function setText(id, value) {
    const element = $(id);
    if (element) element.textContent = value ?? "";
}

function showElement(id, visible) {
    const element = $(id);
    if (element) element.classList.toggle("hidden", !visible);
}

function showMessage(text, type = "info") {
    if (!message) return;

    message.textContent = text;
    message.className = `message ${type}`;
    message.classList.remove("hidden");
}

function setLoading(loading) {
    if (checkButton) checkButton.disabled = loading;

    const buttonText = $("buttonText");
    const spinner = $("buttonSpinner");

    if (buttonText) {
        buttonText.textContent = loading ? "Analysing..." : "Analyze job post";
    }

    if (spinner) {
        spinner.classList.toggle("hidden", !loading);
    }
}

// Character counter
function updateCharacterCount() {
    if (!jobText) return;

    const count = jobText.value.length;
    const max = jobText.maxLength || 20000;

    setText("characterCount", `${count} / ${max} characters`);
}

if (jobText) {
    jobText.addEventListener("input", updateCharacterCount);
    updateCharacterCount();
}

// Analyse button
if (checkButton) {
    checkButton.addEventListener("click", analyseJob);
}

async function analyseJob() {
    const text = jobText?.value.trim();

    if (!text) {
        showMessage("Please paste a job or internship post first.", "error");
        jobText?.focus();
        return;
    }

    setLoading(true);
    showMessage("Analysing the job post...", "info");

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = Array.isArray(data.detail)
                ? data.detail.map(item => item.msg).join(", ")
                : data.detail || data.error;

            throw new Error(detail || `Server error: ${response.status}`);
        }

        if (data.received === false) {
            throw new Error(data.error || "The job post could not be analysed.");
        }

        renderResults(data);

        showMessage("Analysis completed successfully.", "success");

    } catch (error) {
        console.error("JobGuard error:", error);

        showMessage(
            `Analysis failed: ${error.message}. Check that FastAPI is running on port 8000.`,
            "error"
        );
    } finally {
        setLoading(false);
    }
}

function renderResults(data) {
    const score = Math.max(
        0,
        Math.min(100, Number(data.risk_score) || 0)
    );

    const level = data.risk_level || "Unknown";
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    const links = Array.isArray(data.links_found) ? data.links_found : [];

    // Reveal the dashboard. Your HTML initially hides it with "hidden".
    if (analysisSection) {
        analysisSection.classList.remove("hidden");
    }

    // Overall result banner
    setText("riskBadge", `${level} Risk`);
    setText("riskSummary", `Risk score: ${score}/100`);
    setText("riskScore", `${score}/100`);
    setText("resultMessage", data.message || "Analysis finished.");

    const resultSymbol = $("resultSymbol");
    if (resultSymbol) {
        resultSymbol.textContent =
            level.toLowerCase() === "high" ? "!" :
            level.toLowerCase() === "medium" ? "⚠" : "✓";
    }

    const banner = $("resultBanner");
    if (banner) {
        banner.classList.remove(
            "risk-high",
            "risk-medium",
            "risk-low",
            "risk-unknown"
        );
        banner.classList.add(`risk-${level.toLowerCase()}`);
    }

    // ML results
    setText("mlPrediction", data.ml_prediction || "Unavailable");

    const probability = data.ml_fake_probability;
    setText(
        "mlProbability",
        probability === null || probability === undefined
            ? "Not available"
            : `${probability}%`
    );

    setText(
        "mlExplanation",
        data.ml_explanation ||
        "The ML prediction is an estimate, not proof that a post is fake."
    );

    // Overall risk donut
    setText("overallDonutScore", score);
    setText("riskLegendScore", `${score} / 100`);
    setText("remainingScore", 100 - score);

    const overallDonut = $("overallDonut");
    if (overallDonut) {
        overallDonut.style.background =
            `conic-gradient(#e5484d ${score * 3.6}deg, #e5e7eb 0deg)`;
    }

    // Warning statistics
    const seriousCount = warnings.filter(
        warning => (warning.severity || "").toLowerCase() === "high"
    ).length;

    setText("warningCount", warnings.length);
    setText("seriousCount", seriousCount);
    setText("linkCount", links.length);
    setText("warningHeadingCount", `${warnings.length} signals`);
    setText("severityTotal", warnings.length);

    // Warning severity donut and legend
    const highCount = warnings.filter(
        warning => (warning.severity || "").toLowerCase() === "high"
    ).length;

    const mediumCount = warnings.filter(
        warning => (warning.severity || "").toLowerCase() === "medium"
    ).length;

    const lowCount = warnings.filter(
        warning => (warning.severity || "").toLowerCase() === "low"
    ).length;

    const severityDonut = $("severityDonut");

    if (severityDonut) {
        const total = warnings.length || 1;
        const highEnd = highCount / total * 100;
        const mediumEnd = (highCount + mediumCount) / total * 100;

        severityDonut.style.background =
            `conic-gradient(
                #e5484d 0% ${highEnd}%,
                #e5a000 ${highEnd}% ${mediumEnd}%,
                #2da66f ${mediumEnd}% 100%
            )`;
    }

    const severityLegend = $("severityLegend");

    if (severityLegend) {
        severityLegend.replaceChildren();

        [
            ["High", highCount],
            ["Medium", mediumCount],
            ["Low", lowCount]
        ].forEach(([label, count]) => {
            const item = document.createElement("div");
            item.className = "chart-caption";

            const text = document.createElement("span");
            text.textContent = `${label} severity`;

            const value = document.createElement("strong");
            value.textContent = count;

            item.append(text, value);
            severityLegend.appendChild(item);
        });
    }

    // Render warning charts, details, links and disclaimer
    renderWarningBars(warnings);
    renderWarningDetails(warnings);
    renderLinks(links);

    setText("disclaimer", data.disclaimer || "");

    showElement("noWarnings", warnings.length === 0);

    // Scroll the results into view
    analysisSection?.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function renderWarningBars(warnings) {
    const container = $("warningBars");
    if (!container) return;

    container.replaceChildren();

    if (warnings.length === 0) {
        return;
    }

    warnings.forEach(warning => {
        const severity = (warning.severity || "low").toLowerCase();

        // Convert the rule weight to a display score out of 10.
        const weight = Number(warning.weight) || 0;
        const barScore = Math.min(10, Math.round(weight / 3.5 * 10) / 10);
        const barWidth = Math.min(100, weight / 35 * 100);

        const row = document.createElement("div");
        row.className = "warning-bar-row";

        const header = document.createElement("div");
        header.className = "warning-bar-header";

        const title = document.createElement("span");
        title.textContent = warning.title || "Warning signal";

        const value = document.createElement("strong");
        value.textContent = `${barScore}/10`;

        header.append(title, value);

        const track = document.createElement("div");
        track.className = "warning-bar";

        const fill = document.createElement("div");
        fill.className = `warning-bar-fill ${severity}`;
        fill.style.width = `${barWidth}%`;

        track.appendChild(fill);
        row.append(header, track);
        container.appendChild(row);
    });
}

function renderWarningDetails(warnings) {
    const container = $("allWarningsList");
    if (!container) return;

    container.replaceChildren();

    if (warnings.length === 0) {
        const empty = document.createElement("p");
        empty.textContent =
            "No warning signals were detected. This does not prove that the job is genuine.";
        container.appendChild(empty);
        return;
    }

    warnings.forEach(warning => {
        const severity = (warning.severity || "low").toLowerCase();

        const details = document.createElement("details");
        details.className = `warning-detail ${severity}`;

        const summary = document.createElement("summary");
        summary.textContent =
            `${warning.title || "Warning"} (${severity.toUpperCase()} risk)`;

        const body = document.createElement("div");
        body.className = "warning-detail-body";

        const reason = document.createElement("p");
        reason.textContent = warning.reason || "A warning pattern was detected.";

        const advice = document.createElement("p");
        advice.textContent = `What to do: ${
            warning.advice || "Verify the company independently before applying."
        }`;

        body.append(reason, advice);
        details.append(summary, body);
        container.appendChild(details);
    });
}

function renderLinks(links) {
    const container = $("linksList");
    if (!container) return;

    container.replaceChildren();

    if (links.length === 0) {
        const item = document.createElement("li");
        item.className = "empty-link";
        item.textContent = "No links found in the job post.";
        container.appendChild(item);
        return;
    }

    links.forEach(link => {
        const item = document.createElement("li");

        const address = document.createElement("span");
        address.textContent = link.url || link.domain || "Unknown link";
        item.appendChild(address);

        if (link.suspicious) {
            const warning = document.createElement("strong");
            warning.textContent = " — Check this link carefully";
            item.appendChild(warning);
        }

        container.appendChild(item);
    });
}
