from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # admin, professor, student
    student_id = db.Column(db.String(20), unique=True, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('Enrollment', foreign_keys='Enrollment.student_id', backref='student', lazy='dynamic')
    taught_courses = db.relationship('Course', foreign_keys='Course.professor_id', backref='professor', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy='dynamic')
    assignment_submissions = db.relationship('AssignmentSubmission', foreign_keys='AssignmentSubmission.student_id', backref='student', lazy='dynamic')
    sent_messages = db.relationship('ChatMessage', foreign_keys='ChatMessage.sender_id', backref='sender', lazy='dynamic')
    announcements = db.relationship('Announcement', backref='author', lazy='dynamic')
    forum_posts = db.relationship('ForumPost', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_professor(self):
        return self.role == 'professor'

    def is_student(self):
        return self.role == 'student'

    def get_enrolled_courses(self):
        from app.models.course import Course, Enrollment
        return Course.query.join(Enrollment).filter(
            Enrollment.student_id == self.id,
            Enrollment.is_active == True
        ).all()

    def get_performance_summary(self):
        from app.models.activity import QuizAttempt, AssignmentSubmission
        attempts = QuizAttempt.query.filter_by(student_id=self.id, is_completed=True).all()
        submissions = AssignmentSubmission.query.filter_by(student_id=self.id).all()

        quiz_scores = [a.score for a in attempts if a.score is not None]
        assignment_scores = [s.grade for s in submissions if s.grade is not None]

        all_scores = quiz_scores + assignment_scores
        avg = sum(all_scores) / len(all_scores) if all_scores else 0

        return {
            'total_quizzes': len(attempts),
            'total_assignments': len(submissions),
            'average_score': round(avg, 2),
            'quiz_avg': round(sum(quiz_scores) / len(quiz_scores), 2) if quiz_scores else 0,
            'assignment_avg': round(sum(assignment_scores) / len(assignment_scores), 2) if assignment_scores else 0,
        }

    def __repr__(self):
        return f'<User {self.email}>'