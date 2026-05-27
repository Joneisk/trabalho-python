from app import db
from datetime import datetime


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    professor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    semester = db.Column(db.String(10), nullable=False)
    credits = db.Column(db.Integer, default=4)
    max_students = db.Column(db.Integer, default=50)
    status = db.Column(db.String(20), default='active')  # active, archived, draft
    syllabus = db.Column(db.Text)
    cover_image = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    materials = db.relationship('CourseMaterial', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    video_lessons = db.relationship('VideoLesson', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    forum_threads = db.relationship('ForumThread', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    chat_rooms = db.relationship('ChatRoom', backref='course', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def enrolled_count(self):
        return self.enrollments.filter_by(is_active=True).count()

    def is_student_enrolled(self, user_id):
        return self.enrollments.filter_by(student_id=user_id, is_active=True).first() is not None

    def get_average_grade(self):
        from app.models.activity import QuizAttempt, AssignmentSubmission
        quiz_ids = [q.id for q in self.quizzes.all()]
        assignment_ids = [a.id for a in self.assignments.all()]

        scores = []
        if quiz_ids:
            attempts = QuizAttempt.query.filter(
                QuizAttempt.quiz_id.in_(quiz_ids),
                QuizAttempt.is_completed == True,
                QuizAttempt.score.isnot(None)
            ).all()
            scores.extend([a.score for a in attempts])

        if assignment_ids:
            subs = AssignmentSubmission.query.filter(
                AssignmentSubmission.assignment_id.in_(assignment_ids),
                AssignmentSubmission.grade.isnot(None)
            ).all()
            scores.extend([s.grade for s in subs])

        return round(sum(scores) / len(scores), 2) if scores else 0

    def __repr__(self):
        return f'<Course {self.code}: {self.title}>'


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    final_grade = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='enrolled')  # enrolled, completed, dropped

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),)

    def __repr__(self):
        return f'<Enrollment student={self.student_id} course={self.course_id}>'


class CourseMaterial(db.Model):
    __tablename__ = 'course_materials'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(300))
    file_type = db.Column(db.String(50))  # pdf, doc, ppt, video, link
    file_size = db.Column(db.Integer)  # bytes
    external_url = db.Column(db.String(300))
    order = db.Column(db.Integer, default=0)
    week_number = db.Column(db.Integer, nullable=True)
    is_visible = db.Column(db.Boolean, default=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CourseMaterial {self.title}>'