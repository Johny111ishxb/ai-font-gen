// Intersection Observer for fade-in animations
const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
};

const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target); // Stop observing once visible
        }
    });
}, observerOptions);

// Observe all tool containers and fade-in elements
document.addEventListener('DOMContentLoaded', () => {
    const elements = document.querySelectorAll('.tool-container, .fade-in');
    elements.forEach(el => observer.observe(el));
    
    // Initialize dropzone functionality
    initDropzone();
    
    // Initialize UI elements
    initUI();
});

// Initialize dropzone functionality
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const previewContainer = document.getElementById('preview');
    const previewImage = document.getElementById('previewImage');
    const generateBtn = document.getElementById('generateBtn');
    
    if (dropzone && fileInput) {
        // Handle click on dropzone
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Handle drag and drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });
        
        // Handle file selection
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        // Handle file preview
        function handleFileSelect(file) {
            if (file) {
                const reader = new FileReader();
                
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewContainer.classList.add('visible');
                    generateBtn.classList.add('visible');
                };
                
                reader.readAsDataURL(file);
            }
        }
    }
}

// Initialize UI elements
function initUI() {
    const generateBtn = document.getElementById('generateBtn');
    const status = document.getElementById('status');
    const downloadSection = document.getElementById('downloadSection');
    
    if (generateBtn) {
        generateBtn.addEventListener('click', () => {
            generateBtn.classList.remove('visible');
            status.classList.add('visible');
            
            // Simulate processing delay
            setTimeout(() => {
                status.classList.remove('visible');
                downloadSection.classList.add('visible');
            }, 3000);
        });
    }
}

// Theme Management Module
const ThemeManager = {
    // Default theme configuration
    defaultTheme: 'light',
    storageKey: 'user-theme-preference',

    // Initialize theme on page load
    init() {
        // Add theme toggle listener
        this.setupThemeToggle();
        
        // Load saved theme or use default
        this.loadSavedTheme();
    },

    // Setup theme toggle button
    setupThemeToggle() {
        const toggleBtn = document.querySelector('.theme-toggle-btn');
        if (!toggleBtn) {
            console.warn('Theme toggle button not found');
            return;
        }

        toggleBtn.addEventListener('click', () => {
            this.toggleTheme();
        });
    },

    // Toggle between light and dark themes
    toggleTheme() {
        const currentTheme = this.getCurrentTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        this.setTheme(newTheme);
    },

    // Get current theme
    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || this.defaultTheme;
    },

    // Set theme and save preference
    setTheme(theme) {
        // Set theme attribute
        document.documentElement.setAttribute('data-theme', theme);
        
        // Save to local storage
        localStorage.setItem(this.storageKey, theme);
        
        // Update theme toggle button or other UI elements if needed
        this.updateThemeToggleUI(theme);
        
        // Dispatch custom theme change event
        this.dispatchThemeChangeEvent(theme);
    },

    // Load saved theme from storage
    loadSavedTheme() {
        const savedTheme = localStorage.getItem(this.storageKey);
        
        if (savedTheme) {
            this.setTheme(savedTheme);
        } else {
            // Check system preference if no saved theme
            this.checkSystemPreference();
        }
    },

    // Check system preference for theme
    checkSystemPreference() {
        const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)');
        
        if (prefersDarkMode.matches) {
            this.setTheme('dark');
        } else {
            this.setTheme('light');
        }

        // Listen for system theme changes
        prefersDarkMode.addEventListener('change', (e) => {
            this.setTheme(e.matches ? 'dark' : 'light');
        });
    },

    // Update theme toggle UI
    updateThemeToggleUI(theme) {
        const toggleBtn = document.querySelector('.theme-toggle-btn');
        if (toggleBtn) {
            toggleBtn.setAttribute('data-current-theme', theme);
            
            // Change icon based on theme
            const themeIcon = toggleBtn.querySelector('.theme-icon');
            if (themeIcon) {
                themeIcon.textContent = theme === 'dark' ? '🌙' : '☀️';
            }
        }
    },

    // Dispatch custom theme change event
    dispatchThemeChangeEvent(theme) {
        const event = new CustomEvent('themeChanged', { 
            detail: { theme: theme } 
        });
        document.dispatchEvent(event);
    }
};

// Initialize theme management when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
});

// Listen for theme change events
document.addEventListener('themeChanged', (e) => {
    console.log(`Theme changed to: ${e.detail.theme}`);
});

// Handle mobile interactions for tool images
document.querySelectorAll('.tool-image').forEach(container => {
    let isMobile = window.matchMedia("(max-width: 768px)").matches;
    let isActive = false;

    if(isMobile) {
        container.addEventListener('click', () => {
            isActive = !isActive;
            container.classList.toggle('active', isActive);
        });
    }
});
