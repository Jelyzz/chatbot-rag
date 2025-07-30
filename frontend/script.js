async function uploadFiles() {
    const files = document.getElementById("fileInput").files;
    const spinner = document.getElementById("spinnerFile");
    const message = document.getElementById("fileMessage");

    if (!files.length) {
        message.textContent = "Please select at least one file.";
        return;
    }

    spinner.style.display = "inline-block";
    message.textContent = "";

    const formData = new FormData();
    for (let file of files) {
        formData.append("files", file);
    }

    try {
        const res = await fetch("http://127.0.0.1:8002/upload_files/", {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        if (data.status === "success") {
            message.textContent = `✅ ${data.message}`;
        } else {
            message.textContent = "❌ " + JSON.stringify(data);
        }
    } catch (err) {
        message.textContent = "❌ Failed to upload files.";
    }

    spinner.style.display = "none";
}

async function uploadURL() {
    const url = document.getElementById("urlInput").value;
    const spinner = document.getElementById("spinnerURL");
    const message = document.getElementById("urlMessage");

    if (!url) {
        message.textContent = "Please enter a URL.";
        return;
    }

    spinner.style.display = "inline-block";
    message.textContent = "";

    try {
        const res = await fetch("http://127.0.0.1:8002/upload_url/", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `url=${encodeURIComponent(url)}`
        });

        const data = await res.json();
        if (data.status === "success") {
            message.textContent = `✅ ${data.message}`;
        } else {
            message.textContent = "❌ " + (data.error || "Unknown error");
        }
    } catch (err) {
        message.textContent = "❌ Failed to upload URL.";
    }

    spinner.style.display = "none";
}

async function askQuestion() {
    const question = document.getElementById("questionInput").value;
    const spinner = document.getElementById("spinnerAsk");
    const message = document.getElementById("askMessage");

    if (!question) {
        message.textContent = "Please enter a question.";
        return;
    }

    spinner.style.display = "inline-block";
    message.textContent = "";

    try {
        const res = await fetch("http://127.0.0.1:8002/ask/", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `query=${encodeURIComponent(question)}`
        });

        const data = await res.json();
        if (data.answer) {
            message.textContent = data.answer;
        } else {
            message.textContent = "❌ " + (data.error || "Unknown error");
        }
    } catch (err) {
        message.textContent = "❌ Failed to fetch answer.";
    }

    spinner.style.display = "none";
}
