// ==UserScript==
// @name         Bili-ASR-Sum 视频总结助手
// @namespace    https://github.com/bili-asr-sum
// @version      1.0.0
// @description  在 YouTube 和 Bilibili 视频缩略图旁添加总结按钮，一键获取视频内容摘要
// @author       bili-asr-sum
// @match        *://www.youtube.com/*
// @match        *://youtube.com/*
// @match        *://www.bilibili.com/*
// @match        *://bilibili.com/*
// @match        *://search.bilibili.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_notification
// @connect      *
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    // ============================================
    // 配置管理模块
    // ============================================
    const Config = {
        getApiBase() {
            return GM_getValue('apiBase', 'https://sum.icmb.top:8443');
        },
        setApiBase(url) {
            GM_setValue('apiBase', url.replace(/\/$/, ''));
        },
        isConfigured() {
            return this.getApiBase() !== '';
        },
        promptForApiBase() {
            const current = this.getApiBase();
            const url = prompt('请输入 API 服务地址（如 https://api.example.com）：', current);
            if (url && url.trim()) {
                this.setApiBase(url.trim());
                alert('API 地址已保存：' + this.getApiBase());
                return true;
            }
            return false;
        }
    };

    // 注册油猴菜单
    GM_registerMenuCommand('⚙️ 设置 API 地址', () => {
        Config.promptForApiBase();
    });

    // ============================================
    // API 交互模块
    // ============================================
    const API = {
        async submitTask(url) {
            const apiBase = Config.getApiBase();
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'POST',
                    url: `${apiBase}/api/summarize`,
                    headers: { 'Content-Type': 'application/json' },
                    data: JSON.stringify({ url }),
                    onload(response) {
                        if (response.status === 202) {
                            resolve(JSON.parse(response.responseText));
                        } else {
                            reject(new Error(`提交失败: ${response.status}`));
                        }
                    },
                    onerror(error) {
                        reject(new Error('网络请求失败'));
                    }
                });
            });
        },

        async getTask(taskId) {
            const apiBase = Config.getApiBase();
            return new Promise((resolve, reject) => {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: `${apiBase}/api/tasks/${taskId}`,
                    onload(response) {
                        if (response.status === 200) {
                            resolve(JSON.parse(response.responseText));
                        } else {
                            reject(new Error(`查询失败: ${response.status}`));
                        }
                    },
                    onerror() {
                        reject(new Error('网络请求失败'));
                    }
                });
            });
        },

        // 轮询任务状态直到完成
        async pollTask(taskId, onProgress) {
            const maxAttempts = 300; // 最多轮询5分钟
            const interval = 1000; // 1秒间隔

            for (let i = 0; i < maxAttempts; i++) {
                const task = await this.getTask(taskId);
                onProgress(task);

                if (task.status === 'completed' || task.status === 'failed') {
                    return task;
                }

                await new Promise(resolve => setTimeout(resolve, interval));
            }

            throw new Error('任务超时');
        }
    };

    // ============================================
    // 侧边栏组件
    // ============================================
    const Sidebar = {
        container: null,
        taskList: null,
        tasks: new Map(), // taskId -> taskData

        init() {
            if (this.container) return;

            this.container = document.createElement('div');
            this.container.id = 'bili-asr-sum-sidebar';
            this.container.innerHTML = `
                <button class="bas-sidebar-toggle" title="收起">▶</button>
                <div class="bas-sidebar-inner">
                    <div class="bas-sidebar-header">
                        <span class="bas-sidebar-title">📝 视频总结</span>
                        <button class="bas-sidebar-close" title="关闭">&times;</button>
                    </div>
                    <div class="bas-sidebar-content">
                        <div class="bas-task-list"></div>
                    </div>
                </div>
            `;

            this.taskList = this.container.querySelector('.bas-task-list');
            this.container.querySelector('.bas-sidebar-close').addEventListener('click', () => {
                this.hide();
            });
            this.container.querySelector('.bas-sidebar-toggle').addEventListener('click', () => {
                this.toggleMinimize();
            });

            document.body.appendChild(this.container);
        },

        show() {
            this.init();
            this.container.classList.add('bas-sidebar-visible');
        },

        hide() {
            if (this.container) {
                this.container.classList.remove('bas-sidebar-visible');
                // 同步清除收起状态，避免下次展开时状态残留
                this.container.classList.remove('bas-sidebar-minimized');
                const btn = this.container.querySelector('.bas-sidebar-toggle');
                if (btn) {
                    btn.textContent = '▶';
                    btn.title = '收起';
                }
            }
        },

        toggle() {
            if (this.container && this.container.classList.contains('bas-sidebar-visible')) {
                this.hide();
            } else {
                this.show();
            }
        },

        toggleMinimize() {
            if (!this.container) return;
            // 若侧边栏不可见（已关闭），点击 toggle 应直接展开而非空转
            if (!this.container.classList.contains('bas-sidebar-visible')) {
                this.container.classList.remove('bas-sidebar-minimized');
                this.show();
                const btn = this.container.querySelector('.bas-sidebar-toggle');
                if (btn) { btn.textContent = '▶'; btn.title = '收起'; }
                return;
            }
            const isMinimized = this.container.classList.toggle('bas-sidebar-minimized');
            const btn = this.container.querySelector('.bas-sidebar-toggle');
            btn.textContent = isMinimized ? '◀' : '▶';
            btn.title = isMinimized ? '展开' : '收起';
        },

        addTask(taskId, videoUrl, videoTitle) {
            this.show();
            
            const taskEl = document.createElement('div');
            taskEl.className = 'bas-task-card';
            taskEl.id = `bas-task-${taskId}`;
            taskEl.innerHTML = `
                <div class="bas-task-header">
                    <button class="bas-task-collapse" title="折叠/展开">▾</button>
                    <span class="bas-task-title">${this.escapeHtml(videoTitle || '获取中...')}</span>
                    <button class="bas-task-remove">&times;</button>
                </div>
                <div class="bas-task-body">
                    <div class="bas-task-status">
                        <span class="bas-status-icon">⏳</span>
                        <span class="bas-status-text">等待处理...</span>
                    </div>
                    <div class="bas-task-summary" style="display:none;"></div>
                </div>
            `;

            taskEl.querySelector('.bas-task-remove').addEventListener('click', () => {
                taskEl.remove();
                this.tasks.delete(taskId);
            });

            taskEl.querySelector('.bas-task-collapse').addEventListener('click', () => {
                const body = taskEl.querySelector('.bas-task-body');
                const btn = taskEl.querySelector('.bas-task-collapse');
                const collapsed = body.style.display === 'none';
                body.style.display = collapsed ? '' : 'none';
                btn.textContent = collapsed ? '▾' : '▸';
                taskEl.classList.toggle('bas-task-collapsed', !collapsed);
            });

            this.taskList.insertBefore(taskEl, this.taskList.firstChild);
            this.tasks.set(taskId, { el: taskEl, url: videoUrl });
        },

        updateTask(taskId, taskData) {
            const task = this.tasks.get(taskId);
            if (!task) return;

            const el = task.el;
            const statusIcon = el.querySelector('.bas-status-icon');
            const statusText = el.querySelector('.bas-status-text');
            const summaryEl = el.querySelector('.bas-task-summary');
            const titleEl = el.querySelector('.bas-task-title');

            // 更新标题
            if (taskData.title) {
                titleEl.textContent = taskData.title;
            }

            // 状态映射
            const statusMap = {
                pending: { icon: '⏳', text: '等待处理...' },
                downloading: { icon: '📥', text: '下载视频中...' },
                transcribing: { icon: '🎙️', text: '语音识别中...' },
                summarizing: { icon: '🤖', text: 'AI 总结中...' },
                completed: { icon: '✅', text: '完成' },
                failed: { icon: '❌', text: '失败' }
            };

            const status = statusMap[taskData.status] || { icon: '❓', text: taskData.status };
            statusIcon.textContent = status.icon;
            statusText.textContent = status.text;

            // 显示总结内容
            if (taskData.status === 'completed' && taskData.summary) {
                summaryEl.style.display = 'block';
                summaryEl.innerHTML = this.formatSummary(taskData.summary);
                el.classList.add('bas-task-completed');
            }

            // 显示错误
            if (taskData.status === 'failed' && taskData.error) {
                summaryEl.style.display = 'block';
                summaryEl.innerHTML = `<div class="bas-error">${this.escapeHtml(taskData.error)}</div>`;
                el.classList.add('bas-task-failed');
            }
        },

        formatSummary(summary) {
            // 按行处理，逐行转换 Markdown
            const lines = summary.split('\n');
            const result = [];
            let inList = false;

            for (const raw of lines) {
                const line = raw
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>');

                if (/^#{1,6}\s/.test(raw)) {
                    if (inList) { result.push('</ul>'); inList = false; }
                    const level = raw.match(/^(#{1,6})/)[1].length;
                    const text = line.replace(/^#{1,6}\s+/, '');
                    result.push(`<h${level} class="bas-summary-h${level}">${text}</h${level}>`);
                } else if (/^[-*]\s+/.test(raw)) {
                    if (!inList) { result.push('<ul>'); inList = true; }
                    result.push(`<li>${line.replace(/^[-*]\s+/, '')}</li>`);
                } else if (raw.trim() === '') {
                    if (inList) { result.push('</ul>'); inList = false; }
                    result.push('');
                } else {
                    if (inList) { result.push('</ul>'); inList = false; }
                    result.push(`<p>${line}</p>`);
                }
            }
            if (inList) result.push('</ul>');

            return result.join('');
        },

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };

    // ============================================
    // 视频卡片注入逻辑
    // ============================================
    const VideoCardInjector = {
        processedCards: new WeakSet(),

        init() {
            // 初始扫描
            this.scanAndInject();

            // 监听动态加载
            this.observe();
        },

        observe() {
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.scanAndInject(node);
                        }
                    }
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        },

        scanAndInject(root = document.body) {
            const YT_SELECTOR = 'ytd-rich-item-renderer, ytd-video-renderer, ytd-grid-video-renderer, ytd-compact-video-renderer';
            const BILI_SELECTOR = '.bili-video-card, .bili-video-card-recommend, .feed-card, .recommend-list__item, .video-list-item, .search-all-list .item, .video-card, .rank-item';

            // root 本身可能就是视频卡片（滚动加载时 MutationObserver 直接传入卡片节点）
            if (root.matches) {
                if (root.matches(YT_SELECTOR)) this.injectYouTube(root);
                else if (root.matches(BILI_SELECTOR)) this.injectBilibili(root);
            }

            // YouTube 视频卡片
            root.querySelectorAll(YT_SELECTOR).forEach(card => this.injectYouTube(card));

            // Bilibili 视频卡片
            root.querySelectorAll(BILI_SELECTOR).forEach(card => this.injectBilibili(card));
        },

        // 穿透 shadow DOM 查找元素
        deepQuerySelector(root, selector) {
            // 先在普通 DOM 中查找
            let el = root.querySelector(selector);
            if (el) return el;

            // 遍历所有子节点，尝试穿透 shadow root
            const all = root.querySelectorAll('*');
            for (const node of all) {
                if (node.shadowRoot) {
                    el = this.deepQuerySelector(node.shadowRoot, selector);
                    if (el) return el;
                }
            }
            return null;
        },

        injectYouTube(card) {
            if (this.processedCards.has(card)) return;

            // 在标题末尾注入按钮，避免 shadow DOM 问题
            // 兼容旧版（a#video-title-link / a#video-title）和新版 lockup 架构
            const titleLink = card.querySelector(
                'a#video-title-link, a#video-title, ' +
                '.yt-lockup-metadata-view-model__title a, ' +
                'h3 a[href*="watch?v="]'
            );
            if (!titleLink) return;

            const videoUrl = titleLink.href;
            if (!videoUrl || !videoUrl.includes('watch?v=')) return;

            // 已有按钮则跳过
            if (card.querySelector('.bas-yt-title-btn')) {
                this.processedCards.add(card);
                return;
            }

            const btn = this.createButton(videoUrl, 'youtube');
            btn.classList.add('bas-yt-title-btn');

            // 找到标题的父容器，将按钮插入其中（与标题同行）
            const titleParent = titleLink.closest('h3') || titleLink.parentElement;
            titleParent.appendChild(btn);

            this.processedCards.add(card);
        },

        injectBilibili(card) {
            if (this.processedCards.has(card)) return;

            // 获取视频链接
            const link = card.querySelector('a[href*="video/BV"], a[href*="video/av"]');
            if (!link) return;

            // 构建完整URL
            let videoUrl = link.href;
            if (!videoUrl.startsWith('http')) {
                videoUrl = 'https://www.bilibili.com' + videoUrl;
            }

            // 创建按钮
            const btn = this.createButton(videoUrl, 'bilibili');

            // 查找缩略图容器用于定位参考
            const thumbnail = card.querySelector('.bili-video-card__cover, .bili-video-card__image, .feed-card__cover, .recommend-list__item-link, .video-card__content, a[href*="video/"]');

            // 直接在卡片上添加按钮容器（避免影响缩略图内部布局）
            // 卡片通常已经有 position: relative 或类似定位
            let btnContainer = card.querySelector('.bas-btn-container');
            if (!btnContainer) {
                btnContainer = document.createElement('div');
                btnContainer.className = 'bas-btn-container bas-bili-btn-container';
                card.appendChild(btnContainer);
            }
            btnContainer.appendChild(btn);

            // 样式定位：如果找到缩略图，按钮定位相对于缩略图区域
            // 默认已在 CSS 中设置 top: 8px, right: 8px
            if (thumbnail) {
                // 确保 card 有定位基准
                const cardStyle = window.getComputedStyle(card);
                if (cardStyle.position === 'static') {
                    card.style.position = 'relative';
                }
            }

            this.processedCards.add(card);
        },

        createButton(videoUrl, platform) {
            const btn = document.createElement('button');
            btn.className = `bas-summarize-btn bas-btn-${platform}`;
            btn.innerHTML = '📝';
            btn.title = '总结视频内容';
            
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();

                if (!Config.isConfigured()) {
                    const success = Config.promptForApiBase();
                    if (!success) return;
                }

                // 显示加载状态
                btn.disabled = true;
                btn.innerHTML = '⏳';

                try {
                    // 提交任务
                    const result = await API.submitTask(videoUrl);
                    
                    // 添加到侧边栏
                    Sidebar.addTask(result.task_id, videoUrl, null);

                    // 开始轮询
                    API.pollTask(result.task_id, (task) => {
                        Sidebar.updateTask(result.task_id, task);
                    });

                    btn.innerHTML = '✅';
                } catch (error) {
                    console.error('Bili-ASR-Sum Error:', error);
                    btn.innerHTML = '❌';
                    GM_notification({
                        title: '总结失败',
                        text: error.message,
                        timeout: 3000
                    });
                } finally {
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = '📝';
                    }, 2000);
                }
            });

            return btn;
        }
    };

    // ============================================
    // 样式注入
    // ============================================
    const Styles = {
        inject() {
            const style = document.createElement('style');
            style.textContent = `
                /* Bilibili 按钮容器 - 绝对定位叠在缩略图上 */
                .bas-btn-container {
                    position: absolute !important;
                    top: 8px !important;
                    right: 8px !important;
                    z-index: 999 !important;
                    opacity: 0;
                    transition: opacity 0.2s;
                    margin: 0 !important;
                    padding: 0 !important;
                    width: 32px !important;
                    height: 32px !important;
                    display: block !important;
                    overflow: visible !important;
                    box-sizing: border-box !important;
                }

                /* Bilibili hover */
                .bili-video-card:hover .bas-btn-container,
                .feed-card:hover .bas-btn-container,
                .recommend-list__item:hover .bas-btn-container,
                .video-list-item:hover .bas-btn-container,
                .search-all-list .item:hover .bas-btn-container,
                .video-card:hover .bas-btn-container,
                .rank-item:hover .bas-btn-container,
                .bas-btn-container:hover {
                    opacity: 1;
                }

                /* 总结按钮通用样式（Bilibili 缩略图悬浮按钮） */
                .bas-summarize-btn {
                    display: flex !important;
                    align-items: center;
                    justify-content: center;
                    width: 32px !important;
                    height: 32px !important;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    transition: all 0.2s;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    pointer-events: auto;
                    margin: 0 !important;
                    padding: 0 !important;
                    box-sizing: border-box !important;
                }

                .bas-summarize-btn:hover:not(:disabled) {
                    transform: scale(1.1);
                }

                .bas-summarize-btn:disabled {
                    cursor: wait;
                }

                /* YouTube 标题行内按钮 */
                .bas-yt-title-btn {
                    display: inline-flex !important;
                    align-items: center;
                    justify-content: center;
                    width: 22px !important;
                    height: 22px !important;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                    background: transparent;
                    color: #606060;
                    margin-left: 6px !important;
                    padding: 0 !important;
                    vertical-align: middle;
                    flex-shrink: 0;
                    box-shadow: none;
                    opacity: 0.5;
                    transition: opacity 0.15s, background 0.15s;
                    position: static !important;
                }

                h3:hover .bas-yt-title-btn,
                .bas-yt-title-btn:hover {
                    opacity: 1;
                    background: rgba(0, 0, 0, 0.08);
                }

                html[dark] .bas-yt-title-btn,
                ytd-app[is-dark-theme] .bas-yt-title-btn {
                    color: #aaa;
                }

                html[dark] h3:hover .bas-yt-title-btn,
                ytd-app[is-dark-theme] h3:hover .bas-yt-title-btn,
                html[dark] .bas-yt-title-btn:hover,
                ytd-app[is-dark-theme] .bas-yt-title-btn:hover {
                    background: rgba(255, 255, 255, 0.1);
                }

                /* YouTube 按钮（Bilibili 缩略图覆盖样式，非 title 模式） */
                .bas-btn-youtube {
                    background: rgba(0, 0, 0, 0.7);
                    color: white;
                }

                .bas-btn-youtube:hover:not(:disabled) {
                    background: rgba(204, 0, 0, 0.9);
                }

                /* Bilibili 按钮样式 */
                .bas-btn-bilibili {
                    background: rgba(255, 255, 255, 0.9);
                    color: #fb7299;
                }

                .bas-btn-bilibili:hover:not(:disabled) {
                    background: #fb7299;
                    color: white;
                }

                /* 侧边栏样式 */
                #bili-asr-sum-sidebar {
                    position: fixed;
                    top: 0;
                    right: -420px;
                    width: 420px;
                    height: 100vh;
                    background: #fff;
                    box-shadow: -4px 0 20px rgba(0,0,0,0.15);
                    z-index: 999999;
                    transition: right 0.3s ease;
                    display: flex;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }

                #bili-asr-sum-sidebar.bas-sidebar-visible {
                    right: 0;
                }

                /* 左侧收起/展开按钮 */
                .bas-sidebar-toggle {
                    position: absolute;
                    left: -20px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 20px;
                    height: 60px;
                    border: none;
                    background: #fff;
                    cursor: pointer;
                    border-radius: 6px 0 0 6px;
                    font-size: 12px;
                    color: #666;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
                    z-index: 10;
                }

                .bas-sidebar-toggle:hover {
                    background: #f5f5f5;
                    color: #333;
                }

                html[dark] .bas-sidebar-toggle,
                [data-dark-mode="true"] .bas-sidebar-toggle {
                    background: #2a2a2a;
                    color: #aaa;
                }

                html[dark] .bas-sidebar-toggle:hover,
                [data-dark-mode="true"] .bas-sidebar-toggle:hover {
                    background: #333;
                    color: #fff;
                }

                /* 收起状态 */
                #bili-asr-sum-sidebar.bas-sidebar-minimized {
                    right: -400px;
                }

                #bili-asr-sum-sidebar.bas-sidebar-minimized .bas-sidebar-toggle {
                    left: -20px;
                    box-shadow: -2px 0 8px rgba(0,0,0,0.15);
                }

                #bili-asr-sum-sidebar.bas-sidebar-minimized .bas-sidebar-inner {
                    display: none;
                }

                /* 侧边栏内部容器 */
                .bas-sidebar-inner {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }

                /* YouTube 深色模式适配 */
                html[dark] #bili-asr-sum-sidebar,
                [data-dark-mode="true"] #bili-asr-sum-sidebar {
                    background: #212121;
                    color: #f1f1f1;
                }

                /* Bilibili 主题适配 */
                .bili-dark #bili-asr-sum-sidebar {
                    background: #18191c;
                    color: #f1f1f1;
                }

                .bas-sidebar-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 20px;
                    border-bottom: 1px solid #eee;
                    flex-shrink: 0;
                }

                html[dark] .bas-sidebar-header,
                [data-dark-mode="true"] .bas-sidebar-header {
                    border-bottom-color: #333;
                }

                .bas-sidebar-title {
                    font-size: 18px;
                    font-weight: 600;
                }

                .bas-sidebar-close {
                    width: 32px;
                    height: 32px;
                    border: none;
                    background: transparent;
                    font-size: 24px;
                    cursor: pointer;
                    border-radius: 6px;
                    color: inherit;
                }

                .bas-sidebar-close:hover {
                    background: rgba(0,0,0,0.1);
                }

                .bas-sidebar-content {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                }

                .bas-task-list {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                /* 任务卡片样式 */
                .bas-task-card {
                    background: #f8f9fa;
                    border-radius: 12px;
                    padding: 16px;
                    border: 1px solid #e9ecef;
                }

                html[dark] .bas-task-card,
                [data-dark-mode="true"] .bas-task-card {
                    background: #2a2a2a;
                    border-color: #404040;
                }

                .bas-task-header {
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 4px;
                    margin-bottom: 8px;
                }

                .bas-task-collapsed .bas-task-header {
                    margin-bottom: 0;
                }

                .bas-task-collapse {
                    flex-shrink: 0;
                    width: 20px;
                    height: 20px;
                    border: none;
                    background: transparent;
                    font-size: 14px;
                    cursor: pointer;
                    border-radius: 4px;
                    color: #999;
                    padding: 0;
                    line-height: 1;
                    margin-top: 1px;
                }

                .bas-task-collapse:hover {
                    background: rgba(0,0,0,0.1);
                    color: #333;
                }

                .bas-task-title {
                    font-size: 14px;
                    font-weight: 500;
                    line-height: 1.4;
                    flex: 1;
                    word-break: break-word;
                }

                .bas-task-remove {
                    flex-shrink: 0;
                    width: 24px;
                    height: 24px;
                    border: none;
                    background: transparent;
                    font-size: 18px;
                    cursor: pointer;
                    border-radius: 4px;
                    color: #999;
                }

                .bas-task-remove:hover {
                    background: rgba(0,0,0,0.1);
                    color: #333;
                }

                .bas-task-status {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 13px;
                    color: #666;
                    padding: 8px 12px;
                    background: rgba(0,0,0,0.03);
                    border-radius: 8px;
                }

                html[dark] .bas-task-status,
                [data-dark-mode="true"] .bas-task-status {
                    background: rgba(255,255,255,0.05);
                    color: #aaa;
                }

                .bas-status-icon {
                    font-size: 16px;
                }

                .bas-task-summary {
                    margin-top: 12px;
                    padding: 12px;
                    background: white;
                    border-radius: 8px;
                    font-size: 14px;
                    line-height: 1.6;
                    border: 1px solid #e9ecef;
                }

                html[dark] .bas-task-summary,
                [data-dark-mode="true"] .bas-task-summary {
                    background: #1a1a1a;
                    border-color: #404040;
                }

                .bas-task-summary p {
                    margin: 0 0 8px 0;
                }

                .bas-task-summary p:last-child {
                    margin-bottom: 0;
                }

                .bas-task-summary ul {
                    margin: 8px 0;
                    padding-left: 20px;
                }

                .bas-task-summary li {
                    margin: 4px 0;
                }

                .bas-task-summary h1,
                .bas-task-summary h2,
                .bas-task-summary h3,
                .bas-task-summary h4,
                .bas-task-summary h5,
                .bas-task-summary h6 {
                    margin: 12px 0 4px 0;
                    line-height: 1.3;
                    font-weight: 600;
                }

                .bas-task-summary h1 { font-size: 16px; }
                .bas-task-summary h2 { font-size: 15px; }
                .bas-task-summary h3 { font-size: 14px; }
                .bas-task-summary h4,
                .bas-task-summary h5,
                .bas-task-summary h6 { font-size: 13px; }

                .bas-task-completed .bas-task-status {
                    background: rgba(76, 175, 80, 0.1);
                    color: #4caf50;
                }

                .bas-task-failed .bas-task-status {
                    background: rgba(244, 67, 54, 0.1);
                    color: #f44336;
                }

                .bas-error {
                    color: #f44336;
                    font-size: 13px;
                }

                /* 滚动条样式 */
                .bas-sidebar-content::-webkit-scrollbar {
                    width: 6px;
                }

                .bas-sidebar-content::-webkit-scrollbar-track {
                    background: transparent;
                }

                .bas-sidebar-content::-webkit-scrollbar-thumb {
                    background: #ccc;
                    border-radius: 3px;
                }

                .bas-sidebar-content::-webkit-scrollbar-thumb:hover {
                    background: #aaa;
                }
            `;
            document.head.appendChild(style);
        }
    };

    // ============================================
    // 初始化
    // ============================================
    function init() {
        // 注入样式
        Styles.inject();

        // 初始化侧边栏（但不显示）
        Sidebar.init();

        // 开始监听视频卡片
        VideoCardInjector.init();

        // YouTube 是 SPA，监听页面导航事件重新扫描
        if (location.hostname.includes('youtube.com')) {
            document.addEventListener('yt-navigate-finish', () => {
                // 导航完成后稍等 DOM 渲染再扫描
                setTimeout(() => VideoCardInjector.scanAndInject(), 500);
                setTimeout(() => VideoCardInjector.scanAndInject(), 1500);
            });
        }

        console.log('Bili-ASR-Sum: 已加载');
    }

    // 等待页面加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();