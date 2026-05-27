from app import db
from datetime import datetime


class Announcement(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)  # None = global
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Announcement {self.title}>'


class ForumThread(db.Model):
    __tablename__ = 'forum_threads'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = db.relationship('ForumPost', backref='thread', lazy='dynamic',
                             cascade='all, delete-orphan', order_by='ForumPost.created_at')
    author = db.relationship('User', foreign_keys=[author_id])
    attachments = db.relationship('ForumAttachment', backref='thread', lazy='dynamic', cascade='all, delete-orphan')

    def post_count(self):
        return self.posts.count()

    def last_post(self):
        return self.posts.order_by(ForumPost.created_at.desc()).first()

    def __repr__(self):
        return f'<ForumThread {self.title}>'


class ForumPost(db.Model):
    __tablename__ = 'forum_posts'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_threads.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    is_solution = db.Column(db.Boolean, default=False)
    upvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = db.relationship('ForumPost', backref=db.backref('parent', remote_side='ForumPost.id'), lazy='dynamic')
    attachments = db.relationship('ForumAttachment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ForumPost thread={self.thread_id}>'


class ForumAttachment(db.Model):
    __tablename__ = 'forum_attachments'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_threads.id'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    file_name = db.Column(db.String(200), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # document, video, image, audio
    file_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ForumAttachment {self.file_name}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(50), default='info')  # announcement, grade, activity, forum
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Notification {self.title}>'


class ChatRoom(db.Model):
    __tablename__ = 'chat_rooms'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    room_type = db.Column(db.String(20), default='course')  # course, direct, group
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('ChatMessage', backref='room', lazy='dynamic',
                                cascade='all, delete-orphan', order_by='ChatMessage.sent_at')

    def __repr__(self):
        return f'<ChatRoom {self.name}>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_rooms.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, image
    file_url = db.Column(db.String(300), nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<ChatMessage room={self.room_id}>'


class VideoConference(db.Model):
    __tablename__ = 'video_conferences'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    meeting_url = db.Column(db.String(500))
    meeting_id = db.Column(db.String(100))
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=90)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, ongoing, ended, cancelled
    recording_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('conferences', lazy='dynamic'))
    host = db.relationship('User', foreign_keys=[host_id])

    def __repr__(self):
        return f'<VideoConference {self.title}>'