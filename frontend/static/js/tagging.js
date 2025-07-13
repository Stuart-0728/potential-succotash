class TagManager {
    constructor() {
        this.studentTags = new Set();
        this.activityTags = new Set();
    }

    async addTagToStudent(tagName) {
        try {
            const response = await fetch('/api/tags/student', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ tagName })
            });
            if (response.ok) {
                this.studentTags.add(tagName);
                this.renderStudentTags();
            }
        } catch (error) {
            console.error('添加标签失败:', error);
        }
    }

    async addTagToActivity(tagName) {
        try {
            const response = await fetch('/api/tags/activity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ tagName })
            });
            if (response.ok) {
                this.activityTags.add(tagName);
                this.renderActivityTags();
            }
        } catch (error) {
            console.error('添加标签失败:', error);
        }
    }

    renderStudentTags() {
        const container = document.getElementById('studentTags');
        container.innerHTML = Array.from(this.studentTags)
            .map(tag => `<span class="tag">${tag}</span>`)
            .join('');
    }

    renderActivityTags() {
        const container = document.getElementById('activityTags');
        container.innerHTML = Array.from(this.activityTags)
            .map(tag => `<span class="tag">${tag}</span>`)
            .join('');
    }
}

const tagManager = new TagManager();
