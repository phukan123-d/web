document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.solve-button').forEach(button => {
    button.addEventListener('click', async () => {
      const questionId = button.dataset.id;
      if (!questionId) return;

      button.disabled = true;
      const formData = new FormData();
      formData.append('status', 'done');

      try {
        const response = await fetch(`/update_status/${questionId}`, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();
        if (result.success) {
          button.textContent = 'Solved!';
          button.classList.remove('button-primary');
          button.classList.add('button-outline');
          setTimeout(() => window.location.reload(), 700);
        }
      } catch (error) {
        console.error('Update failed', error);
        button.disabled = false;
      }
    });
  });

  const generateForm = document.getElementById('generate-form');
  const generatedResults = document.getElementById('generated-results');

  if (generateForm && generatedResults) {
    generateForm.addEventListener('submit', async event => {
      event.preventDefault();

      const formData = new FormData(generateForm);
      const payload = {
        topic: formData.get('topic') || '',
        tags: formData.get('tags') || '',
        difficulty: formData.get('difficulty') || 'Medium',
      };

      const submitButton = generateForm.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.textContent = 'Generating...';

      try {
        const response = await fetch('/suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const results = await response.json();
        renderGeneratedQuestions(results);
      } catch (error) {
        console.error('Suggestion fetch failed', error);
        generatedResults.innerHTML = '<div class="empty-state">Unable to generate ideas right now. Try again later.</div>';
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Generate ideas';
      }
    });
  }

  generatedResults?.addEventListener('click', async event => {
    const button = event.target.closest('.save-idea');
    if (!button) return;

    button.disabled = true;
    button.textContent = 'Saving...';

    try {
      const response = await fetch('/save_suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: button.dataset.title,
          topic: button.dataset.topic,
          difficulty: button.dataset.difficulty,
          tags: button.dataset.tags,
        }),
      });

      const result = await response.json();
      if (result.success) {
        button.textContent = 'Saved';
        button.classList.remove('button-outline');
        button.classList.add('button-primary');
      } else {
        button.textContent = result.message || 'Save failed';
        button.disabled = false;
      }
    } catch (error) {
      console.error('Save failed', error);
      button.textContent = 'Save failed';
      button.disabled = false;
    }
  });

  function renderGeneratedQuestions(questions) {
    if (!questions || questions.length === 0) {
      generatedResults.innerHTML = '<div class="empty-state">No AI ideas found. Try a different topic or tags.</div>';
      return;
    }

    generatedResults.innerHTML = questions.map(question => {
      return `
        <article class="card small-card">
          <div class="card-badge todo">AI idea</div>
          <h3>${question.title}</h3>
          <p class="meta">${question.topic} · ${question.difficulty}</p>
          <p class="tags">${question.tags || 'generated'}</p>
          <div class="card-actions">
            <button class="button button-outline save-idea" data-title="${encodeHTML(question.title)}" data-topic="${encodeHTML(question.topic)}" data-difficulty="${encodeHTML(question.difficulty)}" data-tags="${encodeHTML(question.tags || '')}">Save to tracker</button>
          </div>
        </article>
      `;
    }).join('');
  }

  function encodeHTML(value) {
    return String(value || '').replace(/[&<>"']/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[tag]));
  }
});
