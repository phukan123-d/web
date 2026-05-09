from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import json
import os
import re

try:
    import openai
except ImportError:
    openai = None

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    difficulty = db.Column(db.String(50), default='Medium')
    topic = db.Column(db.String(120), default='General')
    tags = db.Column(db.String(250), default='')
    status = db.Column(db.String(50), default='todo')
    code = db.Column(db.Text, default='')
    notes = db.Column(db.Text, default='')
    solved = db.Column(db.Boolean, default=False)

    def tag_set(self):
        return {tag.strip().lower() for tag in self.tags.split(',') if tag.strip()}


def recommend_similar(question):
    all_questions = Question.query.filter(Question.id != question.id).all()
    scored = []
    base_tags = question.tag_set()

    for q in all_questions:
        score = 0
        if q.topic == question.topic:
            score += 4
        if q.difficulty == question.difficulty:
            score += 2
        shared_tags = len(base_tags & q.tag_set())
        score += shared_tags * 2
        if q.solved:
            score += 1
        if score > 0:
            scored.append((score, q))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [question for _, question in scored[:6]]


def build_progress_summary(questions):
    total = len(questions)
    solved = sum(1 for q in questions if q.solved)
    review = sum(1 for q in questions if q.status == 'review')
    todo = sum(1 for q in questions if q.status == 'todo')
    percent = round((solved / total) * 100) if total else 0
    return {
        'total': total,
        'solved': solved,
        'review': review,
        'todo': todo,
        'percent': percent,
    }


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

if openai and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


def ai_generate_questions_local(topic, tags, difficulty, max_results=6):
    topic = topic.strip()
    tags = tags.strip()
    difficulty = difficulty.strip() or 'Medium'
    tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    topic_name = topic.title() if topic else 'General'

    existing_titles = {q.title.lower() for q in Question.query.all() if q.title}
    suggestions = []

    base_terms = [topic_name] + [tag.title() for tag in tags_list]
    if not base_terms:
        base_terms = ['Array', 'Graph', 'String', 'Tree', 'Dynamic Programming']

    templates = [
        '{difficulty} {term} problem',
        '{difficulty} {term} challenge',
        '{difficulty} {term} optimization',
        '{difficulty} {term} with edge cases',
        '{difficulty} {term} using {extra}',
        '{difficulty} {term} and constraints',
    ]
    extras = [tag.title() for tag in tags_list] or [topic_name]

    for term in base_terms:
        for template in templates:
            if '{extra}' in template:
                for extra in extras:
                    title = template.format(difficulty=difficulty, term=term, extra=extra)
                    if title.lower() in existing_titles:
                        continue
                    if title in [item['title'] for item in suggestions]:
                        continue
                    suggestions.append({
                        'title': title,
                        'topic': topic_name,
                        'difficulty': difficulty,
                        'tags': ', '.join(tags_list) if tags_list else 'generated',
                    })
            else:
                title = template.format(difficulty=difficulty, term=term)
                if title.lower() in existing_titles:
                    continue
                if title in [item['title'] for item in suggestions]:
                    continue
                suggestions.append({
                    'title': title,
                    'topic': topic_name,
                    'difficulty': difficulty,
                    'tags': ', '.join(tags_list) if tags_list else 'generated',
                })

            if len(suggestions) >= max_results:
                break
        if len(suggestions) >= max_results:
            break

    if len(suggestions) < max_results:
        fallback_count = 1
        while len(suggestions) < max_results:
            title = f"{difficulty} {topic_name} question idea {fallback_count}"
            if title.lower() not in existing_titles and title not in [item['title'] for item in suggestions]:
                suggestions.append({
                    'title': title,
                    'topic': topic_name,
                    'difficulty': difficulty,
                    'tags': ', '.join(tags_list) if tags_list else 'generated',
                })
            fallback_count += 1

    return suggestions


def ai_generate_questions_external(topic, tags, difficulty, max_results=6):
    if not openai or not OPENAI_API_KEY:
        return []

    prompt = (
        'You are a DSA question idea generator. Create up to {max_results} unique practice problem titles. '
        'Return valid JSON only as an array of objects with title, topic, difficulty, and tags. '
        'Use the following values exactly and keep titles short and clear. '\
        '\nTopic: {topic}\nTags: {tags}\nDifficulty: {difficulty}\n'
    ).format(max_results=max_results, topic=topic or 'General', tags=tags or 'general', difficulty=difficulty or 'Medium')

    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': 'You generate practice problem titles for data structures and algorithms.'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.7,
            max_tokens=400,
        )

        text = response.choices[0].message['content']
        json_match = re.search(r'\[.*\]', text, re.S)
        if not json_match:
            return []

        items = json.loads(json_match.group(0))
        if not isinstance(items, list):
            return []

        ideas = []
        seen_titles = set()
        for item in items:
            title = item.get('title', '').strip()
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            ideas.append({
                'title': title,
                'topic': item.get('topic', topic.title() if topic else 'General').strip() or (topic.title() if topic else 'General'),
                'difficulty': item.get('difficulty', difficulty).strip() or difficulty,
                'tags': item.get('tags', tags or 'generated').strip() or (tags or 'generated'),
            })
            if len(ideas) >= max_results:
                break

        return ideas
    except Exception:
        return []


def ai_generate_questions(topic, tags, difficulty, max_results=6):
    ideas = ai_generate_questions_external(topic, tags, difficulty, max_results)
    if ideas:
        return ideas
    return ai_generate_questions_local(topic, tags, difficulty, max_results)


@app.route('/')
def home():
    questions = Question.query.order_by(Question.id.desc()).all()
    featured = Question.query.filter_by(solved=False).limit(6).all()
    progress = build_progress_summary(questions)
    return render_template('index.html', questions=questions, featured=featured, progress=progress)


@app.route('/question/<int:question_id>')
def question_page(question_id):
    question = Question.query.get_or_404(question_id)
    suggestions = recommend_similar(question)
    return render_template('question.html', question=question, suggestions=suggestions)


@app.route('/add', methods=['POST'])
def add_question():
    data = request.form
    new_question = Question(
        title=data.get('title', '').strip(),
        difficulty=data.get('difficulty', 'Medium'),
        topic=data.get('topic', 'General').strip(),
        tags=data.get('tags', '').strip(),
        status=data.get('status', 'todo'),
        code=data.get('code', '').strip(),
        notes=data.get('notes', '').strip(),
        solved=(data.get('status') == 'done')
    )
    db.session.add(new_question)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/update_status/<int:question_id>', methods=['POST'])
def update_status(question_id):
    question = Question.query.get_or_404(question_id)
    new_status = request.form.get('status')
    question.status = new_status or question.status
    question.solved = new_status == 'done'
    db.session.commit()
    return jsonify({'success': True, 'status': question.status})


@app.route('/save_suggestion', methods=['POST'])
def save_suggestion():
    data = request.json or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'success': False, 'message': 'Title is required.'}), 400

    existing = Question.query.filter_by(title=title).first()
    if existing:
        return jsonify({'success': False, 'message': 'This question already exists.'}), 409

    new_question = Question(
        title=title,
        topic=(data.get('topic') or 'General').strip() or 'General',
        difficulty=(data.get('difficulty') or 'Medium'),
        tags=(data.get('tags') or '').strip(),
        status='todo',
        code='',
        notes='',
        solved=False,
    )
    db.session.add(new_question)
    db.session.commit()
    return jsonify({'success': True, 'id': new_question.id})


@app.route('/suggestions', methods=['POST'])
def suggestions():
    data = request.json or {}
    topic = data.get('topic', '')
    tags = data.get('tags', '')
    difficulty = data.get('difficulty', 'Medium')
    results = ai_generate_questions(topic, tags, difficulty)
    return jsonify(results)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
