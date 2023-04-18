import json
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.models import User
from courses.models import Course
from professors.models import Professors
from attribution.models import TeacherCourseSelection, TeacherQueuePosition
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse

#from .task import spleepy, verifyTimeToSelect

startTimeToSelect = timezone.now()
from django.utils.translation import gettext as _
from django.utils.translation import get_language, activate, gettext
from django.urls import reverse
from django.http import HttpResponseRedirect


def is_superuser(user):
    return user.is_superuser

@transaction.atomic
def attribution(request):
    global startTimeToSelect
    if request.method == 'POST':
        tabela_data = json.loads(request.POST['tabela_data'])       
        startTimeToSelect = timezone.now()
        print(startTimeToSelect.strftime("%H:%M:%S"))
        for professorInQueue in tabela_data:
            professor_id = professorInQueue[3]
            position = professorInQueue[0]
            professor = Professors.objects.get(id=professor_id)
            if(TeacherQueuePosition.objects.filter(teacher=professor).exists()):
                TeacherQueuePosition.objects.filter(teacher=professor).update(position=position)
            else:
                add_teacher_to_queue(professor,position)    

    is_next = False
    timeLeft = 0
    if request.method == 'GET':
        
        print("StartTimeToSelect: ", startTimeToSelect.strftime("%H:%M:%S"))
        nextTeacher = TeacherQueuePosition.objects.filter(position=1);
        teacher = nextTeacher.get().teacher
        if(request.user.is_authenticated and nextTeacher is not None and nextTeacher.get().teacher == request.user):
            timeLeft = ((startTimeToSelect + timezone.timedelta(seconds=40)) - timezone.now()).total_seconds()
            print(timeLeft)
            print(nextTeacher)
            is_next = True
            if(timeLeft < 0):
                timeLeft = 0
                teacherToEndOfQueue(teacher, nextTeacher)          
                startTimeToSelect = timezone.now()     

    data = {
        'timeLeft': timeLeft,
        'is_next': is_next,
        'user': request.user,
        'professorsInQueue': TeacherQueuePosition.objects.select_related('teacher').order_by('position').all(),
        'courses': Course.objects.filter(teachercourseselection__isnull=True).distinct()
    }
    return render(request, 'attribution/attribution.html', data)

@user_passes_test(is_superuser)
def queueSetup(request):
    trans = translate(language='en')
    data = {
        'professors': Professors.objects.all(),
        'text': trans
    }
    return render(request, 'attribution/queueSetup.html', data)

def translate(language):
    cur_language = get_language()
    try:
        activate(language)
        text = gettext('Search')
        text = gettext('entries') #identifica o que mudar
    finally:
        activate(cur_language)
    return text

@transaction.atomic
def teacherToEndOfQueue(teacher, queue_position):
    queue_position.delete()
    queue_size = TeacherQueuePosition.objects.count()
    for teacherQueuePosition in TeacherQueuePosition.objects.all():
        if teacherQueuePosition.position > 1:
            teacherQueuePosition.position = teacherQueuePosition.position - 1
            teacherQueuePosition.save()
    position = queue_size + 1
    TeacherQueuePosition.objects.create(teacher=teacher, position=position)
    
    print("Time's up! You have been moved to the end of the queue.")

@transaction.atomic
def teacherSelectCourse(teacher, CourseSelected, queue_position):
    selected_course = Course.objects.get(id=CourseSelected)
    TeacherCourseSelection.objects.create(teacher=teacher, course=selected_course)
    #atualiza a o curso, colocando um prof nele
    Course.objects.filter(id=selected_course.id).update(teacher=teacher)
    # deleta o prof da fila

    queue_position.delete()
    # atualiza a posição dos outros profs
    
    for teacherQueuePosition in TeacherQueuePosition.objects.all():
        if teacherQueuePosition.position > 1:
            teacherQueuePosition.position = teacherQueuePosition.position - 1
            teacherQueuePosition.save()
    print(f"{teacher} selected {selected_course.title}")

@transaction.atomic
def selectCourse(request):
    global startTimeToSelect
    if request.method == 'POST':
        CourseSelected = request.POST.get("SelectCourse")
        teacher = request.user

        queue_position = TeacherQueuePosition.objects.filter(position=1);

        if queue_position is None or queue_position.get().teacher != teacher:
            raise ValueError("Teacher is not in the queue")

        data = {
            'course': CourseSelected,
        }

        if(CourseSelected == None):
           # se n selecionou vai p final da fila
            teacherToEndOfQueue(teacher,queue_position)
            startTimeToSelect = timezone.now()
            return render(request, 'attribution/selectCourse.html',data)
        else:
            teacherSelectCourse(teacher, CourseSelected, queue_position)
            startTimeToSelect = timezone.now()

        return render(request, 'attribution/selectCourse.html', data)
            
    

@transaction.atomic
def add_teacher_to_queue(teacher,positionInput):
    position = positionInput
    TeacherQueuePosition.objects.create(teacher=teacher, position=position)

@transaction.atomic
def select_course(teacher, StartTimeToSelect):
    # pega o 1o prof da lista
    queue_position = TeacherQueuePosition.objects.filter(position=1);

    if queue_position is None or queue_position.get().teacher != teacher:
        raise ValueError("Teacher is not in the queue")

    # pega os cursos disponíoveis
    available_courses = Course.objects.filter(teachercourseselection__isnull=True).distinct()

    # mostra os cursos disponiveis
    selected_course = None
    for course in available_courses:
        print(f"{course.id}: {course.title}")
    while not selected_course:

        course_id = input("Select a course ID: ")
        try:
            selected_course = Course.objects.get(id=course_id)
            
        except Course.DoesNotExist:
            print("Invalid course ID")

    # ve se selecionou dentro de 1 minutio
    print("Now: ", timezone.now().strftime("%H:%M:%S"))
    print("StartTimeToSelect: ", StartTimeToSelect.strftime("%H:%M:%S"))
    print("Now - StartTimeToSelect (totalsecond): ", (timezone.now() - StartTimeToSelect ).total_seconds())
    if (timezone.now() - StartTimeToSelect ).total_seconds() > 40:
        # se n selecionou vai p final da fila
        queue_position.delete()
        queue_size = TeacherQueuePosition.objects.count()
        for teacherQueuePosition in TeacherQueuePosition.objects.all():
            if teacherQueuePosition.position > 1:
                teacherQueuePosition.position = teacherQueuePosition.position - 1
                teacherQueuePosition.save()
        position = queue_size + 1
        TeacherQueuePosition.objects.create(teacher=teacher, position=position)
        
        print("Time's up! You have been moved to the end of the queue.")
    else:
        # salva a seleção do curso
        TeacherCourseSelection.objects.create(teacher=teacher, course=selected_course)
        # deleta o prof da fila

        queue_position.delete()
        # atualiza a posição dos outros profs
        
        for teacherQueuePosition in TeacherQueuePosition.objects.all():
            if teacherQueuePosition.position > 1:
                teacherQueuePosition.position = teacherQueuePosition.position - 1
                teacherQueuePosition.save()
        
        print(f"{teacher} selected {selected_course.title}")

