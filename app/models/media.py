from app import db
from datetime import datetime


class VideoLesson(db.Model):
    __tablename__ = 'video_lessons'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    duration = db.Column(db.Integer)  # minutes
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    transcript = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress_records = db.relationship('VideoProgress', backref='video', lazy='dynamic',
                                        cascade='all, delete-orphan')

    def get_student_progress(self, student_id):
        return self.progress_records.filter_by(student_id=student_id).first()

    def __repr__(self):
        return f'<VideoLesson {self.title}>'


class VideoProgress(db.Model):
    __tablename__ = 'video_progress'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video_lessons.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    watch_percentage = db.Column(db.Float, default=0.0)
    last_position = db.Column(db.Integer, default=0)  # seconds
    is_completed = db.Column(db.Boolean, default=False)
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('video_id', 'student_id', name='unique_video_progress'),)


class EBook(db.Model):
    __tablename__ = 'ebooks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(200))
    description = db.Column(db.Text)
    file_url = db.Column(db.String(500))
    cover_url = db.Column(db.String(500))
    category = db.Column(db.String(100))
    isbn = db.Column(db.String(20))
    pages = db.Column(db.Integer)
    language = db.Column(db.String(30), default='Português')
    is_available = db.Column(db.Boolean, default=True)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<EBook {self.title}>'


class InteractiveResource(db.Model):
    __tablename__ = 'interactive_resources'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50))  # simulation, game, exercise
    url = db.Column(db.String(500))
    thumbnail = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('interactive_resources', lazy='dynamic'))

    def __repr__(self):
        return f'<InteractiveResource {self.title}>'