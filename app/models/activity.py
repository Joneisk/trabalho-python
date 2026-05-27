from app import db
from datetime import datetime


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    time_limit = db.Column(db.Integer, nullable=True)  # minutes, None = unlimited
    max_attempts = db.Column(db.Integer, default=1)
    due_date = db.Column(db.DateTime, nullable=True)
    available_from = db.Column(db.DateTime, nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    shuffle_questions = db.Column(db.Boolean, default=False)
    show_correct_answers = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic',
                                 cascade='all, delete-orphan', order_by='QuizQuestion.order')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')

    def total_points(self):
        return sum(q.points for q in self.questions.all())

    def get_student_best_attempt(self, student_id):
        return QuizAttempt.query.filter_by(
            quiz_id=self.id, student_id=student_id, is_completed=True
        ).order_by(QuizAttempt.score.desc()).first()

    def get_student_attempt_count(self, student_id):
        return QuizAttempt.query.filter_by(quiz_id=self.id, student_id=student_id).count()

    def is_available(self):
        now = datetime.utcnow()
        if self.available_from and now < self.available_from:
            return False
        if self.due_date and now > self.due_date:
            return False
        return self.is_published

    def __repr__(self):
        return f'<Quiz {self.title}>'


class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # A, B, C, D
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Float, default=1.0)
    order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<QuizQuestion {self.id}>'


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float, nullable=True)  # percentage 0-10
    time_spent = db.Column(db.Integer, nullable=True)  # seconds
    feedback = db.Column(db.Text, nullable=True)
    is_graded = db.Column(db.Boolean, default=False)
    graded_at = db.Column(db.DateTime, nullable=True)

    answers = db.relationship('QuizAnswer', backref='attempt', lazy='dynamic',
                               cascade='all, delete-orphan')

    def calculate_score(self):
        total_points = self.quiz.total_points()
        if total_points == 0:
            return 0
        earned = sum(
            ans.question.points for ans in self.answers.all()
            if ans.is_correct
        )
        return round((earned / total_points) * 10, 2)

    def get_percentage(self):
        if self.score is None:
            return 0
        return round(self.score * 10, 1)

    def __repr__(self):
        return f'<QuizAttempt quiz={self.quiz_id} student={self.student_id}>'


class QuizAnswer(db.Model):
    __tablename__ = 'quiz_answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_questions.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True)  # A, B, C, D
    is_correct = db.Column(db.Boolean, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('QuizQuestion')

    def __repr__(self):
        return f'<QuizAnswer attempt={self.attempt_id} q={self.question_id}>'


class Assignment(db.Model):
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=True)
    available_from = db.Column(db.DateTime, nullable=True)
    max_score = db.Column(db.Float, default=10.0)
    allowed_extensions = db.Column(db.String(200), default='pdf,doc,docx,zip,py,java,txt')
    max_file_size_mb = db.Column(db.Integer, default=100)
    allow_late = db.Column(db.Boolean, default=True)
    late_penalty_percent = db.Column(db.Float, default=10.0)
    is_published = db.Column(db.Boolean, default=False)
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def get_student_submission(self, student_id):
        return self.submissions.filter_by(student_id=student_id).order_by(
            AssignmentSubmission.submitted_at.desc()
        ).first()

    def is_overdue(self):
        return self.due_date and datetime.utcnow() > self.due_date

    def submission_count(self):
        return self.submissions.count()

    def __repr__(self):
        return f'<Assignment {self.title}>'


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=True)
    file_name = db.Column(db.String(200), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)
    grade = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    grader = db.relationship('User', foreign_keys=[graded_by])

    def __repr__(self):
        return f'<AssignmentSubmission assignment={self.assignment_id} student={self.student_id}>'