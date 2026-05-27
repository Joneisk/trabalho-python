from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.course import Course, Enrollment, CourseMaterial
from app.models.activity import Quiz, Assignment, QuizAttempt, AssignmentSubmission
from app.models.communication import Announcement, ForumThread, ForumPost, ChatRoom, ChatMessage, Notification, ForumAttachment
from app.models.media import EBook, VideoLesson, InteractiveResource, VideoProgress
from app.utils.storage import upload_to_oci
from app import db
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/library')
@login_required
def library():
    ebooks = EBook.query.filter_by(is_available=True).all()
    categories = db.session.query(EBook.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    return render_template('main/library.html', ebooks=ebooks, categories=categories)


@main_bp.route('/admin/library/manage', methods=['GET', 'POST'])
@login_required
def admin_manage_library():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        category = request.form.get('category')
        description = request.form.get('description')
        file_url = request.form.get('file_url')
        cover_url = request.form.get('cover_url')
        
        ebook = EBook(
            title=title,
            author=author,
            category=category,
            description=description,
            file_url=file_url,
            cover_url=cover_url,
            is_available=True
        )
        db.session.add(ebook)
        db.session.commit()
        flash('E-book adicionado à biblioteca!', 'success')
        return redirect(url_for('main.admin_manage_library'))
        
    ebooks = EBook.query.all()
    return render_template('admin/manage_library.html', ebooks=ebooks)


@main_bp.route('/admin/library/delete/<int:ebook_id>', methods=['POST'])
@login_required
def admin_delete_ebook(ebook_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    ebook = EBook.query.get_or_404(ebook_id)
    db.session.delete(ebook)
    db.session.commit()
    flash('E-book removido com sucesso!', 'success')
    return redirect(url_for('main.admin_manage_library'))


@main_bp.route('/video/heartbeat', methods=['POST'])
@login_required
def video_heartbeat():
    data = request.get_json()
    video_id = data.get('video_id')
    current_time = data.get('current_time')
    
    progress = VideoProgress.query.filter_by(student_id=current_user.id, video_id=video_id).first()
    
    if not progress:
        progress = VideoProgress(student_id=current_user.id, video_id=video_id)
        db.session.add(progress)
    
    if current_time > (progress.last_position or 0):
        progress.last_position = int(current_time)
    
    progress.last_watched = datetime.utcnow()
    
    video = VideoLesson.query.get(video_id)
    if video and video.duration > 0:
        if (current_time / 60) >= (video.duration * 0.9):
            progress.is_completed = True
            
    db.session.commit()
    return jsonify({"status": "success"})


@main_bp.route('/course/<int:course_id>/forum')
@login_required
def forum(course_id):
    course = Course.query.get_or_404(course_id)
    threads = ForumThread.query.filter_by(course_id=course_id).order_by(ForumThread.is_pinned.desc(), ForumThread.created_at.desc()).all()
    return render_template('main/forum_threads.html', course=course, threads=threads)


def create_notification(user_id, title, message, link=None, category='info'):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        category=category
    )
    db.session.add(notification)
    db.session.commit()


@main_bp.route('/notifications')
@login_required
def notifications():
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    return render_template('main/notifications.html', notifications=notifications)


@main_bp.route('/notifications/read/<int:notif_id>')
@login_required
def read_notification(notif_id):
    notification = Notification.query.get_or_404(notif_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    return redirect(request.referrer or url_for('main.dashboard'))


@main_bp.route('/course/<int:course_id>/forum/new', methods=['GET', 'POST'])
@login_required
def new_forum_thread(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash('Título e conteúdo são obrigatórios.', 'danger')
        else:
            thread = ForumThread(course_id=course_id, author_id=current_user.id, title=title, content=content)
            db.session.add(thread)
            db.session.flush()  # To get thread.id

            # Handle attachment
            file = request.files.get('attachment')
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Faz upload para OCI
                oci_url = upload_to_oci(file, f"forum/{filename}")
                
                attachment = ForumAttachment(
                    thread_id=thread.id,
                    file_name=filename,
                    file_url=oci_url or f"/uploads/forum/{filename}",
                    file_type="document" if "." in filename and filename.split(".")[-1] in ["pdf", "doc", "docx"] else "other"
                )
                db.session.add(attachment)

            db.session.commit()
            flash('Tópico criado com sucesso!', 'success')
            return redirect(url_for('main.forum', course_id=course_id))
            
    return render_template('main/new_forum_thread.html', course=course)


@main_bp.route('/course/<int:course_id>/forum/thread/<int:thread_id>', methods=['GET', 'POST'])
@login_required
def forum_thread(course_id, thread_id):
    course = Course.query.get_or_404(course_id)
    thread = ForumThread.query.get_or_404(thread_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        if not content:
            flash('O conteúdo da resposta não pode estar vazio.', 'danger')
        else:
            post = ForumPost(thread_id=thread_id, author_id=current_user.id, content=content)
            db.session.add(post)
            db.session.flush()

            # Handle attachment
            file = request.files.get('attachment')
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Faz upload para OCI
                oci_url = upload_to_oci(file, f"forum/{filename}")
                
                attachment = ForumAttachment(
                    post_id=post.id,
                    file_name=filename,
                    file_url=oci_url or f"/uploads/forum/{filename}",
                    file_type="document"
                )
                db.session.add(attachment)

            db.session.commit()
            flash('Resposta enviada com sucesso!', 'success')
            return redirect(url_for('main.forum_thread', course_id=course_id, thread_id=thread_id))
            
    thread.view_count += 1
    db.session.commit()
    posts = thread.posts.all()
    return render_template('main/forum_view.html', course=course, thread=thread, posts=posts)


@main_bp.route('/course/<int:course_id>/announcements/new', methods=['GET', 'POST'])
@login_required
def new_announcement(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_pinned = 'is_pinned' in request.form
        
        announcement = Announcement(
            course_id=course.id,
            author_id=current_user.id,
            title=title,
            content=content,
            is_pinned=is_pinned
        )
        db.session.add(announcement)
        db.session.commit()

        # Notify all enrolled students
        students = course.enrollments.filter_by(is_active=True).all()
        for enrollment in students:
            create_notification(
                user_id=enrollment.student_id,
                title=f"Novo aviso: {title}",
                message=f"Um novo aviso foi postado no curso {course.title}.",
                link=url_for('main.view_course', course_id=course.id),
                category='announcement'
            )

        flash('Aviso publicado com sucesso!', 'success')
        return redirect(url_for('main.view_course', course_id=course.id))
        
    return render_template('main/new_announcement.html', course=course)


@main_bp.route('/course/<int:course_id>/quiz/<int:quiz_id>')
@login_required
def view_quiz(course_id, quiz_id):
    course = Course.query.get_or_404(course_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt_count = quiz.get_student_attempt_count(current_user.id)
    best_attempt = quiz.get_student_best_attempt(current_user.id)
    
    return render_template('main/quiz_view.html', course=course, quiz=quiz, 
                           attempt_count=attempt_count, best_attempt=best_attempt)


@main_bp.route('/course/<int:course_id>/quiz/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
def take_quiz(course_id, quiz_id):
    course = Course.query.get_or_404(course_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not course.is_student_enrolled(current_user.id):
        flash('Você não está matriculado neste curso.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    attempt_count = quiz.get_student_attempt_count(current_user.id)
    if quiz.max_attempts and attempt_count >= quiz.max_attempts:
        flash('Você já atingiu o limite de tentativas para este quiz.', 'warning')
        return redirect(url_for('main.view_quiz', course_id=course_id, quiz_id=quiz_id))
    
    if request.method == 'POST':
        attempt = QuizAttempt(quiz_id=quiz_id, student_id=current_user.id)
        db.session.add(attempt)
        db.session.flush()

        questions = quiz.questions.all()
        for q in questions:
            selected = request.form.get(f'question_{q.id}')
            is_correct = (selected == q.correct_option)
            answer = QuizAnswer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option=selected,
                is_correct=is_correct
            )
            db.session.add(answer)
        
        attempt.is_completed = True
        attempt.submitted_at = datetime.utcnow()
        attempt.score = attempt.calculate_score()
        db.session.commit()
        
        flash(f'Quiz finalizado! Sua nota: {attempt.score}', 'success')
        return redirect(url_for('main.view_quiz', course_id=course_id, quiz_id=quiz_id))
        
    questions = quiz.questions.all()
    return render_template('main/take_quiz.html', course=course, quiz=quiz, questions=questions)


@main_bp.route('/course/<int:course_id>/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(course_id, assignment_id):
    course = Course.query.get_or_404(course_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = assignment.get_student_submission(current_user.id)
    
    if request.method == 'POST':
        file = request.files.get('file')
        comment = request.form.get('comment')
        
        if not file or not file.filename:
            flash('Por favor, selecione um arquivo para enviar.', 'danger')
        else:
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            
            max_size = assignment.max_file_size_mb * 1024 * 1024
            if file_length > max_size:
                flash(f'O arquivo excede o limite de {assignment.max_file_size_mb}MB.', 'danger')
                return redirect(url_for('main.view_assignment', course_id=course_id, assignment_id=assignment_id))

            filename = secure_filename(file.filename)
            # Faz upload para OCI
            oci_url = upload_to_oci(file, f"assignments/{filename}")
            
            new_submission = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                file_name=filename,
                file_path=oci_url or f"/uploads/assignments/{filename}",
                file_size=file_length,
                comment=comment,
                submitted_at=datetime.utcnow(),
                is_late=assignment.is_overdue()
            )
            db.session.add(new_submission)
            db.session.commit()
            
            create_notification(
                user_id=course.professor_id,
                title="Nova entrega de trabalho",
                message=f"O aluno {current_user.name} enviou o trabalho '{assignment.title}'.",
                link=url_for('main.view_submissions', course_id=course.id, assignment_id=assignment.id),
                category='activity'
            )

            flash('Trabalho enviado com sucesso!', 'success')
            return redirect(url_for('main.view_assignment', course_id=course_id, assignment_id=assignment_id))
        
    return render_template('main/assignment_view.html', course=course, 
                           assignment=assignment, submission=submission)


@main_bp.route('/course/<int:course_id>/assignment/grade/<int:submission_id>', methods=['POST'])
@login_required
def grade_submission(course_id, submission_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    grade = request.form.get('grade', type=float)
    feedback = request.form.get('feedback')
    
    submission.grade = grade
    submission.feedback = feedback
    submission.graded_at = datetime.utcnow()
    submission.graded_by = current_user.id
    db.session.commit()
    
    create_notification(
        user_id=submission.student_id,
        title="Trabalho avaliado",
        message=f"Sua entrega para '{submission.assignment.title}' foi avaliada. Nota: {grade}",
        link=url_for('main.view_assignment', course_id=course.id, assignment_id=submission.assignment_id),
        category='grade'
    )
    
    flash('Avaliação salva com sucesso!', 'success')
    return redirect(url_for('main.view_submissions', course_id=course.id, assignment_id=submission.assignment_id))


@main_bp.route('/course/<int:course_id>/quiz/grade/<int:attempt_id>', methods=['POST'])
@login_required
def grade_quiz_attempt(course_id, attempt_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    feedback = request.form.get('feedback')
    
    attempt.feedback = feedback
    attempt.is_graded = True
    attempt.graded_at = datetime.utcnow()
    db.session.commit()
    
    create_notification(
        user_id=attempt.student_id,
        title="Feedback de Quiz disponível",
        message=f"O professor deixou um feedback no seu quiz '{attempt.quiz.title}'.",
        link=url_for('main.view_quiz', course_id=course.id, quiz_id=attempt.quiz_id),
        category='grade'
    )
    
    flash('Feedback salvo com sucesso!', 'success')
    return redirect(url_for('main.quiz_analytics', course_id=course.id, quiz_id=attempt.quiz_id))


@main_bp.route('/course/<int:course_id>/video/<int:video_id>')
@login_required
def view_video(course_id, video_id):
    course = Course.query.get_or_404(course_id)
    video = VideoLesson.query.get_or_404(video_id)
    
    if not course.is_student_enrolled(current_user.id) and not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    video.view_count += 1
    db.session.commit()
    
    progress = video.get_student_progress(current_user.id)
    return render_template('main/video_view.html', course=course, video=video, progress=progress)


@main_bp.route('/course/<int:course_id>/interactive/<int:resource_id>')
@login_required
def view_interactive(course_id, resource_id):
    course = Course.query.get_or_404(course_id)
    resource = InteractiveResource.query.get_or_404(resource_id)
    
    if not course.is_student_enrolled(current_user.id) and not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    return render_template('main/interactive_view.html', course=course, resource=resource)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()

    if current_user.is_admin():
        stats = {
            'total_students': User.query.filter_by(role='student').count(),
            'total_professors': User.query.filter_by(role='professor').count(),
            'total_courses': Course.query.count(),
            'active_courses': Course.query.filter_by(status='active').count(),
            'total_enrollments': Enrollment.query.filter_by(is_active=True).count(),
            'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
            'recent_courses': Course.query.order_by(Course.created_at.desc()).limit(5).all(),
        }
        return render_template('admin/dashboard.html', stats=stats)

    elif current_user.is_professor():
        courses = current_user.taught_courses.filter_by(status='active').all()
        course_ids = [c.id for c in courses]

        pending_submissions = []
        if course_ids:
            pending_submissions = AssignmentSubmission.query.join(Assignment).filter(
                Assignment.course_id.in_(course_ids),
                AssignmentSubmission.grade.is_(None)
            ).order_by(AssignmentSubmission.submitted_at.desc()).limit(5).all()

        announcements = Announcement.query.filter(
            Announcement.course_id.in_(course_ids)
        ).order_by(Announcement.created_at.desc()).limit(5).all()

        return render_template('main/dashboard_professor.html',
                               courses=courses,
                               pending_submissions=pending_submissions,
                               announcements=announcements,
                               now=now)
    else:
        enrolled_courses = current_user.get_enrolled_courses()
        course_ids = [c.id for c in enrolled_courses]

        upcoming_quizzes = []
        upcoming_assignments = []

        if course_ids:
            upcoming_quizzes = Quiz.query.filter(
                Quiz.course_id.in_(course_ids),
                Quiz.is_published == True,
                Quiz.due_date >= now,
                Quiz.due_date <= now + timedelta(days=14)
            ).order_by(Quiz.due_date).limit(5).all()

            upcoming_assignments = Assignment.query.filter(
                Assignment.course_id.in_(course_ids),
                Assignment.is_published == True,
                Assignment.due_date >= now,
                Assignment.due_date <= now + timedelta(days=14)
            ).order_by(Assignment.due_date).limit(5).all()

        announcements = Announcement.query.filter(
            (Announcement.course_id.in_(course_ids)) |
            (Announcement.course_id.is_(None))
        ).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(8).all()

        performance = current_user.get_performance_summary()

        return render_template('main/dashboard_student.html',
                               courses=enrolled_courses,
                               upcoming_quizzes=upcoming_quizzes,
                               upcoming_assignments=upcoming_assignments,
                               announcements=announcements,
                               performance=performance,
                               now=now)


@main_bp.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    users = User.query.order_by(User.name).all()
    return render_template('admin/users.html', users=users)


@main_bp.route('/admin/courses')
@login_required
def admin_courses():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)


@main_bp.route('/admin/courses/new', methods=['GET', 'POST'])
@login_required
def admin_new_course():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    professors = User.query.filter_by(role='professor').all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        code = request.form.get('code')
        professor_id = request.form.get('professor_id')
        semester = request.form.get('semester')
        description = request.form.get('description')
        
        if not title or not code or not professor_id:
            flash('Preencha todos os campos obrigatórios.', 'danger')
        elif Course.query.filter_by(code=code).first():
            flash('Este código de curso já existe.', 'danger')
        else:
            course = Course(
                title=title,
                code=code,
                professor_id=professor_id,
                semester=semester,
                description=description
            )
            db.session.add(course)
            db.session.commit()
            flash('Curso criado com sucesso!', 'success')
            return redirect(url_for('main.admin_courses'))
            
    return render_template('admin/new_course.html', professors=professors)


@main_bp.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
def admin_new_user():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        
        if not name or not email or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'danger')
        else:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('main.admin_users'))
            
    return render_template('admin/new_user.html')


@main_bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.role = request.form.get('role', 'student')
        user.is_active = 'is_active' in request.form
        
        password = request.form.get('password')
        if password:
            user.set_password(password)
            
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('main.admin_users'))
        
    return render_template('admin/edit_user.html', user=user)


@main_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('Usuário excluído com sucesso!', 'success')
        
    return redirect(url_for('main.admin_users'))


@main_bp.route('/admin/courses/enroll', methods=['GET', 'POST'])
@login_required
def admin_enroll_student():
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    courses = Course.query.filter_by(status='active').all()
    students = User.query.filter_by(role='student', is_active=True).all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        
        if not student_id or not course_id:
            flash('Selecione um aluno e um curso.', 'danger')
        else:
            existing = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    db.session.commit()
                    flash('Matrícula reativada com sucesso!', 'success')
                else:
                    flash('Este aluno já está matriculado neste curso.', 'info')
            else:
                enrollment = Enrollment(student_id=student_id, course_id=course_id)
                db.session.add(enrollment)
                db.session.commit()
                flash('Aluno matriculado com sucesso!', 'success')
            return redirect(url_for('main.admin_courses'))
            
    return render_template('admin/enroll_student.html', courses=courses, students=students)


@main_bp.route('/admin/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_course(course_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    course = Course.query.get_or_404(course_id)
    professors = User.query.filter_by(role='professor').all()
    
    if request.method == 'POST':
        course.title = request.form.get('title')
        course.code = request.form.get('code')
        course.professor_id = request.form.get('professor_id')
        course.semester = request.form.get('semester')
        course.description = request.form.get('description')
        course.status = request.form.get('status', 'active')
        
        db.session.commit()
        flash('Curso atualizado com sucesso!', 'success')
        return redirect(url_for('main.admin_courses'))
        
    return render_template('admin/edit_course.html', course=course, professors=professors)


@main_bp.route('/admin/courses/delete/<int:course_id>', methods=['POST'])
@login_required
def admin_delete_course(course_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Curso excluído com sucesso!', 'success')
    return redirect(url_for('main.admin_courses'))


@main_bp.route('/course/<int:course_id>/materials/manage', methods=['GET', 'POST'])
@login_required
def manage_materials(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        file_type = request.form.get('file_type')
        external_url = request.form.get('external_url')
        
        material = CourseMaterial(
            course_id=course.id,
            title=title,
            description=description,
            file_type=file_type,
            external_url=external_url,
            uploaded_by=current_user.id
        )
        db.session.add(material)
        db.session.commit()
        flash('Material adicionado com sucesso!', 'success')
        return redirect(url_for('main.manage_materials', course_id=course.id))
        
    materials = course.materials.all()
    return render_template('main/manage_materials.html', course=course, materials=materials)


@main_bp.route('/course/<int:course_id>/materials/delete/<int:material_id>', methods=['POST'])
@login_required
def delete_material(course_id, material_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    material = CourseMaterial.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash('Material removido com sucesso!', 'success')
    return redirect(url_for('main.manage_materials', course_id=course.id))


@main_bp.route('/course/<int:course_id>/activities/manage')
@login_required
def manage_activities(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    quizzes = course.quizzes.all()
    assignments = course.assignments.all()
    return render_template('main/manage_activities.html', course=course, quizzes=quizzes, assignments=assignments)


@main_bp.route('/course/<int:course_id>/chat/messages')
@login_required
def chat_messages(course_id):
    last_id = request.args.get('last_id', 0, type=int)
    room = ChatRoom.query.filter_by(course_id=course_id).first()
    if not room:
        return jsonify([])
    messages = ChatMessage.query.filter(ChatMessage.room_id == room.id, ChatMessage.id > last_id).order_by(ChatMessage.id.asc()).all()
    return jsonify([{
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': msg.sender.name,
        'content': msg.content,
        'timestamp': msg.sent_at.strftime('%H:%M')
    } for msg in messages])


@main_bp.route('/course/<int:course_id>/meet')
@login_required
def course_meet(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id and not course.is_student_enrolled(current_user.id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    from app.models.communication import VideoConference
    conf = VideoConference.query.filter_by(course_id=course_id, status='ongoing').first()
    if not conf:
        if current_user.is_professor() or current_user.is_admin():
            conf = VideoConference(
                course_id=course_id, 
                host_id=current_user.id, 
                title=f"Aula Síncrona: {course.title}", 
                scheduled_at=datetime.utcnow(), 
                status='ongoing'
            )
            db.session.add(conf)
            db.session.commit()
        else:
            flash('Nenhuma aula síncrona está acontecendo no momento. Aguarde o professor iniciar.', 'info')
            return redirect(url_for('main.view_course', course_id=course.id))
            
    return render_template('main/meet.html', course=course, conf=conf)


@main_bp.route('/course/<int:course_id>/analytics')
@login_required
def course_analytics(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    enrollments = course.enrollments.filter_by(is_active=True).all()
    students = [e.student for e in enrollments]
    
    # Calculate average grades
    assignments = course.assignments.all()
    quizzes = course.quizzes.all()
    
    student_stats = []
    for student in students:
        total_score = 0
        total_max = 0
        for task in assignments:
            sub = task.get_student_submission(student.id)
            if sub and sub.grade is not None:
                total_score += sub.grade
                total_max += task.max_score
        
        for quiz in quizzes:
            attempt = quiz.get_student_best_attempt(student.id)
            if attempt and attempt.score is not None:
                total_score += attempt.score
                total_max += 10 # quizzes are 0-10
                
        avg = round((total_score / total_max) * 10, 2) if total_max > 0 else 0
        student_stats.append({
            'student': student,
            'avg': avg
        })
        
    student_stats.sort(key=lambda x: x['avg'], reverse=True)
    
    return render_template('main/course_analytics.html', course=course, stats=student_stats, 
                           total_students=len(students), total_assignments=len(assignments), total_quizzes=len(quizzes))

@main_bp.route('/course/<int:course_id>/chat', methods=['GET', 'POST'])
@login_required
def chat(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check access
    if not current_user.is_admin() and course.professor_id != current_user.id and not course.is_student_enrolled(current_user.id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    room = ChatRoom.query.filter_by(course_id=course_id).first()
    if not room:
        room = ChatRoom(course_id=course_id, name=f"Chat: {course.title}")
        db.session.add(room)
        db.session.commit()
        
    if request.method == 'POST':
        content = request.form.get('content')
        if content and content.strip():
            msg = ChatMessage(room_id=room.id, sender_id=current_user.id, content=content.strip())
            db.session.add(msg)
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'id': msg.id,
                    'sender_name': current_user.name,
                    'content': msg.content,
                    'timestamp': msg.sent_at.strftime('%H:%M')
                })
            return redirect(url_for('main.chat', course_id=course_id))
            
    messages = room.messages.order_by(ChatMessage.sent_at.asc()).all()
    return render_template('main/chat.html', course=course, messages=messages)


@main_bp.route('/course/<int:course_id>/activities/quiz/new', methods=['GET', 'POST'])
@login_required
def new_quiz(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        instructions = request.form.get('instructions')
        time_limit = request.form.get('time_limit', type=int)
        max_attempts = request.form.get('max_attempts', type=int)
        due_date_str = request.form.get('due_date')
        
        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
        quiz = Quiz(
            course_id=course.id,
            title=title,
            description=description,
            instructions=instructions,
            time_limit=time_limit,
            max_attempts=max_attempts,
            due_date=due_date,
            is_published=True
        )
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz criado com sucesso! Agora você pode adicionar questões.', 'success')
        return redirect(url_for('main.manage_activities', course_id=course.id))
        
    return render_template('main/new_quiz.html', course=course)


@main_bp.route('/course/<int:course_id>/activities/assignment/new', methods=['GET', 'POST'])
@login_required
def new_assignment(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        instructions = request.form.get('instructions')
        max_score = request.form.get('max_score', type=float)
        allowed_extensions = request.form.get('allowed_extensions', '.pdf,.doc,.docx')
        due_date_str = request.form.get('due_date')
        is_group = request.form.get('is_group') == 'yes'
        
        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
        assignment = Assignment(
            course_id=course.id,
            title=title,
            description=description,
            instructions=instructions,
            max_score=max_score,
            allowed_extensions=allowed_extensions,
            due_date=due_date,
            is_group=is_group,
            is_published=True
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('main.manage_activities', course_id=course.id))
        
    return render_template('main/new_assignment.html', course=course)


@main_bp.route('/course/<int:course_id>/activities/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(course_id, quiz_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        quiz.instructions = request.form.get('instructions')
        quiz.time_limit = request.form.get('time_limit', type=int)
        quiz.max_attempts = request.form.get('max_attempts', type=int)
        due_date_str = request.form.get('due_date')
        
        if due_date_str:
            quiz.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
        db.session.commit()
        flash('Quiz atualizado com sucesso!', 'success')
        return redirect(url_for('main.manage_activities', course_id=course.id))
        
    return render_template('main/edit_quiz.html', course=course, quiz=quiz)


@main_bp.route('/course/<int:course_id>/activities/quiz/analytics/<int:quiz_id>')
@login_required
def quiz_analytics(course_id, quiz_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    attempts = quiz.attempts.order_by(QuizAttempt.submitted_at.desc()).all()
    
    return render_template('main/quiz_analytics.html', course=course, quiz=quiz, attempts=attempts)


@main_bp.route('/course/<int:course_id>/activities/assignment/edit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def edit_assignment(course_id, assignment_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    
    if request.method == 'POST':
        assignment.title = request.form.get('title')
        assignment.description = request.form.get('description')
        assignment.instructions = request.form.get('instructions')
        assignment.max_score = request.form.get('max_score', type=float)
        assignment.allowed_extensions = request.form.get('allowed_extensions')
        due_date_str = request.form.get('due_date')
        
        if due_date_str:
            assignment.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            
        db.session.commit()
        flash('Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('main.manage_activities', course_id=course.id))
        
    return render_template('main/edit_assignment.html', course=course, assignment=assignment)


@main_bp.route('/course/<int:course_id>/activities/assignment/submissions/<int:assignment_id>')
@login_required
def view_submissions(course_id, assignment_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = assignment.submissions.order_by(AssignmentSubmission.submitted_at.desc()).all()
    
    return render_template('main/view_submissions.html', course=course, assignment=assignment, submissions=submissions)


@main_bp.route('/course/<int:course_id>/videos/manage', methods=['GET', 'POST'])
@login_required
def manage_videos(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        video_url = request.form.get('video_url')
        thumbnail_url = request.form.get('thumbnail_url')
        duration = request.form.get('duration', type=int)
        
        video = VideoLesson(
            course_id=course.id,
            title=title,
            description=description,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration=duration
        )
        db.session.add(video)
        db.session.commit()
        flash('Vídeo-aula adicionada com sucesso!', 'success')
        return redirect(url_for('main.manage_videos', course_id=course.id))
        
    videos = course.video_lessons.all()
    return render_template('main/manage_videos.html', course=course, videos=videos)


@main_bp.route('/course/<int:course_id>/videos/delete/<int:video_id>', methods=['POST'])
@login_required
def delete_video(course_id, video_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin() and course.professor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    video = VideoLesson.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    flash('Vídeo-aula removida com sucesso!', 'success')
    return redirect(url_for('main.manage_videos', course_id=course.id))


@main_bp.route('/course/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    can_access = False
    if current_user.is_admin():
        can_access = True
    elif current_user.is_professor() and course.professor_id == current_user.id:
        can_access = True
    elif course.is_student_enrolled(current_user.id):
        can_access = True
        
    if not can_access:
        flash('Você não tem permissão para acessar este curso.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    materials = course.materials.order_by(CourseMaterial.order).all()
    announcements = course.announcements.order_by(Announcement.created_at.desc()).all()
    threads = course.forum_threads.order_by(ForumThread.created_at.desc()).limit(5).all()
    
    return render_template('main/course_view.html', course=course, materials=materials, 
                           announcements=announcements, threads=threads)
