let mediaRecorder;
let audioChunks = [];
let voiceEnabled = true;
let recordingCount = 0;
let moodChart;
const moodLabels = [];
const moodScores = [];

const status = document.getElementById("status");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const voiceToggleBtn = document.getElementById("voiceToggleBtn");
const analyzeTextBtn = document.getElementById("analyzeTextBtn");
const demoText = document.getElementById("demoText");

const emotionEmojiMap = {
    high_distress: "😟",
    distressed: "😔",
    emotional_mismatch: "🫤",
    low_mood: "😕",
    agitated: "😤",
    neutral: "🙂"
};

function initMoodChart() {
    const ctx = document.getElementById("moodChart");
    moodChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: moodLabels,
            datasets: [{
                label: "Mood score",
                data: moodScores,
                borderColor: "#00adb5",
                backgroundColor: "rgba(0, 173, 181, 0.2)",
                tension: 0.25,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

function riskToMoodScore(finalEmotion, combinedRisk) {
    const numericRisk = Number(combinedRisk);
    const safeRisk = Number.isFinite(numericRisk) ? numericRisk : 0;
    let baseScore = Math.round((1 - safeRisk) * 100);

    if (finalEmotion === "high_distress") baseScore -= 12;
    if (finalEmotion === "distressed") baseScore -= 8;
    if (finalEmotion === "agitated") baseScore -= 6;
    if (finalEmotion === "low_mood") baseScore -= 5;
    if (finalEmotion === "emotional_mismatch") baseScore -= 4;

    return Math.max(0, Math.min(100, baseScore));
}

function pushMoodPoint(finalEmotion, combinedRisk) {
    recordingCount += 1;
    moodLabels.push(`R${recordingCount}`);
    moodScores.push(riskToMoodScore(finalEmotion, combinedRisk));

    if (moodLabels.length > 12) {
        moodLabels.shift();
        moodScores.shift();
    }
    moodChart.update();
}

function speakResponse(text) {
    if (!voiceEnabled || !("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);
}

voiceToggleBtn.onclick = () => {
    voiceEnabled = !voiceEnabled;
    voiceToggleBtn.innerText = voiceEnabled ? "🔊 Voice: On" : "🔇 Voice: Off";
    voiceToggleBtn.classList.toggle("muted", !voiceEnabled);
    if (!voiceEnabled && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
};

initMoodChart();

function renderAnalysis(data) {
    const analysis = data.analysis || {};
    document.getElementById("text").innerText = data.text || "(No text detected)";
    document.getElementById("finalEmotion").innerText = data.final_emotion || "unknown";
    document.getElementById("riskScore").innerText = analysis.combined_risk ?? "n/a";
    document.getElementById("reason").innerText = analysis.reason || "No reason available";
    document.getElementById("response").innerText = data.response || "No response";
    document.getElementById("emoji").innerText = emotionEmojiMap[data.final_emotion] || "🙂";
    pushMoodPoint(data.final_emotion, analysis.combined_risk);
    speakResponse(data.response || "");
}

analyzeTextBtn.onclick = async () => {
    const text = (demoText.value || "").trim();
    if (!text) {
        status.innerText = "Type some text first.";
        return;
    }

    status.innerText = "Analyzing text...";
    try {
        const res = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || "Server error");
        }
        renderAnalysis(data);
        status.innerText = "Done (text mode)";
    } catch (error) {
        status.innerText = `Error: ${error.message}`;
    }
};

recordBtn.onclick = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();

        audioChunks = [];
        mediaRecorder.ondataavailable = (e) => {
            audioChunks.push(e.data);
        };

        status.innerText = "Recording...";
    } catch (error) {
        status.innerText = "Mic permission denied or unavailable.";
    }
};

stopBtn.onclick = () => {
    if (!mediaRecorder || mediaRecorder.state !== "recording") {
        status.innerText = "Start recording first.";
        return;
    }

    mediaRecorder.stop();

    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: "audio/webm" });

        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");

        status.innerText = "Processing...";

        try {
            const res = await fetch("http://127.0.0.1:5000/analyze", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || "Server error");
            }

            renderAnalysis(data);

            status.innerText = "Done";
        } catch (error) {
            status.innerText = `Error: ${error.message}`;
        }
    };
};