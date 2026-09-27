class FullscreenContainer extends HTMLElement {
    constructor() {
        super();

        this.attachShadow({ mode: 'open' });

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    position: relative;
                    display: block;
                    width: 100%;
                    height: 500px;
                }

                ::slotted(*) {
                    display: block;
                    width: 100%;
                    height: 100%;
                }

                :host(:fullscreen) {
                    position: fixed;
                    inset: 0;

                    width: 100vw;
                    height: 100vh;

                    margin: 0;
                    padding: 0;

                    background: var(--md-code-bg-color);
                }

                .fullscreen-btn {
                    position: absolute;
                    top: 12px;
                    left: 12px;
                    z-index: 10;

                    width: 36px;
                    height: 36px;
                    padding: 0;

                    border: none;
                    border-radius: 6px;

                    background: rgba(40, 40, 40, 0.75);
                    color: white;

                    font-size: 22px;
                    line-height: 36px;

                    cursor: pointer;

                    backdrop-filter: blur(4px);
                }

                .fullscreen-btn:hover {
                    background: rgba(60, 60, 60, 0.9);
                }

                :host(:fullscreen) ::slotted(*) {
                    width: 100%;
                    height: 100%;
                    border: none;
                    border-radius: 0;
                }
            </style>

            <button
                class="fullscreen-btn"
                type="button"
                title="Fullscreen"
                aria-label="Fullscreen">
                ⛶
            </button>

            <slot></slot>
        `;

        this.button = this.shadowRoot.querySelector('.fullscreen-btn');

        this.button.addEventListener('click', () => {
            this.toggleFullscreen();
        });
    }

    async toggleFullscreen() {
        try {
            if (document.fullscreenElement === this) {
                await document.exitFullscreen();
            } else {
                await this.requestFullscreen();
            }
        } catch (error) {
            console.error('Fullscreen error:', error);
        }
    }

    updateButton() {
        const isFullscreen = document.fullscreenElement === this;

        this.button.title = isFullscreen
            ? 'Exit fullscreen'
            : 'Fullscreen';

        this.button.setAttribute(
            'aria-label',
            isFullscreen
                ? 'Exit fullscreen'
                : 'Fullscreen'
        );
    }

    connectedCallback() {
        this.fullscreenChangeHandler = () => {
            this.updateButton();
        };

        document.addEventListener(
            'fullscreenchange',
            this.fullscreenChangeHandler
        );
    }

    disconnectedCallback() {
        document.removeEventListener(
            'fullscreenchange',
            this.fullscreenChangeHandler
        );
    }
}

customElements.define('fullscreen-container', FullscreenContainer);
