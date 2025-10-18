document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selection ---
    const audiobookForm = document.getElementById('upload-form');
    const storyForm = document.getElementById('story-form');

    const tabAudiobook = document.getElementById('tab-audiobook');
    const tabStory = document.getElementById('tab-story');
    const contentAudiobook = document.getElementById('content-audiobook');
    const contentStory = document.getElementById('content-story');

    const statusContainer = document.getElementById('status-container');
    const statusText = document.getElementById('status-text');
    const resultContainer = document.getElementById('result-container');
    const resultMessage = document.getElementById('result-message');
    const spinner = document.getElementById('spinner');

    const progressBarContainer = document.getElementById('progress-bar-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    let pollingInterval;
    let currentJobType = 'audiobook'; // To manage which form to reset

    // --- Tab Switching Logic ---
    tabAudiobook.addEventListener('click', () => {
        switchTab('audiobook');
    });

    tabStory.addEventListener('click', () => {
        switchTab('story');
    });

    function switchTab(tabName) {
        currentJobType = tabName;
        if (tabName === 'audiobook') {
            tabAudiobook.classList.add('active');
            tabStory.classList.remove('active');
            contentAudiobook.classList.add('active');
            contentStory.classList.remove('active');
        } else {
            tabStory.classList.add('active');
            tabAudiobook.classList.remove('active');
            contentStory.classList.add('active');
            contentAudiobook.classList.remove('active');
        }
    }

    // --- Form Submission Handlers ---

    // 1. Audiobook Form Handler
    audiobookForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const fileInput = document.getElementById('pdf-upload');
        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a PDF file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        startJob('/create-job', formData, 'audiobook');
    });

    // 2. Story Form Handler
    storyForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const storyData = {
            name: document.getElementById('story-name').value,
            summary: document.getElementById('story-summary').value,
            chapters: parseInt(document.getElementById('story-chapters').value, 10),
            chars_per_chapter: parseInt(document.getElementById('story-chars').value, 10)
        };
        
        startJob('/create-story-job', JSON.stringify(storyData), 'story');
    });

    // --- Generic Job Starter Function ---
    async function startJob(endpoint, body, jobType) {
        // --- UI Updates: Start Processing ---
        setUiProcessing(true, jobType);

        try {
            const options = {
                method: 'POST',
                body: body,
            };
            // Set headers for JSON data if needed
            if (jobType === 'story') {
                options.headers = { 'Content-Type': 'application/json' };
            }

            const response = await fetch(endpoint, options);

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                const detail = errorData?.detail || `HTTP error! status: ${response.status}`;
                throw new Error(detail);
            }

            const data = await response.json();
            const { job_id } = data;
            startPolling(job_id);

        } catch (error) {
            console.error(`Error creating ${jobType} job:`, error);
            showError(`Failed to start the process: ${error.message}`);
        }
    }

    // --- Polling and UI Update Logic (mostly unchanged, but now generic) ---
    function startPolling(jobId) {
        statusText.textContent = 'Job accepted. Waiting for process to start...';
        pollingInterval = setInterval(() => {
            checkStatus(jobId);
        }, 3000); // Poll every 3 seconds
    }

    async function checkStatus(jobId) {
        try {
            const response = await fetch(`/status/${jobId}`);
            if (!response.ok) {
                throw new Error('Could not fetch status.');
            }
            const data = await response.json();
            if (data.status === 'processing' && data.progress !== undefined && data.progress >= 0) {
                progressBarContainer.style.display = 'block';
                const progressInt = Math.floor(data.progress);
                progressBar.style.width = `${progressInt}%`;
                progressText.textContent = `${progressInt}%`;
            } else {
                progressBarContainer.style.display = 'none';
            }

            statusText.textContent = data.message;

            if (data.status === 'complete') {
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                clearInterval(pollingInterval);
                setTimeout(() => showSuccess(jobId, data.message), 500);
            } else if (data.status === 'error') {
                clearInterval(pollingInterval);
                showError(data.message);
            }
            statusText.textContent = data.message;

            if (data.status === 'complete') {
                clearInterval(pollingInterval);
                showSuccess(jobId, data.message);
            } else if (data.status === 'error') {
                clearInterval(pollingInterval);
                showError(data.message);
            }
        } catch (error) {
            console.error('Polling error:', error);
            clearInterval(pollingInterval);
            showError('Lost connection to the server.');
        }
    }

    // --- UI Helper Functions ---
    function setUiProcessing(isProcessing, jobType) {
        const audiobookBtn = document.getElementById('submit-audiobook-btn');
        const storyBtn = document.getElementById('submit-story-btn');
        
        audiobookBtn.disabled = isProcessing;
        storyBtn.disabled = isProcessing;
        
        if (isProcessing) {
            if (jobType === 'audiobook') audiobookBtn.textContent = 'Processing...';
            if (jobType === 'story') storyBtn.textContent = 'Generating...';
            statusContainer.classList.remove('hidden');
            resultContainer.classList.add('hidden');
            statusText.classList.remove('error-message');
            spinner.classList.remove('hidden');
            statusText.textContent = 'Submitting job...';
            progressBarContainer.style.display = 'none';
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
        } else {
            audiobookBtn.textContent = 'Create Audiobook';
            storyBtn.textContent = 'Generate Story';
            audiobookForm.reset();
            storyForm.reset();
        }
    }

    function showSuccess(jobId, message) {
        statusContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        resultMessage.textContent = message;

        // Create and append the download link (this now works for both job types)
        const downloadLink = document.createElement('a');
        downloadLink.href = `/download/${jobId}`;
        downloadLink.textContent = 'Download Your File'; // Generic text
        
        const existingLink = resultContainer.querySelector('a');
        if (existingLink) existingLink.remove();
        resultContainer.appendChild(downloadLink);

        setUiProcessing(false, currentJobType);
    }

    function showError(message) {
        spinner.classList.add('hidden');
        statusText.textContent = message;
        statusText.classList.add('error-message');
        setUiProcessing(false, currentJobType);
    }
});